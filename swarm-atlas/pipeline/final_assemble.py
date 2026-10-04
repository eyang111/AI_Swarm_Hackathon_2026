"""Assemble the final, post-aligned episode set from the locked review outputs.

Inputs (scratchpad): final_locked/av_A.jsonl, final_locked/moltbook.jsonl,
sweep_final/aligned/av_B.jsonl, final_locked/dsewiki.jsonl.
Applies the recall-gap window corrections for AI Village part A, checks ids are unique and
fields complete, and writes final/episodes.jsonl plus a summary.
"""
import json, os, sys
from collections import Counter

S = os.environ.get("SWARM_WORK", ".")  # folder holding final_locked/ (review outputs)
SRC = [f"{S}/final_locked/av_A.jsonl", f"{S}/final_locked/av_B.jsonl",
       f"{S}/final_locked/moltbook.jsonl", f"{S}/final_locked/dsewiki.jsonl"]
CORR_END = {"AV2232-62": "2026-03-04 22:00:16", "AV2232-57": "2026-03-04 20:46:14",
            "AV2232-04": "2025-12-18 22:01:00", "AV0010-41": "2025-07-15 20:00:00",
            "AV0010-53": "2025-08-22 20:01:00"}
NOTE_56 = ("Recurred on 2026-03-04 (rescue PRs, 'shadow-banned' and 'ghost' PRs) during the "
           "governance-toolkit sprint; see GAP-AV-01.")

def load(p):
    return [json.loads(l) for l in open(p) if l.strip()]

def main():
    rows, seen = [], {}
    for p in SRC:
        if not os.path.exists(p):
            sys.exit(f"missing input {p}")
        for r in load(p):
            if r["id"] in seen:
                print("DUPLICATE id", r["id"], "in", os.path.basename(p), "and", seen[r["id"]]); continue
            seen[r["id"]] = os.path.basename(p); rows.append(r)
    byid = {r["id"]: r for r in rows}
    def find(old):
        if old in byid: return byid[old]
        for r in rows:
            if old in (r.get("merged_from") or []): return r
        return None
    for old, end in CORR_END.items():
        r = find(old)
        if r is None: print("correction target not found:", old); continue
        if end > r["end"]:
            r["end"] = end
            r["review"] = (r.get("review") or "") + f" Window extended to {end} after the recall gap review."
    for old in ("AV2232-56", "AV3344-02"):
        r = find(old)
        if r is not None and NOTE_56 not in (r.get("caveats") or ""):
            r["caveats"] = ((r.get("caveats") or "") + " " + NOTE_56).strip()
    # sanity
    need = ["id", "dataset", "title", "start", "end", "selector", "participants", "key_messages", "features",
            "level", "origin", "goal_relation", "goal_type", "consequence"]
    bad = [(r["id"], k) for r in rows for k in need if r.get(k) in (None, "")]
    for r in rows:
        if not r.get("goal_relations"): r["goal_relations"] = [r["goal_relation"]]
        r["level"] = int(r["level"])
    print("missing fields:", len(bad), bad[:10])
    os.makedirs(f"{S}/final", exist_ok=True)
    with open(f"{S}/final/episodes.jsonl", "w") as f:
        for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    for ds in ("ai_village", "moltbook", "dsewiki"):
        R = [r for r in rows if r["dataset"] == ds]
        lv = Counter(r["level"] for r in R)
        print(ds, len(R), "levels", [lv.get(i, 0) for i in range(6)],
              "origin", dict(Counter(r["origin"] for r in R)),
              "consequence", dict(Counter(r["consequence"] for r in R)))
    print("total", len(rows))

if __name__ == "__main__":
    main()
