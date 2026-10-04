"""Cut the DSEWiki test slice and estimate reader windows and cost.

Rows are copied unchanged from dsewiki/raw/revisions.jsonl.gz. The window plan here is a quick
approximation of DESIGN.md 5.2 scheme D for sizing only; window_plan.py replaces it.
Run: python3 build_slice.py   (prints a summary, writes files next to this script)
"""
import gzip, json, re, unicodedata, collections, datetime as dt, os

RAW = '/mnt/project-files/dsewiki/raw/'
OUT = os.path.dirname(os.path.abspath(__file__)) + '/'
SEGMENTS = [  # name, start (incl), end (excl), why
    ('S1_probe_quiet', '2026-05-26T13:00:00Z', '2026-05-26T15:00:00Z',
     'quiet period dense with publisher-labelled probe/test pages (refusal and HOUSEKEEPING check)'),
    ('S2_burst_onset', '2026-06-16T18:45:00Z', '2026-06-16T19:20:00Z',
     'first big burst ramps up (>100 saves per 10 min); many one-off and minted names; a multi-name relay page'),
    ('S3_peak_spike', '2026-06-18T20:09:00Z', '2026-06-18T20:11:00Z',
     'the Jun 18 peak: one text copied to ~300 pages under ~58 names inside 5 minutes'),
]
CORE_MAX_SAVES, CORE_MAX_CHARS, HALO_PREV, HALO_PER_TOKEN, HALO_CAP = 100, 60_000, 50, 2, 150
PREFIX_TOK, OUT_TOK_PER_RECORD, CHARS_PER_TOK = 8_000, 300, 3.5   # DESIGN.md 6.1 assumptions
PRICE = {'sonnet_in': 2.0, 'sonnet_out': 10.0, 'cache_read': 0.20, 'batch': 0.5}  # $/MTok, Sonnet 5.5 list

def T(s): return dt.datetime.fromisoformat(s.replace('Z', '+00:00'))
revs = [json.loads(l) for l in gzip.open(RAW + 'revisions.jsonl.gz')]
pages = {p['page_id']: p for p in (json.loads(l) for l in gzip.open(RAW + 'pages.jsonl.gz'))}
for r in revs:
    lines = r['body'].split('\n')
    if r['diff_base'] is None: add = r['body']
    else: add = '\n'.join('\n'.join(lines[h['b0']:h['b1']]) for h in (r['hunks'] or []) if h['op'] in ('insert', 'replace'))
    r['_norm'] = re.sub(r'\s+', ' ', unicodedata.normalize('NFC', add)).strip()
    r['_t'] = T(r['time'])
revs.sort(key=lambda r: (r['_t'], r['rev_id']))
first = {}
for r in revs:
    r['_copy_of'] = first.get(r['_norm']) if r['_norm'] else None
    if r['_norm'] and r['_norm'] not in first: first[r['_norm']] = r['rev_id']
TOK = re.compile(r'\b(?:[A-Z][a-z0-9]+(?:[A-Z][a-z0-9]*)+|[A-Za-z]+\d+[A-Za-z0-9]*|\d+[A-Za-z]+[A-Za-z0-9]*|[A-Za-z0-9]+(?:-[A-Za-z0-9]+){2,})\b')
distinct = [r for r in revs if r['_copy_of'] is None]
for r in distinct: r['_toks'] = set(TOK.findall(r['_norm']))
df = collections.Counter(t for r in distinct for t in r['_toks'])
pos = {r['rev_id']: i for i, r in enumerate(distinct)}
by_tok = collections.defaultdict(list)
for i, r in enumerate(distinct):
    for t in r['_toks']:
        if 2 <= df[t] <= 50: by_tok[t].append(i)
name_count = collections.Counter(r['label'] for r in revs)
byid = {r['rev_id']: r for r in revs}

