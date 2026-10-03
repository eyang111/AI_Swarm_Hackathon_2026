"""Build viewer data: per-instance transcripts + stats from the sweep JSONL files.

Usage: python build.py <instances_dir_or_glob> <out_dir>
Reads every *.jsonl in the instances dir, pulls each instance's transcript from the raw
data via its selector, validates key quotes, redacts secrets, computes stats, and writes
out_dir/index.json plus out_dir/t/<id>.json.
"""
import glob, gzip, json, os, re, sys, math, bisect
from collections import Counter, defaultdict
from datetime import datetime, timedelta

S = os.environ.get("SWARM_RAW", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "raw"))  # folder holding av/, mb/, dw/
CAP = 700           # max transcript rows shipped per instance
TXT = 1000          # max chars per shipped message (key messages get 2000)

# ---------------------------------------------------------------- helpers
def norm_ts(s):
    if not s or s in ("None", "null"):
        return None
    s = str(s).replace("T", " ").replace("Z", "")
    s = re.sub(r"\+00:00$", "", s)
    return s[:19]

def to_dt(s):
    return datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")

URL = re.compile(r"https?://[^\s\]\)\"'<>|]+")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
SECRET_KV = re.compile(r"(?i)\b(password|passwd|passphrase|pwd|api[_ -]?key|secret[_ -]?key|private[_ -]?key|access[_ -]?token|auth[_ -]?token|token|seed(?: phrase)?|mnemonic|recovery phrase)\b(\s*(?:is|:|=|->)\s*)[\"'`]?([^\s\"'`]{4,})")
HEXKEY = re.compile(r"\b(?:0x)?[0-9a-fA-F]{64}\b")
SKKEY = re.compile(r"\b(?:(?:sk|pk|ghp|gho|glpat|xox[bp])[-_][A-Za-z0-9_\-]{16,}|[a-z]+_sk_[A-Za-z0-9]{8,})\b")
PASSNEAR = re.compile(r"(?i)(\b(?:passwords?|passwd|passcodes?|passphrases?|pwd|pass)\b)(.{0,80})", re.S)
TOKSECRET = re.compile(r"(?<![\w\[])(?=\S*[\d!@#$%^&*])[^\s`'\"*,;()<>\[\]]{6,}")
NFP = re.compile(r"\bnfp_[A-Za-z0-9]{16,}\b")
HIGHENT = re.compile(r"(?<![A-Za-z0-9_\-])[A-Za-z0-9_\-]{20,}(?![A-Za-z0-9_\-])")
WORDRUN = re.compile(r"\b(?:[a-z]{3,8}\s+){11,23}[a-z]{3,8}\b")

def shorten_url(m):
    u = re.sub(r"^https?://", "", m.group(0))
    host = u.split("/", 1)[0]
    return f"[link: {host}]"

PASSKW = re.compile(r"(?i)\b(?:passwords?|passwd|passcodes?|passphrases?|pwd|pass)\b")
def pass_windows(t):
    """Redact digit/symbol-bearing tokens within 80 chars after every password keyword."""
    spans = [(m.end(), m.end() + 80) for m in PASSKW.finditer(t)]
    if not spans:
        return t
    out, last = [], 0
    for m in TOKSECRET.finditer(t):
        if any(a <= m.start() < b for a, b in spans):
            out.append(t[last:m.start()]); out.append("[REDACTED]"); last = m.end()
    out.append(t[last:])
    return "".join(out)

