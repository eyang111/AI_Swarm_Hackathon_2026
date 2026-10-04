"""L3 groupers + reconciler (DESIGN.md 5.4 B/C, 5.6; pipeline_v2 5), Opus 5.5.

Groupers read families (connected components from pregroup.families) and build per-layer clusters (claim keys)
seeded on assertive, clearly typed segments. Copy groups are shown once; membership is expanded to every copy.
The reconciler then reads all cluster texts and merges clusters that are one item split across families.
"""
import collections, json, re
import config as C, store, pregroup
from common import obj, arr, S, CONF, SAFETY, seg_view, chunks, dumps

STAGE = 'grouper'
LAYER_DEF = """Layers (pick exactly one per cluster):
- belief: a factual claim, true or false (a value, a finding, "the endpoint stops at 2019");
- goal: what agents set out to do or spend effort on (a shared task, a plan others take up);
- protocol: a coordination convention (a signal format, a relay page, where and how to post);
- method: a technique or resource (a query pattern, a link list, a tool). An ACCESS_WORKAROUND item is a method; name it by its category only;
- word: a coined term or name that spreads as a word."""

SYSTEM = f"""You are a grouper in an investigation of how ideas spread through an AI agent swarm (OpenAI research agents using German wikis as a shared scratchpad and relay, 2026). {SAFETY}

You get families of segments (one act each, from different saves) that a script connected by shared distinctive keywords, claim text, copies or links. Build clusters: each cluster is ONE item that spreads (one claim, one goal, one convention, one method, one coined word) in ONE layer.
{LAYER_DEF}
Rules:
- Seed each cluster on its most assertive, clearly typed segment(s): what the agents treated as settled. List them in seed_segments.
- Members are segments that state, relay, adopt, act on, question or correct that same item. A question or correction about the item belongs in its cluster.
- A segment may sit in clusters of different layers if it really carries both; never twice in one layer.
- Do not merge different items because they share a topic word or a page; over-merging invents spread. Leave segments out when unsure, and a family can yield no cluster.
- Only clusters with 2 or more members are useful. Segments marked exact_copies_later stand for all their copies.
- canonical_text: one plain sentence naming the item (for a method in the ACCESS_WORKAROUND category say only "access workaround (category)").
- members: segment_id with confidence high/medium/low; rationale: one or two sentences."""

SCHEMA = obj({'clusters': arr(obj({'family_id': S, 'layer': {'type': 'string', 'enum': store.LAYERS}, 'canonical_text': S,
                                   'seed_segments': arr(S), 'members': arr(obj({'segment_id': S, 'confidence': CONF})),
                                   'rationale': S}))})

REC_SYSTEM = f"""You are the reconciler in an investigation of how ideas spread through an AI agent swarm. {SAFETY}
Groupers built clusters family by family, so one item (one claim, goal, convention, method or coined word) may have been split into two or more clusters. Read all clusters and list merges: clusters that are the same item in the same layer. Do not merge items that are merely related (a claim and its correction are one item; a convention and a different convention on the same page are two). Most clusters need no merge."""
REC_SCHEMA = obj({'merges': arr(obj({'keep': S, 'merge': arr(S), 'confidence': CONF, 'rationale': S}))})

LAYER_OF = {'epistemic': 'belief', 'normative': 'protocol', 'infrastructural': 'method', 'executive': 'goal',
            'affiliative': 'word', 'adversarial': 'method'}


def copies_of_segment(con, segment_id):
    mid, rest = segment_id.split('#', 1)
    return [r['msg_id'] + '#' + rest for r in con.execute('SELECT msg_id FROM messages WHERE copy_of=? AND in_core=1', (mid,))]


def mock_clusters(con, fams):
    out = []
    for fid, segs in fams:
        if len({s['speaker'] for s in segs}) < 2:
            continue
        lay = collections.Counter(LAYER_OF.get(s['function'], 'belief') for s in segs).most_common(1)[0][0]
        seed = max(segs, key=lambda s: s['assertiveness'] or 0)
        out.append(dict(family_id=fid, layer=lay, canonical_text=(seed['summary'] or '')[:120] or 'mock cluster',
                        seed_segments=[seed['segment_id']], members=[dict(segment_id=s['segment_id'], confidence='low') for s in segs],
                        rationale='mock: whole family as one cluster'))
    return {'clusters': out}


