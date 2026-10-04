"""Model calls for every tier: one-shot structured output, cached instructions, cost ledger, budget guard.

Backends
  anthropic : the real API. Readers go through the Message Batches API; other tiers are direct streaming calls
              (with the server-side refusal fallback, DESIGN.md 7.1) run in a thread pool.
  mock      : no network. Each job carries a `mock` function (a heuristic stand-in) so the whole pipeline can run
              and be tested offline. Mock usage is estimated from prompt size, so a mock run also prints a cost estimate.
"""
import json, os, time, threading, concurrent.futures as cf
import config as C, store, errlog


class BudgetExceeded(Exception):
    pass


def est_tokens(s):
    return int(len(s) / C.CHARS_PER_TOKEN) + 1


class LLM:
    def __init__(self, con, run_id, backend='anthropic', budget=25.0, log_dir=None, batch_all=False):
        self.con, self.run_id, self.backend, self.budget = con, run_id, backend, budget
        self.batch_all = batch_all          # send every tier through the Batch API (50% off, slower; no server-side fallback)
        self.log_dir = log_dir or C.CALL_LOG
        self.lock = threading.Lock()
        self.client = None
        self.fake_registry = {}
        if backend == 'anthropic' and os.environ.get('SI_FAKE_API'):
            import fake_api                                  # offline test of the real request/response path
            self.client = fake_api.make_client(self.fake_registry)
        elif backend == 'anthropic':
            import anthropic
            self.client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY') or os.environ.get('SI_ANTHROPIC_API_KEY'),
                                             max_retries=4, timeout=900)
        self.mock_refuse = set(filter(None, os.environ.get('SI_MOCK_REFUSE_IDS', '').split(',')))

    # ------------------------------------------------------------ helpers
    def _params(self, tier, system, user, schema, max_tokens):
        model = C.TIER_MODEL[tier]
        effort = C.TIER_EFFORT.get(tier, 'medium')
        return dict(model=model, max_tokens=max_tokens,
                    system=[{'type': 'text', 'text': system, 'cache_control': {'type': 'ephemeral'}}],
                    messages=[{'role': 'user', 'content': user}],
                    output_config={'effort': effort, 'format': {'type': 'json_schema', 'schema': schema}})

    def _guard(self, tier, jobs, batch):
        model = C.TIER_MODEL[tier]
        pin, pout = C.PRICE[model]
        disc = C.BATCH_DISCOUNT if batch else 1.0
        est = sum((est_tokens(j['system']) + est_tokens(j['user'])) * pin + j.get('est_out', 2000) * pout
                  for j in jobs) * disc / 1e6
        with self.lock:
            spent = store.spent(self.con)
        if self.backend != 'mock' and spent + est > self.budget:
            raise BudgetExceeded(f'{tier}: spent ${spent:.2f} + next ~${est:.2f} would pass the ${self.budget:.2f} budget')
        return est

    def _log(self, tier, custom_id, payload):
        d = os.path.join(self.log_dir, tier)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, custom_id.replace('/', '_') + '.json'), 'w') as f:
            json.dump(payload, f, ensure_ascii=False, indent=1, default=str)

    def _finish(self, tier, job, batch, text, usage, stop_reason, stop_details, model, alt_text=None):
        data, err = None, None
        if stop_reason == 'refusal':
            err = 'refusal'
        else:
            for t in [text] + ([alt_text] if alt_text and alt_text != text else []):
                try:
                    data, err = (json.loads(t) if t else None), None
                    if data is None:
                        err = 'empty'
                    break
                except json.JSONDecodeError:
                    err = 'max_tokens' if stop_reason == 'max_tokens' else 'bad_json'
        if err:
            errlog.log(tier, err, f'{err} from {model}', custom_id=job['custom_id'], task_id=job.get('task_id'),
                       stop_reason=stop_reason, category=(stop_details or {}).get('category') if isinstance(stop_details, dict) else None,
                       output_chars=len(text or ''))
        with self.lock:
            cost = store.record_usage(self.con, f"{self.run_id}/{tier}/{job['custom_id']}/{time.time_ns()}", job.get('task_id'),
                                      tier, model, batch, usage, stop_reason)
            self.con.commit()
        self._log(tier, job['custom_id'], dict(stop_reason=stop_reason, stop_details=stop_details, usage=usage,
                                              cost_usd=cost, model=model, batch=batch, error=err,
                                              prompt_chars=len(job['system']) + len(job['user']), output=data if data else text))
        return dict(custom_id=job['custom_id'], data=data, error=err, stop_reason=stop_reason,
                    category=(stop_details or {}).get('category') if isinstance(stop_details, dict) else None, model=model)

    def _mock(self, tier, job, batch):
        refused = any(m in job['user'] for m in self.mock_refuse)
        data = None if refused else job['mock']()
        text = json.dumps(data, ensure_ascii=False) if data is not None else ''
        usage = dict(input_tokens=est_tokens(job['user']), cache_read=est_tokens(job['system']),
                     output_tokens=max(est_tokens(text), job.get('est_out', 0)))
        return self._finish(tier, job, batch, text, usage, 'refusal' if refused else 'end_turn',
                            {'category': 'mock'} if refused else None, C.TIER_MODEL[tier])

    @staticmethod
    def _usage(u):
        return dict(input_tokens=u.input_tokens or 0, output_tokens=u.output_tokens or 0,
                    cache_read=getattr(u, 'cache_read_input_tokens', 0) or 0,
                    cache_write=getattr(u, 'cache_creation_input_tokens', 0) or 0)

    @staticmethod
    def _text(msg, after_fallback=True):
        """Text of the response. After a mid-stream refusal the server keeps the declined model's partial text, adds a
        `fallback` block, and the fallback model's output follows; that output usually restarts the JSON, so read
        only what comes after the last boundary (after_fallback=False joins everything, used as a second try)."""
        blocks = list(msg.content)
        if after_fallback:
            idx = [i for i, b in enumerate(blocks) if getattr(b, 'type', '') == 'fallback']
            if idx:
                blocks = blocks[idx[-1] + 1:]
        return ''.join(b.text for b in blocks if getattr(b, 'type', '') == 'text')

    def _declined_usage(self, tier, job, msg):
        """Bill the declined hops of a server-side fallback: top-level usage covers only the serving attempt."""
        its = getattr(msg.usage, 'iterations', None) or []
        if not any(getattr(it, 'type', '') == 'fallback_message' for it in its):
            return
        for k, it in enumerate(its):
            if getattr(it, 'type', '') != 'message':
                continue
            u = dict(input_tokens=getattr(it, 'input_tokens', 0) or 0, output_tokens=getattr(it, 'output_tokens', 0) or 0,
                     cache_read=getattr(it, 'cache_read_input_tokens', 0) or 0,
                     cache_write=getattr(it, 'cache_creation_input_tokens', 0) or 0)
            with self.lock:
                store.record_usage(self.con, f"{self.run_id}/{tier}/{job['custom_id']}/declined{k}/{time.time_ns()}",
                                   job.get('task_id'), tier, getattr(it, 'model', None) or C.TIER_MODEL[tier], False, u, 'refusal')
                self.con.commit()

    # ------------------------------------------------------------ direct calls (thread pool)
    def _direct(self, tier, job):
        if self.backend == 'mock':
            return self._mock(tier, job, False)
        import anthropic
        self.fake_registry[job['user']] = job['mock']
        p = self._params(tier, job['system'], job['user'], job['schema'], job.get('max_tokens', 16000))
        try:
            with self.client.beta.messages.stream(betas=['server-side-fallback-2026-07-01'], fallbacks='default', **p) as s:
                msg = s.get_final_message()
        except anthropic.BadRequestError as e:          # fallback not available on this key: plain call
            if 'fallback' not in str(e).lower():
                raise
            with self.client.messages.stream(**p) as s:
                msg = s.get_final_message()
        sd = msg.stop_details.model_dump() if getattr(msg, 'stop_details', None) else None
        self._declined_usage(tier, job, msg)
        return self._finish(tier, job, False, self._text(msg), self._usage(msg.usage), msg.stop_reason, sd, msg.model,
                            alt_text=self._text(msg, after_fallback=False))

    def call_many(self, tier, jobs, workers=6):
        if not jobs:
            return []
        if self.batch_all:
            res = self.batch(tier, jobs)
            out = [res.get(j['custom_id']) or dict(custom_id=j['custom_id'], data=None, error='missing batch result',
                                                   stop_reason=None, category=None, model=C.TIER_MODEL[tier]) for j in jobs]
        else:
            self._guard(tier, jobs, False)
            out = self._run_direct(tier, jobs, workers)
        return self._repair(tier, jobs, out)

    def _run_direct(self, tier, jobs, workers=6):
        out = [None] * len(jobs)
        if self.backend == 'mock':
            workers = 1                       # mock functions read the db; keep them on one thread
        if workers == 1:
            for i, j in enumerate(jobs):
                out[i] = self._safe_direct(tier, j)
            return out
        with cf.ThreadPoolExecutor(min(workers, len(jobs))) as ex:
            futs = {ex.submit(self._safe_direct, tier, j): i for i, j in enumerate(jobs)}
            for f in cf.as_completed(futs):
                out[futs[f]] = f.result()
        return out

    def _safe_direct(self, tier, job):
        try:
            return self._direct(tier, job)
        except BudgetExceeded:
            raise
        except Exception as e:                    # keep going; the error log and call log keep the reason
            err = f'exception: {e!r}'[:500]
            errlog.log(tier, 'call_exception', err, exc=e, custom_id=job['custom_id'], task_id=job.get('task_id'))
            self._log(tier, job['custom_id'], dict(error=err, model=C.TIER_MODEL[tier],
                                                  prompt_chars=len(job['system']) + len(job['user'])))
            return dict(custom_id=job['custom_id'], data=None, error=err, stop_reason=None, category=None,
                        model=C.TIER_MODEL[tier])

    # ------------------------------------------------------------ retry and split for failed calls
    RETRYABLE = ('bad_json', 'empty', 'max_tokens', 'exception', 'missing batch result', 'batch ')

    @staticmethod
    def _split(job):
        """Halve a job whose user payload is 'LABEL:\n' + a JSON list (every tier after the readers builds it so)."""
        head, sep, body = job['user'].partition(':\n')
        try:
            items = json.loads(body) if sep else None
        except json.JSONDecodeError:
            return None
        if not isinstance(items, list) or len(items) < 2:
            return None
        mid = len(items) // 2
        dump = lambda xs: json.dumps(xs, ensure_ascii=False, separators=(',', ':'))
        return [dict(job, custom_id=f"{job['custom_id']}.{k}", user=f'{head}:\n' + dump(part),
                     est_out=max(200, job.get('est_out', 2000) // 2)) for k, part in enumerate((items[:mid], items[mid:]))]

    @staticmethod
    def _merge(parts):
        """Merge the data of split halves: list fields are concatenated, other fields keep the first value."""
        data = {}
        for d in parts:
            for k, v in (d or {}).items():
                if isinstance(v, list):
                    data.setdefault(k, []).extend(v)
                else:
                    data.setdefault(k, v)
        return data

    def _repair(self, tier, jobs, out, depth=0):
        """One plain retry for a failed call, then split it in halves (up to 3 levels) so one bad item cannot sink
        the whole chunk. A refusal is not retried as is (the server-side fallback already had its go) but is split,
        which isolates the items that trip the classifier. Everything that still fails goes to the error log.
        Readers are skipped: readers.py runs its own halo-first bisection and records coverage gaps."""
        if tier == 'reader':
            return out
        for i, (j, r) in enumerate(zip(jobs, out)):
            if not r or not r['error']:
                continue
            first_err = r['error']
            if depth == 0 and first_err.startswith(self.RETRYABLE):
                self._guard(tier, [j], False)
                r2 = self._safe_direct(tier, dict(j, custom_id=j['custom_id'] + '.retry'))
                if not r2['error']:
                    errlog.log(tier, 'recovered_by_retry', first_err, custom_id=j['custom_id'])
                    out[i] = dict(r2, custom_id=j['custom_id'], recovered='retry')
                    continue
                r = r2
            halves = self._split(j) if depth < 3 else None
            if not halves:
                errlog.log(tier, 'call_failed', r['error'], custom_id=j['custom_id'], task_id=j.get('task_id'),
                           first_error=first_err, depth=depth)
                continue
            self._guard(tier, halves, False)
            sub = self._repair(tier, halves, self._run_direct(tier, halves), depth + 1)
            ok = [s for s in sub if not s['error']]
            if not ok:
                out[i] = dict(r, custom_id=j['custom_id'])
                continue
            failed = [h['custom_id'] for h, s in zip(halves, sub) if s['error']]
            errlog.log(tier, 'recovered_by_split' if not failed else 'partial_after_split', first_err,
                       custom_id=j['custom_id'], failed_parts=failed)
            out[i] = dict(custom_id=j['custom_id'], data=self._merge([s['data'] for s in ok]), error=None,
                          stop_reason=ok[0]['stop_reason'], category=None, model=ok[0]['model'],
                          recovered='split' if not failed else 'partial', failed_parts=failed)
        return out

    # ------------------------------------------------------------ Message Batches (readers)
    def batch(self, tier, jobs, poll_s=30):
        if not jobs:
            return {}
        self._guard(tier, jobs, True)
        if self.backend == 'mock':
            return {j['custom_id']: self._mock(tier, j, True) for j in jobs}
        for j in jobs:
            self.fake_registry[j['user']] = j['mock']
        from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
        from anthropic.types.messages.batch_create_params import Request
        reqs = [Request(custom_id=j['custom_id'], params=MessageCreateParamsNonStreaming(
            **self._params(tier, j['system'], j['user'], j['schema'], j.get('max_tokens', 64000)))) for j in jobs]
        b = self.client.messages.batches.create(requests=reqs)
        print(f'  batch {b.id}: {len(reqs)} requests submitted', flush=True)
        while True:
            b = self.client.messages.batches.retrieve(b.id)
            if b.processing_status == 'ended':
                break
            rc = b.request_counts
            print(f'  batch {b.id}: processing {rc.processing}, succeeded {rc.succeeded}, errored {rc.errored}', flush=True)
            time.sleep(0 if os.environ.get('SI_FAKE_API') else poll_s)
        byid = {j['custom_id']: j for j in jobs}
        out = {}
        for r in self.client.messages.batches.results(b.id):
            j = byid[r.custom_id]
            if r.result.type == 'succeeded':
                m = r.result.message
                sd = m.stop_details.model_dump() if getattr(m, 'stop_details', None) else None
                out[r.custom_id] = self._finish(tier, j, True, self._text(m), self._usage(m.usage), m.stop_reason, sd, m.model)
            else:
                err = getattr(getattr(r.result, 'error', None), 'error', None)
                out[r.custom_id] = dict(custom_id=r.custom_id, data=None, error=f'batch {r.result.type}: {err}'[:500],
                                        stop_reason=None, category=None, model=C.TIER_MODEL[tier])
        return out
