"""L1.9 re-verify (DESIGN.md 4.2 / pipeline_v2 2a), Sonnet 5.5.

Pass 1 (after readers): every record with context gaps, uncertain fields or a low reader_confidence segment.
The script pulls raw context (search hints via FTS, the page's previous save, earlier saves on the page); the model
resolves gaps against that raw text and may write a revised record. Version 1 is never edited (new version row).
Pass 2 (after groupers, run_seeds): every assertive cluster seed is checked against raw; unsupported seeds are flagged.
"""
import json, re
import config as C, store, errlog
from common import obj, arr, S, CONF, NULLSTR, SAFETY, raw, seg_view, chunks, dumps
from readers import RECORD, SYSTEM as READER_SYSTEM

STAGE = 'reverify'

SYSTEM = f"""You re-verify readers' records against the raw wiki text in an investigation of an AI agent swarm (OpenAI research agents using German wikis as a shared scratchpad, 2026). {SAFETY}

For each item you get the message's raw text, the reader's version-1 record, and raw context the script pulled (earlier saves named by the reader's search hints, the page's previous saves). For each context gap (context_needs, by index) say whether the raw context resolves it: resolved (name the msg_ids that resolve it), ambiguous (several candidates), or unresolvable (not in the context; outside_transcript gaps always are). Never invent: if raw text does not settle it, keep the uncertainty.

If resolving gaps or re-reading the raw text shows the record is wrong (wrong purpose, missed segment, a claim the text does not make, wrong context_status), set revise=true and give the revision_reason in one or two sentences; otherwise revise=false and revision_reason=null. A follow-up call writes the revised record."""

# The revised record is written in a second call: nesting RECORD inside ITEMS (as anyOf with null) makes the
# structured-output grammar too large for the API (400 "compiled grammar is too large").
REVISE_SYSTEM = f"""You rewrite readers' records in an investigation of an AI agent swarm (OpenAI research agents using German wikis as a shared scratchpad, 2026). {SAFETY}

For each item you get the message's raw text, the reader's version-1 record, raw context, and the reason a checker gave for revising it. Return one complete revised record per item (same msg_id) using the reader's record format below, fixing what the reason names and keeping everything the raw text supports. Never invent: if raw text does not settle a field, keep the uncertainty.

READER RECORD FORMAT:
{READER_SYSTEM.split('RECORD FIELDS', 1)[1]}"""
REVISED = obj({'records': arr(RECORD)})

ITEMS = obj({'items': arr(obj({
    'msg_id': S,
    'resolutions': arr(obj({'need_index': {'type': 'integer'},
                            'status': {'type': 'string', 'enum': ['resolved', 'unresolvable', 'ambiguous']},
                            'resolved_by': arr(S), 'resolution': S, 'confidence': CONF})),
    'revise': {'type': 'boolean'}, 'revision_reason': NULLSTR}))})

SEED_SYSTEM = f"""You check cluster seeds in an investigation of an AI agent swarm (OpenAI research agents using German wikis as a shared scratchpad, 2026). {SAFETY}
A seed is the segment a cluster of similar statements is anchored on, chosen because the agent stated it flatly. Check each seed's reader summary and claims against its raw text and nearby raw context. Verdict: supported (the raw text says what the record says), unsupported (the record misreads the text), unclear. Give a one-line note."""
SEEDS = obj({'seeds': arr(obj({'segment_id': S, 'verdict': {'type': 'string', 'enum': ['supported', 'unsupported', 'unclear']},
                                'note': S}))})


def fts(con, terms, before, limit=3):
    out = []
    for t in terms[:4]:
        q = re.sub(r'[^\w ]', ' ', t).strip()
        if not q:
            continue
        try:
            rows = con.execute('''SELECT m.msg_id FROM messages_fts f JOIN messages m ON m.rowid=f.rowid
                WHERE messages_fts MATCH ? AND m.t < ? ORDER BY m.t DESC LIMIT ?''', ('"' + q + '"', before, limit)).fetchall()
        except Exception:
            continue
        out += [r['msg_id'] for r in rows]
    return out


def queue(con):
    items = []
    for r in store.live_records(con):
        if r['cloned_from'] or r['record_version'] > 1:
            continue
        needs = json.loads(r['context_needs'] or '[]')
        unc = json.loads(r['uncertain_fields'] or '[]')
        lowc = con.execute('SELECT MIN(reader_confidence) FROM segments WHERE record_id=?', (r['record_id'],)).fetchone()[0]
        if r['context_status'] != 'complete' or needs or unc or (lowc is not None and lowc < C.LOW_READER_CONF):
            items.append(r)
    return items