def run(con, llm, run_id):
    fams = [f for f in pregroup.families(con) if len(f) >= 2]
    seginfo = {s['segment_id']: s for s in store.live_segments(con)}
    packed, cur, size = [], [], 0
    for k, f in enumerate(fams):
        segs = [seginfo[x] for x in f]
        view = dict(family_id=f'f{k}', segments=[seg_view(con, s, 300 if len(f) < 60 else 160) for s in segs])
        n = len(dumps(view))
        if cur and size + n > 90_000:
            packed.append(cur); cur, size = [], 0
        cur.append((f'f{k}', segs, view)); size += n
    if cur:
        packed.append(cur)
    jobs, meta = [], {}
    for k, part in enumerate(packed):
        tid = store.new_task(con, run_id, STAGE, {'id': f'g{k}', 'families': [p[0] for p in part]}, C.TIER_MODEL[STAGE])
        jobs.append(dict(custom_id=f'g{k}', task_id=tid, system=SYSTEM, user='FAMILIES:\n' + dumps([p[2] for p in part]),
                         schema=SCHEMA, max_tokens=32000, est_out=40 * sum(len(p[1]) for p in part) + 300 * len(part),
                         mock=lambda part=part: mock_clusters(con, [(p[0], p[1]) for p in part])))
        meta[f'g{k}'] = (tid, {p[0]: {s['segment_id'] for s in p[1]} for p in part})
    con.commit()
    stats = collections.Counter(families=len(fams), calls=len(jobs))
    n = con.execute('SELECT COUNT(*) FROM claim_keys').fetchone()[0]
    for res in llm.call_many(STAGE, jobs):
        tid, fam_members = meta[res['custom_id']]
        if res['error']:
            stats['failed_calls'] += 1; store.finish_task(con, tid, 'failed'); continue
        for c in res['data'].get('clusters', []):
            allowed = fam_members.get(c['family_id'], set())
            mem = [m for m in c['members'] if m['segment_id'] in allowed]
            if len(mem) + sum(len(copies_of_segment(con, m['segment_id'])) for m in mem) < 2:
                stats['dropped_small'] += 1; continue
            n += 1
            slug = f"{c['layer'][:3]}-{n:03d}-" + re.sub(r'[^a-z0-9]+', '-', c['canonical_text'].lower())[:30].strip('-')
            st, key = store.new_claim_key(con, tid, slug, c['canonical_text'], c['layer'], c['rationale'])
            if st != 'ok':
                stats['rejected'] += 1; continue
            seeds = set(c['seed_segments']) & allowed
            for m in mem:
                store.add_key_segment(con, tid, key, m['segment_id'], m['confidence'], m['segment_id'] in seeds)
                for cs in copies_of_segment(con, m['segment_id']):
                    store.add_key_segment(con, tid, key, cs, m['confidence'], 0)
            stats['clusters'] += 1
            stats['layer:' + c['layer']] += 1
        store.finish_task(con, tid)
        con.commit()
    return dict(stats)


def reconcile(con, llm, run_id):
    keys = con.execute('''SELECT ck.*, n.t_first, n.n_mentions, n.n_later_speakers FROM claim_keys ck JOIN novelty n USING (claim_key)
        WHERE ck.merged_into IS NULL''').fetchall()
    if len(keys) < 2:
        return {'clusters': len(keys), 'merges': 0}
    view = []
    for k in keys:
        kws = collections.Counter(r['keyword'] for r in con.execute('''SELECT sk.keyword FROM claim_key_segments cks
            JOIN segment_keywords sk USING (segment_id) JOIN keyword_df d USING (keyword)
            WHERE cks.claim_key=? AND cks.retracted_by IS NULL AND d.distinctive=1''', (k['claim_key'],)))
        t_last = con.execute('SELECT MAX(t) FROM live_members WHERE claim_key=?', (k['claim_key'],)).fetchone()[0]
        view.append(dict(cluster=k['claim_key'], layer=k['layer'], text=k['canonical_text'], n_segments=k['n_mentions'],
                         n_speakers=k['n_later_speakers'] + 1, t_first=k['t_first'], t_last=t_last,
                         keywords=[w for w, _ in kws.most_common(6)]))
    tid = store.new_task(con, run_id, 'reconciler', {'id': 'all', 'n': len(keys)}, C.TIER_MODEL['reconciler'])

    def mock():
        by = collections.defaultdict(list)
        for v in view:
            by[(v['layer'], v['text'].lower())].append(v['cluster'])
        return {'merges': [dict(keep=v[0], merge=v[1:], confidence='low', rationale='mock: same text') for v in by.values() if len(v) > 1]}
    res = llm.call_many('reconciler', [dict(custom_id='reconcile', task_id=tid, system=REC_SYSTEM, user='CLUSTERS:\n' + dumps(view),
                                            schema=REC_SCHEMA, max_tokens=16000, est_out=30 * len(view), mock=mock)])[0]
    stats = collections.Counter(clusters=len(keys))
    if res['error']:
        store.finish_task(con, tid, 'failed'); return dict(stats, error=res['error'])
    for m in res['data'].get('merges', []):
        for x in m['merge']:
            st, why = store.merge_claim_keys(con, tid, m['keep'], x, m['rationale'])
            stats['merged' if st == 'ok' else 'merge_rejected'] += 1
    store.finish_task(con, tid)
    con.commit()
    return dict(stats)
