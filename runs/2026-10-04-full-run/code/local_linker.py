"""L2 local linkers (DESIGN.md 4.3, 5.4 A; pipeline_v2 3), Sonnet 5.5, one call per chunk of a window.

The script proposes candidate targets per segment (earlier segments sharing a distinctive keyword or claim text,
the page's previous save, the reader's reply hint, the most assertive earlier segment on a shared keyword as the
anchor candidate, and halo saves sharing a token). The model picks links; store.add_link enforces the 3-outgoing
cap, time order and the evidence quote.
"""
import collections, json, re
import config as C, store, pregroup
from common import obj, arr, S, CONF, NULLSTR, SAFETY, raw, seg_view, chunks, dumps
from window_plan import tokens

STAGE = 'local_linker'
LOCAL_TYPES = ['reply_to', 'acted_on', 'confirms', 'doubts', 'corrects', 'source_of', 'exposed_to', 'anchor']

SYSTEM = f"""You are a local linker in an investigation of how ideas spread through an AI agent swarm (OpenAI research agents using German wikis as a shared scratchpad and relay, 2026). {SAFETY}

For each FROM segment you get its raw text and reader labels, and a short list of earlier CANDIDATE segments or messages that share a distinctive keyword, claim text or page with it. Decide which candidates the FROM segment is actually connected to. At most 3 links per FROM segment, chosen in this order:
1. up to 2 links to the nearest earlier segments it replies to, continues, restates or evaluates;
2. 1 anchor link to the most assertive earlier segment on the same topic (the one that stated the thing most definitely), if that is a different segment.
Link types: reply_to (answers or continues it), acted_on (reports doing something because of it), confirms, doubts, corrects (evaluation acts aimed at it), source_of (the FROM segment's stated source is that earlier message, e.g. "other cohorts" or a page title resolved to it), exposed_to (the FROM agent evidently saw it, without it being the source), anchor (topic anchor as above).
via: direct_message (addresses it or replies on the same thread), shared_page (same page or a page it names), external_source, task_prompt (both plausibly come from the agents' common task), unknown.
Each link needs a quote: an exact substring (at most 200 characters) of the FROM message's raw text that shows the connection. Sharing a generic word is not a connection. Time order alone is not a connection. No link is a valid answer; most candidates should get none."""

SCHEMA = obj({'links': arr(obj({
    'from_segment': S, 'to_segment': NULLSTR, 'to_msg_id': NULLSTR,
    'type': {'type': 'string', 'enum': LOCAL_TYPES},
    'via': {'type': 'string', 'enum': store.VIAS}, 'quote': S, 'confidence': CONF, 'rationale': S}))})


_CM = {}


def _cm_index(con):
    """built once per run (full dump): reps in time order plus inverted indexes, so each window's lookups stay cheap"""
    if _CM.get('con') is con:
        return _CM
    segs = store.live_segments(con)
    core = {r[0]: r[1] for r in con.execute('SELECT msg_id, in_core FROM messages')}
    reps = [s for s in segs if not s['copy_of'] or not core.get(s['copy_of'])]
    reps.sort(key=lambda s: (s['t'], s['segment_id']))
    kws = collections.defaultdict(set)
    for r in con.execute('''SELECT sk.segment_id, sk.keyword FROM segment_keywords sk JOIN keyword_df d USING (keyword)
        WHERE d.distinctive=1'''):
        kws[r[0]].add(r[1])
    norms = collections.defaultdict(set)
    for c in con.execute('SELECT segment_id, norm_text FROM claims WHERE segment_id IS NOT NULL'):
        norms[c['segment_id']].add(c['norm_text'])
    by_kw, by_norm, by_msg = collections.defaultdict(list), collections.defaultdict(list), collections.defaultdict(list)
    for i, e in enumerate(reps):
        for k in kws[e['segment_id']]:
            by_kw[k].append(i)
        for n in norms[e['segment_id']]:
            by_norm[n].append(i)
        by_msg[e['msg_id']].append(i)
    halo_msgs = con.execute('SELECT msg_id, t, text, channel FROM messages WHERE in_core=0').fetchall()
    _CM.clear()
    _CM.update(con=con, reps=reps, pos={e['segment_id']: i for i, e in enumerate(reps)}, kws=kws, norms=norms,
               by_kw=by_kw, by_norm=by_norm, by_msg=by_msg, halo_msgs=halo_msgs,
               halo_tok={h['msg_id']: tokens(h['text']) for h in halo_msgs},
               hints={r['msg_id']: r['reply_to_hint'] for r in store.live_records(con)})
    return _CM


