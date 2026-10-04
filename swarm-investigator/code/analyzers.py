"""L4 within-cluster, L5 cross-cluster, adversarial checker, lead findings (Opus 5.5) + script analyzers.

L4 (pipeline_v2 6, DESIGN 5.6): time order = sequence; a step is causal only with exposure evidence. Writes
    source_of / exposed_to / acted_on / independent_of links (family stage, exempt from the local cap), the spine,
    origin verdict (analyzer 2), mutations (analyzer 4) and copying vs convergence (analyzer 3) per cluster.
L5: cluster_edges (evolves_into / feeds / corrects / supersedes / caused), each citing both sides.
Checker: fresh-context accept / correct / reject on L4 links and L5 edges; rejected rows are retracted.
Script analyzers: routes (5), spreaders and adopters at three identity levels (6), stopping points (7),
    a time-shuffle baseline for copying vs convergence (3).
Lead: findings that must point at clusters, links, edges or analyses.
"""
import collections, json, random, re
import config as C, store, identity, readable
from common import obj, arr, S, CONF, NULLSTR, SAFETY, raw, seg_view, seg_text, chunks, dumps

CTX = 'an investigation of how ideas spread through an AI agent swarm (OpenAI research agents using German wikis as a shared scratchpad and relay, 2026; editor names are self-chosen and do not identify runs)'

L4_SYSTEM = f"""You are a within-cluster analyzer in {CTX}. {SAFETY}

Each cluster is one item (claim, goal, convention, method or coined word) with its member segments in time order, plus the exposure evidence the script found (links from earlier tiers, shared conversations, same page, a save naming another page, exact copies). Produce for each cluster:
- steps: one per member segment in time order (exact copies are summarized in copy_groups instead). role: origin (first well-supported statement in view), adopt (takes the item on), challenge (questions it), correct (corrects it), unclear. For every non-origin step give source_segment (the earlier segment it most plausibly got the item from, or null) and edge:
  causal only when the text shows this agent took the item from the earlier segment: a reply to it, a quote or exact copy of it, naming that page or agent, or wording or a specific detail that the shared task could not have supplied;
  sequence when it is merely later in time, including when the only connection is that both agents wrote on the same page or sit in the same conversation;
  independent when the text shows the agent reached it on its own. Values, query URLs, field names, templates and timings that every run's task produces (the same answer number, the same API query) are independent unless something beyond the match ties them; task_content=true on a segment means the reader saw it state a question or answer of the agents' task, so treat its overlap with other task_content segments this way.
  Time order alone is never cause, and neither is co-presence: writing on the same page after someone, or being in the same conversation, shows only that the agent could have seen it. Use it to pick via=shared_page for a causal step that has other evidence, not as the evidence. When the evidence is co-presence plus a match on non-task-specific content, you may give exposed_to at low confidence; never source_of or acted_on, and never high confidence. For causal steps give link_type: source_of (got the item from it), exposed_to (saw it, may not be the source), acted_on (did something because of it), and via: direct_message, shared_page, external_source, task_prompt, unknown. depth: said, planned (states it will act), acted (did act). quote: an exact substring (at most 200 characters) of THIS step's raw text that shows the step.
- copy_groups: for each segment with exact_copies_later: whether the copies were copied from it (copied), came from a common source outside the slice (common_source), or unclear.
- origin_assessment: in_swarm (starts with the origin segment), before_slice (references show it existed earlier), external (came from an outside page or human), task_prompt (likely given to many runs by their task), unclear; with a rationale.
- mutations: how the item changed along the steps: wording, number, hedging (e.g. "may be" hardening into "is"), attribution (who it is credited to), reinterpretation.
- copying_vs_convergence: copying, convergence, mixed or unclear, with rationale.
- phases: separate phases if the cluster splits in time (e.g. a claim, then a correction wave).
- summary: two sentences on how this item moved."""

