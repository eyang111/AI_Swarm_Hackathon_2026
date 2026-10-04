"""Reader windows, DESIGN.md 5.2 scheme D (build step 2). Script only.

core  = up to 100 saves to read and at most 60k characters, cut within one slice segment
halo  = previous 50 distinct saves + for each distinctive token in the core the 2 most recent earlier saves using it
        within 24 h; capped at 150 saves (and HALO_MAX_CHARS); raw text, marked context-only
context pack = pointers (msg_id, time, page, token) to earlier saves using a core token that are not in view
"""
import json, re, collections
import config as C, store

TOK = re.compile(r'\b(?:[A-Z][a-z0-9]+(?:[A-Z][a-z0-9]*)+|[A-Za-z]+\d+[A-Za-z0-9]*|\d+[A-Za-z]+[A-Za-z0-9]*|[A-Za-z0-9]+(?:-[A-Za-z0-9]+){2,})\b')


def tokens(text):
    return set(TOK.findall(text))


def to_read(con):
    return con.execute('''SELECT * FROM messages m WHERE in_core=1 AND COALESCE(script_label,'')!='EMPTY' AND
        (copy_of IS NULL OR NOT EXISTS (SELECT 1 FROM messages f WHERE f.msg_id=m.copy_of AND f.in_core=1))
        ORDER BY t, msg_id''').fetchall()


def main():
    con = store.connect()
    con.execute('DELETE FROM windows')
    allm = con.execute('SELECT msg_id, t, text, copy_of, channel FROM messages ORDER BY t, msg_id').fetchall()
    distinct = [m for m in allm if m['copy_of'] is None]
    pos = {m['msg_id']: i for i, m in enumerate(distinct)}
    toks = {m['msg_id']: tokens(m['text']) for m in allm}
    df = collections.Counter(t for m in distinct for t in toks[m['msg_id']])
    by_tok = collections.defaultdict(list)
    for i, m in enumerate(distinct):
        for t in toks[m['msg_id']]:
            if C.DF_MIN <= df[t] <= C.DF_CAP:
                by_tok[t].append(i)
    ts = lambda s: store.dt.datetime.fromisoformat(s.replace('Z', '+00:00')).timestamp()
    reads = to_read(con)
    windows = []
    t_of = {m['msg_id']: m['t'] for m in allm}
    text_of = {m['msg_id']: m['text'] for m in allm}
    import bisect
    dist_t = [m['t'] for m in distinct]
    for seg in sorted({r['segment'] for r in reads}):
        cur, chars, cores = [], 0, []
        for m in [r for r in reads if r['segment'] == seg]:
            n = len(m['text'])
            if cur and (len(cur) >= C.CORE_MAX_SAVES or chars + n > C.CORE_MAX_CHARS):
                cores.append(cur); cur, chars = [], 0
            cur.append(m); chars += n
        if cur:
            cores.append(cur)
        for k, core in enumerate(cores, 1):
            cids = {m['msg_id'] for m in core}
            start = core[0]['t']
            halo = [m['msg_id'] for m in distinct[:bisect.bisect_left(dist_t, start)]][-C.HALO_PREV:]
            pack = {}
            for m in core:
                i = pos.get(m['msg_id'], None)
                limit_t = m['t']
                for t in toks[m['msg_id']]:
                    if not (C.DF_MIN <= df[t] <= C.DF_CAP):
                        continue
                    got, older = 0, None
                    for j in reversed(by_tok[t]):
                        h = distinct[j]
                        if h['t'] >= limit_t or h['msg_id'] in cids:
                            continue
                        if got >= C.HALO_PER_TOKEN or ts(m['t']) - ts(h['t']) > C.HALO_MAX_AGE_S:
                            older = h; continue
                        if h['msg_id'] not in halo:
                            halo.append(h['msg_id'])
                        got += 1
                    if older is not None and older['msg_id'] not in halo:
                        pack.setdefault(older['msg_id'], dict(msg_id=older['msg_id'], t=older['t'],
                                                              page=older['channel'], tokens=[]))['tokens'].append(t)
            halo = [h for h in halo if h not in cids][:C.HALO_CAP]
            kept, hc = [], 0
            for h in reversed(halo):                      # keep the nearest ones when over the char cap
                if hc + len(text_of[h]) > C.HALO_MAX_CHARS:
                    continue
                kept.append(h); hc += len(text_of[h])
            halo = sorted(kept, key=lambda h: t_of[h])
            pack = [p for p in pack.values() if p['msg_id'] not in halo][:60]
            wid = f'{seg}_w{k}'
            con.execute('INSERT INTO windows VALUES (?,?,?,?,?,?,?,?,?)',
                        (wid, seg, start, core[-1]['t'], json.dumps([m['msg_id'] for m in core]), json.dumps(halo),
                         json.dumps(pack), sum(len(m['text']) for m in core), hc))
            windows.append((wid, len(core), sum(len(m['text']) for m in core), len(halo), hc, len(pack)))
    con.commit()
    for w in windows:
        print('%-8s core %3d saves %6d chars | halo %3d saves %6d chars | pack %d' % w)
    print('windows', len(windows), 'core saves', sum(w[1] for w in windows))


if __name__ == '__main__':
    main()