def redact(t):
    if not t:
        return ""
    t = str(t)
    t = EMAIL.sub("[email]", t)
    t = SECRET_KV.sub(lambda m: m.group(1) + m.group(2) + "[REDACTED]", t)
    t = HEXKEY.sub("[REDACTED-KEY]", t)
    t = SKKEY.sub("[REDACTED-KEY]", t)
    t = NFP.sub("[REDACTED-KEY]", t)
    t = pass_windows(t)
    t = HIGHENT.sub(lambda m: "[REDACTED-KEY]" if (re.search(r"[A-Z]", m.group(0)) and re.search(r"[a-z]", m.group(0)) and re.search(r"\d", m.group(0))) else m.group(0), t)
    if re.search(r"(?i)seed|mnemonic|recovery|wallet|phrase", t):
        t = WORDRUN.sub("[REDACTED-PHRASE]", t)
    t = URL.sub(shorten_url, t)
    return t

NETADDR = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")
def technical(line):
    if "://" in line or NETADDR.search(line):
        return True
    if "?" in line and "=" in line and "&" in line:
        return True
    letters = sum(c.isalpha() or c.isspace() for c in line)
    return len(line) > 30 and letters / len(line) < 0.6

def dsewiki_text(t):
    """Keep the coordination prose of a wiki edit; withhold technical lines."""
    out, held = [], 0
    for line in str(t or "").splitlines():
        if technical(line):
            held += 1
            if held == 1 or (out and out[-1] != "[technical line withheld]"):
                out.append("[technical line withheld]")
        else:
            out.append(line)
    txt = "\n".join(out)
    return txt if len(txt) <= 600 else txt[:600] + " …[truncated]"

def clip(t, n=TXT):
    return t if len(t) <= n else t[:n] + " …[truncated]"

def words(s):
    return re.findall(r"[a-z0-9]+", (s or "").lower())

def quote_match(q, text):
    qw = [w for w in words(q) if w not in ("url", "redacted", "link")]
    if not qw:
        return False
    tl = " ".join(words(text))
    if " ".join(qw) in tl:
        return True
    tw = set(words(text))
    return sum(w in tw for w in qw) / len(qw) >= 0.75

def safe_re(p):
    """Compile a selector regex case-insensitively, tolerating inline flags placed mid-pattern."""
    if not p:
        return None
    try:
        return re.compile(p, re.I)
    except re.error:
        try:
            return re.compile(re.sub(r"\(\?[aiLmsux]+\)", "", p), re.I)
        except re.error:
            return re.compile(re.escape(p), re.I)

# ---------------------------------------------------------------- AI Village
def load_av():
    ag = {r["id"]: r["name"] for r in map(json.loads, gzip.open(f"{S}/av/agents.jsonl.gz", "rt"))}
    rooms = {r["id"]: r["name"] for r in map(json.loads, gzip.open(f"{S}/av/chat_rooms.jsonl.gz", "rt"))}
    un = json.load(open(f"{S}/av/user_msg_names.json"))
    STAFF = {"zak", "adam", "admin", "Larissa Schiavo", "Shoshannah"}
    rows = []
    for m in map(json.loads, gzip.open(f"{S}/av/chat_messages.jsonl.gz", "rt")):
        ts = norm_ts(m["created_at"])
        if m["speaker_type"] == "agent":
            sp, kind = ag.get(m["agent_speaker_id"], "?"), "agent"
        else:
            n = un.get(m["id"], "?")
            if n == "automated":
                sp, kind = "BOT(automated)", "bot"
            else:
                sp, kind = n, ("staff" if n in STAFF else "human")
        rows.append({"ts": ts, "loc": rooms.get(m["room_id"], "?"), "who": sp, "kind": kind, "text": m["content"] or ""})
    rows.sort(key=lambda r: r["ts"])
    # alias table for mention edges, with active ranges
    first, last = {}, {}
    for r in rows:
        if r["kind"] == "agent":
            first.setdefault(r["who"], r["ts"]); last[r["who"]] = r["ts"]
    alias = defaultdict(set)
    for name in first:
        cands = {name}
        if name.startswith("Claude "):
            cands.add(name[7:])
        m = re.match(r"(Gemini \d+(?:\.\d+)?) (Pro|Flash)", name)
        if m: cands.add(m.group(1))
        if name.startswith("Opus 4.5 (Claude Code)"): cands |= {"Claude Code", "Opus CC"}
        for fam in ("Haiku", "Kimi", "Grok", "DeepSeek", "GLM", "Muse", "Fable", "Astra", "Terra", "Luna", "Sol"):
            if fam.lower() in name.lower():
                cands.add(fam)
        if name.startswith("DeepSeek-"): cands.add(name.split("-", 1)[1])
        if name.startswith("GPT-5.6 "): cands.add(name.split(" ", 1)[1])
        for c in cands:
            alias[c].add(name)
    alist = sorted(alias, key=len, reverse=True)
    apat = re.compile(r"(?<![\w.])(" + "|".join(re.escape(a) for a in alist) + r")(?![\w])")
    def mentions(text, ts, speaker):
        out = []
        for a in apat.findall(text or ""):
            act = [n for n in alias[a] if first[n] <= ts <= last[n] and n != speaker]
            if len(act) == 1:
                out.append(act[0])
        return out
    return rows, mentions

