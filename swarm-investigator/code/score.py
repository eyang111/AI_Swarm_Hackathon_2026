"""Scoring (DESIGN.md 8) and the run report. Reads truth only here, after every model stage has finished.

- planted cascades: was each planted item found as one cluster, and which truth event rows the events view matched
  (same agent, role, layer, item; t within 30 min), plus source and depth agreement;
- the four README cases (candidates, not truth): what the pipeline made of each;
- reader stats: coverage, refusals, context status, version-1 vs version-2 changes, before/after Jun 18;
- cost from the usage ledger.
Output: test_run/report.md and test_run/scores.json (no message quotes).
"""
import collections, json, os
import config as C, errlog, store, identity

JUN18 = '2026-06-18'


def plants(con):
    out = []
    path = os.path.join(C.TRUTH_DIR, 'truth_plants.jsonl')
    if not os.path.exists(path):
        return out
    ev = con.execute('SELECT * FROM events').fetchall()
    for p in map(json.loads, open(path)):
        pm = set(p['msg_ids'])
        keys = collections.Counter(r['claim_key'] for r in con.execute('SELECT claim_key, msg_id FROM live_members') if r['msg_id'] in pm)
        best = keys.most_common(1)[0][0] if keys else None
        key_row = con.execute('SELECT * FROM claim_keys WHERE claim_key=?', (best,)).fetchone() if best else None
        members = {r['msg_id'] for r in con.execute('SELECT msg_id FROM live_members WHERE claim_key=?', (best,))} if best else set()
        rows = []
        for t in p['events']:
            cand = [e for e in ev if e['msg_id'] == t['msg_id'] and e['item_id'] == best]
            e = cand[0] if cand else None
            rows.append(dict(msg_id=t['msg_id'], agent=t['agent'], truth_role=t['role'], truth_depth=t['depth'],
                             found=bool(e), role=e['role'] if e else None, depth=e['depth'] if e else None,
                             role_ok=bool(e and e['role'] == t['role']),
                             depth_ok=bool(e and ['said', 'planned', 'acted'].index(e['depth']) <= ['said', 'planned', 'acted'].index(t['depth'])),
                             depth_exact=bool(e and e['depth'] == t['depth']),
                             source_ok=(e['exposure_msg_id'] == t['source_msg_id']) if (e and t['source_msg_id']) else None,
                             confidence=e['confidence'] if e else None))
        out.append(dict(plant_id=p['plant_id'], difficulty=p['difficulty'], layer=p['layer'], cluster=best,
                        cluster_layer=key_row['layer'] if key_row else None, layer_ok=bool(key_row and key_row['layer'] == p['layer']),
                        plant_msgs_in_cluster=len(members & pm), plant_msgs=len(pm), other_msgs_in_cluster=len(members - pm),
                        split_across_clusters=len(keys), events=rows,
                        recall_strict=sum(r['found'] and r['role_ok'] for r in rows) / len(rows),
                        recall_found=sum(r['found'] for r in rows) / len(rows)))
    return out


def readme_cases(con):
    ids = identity.group_of(con)
    cases = {}
    # 1. S3 exact-copy cascade: biggest copy group in S3
    g = con.execute('''SELECT copy_of, COUNT(*) AS n FROM messages WHERE segment='S3' AND copy_of IS NOT NULL
                       GROUP BY copy_of ORDER BY n DESC LIMIT 1''').fetchone()
    if g:
        grp = [g['copy_of']] + [r['msg_id'] for r in con.execute('SELECT msg_id FROM messages WHERE copy_of=?', (g['copy_of'],))]
        keys = collections.Counter(r['claim_key'] for r in con.execute('SELECT claim_key, msg_id FROM live_members') if r['msg_id'] in set(grp))
        names = {con.execute('SELECT speaker FROM messages WHERE msg_id=?', (m,)).fetchone()[0] for m in grp}
        cases['1_s3_copy_cascade'] = dict(first_instance=g['copy_of'], saves=len(grp), names=len(names),
                                          name_sessions=len({ids.get(m, (None,))[0] for m in grp}),
                                          run_groups=len({ids.get(m, (None, None))[1] for m in grp} - {None}),
                                          saves_in_a_run_group=sum(1 for m in grp if ids.get(m, (None, None))[1]),
                                          clusters=dict(keys.most_common(3)),
                                          source_of_links=con.execute(f'''SELECT COUNT(*) FROM live_links WHERE type='source_of' AND from_msg_id IN
                                              ({','.join('?' * len(grp))})''', grp).fetchone()[0],
                                          l4_verdict=_l4(con, keys.most_common(1)[0][0]) if keys else None)
    # 2. Data USA grocery/Georgia/2014 query URL in S2 (copying vs convergence)
    ms = [r['msg_id'] for r in con.execute('''SELECT msg_id, text FROM messages WHERE in_core=1 AND segment='S2' ''')
          if 'datausa' in r['text'].lower() and '2014' in r['text'] and 'georgia' in r['text'].lower() and 'grocer' in r['text'].lower()]
    keys = collections.Counter(r['claim_key'] for r in con.execute('SELECT claim_key, msg_id FROM live_members') if r['msg_id'] in set(ms))
    cases['2_s2_query_url'] = dict(saves_matching=len(ms), clusters=dict(keys.most_common(3)),
                                   l4_verdict=_l4(con, keys.most_common(1)[0][0]) if keys else None)
    # 3. relay page conversation
    ms = [r['msg_id'] for r in con.execute("SELECT msg_id FROM messages WHERE channel='dse~DataUSAGroceryLiveRounds2027' AND in_core=1")]
    convs = collections.Counter(r['conv_id'] for r in con.execute('SELECT conv_id, msg_id FROM conversation_members') if r['msg_id'] in set(ms))
    cases['3_s2_relay_conversation'] = dict(saves=len(ms), conversations=dict(convs.most_common(3)),
                                            all_in_one=bool(convs) and convs.most_common(1)[0][1] == len(ms),
                                            topic=(con.execute('SELECT topic FROM conversations WHERE conv_id=?', (convs.most_common(1)[0][0],)).fetchone()[0]
                                                   if convs else None))
    # 4. S1 link-list spread
    ms = [r['msg_id'] for r in con.execute("SELECT msg_id, text FROM messages WHERE in_core=1 AND segment='S1'")
          if 'PublicDirectoryResearchLinks' in r['text'] or 'OpenDirectoryBridge' in r['text']]
    keys = collections.Counter(r['claim_key'] for r in con.execute('SELECT claim_key, msg_id FROM live_members') if r['msg_id'] in set(ms))
    pages = {con.execute('SELECT channel FROM messages WHERE msg_id=?', (m,)).fetchone()[0] for m in ms}
    cases['4_s1_link_list'] = dict(saves=len(ms), pages=len(pages), clusters=dict(keys.most_common(3)),
                                   l4_verdict=_l4(con, keys.most_common(1)[0][0]) if keys else None)
    return cases