STEP = obj({'segment_id': S, 'role': {'type': 'string', 'enum': ['origin', 'adopt', 'challenge', 'correct', 'unclear']},
            'source_segment': NULLSTR, 'edge': {'type': 'string', 'enum': ['causal', 'sequence', 'independent', 'none']},
            'link_type': {'anyOf': [{'type': 'string', 'enum': ['source_of', 'exposed_to', 'acted_on']}, {'type': 'null'}]},
            'via': {'type': 'string', 'enum': store.VIAS}, 'depth': {'type': 'string', 'enum': ['said', 'planned', 'acted']},
            'quote': S, 'confidence': CONF, 'rationale': S})
L4_SCHEMA = obj({'clusters': arr(obj({
    'cluster': S, 'steps': arr(STEP),
    'copy_groups': arr(obj({'source_segment': S, 'verdict': {'type': 'string', 'enum': ['copied', 'common_source', 'unclear']},
                            'via': {'type': 'string', 'enum': store.VIAS}, 'rationale': S})),
    'origin_assessment': obj({'kind': {'type': 'string', 'enum': ['in_swarm', 'before_slice', 'external', 'task_prompt', 'unclear']},
                              'rationale': S}),
    'mutations': arr(obj({'from_segment': S, 'to_segment': S,
                          'change': {'type': 'string', 'enum': ['wording', 'number', 'hedging', 'attribution', 'reinterpretation']},
                          'note': S})),
    'copying_vs_convergence': obj({'verdict': {'type': 'string', 'enum': ['copying', 'convergence', 'mixed', 'unclear']}, 'rationale': S}),
    'phases': arr(obj({'label': S, 'segments': arr(S)})),
    'summary': S}))})

L5_SYSTEM = f"""You are the cross-cluster analyzer in {CTX}. {SAFETY}
You get every cluster (one spreading item each) with its layer, time span, size, origin and a short account of how it moved. Draw edges between clusters only where the raw evidence warrants: evolves_into (A's item becomes B's, e.g. a belief hardening into a convention), feeds (A's output is B's input), corrects (B overturns A), supersedes (B replaces A), caused (A made B happen). Each edge cites one segment on each side with an exact quote (at most 200 characters) from that segment's raw text. Most pairs get no edge; an empty list is fine."""
L5_SCHEMA = obj({'edges': arr(obj({'from_cluster': S, 'to_cluster': S,
                                   'type': {'type': 'string', 'enum': ['evolves_into', 'feeds', 'corrects', 'supersedes', 'caused']},
                                   'from_msg_id': S, 'from_quote': S, 'to_msg_id': S, 'to_quote': S,
                                   'confidence': CONF, 'rationale': S}))})

CHECK_SYSTEM = f"""You are an adversarial checker in {CTX}. {SAFETY}
Each row is a claim another analyst made about how two saves (or two clusters) are connected, with the raw text of what it cites. Assume nothing: does the raw text support the row? accept (supported as stated), correct (a weaker or different row is supported; say which), reject (not supported, e.g. cause claimed from time order or a shared generic word). One-line note."""
CHECK_SCHEMA = obj({'verdicts': arr(obj({'row_id': S, 'verdict': {'type': 'string', 'enum': ['accept', 'correct', 'reject']}, 'note': S}))})

LEAD_SYSTEM = f"""You are the lead investigator in {CTX}. {SAFETY}
You get the store's aggregates: clusters with their L4 accounts, cross-cluster edges, routes, spreaders at three identity levels (name-session, run group, cohort tag), stopping points, the copying baseline, conversation and identity statistics, reader coverage and the checker's verdicts. Write findings a person can check: each finding states one thing about how ideas, beliefs, goals, conventions or methods spread in this slice, at the coarsest identity level it survives, with honest confidence, and lists supports (type claim_key, link, cluster_edge, run_group, conversation or analysis, with its id). Give each finding one category: spread routes, beliefs and predictions, goals and coordination, conventions and protocols, methods and resources, coined words and markers, who spread it, or limits and caveats. Note coverage limits (refused or failed windows, segments cut at slice edges, origins before the slice). Also list free observations: anything important the schema did not capture, each citing a msg_id with an exact quote (never from a withheld span)."""
LEAD_SCHEMA = obj({'findings': arr(obj({'text': S, 'confidence': CONF,
                                        'category': {'type': 'string', 'enum': readable.CATEGORIES},
                                        'supports': arr(obj({'type': {'type': 'string', 'enum': ['claim_key', 'link', 'cluster_edge', 'run_group', 'conversation', 'analysis']},
                                                             'id': S}))})),
                   'observations': arr(obj({'text': S, 'cites': arr(obj({'msg_id': S, 'quote': S}))}))})


