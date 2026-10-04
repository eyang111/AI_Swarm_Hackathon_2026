"""Run-wide error log: one JSON line per problem in test_run/errors.jsonl, from any stage.

Use it anywhere something goes wrong but the run carries on (a failed or partial model call, a rejected row, a
stage exception), so failures are visible after the run instead of only as a count in stage_log.json:

    import errlog
    errlog.log('reverify', 'revise_rejected', 'record failed validation', msg_id=m, reason=why)

`stage` is the pipeline stage or model tier, `kind` a short slug to group by, `detail` one human-readable line;
any keyword arguments are stored as context. score.py summarises the file in report.md. Never put raw wiki text
from an ACCESS_WORKAROUND span in `detail` or the context.
"""
import collections, json, os, threading, time, traceback as tb
import config as C

_lock = threading.Lock()


def path():
    return os.path.join(C.RUN_DIR, 'errors.jsonl')


def log(stage, kind, detail, exc=None, **ctx):
    row = dict(t=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), stage=stage, kind=kind, detail=str(detail)[:1000])
    if exc is not None:
        row['exception'] = repr(exc)[:1000]
        row['traceback'] = ''.join(tb.format_exception(type(exc), exc, exc.__traceback__))[-3000:]
    if ctx:
        row['context'] = ctx
    with _lock:
        os.makedirs(C.RUN_DIR, exist_ok=True)
        with open(path(), 'a') as f:
            f.write(json.dumps(row, ensure_ascii=False, default=str) + '\n')
    return row


def reset():
    """Called at the start of a fresh run (from the plant stage); a resumed run (--from) appends."""
    with _lock:
        if os.path.exists(path()):
            os.remove(path())


def read():
    if not os.path.exists(path()):
        return []
    with open(path()) as f:
        return [json.loads(l) for l in f if l.strip()]


def summary():
    rows = read()
    return dict(total=len(rows), by_stage_kind=collections.Counter(f"{r['stage']}/{r['kind']}" for r in rows).most_common())