def _l4(con, key):
    r = con.execute("SELECT body FROM analyses WHERE analysis_id=?", (f'l4:{key}',)).fetchone()
    if not r:
        return None
    b = json.loads(r['body'])
    return dict(origin=(b.get('origin_assessment') or {}).get('kind'), copying=(b.get('copying_vs_convergence') or {}).get('verdict'))


def reader_stats(con):
    core = con.execute("SELECT COUNT(*) FROM messages WHERE in_core=1 AND COALESCE(script_label,'')!='EMPTY'").fetchone()[0]
    rec = con.execute('SELECT COUNT(DISTINCT msg_id) FROM records').fetchone()[0]
    gaps = {r['reason']: r['n'] for r in con.execute('SELECT reason, COUNT(*) AS n FROM coverage_gaps GROUP BY reason')}
    by_seg = {}
    for seg in ('S1', 'S2', 'S3'):
        rows = [r for r in store.live_records(con) if con.execute('SELECT segment FROM messages WHERE msg_id=?', (r['msg_id'],)).fetchone()[0] == seg
                and not r['cloned_from']]
        cs = collections.Counter(r['context_status'] for r in rows)
        by_seg[seg] = dict(records=len(rows), context=dict(cs),
                           reply_to_unseen=sum('reply_to_unseen' in (r['context_needs'] or '') for r in rows),
                           purposes=dict(collections.Counter(r['purpose'] for r in rows).most_common(6)))
    v2 = con.execute('SELECT COUNT(*) FROM records WHERE record_version>1 AND cloned_from IS NULL').fetchone()[0]
    changed = 0
    for r in con.execute('SELECT r2.purpose AS p2, r1.purpose AS p1 FROM records r2 JOIN records r1 ON r1.record_id=r2.supersedes WHERE r2.cloned_from IS NULL'):
        changed += r['p1'] != r['p2']
    return dict(core_saves=core, saves_with_records=rec, coverage=round(rec / core, 3) if core else None, gaps=gaps,
                by_segment=by_seg, v2_records=v2, v2_purpose_changed=changed,
                aw_segments=con.execute("SELECT COUNT(*) FROM segments WHERE purpose='ACCESS_WORKAROUND'").fetchone()[0],
                before_jun18=con.execute(f"SELECT COUNT(DISTINCT msg_id) FROM records r JOIN messages m USING (msg_id) WHERE m.t < '{JUN18}'").fetchone()[0],
                after_jun18=con.execute(f"SELECT COUNT(DISTINCT msg_id) FROM records r JOIN messages m USING (msg_id) WHERE m.t >= '{JUN18}'").fetchone()[0])


def costs(con):
    rows = con.execute('''SELECT tier, model, COUNT(*) AS calls, SUM(input_tokens) AS inp, SUM(output_tokens) AS outp,
        SUM(cache_read) AS cr, SUM(cost_usd) AS usd FROM usage GROUP BY tier, model''').fetchall()
    return [dict(r) for r in rows], store.spent(con)