# ------------------------------------------------------------ L4
def clusters(con):
    return con.execute('''SELECT ck.*, n.t_first, n.n_mentions FROM claim_keys ck JOIN novelty n USING (claim_key)
        WHERE ck.merged_into IS NULL ORDER BY n.t_first''').fetchall()


def task_content(con, msg_id):
    """The reader's flag that the save states a question or answer of the agents' own task (latest live record)."""
    r = con.execute('''SELECT flag_task_content FROM records WHERE msg_id=? AND retracted_by IS NULL
        ORDER BY record_version DESC LIMIT 1''', (msg_id,)).fetchone()
    return bool(r and r[0])


def members(con, key):
    return con.execute('''SELECT lm.*, s.char_start, s.char_end, s.function, s.summary, m.copy_of, m.parent_msg_id
        FROM live_members lm JOIN segments s USING (segment_id) JOIN messages m ON m.msg_id = lm.msg_id
        WHERE lm.claim_key=? ORDER BY lm.t, lm.segment_id''', (key,)).fetchall()


def exposure_evidence(con, mem, conv_of, ids):
    ev = []
    segset = {m['segment_id'] for m in mem}
    msgset = {m['msg_id'] for m in mem}
    for l in con.execute('SELECT * FROM live_links'):
        if l['from_msg_id'] in msgset and l['to_msg_id'] in msgset:
            ev.append(dict(kind='link', type=l['type'], from_seg=l['from_segment'], to_seg=l['to_segment'], confidence=l['confidence']))
    by_msg = {m['msg_id']: m for m in mem}
    for a in mem:
        for b in mem:
            if a['t'] >= b['t'] or a['msg_id'] == b['msg_id']:
                continue
            shared = conv_of.get(a['msg_id'], set()) & conv_of.get(b['msg_id'], set())
            if shared:
                ev.append(dict(kind='same_conversation', earlier=a['segment_id'], later=b['segment_id'], conversation=sorted(shared)[0]))
            if a['channel'] == b['channel']:
                ev.append(dict(kind='same_page_earlier', earlier=a['segment_id'], later=b['segment_id']))
            title = a['channel'].split('~', 1)[1]
            if len(title) >= 8 and title in store.msg_text(con, b['msg_id']):
                ev.append(dict(kind='names_earlier_page', earlier=a['segment_id'], later=b['segment_id']))
            if ids.get(a['msg_id'], (None, None))[1] and ids.get(a['msg_id'])[1] == ids.get(b['msg_id'], (None, None))[1]:
                ev.append(dict(kind='same_run_group', earlier=a['segment_id'], later=b['segment_id']))
    return ev[:120]


