"""investigation.db and its write tools (store_design.md, DESIGN.md 4.6).

Model stages never write SQL. Their structured outputs are passed to the functions here, which check
citations, labels, caps and time order, then append. Every function returns ('ok', ids) or ('rejected', reason).
Append-only: nothing is updated except retracted_by / merged_into / status fields.
"""
import json, os, re, sqlite3, unicodedata, datetime as dt
import config as C

PURPOSES = ['STATUS', 'CLAIM', 'RELAY', 'ASK', 'DIRECT', 'COMMIT', 'STANDBY', 'CONFIRM', 'DOUBT', 'CORRECT',
            'SOCIAL', 'REFLECT', 'WORK', 'STASH', 'HOUSEKEEPING', 'ACCESS_WORKAROUND', 'UNCLEAR']
PRECEDENCE = ['ACCESS_WORKAROUND', 'CORRECT', 'DOUBT', 'CONFIRM', 'DIRECT', 'CLAIM', 'RELAY', 'ASK', 'COMMIT', 'STATUS']
FUNCTIONS = ['epistemic', 'executive', 'normative', 'infrastructural', 'affiliative', 'adversarial']
GAP_TYPES = ['reply_to_unseen', 'unresolved_reference', 'coded_token', 'continuation', 'compacted_history',
             'implicit_task', 'identity', 'outside_transcript']
LINK_TYPES = ['source_of', 'reply_to', 'acted_on', 'confirms', 'doubts', 'corrects', 'same_run', 'exposed_to',
              'independent_of', 'anchor']
VIAS = ['direct_message', 'shared_page', 'human_relay', 'external_source', 'task_prompt', 'unknown']
LAYERS = ['belief', 'goal', 'protocol', 'method', 'word']
CONF = ['high', 'medium', 'low']
AW = 'ACCESS_WORKAROUND'
KEEP_KW_PREFIX = ('page:', 'agent:', 'task:')     # only these keywords survive on an ACCESS_WORKAROUND segment


def now():
    return dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def connect(path=None):
    con = sqlite3.connect(path or C.DB, timeout=60, check_same_thread=False)  # llm.py serializes writes with a lock
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys = ON')
    return con


def init_db(path=None):
    path = path or C.DB
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        os.remove(path)
    for ext in ('-wal', '-shm'):
        if os.path.exists(path + ext):
            os.remove(path + ext)
    sql = open(os.path.join(C.SPEC, 'store_schema.sql')).read()
    # run groups are built over name-sessions (DESIGN 5.5), so membership may be a session id
    sql = sql.replace("member_kind IN ('speaker','signed_name','run_tag')",
                      "member_kind IN ('speaker','signed_name','run_tag','session')")
    con = connect(path)
    con.executescript(sql)
    con.executescript(open(os.path.join(os.path.dirname(__file__), 'schema_patch.sql')).read())
    con.commit()
    return con


# ---------------------------------------------------------------- provenance
def new_run(con, run_id, config):
    con.execute('INSERT OR REPLACE INTO runs VALUES (?,?,?,?)', (run_id, now(), json.dumps(config), None))
    con.commit()


def new_task(con, run_id, tier, scope, model, replica=0):
    scope_s = json.dumps(scope, sort_keys=True)
    task_id = f'{run_id}/{tier}/' + (scope.get('id') if isinstance(scope, dict) and scope.get('id') else
                                     str(abs(hash(scope_s)) % 10**8))
    con.execute('INSERT OR REPLACE INTO tasks (task_id, run_id, tier, scope, replica, model, status, started_at) '
                'VALUES (?,?,?,?,?,?,?,?)', (task_id, run_id, tier, scope_s, replica, model, 'open', now()))
    return task_id


def finish_task(con, task_id, status='done'):
    con.execute('UPDATE tasks SET status=?, finished_at=? WHERE task_id=?', (status, now(), task_id))


def log_op(con, task_id, tool, args, result):
    con.execute('INSERT INTO ops (t, task_id, tool, args, result) VALUES (?,?,?,?,?)',
                (now(), task_id, tool, json.dumps(args, ensure_ascii=False, default=str)[:4000], result))


