"""Conversation layer (DESIGN.md 4.5, store_design 2a): cluster.py script pass + clusterer (Opus 5.5).

Script: connects core messages by reply hints / reply_to links, saves on the same page within 30 minutes, and a save
that names a page saved in the previous 60 minutes. Connected groups = candidate conversations.
Clusterer: reads candidates with 3+ members (and oversized ones), writes topic lines, splits mixed candidates, and
records split / merge / drift / resume edges anchored on a message with a checked quote. Presence is exposure
evidence, not proof.
"""
import collections, json, re
import config as C, store, load
from common import obj, arr, S, CONF, NULLSTR, SAFETY, raw, chunks, dumps

STAGE = 'clusterer'
PAGE_GAP_S, REF_GAP_S = 1800, 3600

SYSTEM = f"""You are the conversation clusterer in an investigation of an AI agent swarm (OpenAI research agents using German wikis as a shared scratchpad and relay, 2026). {SAFETY}

A conversation is a set of saves that are talking with each other: replies, a relay page several agents write to, a save that names another page and continues it. A script grouped saves into candidate conversations by reply hints, same-page saves within 30 minutes and page references. For each candidate:
- write a one-line topic in your own words;
- if it mixes unrelated threads, split it: list the member msg_ids of each part (every member in exactly one part, or drop a member that belongs to none);
- confidence high/medium/low.
Then list edges between conversations where the raw text shows them: merge (two conversations join; anchor = the bridging save), split (one becomes two), drift (same people, new topic), resume (an old conversation picked up again). Each edge cites an anchor msg_id and an exact quote (at most 200 characters) from it. Membership is evidence that an agent was present, not that it read anything."""

SCHEMA = obj({
    'conversations': arr(obj({'candidate_id': S, 'parts': arr(obj({'topic': S, 'members': arr(S), 'confidence': CONF,
                                                                   'rationale': S}))})),
    'edges': arr(obj({'type': {'type': 'string', 'enum': ['split', 'merge', 'drift', 'resume']},
                      'from_candidate': S, 'from_part': {'type': 'integer'}, 'to_candidate': S, 'to_part': {'type': 'integer'},
                      'at_msg_id': S, 'quote': S, 'confidence': CONF, 'rationale': S}))})


def script_pass(con):
    msgs = con.execute("SELECT * FROM messages WHERE in_core=1 AND COALESCE(script_label,'')!='EMPTY' ORDER BY t").fetchall()
    ids = [m['msg_id'] for m in msgs]
    parent = {i: i for i in ids}
    basis = collections.defaultdict(set)

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x

    def union(a, b, why):
        if a in parent and b in parent:
            parent[find(a)] = find(b); basis[a].add(why); basis[b].add(why)
    hints = {r['msg_id']: r['reply_to_hint'] for r in store.live_records(con)}
    for mid, h in hints.items():
        if h and h in parent:
            union(mid, h, 'reply_to')
    for l in con.execute("SELECT from_msg_id, to_msg_id FROM links WHERE type='reply_to' AND retracted_by IS NULL"):
        union(l['from_msg_id'], l['to_msg_id'], 'reply_to')
    last = {}
    titles = {}
    for m in msgs:
        t = load.ts(m['t'])
        if m['channel'] in last and t - last[m['channel']][1] <= PAGE_GAP_S:
            union(m['msg_id'], last[m['channel']][0], 'same_page_chain')
        last[m['channel']] = (m['msg_id'], t)
        title = m['channel'].split('~', 1)[1]
        body = m['text'][m['text'].find('\n') + 1:]
        for other, (oid, ot) in list(titles.items()):
            if other != title and len(other) >= 8 and other in body and t - ot <= REF_GAP_S:
                union(m['msg_id'], oid, 'page_reference')
        titles[title] = (m['msg_id'], t)
    groups = collections.defaultdict(list)
    for i in ids:
        groups[find(i)].append(i)
    return [(g, {i: (sorted(basis[i]) or ['time_gap'])[0] for i in g}) for g in groups.values() if len(g) >= 2]


def mock_conv(cands):
    return {'conversations': [dict(candidate_id=cid, parts=[dict(topic='mock topic: ' + topic, members=members, confidence='low',
                                                                 rationale='mock: script candidate kept as is')])
                              for cid, members, topic in cands], 'edges': []}


