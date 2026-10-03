# Download the AI Village text tables (gated HF dataset; needs HF_TOKEN with access).
# Xet CAS hosts may be blocked by egress policy; HF_HUB_DISABLE_XET=1 uses the plain CDN redirect.
import os
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
from huggingface_hub import hf_hub_download
REV = "838b4150303ca8228e8edb432d8b8ccae353d258"
FILES = ["README.md", "SCHEMA.md", "CHANGELOG.md", "manifest.json", "agents.jsonl.gz", "agent_goals.jsonl.gz",
         "village_goals.jsonl.gz", "villages.jsonl.gz", "chat_rooms.jsonl.gz", "summaries.jsonl.gz",
         "chat_messages.jsonl.gz", "computer_use_sessions.jsonl.gz", "events.jsonl.gz",
         "agent_memories.jsonl.gz", "computer_use_turns.jsonl.gz"]
for f in FILES:
    p = hf_hub_download("aidigestorg/ai-village", f, repo_type="dataset", local_dir="av", revision=REV,
                        token=os.environ["HF_TOKEN"])
    print(f, os.path.getsize(p))