# ---------------------------------------------------------------- citations
_ws = re.compile(r'\s+')


def _norm_map(s):
    """whitespace-collapsed, NFC text plus a map from each normalized char to its index in s."""
    out, idx, prev_space = [], [], False
    for i, ch in enumerate(s):
        if ch.isspace():
            if prev_space or not out:
                continue
            out.append(' '); idx.append(i); prev_space = True
        else:
            for c in unicodedata.normalize('NFC', ch):
                out.append(c); idx.append(i)
            prev_space = False
    return ''.join(out), idx


def locate(text, quote):
    """(start, end) of quote in text. Exact first; then whitespace/NFC-tolerant (the stored quote is then the
    exact text span, so the citation is still an exact substring). None if not found."""
    if not quote:
        return None
    i = text.find(quote)
    if i >= 0:
        return i, i + len(quote)
    nt, idx = _norm_map(text)
    nq = _ws.sub(' ', unicodedata.normalize('NFC', quote)).strip()
    if not nq:
        return None
    j = nt.find(nq)
    if j < 0:
        return None
    return idx[j], idx[j + len(nq) - 1] + 1


def msg_text(con, msg_id):
    r = con.execute('SELECT text FROM messages WHERE msg_id=?', (msg_id,)).fetchone()
    return r['text'] if r else None


def is_aw_span(con, msg_id, start, end):
    for s in con.execute("SELECT char_start, char_end FROM segments WHERE msg_id=? AND purpose=? AND retracted_by IS NULL",
                         (msg_id, AW)):
        if start < s['char_end'] and end > s['char_start']:
            return True
    return False


def add_citation(con, obj_type, obj_id, msg_id, quote):
    text = msg_text(con, msg_id)
    if text is None:
        return 'rejected', f'unknown msg_id {msg_id}'
    loc = locate(text, quote)
    if not loc:
        return 'rejected', f'quote not found in {msg_id}'
    a, b = loc
    if b - a > 200:
        b = a + 200
    q = text[a:b]
    con.execute('INSERT INTO citations (obj_type, obj_id, msg_id, quote, q_start, q_end, redact) VALUES (?,?,?,?,?,?,?)',
                (obj_type, obj_id, msg_id, q, a, b, int(is_aw_span(con, msg_id, a, b))))
    return 'ok', (a, b)


def citation_ok(con, msg_id, quote):
    text = msg_text(con, msg_id)
    return bool(text is not None and locate(text, quote))


# ---------------------------------------------------------------- L1 reader records
def _clean_kw(k):
    return re.sub(r'\s+', ' ', (k or '').strip().lower())[:120]