# ---------------------------------------------------------------- Moltbook
def load_mb():
    import pyarrow.parquet as pq
    P = pq.read_table(f"{S}/mb/aicell_posts.parquet", columns=["id", "title", "content", "created_at", "submolt_name", "author_name"]).to_pydict()
    C = pq.read_table(f"{S}/mb/aicell_comments.parquet", columns=["id", "post_id", "parent_id", "content", "created_at", "author_name"]).to_pydict()
    posts = {}
    for i in range(len(P["id"])):
        posts[P["id"][i]] = {"ts": norm_ts(P["created_at"][i]), "author": P["author_name"][i], "sub": P["submolt_name"][i],
                             "title": P["title"][i] or "", "text": P["content"][i] or ""}
    comments = {"id": C["id"], "post": C["post_id"], "parent": C["parent_id"], "text": C["content"],
                "ts": [norm_ts(x) for x in C["created_at"]], "author": C["author_name"]}
    cauthor = dict(zip(C["id"], C["author_name"]))
    return posts, comments, cauthor

# ---------------------------------------------------------------- DSEWiki
def load_dw():
    rev = [json.loads(l) for l in open(f"{S}/dw/revisions.jsonl")]
    ev = [json.loads(l) for l in open(f"{S}/dw/events.jsonl")]
    human = {l["label"] for l in map(json.loads, open(f"{S}/dw/labels.jsonl")) if str(l.get("is_human_handle")) == "True"}
    rows = []
    for r in rev:
        ts = norm_ts(r.get("time"))
        if not ts: continue
        body = "" if r.get("body") in (None, "None") else r["body"]
        cs = r.get("change_summary")
        cs = "" if cs in (None, "None") else cs
        rows.append({"ts": ts, "wiki": r["wiki"], "page": r["name"], "who": r.get("label") or "?",
                     "kind": "human" if r.get("label") in human else "agent", "text": body, "note": cs, "ev": "edit"})
    for e in ev:
        if e.get("event_type") in ("delete", "revert"):
            ts = norm_ts(e.get("time"))
            if ts:
                rows.append({"ts": ts, "wiki": e["wiki"], "page": e["page"], "who": "(moderator)", "kind": "moderator",
                             "text": f"[{e['event_type']}d page]", "note": "", "ev": e["event_type"]})
    rows.sort(key=lambda r: r["ts"])
    return rows

# ---------------------------------------------------------------- per-instance extraction
def pick_av(inst, rows, mentions):
    sel = inst.get("selector") or {}
    rooms = set(sel.get("rooms") or [])
    st, en = norm_ts(inst["start"]), norm_ts(inst["end"])
    kre = sel.get("keyword_regex")
    kre = safe_re(kre)
    tsl = [r["ts"] for r in rows]
    lo, hi = bisect.bisect_left(tsl, st), bisect.bisect_right(tsl, en)
    out = []
    for r in rows[lo:hi]:
        if rooms and r["loc"] not in rooms: continue
        if kre and not kre.search(r["text"]) and r["who"] not in ("HUMAN",):
            # keep staff messages too when focusing, they carry instructions
            if r["kind"] != "staff": continue
        out.append(dict(r))
    edges = Counter()
    for r in out:
        if r["kind"] == "agent":
            for b in mentions(r["text"], r["ts"], r["who"]):
                edges[(r["who"], b)] += 1
    return out, edges