def context_for(con, r):
    m = con.execute('SELECT * FROM messages WHERE msg_id=?', (r['msg_id'],)).fetchone()
    ids = []
    for n in json.loads(r['context_needs'] or '[]'):
        h = n.get('search_hints') or {}
        ids += fts(con, (h.get('terms') or []) + (h.get('agents') or []), m['t'])
    if m['parent_msg_id']:
        ids.append(m['parent_msg_id'])
    ids += [x['msg_id'] for x in con.execute('SELECT msg_id FROM messages WHERE channel=? AND t<? ORDER BY t DESC LIMIT 3',
                                             (m['channel'], m['t']))]
    seen, out = set(), []
    for i in ids:
        if i not in seen and i != r['msg_id']:
            seen.add(i); out.append(dict(msg_id=i, raw=raw(con, i, 600)))
    return out[:8]


def record_view(con, r):
    segs = con.execute('SELECT * FROM segments WHERE record_id=? ORDER BY char_start', (r['record_id'],)).fetchall()
    return dict(summary=r['summary'], purpose=r['purpose'], context_status=r['context_status'],
                context_needs=json.loads(r['context_needs'] or '[]'), uncertain_fields=json.loads(r['uncertain_fields'] or '[]'),
                confidence=r['confidence'],
                segments=[dict(purpose=s['purpose'], function=s['function'], assertiveness=s['assertiveness'],
                               reader_confidence=s['reader_confidence'], summary=s['summary'],
                               claims=[c['claim_text'] for c in con.execute('SELECT claim_text FROM claims WHERE segment_id=?', (s['segment_id'],))])
                          for s in segs])


def mock_items(con, rs):
    return {'items': [dict(msg_id=r['msg_id'], resolutions=[dict(need_index=i, status='unresolvable', resolved_by=[],
                                                                  resolution='not in the pulled context', confidence='low')
                                                             for i, _ in enumerate(json.loads(r['context_needs'] or '[]'))],
                           revise=False, revision_reason=None, revised_record=None) for r in rs]}


def run(con, llm, run_id):
    items = queue(con)
    jobs, meta = [], {}
    for k, part in enumerate(chunks(items, 20)):
        tid = store.new_task(con, run_id, STAGE, {'id': f'pass1_{k}', 'n': len(part)}, C.TIER_MODEL[STAGE])
        for r in part:
            store.add_loose_end(con, tid, f'le:{r["record_id"]}', 'record', r['record_id'], 're-verify flagged record')
        payload = [dict(msg_id=r['msg_id'], raw=raw(con, r['msg_id'], 2500), record_v1=record_view(con, r),
                        context=context_for(con, r)) for r in part]
        user = 'ITEMS:\n' + dumps(payload)
        jobs.append(dict(custom_id=f'pass1_{k}', task_id=tid, system=SYSTEM, user=user, schema=ITEMS, max_tokens=32000,
                         est_out=250 * len(part), mock=lambda part=part: mock_items(con, part)))
        meta[f'pass1_{k}'] = (tid, {r['msg_id']: r for r in part})
    con.commit()
    stats = dict(items=len(items), calls=len(jobs), resolved=0, unresolvable=0, ambiguous=0, revised=0, revise_rejected=0, failed_calls=0)
    to_revise = []                       # (tid, record row, reason, payload item)
    for res in llm.call_many(STAGE, jobs):
        tid, byid = meta[res['custom_id']]
        if res['error']:
            stats['failed_calls'] += 1
            store.finish_task(con, tid, 'failed'); continue
        for it in res['data'].get('items', []):
            r = byid.get(it.get('msg_id'))
            if not r:
                continue
            for z in it.get('resolutions') or []:
                rid = f'{tid}:{r["msg_id"]}:{z.get("need_index")}'
                con.execute('INSERT OR REPLACE INTO context_resolutions VALUES (?,?,?,?,?,?,?,?,?)',
                            (rid, tid, r['msg_id'], z.get('need_index', 0), z['status'], json.dumps(z.get('resolved_by') or []),
                             z.get('resolution'), z.get('confidence'), None))
                stats[z['status']] += 1
            if it.get('revise'):
                to_revise.append((tid, r, (it.get('revision_reason') or '')[:300]))
            con.execute("UPDATE loose_ends SET status='closed', closed_by=? WHERE le_id=?", (tid, f'le:{r["record_id"]}'))
        store.finish_task(con, tid)
        con.commit()
    stats['revise_asked'] = len(to_revise)
    rjobs, rmeta = [], {}
    for k, part in enumerate(chunks(to_revise, 10)):
        payload = [dict(msg_id=r['msg_id'], raw=raw(con, r['msg_id'], 2500), record_v1=record_view(con, r),
                        context=context_for(con, r), revision_reason=reason) for _, r, reason in part]
        rjobs.append(dict(custom_id=f'revise_{k}', task_id=part[0][0], system=REVISE_SYSTEM, user='ITEMS:\n' + dumps(payload),
                          schema=REVISED, max_tokens=32000, est_out=450 * len(part), mock=lambda: {'records': []}))
        rmeta[f'revise_{k}'] = {r['msg_id']: (tid, r, reason) for tid, r, reason in part}
    for res in llm.call_many(STAGE, rjobs):
        byid = rmeta[res['custom_id']]
        if res['error']:
            stats['failed_calls'] += 1; continue
        for rec in res['data'].get('records', []):
            hit = byid.get(rec.get('msg_id'))
            if not hit:
                continue
            tid, r, reason = hit
            reason_bad, prep = store.validate_record(con, dict(rec, msg_id=r['msg_id']), {r['msg_id']})
            if reason_bad:
                stats['revise_rejected'] += 1
                errlog.log(STAGE, 'revise_rejected', reason_bad, msg_id=r['msg_id'])
                continue
            store.write_record(con, tid, prep, version=2, supersedes=r['record_id'], revision_reason=reason)
            store.clone_to_copies(con, tid, prep, r['msg_id'], version=2, revision_reason='clone of revised record')
            stats['revised'] += 1
        con.commit()
    return stats


