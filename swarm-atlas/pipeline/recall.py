"""Recall check: score every candidate unit for multi-agent interaction and list strong
units that no swept instance covers. Independent of the sweep agents' judgment.

Units:
  AI Village  = (room, UTC day). Score uses distinct agents, reciprocal mention pairs, and
                distinct agents using self-organization vocabulary (claims, locks, votes, rules...).
  DSEWiki     = page. Score uses distinct agent handles, handle-to-handle succession edges,
                and coordination vocabulary.
  Moltbook    = post thread. Score uses distinct commenters and reciprocal A->B->A exchanges.
Usage: python recall.py <instances_dir> <out_json>
"""
import glob, json, math, os, re, sys
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(__file__))
import build

SELFORG = re.compile(r"(?i)\b(i'?ll take|claim(?:ed|ing)?|lock(?:ed)?\b|free\b|owner|assign(?:ed|ment)?|lane|protocol|rule|norm|vote|voting|agreed|consensus|tracker|hub|schedule|rotation|division of labor|split (?:the|it)|coordinat\w+|hand ?off|single source of truth|process|checklist|relay|cohort|round|liveness|heartbeat|backup|mirror|survival|confirm(?:ed)?)\b")

def load_insts(d):
    out = []
    for f in sorted(glob.glob(os.path.join(d, "*.jsonl"))):
        for l in open(f):
            l = l.strip()
            if l:
                try: out.append(json.loads(l))
                except Exception: pass
    return out

def av_units(insts):
    rows, mentions = build.load_av()
    U = defaultdict(lambda: {"agents": set(), "msgs": 0, "edges": Counter(), "selforg": set()})
    for r in rows:
        if r["kind"] != "agent": continue
        k = (r["loc"], r["ts"][:10]); u = U[k]
        u["agents"].add(r["who"]); u["msgs"] += 1
        for b in mentions(r["text"], r["ts"], r["who"]):
            u["edges"][(r["who"], b)] += 1
        if SELFORG.search(r["text"]): u["selforg"].add(r["who"])
    cov = [(set((i.get("selector") or {}).get("rooms") or []), build.norm_ts(i["start"])[:10], build.norm_ts(i["end"])[:10], i["id"])
           for i in insts if i.get("dataset") == "ai_village"]
    res = []
    for (room, day), u in U.items():
        if len(u["agents"]) < 3: continue
        recip = sum(1 for (a, b) in u["edges"] if (b, a) in u["edges"] and a < b)
        score = recip * math.log1p(u["msgs"]) + 2 * len(u["selforg"])
        hits = [iid for rooms, s, e, iid in cov if (not rooms or room in rooms) and s <= day <= e]
        res.append({"dataset": "ai_village", "unit": f"#{room} {day}", "room": room, "day": day, "agents": len(u["agents"]),
                    "msgs": u["msgs"], "reciprocal_pairs": recip, "selforg_agents": len(u["selforg"]),
                    "score": round(score, 2), "covered_by": hits})
    return res

def dw_units(insts):
    rows = build.load_dw()
    P = defaultdict(lambda: {"handles": set(), "edits": 0, "succ": 0, "selforg": 0, "first": None, "last": None, "wiki": None})
    lastw = {}
    for r in rows:
        if r["ev"] != "edit" or r["kind"] != "agent": continue
        k = (r["wiki"], r["page"]); p = P[k]
        p["wiki"] = r["wiki"]; p["handles"].add(r["who"]); p["edits"] += 1
        p["first"] = p["first"] or r["ts"]; p["last"] = r["ts"]
        if k in lastw and lastw[k] != r["who"]: p["succ"] += 1
        lastw[k] = r["who"]
        if SELFORG.search(r["text"][:4000]): p["selforg"] += 1
    sels = [(i.get("selector") or {}, build.norm_ts(i["start"]), build.norm_ts(i["end"]), i["id"]) for i in insts if i.get("dataset") == "dsewiki"]
    res = []
    for (wiki, page), p in P.items():
        if len(p["handles"]) < 3: continue
        score = math.log1p(p["succ"]) * len(p["handles"]) ** 0.5 + math.log1p(p["selforg"])
        hits = []
        for sel, s, e, iid in sels:
            if sel.get("wiki") not in (None, "all", "*", wiki): continue
            if not (p["first"] <= e and p["last"] >= s): continue
            pr = sel.get("page_regex")
            if page in (sel.get("pages") or []) or (pr and re.search(pr, page, re.I)) or (p["handles"] & set(sel.get("handles") or [])):
                hits.append(iid)
        res.append({"dataset": "dsewiki", "unit": f"{wiki}:{page}", "agents": len(p["handles"]), "msgs": p["edits"],
                    "succession_edges": p["succ"], "selforg_edits": p["selforg"], "first": p["first"], "last": p["last"],
                    "score": round(score, 2), "covered_by": hits})
    return res

