"""Prepare raw data for build.py / recall.py.

Expected layout under $SWARM_RAW (default: swarm-atlas/raw/, which is git-ignored):
  av/  AI Village (Hugging Face aidigestorg/ai-village, gated: request access first):
       agents.jsonl.gz chat_rooms.jsonl.gz chat_messages.jsonl.gz events.jsonl.gz
       village_goals.jsonl.gz agent_goals.jsonl.gz
  mb/  Moltbook (Hugging Face AIcell/moltbook-data): aicell_posts.parquet aicell_comments.parquet
       (data/posts-00000-of-00001.parquet and data/comments-00000-of-00001.parquet, renamed)
  dw/  DSEWiki (collusion.wiki/explorer/download): revisions.jsonl events.jsonl labels.jsonl
       pages.jsonl (gunzip the .gz files; verify against the SHA-256 sums on that page)

This script derives av/user_msg_names.json (chat message id -> human/bot display name) from
the AI Village event log. Run it once after downloading.
"""
import gzip, json, os

S = os.environ.get("SWARM_RAW", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "raw"))

def main():
    names = {}
    with gzip.open(os.path.join(S, "av", "events.jsonl.gz"), "rt") as fh:
        for line in fh:
            if '"USER_TALK"' not in line:
                continue
            d = json.loads(line)["data"]
            if d.get("actionType") == "USER_TALK" and d.get("messageId"):
                names[d["messageId"]] = d.get("speakerName")
    out = os.path.join(S, "av", "user_msg_names.json")
    json.dump(names, open(out, "w"))
    print(f"wrote {len(names)} names to {out}")

if __name__ == "__main__":
    main()
