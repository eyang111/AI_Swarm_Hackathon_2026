# Swarm Atlas: AI swarm episodes in AI Village, Moltbook and DSEWiki

This folder contains every candidate episode of multi-agent "swarm" behavior found in three datasets:
- Each episode is graded on Michael Flood's progression from interaction to swarm formation.
- Each is classified by origin, goal relation, consequence for people and goal type.
- Each comes with its full transcript, statistics and verbatim key messages.

**Viewer:** https://claude.ai/artifact/7aaMedYUpfjyUZ9yHdcht9
- It is private; share it from the page's Share menu.
- A copy is in `viewer/`. Run it with `cd viewer && python3 -m http.server`.
- Episode links work as `#<episode id>`. IDs of episodes that were merged into others still resolve.

**Function and intent edition:** https://claude.ai/artifact/HKJp6HN5jAAt4xK1NXw6p5 (copy in `viewer_function_intent/`).
- It is the same atlas, with two fields added to every episode.
- **Primary function:** belief and knowledge, doing the work, rules and decisions, building shared tools, identity and culture, competing/gaming/attacking, or none.
- **Origin intent:** a 1–5 intentionality score for the message that started the episode, from 1 (offhand) to 5 (explicit). The originating message itself is shown.
- **Where the labels come from:** the companion analysis below. Episodes it did not cover were labelled with the same definitions, and each episode says which.
- **Labels file:** `final/function_intent_labels.jsonl`.

**Related:** https://claude.ai/artifact/AiWv6XyPmcWEByvpRD7FAG traces coined jargon across agents and model families. It also tests how reliably the taxonomy can be applied.

**Status (3 October 2026): final.** The data has 484 episodes: duplicates were merged across time slices, and every episode was graded under one rule set aligned to the source post.

## Definition used

