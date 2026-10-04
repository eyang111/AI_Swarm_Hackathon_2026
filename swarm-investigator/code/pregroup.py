"""Script pre-grouping, no AI (reader_format 4, pipeline_v2 4, DESIGN 5.4).

keyword_df(): document frequency of reader keywords over distinct messages; distinctive = DF_MIN..DF_CAP.
              Runs before the local linker (the one place a script overrides a reader label).
candidates(): copy groups, same claim text, shared distinctive keywords, signed names, run tags.
families():   connected components over live links + candidate edges, split at ~300 segments, for the groupers.
"""
import collections, json
import config as C, store


def keyword_df(con):
    con.execute('DELETE FROM keyword_df')
    rows = con.execute('''SELECT sk.keyword, s.msg_id FROM segment_keywords sk JOIN segments s USING (segment_id)
        JOIN records r ON r.record_id = s.record_id WHERE r.cloned_from IS NULL''').fetchall()
    df = collections.Counter()
    per = collections.defaultdict(set)
    for r in rows:
        per[r['keyword']].add(r['msg_id'])
    for kw, ms in per.items():
        df[kw] = len(ms)
    for kw, n in df.items():
        con.execute('INSERT INTO keyword_df VALUES (?,?,?)', (kw, n, int(C.DF_MIN <= n <= C.DF_CAP)))
    con.commit()
    return dict(keywords=len(df), distinctive=sum(C.DF_MIN <= n <= C.DF_CAP for n in df.values()))


def distinctive_kws(con, segment_id):
    return {r['keyword'] for r in con.execute('''SELECT sk.keyword FROM segment_keywords sk JOIN keyword_df d USING (keyword)
        WHERE sk.segment_id=? AND d.distinctive=1''', (segment_id,))}


def candidates(con, run_id):
    con.execute('DELETE FROM candidate_members'); con.execute('DELETE FROM candidates')
    segs = store.live_segments(con)
    n = collections.Counter()

    def add(basis, key, members):
        cid = f'{basis}:{key}'[:200]
        con.execute('INSERT OR IGNORE INTO candidates VALUES (?,?,?,?,?)', (cid, run_id, basis, key[:200], 'open'))
        for msg_id, claim_id in members:
            con.execute('INSERT OR IGNORE INTO candidate_members VALUES (?,?,?)', (cid, msg_id, claim_id))
        n[basis] += 1
    # copy groups: copies on another page or under another name (DESIGN 5.3)
    for g in con.execute('''SELECT copy_of, GROUP_CONCAT(msg_id) AS ms FROM messages m WHERE copy_of IS NOT NULL
        AND COALESCE(script_label,'') != 'DUPLICATE' GROUP BY copy_of''').fetchall():
        add('copy_group', g['copy_of'], [(g['copy_of'], None)] + [(x, None) for x in g['ms'].split(',')])
    by_norm = collections.defaultdict(list)
    for c in con.execute('''SELECT c.claim_id, c.msg_id, c.norm_text FROM claims c JOIN records r USING (record_id)
        WHERE r.cloned_from IS NULL AND r.retracted_by IS NULL'''):
        by_norm[c['norm_text']].append((c['msg_id'], c['claim_id']))
    for k, ms in by_norm.items():
        if len({m for m, _ in ms}) >= 2 and len(k) > 10:
            add('same_claim_text', k, ms)
    by_kw = collections.defaultdict(set)
    for s in segs:
        if s['copy_of']:
            continue
        for kw in distinctive_kws(con, s['segment_id']):
            by_kw[kw].add(s['msg_id'])
    for kw, ms in by_kw.items():
        if len(ms) >= 2:
            add('shared_entity', kw, [(m, None) for m in ms])
    for col, basis in (('signed_name', 'signed_name'), ('run_tag', 'run_tag')):
        g = collections.defaultdict(set)
        for r in store.live_records(con):
            if r[col]:
                g[r[col]].add((r['msg_id'], con.execute('SELECT speaker FROM messages WHERE msg_id=?', (r['msg_id'],)).fetchone()[0]))
        for k, ms in g.items():
            if len({sp for _, sp in ms}) >= 2:
                add(basis, k, [(m, None) for m, _ in ms])
    con.commit()
    return dict(n)


def families(con, max_size=300):
    """components over segments: links, copy groups, same claim text, shared distinctive keywords.
    Copies are folded into their first instance (groupers see one representative per copy group)."""
    segs = [s for s in store.live_segments(con)]
    first_in_core = {r['msg_id']: r['copy_of'] for r in con.execute(
        "SELECT m.msg_id, m.copy_of FROM messages m JOIN messages f ON f.msg_id=m.copy_of WHERE f.in_core=1 AND m.in_core=1")}
    reps = [s for s in segs if s['msg_id'] not in first_in_core]
    ids = [s['segment_id'] for s in reps]
    parent = {i: i for i in ids}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x

    def union(a, b):
        if a in parent and b in parent:
            parent[find(a)] = find(b)
    for l in con.execute('SELECT from_segment, to_segment FROM links WHERE retracted_by IS NULL AND to_segment IS NOT NULL'):
        union(l['from_segment'], l['to_segment'])
    by_kw = collections.defaultdict(list)
    for s in reps:
        for kw in distinctive_kws(con, s['segment_id']):
            by_kw[kw].append(s['segment_id'])
    for kw, ss in by_kw.items():
        for x in ss[1:]:
            union(ss[0], x)
    by_norm = collections.defaultdict(list)
    for c in con.execute('SELECT segment_id, norm_text FROM claims WHERE segment_id IS NOT NULL'):
        if c['segment_id'] in parent and len(c['norm_text']) > 10:
            by_norm[c['norm_text']].append(c['segment_id'])
    for k, ss in by_norm.items():
        for x in ss[1:]:
            union(ss[0], x)
    comps = collections.defaultdict(list)
    for i in ids:
        comps[find(i)].append(i)
    t_of = {s['segment_id']: s['t'] for s in reps}
    out = []
    for c in comps.values():
        c.sort(key=lambda x: (t_of[x], x))
        for k in range(0, len(c), max_size):
            out.append(c[k:k + max_size])
    out.sort(key=lambda c: -len(c))
    return out