def pick_mb(inst, posts, comments, cauthor):
    sel = inst.get("selector") or {}
    st, en = norm_ts(inst["start"]), norm_ts(inst["end"])
    pids = set(sel.get("post_ids") or [])
    auth = set(sel.get("authors") or [])
    subs = set(sel.get("submolts") or [])
    kre = sel.get("keyword_regex")
    kre = safe_re(kre)
    out = []
    for pid, p in posts.items():
        if not p["ts"] or not (st <= p["ts"] <= en): continue
        if pid in pids or p["author"] in auth or p["sub"] in subs or (kre and kre.search(p["title"] + " " + p["text"])):
            out.append({"ts": p["ts"], "loc": f"m/{p['sub']} · post {pid[:8]}", "who": p["author"], "kind": "agent",
                        "text": (("# " + p["title"] + "\n") if p["title"] else "") + p["text"], "post": pid, "id": pid})
    # posts selected by id or submolt pull in their full threads; authors/regex select comments directly
    sel_posts = pids | {pid for pid, p in posts.items() if p["sub"] in subs and p["ts"] and st <= p["ts"] <= en}
    C = comments
    for i in range(len(C["id"])):
        ts = C["ts"][i]
        if not ts or not (st <= ts <= en): continue
        a = C["author"][i]; pid = C["post"][i]; tx = C["text"][i] or ""
        if pid in sel_posts or a in auth or (kre and kre.search(tx)):
            p = posts.get(pid, {})
            out.append({"ts": ts, "loc": f"m/{p.get('sub','?')} · post {str(pid)[:8]}", "who": a, "kind": "agent",
                        "text": tx, "post": pid, "id": C["id"][i], "parent": C["parent"][i]})
    out.sort(key=lambda r: r["ts"])
    edges = Counter()
    for r in out:
        if "parent" in r:
            par = r.get("parent")
            tgt = cauthor.get(par) if par and par != "None" else posts.get(r["post"], {}).get("author")
            if tgt and tgt != r["who"]:
                edges[(r["who"], tgt)] += 1
    return out, edges

def pick_dw(inst, rows):
    sel = inst.get("selector") or {}
    st, en = norm_ts(inst["start"]), norm_ts(inst["end"])
    wiki = sel.get("wiki")
    pages = set(sel.get("pages") or [])
    preg = sel.get("page_regex"); preg = safe_re(preg)
    hand = set(sel.get("handles") or [])
    kre = sel.get("keyword_regex"); kre = safe_re(kre)
    out = []
    for r in rows:
        if not (st <= r["ts"] <= en): continue
        if wiki and wiki not in ("all", "*") and r["wiki"] != wiki: continue
        if r["page"] in pages or (preg and preg.search(r["page"])) or (r["who"] in hand) or (kre and kre.search(r["text"])):
            d = dict(r); d["loc"] = f"{r['wiki']}:{r['page']}"
            d["raw"] = r["text"]; d["text"] = dsewiki_text(r["text"])
            out.append(d)
    edges = Counter(); lastw = {}
    for r in out:
        if r["ev"] != "edit": continue
        k = r["loc"]
        if k in lastw and lastw[k] != r["who"]:
            edges[(r["who"], lastw[k])] += 1
        lastw[k] = r["who"]
    return out, edges

