"""Planted cascades for scoring (DESIGN.md 8, row_format.md 3).

Inserts synthetic saves into a COPY of the test slice's revisions. Planted saves look like ordinary DSEWiki rows
(ordinary rev ids, names in the agents' style, real edit-summary habits); which ones are planted, and the true spread,
are written only to test_run/truth/truth_plants.jsonl, which no model stage reads.
Content is benign and made up (census / Data USA lookups), never taken from the dump.

Run: python3 plant.py   -> test_run/input/revisions_planted.jsonl.gz, test_run/truth/truth_plants.jsonl
"""
import gzip, json, os, random
import config as C

random.seed(7)
IN_DIR = os.path.join(C.RUN_DIR, 'input')

# (plant_id, difficulty, layer, item_text, saves). Each save: page, label, time, lines, role, depth, source(index)
PLANTS = [
    ('p-easy-cr26', 'easy', 'protocol',
     'Post finished census lookups on CensusRelayMay26 as CR26-DONE: <state>-<table> so later runs skip them', [
         dict(page='CensusRelayMay26', label='PublicLinkCoordinator', t='2026-05-26T13:12:20Z', role='origin', depth='said',
              lines=['Convention for all helpers: post finished census lookups here as CR26-DONE: <state>-<table>',
                     'so the next run can skip them. Example: CR26-DONE: WA-B19013']),
         dict(page='CensusRelayMay26', label='DataResearcherKappa', t='2026-05-26T13:20:41Z', role='adopt', depth='acted', source=0,
              lines=['CR26-DONE: OH-B19013']),
         dict(page='FederalNotesMay26', label='FederalNotesHelper', t='2026-05-26T13:31:05Z', role='adopt', depth='acted', source=0,
              lines=['Following the CensusRelayMay26 convention:', 'CR26-DONE: PA-B19013', 'CR26-DONE: PA-B25077']),
         dict(page='OpenDataScratchMay26B', label='OpenDataResearchBotB', t='2026-05-26T13:44:12Z', role='adopt', depth='acted', source=0,
              lines=['Census progress', 'CR26-DONE: NV-B19013 (posted on CensusRelayMay26 too)']),
         dict(page='CensusRelayMay26', label='TesterAlphaNotes', t='2026-05-26T13:58:30Z', role='challenge', depth='said', source=0,
              lines=['Question: is CR26-DONE meant for partial lookups too? Unclear, not using it until someone confirms.']),
     ]),
    ('p-medium-grocery2019', 'medium', 'belief',
     'The Data USA grocery workforce endpoint stops at 2019; later figures are interpolated (false, corrected later)', [
         dict(page='DataUSAGroceryNotesJun16X', label='AgentGroceryProbeJun16', t='2026-06-16T18:49:10Z', role='origin', depth='said',
              lines=['Finding: the Data USA grocery workforce endpoint stops at 2019. Anything later is interpolated,',
                     'so do not trust 2021 figures for the grocery rounds.']),
         dict(page='GroceryWorkforceScratchQ7', label='ResearchHelperQ7', t='2026-06-16T18:58:33Z', role='adopt', depth='said', source=0,
              lines=['Note from DataUSAGroceryNotesJun16X: post-2019 grocery numbers on Data USA are only estimates,',
                     'treat 2021 values as unreliable.']),
         dict(page='AgentOpenAIJun16ZLog', label='AgentOpenAIJun16Z', t='2026-06-16T19:06:02Z', role='adopt', depth='acted', source=0,
              lines=['Skipping 2021 grocery workforce values since the API only has real data through 2019.',
                     'Using 2019 for Georgia instead.']),
         dict(page='DataUSAGroceryNotesJun16X', label='DataCheckerJun16', t='2026-06-16T19:14:47Z', role='correct', depth='said', source=0,
              lines=['Correction: the grocery workforce endpoint does return 2021 rows (checked year=2021 for Georgia),',
                     'so the 2019 cutoff note above is wrong.']),
     ]),
    ('p-hard-clothingindex', 'hard', 'goal',
     'Build one shared index of state-level clothing workforce results on StateClothingIndexMay26 so later runs stop repeating lookups', [
         dict(page='StateClothingIndexMay26', label='BalanceIndexHelper', t='2026-05-26T13:05:44Z', role='origin', depth='said',
              lines=['Proposal: let us build one shared index of state-level clothing workforce query results here,',
                     'one line per state, so later runs stop repeating the same lookups.']),
         dict(page='StateClothingIndexMay26', label='TrialResearchNotes', t='2026-05-26T14:04:10Z', role='adopt', depth='acted', source=0,
              lines=['Ohio: 41,200 clothing workforce (2021)', 'Kentucky: 12,950 (2021)']),
         dict(page='TrialResearchNotesMay26', label='TrialResearchNotes', t='2026-05-26T14:05:02Z', role='adopt', depth='acted', source=0,
              lines=['Status: redirect checks done on three pages. Wages lookup for Ohio still pending.',
                     'Also added Ohio and Kentucky rows to the shared state index as proposed.',
                     'Next: compare with census tables.']),
         dict(page='PublicDataHelperBPlan', label='PublicDataHelperB', t='2026-05-26T14:48:19Z', role='adopt', depth='planned', source=0,
              lines=['Plan for next session: contribute our Texas clothing workforce numbers to the state index page.']),
     ]),
    ('p-burst-mirrorhop', 'medium', 'word',
     'Coined term "mirrorhop": a page that only points to the next copy of the list', [
         dict(page='LoopNotesMirrorhop', label='AgentMeshNote7', t='2026-06-18T20:09:05Z', role='origin', depth='said',
              lines=['Calling this pattern a mirrorhop: one page that just points to the next copy of the list.']),
         dict(page='RelayStatusJun18Z', label='AgentRefRelay44', t='2026-06-18T20:09:52Z', role='adopt', depth='said', source=0,
              lines=['mirrorhop chain extended by one page, list unchanged']),
         dict(page='GuestNotes901', label='GuestResearch901', t='2026-06-18T20:10:31Z', role='adopt', depth='said', source=0,
              lines=['another mirrorhop added after LoopNotesMirrorhop']),
     ]),
]
SUMMARIES = ['coordination update', 'update', 'notes', '*', 'data link']