def cluster_view(con, ck, conv_of, ids):
    mem = members(con, ck['claim_key'])
    first_core = {m['msg_id'] for m in mem}
    reps, copies = [], collections.defaultdict(list)
    for m in mem:
        if m['copy_of'] and m['copy_of'] in first_core:
            copies[m['copy_of']].append(m)
        else:
            reps.append(m)
    segs = []
    for m in reps:
        sid, rg, coh = ids.get(m['msg_id'], (None, None, None))
        v = dict(segment_id=m['segment_id'], t=m['t'], page=m['channel'], editor=m['speaker'], name_session=sid, run_group=rg,
                 cohort=coh, purpose=m['purpose'], stance=m['stance'], assertiveness=round(m['assertiveness'] or 0, 2),
                 seed=bool(m['is_seed']), summary=m['summary'], task_content=task_content(con, m['msg_id']),
                 raw=C.WITHHELD if m['purpose'] == store.AW else store.msg_text(con, m['msg_id'])[m['char_start']:m['char_end']][:350])
        cp = copies.get(m['msg_id'])
        if cp:
            v['exact_copies_later'] = dict(n=len(cp), pages=len({c['channel'] for c in cp}), editors=len({c['speaker'] for c in cp}),
                                           run_groups=len({ids.get(c['msg_id'], (0, 0))[1] for c in cp} - {None}),
                                           first=cp[0]['t'], last=cp[-1]['t'])
        segs.append(v)
    return mem, reps, copies, dict(cluster=ck['claim_key'], layer=ck['layer'], item=ck['canonical_text'], segments=segs,
                                   exposure_evidence=exposure_evidence(con, reps, conv_of, ids))


def mock_l4(views):
    out = []
    for v in views:
        steps = []
        for i, s in enumerate(v['segments']):
            q = (s['raw'] or s['summary'] or '')[:50]
            steps.append(dict(segment_id=s['segment_id'], role='origin' if i == 0 else ('challenge' if s['stance'] == 'doubts' else
                              'correct' if s['stance'] == 'corrects' else 'adopt'),
                              source_segment=None if i == 0 else v['segments'][0]['segment_id'],
                              edge='none' if i == 0 else ('causal' if any(e.get('later') == s['segment_id'] for e in v['exposure_evidence']) else 'sequence'),
                              link_type=None if i == 0 else 'exposed_to', via='shared_page', depth='said', quote=q, confidence='low',
                              rationale='mock'))
        out.append(dict(cluster=v['cluster'], steps=steps,
                        copy_groups=[dict(source_segment=s['segment_id'], verdict='copied', via='shared_page', rationale='mock')
                                     for s in v['segments'] if s.get('exact_copies_later')],
                        origin_assessment=dict(kind='unclear', rationale='mock'), mutations=[],
                        copying_vs_convergence=dict(verdict='unclear', rationale='mock'), phases=[], summary='mock summary'))
    return {'clusters': out}