def run(con, llm, run_id):
    groups = script_pass(con)
    script_tid = store.new_task(con, run_id, 'clusterer', {'id': 'script'}, 'script')
    big = [(g, b) for g, b in groups if len(g) >= 3]
    small = [(g, b) for g, b in groups if len(g) < 3]
    # pairs are written straight from the script pass
    for k, (g, b) in enumerate(small):
        cid = f'conv-s{k}'
        ts = [con.execute('SELECT t, channel FROM messages WHERE msg_id=?', (i,)).fetchone() for i in g]
        con.execute('INSERT INTO conversations VALUES (?,?,?,?,?,?,?,?)', (cid, script_tid, '(script pair, no topic)',
                    json.dumps(sorted({x['channel'] for x in ts})), min(x['t'] for x in ts), max(x['t'] for x in ts),
                    'script pass: ' + ','.join(sorted(set(b.values()))), None))
        for i in g:
            con.execute('INSERT INTO conversation_members VALUES (?,?,?,?,?,?)', (cid, i, script_tid, b[i], 'medium', None))
    jobs, meta = [], {}
    cands = []
    for k, (g, b) in enumerate(big):
        cid = f'cand{k}'
        rows = [con.execute('SELECT msg_id, t, channel, speaker FROM messages WHERE msg_id=?', (i,)).fetchone() for i in sorted(g)]
        rows.sort(key=lambda r: r['t'])
        summ = {r['msg_id']: r['summary'] for r in store.live_records(con) if r['msg_id'] in b}
        cands.append(dict(candidate_id=cid, members=[dict(msg_id=r['msg_id'], t=r['t'], page=r['channel'], editor=r['speaker'],
                                                          linked_by=b[r['msg_id']], reader_summary=summ.get(r['msg_id']),
                                                          raw=raw(con, r['msg_id'], 160 if len(g) > 40 else 300)) for r in rows]))
    bins, cur, size = [], [], 0
    for c in sorted(cands, key=lambda c: -len(c['members'])):
        n = len(dumps(c))
        if cur and size + n > 120_000:
            bins.append(cur); cur, size = [], 0
        cur.append(c); size += n
    if cur:
        bins.append(cur)
    for k, part in enumerate(bins):
        tid = store.new_task(con, run_id, STAGE, {'id': f'conv{k}', 'n': len(part)}, C.TIER_MODEL[STAGE])
        mk = [(c['candidate_id'], [m['msg_id'] for m in c['members']], c['members'][0]['page']) for c in part]
        jobs.append(dict(custom_id=f'conv{k}', task_id=tid, system=SYSTEM, user='CANDIDATES:\n' + dumps(part), schema=SCHEMA,
                         max_tokens=32000, est_out=60 * sum(len(c['members']) for c in part),
                         mock=lambda mk=mk: mock_conv(mk)))
        meta[f'conv{k}'] = (tid, {c['candidate_id']: c for c in part})
    con.commit()
    stats = collections.Counter(script_groups=len(groups), pairs=len(small), candidates=len(big), calls=len(jobs))
    for res in llm.call_many(STAGE, jobs):
        tid, byc = meta[res['custom_id']]
        if res['error']:
            stats['failed_calls'] += 1
            for c in byc.values():          # keep the script grouping
                _write_conv(con, script_tid, c['candidate_id'] + '_0', '(clusterer failed; script grouping)',
                            [m['msg_id'] for m in c['members']], 'low', 'script pass only', {m['msg_id']: m['linked_by'] for m in c['members']})
            continue
        part_ids = {}
        for cv in res['data'].get('conversations', []):
            c = byc.get(cv['candidate_id'])
            if not c:
                continue
            allowed = {m['msg_id']: m['linked_by'] for m in c['members']}
            for j, p in enumerate(cv['parts']):
                mem = [x for x in p['members'] if x in allowed]
                if not mem:
                    continue
                conv_id = f'{c["candidate_id"]}_{j}'
                _write_conv(con, tid, conv_id, p['topic'], mem, p['confidence'], p['rationale'],
                            {x: (allowed[x] if len(cv['parts']) == 1 else 'agent_judgment') for x in mem})
                part_ids[(cv['candidate_id'], j)] = conv_id
                stats['conversations'] += 1
                stats['split_parts'] += len(cv['parts']) > 1
        for n, e in enumerate(res['data'].get('edges', [])):
            a, b = part_ids.get((e['from_candidate'], e['from_part'])), part_ids.get((e['to_candidate'], e['to_part']))
            if not a or not b or not store.citation_ok(con, e['at_msg_id'], e['quote']):
                stats['edges_rejected'] += 1; continue
            eid = f'{tid}/e{n}'
            con.execute('INSERT INTO conversation_edges VALUES (?,?,?,?,?,?,?,?,?)', (eid, tid, e['type'], a, b, e['at_msg_id'],
                                                                                    e['confidence'], e['rationale'], None))
            store.add_citation(con, 'conv_edge', eid, e['at_msg_id'], e['quote'])
            stats['edges'] += 1
        store.finish_task(con, tid)
    con.commit()
    return dict(stats)


def _write_conv(con, tid, conv_id, topic, members, conf, rationale, basis):
    rows = [con.execute('SELECT t, channel FROM messages WHERE msg_id=?', (i,)).fetchone() for i in members]
    con.execute('INSERT OR REPLACE INTO conversations VALUES (?,?,?,?,?,?,?,?)', (conv_id, tid, topic[:300],
                json.dumps(sorted({r['channel'] for r in rows})), min(r['t'] for r in rows), max(r['t'] for r in rows), rationale[:500], None))
    for i in members:
        con.execute('INSERT OR IGNORE INTO conversation_members VALUES (?,?,?,?,?,?)',
                    (conv_id, i, tid, basis.get(i, 'agent_judgment'), conf if conf in store.CONF else 'low', None))