def counts(con):
    q = lambda s: con.execute(s).fetchone()[0]
    return dict(records=q('SELECT COUNT(*) FROM records'), segments=q('SELECT COUNT(*) FROM segments'),
                links=q('SELECT COUNT(*) FROM live_links'), conversations=q('SELECT COUNT(*) FROM conversations'),
                clusters=q('SELECT COUNT(*) FROM claim_keys WHERE merged_into IS NULL'),
                merged_clusters=q('SELECT COUNT(*) FROM claim_keys WHERE merged_into IS NOT NULL'),
                cluster_edges=q('SELECT COUNT(*) FROM cluster_edges WHERE retracted_by IS NULL'),
                run_groups=q('SELECT COUNT(*) FROM run_groups'), findings=q('SELECT COUNT(*) FROM findings'),
                observations=q('SELECT COUNT(*) FROM observations'), events=q('SELECT COUNT(*) FROM events'),
                checker=dict(con.execute("SELECT verdict, COUNT(*) FROM checks WHERE checker='same_model' GROUP BY verdict").fetchall()))


def main(stage_stats=None, backend='?'):
    con = store.connect()
    P = plants(con)
    out = dict(backend=backend, counts=counts(con), plants=P, readme_cases=readme_cases(con), readers=reader_stats(con),
               costs=costs(con)[0], spent_usd=round(costs(con)[1], 3), stages=stage_stats or {})
    json.dump(out, open(os.path.join(C.RUN_DIR, 'scores.json'), 'w'), indent=1, default=str)
    L = [f'# Test run report ({backend} backend)', '']
    if backend == 'mock':
        L += ['**Mock backend: no model was called. Every model stage used a heuristic stand-in, so these numbers test the plumbing, not the investigator.**', '']
    c = out['counts']
    L += ['## What the store holds', '', ' | '.join(f'{k}: {v}' for k, v in c.items() if k != 'checker'), '',
          f"Checker verdicts: {c['checker']}", '']
    L += ['## Planted cascades', '', '| plant | difficulty | layer (found) | plant saves in best cluster | other saves in it | clusters touched | events found | role correct | source correct | depth ok |',
          '|---|---|---|---|---|---|---|---|---|---|']
    for p in P:
        ev = p['events']
        src = [e['source_ok'] for e in ev if e['source_ok'] is not None]
        L.append(f"| {p['plant_id']} | {p['difficulty']} | {p['layer']} ({p['cluster_layer']}) | {p['plant_msgs_in_cluster']}/{p['plant_msgs']} | "
                 f"{p['other_msgs_in_cluster']} | {p['split_across_clusters']} | {sum(e['found'] for e in ev)}/{len(ev)} | "
                 f"{sum(e['role_ok'] for e in ev)}/{len(ev)} | {sum(src)}/{len(src)} | {sum(e['depth_ok'] for e in ev)}/{len(ev)} |")
    if P:
        allev = [e for p in P for e in p['events']]
        L += ['', f"Overall strict recall (found with the right role): {sum(e['found'] and e['role_ok'] for e in allev)}/{len(allev)}.", '']
    L += ['## The four README cases (candidates, not truth)', '']
    for k, v in out['readme_cases'].items():
        L.append(f'- **{k}**: ' + json.dumps(v, default=str))
    r = out['readers']
    L += ['', '## Readers', '', f"Coverage {r['saves_with_records']}/{r['core_saves']} core saves; gaps {r['gaps']}; "
          f"ACCESS_WORKAROUND segments {r['aw_segments']}; re-verify wrote {r['v2_records']} version-2 records "
          f"({r['v2_purpose_changed']} changed primary purpose). Saves with records before Jun 18: {r['before_jun18']}, from Jun 18: {r['after_jun18']}.", '']
    for seg, s in r['by_segment'].items():
        L.append(f"- {seg}: {s['records']} records read; context {s['context']}; reply_to_unseen gaps {s['reply_to_unseen']}; top purposes {s['purposes']}")
    L += ['', '## Cost', '', '| tier | model | calls | input tok | output tok | cache read | $ |', '|---|---|---|---|---|---|---|']
    for x in out['costs']:
        L.append(f"| {x['tier']} | {x['model']} | {x['calls']} | {x['inp']} | {x['outp']} | {x['cr']} | {x['usd']:.2f} |")
    L += ['', f"Total: ${out['spent_usd']:.2f}" + (' (estimated from prompt sizes; nothing was spent)' if backend == 'mock' else ''), '']
    if stage_stats:
        L += ['## Stage log', '']
        for k, v in stage_stats.items():
            L.append(f'- {k}: {json.dumps(v, default=str)}')
    es = errlog.summary()
    L += ['', '## Errors', '', f"{es['total']} entries in errors.jsonl (failed, retried or split calls; stage exceptions; rejected rows)."]
    L += [f'- {k}: {n}' for k, n in es['by_stage_kind']]
    L += ['', '## Findings (lead, Opus)', '']
    for f in con.execute('SELECT * FROM findings ORDER BY finding_id'):
        L.append(f"- {f['finding_id']} ({f['confidence']}): {f['text']}  supports: {f['supports']}")
    open(os.path.join(C.RUN_DIR, 'report.md'), 'w').write('\n'.join(L) + '\n')
    return out


if __name__ == '__main__':
    main()