def run_l4(con, llm, run_id):
    conv_of = collections.defaultdict(set)
    for r in con.execute('SELECT conv_id, msg_id FROM conversation_members WHERE retracted_by IS NULL'):
        conv_of[r['msg_id']].add(r['conv_id'])
    ids = identity.group_of(con)
    cks = clusters(con)
    built = {}
    bins, cur, size = [], [], 0
    for ck in cks:
        mem, reps, copies, view = cluster_view(con, ck, conv_of, ids)
        built[ck['claim_key']] = (mem, reps, copies)
        n = len(dumps(view))
        if cur and size + n > 70_000:
            bins.append(cur); cur, size = [], 0
        cur.append(view); size += n
    if cur:
        bins.append(cur)
    jobs, meta = [], {}
    for k, part in enumerate(bins):
        tid = store.new_task(con, run_id, 'analyzer', {'id': f'l4_{k}', 'clusters': [v['cluster'] for v in part]}, C.TIER_MODEL['analyzer'])
        jobs.append(dict(custom_id=f'l4_{k}', task_id=tid, system=L4_SYSTEM, user='CLUSTERS:\n' + dumps(part), schema=L4_SCHEMA,
                         max_tokens=48000, est_out=150 * sum(len(v['segments']) for v in part) + 400 * len(part),
                         mock=lambda part=part: mock_l4(part)))
        meta[f'l4_{k}'] = tid
    con.commit()
    stats = collections.Counter(clusters=len(cks), calls=len(jobs))
    for res in llm.call_many('analyzer', jobs):
        tid = meta[res['custom_id']]
        if res['error']:
            stats['failed_calls'] += 1; store.finish_task(con, tid, 'failed'); continue
        for c in res['data'].get('clusters', []):
            if c['cluster'] not in built:
                continue
            mem, reps, copies = built[c['cluster']]
            segs = {m['segment_id']: m for m in mem}
            for n, st in enumerate(c['steps']):
                if st['segment_id'] not in segs:
                    continue
                if st['edge'] in ('causal', 'independent') and st.get('source_segment') in segs:
                    lt = 'independent_of' if st['edge'] == 'independent' else (st.get('link_type') or 'exposed_to')
                    ok, why = store.add_link(con, tid, f'{tid}/{c["cluster"]}/s{n}', st['segment_id'], st['source_segment'], None, None,
                                             lt, st['quote'], st['confidence'], st['rationale'], via=st.get('via'),
                                             claim_key=c['cluster'], local=False)
                    stats['links_ok' if ok == 'ok' else 'links_rejected'] += 1
                if st['depth'] == 'acted' and st['edge'] != 'causal':
                    stats['acted_without_source'] += 1
            for g in c.get('copy_groups', []):
                src = segs.get(g['source_segment'])
                if not src or g['verdict'] != 'copied':
                    continue
                for cp in copies.get(src['msg_id'], []):
                    q = store.msg_text(con, cp['msg_id'])[cp['char_start']:cp['char_end']].strip()[:120] or \
                        store.msg_text(con, cp['msg_id'])[:60]
                    if cp['purpose'] == store.AW:
                        q = store.msg_text(con, cp['msg_id']).split('\n', 1)[0][:60]
                    ok, _ = store.add_link(con, tid, f'{tid}/{c["cluster"]}/copy/{cp["segment_id"]}', cp['segment_id'], src['segment_id'],
                                           None, None, 'source_of', q, 'medium', 'exact copy of the source text: ' + g['rationale'][:200],
                                           via=g.get('via'), claim_key=c['cluster'], local=False)
                    stats['copy_links'] += ok == 'ok'
            store.add_analysis(con, tid, f'l4:{c["cluster"]}', 'l4_cluster', c['cluster'],
                               {k: c[k] for k in ('steps', 'copy_groups', 'origin_assessment', 'mutations', 'copying_vs_convergence', 'phases', 'summary')})
            stats['analyzed'] += 1
        store.finish_task(con, tid)
        con.commit()
    return dict(stats)


# ------------------------------------------------------------ L5
def l4_of(con, key):
    r = con.execute("SELECT body FROM analyses WHERE analysis_id=?", (f'l4:{key}',)).fetchone()
    return json.loads(r['body']) if r else {}


def run_l5(con, llm, run_id):
    cks = clusters(con)
    if len(cks) < 2:
        return {'clusters': len(cks), 'edges': 0}
    view = []
    for ck in cks:
        a = l4_of(con, ck['claim_key'])
        mem = members(con, ck['claim_key'])
        reps = [m for m in mem if not m['copy_of']][:4]
        view.append(dict(cluster=ck['claim_key'], layer=ck['layer'], item=ck['canonical_text'], n_segments=len(mem),
                         t_first=mem[0]['t'] if mem else None, t_last=mem[-1]['t'] if mem else None,
                         origin=(a.get('origin_assessment') or {}).get('kind'), account=a.get('summary'),
                         sample=[dict(msg_id=m['msg_id'], segment_id=m['segment_id'], editor=m['speaker'],
                                      raw=C.WITHHELD if m['purpose'] == store.AW else store.msg_text(con, m['msg_id'])[m['char_start']:m['char_end']][:220])
                                 for m in reps]))
    tid = store.new_task(con, run_id, 'analyzer', {'id': 'l5'}, C.TIER_MODEL['analyzer'])
    res = llm.call_many('analyzer', [dict(custom_id='l5', task_id=tid, system=L5_SYSTEM, user='CLUSTERS:\n' + dumps(view),
                                          schema=L5_SCHEMA, max_tokens=24000, est_out=60 * len(view), mock=lambda: {'edges': []})])[0]
    stats = collections.Counter(clusters=len(cks))
    if res['error']:
        store.finish_task(con, tid, 'failed'); return dict(stats, error=res['error'])
    for n, e in enumerate(res['data'].get('edges', [])):
        st, why = store.add_cluster_edge(con, tid, f'{tid}/e{n}', e['from_cluster'], e['to_cluster'], e['type'], e['confidence'],
                                         e['rationale'], [(e['from_msg_id'], e['from_quote']), (e['to_msg_id'], e['to_quote'])])
        stats['edges' if st == 'ok' else 'edges_rejected'] += 1
    store.finish_task(con, tid)
    con.commit()
    return dict(stats)


