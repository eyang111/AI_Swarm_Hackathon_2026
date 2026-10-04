"""L6 timeline graph + export screen (DESIGN.md 5.7, 7.4).

Nodes = clusters (split into phases where L4 found them), arrows = live cluster edges. Every node drills to its
segments with msg_ids and reader summaries. No quotes leave the store unless the msg_id is on the reviewed allowlist
(test_run/export_allowlist.txt, empty by default); coverage-gap and ACCESS_WORKAROUND messages never are.
Writes test_run/timeline.json and test_run/timeline.html (self-contained).
"""
import json, os
import config as C, store


def build(con):
    allow = set()
    p = os.path.join(C.RUN_DIR, 'export_allowlist.txt')
    if os.path.exists(p):
        allow = {l.strip() for l in open(p) if l.strip()}
    blocked = {r['msg_id'] for r in con.execute('SELECT msg_id FROM coverage_gaps')} | \
              {r['msg_id'] for r in con.execute("SELECT msg_id FROM segments WHERE purpose='ACCESS_WORKAROUND'")}
    nodes = []
    for ck in con.execute('''SELECT ck.*, n.t_first FROM claim_keys ck JOIN novelty n USING (claim_key)
                             WHERE merged_into IS NULL ORDER BY n.t_first'''):
        mem = con.execute('''SELECT lm.*, s.summary, s.function FROM live_members lm JOIN segments s USING (segment_id)
                             WHERE claim_key=? ORDER BY lm.t''', (ck['claim_key'],)).fetchall()
        a = con.execute("SELECT body FROM analyses WHERE analysis_id=?", (f'l4:{ck["claim_key"]}',)).fetchone()
        a = json.loads(a['body']) if a else {}
        roles = {s['segment_id']: s['role'] for s in a.get('steps', [])}
        phases = a.get('phases') or [{'label': 'all', 'segments': [m['segment_id'] for m in mem]}]
        assigned = set()
        for k, ph in enumerate(phases):
            seg = [m for m in mem if m['segment_id'] in set(ph['segments'])] if len(phases) > 1 else mem
            if len(phases) > 1 and k == len(phases) - 1:
                seg += [m for m in mem if m['segment_id'] not in assigned and m not in seg]
            assigned |= {m['segment_id'] for m in seg}
            if not seg:
                continue
            msgs = []
            for m in seg:
                d = dict(msg_id=m['msg_id'], segment_id=m['segment_id'], t=m['t'], editor=m['speaker'], page=m['channel'],
                         purpose=m['purpose'], role=roles.get(m['segment_id']),
                         summary=C.AW_SUMMARY if m['purpose'] == store.AW else m['summary'])
                if m['msg_id'] in allow and m['msg_id'] not in blocked:
                    s = con.execute('SELECT char_start, char_end FROM segments WHERE segment_id=?', (m['segment_id'],)).fetchone()
                    d['quote'] = store.msg_text(con, m['msg_id'])[s['char_start']:s['char_end']][:200]
                msgs.append(d)
            nodes.append(dict(id=ck['claim_key'] + (f'#p{k}' if len(phases) > 1 else ''), cluster=ck['claim_key'],
                              phase=ph['label'] if len(phases) > 1 else None, layer=ck['layer'], text=ck['canonical_text'],
                              t_first=seg[0]['t'], t_last=seg[-1]['t'], n=len(seg), editors=len({m['speaker'] for m in seg}),
                              origin=(a.get('origin_assessment') or {}).get('kind'),
                              copying=(a.get('copying_vs_convergence') or {}).get('verdict'), account=a.get('summary'),
                              members=msgs))
    edges = [dict(id=e['edge_id'], source=e['from_key'], target=e['to_key'], type=e['type'], confidence=e['confidence'],
                  rationale=e['rationale']) for e in con.execute('SELECT * FROM cluster_edges WHERE retracted_by IS NULL')]
    return dict(nodes=nodes, edges=edges, quotes_allowlisted=len(allow))


