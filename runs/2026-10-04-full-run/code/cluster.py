"""Conversation layer (DESIGN.md 4.5, store_design 2a): script pass only.

Connects core messages by reply hints / reply_to links, saves on the same page within 30 minutes, and a save that names
a page saved in the previous 60 minutes. Each connected group of 2+ saves is a conversation. Presence is exposure
evidence, not proof. The Opus clusterer that wrote topics and split/merge edges was cut on 2026-10-04 (DESIGN 15):
it failed on the largest conversations in run #1 and nothing downstream used its topics or edges.
"""
import collections, json, re
import config as C, store, load

STAGE = 'clusterer'
PAGE_GAP_S, REF_GAP_S = 1800, 3600

def script_pass(con):
    msgs = con.execute("SELECT * FROM messages WHERE in_core=1 AND COALESCE(script_label,'')!='EMPTY' ORDER BY t").fetchall()
    ids = [m['msg_id'] for m in msgs]
    parent = {i: i for i in ids}
    basis = collections.defaultdict(set)

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x

    def union(a, b, why):
        if a in parent and b in parent:
            parent[find(a)] = find(b); basis[a].add(why); basis[b].add(why)
    hints = {r['msg_id']: r['reply_to_hint'] for r in store.live_records(con)}
    for mid, h in hints.items():
        if h and h in parent:
            union(mid, h, 'reply_to')
    for l in con.execute("SELECT from_msg_id, to_msg_id FROM links WHERE type='reply_to' AND retracted_by IS NULL"):
        union(l['from_msg_id'], l['to_msg_id'], 'reply_to')
    last = {}
    titles = {}
    for m in msgs:
        t = load.ts(m['t'])
        if m['channel'] in last and t - last[m['channel']][1] <= PAGE_GAP_S:
            union(m['msg_id'], last[m['channel']][0], 'same_page_chain')
        last[m['channel']] = (m['msg_id'], t)
        title = m['channel'].split('~', 1)[1]
        body = m['text'][m['text'].find('\n') + 1:]
        for other, (oid, ot) in list(titles.items()):
            if other != title and len(other) >= 8 and other in body and t - ot <= REF_GAP_S:
                union(m['msg_id'], oid, 'page_reference')
        titles[title] = (m['msg_id'], t)
    groups = collections.defaultdict(list)
    for i in ids:
        groups[find(i)].append(i)
    return [(g, {i: (sorted(basis[i]) or ['time_gap'])[0] for i in g}) for g in groups.values() if len(g) >= 2]


def run(con, llm, run_id):
    """Writes every script group as a conversation (llm is unused; kept for the run.py stage signature)."""
    groups = script_pass(con)
    tid = store.new_task(con, run_id, STAGE, {'id': 'script'}, 'script')
    sizes = collections.Counter()
    for k, (g, b) in enumerate(sorted(groups, key=lambda gb: min(gb[0]))):
        _write_conv(con, tid, f'conv{k}', '(script grouping)', sorted(g), 'medium',
                    'script pass: ' + ','.join(sorted(set(b.values()))), b)
        sizes['pairs' if len(g) == 2 else 'groups_3plus'] += 1
    store.finish_task(con, tid)
    con.commit()
    return dict(conversations=len(groups), **sizes, largest=max((len(g) for g, _ in groups), default=0))


def _write_conv(con, tid, conv_id, topic, members, conf, rationale, basis):
    rows = [con.execute('SELECT t, channel FROM messages WHERE msg_id=?', (i,)).fetchone() for i in members]
    con.execute('INSERT OR REPLACE INTO conversations VALUES (?,?,?,?,?,?,?,?)', (conv_id, tid, topic[:300],
                json.dumps(sorted({r['channel'] for r in rows})), min(r['t'] for r in rows), max(r['t'] for r in rows), rationale[:500], None))
    for i in members:
        con.execute('INSERT OR IGNORE INTO conversation_members VALUES (?,?,?,?,?,?)',
                    (conv_id, i, tid, basis.get(i, 'agent_judgment'), conf if conf in store.CONF else 'low', None))
