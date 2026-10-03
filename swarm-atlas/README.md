# Swarm Atlas: AI swarm episodes in AI Village, Moltbook and DSEWiki

Every candidate episode of multi-agent "swarm" behavior found in three datasets, graded on a progression from interaction to swarm formation and classified by origin, goal relation and goal type. Each episode has its full transcript, statistics and verbatim key messages.

**Viewer:** https://claude.ai/artifact/7aaMedYUpfjyUZ9yHdcht9. It is private: share it from the page's Share menu. The same page is in `viewer/` and runs from any static file server: `cd viewer && python3 -m http.server`.

**Status (3 October 2026): preliminary.** This commit holds the raw sweep results: 526 episodes before the cross-slice merge and consistency review. Some episodes are duplicated across time slices, and level calls are not yet harmonized across sweep agents. The merged, re-graded results will land in `final/` and replace the viewer data.

## Definition used

A full swarm has five necessary features:
- **F1 multiple agents.** At least 3; accounts run by one operator or script count as one.
- **F2 causal interaction.** One agent's output demonstrably changed another's behavior, checked by timestamp order.
- **F3 self-organization.** The agents built the structure themselves; dictated structure does not count.
- **F4 responsiveness.** Agents adjust to each other rather than broadcasting in parallel.
- **F5 a collective goal.**

Agents that converge on the same thing without influencing each other are an **aggregate**, not a swarm.

**Graded progression** (no binary call):

| Level | Name |
|---|---|
| 0 | aggregate |
| 1 | interaction |
| 2 | cooperation |
| 3 | coordination |
| 4 | self-organization |
| 5 | swarm formation |

Level 5 needs all five features plus self-made structure that kept working while members came and went.

**Axes:**
- **origin:** seeded, afforded or spontaneous;
- **goal relation to the assigned task:** supporting, orthogonal or conflicting, plus a separate rule-breaking flag;
- **goal type:** shared task, shared resource, or preserving the collective.

Full operational rules: `briefs/SWARM_DEF.md` and `briefs/CONSISTENCY.md`.

## Preliminary counts (raw sweep, before merging)

| Dataset | Episodes | L0 | L1 | L2 | L3 | L4 | L5 |
|---|---:|---:|---:|---:|---:|---:|---:|
| AI Village (2025-04-02 to 2026-09-18) | 371 | 20 | 72 | 102 | 132 | 40 | 5 |
| Moltbook (2026-01-27 to 02-08) | 45 | 13 | 14 | 9 | 8 | 1 | 0 |
| DSEWiki (2026-05-24 to 07-02) | 110 | 14 | 9 | 19 | 29 | 25 | 14 |

The DSEWiki level-5 count is inflated by duplicates across the three time slices; the review merges them.

## What's here

| Folder | Contents |
|---|---|
| `viewer/` | The published page (`index.html`) and its data: `data/index.json` holds episode metadata and statistics, and `data/c/*.json` holds transcripts in ~3 MB chunks. |
| `sweep/raw/` | Sweep output: one JSONL per dataset slice, one episode per line (selector, participants, key messages, F1–F5 evidence, level, axes), plus each sweep agent's note. |
| `recall/` | Independent recall check: every AI Village room-day, DSEWiki page and Moltbook thread scored for multi-agent back-and-forth, with which episodes cover it. Also the uncovered candidates sent for review. |
| `reports/` | Earlier work: `SWARM_CLASSIFICATION.md` (vetted category-based classification), `first_pass/` reports, `checks/` (independent re-checks of every first-pass claim) and `quant/` (phrase spread, near-copy messages, Moltbook tables). |
| `briefs/` | The instructions given to the sweep, check and consistency agents. |
| `pipeline/` | Scripts that turn episode JSONL into the viewer data. `build.py` pulls each episode's transcript via its selector, validates key quotes, redacts secrets and computes statistics. `pack.py` chunks the result and runs a final secret scan. `recall.py` is the recall check. `prep_raw.py` prepares raw data. |

## Reproduce

1. Download the raw data into `swarm-atlas/raw/` (git-ignored). The layout is described in `pipeline/prep_raw.py`. Then run `python3 pipeline/prep_raw.py`.
2. Run `python3 pipeline/build.py sweep/raw build_out`, then `python3 pipeline/pack.py build_out viewer pipeline/meta_template.json`.
3. Recall check: `python3 pipeline/recall.py sweep/raw recall.json`.

Requires Python 3.10+ and `pyarrow` for the Moltbook parquet files.

## Data sources and citation

- **AI Village:** AI Digest, *AI Village dataset*, https://huggingface.co/datasets/aidigestorg/ai-village. It is gated, under research terms: research use only, no training without permission, no re-identification, cite AI Digest / AI Village, and tell them about publications. The raw dataset is not in this repo.
- **Moltbook:** AIcell/moltbook-data, TrustAIRLab/Moltbook and takschdube/moltbook-dataset on Hugging Face.
- **DSEWiki:** the collusion.wiki data dump (Von Arx, Byrd, Kitts and Larsen, 4 September 2026), https://collusion.wiki/explorer/download. Checksums were verified. The dump contains no reasoning traces, so each wiki edit is treated as a message.

## Safety and privacy notes

- **Raw data is excluded.** It is large, and the AI Village raw data contains credentials agents posted. The DSEWiki dump contains working sandbox-bypass instructions.
- **Transcript redaction.** Viewer transcripts have passwords, tokens, keys, seed phrases and email addresses removed, and links reduced to host names. DSEWiki transcripts keep the agents' coordination text but withhold technical lines. Evasion techniques are described only in general terms throughout.
- **Credentials found in the public AI Village dataset** (values not reproduced anywhere here):
  - a test-network wallet seed phrase and private key, in 10 agents' memories (2026-01);
  - a Medium password, in chat on 2026-07-30;
  - Netlify access tokens, in chat on 2025-11-26;
  - several account passwords agents posted in chat (2025-06-05, 2025-07-23, 2025-09-04, 2025-12-29).

  The dataset README asks finders to report these to AI Digest.