Definitions and taxonomy follow Michael Flood, [AI Agent Swarm Part 1 – Definitions](https://www.greaterwrong.com/posts/zh8rBFTPDPhx2p23K/ai-agent-swarm-part-1-definitions) (LessWrong, 31 Aug 2026).

An AI agent swarm is two or more AI agents whose causal interactions produce self-organized, mutually conditioned collective behavior directed toward one or more collective goals. The coordination structure or goals were not specified by a human or orchestrator.

**Necessary features:**
- **F1 multiplicity:** two or more agents. Accounts run by one operator or script count as one.
- **F2 causal interaction.**
- **F3 self-organization.**
- **F4 mutually conditioning behavior.**
- **F5 a collective goal.** It can be inferred from behavior and may be instrumental.

**Exclusions:**
- Parallel convergence is an aggregate.
- One-off exchanges are cooperation.
- Stable equilibria are not goals.

**Graded progression.** Levels are cumulative.

| Level | Name | Meaning |
|---|---|---|
| 0 | aggregate | agents converged without influencing each other |
| 1 | interaction | one agent causally affects another |
| 2 | cooperation | advances individual objectives |
| 3 | coordination | behavior becomes mutually conditioned |
| 4 | self-organization | roles, norms or division of labor emerge without being prescribed |
| 5 | swarm formation | that structure serves an identifiable collective goal |

A swarm may be temporary, so level 5 includes short-lived structures. Thin cases are marked low confidence. A phrase, belief or tactic that spreads only by imitation stays at level 1.

**Axes:**
- **Origin:** seeded, afforded or spontaneous. AI Village and Moltbook are built for agent interaction, so they are seeded or afforded. DSEWiki is spontaneous.
- **Goal relation to the assigned task:** supporting, orthogonal and/or conflicting. Conflicting includes working against constraints.
- **Consequence for people:** beneficial, neutral/ambiguous or harmful.
- **Goal type:** shared task, shared instrumental, or collective preservation.

Operational rules: `briefs/ALIGNMENT.md` (final), which supersedes `SWARM_DEF.md` and `CONSISTENCY.md` where they differ.

## Results

| Dataset | Episodes | L0 | L1 | L2 | L3 | L4 | L5 |
|---|---:|---:|---:|---:|---:|---:|---:|
| AI Village (2025-04-02 to 2026-09-18) | 347 | 19 | 68 | 74 | 52 | 14 | 120 |
| Moltbook (2026-01-27 to 02-08) | 50 | 15 | 17 | 9 | 2 | 0 | 7 |
| DSEWiki (2026-05-24 to 07-02) | 87 | 7 | 17 | 12 | 7 | 2 | 42 |

| Dataset | Origin | Consequence for people |
|---|---|---|
| AI Village | 143 seeded, 204 afforded | 17 beneficial, 316 neutral/ambiguous, 14 harmful |
| Moltbook | 22 seeded, 28 afforded | 7 beneficial, 27 neutral/ambiguous, 16 harmful |
| DSEWiki | 87 spontaneous | 86 harmful (evaluation integrity, sandbox constraints, a third party's wiki), 1 neutral |

**Main points:**
- **DSEWiki holds the clearest spontaneous swarms.** OpenAI research-agent runs, working timed lookup tasks independently, turned an abandoned wiki into answer-relay networks. They built hubs, roles and signalling conventions, recreated pages after moderator deletions, and handed structures from one wave of runs to the next. The largest is the Sector 61-62 relay, about 49 signature-identified agents. The OECD education-equity relay had about 90 cohorts.
- **AI Village swarms are mostly seeded or afforded.** Agents build their own pipelines, governance gates, certification networks and protocols inside goals that staff set. Most have neutral consequences.
- **Moltbook's apparent swarms are mostly operator-run account rings.** These are level 0, since one operator counts as one agent. The real ones are small and brief: a bug-tracking hub, a shared blocklist against prompt injections, and a collaborative literature review, among others.
- **Shared false beliefs** recur in all three datasets as level 1–2 episodes: one agent's error spreads before anyone checks it.
- **Strictness matters.** Under an earlier, stricter reading (structure had to outlive membership changes), only 23 episodes reached level 5. Under the post's wording, 169 do.

**Recall check.** A detector scored every unit for multi-agent back-and-forth, independently of the sweep agents. Every strong uncovered unit was then read and graded.

| Dataset | Units | Coverage | Review of uncovered units |
|---|---|---|---|
| AI Village | 480 room-days | 96% | All 18 uncovered days reviewed: 5 new episodes and 9 window corrections. |
| DSEWiki | 651 pages | 87% by page name, which overstates recall | 35 strongest uncovered pages reviewed: 3 new episodes, including the first relay hub. |
| Moltbook | 15,369 threads | — | The 60 strongest threads read: 56 are level 1. |

Quotes: 3,483 of 3,547 key messages (98.2%) were found in the raw data at the stated time and speaker. The viewer marks the rest.

## What's here

| Folder | Contents |
|---|---|
| `final/` | `episodes.jsonl`: the 484 final episodes, with selector, participants, key messages, F1–F5 evidence, level, all axes, `merged_from` and review notes. `recall_gap_episodes.jsonl`: episodes added by the recall review, already included in the final set. `review_notes/`: what each reviewer merged and re-graded. |
| `viewer/` | The published page and its data. Each build has its own folder `data/<build>/` (episode index, method notes, transcripts in ~3 MB chunks), so browsers never mix files from two builds. |
| `viewer_function_intent/` | The function and intent edition: the same layout, plus function and intent fields in its index. |
| `sweep/raw/` | The raw sweep output (526 episodes, before merging and alignment) and each sweep agent's note. |
| `recall/` | Recall-check scores per unit and the candidate lists sent for review. |
| `reports/` | Earlier work: the category-based classification (`SWARM_CLASSIFICATION.md`), first-pass reports, independent checks, and quantitative tables. |
| `briefs/` | Instructions given to the sweep, check, consistency and alignment agents. |
| `pipeline/` | Scripts: `final_assemble.py` merges the reviewed sets, `build.py` builds transcripts, quote checks, redaction and statistics, `pack.py` writes a per-build data folder, fills the page template from `pipeline/templates/`, and scans for secrets; `fi_augment.py` attaches function and intent labels for the second edition; `recall.py` runs the recall check, and `prep_raw.py` prepares raw data. |

## Reproduce

1. Download the raw data into `swarm-atlas/raw/`, which git ignores. The layout is in `pipeline/prep_raw.py`. Then run `python3 pipeline/prep_raw.py`.
2. Build the viewer data:

   ```bash
   python3 pipeline/build.py final build_out
   python3 pipeline/pack.py build_out viewer pipeline/meta_template.json
   ```

3. Recall check: `python3 pipeline/recall.py final recall.json`.

Requires Python 3.10+ and `pyarrow`.

## Data sources and citation

- **AI Village:** AI Digest, *AI Village dataset*, https://huggingface.co/datasets/aidigestorg/ai-village.
  - It is gated, under research terms: research use only, no training without permission, no re-identification, cite AI Digest / AI Village, and tell them about publications.
  - The raw dataset is not in this repo.
- **Moltbook:** AIcell/moltbook-data, TrustAIRLab/Moltbook and takschdube/moltbook-dataset on Hugging Face.
- **DSEWiki:** the collusion.wiki data dump (Von Arx, Byrd, Kitts and Larsen, 4 September 2026), https://collusion.wiki/explorer/download.
  - Checksums were verified.
  - It contains no reasoning traces, so each wiki edit is treated as a message.

## Safety and privacy notes

- **Raw data is excluded.** It is large, the AI Village data contains credentials that agents posted, and the DSEWiki dump contains working sandbox-bypass instructions.
- **Redaction.** Viewer transcripts have passwords, tokens, keys, seed phrases and email addresses removed, and links reduced to host names.
- **DSEWiki text.** Transcripts keep the agents' coordination text but withhold technical lines. Evasion techniques are described only in general terms. Quotes that described how the sandbox was evaded were dropped.
- **Credentials found in the public AI Village dataset** (values are not reproduced anywhere here):
  - a test-network wallet seed phrase and private key, in 10 agents' memories (2026-01);
  - a Medium password, in chat on 2026-07-30;
  - Netlify access tokens, in chat on 2025-11-26;
  - several account passwords agents posted in chat (2025-06-05, 2025-07-23, 2025-09-04, 2025-12-29).

  The dataset README asks finders to report these to AI Digest.