def mb_units(insts):
    posts, C, cauthor = build.load_mb()
    # crude ring filter: accounts with > 2000 comments and < 60 distinct texts are scripts
    cnt = Counter(C["author"]); distinct = defaultdict(set)
    for a, t in zip(C["author"], C["text"]):
        if cnt[a] > 2000 and len(distinct[a]) < 61: distinct[a].add((t or "")[:80])
    script = {a for a in cnt if cnt[a] > 2000 and len(distinct[a]) < 60}
    T = defaultdict(lambda: {"authors": set(), "n": 0, "pairs": Counter(), "first": None, "last": None})
    for i in range(len(C["id"])):
        a = C["author"][i]
        if a in script: continue
        pid = C["post"][i]; t = T[pid]
        t["authors"].add(a); t["n"] += 1
        ts = C["ts"][i]
        if ts:
            t["first"] = min(t["first"] or ts, ts); t["last"] = max(t["last"] or ts, ts)
        par = C["parent"][i]
        tgt = cauthor.get(par) if par and par != "None" else posts.get(pid, {}).get("author")
        if tgt and tgt != a and tgt not in script: t["pairs"][(a, tgt)] += 1
    sels = [(i.get("selector") or {}, build.norm_ts(i["start"]), build.norm_ts(i["end"]), i["id"]) for i in insts if i.get("dataset") == "moltbook"]
    res = []
    for pid, t in T.items():
        if len(t["authors"]) < 3: continue
        recip = sum(1 for (a, b) in t["pairs"] if (b, a) in t["pairs"] and a < b)
        if recip == 0: continue
        p = posts.get(pid, {})
        score = recip * math.log1p(len(t["authors"]))
        hits = []
        for sel, s, e, iid in sels:
            if pid in (sel.get("post_ids") or []) or p.get("sub") in (sel.get("submolts") or []):
                hits.append(iid); continue
            kre = sel.get("keyword_regex")
            if kre and t["first"] and s <= t["last"] and e >= t["first"] and re.search(kre, (p.get("title", "") + " " + p.get("text", "")), re.I):
                hits.append(iid)
        res.append({"dataset": "moltbook", "unit": f"post {pid}", "post_id": pid, "title": (p.get("title") or "")[:90], "submolt": p.get("sub"),
                    "agents": len(t["authors"]), "msgs": t["n"], "reciprocal_pairs": recip, "first": t["first"], "last": t["last"],
                    "score": round(score, 2), "covered_by": hits})
    return res

if __name__ == "__main__":
    insts = load_insts(sys.argv[1])
    ds = set(sys.argv[3].split(",")) if len(sys.argv) > 3 else {"ai_village", "dsewiki", "moltbook"}
    allres = []
    if "ai_village" in ds: allres += av_units(insts)
    if "dsewiki" in ds: allres += dw_units(insts)
    if "moltbook" in ds: allres += mb_units(insts)
    json.dump(allres, open(sys.argv[2], "w"))
    for d in sorted({r["dataset"] for r in allres}):
        rs = sorted([r for r in allres if r["dataset"] == d], key=lambda r: -r["score"])
        top = rs[: max(50, len(rs) // 10)]
        cov = sum(bool(r["covered_by"]) for r in top)
        print(f"{d}: {len(rs)} units; top {len(top)} by score, {cov} covered ({cov/len(top):.0%}); all units covered {sum(bool(r['covered_by']) for r in rs)/len(rs):.0%}")
        for r in [r for r in top if not r["covered_by"]][:15]:
            print("   UNCOVERED", r["unit"], {k: r[k] for k in r if k in ("agents", "msgs", "reciprocal_pairs", "succession_edges", "selforg_agents", "score", "title")})
