"""Pack build output into the site: data/index.json, data/c/NN.json chunks (~3MB each), data/meta.json.
Usage: python pack.py <build_out_dir> <site_dir> [meta.json]
"""
import json, os, sys, glob, re

src, site = sys.argv[1], sys.argv[2]
meta = json.load(open(sys.argv[3])) if len(sys.argv) > 3 else None
os.makedirs(f"{site}/data/c", exist_ok=True)
for f in glob.glob(f"{site}/data/c/*.json"):
    os.remove(f)
index = json.load(open(f"{src}/index.json"))
LIMIT = 3_000_000
chunk, size, n = {}, 0, 0
def flush():
    global chunk, size, n
    if chunk:
        open(f"{site}/data/c/{n:02d}.json", "w", encoding="utf-8").write(json.dumps(chunk, ensure_ascii=False, separators=(",", ":")).replace("\ufffd", ""))
        n += 1
    chunk, size = {}, 0
order = sorted(index, key=lambda m: (m["dataset"], m.get("start") or ""))
for m in order:
    t = json.load(open(f"{src}/{m['file']}"))
    s = len(json.dumps(t, ensure_ascii=False))
    if size and size + s > LIMIT:
        flush()
    chunk[m["id"]] = {"messages": t["messages"], "edges": t["edges"]}
    size += s
    m["file"] = f"data/c/{n:02d}.json"
flush()
open(f"{site}/data/index.json", "w", encoding="utf-8").write(json.dumps(index, ensure_ascii=False, separators=(",", ":")).replace("\ufffd", ""))
if meta:
    json.dump(meta, open(f"{site}/data/meta.json", "w"), ensure_ascii=False)
# final secret scan over everything shipped
bad = re.compile(r'''(?i)(password|passwd|api[_ -]?key|private[_ -]?key|seed phrase|mnemonic)\s*(?:is|:|=)\s*(?!\[REDACTED)(?=[^\s"\\]*\d)(?=[^\s"\\]*[A-Za-z])[^\s"\\]{8,}|\b0x[0-9a-fA-F]{64}\b|\b[a-z]+_sk_[A-Za-z0-9]{8,}\b|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}''')
hits = 0
for f in [f"{site}/data/index.json"] + sorted(glob.glob(f"{site}/data/c/*.json")):
    for mm in bad.finditer(open(f).read()):
        hits += 1
        if hits <= 10:
            print("POSSIBLE SECRET", f, mm.group(0)[:40])
tot = sum(os.path.getsize(f) for f in glob.glob(f"{site}/data/**/*.json", recursive=True))
print(f"{len(index)} episodes, {n} chunks, {tot/1e6:.1f} MB total, secret-scan hits: {hits}")
