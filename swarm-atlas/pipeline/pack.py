"""Pack build output into the site under a per-build folder, so browsers can never mix files
from two builds: data/<tag>/index.json, data/<tag>/c/NN.json (~3MB chunks), data/<tag>/meta.json.
The page is written from index_template.html with the tag filled in.

Usage: python pack.py <build_out_dir> <site_dir> [meta.json]
"""
import glob, hashlib, json, os, re, shutil, sys

src, site = sys.argv[1], sys.argv[2]
meta = json.load(open(sys.argv[3])) if len(sys.argv) > 3 else None
index = json.load(open(f"{src}/index.json"))
tag = "b" + hashlib.sha256(json.dumps(index, sort_keys=True).encode()).hexdigest()[:10]
for d in glob.glob(f"{site}/data/*"):           # drop previous builds and any loose files
    shutil.rmtree(d) if os.path.isdir(d) else os.remove(d)
out = f"{site}/data/{tag}"
os.makedirs(f"{out}/c", exist_ok=True)

def write(path, obj):
    open(path, "w", encoding="utf-8").write(json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("\ufffd", ""))

LIMIT = 3_000_000
chunk, size, n = {}, 0, 0
def flush():
    global chunk, size, n
    if chunk:
        write(f"{out}/c/{n:02d}.json", chunk); n += 1
    chunk, size = {}, 0
for m in sorted(index, key=lambda m: (m["dataset"], m.get("start") or "")):
    t = json.load(open(f"{src}/{m['file']}"))
    s = len(json.dumps(t, ensure_ascii=False))
    if size and size + s > LIMIT:
        flush()
    chunk[m["id"]] = {"messages": t["messages"], "edges": t["edges"]}
    size += s
    m["file"] = f"data/{tag}/c/{n:02d}.json"
flush()
write(f"{out}/index.json", index)
if meta:
    write(f"{out}/meta.json", meta)
tpl = open(f"{site}/index_template.html", encoding="utf-8").read()
assert "__BUILD__" in tpl
open(f"{site}/index.html", "w", encoding="utf-8").write(tpl.replace("__BUILD__", tag))

# final secret scan over everything shipped
bad = re.compile(r'''(?i)(password|passwd|api[_ -]?key|private[_ -]?key|seed phrase|mnemonic)\s*(?:is|:|=)\s*(?!\[REDACTED)(?=[^\s"\\]*\d)(?=[^\s"\\]*[A-Za-z])[^\s"\\]{8,}|\b0x[0-9a-fA-F]{64}\b|\b[a-z]+_sk_[A-Za-z0-9]{8,}\b|\bnfp_[A-Za-z0-9]{16,}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}''')
hits = 0
for f in sorted(glob.glob(f"{out}/**/*.json", recursive=True)):
    for mm in bad.finditer(open(f, encoding="utf-8").read()):
        hits += 1
        if hits <= 10:
            print("POSSIBLE SECRET", f, mm.group(0)[:40])
tot = sum(os.path.getsize(f) for f in glob.glob(f"{out}/**/*.json", recursive=True))
print(f"tag {tag}: {len(index)} episodes, {n} chunks, {tot/1e6:.1f} MB, secret-scan hits: {hits}")