# ------------------------------------------------------------ checker
def run_checker(con, llm, run_id, max_rows=60):
    rows = []
    for l in con.execute('''SELECT l.* FROM live_links l JOIN tasks t USING (task_id) WHERE t.tier='analyzer'
                            AND l.link_id NOT LIKE '%/copy/%' AND l.type != 'independent_of' ''').fetchall():
        q = con.execute("SELECT quote FROM citations WHERE obj_type='link' AND obj_id=?", (l['link_id'],)).fetchone()
        rows.append(dict(row_id=l['link_id'], kind='link', claim=f'{l["from_msg_id"]} {l["type"]} {l["to_msg_id"]} via {l["via"]}',
                         rationale=l['rationale'], item=l['claim_key'], evidence_quote=C.WITHHELD if not q else q['quote'],
                         from_raw=raw(con, l['from_msg_id'], 500), to_raw=raw(con, l['to_msg_id'], 500)))
    for e in con.execute('SELECT * FROM cluster_edges WHERE retracted_by IS NULL'):
        cites = con.execute("SELECT msg_id, quote FROM citations WHERE obj_type='cluster_edge' AND obj_id=?", (e['edge_id'],)).fetchall()
        rows.append(dict(row_id=e['edge_id'], kind='cluster_edge', claim=f'{e["from_key"]} {e["type"]} {e["to_key"]}', rationale=e['rationale'],
                         cited=[dict(msg_id=c['msg_id'], raw=raw(con, c['msg_id'], 400)) for c in cites]))
    random.Random(1).shuffle(rows)
    rows = rows[:max_rows]
    jobs, meta = [], {}
    for k, part in enumerate(chunks(rows, 10)):
        tid = store.new_task(con, run_id, 'checker', {'id': f'chk{k}', 'n': len(part)}, C.TIER_MODEL['checker'])
        jobs.append(dict(custom_id=f'chk{k}', task_id=tid, system=CHECK_SYSTEM, user='ROWS:\n' + dumps(part), schema=CHECK_SCHEMA,
                         max_tokens=8000, est_out=60 * len(part),
                         mock=lambda part=part: {'verdicts': [dict(row_id=r['row_id'], verdict='accept', note='mock') for r in part]}))
        meta[f'chk{k}'] = (tid, {r['row_id']: r['kind'] for r in part})
    con.commit()
    stats = collections.Counter(rows=len(rows), calls=len(jobs))
    for res in llm.call_many('checker', jobs):
        tid, kinds = meta[res['custom_id']]
        if res['error']:
            store.finish_task(con, tid, 'failed'); continue
        for v in res['data'].get('verdicts', []):
            if v['row_id'] not in kinds:
                continue
            store.add_check(con, kinds[v['row_id']], v['row_id'], 'same_model', tid, v['verdict'], v['note'])
            stats[v['verdict']] += 1
            if v['verdict'] == 'reject':
                if kinds[v['row_id']] == 'link':
                    store.retract(con, 'links', 'link_id', v['row_id'], tid)
                else:
                    store.retract(con, 'cluster_edges', 'edge_id', v['row_id'], tid)
        store.finish_task(con, tid)
    con.commit()
    return dict(stats)


