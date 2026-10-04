"""Run identity (DESIGN.md 5.5, identity_findings.md): identity_candidates (script) + run-identity linker (Opus 5.5).

Unit = name-session (one name's saves split at gaps over 6 h; anonymous saves are singletons).
Strong edges (template mint, timestamp mint, signature) are accepted by the script; medium edges (distinctive edit
summary within 48 h, same date tag + topic word within 48 h) go to the linker. Merges are blocked by two different
date tags or saves under 5 s apart on different pages. Run groups = connected components of accepted edges.
"""
import collections, gzip, json, os, re
import config as C, store, load
from common import obj, arr, S, CONF, SAFETY, raw, chunks, dumps

STAGE = 'identity'
MON = 'jan feb mar apr may jun jul aug sep oct nov dec'.split()
TAG = re.compile(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*(\d{1,2})(?!\d)')
GENERIC = set('agent research researcher helper open ai oai openai x xyz zz z data test user bot reader scout watcher new a b '
              'final mass guest my the public notes note'.split()) | set(MON)


def datetag(s):
    m = TAG.search(s or '')
    return m.group(1) + '%02d' % int(m.group(2)) if m else None


def words(s):
    s = re.sub(r'(\d+)', r' \1 ', s or ''); s = re.sub(r'([a-z])([A-Z])', r'\1 \2', s)
    return [t.lower() for t in re.split(r'[\s_\-.]+', s) if t]


def template(s):
    return re.sub(r'\d+$', '', s or '')


def topic_words(s):
    return {w for w in words(s) if not w.isdigit() and w not in GENERIC and len(w) > 2}


def sessions(con):
    rows = con.execute('SELECT msg_id, t, channel, speaker FROM messages ORDER BY t').fetchall()
    by = collections.defaultdict(list)
    for r in rows:
        by[r['speaker'] or ('anon:' + r['msg_id'])].append(r)
    out = {}
    for lab, rs in by.items():
        cur = []
        for r in rs:
            if cur and load.ts(r['t']) - load.ts(cur[-1]['t']) > 6 * 3600:
                out[f'{lab}@{cur[0]["t"]}'] = (lab, cur); cur = []
            cur.append(r)
        out[f'{lab}@{cur[0]["t"]}'] = (lab, cur)
    return out


def candidate_edges(con, sess):
    summaries = {}
    for f in (os.path.join(C.RUN_DIR, 'input', 'revisions_planted.jsonl.gz'), os.path.join(C.SLICE, 'halo_revisions.jsonl.gz')):
        for l in gzip.open(f):
            x = json.loads(l)
            summaries['dw:' + x['rev_id']] = x.get('change_summary')
    sum_labels = collections.defaultdict(set)
    for sid, (lab, rs) in sess.items():
        for r in rs:
            if summaries.get(r['msg_id']):
                sum_labels[summaries[r['msg_id']]].add(lab)
    signed = {r['msg_id']: r['signed_name'] for r in store.live_records(con) if r['signed_name']}
    items = list(sess.items())
    t0 = {sid: load.ts(rs[0]['t']) for sid, (lab, rs) in items}
    t1 = {sid: load.ts(rs[-1]['t']) for sid, (lab, rs) in items}
    near = lambda a, b, h: abs(t0[a] - t0[b]) <= h * 3600 or abs(t1[a] - t0[b]) <= h * 3600 or abs(t0[a] - t1[b]) <= h * 3600
    by_label = collections.defaultdict(list)
    for sid, (lab, rs) in items:
        by_label[lab].append(sid)
    edges = []
    named = [(sid, lab) for sid, (lab, rs) in items if not lab.startswith('anon:')]
    for i, (a, la) in enumerate(named):
        for b, lb in named[i + 1:]:
            if la == lb:
                continue
            ta, tb = template(la), template(lb)
            if ta == tb and ta != la and len(ta) >= 6 and topic_words(ta) and near(a, b, 6):
                edges.append((a, b, 'template_mint', 'strong', {'template': ta}))
                continue
            sa, sb = re.sub(r'1[6-9]\d{8}', '#', la), re.sub(r'1[6-9]\d{8}', '#', lb)
            if '#' in sa and sa == sb and near(a, b, 1):
                edges.append((a, b, 'timestamp_mint', 'strong', {'pattern': sa}))
                continue
            da, db = datetag(la), datetag(lb)
            if da and da == db and topic_words(la) & topic_words(lb) and near(a, b, 48):
                edges.append((a, b, 'tag_topic', 'medium', {'tag': da, 'shared': sorted(topic_words(la) & topic_words(lb))}))
                continue
            sa_ = {summaries.get(r['msg_id']) for r in sess[a][1]} - {None}
            sb_ = {summaries.get(r['msg_id']) for r in sess[b][1]} - {None}
            shared = [s for s in sa_ & sb_ if len(sum_labels[s]) <= 5 and len(s) > 3 and s.strip('*') and near(a, b, 48)]
            if shared:
                edges.append((a, b, 'edit_summary', 'medium', {'summary_shared': True, 'n_labels_using': len(sum_labels[shared[0]])}))
    for sid, (lab, rs) in items:
        for r in rs:
            sn = signed.get(r['msg_id'])
            if sn and sn != lab and sn in by_label:
                for other in by_label[sn]:
                    if other != sid:
                        edges.append((sid, other, 'signature', 'strong', {'msg_id': r['msg_id']}))
    return edges


def blocked(sess, a, b):
    da, db = datetag(sess[a][0]), datetag(sess[b][0])
    if da and db and da != db:
        return 'different date tags'
    for x in sess[a][1]:
        for y in sess[b][1]:
            if x['channel'] != y['channel'] and abs(load.ts(x['t']) - load.ts(y['t'])) < 5:
                return 'parallel saves under 5 s apart on different pages'
    return None


SYSTEM = f"""You are the run-identity linker in an investigation of an AI agent swarm on German wikis (2026). {SAFETY}
Editor names are self-chosen and reused; one run can use many names and many runs can share one. For each proposed pair of name-sessions, read both sides' raw added text and decide whether they are the same run: same task, same phrasing habits, references to its own earlier notes, and no contradictions (different cohort tags, conflicting claims about itself). Shared vocabulary in names is weak evidence; agents draw names from one common pool. Accept only when the text supports it; reject otherwise; low confidence is fine."""
SCHEMA = obj({'decisions': arr(obj({'edge_id': {'type': 'integer'}, 'decision': {'type': 'string', 'enum': ['accept', 'reject']},
                                    'confidence': CONF, 'rationale': S}))})


def side(con, sess, sid):
    lab, rs = sess[sid]
    return dict(session=sid, name=lab if not lab.startswith('anon:') else '(anonymous)', n_saves=len(rs),
                saves=[dict(msg_id=r['msg_id'], t=r['t'], page=r['channel'], raw=raw(con, r['msg_id'], 300)) for r in rs[:3]])


def run(con, llm, run_id):
    sess = sessions(con)
    edges = candidate_edges(con, sess)
    stats = collections.Counter(sessions=len(sess), named_sessions=sum(not k.startswith('anon:') for k in sess))
    medium = []
    for a, b, et, strength, ev in edges:
        why = blocked(sess, a, b)
        status = 'rejected' if why else ('accepted' if strength == 'strong' else 'proposed')
        if why:
            ev = dict(ev, blocked=why)
        cur = con.execute('INSERT INTO identity_edges (session_a, session_b, edge_type, strength, evidence, status, decided_by) '
                          'VALUES (?,?,?,?,?,?,?)', (a, b, et, strength, json.dumps(ev), status, 'script' if status != 'proposed' else None))
        stats[f'{et}:{status}'] += 1
        if status == 'proposed':
            medium.append((cur.lastrowid, a, b, et, ev))
    jobs, meta = [], {}
    for k, part in enumerate(chunks(medium, 25)):
        tid = store.new_task(con, run_id, STAGE, {'id': f'id{k}', 'n': len(part)}, C.TIER_MODEL[STAGE])
        payload = [dict(edge_id=eid, edge_type=et, evidence=ev, a=side(con, sess, a), b=side(con, sess, b)) for eid, a, b, et, ev in part]
        jobs.append(dict(custom_id=f'id{k}', task_id=tid, system=SYSTEM, user='PAIRS:\n' + dumps(payload), schema=SCHEMA,
                         max_tokens=16000, est_out=80 * len(part),
                         mock=lambda part=part: {'decisions': [dict(edge_id=e[0], decision='reject', confidence='low',
                                                                    rationale='mock: no text evidence checked') for e in part]}))
        meta[f'id{k}'] = (tid, {e[0] for e in part})
    con.commit()
    for res in llm.call_many(STAGE, jobs):
        tid, ok_ids = meta[res['custom_id']]
        if res['error']:
            store.finish_task(con, tid, 'failed'); continue
        for d in res['data'].get('decisions', []):
            if d['edge_id'] in ok_ids:
                st = 'accepted' if d['decision'] == 'accept' else 'rejected'
                con.execute('UPDATE identity_edges SET status=?, decided_by=?, version=version+1, evidence=json_set(evidence, "$.linker", ?) '
                            'WHERE edge_id=?', (st, tid, f'{d["confidence"]}: {d["rationale"][:300]}', d['edge_id']))
                stats['linker_' + st] += 1
        store.finish_task(con, tid)
    # run groups = components of accepted edges
    parent = {s: s for s in sess}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for e in con.execute("SELECT session_a, session_b FROM identity_edges WHERE status='accepted'"):
        parent[find(e['session_a'])] = find(e['session_b'])
    comps = collections.defaultdict(list)
    for s in sess:
        comps[find(s)].append(s)
    gtid = store.new_task(con, run_id, STAGE, {'id': 'groups'}, 'script')
    n = 0
    for root, members in comps.items():
        if len(members) < 2:
            continue
        n += 1
        gid = f'rg{n:03d}'
        con.execute('INSERT INTO run_groups VALUES (?,?,?,?,?)', (gid, gtid, 'dsewiki', 'components of accepted identity edges', None))
        for m in members:
            con.execute('INSERT INTO run_group_members VALUES (?,?,?,?,?,?)', (gid, m, 'session', gtid, 'medium', None))
    stats['run_groups'] = n
    stats['sessions_in_groups'] = sum(len(m) for m in comps.values() if len(m) >= 2)
    con.commit()
    return dict(stats)


def group_of(con):
    """msg_id -> (session_id, run_group or None, cohort tag)"""
    sess = sessions(con)
    g = {r['member']: r['group_id'] for r in con.execute("SELECT * FROM run_group_members WHERE member_kind='session' AND retracted_by IS NULL")}
    out = {}
    for sid, (lab, rs) in sess.items():
        for r in rs:
            out[r['msg_id']] = (sid, g.get(sid), datetag(lab) or datetag(r['channel']))
    return out