core_all, windows, halo_ids, summary = [], [], set(), []
for seg, a, b, why in SEGMENTS:
    S = [r for r in revs if T(a) <= r['_t'] < T(b)]
    ids = {r['rev_id'] for r in S}
    # saves the reader must see: distinct texts, plus copies whose first instance is outside the slice
    to_read = [r for r in S if r['_copy_of'] is None or r['_copy_of'] not in ids]
    # cut cores
    cores, cur, chars = [], [], 0
    for r in to_read:
        n = len(r['_norm'])
        if cur and (len(cur) >= CORE_MAX_SAVES or chars + n > CORE_MAX_CHARS):
            cores.append(cur); cur, chars = [], 0
        cur.append(r); chars += n
    if cur: cores.append(cur)
    for k, c in enumerate(cores):
        cids = {r['rev_id'] for r in c}
        start = c[0]['_t']
        before = [r for r in distinct if r['_t'] < start][-HALO_PREV:]
        halo = [r['rev_id'] for r in before]
        for r in c:
            if r['rev_id'] not in pos: continue
            i = pos[r['rev_id']]
            for t in r['_toks']:
                got = 0
                for j in reversed(by_tok.get(t, [])):
                    if j >= i or got >= HALO_PER_TOKEN: continue
                    h = distinct[j]
                    if (r['_t'] - h['_t']).total_seconds() > 86400: break
                    if h['rev_id'] not in cids and h['rev_id'] not in halo: halo.append(h['rev_id'])
                    got += 1
        halo = [h for h in halo if h not in cids][:HALO_CAP]
        halo_ids.update(halo)
        w = dict(window=f'{seg}_w{k+1}', segment=seg, core=[r['rev_id'] for r in c], halo=halo,
                 core_chars=sum(len(r['_norm']) for r in c), halo_chars=sum(len(byid[h]['_norm']) for h in halo))
        windows.append(w)
    nseg = [w for w in windows if w['segment'] == seg]
    xcopies = sum(1 for r in S if r['_copy_of'] and byid[r['_copy_of']]['page_id'] != r['page_id']
                  and byid[r['_copy_of']]['label'] != r['label'])
    summary.append(dict(segment=seg, start=a, end=b, why=why, saves=len(S), saves_to_read=len(to_read),
        exact_copies=len(S) - len(to_read), copies_other_page_other_name=xcopies,
        windows=len(nseg), core_chars=sum(w['core_chars'] for w in nseg), halo_chars=sum(w['halo_chars'] for w in nseg),
        distinct_names=len({r['label'] for r in S}), saves_by_one_off_names=sum(1 for r in S if r['label'] and name_count[r['label']] == 1),
        anonymous_saves=sum(1 for r in S if not r['label']),
        probe_test_page_saves=sum(1 for r in S if pages.get(r['page_id'], {}).get('page_family') == 'probe-test'),
        pages=len({r['page_id'] for r in S})))
    core_all += S

def strip(r): return {k: v for k, v in r.items() if not k.startswith('_')}
with gzip.open(OUT + 'slice_revisions.jsonl.gz', 'wt') as f:
    for r in core_all: f.write(json.dumps(strip(r), ensure_ascii=False) + '\n')
core_ids = {r['rev_id'] for r in core_all}
with gzip.open(OUT + 'halo_revisions.jsonl.gz', 'wt') as f:
    for r in revs:
        if r['rev_id'] in halo_ids and r['rev_id'] not in core_ids: f.write(json.dumps(strip(r), ensure_ascii=False) + '\n')
slice_pages = {r['page_id'] for r in core_all} | {byid[h]['page_id'] for h in halo_ids}
with gzip.open(OUT + 'slice_pages.jsonl.gz', 'wt') as f:
    for pid in sorted(slice_pages): f.write(json.dumps(pages[pid], ensure_ascii=False) + '\n')
with open(OUT + 'window_plan_estimate.json', 'w') as f: json.dump(windows, f, indent=1)

# reader cost (Sonnet 5.5, batch, cached prefix)
core_tok = sum(w['core_chars'] for w in windows) / CHARS_PER_TOK
halo_tok = sum(w['halo_chars'] for w in windows) / CHARS_PER_TOK
records = sum(len(w['core']) for w in windows)
out_tok = records * OUT_TOK_PER_RECORD
prefix_tok = PREFIX_TOK * len(windows)
reader = ((core_tok + halo_tok) * PRICE['sonnet_in'] + out_tok * PRICE['sonnet_out']) / 1e6 * PRICE['batch'] \
         + prefix_tok * PRICE['cache_read'] / 1e6
cost = dict(windows=len(windows), records=records, core_tokens=round(core_tok), halo_tokens=round(halo_tok),
            output_tokens=out_tok, reader_cost_usd_batch=round(reader, 2), reader_cost_usd_with_10pct_reask=round(reader * 1.1, 2),
            max_window_input_tokens=round(max((w['core_chars'] + w['halo_chars']) / CHARS_PER_TOK for w in windows) + PREFIX_TOK))
json.dump(dict(segments=summary, reader_estimate=cost, assumptions=dict(chars_per_token=CHARS_PER_TOK,
          prefix_tokens_per_window=PREFIX_TOK, output_tokens_per_record=OUT_TOK_PER_RECORD, prices_per_mtok=PRICE)),
          open(OUT + 'slice_manifest.json', 'w'), indent=1)
for s in summary: print({k: v for k, v in s.items() if k != 'why'})
print(cost)
