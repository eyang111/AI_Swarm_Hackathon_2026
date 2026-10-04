"""Run the whole Swarm Investigator pipeline on the test slice (DESIGN.md 3 / 5.4 order).

  python3 run.py --backend mock                         # offline end-to-end test, prints a cost estimate
  python3 run.py --backend anthropic --budget 25        # the real run (needs ANTHROPIC_API_KEY)
  python3 run.py --backend anthropic --from groupers    # resume from a stage on the existing db

Outputs in test_run/ (or $SI_RUN_DIR): investigation.db, report.md, scores.json, timeline.json/.html, calls/, stage_log.json.
"""
import argparse, json, os, sys, time
import config as C

STAGES = ['plant', 'load', 'windows', 'readers', 'keyword_df', 'local_linker', 'conversations', 'pregroup',
          'identity', 'groupers', 'reconciler', 'l4', 'l5', 'script_analyzers', 'checker', 'lead',
          'timeline', 'score']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--backend', choices=['mock', 'anthropic', 'manual'], default='mock')
    ap.add_argument('--budget', type=float, default=25.0, help='stop before a stage would push spend past this ($)')
    ap.add_argument('--from', dest='start', default='plant', choices=STAGES)
    ap.add_argument('--to', dest='stop', default='score', choices=STAGES)
    ap.add_argument('--run-id', default=None)
    ap.add_argument('--batch-all', action='store_true', help='Batch API for every tier (half price, slower)')
    a = ap.parse_args()
    if a.backend == 'anthropic' and not (os.environ.get('ANTHROPIC_API_KEY') or os.environ.get('SI_ANTHROPIC_API_KEY')) \
            and not os.environ.get('SI_FAKE_API'):
        sys.exit('No API key: set ANTHROPIC_API_KEY or SI_ANTHROPIC_API_KEY in the project environment settings.')
    import plant, load, window_plan, store, llm, readers, pregroup, local_linker, cluster, identity, groupers, \
        analyzers, timeline, score, errlog
    os.makedirs(C.RUN_DIR, exist_ok=True)
    log_path = os.path.join(C.RUN_DIR, 'stage_log.json')
    log = json.load(open(log_path)) if a.start != 'plant' and os.path.exists(log_path) else {}
    run_id = a.run_id or log.get('_run_id') or time.strftime('run-%m%d-%H%M')
    log['_run_id'], log['_backend'] = run_id, a.backend
    todo = STAGES[STAGES.index(a.start):STAGES.index(a.stop) + 1]
    con = L = None

    def ready():
        nonlocal con, L
        if con is None:
            con = store.connect()
            store.new_run(con, run_id, dict(backend=a.backend, models=C.TIER_MODEL, budget=a.budget, plants=True))
            L = llm.LLM(con, run_id, a.backend, a.budget, batch_all=a.batch_all)
        return con, L
    steps = {
        'plant': lambda: plant.main(),
        'load': lambda: load.main(),
        'windows': lambda: window_plan.main(),
        'readers': lambda: readers.run(*ready(), run_id),
        'keyword_df': lambda: pregroup.keyword_df(ready()[0]),
        'local_linker': lambda: local_linker.run(*ready(), run_id),
        'conversations': lambda: cluster.run(*ready(), run_id),
        'pregroup': lambda: pregroup.candidates(ready()[0], run_id),
        'identity': lambda: identity.run(*ready(), run_id),
        'groupers': lambda: groupers.run(*ready(), run_id),
        'reconciler': lambda: groupers.reconcile(*ready(), run_id),
        'l4': lambda: analyzers.run_l4(*ready(), run_id),
        'l5': lambda: analyzers.run_l5(*ready(), run_id),
        'script_analyzers': lambda: analyzers.script_analyzers(ready()[0], run_id),
        'checker': lambda: analyzers.run_checker(*ready(), run_id),
        'lead': lambda: analyzers.run_lead(*ready(), run_id),
        'timeline': lambda: timeline.main(),
        'score': lambda: score.main({k: v for k, v in log.items() if not k.startswith('_')}, a.backend) and 'written',
    }
    for st in todo:
        if st in ('load',):          # load rebuilds the db: drop any open handle first
            if con is not None:
                con.close(); con = L = None
        t0 = time.time()
        print(f'== {st}', flush=True)
        if st == 'plant':
            errlog.reset()
        try:
            out = steps[st]()
        except llm.BudgetExceeded as e:
            print(f'STOPPED before {st}: {e}', flush=True)
            log[st] = {'stopped': str(e)}
            json.dump(log, open(log_path, 'w'), indent=1, default=str)
            errlog.log(st, 'budget_stop', str(e))
            sys.exit(2)
        except Exception as e:
            errlog.log(st, 'stage_exception', f'{st} crashed; resume with --from {st}', exc=e)
            log[st] = {'crashed': repr(e)[:300]}
            json.dump(log, open(log_path, 'w'), indent=1, default=str)
            raise
        spent = store.spent(con) if con is not None else 0
        log[st] = dict(out) if isinstance(out, dict) else out
        if isinstance(log[st], dict):
            log[st]['_secs'] = round(time.time() - t0, 1)
            log[st]['_spent_total'] = round(spent, 3)
        print(f'   {json.dumps(log[st], default=str)[:600]}', flush=True)
        json.dump(log, open(log_path, 'w'), indent=1, default=str)
        if con is not None:              # full run: closed snapshot after every stage (the live db may not survive a restart)
            con.commit()
            bk = store.sqlite3.connect(os.path.join(C.RUN_DIR, 'investigation.snapshot.db'))
            con.backup(bk); bk.close()
    if con is not None:
        print(f'total model spend: ${store.spent(con):.2f}' + (' (mock estimate)' if a.backend == 'mock' else ''))


if __name__ == '__main__':
    main()
