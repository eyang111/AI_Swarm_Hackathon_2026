"""Compare the Swarm Atlas (baseline) with the Swarm Investigator on DSEWiki.

Both ran over the same DSEWiki dump (May 24 to Jul 2 2026). Everything here is computed from files already in the
repo; no raw data and no API calls are needed.

  python3 comparisons/atlas-vs-investigator/compare.py                       # metrics -> results.json
  python3 comparisons/atlas-vs-investigator/compare.py --build-judge-inputs  # rebuild judging/ inputs

Run from the repository root. Python 3.10+, standard library only.
"""
import argparse, collections, glob, json, math, os, random, re
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ATLAS_EPISODES = 'swarm-atlas/final/episodes.jsonl'
ATLAS_RECALL = 'swarm-atlas/recall/recall_av_dw.json'
ATLAS_RAW = 'swarm-atlas/sweep/raw/dsewiki_{}.jsonl'
INV_TIMELINE = 'runs/2026-10-04-full-run/timeline.json'
INV_SCORES = 'runs/2026-10-04-full-run/scores.json'
INV_REPORT = 'runs/2026-10-04-full-run/report.md'
JUDGE_DIR = os.path.join(HERE, 'judging')


def ts(s):
    return datetime.fromisoformat(s.replace('Z', '').replace('T', ' ')[:19])


def page_key(p):
    """'dse~Page' (investigator) and 'dse:Page' (atlas recall units) -> 'dse:Page'."""
    return p.replace('~', ':', 1)


def load():
    eps = [json.loads(l) for l in open(ATLAS_EPISODES)]
    dw = [e for e in eps if e['dataset'] == 'dsewiki']
    for e in dw:
        sel = e['selector']
        pr = sel.get('page_regex')
        # inline (?i) flags mid-pattern are an error on Python 3.11+; match case-insensitively instead
        e['_rx'] = re.compile(pr.replace('(?i)', ''), re.I) if pr else None
        e['_s'], e['_e'] = ts(e['start']), ts(e['end'])
    units = [u for u in json.load(open(ATLAS_RECALL)) if u['dataset'] == 'dsewiki']
    tl = json.load(open(INV_TIMELINE))
    items = collections.OrderedDict()
    for n in tl['nodes']:
        c = items.setdefault(n['cluster'], dict(id=n['cluster'], layer=n['layer'], text=n['text'], nodes=[], members=[],
                                                editors=set(), copying=set(), roles=collections.Counter()))
        c['nodes'].append(n)
        if n.get('copying'):
            c['copying'].add(n['copying'])
        for m in n['members']:
            c['members'].append(m)
            c['editors'].add(m['editor'])
            c['roles'][m.get('role')] += 1
    by_page = collections.defaultdict(list)
    for cid, c in items.items():
        for m in c['members']:
            by_page[page_key(m['page'])].append((ts(m['t']), cid))
    scores = json.load(open(INV_SCORES))
    return dw, units, items, by_page, tl['edges'], scores


def ep_covers(e, page, strict=False):
    """Does atlas episode e name this page? strict = explicit page list only (no regex)."""
    sel = e['selector']
    wiki, name = page.split(':', 1)
    if sel.get('wiki') not in (None, 'all', '*', wiki):
        return False
    if name in (sel.get('pages') or []):
        return True
    return (not strict) and bool(e['_rx'] and e['_rx'].search(name))


def short(item_id):
    """'met-612-some-slug' -> 'met-612'. Unique per item; keeps item text out of the committed judging files."""
    return '-'.join(item_id.split('-')[:2])


def pct(a, b):
    return round(100.0 * a / b, 1) if b else None


# ---------------------------------------------------------------- metrics