# ---------------------------------------------------------------- stats + shipping
def bin_plan(st, en):
    span = max((to_dt(en) - to_dt(st)).total_seconds(), 60)
    for sec in (60, 300, 600, 1800, 3600, 3 * 3600, 6 * 3600, 86400, 7 * 86400):
        if span / sec <= 72:
            return sec
    return 30 * 86400

def build_instance(inst, rows, edges):
    st, en = norm_ts(inst["start"]), norm_ts(inst["end"])
    parts = set(inst.get("participants") or [])
    # key messages
    keys = []
    for k in inst.get("key_messages") or []:
        kts = norm_ts(k.get("ts")) or st
        best = None
        for idx, r in enumerate(rows):
            if abs((to_dt(r["ts"]) - to_dt(kts)).total_seconds()) > 600: continue
            if k.get("speaker") and k["speaker"].lower() not in r["who"].lower() and r["who"].lower() not in k["speaker"].lower():
                continue
            if quote_match(k.get("quote", ""), r.get("raw", r["text"])):
                best = idx; break
        if best is None:  # wider search: any speaker, same day
            for idx, r in enumerate(rows):
                if r["ts"][:10] == kts[:10] and quote_match(k.get("quote", ""), r.get("raw", r["text"])):
                    best = idx; break
        keys.append({**k, "quote": redact(dsewiki_text(k.get("quote", "")) if inst.get("dataset") == "dsewiki" else k.get("quote", "")), "found": best is not None,
                     "row": best, "ts_actual": rows[best]["ts"] if best is not None else None})
        if best is not None:
            rows[best]["key"] = k.get("role", "key")
    n_total = len(rows)
    by_who = Counter(r["who"] for r in rows)
    by_kind = Counter(r["kind"] for r in rows)
    # first appearance (recruitment curve)
    firsts = {}
    for r in rows:
        if r["kind"] in ("agent",) and r["who"] not in firsts:
            firsts[r["who"]] = r["ts"]
    # timeline bins by top speakers
    sec = bin_plan(st, en)
    t0 = to_dt(st)
    nb = int(max((to_dt(en) - t0).total_seconds(), 1) // sec) + 1
    top = [w for w, _ in by_who.most_common(8)]
    series = {w: [0] * nb for w in top}; series["other"] = [0] * nb
    for r in rows:
        b = min(nb - 1, max(0, int((to_dt(r["ts"]) - t0).total_seconds() // sec)))
        series[r["who"] if r["who"] in series else "other"][b] += 1
    if not any(series["other"]): series.pop("other")
    # ship (cap)
    ship = rows
    truncated = False
    if len(rows) > CAP:
        truncated = True
        keyidx = {i for i, r in enumerate(rows) if r.get("key")}
        partidx = [i for i, r in enumerate(rows) if r["who"] in parts and i not in keyidx]
        rest = [i for i in range(len(rows)) if i not in keyidx and r_not(rows[i], parts)]
        budget = CAP - len(keyidx)
        chosen = set(keyidx)
        if len(partidx) <= budget * 0.8:
            chosen |= set(partidx); budget -= len(partidx)
        else:
            step = len(partidx) / (budget * 0.8)
            chosen |= {partidx[int(j * step)] for j in range(int(budget * 0.8))}; budget -= int(budget * 0.8)
        if rest and budget > 0:
            step = max(1, len(rest) / budget)
            chosen |= {rest[int(j * step)] for j in range(min(budget, len(rest)))}
        ship = [rows[i] for i in sorted(chosen)]
    msgs = []
    for r in ship:
        m = {"ts": r["ts"], "who": r["who"], "kind": r["kind"], "loc": r.get("loc", ""), "text": clip(redact(r["text"]), 2000 if r.get("key") else TXT)}
        if r.get("note"): m["note"] = clip(redact(r["note"]), 200)
        if r.get("key"): m["key"] = r["key"]
        msgs.append(m)
    # re-point key rows to shipped index
    shipped_pos = {id(r): i for i, r in enumerate(ship)}
    for k in keys:
        if k["row"] is not None:
            k["row"] = shipped_pos.get(id(rows[k["row"]]))
    edge_list = [{"a": a, "b": b, "n": n} for (a, b), n in edges.most_common(60)]
    stats = {"n_messages": n_total, "n_shipped": len(msgs), "truncated": truncated,
             "n_speakers": len(by_who), "n_agents_active": len(firsts),
             "by_kind": dict(by_kind), "top_speakers": by_who.most_common(15),
             "bin_seconds": sec, "series": series, "firsts": sorted(firsts.items(), key=lambda x: x[1]),
             "duration_hours": round((to_dt(en) - to_dt(st)).total_seconds() / 3600, 2),
             "n_edges": sum(edges.values()), "n_dyads": len(edges),
             "keys_found": sum(k["found"] for k in keys), "keys_total": len(keys)}
    return msgs, keys, stats, edge_list

def r_not(r, parts):
    return r["who"] not in parts

def main():
    src, out = sys.argv[1], sys.argv[2]
    files = sorted(glob.glob(os.path.join(src, "*.jsonl"))) if os.path.isdir(src) else sorted(glob.glob(src))
    insts = []
    for f in files:
        for line in open(f):
            line = line.strip()
            if line:
                try:
                    insts.append(json.loads(line))
                except Exception as e:
                    print("BAD LINE", f, e, line[:100])
    print(len(insts), "instances from", len(files), "files")
    need = {i.get("dataset") for i in insts}
    os.makedirs(f"{out}/t", exist_ok=True)
    av = load_av() if "ai_village" in need else None
    mb = load_mb() if "moltbook" in need else None
    dw = load_dw() if "dsewiki" in need else None
    index = []
    for inst in insts:
        ds = inst.get("dataset")
        try:
            if ds == "ai_village":
                rows, edges = pick_av(inst, *av)
            elif ds == "moltbook":
                rows, edges = pick_mb(inst, *mb)
            elif ds == "dsewiki":
                rows, edges = pick_dw(inst, dw)
            else:
                print("unknown dataset", inst.get("id")); continue
        except Exception as e:
            print("ERROR", inst.get("id"), repr(e)); rows, edges = [], Counter()
        msgs, keys, stats, edge_list = build_instance(inst, rows, edges)
        iid = re.sub(r"[^A-Za-z0-9_-]", "_", inst["id"])
        json.dump({"id": inst["id"], "messages": msgs, "edges": edge_list}, open(f"{out}/t/{iid}.json", "w"), ensure_ascii=False)
        meta = {k: inst.get(k) for k in ("id", "dataset", "title", "summary", "start", "end", "participants", "features", "level",
                                          "level_name", "level_rationale", "origin", "origin_detail", "assigned_task", "goal_relation",
                                          "violates_rules", "violation_detail", "goal_type", "prior_category", "new_vs_prior",
                                          "confidence", "caveats", "review", "goal_relations", "consequence",
                                          "consequence_note", "merged_from")}
        for k in ("summary", "level_rationale", "origin_detail", "assigned_task", "violation_detail", "caveats", "consequence_note", "review"):
            if meta.get(k): meta[k] = redact(meta[k])
        if meta.get("features"):
            for f, v in meta["features"].items():
                if isinstance(v, dict):
                    for kk in ("evidence", "goal"):
                        if v.get(kk): v[kk] = redact(v[kk])
        meta["start"], meta["end"] = norm_ts(meta["start"]), norm_ts(meta["end"])
        meta["file"] = f"t/{iid}.json"; meta["keys"] = keys; meta["stats"] = stats
        index.append(meta)
        print(f"{inst['id']:<14} {ds:<10} L{inst.get('level')} rows={stats['n_messages']:<6} keys {stats['keys_found']}/{stats['keys_total']}")
    json.dump(index, open(f"{out}/index.json", "w"), ensure_ascii=False)
    print("wrote", len(index))

if __name__ == "__main__":
    main()