def candidate_map(con, window_core):
    X = _cm_index(con)
    reps, kws, norms, halo_msgs, halo_tok, hints = X['reps'], X['kws'], X['norms'], X['halo_msgs'], X['halo_tok'], X['hints']
    out = {}
    for i, s in enumerate(reps):
        if s['msg_id'] not in window_core:
            continue
        sid = s['segment_id']
        # earlier = reps before s in (t, segment_id) order, other messages only
        hit = set()
        for k in kws[sid]:
            hit.update(j for j in X['by_kw'][k] if j < i)
        for n in norms[sid]:
            hit.update(j for j in X['by_norm'][n] if j < i)
        same = [reps[j] for j in sorted(hit) if reps[j]['msg_id'] != s['msg_id']]
        cands = same[-4:]
        if same:
            anchor = max(same, key=lambda e: (e['assertiveness'] or 0, e['t']))
            if anchor not in cands:
                cands.append(anchor)
        m = con.execute('SELECT parent_msg_id, text FROM messages WHERE msg_id=?', (s['msg_id'],)).fetchone()
        for target in (m['parent_msg_id'], hints.get(s['msg_id'])):
            for j in X['by_msg'].get(target, []) if target else []:
                e = reps[j]
                if j < i and e['msg_id'] != s['msg_id'] and e not in cands:
                    cands.append(e)
        hm = []
        if halo_msgs:
            mt = tokens(m['text'][m['text'].find('\n') + 1:])
            hm = [h for h in halo_msgs if h['t'] < s['t'] and len(halo_tok[h['msg_id']] & mt) >= 1 and
                  any(len(t) > 6 for t in halo_tok[h['msg_id']] & mt)][-2:]
        if cands or hm:
            out[sid] = (s, cands, hm)
    return out


def mock_links(con, part):
    links = []
    for s, cands, hm in part:
        q = store.msg_text(con, s['msg_id'])[s['char_start']:s['char_end']].strip()[:60]
        if not q:
            continue
        for e in cands[-2:]:
            links.append(dict(from_segment=s['segment_id'], to_segment=e['segment_id'], to_msg_id=None,
                              type='reply_to' if e['channel'] == s['channel'] else 'exposed_to',
                              via='shared_page', quote=q, confidence='low', rationale='mock: shares a distinctive keyword'))
    return {'links': links}


def run(con, llm, run_id):
    wins = con.execute('SELECT * FROM windows ORDER BY window_id').fetchall()
    jobs, meta = [], {}
    for w in wins:
        cm = candidate_map(con, set(json.loads(w['core'])))
        items = list(cm.values())
        for k, part in enumerate(chunks(items, 35)):
            cid = f'{w["window_id"]}_{k}'
            tid = store.new_task(con, run_id, STAGE, {'id': cid, 'window': w['window_id']}, C.TIER_MODEL[STAGE])
            payload = []
            for s, cands, hm in part:
                v = seg_view(con, s, 500)
                v['candidates'] = [seg_view(con, e, 250, kw=True, claims=False) for e in cands] + \
                                  [dict(msg_id=h['msg_id'], t=h['t'], page=h['channel'], context_only=True, raw=raw(con, h['msg_id'], 250))
                                   for h in hm]
                payload.append(v)
            jobs.append(dict(custom_id=cid, task_id=tid, system=SYSTEM, user='FROM SEGMENTS:\n' + dumps(payload),
                             schema=SCHEMA, max_tokens=24000, est_out=120 * len(part),
                             mock=lambda part=part: mock_links(con, part)))
            meta[cid] = tid
    con.commit()
    stats = collections.Counter(calls=len(jobs))
    for res in llm.call_many(STAGE, jobs):
        tid = meta[res['custom_id']]
        if res['error']:
            stats['failed_calls'] += 1; store.finish_task(con, tid, 'failed'); continue
        for n, l in enumerate(res['data'].get('links', [])):
            st, why = store.add_link(con, tid, f'{tid}/l{n}', l['from_segment'], l.get('to_segment'), None, l.get('to_msg_id'),
                                     l['type'], l['quote'], l['confidence'], l['rationale'], via=l.get('via'), local=True)
            stats['ok' if st == 'ok' else 'rejected'] += 1
            if st != 'ok':
                stats['rej:' + why.split(' ')[0]] += 1
        store.finish_task(con, tid)
        con.commit()
    return dict(stats)