def plants(scores):
    ev = [x for p in scores['plants'] for x in p['events']]
    src = [x for x in ev if x['source_ok'] is not None]
    return dict(
        cascades=len(scores['plants']),
        events=len(ev),
        found_right_role=sum(1 for x in ev if x['found'] and x['role_ok']),
        source_correct=sum(1 for x in src if x['source_ok']), source_scored=len(src),
        clean_clusters=sum(1 for p in scores['plants'] if p['other_msgs_in_cluster'] == 0 and p['split_across_clusters'] == 1),
        atlas='not testable: the Atlas never ran on the planted copy, and the raw dump is not in the repo',
        test_slice_run='14/16 (runs/2026-10-04-test-slice/report.md on branch claude/test-slice-run-report)')


def coverage(dw, units, items, by_page):
    rows = []
    for u in units:
        first, last = ts(u['first']), ts(u['last'])
        atlas_pub = bool(u['covered_by'])
        atlas = any(ep_covers(e, u['unit']) and e['_s'] <= last and e['_e'] >= first for e in dw)
        hits = by_page.get(u['unit'], [])
        inv = bool(hits)
        rows.append(dict(unit=u['unit'], score=u['score'], atlas_published=atlas_pub, atlas=atlas, investigator=inv))
    tot = sum(r['score'] for r in rows)
    top = sorted(rows, key=lambda r: -r['score'])[:65]
    out = dict(units=len(rows), definition='DSEWiki pages edited by 3+ agent handles (the Atlas recall check)')
    for k in ('atlas_published', 'atlas', 'investigator'):
        n = sum(r[k] for r in rows)
        out[k] = dict(covered=n, pct=pct(n, len(rows)),
                      score_weighted_pct=round(100 * sum(r['score'] for r in rows if r[k]) / tot, 1),
                      top65_covered=sum(r[k] for r in top))
    out['both'] = sum(1 for r in rows if r['atlas'] and r['investigator'])
    out['atlas_only'] = sum(1 for r in rows if r['atlas'] and not r['investigator'])
    out['investigator_only'] = sum(1 for r in rows if r['investigator'] and not r['atlas'])
    out['neither'] = sum(1 for r in rows if not r['atlas'] and not r['investigator'])
    out['top_missed_by_atlas'] = [r['unit'] for r in top if not r['atlas']]
    out['top_missed_by_investigator'] = [r['unit'] for r in top if not r['investigator']]
    return out


def page_overlap(dw, items, by_page, edges, plant_ids):
    """Lenient agreement: do the two systems point at the same pages in the same time span?"""
    def inv_touch(e, strict):
        for page, lst in by_page.items():
            if ep_covers(e, page, strict) and any(e['_s'] <= t <= e['_e'] and len(items[c]['editors']) >= 2 for t, c in lst):
                return True
        return False

    def atlas_touch(cid, eps, strict):
        for m in items[cid]['members']:
            p, t = page_key(m['page']), ts(m['t'])
            if any(e['_s'] <= t <= e['_e'] and ep_covers(e, p, strict) for e in eps):
                return True
        return False

    no_umbrella = [e for e in dw if e['id'] != 'DW-UMBRELLA-01']
    spread = [c for c in items if len(items[c]['editors']) >= 2 and c not in plant_ids]
    edge_items = sorted({x.split('#')[0] for e in edges for x in (e['source'], e['target'])} & set(items))
    return dict(
        atlas_episodes_touched=dict(lenient=sum(inv_touch(e, False) for e in dw), strict=sum(inv_touch(e, True) for e in no_umbrella),
                                    of_lenient=len(dw), of_strict=len(no_umbrella)),
        investigator_spread_items_touched=dict(lenient=sum(atlas_touch(c, dw, False) for c in spread),
                                               strict=sum(atlas_touch(c, no_umbrella, True) for c in spread), of=len(spread)),
        investigator_linked_items_touched=dict(strict=sum(atlas_touch(c, no_umbrella, True) for c in edge_items), of=len(edge_items)),
        note='strict = explicit page list only, umbrella episode excluded; lenient = page list or page regex')