def validate_record(con, rec, allowed_msg_ids):
    """Returns (None, prepared) or (reason, None). Does not write."""
    mid = rec.get('msg_id')
    if mid not in allowed_msg_ids:
        return f'msg_id {mid} is not a core message of this window', None
    text = msg_text(con, mid)
    cs = rec.get('context_status')
    if cs not in ('complete', 'partial', 'missing'):
        return f'bad context_status {cs}', None
    if rec.get('confidence') not in CONF:
        return 'bad confidence', None
    segs = rec.get('segments') or []
    if not segs:
        return 'no segments', None
    located = []
    for k, s in enumerate(segs):
        for p in [s.get('purpose')] + list(s.get('secondary_purposes') or []):
            if p not in PURPOSES:
                return f'segment {k}: unknown purpose {p}', None
        if s.get('purpose') == 'UNCLEAR' and cs != 'missing':
            return f'segment {k}: UNCLEAR is only allowed when context_status is missing', None
        if len(s.get('secondary_purposes') or []) > 2:
            return f'segment {k}: more than 2 secondary purposes', None
        if s.get('function') not in FUNCTIONS:
            return f'segment {k}: unknown function {s.get("function")}', None
        for f in ('assertiveness', 'reader_confidence'):
            v = s.get(f)
            if not isinstance(v, (int, float)) or not 0 <= v <= 1:
                return f'segment {k}: {f} must be a number from 0 to 1', None
        loc = locate(text, s.get('start_quote') or '')
        if not loc:
            return f'segment {k}: start_quote is not an exact substring of the message text', None
        located.append((loc[0], k))
        for c in s.get('claims') or []:
            if c.get('about') not in ('self', 'shared') or c.get('stance') not in ('asserts', 'relays', 'doubts', 'corrects'):
                return f'segment {k}: bad claim about/stance', None
            if c.get('quote') and not locate(text, c['quote']):
                return f'segment {k}: claim quote not found', None
    starts = sorted(located)
    if len({a for a, _ in starts}) != len(starts):
        return 'two segments start at the same place', None
    if not locate(text, rec.get('quote') or ''):
        return 'record quote is not an exact substring of the message text', None
    for n, need in enumerate(rec.get('context_needs') or []):
        if need.get('type') not in GAP_TYPES:
            return f'context_needs[{n}]: unknown type', None
        if need.get('span') and not locate(text, need['span']):
            return f'context_needs[{n}]: span not found', None
    # spans: segment i runs from its start to the next segment's start; the first one from 0
    spans = {}
    for i, (a, k) in enumerate(starts):
        b = starts[i + 1][0] if i + 1 < len(starts) else len(text)
        spans[k] = (0 if i == 0 else a, b)
    return None, dict(rec=rec, spans=spans, order=[k for _, k in starts])


