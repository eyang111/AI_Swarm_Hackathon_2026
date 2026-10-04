"""Readable run summary (top of report.md, and summary.md): findings by category and a chronological account.

Built by script from the store, no model calls and no raw JSON. The full report (scores, costs, stage log, raw
findings with their support ids) stays below it in report.md as background, and investigation.db keeps everything.
Item names that look like a host name or mention a proxy are withheld (safety rule: never describe access workarounds).
"""
import collections, json, re
import config as C

CATEGORIES = ['spread routes', 'beliefs and predictions', 'goals and coordination', 'conventions and protocols',
              'methods and resources', 'coined words and markers', 'who spread it', 'limits and caveats']
TITLES = {'spread routes': 'How ideas moved', 'beliefs and predictions': 'Beliefs and predictions',
          'goals and coordination': 'Goals and coordination requests', 'conventions and protocols': 'Conventions and protocols',
          'methods and resources': 'Methods and resources (queries, link lists)', 'coined words and markers': 'Coined words and markers',
          'who spread it': 'Who spread it', 'limits and caveats': 'Limits and caveats'}
LAYER_CAT = {'belief': 'beliefs and predictions', 'goal': 'goals and coordination', 'protocol': 'conventions and protocols',
             'method': 'methods and resources', 'word': 'coined words and markers'}
LAYER_NAME = {'belief': 'belief', 'goal': 'goal', 'protocol': 'convention', 'method': 'method', 'word': 'coined word'}
SEGMENT_NAME = {'S1': 'May 26, quiet period', 'S2': 'June 16, start of the burst', 'S3': 'June 18, peak of the burst'}
UNSAFE = re.compile(r'proxy|\bjqp\b|\b[\w-]+\.(app|com|io|net|org|dev|xyz|sh|me|co|at|de|us|uk|gov|info|ai|cc|tk|ru|link|site|online|top|ly|to|gg|pw|ws)\b|\b[\w-]+(\.[\w-]+)*\.[a-z]{2,6}/', re.I)
UNSAFE_PHRASE = re.compile(r'(\b[\w.-]+\s+)?\S*(?:proxy|\bjqp\b)\S*(\s+block\b)?|\S+\.(app|com|io|net|org|dev|xyz|sh|me|co|at|de|us|uk|gov|info|ai|cc|tk|ru|link|site|online|top|ly|to|gg|pw|ws)\b\S*|\S+\.[a-z]{2,6}/\S*', re.I)
TAGS = {'shared_page': 'a shared page', 'direct_message': 'a direct message', 'same_conversation': 'the same conversation',
        'acted_on': 'acted-on', 'before_slice': 'started before the slice', 'in_swarm': 'started in the swarm',
        'task_prompt': 'from the task', 'exposed_to': 'exposed to'}
ITEM_ID = re.compile(r'\b(bel|goa|pro|met|wor)-\d{3}(-[a-z0-9-]+)?\b')


def _plain(text, info):
    """Finding text without raw ids: item ids become their short names, conversation and run-group ids plain words."""
    names = {k[:7]: v['text'] for k, v in info.items()}
    def item(m):
        t = names.get(m.group(0)[:7])
        return f'"{t[:60]}"' if t else 'an item'
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'\s*\((?:%s)(?:,\s*(?:%s))*\)' % (ITEM_ID.pattern, ITEM_ID.pattern), '', text)
    text = ITEM_ID.sub(item, text)
    text = re.sub(r'\bcand\d+_\d+\b(,\s*n=\d+)?', 'a conversation', text)
    text = re.sub(r'\brg0*(\d+)\b', r'run group \1', text)
    text = re.sub(r'\(a conversation(?:[;,] a conversation)+\)', '', text)
    for tag, words in TAGS.items():
        text = re.sub(r'\b%s\b' % tag, words, text)
    return UNSAFE_PHRASE.sub('[access-related item withheld]', text)


def _safe(text, aw=False):
    if aw or UNSAFE.search(text or ''):
        return '(item withheld: access-related link block)'
    return (text or '').strip().rstrip('.')