def evidence(dw, items, scores):
    km = [m for e in dw for m in e['key_messages']]
    roles = collections.Counter()
    for c in items.values():
        roles.update(c['roles'])
    st = scores['stages']
    return dict(
        atlas=dict(episodes=len(dw), key_quotes=len(km), quote_roles=dict(collections.Counter(m.get('role') for m in km)),
                   cited_by='timestamp + speaker; quotes checked against raw revisions after the run',
                   quotes_per_finding=round(len(km) / len(dw), 1)),
        investigator=dict(items=len(items), member_rows=sum(len(c['members']) for c in items.values()),
                          distinct_saves_cited=len({m['msg_id'] for c in items.values() for m in c['members']}),
                          events=scores['counts']['events'], roles={k or 'none': v for k, v in roles.items()},
                          causal_links=st['l4']['links_ok'], copy_links=st['l4']['copy_links'], cross_item_edges=st['l5']['edges'],
                          cited_by='save id (msg_id); every quote checked as an exact substring when it is written',
                          saves_per_item=round(len({m['msg_id'] for c in items.values() for m in c['members']}) / len(items), 1)))


def report_numbers():
    """Figures the lead wrote into the full-run report (overview and finding F08)."""
    txt = open(INV_REPORT).read()
    chance = re.search(r'(\d+) of (\d+) items with enough members were more connected than chance', txt)
    stops = re.search(r'(\d+) are still alive at the end of the data, (\d+) were corrected and (\d+) challenged, '
                      r'and the store counts (\d+) adoptions', txt)
    return dict(more_than_chance=int(chance.group(1)), chance_tested=int(chance.group(2)),
                stopping_points=dict(alive=int(stops.group(1)), corrected=int(stops.group(2)), challenged=int(stops.group(3)),
                                     adoptions_after_correction=int(stops.group(4))))


def measurements(dw, items, scores):
    st = scores['stages']
    rn = report_numbers()
    bel = [c for c in items.values() if c['layer'] == 'belief']
    atlas_belief = [e for e in dw if re.search(r'belief|guess|false|corrected|misread|hypothes|dispute', e['title'], re.I)]
    return dict(
        investigator=dict(copying_verdicts=st['l4']['analyzed'], chance_baseline_items=st['script_analyzers']['baseline_clusters'],
                          more_than_chance=rn['more_than_chance'], routes=st['script_analyzers']['routes'],
                          belief_items=len(bel), belief_items_challenged_or_corrected=sum(1 for c in bel if c['roles']['correct'] or c['roles']['challenge']),
                          stopping_points=rn['stopping_points'],
                          run_groups=scores['counts']['run_groups']),
        atlas=dict(belief_episodes=len(atlas_belief), episodes_with_correction_quotes=sum(1 for e in dw if any(m.get('role') == 'correction' for m in e['key_messages'])),
                   swarm_levels=dict(collections.Counter(e['level'] for e in dw)), consequence=dict(collections.Counter(e['consequence'] for e in dw)),
                   copying_vs_chance='not measured', routes='not measured'))


def stability(dw, scores):
    raw = {}
    for k in (1, 2, 3):
        for l in open(ATLAS_RAW.format(k)):
            if l.strip():
                x = json.loads(l)
                raw[x['id']] = x
    common = [e for e in dw if e['id'] in raw]
    changed = [e for e in common if raw[e['id']].get('level') != e['level']]
    ch = scores['counts']['checker']
    return dict(
        atlas=dict(raw_episodes=len(raw), final_episodes=len(dw), traceable=len(common), level_changed=len(changed),
                   level_changed_pct=pct(len(changed), len(common)),
                   moves=collections.Counter(f"{raw[e['id']].get('level')}->{e['level']}" for e in changed).most_common(),
                   note='most changes came from re-aligning the rules to the source post, not from fixing reading errors',
                   earlier_vet_av_moltbook=dict(claims=566, confirmed=351, partly_right=173, wrong=30, unchecked=12)),
        investigator=dict(checked_links=sum(ch.values()), accepted=ch['accept'], corrected=ch['correct'], rejected=ch['reject'],
                          changed_pct=pct(ch['correct'] + ch['reject'], sum(ch.values())),
                          note='checker and lead were done by hand by Claude in the project thread (manual backend)'))