def run_seeds(con, llm, run_id):
    """pass 2: re-verify assertive cluster seeds against raw (DESIGN 4.2, pipeline_v2 D1)"""
    seeds = con.execute('''SELECT DISTINCT cks.segment_id, cks.claim_key FROM claim_key_segments cks
        JOIN claim_keys ck USING (claim_key) WHERE cks.is_seed=1 AND cks.retracted_by IS NULL AND ck.merged_into IS NULL''').fetchall()
    segs = []
    for s in seeds:
        seg = store.seg_info(con, s['segment_id'])
        reach = con.execute('SELECT COUNT(*) FROM links WHERE to_segment=? AND retracted_by IS NULL', (s['segment_id'],)).fetchone()[0]
        segs.append((seg, s['claim_key'], reach))
    jobs, meta = [], {}
    for k, part in enumerate(chunks(segs, 25)):
        tid = store.new_task(con, run_id, STAGE, {'id': f'seeds_{k}', 'n': len(part)}, C.TIER_MODEL[STAGE])
        payload = []
        for seg, key, reach in part:
            v = seg_view(con, seg, 1200)
            v.update(cluster=key, incoming_links=reach,
                     context=[dict(msg_id=x['msg_id'], raw=raw(con, x['msg_id'], 400)) for x in
                              con.execute('SELECT msg_id FROM messages WHERE channel=? AND t<? ORDER BY t DESC LIMIT 2',
                                          (seg['channel'], seg['t']))])
            payload.append(v)
        jobs.append(dict(custom_id=f'seeds_{k}', task_id=tid, system=SEED_SYSTEM, user='SEEDS:\n' + dumps(payload),
                         schema=SEEDS, max_tokens=16000, est_out=80 * len(part),
                         mock=lambda part=part: {'seeds': [dict(segment_id=s['segment_id'], verdict='supported', note='mock')
                                                           for s, _, _ in part]}))
        meta[f'seeds_{k}'] = (tid, {s['segment_id']: key for s, key, _ in part})
    con.commit()
    stats = dict(seeds=len(segs), supported=0, unsupported=0, unclear=0)
    for res in llm.call_many(STAGE, jobs):
        tid, keys = meta[res['custom_id']]
        if res['error']:
            store.finish_task(con, tid, 'failed'); continue
        for v in res['data'].get('seeds', []):
            if v.get('segment_id') not in keys:
                continue
            stats[v['verdict']] += 1
            store.add_check(con, 'seed', v['segment_id'], 'same_model', tid, 'pass' if v['verdict'] == 'supported' else 'fail', v.get('note'))
            if v['verdict'] == 'unsupported':
                con.execute('UPDATE claim_key_segments SET is_seed=0 WHERE segment_id=? AND claim_key=?', (v['segment_id'], keys[v['segment_id']]))
                store.add_loose_end(con, tid, f'le:seed:{v["segment_id"]}', 'claim_key', keys[v['segment_id']],
                                    f'seed {v["segment_id"]} not supported by raw text: {v.get("note", "")[:200]}')
        store.finish_task(con, tid)
    con.commit()
    return stats