def _cluster_info(con):
    info = {}
    for ck in con.execute('''SELECT ck.claim_key, ck.layer, ck.canonical_text, n.t_first FROM claim_keys ck
                             JOIN novelty n USING (claim_key) WHERE ck.merged_into IS NULL'''):
        mem = con.execute('SELECT msg_id, speaker, purpose, t FROM live_members WHERE claim_key=?', (ck['claim_key'],)).fetchall()
        aw = any(m['purpose'] == 'ACCESS_WORKAROUND' for m in mem)
        seg = con.execute('SELECT segment FROM messages WHERE msg_id=?', (mem[0]['msg_id'],)).fetchone()[0] if mem else None
        l4 = con.execute("SELECT body FROM analyses WHERE analysis_id=?", ('l4:' + ck['claim_key'],)).fetchone()
        l4 = json.loads(l4[0]) if l4 else {}
        info[ck['claim_key']] = dict(layer=ck['layer'], text=_safe(ck['canonical_text'], aw), t=ck['t_first'], seg=seg,
                                     n=len(mem), editors=len({m['speaker'] for m in mem}),
                                     verdict=(l4.get('copying_vs_convergence') or {}).get('verdict'),
                                     origin=(l4.get('origin_assessment') or {}).get('kind'),
                                     summary=None if aw else l4.get('summary'))
    base = con.execute("SELECT body FROM analyses WHERE analysis_id='copying_baseline'").fetchone()
    for k, b in (json.loads(base[0]) if base else {}).items():
        if k in info and 'reading' in b:
            info[k]['baseline'] = b
    for k in info:
        rej = con.execute('''SELECT COUNT(*) FROM checks ch JOIN links l ON l.link_id = ch.obj_id
                             WHERE ch.obj_type='link' AND ch.verdict='reject' AND l.claim_key=?''', (k,)).fetchone()[0]
        info[k]['rejected_links'] = rej
    return info


def _category(f, info):
    if f['category'] if 'category' in f.keys() else None:
        return f['category']
    sup = json.loads(f['supports'])
    types = collections.Counter(s['type'] for s in sup)
    text = f['text'].lower()
    if types['conversation'] or text.startswith('coverage') or 'baseline' in text or 'before the slice' in text \
            or 'least analysed' in text:
        return 'limits and caveats'
    if types['run_group']:
        return 'who spread it'
    if any(s['type'] == 'analysis' and s['id'] == 'routes' for s in sup):
        return 'spread routes'
    layers = collections.Counter(info[s['id']]['layer'] for s in sup if s['type'] == 'claim_key' and s['id'] in info)
    if layers:
        return LAYER_CAT.get(layers.most_common(1)[0][0], 'limits and caveats')
    return 'spread routes' if types['cluster_edge'] else 'limits and caveats'


STALE_NOTE = {'copying_baseline': 'the copying baseline was fixed and recomputed after this finding was written; the overview has the new numbers.',
              'routes': 'route counts were recomputed after this finding was written, once checker-rejected links were removed.'}


def stale_baseline(con, f):
    """True when the script analyses were recomputed after the lead wrote this finding."""
    r = con.execute('''SELECT b.started_at > l.started_at FROM analyses a JOIN tasks b ON b.task_id = a.task_id, tasks l
                       WHERE a.analysis_id='copying_baseline' AND l.task_id=?''', (f['task_id'],)).fetchone()
    return bool(r and r[0])


def _hm(t):
    return (t or '')[11:16]


def _verdict_words(c):
    bits = []
    v = {'copying': 'copied between agents', 'convergence': 'reached independently', 'mixed': 'partly copied, partly independent'}.get(c['verdict'])
    if v:
        bits.append(v)
    o = {'task_prompt': 'likely from the task itself', 'before_slice': 'started before this slice',
         'external': 'came from outside the wiki', 'in_swarm': 'started inside the swarm here'}.get(c['origin'])
    if o:
        bits.append(o)
    b = c.get('baseline')
    if b:
        bits.append('more connected than chance' if b['reading'].startswith('more') else 'no more connected than chance')
    if c['rejected_links']:
        bits.append(f"checker rejected {c['rejected_links']} of its links")
    return '; '.join(bits)


CHECKED = "SELECT COUNT(*) FROM checks WHERE obj_type IN ('link', 'cluster_edge')"