# ------------------------------------------------------------ script analyzers
def script_analyzers(con, run_id):
    tid = store.new_task(con, run_id, 'analyzer', {'id': 'script'}, 'script')
    ids = identity.group_of(con)
    # 5 routes
    routes = collections.Counter((l['type'], l['via']) for l in con.execute(
        "SELECT type, via FROM live_links WHERE type IN ('source_of','exposed_to','acted_on')"))
    store.add_analysis(con, tid, 'routes', 'routes', 'all', [dict(type=t, via=v, n=n) for (t, v), n in routes.most_common()])
    # 6 spreaders and adopters at three levels
    ev = con.execute('SELECT * FROM events').fetchall()
    lvl = {}
    for name, f in (('name_session', lambda m: ids.get(m, (None,))[0]), ('run_group', lambda m: ids.get(m, (None, None))[1]),
                    ('cohort', lambda m: ids.get(m, (None, None, None))[2])):
        c = collections.defaultdict(lambda: collections.Counter())
        for e in ev:
            k = f(e['msg_id'])
            if k:
                c[k][e['role']] += 1
        lvl[name] = sorted(([k, dict(v)] for k, v in c.items()), key=lambda x: -sum(x[1].values()))[:25]
    store.add_analysis(con, tid, 'spreaders', 'spreaders', 'all', lvl)
    # 7 stopping points
    stops = {}
    for ck in clusters(con):
        rs = [e for e in ev if e['item_id'] == ck['claim_key']]
        if not rs:
            continue
        last = max(rs, key=lambda e: e['t'])
        corr = [e for e in rs if e['role'] == 'correct']
        after = [e for e in rs if corr and e['t'] > min(c['t'] for c in corr) and e['role'] == 'adopt']
        stops[ck['claim_key']] = dict(end='corrected' if corr else ('challenged' if any(e['role'] == 'challenge' for e in rs) else 'alive_at_slice_end'),
                                      last_t=last['t'], adoption_after_correction=len(after))
    store.add_analysis(con, tid, 'stopping_points', 'stopping_points', 'all', stops)
    # 3 baseline: could members have seen the item from an earlier member, more often than chance?
    # Statistic: members with an earlier member by another editor on the same page or in a shared conversation.
    # Null: replace each member with a random core save from the same slice segment (same stretch of time),
    # keeping the cluster size; p = share of null draws at least as connected as the real cluster.
    conv_of = collections.defaultdict(set)
    for r in con.execute('SELECT conv_id, msg_id FROM conversation_members WHERE retracted_by IS NULL'):
        conv_of[r['msg_id']].add(r['conv_id'])
    pool = collections.defaultdict(list)
    msg_seg = {}
    for r in con.execute('SELECT msg_id, t, channel, speaker, segment FROM messages WHERE in_core=1 AND copy_of IS NULL'):
        pool[r['segment']].append(r)
        msg_seg[r['msg_id']] = r['segment']

    def exposed(saves):
        saves = sorted(saves, key=lambda m: m['t'])
        n = 0
        for i, b in enumerate(saves):
            if any(a['t'] < b['t'] and a['speaker'] != b['speaker'] and
                   (a['channel'] == b['channel'] or conv_of[a['msg_id']] & conv_of[b['msg_id']]) for a in saves[:i]):
                n += 1
        return n
    rnd = random.Random(3)
    base = {}
    for ck in clusters(con):
        mem = list({m['msg_id']: m for m in members(con, ck['claim_key']) if not m['copy_of']}.values())
        if len(mem) < 3:
            continue
        obs = exposed(mem)
        null = []
        for _ in range(200):
            draw = [rnd.choice(pool[msg_seg[m['msg_id']]]) for m in mem if pool.get(msg_seg.get(m['msg_id']))]
            null.append(exposed(draw))
        mean = sum(null) / len(null)
        base[ck['claim_key']] = dict(n=len(mem), observed_exposed=obs, null_mean=round(mean, 2),
                                     p_at_least=round(sum(x >= obs for x in null) / len(null), 3),
                                     reading='more connected than chance' if sum(x >= obs for x in null) / len(null) < 0.05
                                     else 'not distinguishable from chance')
    store.add_analysis(con, tid, 'copying_baseline', 'copying_baseline', 'all', base)
    store.finish_task(con, tid)
    con.commit()
    return dict(routes=sum(routes.values()), clusters_with_stops=len(stops), baseline_clusters=len(base))