def cost(scores):
    used = [c for c in scores['costs'] if c['tier'] != 'reader_unused']
    return dict(investigator_usd=round(scores['spent_usd'], 2),
                investigator_usd_excluding_cancelled_batch=round(sum(c['usd'] for c in used), 2),
                investigator_model_calls=sum(c['calls'] for c in used if not c['model'].startswith('manual')),
                atlas_usd='not recorded',
                atlas_dsewiki_agents='3 sweep agents (one per time slice), then consistency, alignment and recall-gap passes')


# ---------------------------------------------------------------- blind judging

def judged(dw, items, plant_ids):
    """Aggregate the blind judges' verdicts (judging/out/*.json).

    The four planted cascades exist only in the Investigator's copy of the data, so they are left out of the
    Investigator -> Atlas direction (the Atlas never saw them)."""
    out = {}
    level = {e['id']: e['level'] for e in dw}
    items = {short(k): v for k, v in items.items()}
    plant_ids = {short(k) for k in plant_ids}
    for d, name in (('A', 'atlas_episodes_found_by_investigator'), ('B', 'investigator_items_found_by_atlas')):
        j1 = {}
        j2 = {}
        for f in sorted(glob.glob(os.path.join(JUDGE_DIR, 'out', f'{d}*_j1.json'))):
            j1.update({x['id']: x['verdict'] for x in json.load(open(f)) if x['id'] not in plant_ids})
        for f in sorted(glob.glob(os.path.join(JUDGE_DIR, 'out', f'{d}*_j2.json'))):
            j2.update({x['id']: x['verdict'] for x in json.load(open(f)) if x['id'] not in plant_ids})
        if not j1:
            continue
        c = collections.Counter(j1.values())
        res = dict(judged=len(j1), match=c['match'], partial=c['partial'], none=c['none'],
                   match_pct=pct(c['match'], len(j1)), match_or_partial_pct=pct(c['match'] + c['partial'], len(j1)))
        if d == 'A':
            res['by_swarm_level'] = {lv: dict(collections.Counter(v for k, v in j1.items() if level[k] == lv))
                                     for lv in sorted(set(level.values()))}
        else:
            res['plants_excluded'] = len(plant_ids)
            buckets = (('2-4 editors', 2, 4), ('5-9 editors', 5, 9), ('10+ editors', 10, 10 ** 9))
            res['by_size'] = {b: dict(collections.Counter(v for k, v in j1.items() if lo <= len(items[k]['editors']) <= hi))
                              for b, lo, hi in buckets}
            res['by_layer'] = {l: dict(collections.Counter(v for k, v in j1.items() if items[k]['layer'] == l))
                               for l in sorted({items[k]['layer'] for k in j1})}
        both = [k for k in j2 if k in j1]
        if both:
            agree = sum(1 for k in both if j1[k] == j2[k])
            labels = ('match', 'partial', 'none')
            pa = agree / len(both)
            pe = sum((sum(1 for k in both if j1[k] == l) / len(both)) * (sum(1 for k in both if j2[k] == l) / len(both)) for l in labels)
            res['double_judged'] = len(both)
            res['agreement_pct'] = pct(agree, len(both))
            res['cohen_kappa'] = round((pa - pe) / (1 - pe), 2) if pe < 1 else None
            res['match_pct_judge2'] = pct(sum(1 for k in both if j2[k] == 'match'), len(both))
            res['match_pct_judge1_same_entries'] = pct(sum(1 for k in both if j1[k] == 'match'), len(both))
        out[name] = res
    return out