def build(con, title='Run summary'):
    info = _cluster_info(con)
    L = [f'# {title}', '',
         'Plain-language view of what this run found. These are the pipeline\'s hypotheses, not ground truth. '
         'The full report with scores, costs, the stage log and the raw findings is below under "Background".', '']
    # overview
    q = lambda s: con.execute(s).fetchone()[0]
    n_checked, n_rejected = q(CHECKED), q(CHECKED + " AND verdict='reject'")
    L += ['## Overview', '',
          f"The run read {q('SELECT COUNT(DISTINCT msg_id) FROM records')} wiki saves and grouped what agents said into "
          f"{len(info)} items (beliefs, goals, conventions, methods and coined words). "
          f"{sum(1 for c in info.values() if c.get('baseline', {}).get('reading', '').startswith('more'))} of "
          f"{sum(1 for c in info.values() if c.get('baseline'))} items with enough members were more connected than chance. "
          f"The checker reviewed {n_checked} model-made links and rejected {n_rejected}.", '']
    # findings by category
    cols = [r[1] for r in con.execute('PRAGMA table_info(findings)')]
    rows = con.execute('SELECT * FROM findings ORDER BY finding_id').fetchall()
    by = collections.defaultdict(list)
    for f in rows:
        by[_category(f, info)].append(f)
    L += ['## Findings by category', '']
    for cat in CATEGORIES:
        if not by.get(cat):
            continue
        L += [f'### {TITLES[cat]}', '']
        for f in by[cat]:
            text = _plain(f['text'], info)
            used = {s['id'] for s in json.loads(f['supports']) if s['type'] == 'analysis'}
            if used & set(STALE_NOTE) and stale_baseline(con, f):
                text += ' *(Note: ' + ' '.join(STALE_NOTE[a] for a in sorted(used & set(STALE_NOTE))) + ')*'
            based = []
            for s in json.loads(f['supports']):
                if s['type'] == 'claim_key' and s['id'] in info:
                    based.append(f"{LAYER_NAME.get(info[s['id']]['layer'], 'item')}: {info[s['id']]['text']}")
            line = f"- {text} *(confidence: {f['confidence']})*"
            if based:
                line += '\n  - Based on: ' + '; '.join(based[:4]) + (f'; and {len(based) - 4} more' if len(based) > 4 else '')
            L.append(line)
        L.append('')
    # chronology
    L += ['## What happened, in order', '']
    segs = collections.defaultdict(list)
    for k, c in info.items():
        segs[c['seg'] or '?'].append(c)
    for seg in sorted(segs):
        items = sorted(segs[seg], key=lambda c: c['t'] or '')
        span = con.execute('SELECT MIN(t), MAX(t), COUNT(*) FROM messages WHERE segment=? AND in_core=1', (seg,)).fetchone()
        L += [f"### {SEGMENT_NAME.get(seg, seg)} ({_hm(span[0])} to {_hm(span[1])} UTC, {span[2]} saves)", '']
        purposes = collections.Counter(r[0] for r in con.execute('''SELECT r.purpose FROM records r JOIN messages m USING (msg_id)
            WHERE m.segment=? AND r.retracted_by IS NULL AND r.cloned_from IS NULL''', (seg,)))
        if purposes:
            top = ', '.join(f'{p.lower().replace("_", " ")} ({n})' for p, n in purposes.most_common(4))
            L += [f'Most common acts: {top}.', '']
        for c in items:
            what = f"{_hm(c['t'])} · {LAYER_NAME.get(c['layer'], 'item')}: {c['text']} ({c['n']} saves, {c['editors']} editor{'s' if c['editors'] != 1 else ''})"
            v = _verdict_words(c)
            L.append(f'- {what}' + (f'. {v[0].upper() + v[1:]}.' if v else '.'))
            if c['summary']:
                L.append(f"  - {_plain(c['summary'], info)}")
        L.append('')
    edges = con.execute('''SELECT e.from_key, e.to_key, e.type FROM cluster_edges e WHERE e.retracted_by IS NULL''').fetchall()
    if edges:
        L += ['### Links between items', '']
        word = {'evolves_into': 'evolved into', 'feeds': 'fed into', 'corrects': 'corrected', 'supersedes': 'replaced', 'caused': 'led to'}
        for e in edges:
            a, b = info.get(e['from_key']), info.get(e['to_key'])
            if a and b:
                L.append(f"- {a['text']} **{word.get(e['type'], e['type'])}** {b['text']}.")
        L.append('')
    return '\n'.join(L) + '\n'
