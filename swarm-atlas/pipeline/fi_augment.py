"""Attach primary function and origin-message intentionality to every final episode.

Sources (scratchpad):
  tax/labels_av1.jsonl, labels_av2.jsonl, labels_other.jsonl   companion labels (D_function)
  intent/scores_*.jsonl + intent/packets.json                  companion intent scores + origin messages
  fi/labels_missing.jsonl                                      labels added for episodes the companion pass did not cover
Writes final_build_fi/index.json (and links final_build/t), ready for pack.py.
"""
import glob, json, os, sys
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build

S = os.environ.get("SWARM_WORK", ".")  # folder holding tax/, intent/, fi/ label files
V = os.environ.get("SWARM_VIEWER_BUILD", ".")  # folder holding final_build/

def jl(p):
    return [json.loads(l) for l in open(p) if l.strip()]

fn = {}
for p in ["labels_av1", "labels_av2", "labels_other"]:
    for d in jl(f"{S}/tax/{p}.jsonl"):
        fn[d["id"]] = d.get("D_function")
sc, pk = {}, {}
for p in sorted(glob.glob(f"{S}/intent/scores_*.jsonl")):
    for d in jl(p):
        if d["pid"].startswith("E::"):
            sc[d["pid"][3:]] = d
for d in json.load(open(f"{S}/intent/packets.json")):
    if d["pid"].startswith("E::"):
        pk[d["pid"][3:]] = d
add = {d["id"]: d for d in jl(f"{S}/fi/labels_missing.jsonl")}

def clean_origin(o, ds):
    if not o:
        return None
    t = o.get("text") or ""
    t = build.dsewiki_text(t) if ds == "dsewiki" else build.clip(build.redact(t), 900)
    return {"ts": build.norm_ts(o.get("ts")), "who": o.get("who"), "loc": o.get("loc"), "text": build.redact(t)}

def find(table, m):
    if m["id"] in table:
        return m["id"]
    for x in (m.get("merged_from") or []):
        if x in table:
            return x
    return None

index = json.load(open(f"{V}/final_build/index.json"))
cf, ci = Counter(), Counter()
for m in index:
    k = find(fn, m)
    a = add.get(m["id"], {})
    if k and fn[k]:
        m["function"], m["function_source"] = fn[k], "companion labeling pass" + ("" if k == m["id"] else f" (labelled as {k} before merging)")
    elif a.get("function"):
        m["function"], m["function_source"] = a["function"], "added in this edition, same definitions"
    cf[m.get("function") or "MISSING"] += 1
    k = find(sc, m)
    if k:
        s0, p0 = sc[k], pk.get(k, {})
        m["intent"] = {"score": int(s0["intent"]), "speech_act": s0.get("speech_act"), "addressed_to_others": s0.get("addressed_to_others"),
                       "reason": build.redact(s0.get("reason") or ""), "confidence": s0.get("confidence"),
                       "source": "companion scoring pass" + ("" if k == m["id"] else f" (scored as {k} before merging)"),
                       "origin": clean_origin(p0.get("origin"), m["dataset"])}
    elif a.get("intent"):
        m["intent"] = {"score": int(a["intent"]), "speech_act": a.get("speech_act"), "addressed_to_others": a.get("addressed_to_others"),
                       "reason": build.redact(a.get("reason") or ""), "confidence": a.get("confidence"),
                       "source": "added in this edition, same definitions", "origin": clean_origin(a.get("origin"), m["dataset"])}
    ci[(m.get("intent") or {}).get("score", "MISSING")] += 1
out = f"{V}/final_build_fi"
os.makedirs(out, exist_ok=True)
if not os.path.exists(f"{out}/t"):
    os.symlink(f"{V}/final_build/t", f"{out}/t")
json.dump(index, open(f"{out}/index.json", "w"), ensure_ascii=False)
print("function", dict(cf)); print("intent", dict(ci))