HTML = r'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Swarm Investigator Timeline</title><style>
:root{--bg:#fbfaf7;--fg:#1f2328;--muted:#6b7078;--line:#d9d6cf;--card:#fff;--belief:#2f6fb3;--goal:#b5562b;--protocol:#5a8a3a;--method:#7d4fa8;--word:#b08a1e}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#16181c;--fg:#e6e6e3;--muted:#9aa0a6;--line:#30343a;--card:#1e2126;--belief:#6ea6e6;--goal:#e58a5c;--protocol:#8dc26a;--method:#b58be0;--word:#e0bd4f}}
:root[data-theme="dark"]{--bg:#16181c;--fg:#e6e6e3;--muted:#9aa0a6;--line:#30343a;--card:#1e2126;--belief:#6ea6e6;--goal:#e58a5c;--protocol:#8dc26a;--method:#b58be0;--word:#e0bd4f}
body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.45 system-ui,sans-serif}
main{max-width:1100px;margin:0 auto;padding:16px}
h1{font-size:20px;margin:4px 0}.muted{color:var(--muted)}
.panel{margin:18px 0}.panel h2{font-size:15px;margin:0 0 6px}
.row{display:grid;grid-template-columns:minmax(0,34%) minmax(0,1fr);gap:8px;align-items:center;padding:3px 0;border-bottom:1px solid var(--line);cursor:pointer}
.row:hover{background:var(--card)}.lbl{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.track{position:relative;height:16px}.bar{position:absolute;height:12px;top:2px;border-radius:6px;min-width:6px;opacity:.85}
.legend span{display:inline-block;margin-right:12px}.dot{display:inline-block;width:10px;height:10px;border-radius:5px;margin-right:4px}
#detail{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px;margin-top:12px}
#detail table{width:100%;border-collapse:collapse;font-size:12px}#detail td{border-top:1px solid var(--line);padding:3px 4px;vertical-align:top;word-break:break-word}
.edges li{margin:2px 0}
</style></head><body><main>
<h1>Swarm Investigator timeline (full DSEWiki dump)</h1>
<div class="muted">Each row is one spreading item (a cluster); bars run from first to last member save, height-ordered by first appearance. Click a row for its saves. Quotes are withheld by default (export screen); summaries are the readers' own words.</div>
<div class="legend" id="legend"></div><div id="panels"></div><div id="detail" class="muted">Select a row.</div>
<h2 style="font-size:15px">Cross-cluster edges</h2><ul class="edges" id="edges"></ul>
</main><script>
const G=__DATA__;const L=['belief','goal','protocol','method','word'];
document.getElementById('legend').innerHTML=L.map(l=>`<span><i class="dot" style="background:var(--${l})"></i>${l}</span>`).join('');
const segs=[...new Set(G.nodes.map(n=>String(n.t_first).slice(0,10)))].sort().map(d=>[d,d+'T00:00:00Z',new Date(Date.parse(d)+86400e3).toISOString()]);
const T=s=>Date.parse(s);const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
let html='';for(const [name,a,b] of segs){const A=T(a),B=T(b);const ns=G.nodes.filter(n=>T(n.t_first)>=A&&T(n.t_first)<B);
if(!ns.length)continue;html+=`<div class="panel"><h2>${name} <span class="muted">${a.slice(0,16)} to ${b.slice(11,16)} UTC, ${ns.length} items</span></h2>`;
for(const n of ns){const x0=Math.max(0,(T(n.t_first)-A)/(B-A)*100),x1=Math.min(100,(T(n.t_last)-A)/(B-A)*100);
html+=`<div class="row" data-id="${esc(n.id)}"><div class="lbl" title="${esc(n.text)}">${esc(n.text)} <span class="muted">(${n.n} saves, ${n.editors} names)</span></div><div class="track"><div class="bar" style="left:${x0}%;width:${Math.max(.8,x1-x0)}%;background:var(--${n.layer})"></div></div></div>`}
html+='</div>'}document.getElementById('panels').innerHTML=html;
document.querySelectorAll('.row').forEach(r=>r.onclick=()=>{const n=G.nodes.find(x=>x.id===r.dataset.id);
document.getElementById('detail').innerHTML=`<b>${esc(n.text)}</b><div class="muted">${n.layer}; origin: ${esc(n.origin)}; copying vs convergence: ${esc(n.copying)}</div><p>${esc(n.account)}</p><table>${n.members.map(m=>`<tr><td>${esc(m.t.slice(5,19))}</td><td>${esc(m.editor)}</td><td>${esc(m.role||'')}</td><td>${esc(m.purpose)}</td><td>${esc(m.summary)}${m.quote?'<br><i>'+esc(m.quote)+'</i>':''}<br><span class="muted">${esc(m.msg_id)}</span></td></tr>`).join('')}</table>`});
document.getElementById('edges').innerHTML=G.edges.length?G.edges.map(e=>`<li>${esc(e.source)} <b>${esc(e.type)}</b> ${esc(e.target)} <span class="muted">(${e.confidence}) ${esc(e.rationale)}</span></li>`).join(''):'<li class="muted">none</li>';
</script></body></html>'''


def main():
    con = store.connect()
    g = build(con)
    json.dump(g, open(os.path.join(C.RUN_DIR, 'timeline.json'), 'w'), indent=1, ensure_ascii=False)
    open(os.path.join(C.RUN_DIR, 'timeline.html'), 'w').write(HTML.replace('__DATA__', json.dumps(g, ensure_ascii=False).replace('</', '<\\/')))
    return dict(nodes=len(g['nodes']), edges=len(g['edges']))


if __name__ == '__main__':
    print(main())