def build_judge_inputs(dw, items, by_page):
    """Blind catalogs for the judges: E = Atlas episodes, I = Investigator items. Neither is labelled."""
    os.makedirs(JUDGE_DIR, exist_ok=True)
    E = [dict(id=e['id'], title=e['title'], start=e['start'], end=e['end'], pages=(e['selector'].get('pages') or [])[:25],
              page_pattern=e['selector'].get('page_regex'), summary=e['summary'],
              key_quotes=[f"[{m['ts']}] {m['speaker']} ({m.get('role')}): {m['quote']}" for m in e['key_messages']][:20],
              notes=(e.get('level_rationale') or '')[:600]) for e in dw]
    I = []
    for cid, c in items.items():
        pages = collections.Counter(m['page'] for m in c['members'])
        I.append(dict(id=short(cid), kind=c['layer'], text=c['text'], t_first=min(n['t_first'] for n in c['nodes']),
                      t_last=max(n['t_last'] for n in c['nodes']), saves=len({m['msg_id'] for m in c['members']}),
                      editors=len(c['editors']), top_pages=[p for p, _ in pages.most_common(6)],
                      phases=[n['phase'] for n in c['nodes'] if n.get('phase')],
                      analysis=' | '.join(n['account'] for n in c['nodes'] if n.get('account'))[:700],
                      member_summaries=list(dict.fromkeys(m['summary'] for m in c['members'] if m.get('summary')))[:6]))
    json.dump(E, open(os.path.join(JUDGE_DIR, 'catalog_E.json'), 'w'), indent=0)
    json.dump(I, open(os.path.join(JUDGE_DIR, 'catalog_I.json'), 'w'), indent=0)

    def inv_cands(e):
        cnt = collections.Counter()
        for page, lst in by_page.items():
            if ep_covers(e, page):
                cnt.update(c for t, c in lst if e['_s'] <= t <= e['_e'])
        return [short(c) for c, _ in cnt.most_common(40)]

    def atlas_cands(cid):
        cnt = collections.Counter()
        for m in items[cid]['members']:
            p, t = page_key(m['page']), ts(m['t'])
            cnt.update(e['id'] for e in dw if e['_s'] <= t <= e['_e'] and ep_covers(e, p))
        return [x for x, _ in cnt.most_common(12)]

    A = [dict(episode_id=e['id'], candidate_item_ids=inv_cands(e)) for e in dw]
    B = [dict(item_id=short(c), candidate_episode_ids=atlas_cands(c)) for c in sorted(c for c in items if len(items[c]['editors']) >= 2)]
    random.seed(11)
    random.shuffle(A)
    random.shuffle(B)
    for k in range(3):
        json.dump(A[k::3], open(os.path.join(JUDGE_DIR, f'A_batch{k}.json'), 'w'), indent=0)
    for k in range(8):
        json.dump(B[k::8], open(os.path.join(JUDGE_DIR, f'B_batch{k}.json'), 'w'), indent=0)
    print(f'wrote judge inputs to {JUDGE_DIR}: {len(A)} episodes in 3 batches, {len(B)} items in 8 batches')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--build-judge-inputs', action='store_true')
    a = ap.parse_args()
    dw, units, items, by_page, edges, scores = load()
    if a.build_judge_inputs:
        build_judge_inputs(dw, items, by_page)
        return
    res = dict(
        scope='DSEWiki only, the one dataset both systems ran on',
        planted_truth=plants(scores),
        coverage=coverage(dw, units, items, by_page),
        page_overlap=page_overlap(dw, items, by_page, edges, {p['cluster'] for p in scores['plants']}),
        judged_cross_recall=judged(dw, items, {p['cluster'] for p in scores['plants']}),
        evidence=evidence(dw, items, scores),
        measurements=measurements(dw, items, scores),
        stability_under_review=stability(dw, scores),
        cost=cost(scores))
    json.dump(res, open(os.path.join(HERE, 'results.json'), 'w'), indent=1, default=list)
    print(json.dumps(res, indent=1, default=list))


if __name__ == '__main__':
    main()