def write_record(con, task_id, prepared, version=1, supersedes=None, revision_reason=None, cloned_from=None,
                 msg_id_override=None, span_override=None, quote_override=None):
    rec = prepared['rec']
    mid = msg_id_override or rec['msg_id']
    rid = f'{task_id}#{mid}'
    segs = rec['segments']
    order = prepared['order']
    spans = span_override or prepared['spans']
    seg_purposes = [segs[k]['purpose'] for k in order]
    allp = seg_purposes + [p for k in order for p in (segs[k].get('secondary_purposes') or [])]
    ranked = sorted(set(allp), key=lambda p: PRECEDENCE.index(p) if p in PRECEDENCE else 99)
    primary = ranked[0]
    rest = [p for p in ranked[1:]][:2]
    summary = C.AW_SUMMARY if AW in allp else (rec.get('summary') or '')[:500]
    flags = rec.get('flags') or {}
    con.execute('''INSERT INTO records (record_id, msg_id, task_id, signed_name, run_tag, purpose, purpose2, purpose3,
        flag_coded_token, flag_task_content, flag_addresses_human, summary, reply_to_hint, anomaly, confidence,
        record_version, supersedes, revision_reason, context_status, context_needs, uncertain_fields, cloned_from)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                (rid, mid, task_id, rec.get('signed_name'), rec.get('run_tag'), primary,
                 rest[0] if rest else None, rest[1] if len(rest) > 1 else None,
                 int(bool(flags.get('coded_token'))), int(bool(flags.get('task_content'))),
                 int(bool(flags.get('addresses_human'))), summary, rec.get('reply_to_hint'),
                 None if AW in allp else rec.get('anomaly'), rec['confidence'], version, supersedes, revision_reason,
                 rec.get('context_status'), json.dumps(rec.get('context_needs') or [], ensure_ascii=False),
                 json.dumps(rec.get('uncertain_fields') or []), cloned_from))
    text = msg_text(con, mid)
    add_citation(con, 'record', rid, mid, (quote_override or rec['quote']) if AW not in allp else text[:min(len(text), 60)])
    for n, k in enumerate(order, 1):
        s = segs[k]
        sid = f'{mid}#{n}' if version == 1 else f'{mid}#{n}v{version}'
        a, b = spans[k]
        aw = s['purpose'] == AW or AW in (s.get('secondary_purposes') or [])
        con.execute('''INSERT INTO segments (segment_id, record_id, msg_id, char_start, char_end, function, purpose,
            assertiveness, reader_confidence, summary) VALUES (?,?,?,?,?,?,?,?,?,?)''',
                    (sid, rid, mid, a, b, s['function'], AW if aw else s['purpose'], float(s['assertiveness']),
                     float(s['reader_confidence']), C.AW_SUMMARY if aw else (s.get('summary') or '')[:300]))
        kws = []
        for kw in s.get('keywords') or []:
            key = _clean_kw(kw.get('keyword') if isinstance(kw, dict) else kw)
            if not key or (aw and not key.startswith(KEEP_KW_PREFIX)):
                continue
            kws.append((key, int(bool(kw.get('from_context'))) if isinstance(kw, dict) else 0))
        for key, fc in dict(kws).items():
            con.execute('INSERT OR IGNORE INTO segment_keywords VALUES (?,?,?)', (sid, key, fc))
        if aw:
            continue                                   # claims about a method are refused (store_design 2)
        for j, c in enumerate(s.get('claims') or [], 1):
            cid = f'{rid}/s{n}c{j}'
            con.execute('INSERT INTO claims (claim_id, record_id, msg_id, claim_text, norm_text, about, stance, stated_source, segment_id) '
                        'VALUES (?,?,?,?,?,?,?,?,?)', (cid, rid, mid, c['claim_text'][:500], norm_text(c['claim_text']),
                                                       c['about'], c['stance'], c.get('stated_source') or 'unstated', sid))
            if c.get('quote') and citation_ok(con, mid, c['quote']):
                add_citation(con, 'claim', cid, mid, c['quote'])
    if AW not in allp:
        for e in rec.get('entities') or []:
            con.execute('INSERT OR IGNORE INTO mentions VALUES (?,?,?,?)', (rid, mid, 'entity', _clean_kw(e)))
    for a in rec.get('addressed_to') or []:
        con.execute('INSERT OR IGNORE INTO mentions VALUES (?,?,?,?)', (rid, mid, 'addressed_to', a.strip()[:120]))
    log_op(con, task_id, 'write_record', {'msg_id': mid, 'version': version}, 'ok')
    return 'ok', rid


def norm_text(s):
    s = unicodedata.normalize('NFC', s or '').lower()
    return re.sub(r'\s+', ' ', re.sub(r'[^\w\s.%$-]', ' ', s)).strip()


def clone_to_copies(con, task_id, prepared, first_msg_id, version=1, revision_reason=None):
    """DESIGN 5.3: copies are read once; the record is cloned to each copy, quotes re-located in the copy.
    Copies share the added text but sit on other pages, so a quote in the title line maps to the copy's title.
    Returns msg_ids whose re-check failed (they must go to readers)."""
    failed = []
    src = msg_text(con, first_msg_id)
    src_title = len(src.split('\n', 1)[0])
    rec = prepared['rec']
    copies = [r['msg_id'] for r in con.execute('SELECT msg_id FROM messages WHERE copy_of=? AND in_core=1', (first_msg_id,))]
    for cm in copies:
        text = msg_text(con, cm)
        title = text.split('\n', 1)[0]

        def where(q):
            a = locate(src, q)
            if a and a[0] <= src_title:
                return 0
            b = locate(text[len(title):], q)
            return None if b is None else b[0] + len(title)
        starts = []
        for k in prepared['order']:
            p = where(rec['segments'][k]['start_quote'])
            if p is None:
                break
            starts.append((p, k))
        rq = where(rec['quote'])
        if len(starts) != len(prepared['order']) or rq is None or len({a for a, _ in starts}) != len(starts):
            failed.append(cm); continue
        starts.sort()
        spans = {}
        for i, (a, k) in enumerate(starts):
            b = starts[i + 1][0] if i + 1 < len(starts) else len(text)
            spans[k] = (0 if i == 0 else a, b)
        qo = title[:120] if rq == 0 and locate(src, rec['quote'])[0] < src_title else None
        sup = None
        if version > 1:
            prev = [r for r in live_records(con) if r['msg_id'] == cm]
            sup = prev[0]['record_id'] if prev else None
        write_record(con, task_id, prepared, version=version, supersedes=sup, revision_reason=revision_reason,
                     cloned_from=f'{task_id}#{first_msg_id}', msg_id_override=cm, span_override=spans, quote_override=qo)
    return failed


def coverage_gap(con, msg_id, task_id, reason, detail=None):
    con.execute('INSERT OR REPLACE INTO coverage_gaps VALUES (?,?,?,?)', (msg_id, task_id, reason, detail))


# ---------------------------------------------------------------- reads used by later tiers
def live_records(con):
    """latest live version per message"""
    return con.execute('''SELECT r.* FROM records r WHERE r.retracted_by IS NULL AND NOT EXISTS
        (SELECT 1 FROM records r2 WHERE r2.supersedes = r.record_id AND r2.retracted_by IS NULL)''').fetchall()


def live_segments(con, msg_ids=None):
    q = '''SELECT s.*, m.t, m.speaker, m.channel, m.copy_of, m.in_core FROM segments s JOIN messages m USING (msg_id)
           WHERE s.retracted_by IS NULL AND NOT EXISTS
           (SELECT 1 FROM records r2 WHERE r2.supersedes = s.record_id AND r2.retracted_by IS NULL)'''
    rows = con.execute(q).fetchall()
    if msg_ids is not None:
        rows = [r for r in rows if r['msg_id'] in msg_ids]
    return rows


def get_raw(con, msg_id, halo=0, max_chars=1500):
    """Raw text for any tier (pipeline_v2 section 7). ACCESS_WORKAROUND spans come back withheld."""
    m = con.execute('SELECT * FROM messages WHERE msg_id=?', (msg_id,)).fetchone()
    if not m:
        return None
    text = m['text']
    for s in sorted(con.execute('SELECT char_start, char_end FROM segments WHERE msg_id=? AND purpose=? AND retracted_by IS NULL',
                                (msg_id, AW)).fetchall(), key=lambda r: -r['char_start']):
        text = text[:s['char_start']] + C.WITHHELD + text[s['char_end']:]
    out = [dict(msg_id=msg_id, t=m['t'], channel=m['channel'], speaker=m['speaker'], text=text[:max_chars],
                truncated=len(text) > max_chars)]
    if halo:
        for n in con.execute('SELECT msg_id FROM messages WHERE t < ? ORDER BY t DESC LIMIT ?', (m['t'], halo)):
            out.append(get_raw(con, n['msg_id'], 0, max_chars // 3)[0])
    return out


def seg_info(con, segment_id):
    return con.execute('SELECT s.*, m.t, m.speaker, m.channel FROM segments s JOIN messages m USING (msg_id) WHERE segment_id=?',
                       (segment_id,)).fetchone()


# ---------------------------------------------------------------- L2 links
def add_link(con, task_id, link_id, from_seg, to_seg, from_msg, to_msg, ltype, quote, confidence, rationale,
             via=None, claim_key=None, local=True):
    if ltype not in LINK_TYPES:
        return 'rejected', f'unknown link type {ltype}'
    if via is not None and via not in VIAS:
        via = 'unknown'
    if confidence not in CONF:
        return 'rejected', 'bad confidence'
    if from_seg:
        si = seg_info(con, from_seg)
        if not si:
            return 'rejected', f'unknown segment {from_seg}'
        from_msg = si['msg_id']
    if to_seg:
        ti = seg_info(con, to_seg)
        if not ti:
            return 'rejected', f'unknown segment {to_seg}'
        to_msg = ti['msg_id']
    fm = con.execute('SELECT t FROM messages WHERE msg_id=?', (from_msg,)).fetchone()
    tm = con.execute('SELECT t FROM messages WHERE msg_id=?', (to_msg,)).fetchone()
    if not fm or not tm:
        return 'rejected', 'unknown msg_id'
    if from_msg == to_msg:
        return 'rejected', 'link to itself'
    if tm['t'] > fm['t'] and ltype not in ('same_run', 'independent_of'):
        return 'rejected', 'to message is later than from message'
    if local and from_seg:
        n = con.execute("SELECT COUNT(*) FROM links WHERE from_segment=? AND retracted_by IS NULL AND task_id IN "
                        "(SELECT task_id FROM tasks WHERE tier='local_linker')", (from_seg,)).fetchone()[0]
        if n >= C.LOCAL_LINK_CAP:
            return 'rejected', f'segment {from_seg} already has {C.LOCAL_LINK_CAP} local links'
    if not citation_ok(con, from_msg, quote):
        return 'rejected', 'evidence quote is not an exact substring of the from message'
    if con.execute('SELECT 1 FROM links WHERE link_id=?', (link_id,)).fetchone():
        return 'rejected', 'duplicate link id'
    con.execute('INSERT INTO links VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                (link_id, task_id, from_msg, to_msg, from_seg, to_seg, ltype, via, claim_key, confidence,
                 (rationale or '')[:600], None))
    add_citation(con, 'link', link_id, from_msg, quote)
    log_op(con, task_id, 'add_link', {'id': link_id, 'type': ltype}, 'ok')
    return 'ok', link_id


def retract(con, table, key_col, key, by):
    con.execute(f'UPDATE {table} SET retracted_by=? WHERE {key_col}=? AND retracted_by IS NULL', (by, key))


# ---------------------------------------------------------------- L3 clusters (claim keys over segments)
def new_claim_key(con, task_id, key, canonical_text, layer, rationale):
    if layer not in LAYERS:
        return 'rejected', f'unknown layer {layer}'
    base, n = key, 2
    while con.execute('SELECT 1 FROM claim_keys WHERE claim_key=?', (key,)).fetchone():
        key = f'{base}-{n}'; n += 1
    con.execute('INSERT INTO claim_keys (claim_key, task_id, canonical_text, layer, rationale) VALUES (?,?,?,?,?)',
                (key, task_id, canonical_text[:500], layer, rationale[:800]))
    log_op(con, task_id, 'new_claim_key', {'key': key}, 'ok')
    return 'ok', key


def add_key_segment(con, task_id, key, segment_id, confidence, is_seed=0):
    if not seg_info(con, segment_id):
        return 'rejected', f'unknown segment {segment_id}'
    if confidence not in CONF:
        confidence = 'low'
    con.execute('INSERT OR IGNORE INTO claim_key_segments VALUES (?,?,?,?,?,?)',
                (key, segment_id, task_id, confidence, int(is_seed), None))
    for c in con.execute('SELECT claim_id FROM claims WHERE segment_id=?', (segment_id,)):
        con.execute('INSERT OR IGNORE INTO claim_key_members VALUES (?,?,?,?,?)', (key, c['claim_id'], task_id, confidence, None))
    return 'ok', None


def merge_claim_keys(con, task_id, keep, merge, rationale):
    if keep == merge:
        return 'rejected', 'same key'
    for k in (keep, merge):
        if not con.execute('SELECT 1 FROM claim_keys WHERE claim_key=? AND merged_into IS NULL', (k,)).fetchone():
            return 'rejected', f'unknown or already merged key {k}'
    for r in con.execute('SELECT * FROM claim_key_segments WHERE claim_key=? AND retracted_by IS NULL', (merge,)).fetchall():
        add_key_segment(con, task_id, keep, r['segment_id'], r['confidence'], r['is_seed'])
    con.execute('UPDATE claim_keys SET merged_into=? WHERE claim_key=?', (keep, merge))
    log_op(con, task_id, 'merge_claim_keys', {'keep': keep, 'merge': merge, 'why': rationale}, 'ok')
    return 'ok', None


def add_cluster_edge(con, task_id, edge_id, from_key, to_key, etype, confidence, rationale, cites):
    """cites: [(msg_id, quote)] with at least one from each side (checked by caller)"""
    if etype not in ('evolves_into', 'feeds', 'corrects', 'supersedes', 'caused'):
        return 'rejected', 'bad type'
    for k in (from_key, to_key):
        if not con.execute('SELECT 1 FROM claim_keys WHERE claim_key=? AND merged_into IS NULL', (k,)).fetchone():
            return 'rejected', f'unknown key {k}'
    for mid, q in cites:
        if not citation_ok(con, mid, q):
            return 'rejected', f'quote not found in {mid}'
    con.execute('INSERT INTO cluster_edges VALUES (?,?,?,?,?,?,?,?)', (edge_id, task_id, from_key, to_key, etype,
                                                                       confidence if confidence in CONF else 'low', rationale[:800], None))
    for mid, q in cites:
        add_citation(con, 'cluster_edge', edge_id, mid, q)
    return 'ok', edge_id


# ---------------------------------------------------------------- misc writers
def add_analysis(con, task_id, analysis_id, kind, subject, body):
    con.execute('INSERT OR REPLACE INTO analyses VALUES (?,?,?,?,?)',
                (analysis_id, task_id, kind, subject, json.dumps(body, ensure_ascii=False)))


def add_check(con, obj_type, obj_id, checker, task_id, verdict, note):
    con.execute('INSERT INTO checks (obj_type, obj_id, checker, task_id, verdict, note, t) VALUES (?,?,?,?,?,?,?)',
                (obj_type, obj_id, checker, task_id, verdict, (note or '')[:800], now()))


def add_loose_end(con, task_id, le_id, about_type, about_id, question):
    con.execute('INSERT OR IGNORE INTO loose_ends VALUES (?,?,?,?,?,?,?)',
                (le_id, task_id, about_type, about_id, question[:500], 'open', None))


def add_observation(con, task_id, obs_id, text, cites):
    good = []
    for m, q in cites:
        t = msg_text(con, m)
        loc = locate(t, q) if t else None
        if loc and not is_aw_span(con, m, *loc):
            good.append((m, q))
    if not good:
        return 'rejected', 'an observation must cite at least one message with an exact quote'
    con.execute('INSERT INTO observations VALUES (?,?,?)', (obs_id, task_id, text[:1500]))
    for m, q in good:
        add_citation(con, 'observation', obs_id, m, q)
    return 'ok', obs_id


def add_finding(con, task_id, finding_id, text, confidence, supports):
    ok = []
    for s in supports:
        t, i = s.get('type'), s.get('id')
        table = {'claim_key': ('claim_keys', 'claim_key'), 'link': ('links', 'link_id'),
                 'cluster_edge': ('cluster_edges', 'edge_id'), 'run_group': ('run_groups', 'group_id'),
                 'conversation': ('conversations', 'conv_id'), 'analysis': ('analyses', 'analysis_id')}.get(t)
        if table and con.execute(f'SELECT 1 FROM {table[0]} WHERE {table[1]}=?', (i,)).fetchone():
            ok.append({'type': t, 'id': i})
    if not ok:
        return 'rejected', 'a finding must point at claim keys, links, cluster edges, run groups, conversations or analyses'
    con.execute('INSERT INTO findings VALUES (?,?,?,?,?)', (finding_id, task_id, text[:2000],
                                                            confidence if confidence in CONF else 'low', json.dumps(ok)))
    return 'ok', finding_id


def record_usage(con, call_id, task_id, tier, model, batch, u, stop_reason):
    pin, pout = C.PRICE.get(model, (4.0, 20.0))
    disc = C.BATCH_DISCOUNT if batch else 1.0
    cost = ((u.get('input_tokens', 0) * pin + u.get('output_tokens', 0) * pout +
             u.get('cache_write', 0) * pin * 1.25) * disc + u.get('cache_read', 0) * C.CACHE_READ * disc) / 1e6
    con.execute('INSERT OR REPLACE INTO usage VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                (call_id, task_id, tier, model, int(batch), u.get('input_tokens', 0), u.get('output_tokens', 0),
                 u.get('cache_read', 0), u.get('cache_write', 0), cost, stop_reason, now()))
    return cost


def spent(con):
    return con.execute('SELECT COALESCE(SUM(cost_usd),0) FROM usage').fetchone()[0]