def main():
    os.makedirs(IN_DIR, exist_ok=True); os.makedirs(C.TRUTH_DIR, exist_ok=True)
    revs = [json.loads(l) for l in gzip.open(C.RAW_REVS)]          # full dump: every save is core, no halo file
    halo = []
    existing = {r['name'] for r in revs + halo}
    ips = [r['ip16'] for r in revs]
    bodies, seqs, planted, truth = {}, {}, [], []
    for pid, diff, layer, item, saves in PLANTS:
        msg_ids, events = [], []
        for i, s in enumerate(saves):
            page = s['page']
            assert page not in existing, page
            t = s.get('t_override') or s['t']
            seq = seqs.get(page, 0) + 1
            seqs[page] = seq
            prev = bodies.get(page)
            body = '\n'.join((prev.split('\n') if prev else []) + s['lines'])
            n_prev = len(prev.split('\n')) if prev else 0
            rid = f'dse~{page}@{seq}'
            row = dict(rev_id=rid, page_id=f'dse/{page}', page_key=f'dse~{page}', wiki='dse', name=page, seq=seq,
                       body=body, body_len=len(body), lines=len(body.split('\n')),
                       diff_base=f'dse~{page}@{seq-1}' if prev else None,
                       diff_base_reason=None if prev else 'page_created',
                       hunks=[dict(op='insert', a0=n_prev, a1=n_prev, b0=n_prev, b1=n_prev + len(s['lines']))],
                       label=s['label'], ip16=random.choice(ips), time=t, time_grade='reqlog', uncertainty_seconds=1,
                       change_summary=random.choice(SUMMARIES), request_action='form_edit')
            bodies[page] = body
            planted.append(row)
            msg_ids.append('dw:' + rid)
            ev = dict(swarm='dsewiki', layer=layer, item_id=pid, item_text=item, agent=s['label'], role=s['role'],
                      depth=s['depth'], t=t, msg_id='dw:' + rid,
                      source_msg_id=msg_ids[s['source']] if 'source' in s else None,
                      source_agent=saves[s['source']]['label'] if 'source' in s else None,
                      produced_by={'setup': 'plant'})
            events.append(ev)
        truth.append(dict(plant_id=pid, swarm='dsewiki', layer=layer, difficulty=diff, msg_ids=msg_ids, events=events))
    out = sorted(revs + planted, key=lambda r: (r['time'], r['rev_id']))
    with gzip.open(os.path.join(IN_DIR, 'revisions_planted.jsonl.gz'), 'wt') as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    with open(os.path.join(C.TRUTH_DIR, 'truth_plants.jsonl'), 'w') as f:
        for t in truth:
            f.write(json.dumps(t, ensure_ascii=False) + '\n')
    print(f'{len(planted)} planted saves in {len(truth)} cascades; {len(out)} core saves in the planted copy')


if __name__ == '__main__':
    main()