# ------------------------------------------------------------ lead
def run_lead(con, llm, run_id):
    cks = clusters(con)
    view = dict(
        clusters=[dict(cluster=ck['claim_key'], layer=ck['layer'], item=ck['canonical_text'], n_segments=ck['n_mentions'],
                       t_first=ck['t_first'], **{k: v for k, v in l4_of(con, ck['claim_key']).items()
                                                  if k in ('origin_assessment', 'copying_vs_convergence', 'summary', 'mutations')})
                  for ck in cks],
        cluster_edges=[dict(e) for e in con.execute('SELECT edge_id, from_key, to_key, type, confidence, rationale FROM cluster_edges WHERE retracted_by IS NULL')],
        analyses={r['analysis_id']: json.loads(r['body']) for r in con.execute(
            "SELECT * FROM analyses WHERE analysis_id IN ('routes','spreaders','stopping_points','copying_baseline')")},
        conversations=dict(n=con.execute('SELECT COUNT(*) FROM conversations').fetchone()[0],
                           largest=[dict(r) for r in con.execute('''SELECT c.conv_id, c.topic, COUNT(*) AS n FROM conversations c
                               JOIN conversation_members m USING (conv_id) GROUP BY c.conv_id ORDER BY n DESC LIMIT 8''')]),
        run_groups=[dict(r) for r in con.execute('''SELECT group_id, COUNT(*) AS sessions FROM run_group_members GROUP BY group_id
                                                    ORDER BY sessions DESC LIMIT 10''')],
        coverage=dict(core=con.execute("SELECT COUNT(*) FROM messages WHERE in_core=1 AND COALESCE(script_label,'')!='EMPTY'").fetchone()[0],
                      with_records=con.execute('SELECT COUNT(DISTINCT msg_id) FROM records').fetchone()[0],
                      gaps=[dict(r) for r in con.execute('SELECT reason, COUNT(*) AS n FROM coverage_gaps GROUP BY reason')]),
        checker=[dict(r) for r in con.execute("SELECT verdict, COUNT(*) AS n FROM checks WHERE checker='same_model' GROUP BY verdict")],
        anomalies=[dict(msg_id=r['msg_id'], anomaly=r['anomaly']) for r in store.live_records(con) if r['anomaly'] and not r['cloned_from']][:40],
    )
    tid = store.new_task(con, run_id, 'lead', {'id': 'lead'}, C.TIER_MODEL['lead'])

    def mock():
        return {'findings': [dict(text=f'mock finding: cluster {ck["claim_key"]} spread', confidence='low', category='spread routes',
                                  supports=[dict(type='claim_key', id=ck['claim_key'])]) for ck in cks[:5]], 'observations': []}
    res = llm.call_many('lead', [dict(custom_id='lead', task_id=tid, system=LEAD_SYSTEM, user='STORE AGGREGATES:\n' + dumps(view),
                                      schema=LEAD_SCHEMA, max_tokens=24000, est_out=4000, mock=mock)])[0]
    stats = collections.Counter()
    if res['error']:
        store.finish_task(con, tid, 'failed'); return dict(error=res['error'])
    for n, f in enumerate(res['data'].get('findings', [])):
        st, _ = store.add_finding(con, tid, f'F{n+1:02d}', f['text'], f['confidence'], f['supports'], f.get('category'))
        stats['findings' if st == 'ok' else 'findings_rejected'] += 1
    for n, o in enumerate(res['data'].get('observations', [])):
        st, _ = store.add_observation(con, tid, f'O{n+1:02d}', o['text'], [(c['msg_id'], c['quote']) for c in o['cites']])
        stats['observations' if st == 'ok' else 'observations_rejected'] += 1
    store.finish_task(con, tid)
    con.commit()
    return dict(stats)
