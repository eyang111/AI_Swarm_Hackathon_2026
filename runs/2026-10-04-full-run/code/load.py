"""L0 loader (DESIGN.md 4.1, build step 1): test-slice DSEWiki saves -> messages. No AI, no interpretation.

text = page title line + the lines this save inserted or replaced (from hunks), Unicode NFC.
removed_text = lines this save deleted or replaced. copy_of = earliest loaded save with the same normalized added text.
Core saves come from the planted copy (plant.py); halo saves (context only) from test_slice/halo_revisions.
"""
import gzip, json, os, re, hashlib, unicodedata, datetime as dt
import config as C, store

SEGMENTS = [('S1', '2026-05-26T13:00:00Z', '2026-05-26T15:00:00Z'),
            ('S2', '2026-06-16T18:45:00Z', '2026-06-16T19:20:00Z'),
            ('S3', '2026-06-18T20:09:00Z', '2026-06-18T20:11:00Z')]
EMPTY_DEFAULTS = {'Beschreibe hier die neue Seite.', ''}
URL = re.compile(r'https?://\S+')


def nfc(s):
    return unicodedata.normalize('NFC', s or '')


def norm(s):
    return re.sub(r'\s+', ' ', nfc(s)).strip()


def ts(s):
    return dt.datetime.fromisoformat(s.replace('Z', '+00:00')).timestamp()


def added_removed(r, prev_body):
    lines = nfc(r['body']).split('\n')
    if r.get('diff_base') is None or not r.get('hunks'):
        return '\n'.join(lines) if r.get('diff_base') is None else '', ''
    prev = nfc(prev_body).split('\n') if prev_body is not None else None
    add, rem = [], []
    for h in r['hunks']:
        if h['op'] in ('insert', 'replace'):
            add += lines[h['b0']:h['b1']]
        if h['op'] in ('delete', 'replace') and prev is not None:
            rem += prev[h['a0']:h['a1']]
    return '\n'.join(add), '\n'.join(rem)


def main():
    con = store.init_db()
    core = [json.loads(l) for l in gzip.open(os.path.join(C.RUN_DIR, 'input', 'revisions_planted.jsonl.gz'))]
    halo = []                                    # full dump: the halo is earlier saves already in the store
    for r in core: r['_core'] = 1
    for r in halo: r['_core'] = 0
    rows = sorted(core + halo, key=lambda r: (r['time'], r['rev_id']))
    # previous bodies for removed_text: from the raw dump (diff_base may be outside the slice)
    need = {r['diff_base'] for r in rows if r.get('diff_base')}
    bodies = {r['rev_id']: r['body'] for r in rows}
    for l in gzip.open('/mnt/project-files/dsewiki/raw/revisions.jsonl.gz'):
        x = json.loads(l)
        if x['rev_id'] in need and x['rev_id'] not in bodies:
            bodies[x['rev_id']] = x['body']
    first_by_norm, last_in_channel, speakers = {}, {}, {}
    n = {'core': 0, 'halo': 0, 'copies': 0, 'dup': 0, 'empty': 0, 'missing_prev': 0}
    for r in rows:
        mid = 'dw:' + r['rev_id']
        channel = f"{r['wiki']}~{r['name']}"
        prev_body = bodies.get(r['diff_base']) if r.get('diff_base') else None
        if r.get('diff_base') and prev_body is None:
            n['missing_prev'] += 1
        add, rem = added_removed(r, prev_body)
        text = nfc(r['name']) + '\n' + add
        key = norm(add)
        copy_of = first_by_norm.get(key) if key and key not in EMPTY_DEFAULTS else None
        label = None
        if key in EMPTY_DEFAULTS:
            label = 'EMPTY'
        elif copy_of:
            src = con.execute('SELECT channel, speaker FROM messages WHERE msg_id=?', (copy_of,)).fetchone()
            if src['channel'] == channel and (src['speaker'] or '') == (r['label'] or ''):
                label = 'DUPLICATE'
        if key and key not in first_by_norm:
            first_by_norm[key] = mid
        speaker = r['label'] or None
        kind = 'human' if speaker and speaker.startswith('[') else ('agent' if speaker else 'unknown')
        gap = int(ts(r['time']) - last_in_channel[channel]) if channel in last_in_channel else None
        last_in_channel[channel] = ts(r['time'])
        seg = 'D' + r['time'][5:7] + r['time'][8:10]           # full dump: one segment per UTC day, e.g. D0618
        con.execute('''INSERT INTO messages (msg_id, swarm, t, t_uncert_s, channel, speaker, ip16, speaker_kind, lab, text,
            body_ref, parent_msg_id, len, n_urls, gap_prev_s, text_hash, dup_of, script_label, copy_of, removed_text, in_core, segment)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                    (mid, 'dsewiki', r['time'], r.get('uncertainty_seconds'), channel, speaker, r.get('ip16'), kind,
                     'OpenAI' if kind == 'agent' else None, text, r['rev_id'],
                     'dw:' + r['diff_base'] if r.get('diff_base') else None, len(add), len(URL.findall(add)), gap,
                     hashlib.sha256(key.encode()).hexdigest()[:16], copy_of if label == 'DUPLICATE' else None,
                     label, copy_of, rem or None, r['_core'], seg))
        speakers.setdefault(speaker, kind)
        n['core' if r['_core'] else 'halo'] += 1
        n['copies'] += bool(copy_of); n['dup'] += label == 'DUPLICATE'; n['empty'] += label == 'EMPTY'
    for s, kind in speakers.items():
        if s:
            con.execute('INSERT OR IGNORE INTO agents VALUES (?,?,?,?,?)', (s, 'dsewiki', 'OpenAI' if kind == 'agent' else None,
                                                                          None, int(kind == 'human')))
    con.execute("INSERT INTO messages_fts(messages_fts) VALUES('rebuild')")
    con.commit()
    to_read = con.execute('''SELECT COUNT(*) FROM messages m WHERE in_core=1 AND COALESCE(script_label,'')!='EMPTY' AND
        (copy_of IS NULL OR NOT EXISTS (SELECT 1 FROM messages f WHERE f.msg_id=m.copy_of AND f.in_core=1))''').fetchone()[0]
    print(json.dumps(dict(n, to_read=to_read)))


if __name__ == '__main__':
    main()
