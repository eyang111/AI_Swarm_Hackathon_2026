# DSEWiki agent identity: findings and proposed method

Thread "DSEWiki agent identity", 2026-10-04. Whole dump used (holdout dropped). Scripts: `identity_scripts/feat.py` (per-save features) and `identity_scripts/sim.py` (name matching). All numbers below come from `dsewiki/raw/revisions.jsonl.gz` and `pages.jsonl.gz`. No body text is quoted here; names only.

"Added text" means the lines a save inserted or replaced (from `hunks`), not the whole page body. Whole bodies carry other agents' earlier text, so signatures and tags in them belong to whoever wrote them first.

## 1. Short answer

- **1,332 names are used for exactly one save** (of 3,103 names; 899 more saves are anonymous).
- **729 of them look like a more common name** (5+ saves), but that resemblance is almost worthless. Agents draw names from one shared vocabulary (Agent / OpenAI / Research / Helper + a topic word + a date tag + digits), so "ResearchHelperX99" resembling "ResearchHelper" says nothing. String-matched pairs share a page, an IP range or a date tag about as often as random pairs (table in section 2).
- **The useful similarity is between one-off names themselves.** 382 one-off names share a template with another name once trailing digits are removed. The clearest case is a run that mints a fresh name per save: 15 names of the form `Sep13WatcherX` + 6 random digits, saved one after another within about an hour. 148 names embed a Unix timestamp, and 82% of those timestamps are within an hour of the save time, so the name was generated at the moment of saving.
- **IP ranges carry no identity signal.** Two consecutive saves by the *same* name within 60 seconds share `ip16` only 2.1% of the time, against 1.6% for two random saves. The agents' outbound address rotates per request across cloud ranges. `ip16` should be dropped from the run-identity linker.
- **The publisher's `page_family_cohort` is not independent evidence.** It equals the date tag in the page title on 4,048 of 4,049 pages that have both. It is a regex over titles, so agreement with it is circular.
- **Date tags are cohort labels, not dates or runs.** 4,035 saves have a date tag in the name (337 distinct, e.g. `Nov18`), and 3,958 of them differ from the actual save date. A name's date tag matches a date written in that save's added text 81% of the time (2,763 of 3,393), so agents carry their tag consistently. But one tag spans several topics and usually several days (median 80 hours), so a tag groups many runs.
- **Realistic ceiling:** about a third of saves can be put into a confident run group; the rest can only be grouped by cohort tag or by content. Section 4 has the breakdown.

## 2. Measurements

### One-off names vs common names

| match type (one-off name vs name with 5+ saves) | pairs | same page | same ip16 within 30 min | same date tag | shared cohort tag in text |
|---|---|---|---|---|---|
| same stem after removing digits and generic words | 3,636 | 5.6% | 1.0% | 0.1% | 2.6% |
| edit distance 2 or less | 89 | 3.4% | 4.5% | 1.1% | 1.1% |
| token overlap (Jaccard 0.67 or more) | 1,594 | 5.2% | 2.8% | 0.6% | 3.7% |
| shared rare word (used in 5 or fewer names) | 128 | 14.1% | 3.9% | 0.8% | 2.3% |
| random common name, weighted by activity | 3,996 | 4.3% | 1.1% | 0% | 0.4% |

Only rare shared words lift page overlap above random, and only to 14%. A matched one-off name typically has several equally good candidates (180 of the 729 have 10 or more).

### What stays stable within a name

Consecutive saves by the same name (names with 5+ saves) compared with saves by different names within the same hour:

| feature | same name | different names |
|---|---|---|
| `ip16` | 2.8% | 1.5% |
| same page | 30.9% | 24.0% |
| title date tag | 37.5% | 7.4% |
| exact edit summary (`change_summary`) | 42.3% | 1.5% |
| cohort tag in added text | 66% (n=89) | 0% |
| wiki | 99.8% | 97.5% |

Edit summaries are a strong style marker when distinctive. Generic ones ("test", "coordination update") are shared by hundreds of names and must be down-weighted by frequency.

### Other signals

- **Signatures in added text** (a line like "-- SomeName", or "from/by SomeAgentName"): only 47 saves; 33 sign with their own name, 14 with a different one. Too rare to matter much, but a differing signature is a direct link candidate.
- **Page chains:** 90% of consecutive saves on the same page within 10 minutes switch names (relay pages are shared), so page adjacency alone is weak.
- **Big names are mostly one session.** The top names (`AgentRelent` 317 saves, `AgentMassPointer13` 187, `MapHelper` 184...) do nearly all their saving on Jun 18, with a few stray saves days later. Their long spans come from stragglers, which may be a different run reusing the name. `MapHelper` has 29 saves under 5 seconds apart on different pages, so it is either parallel workers in one run or several runs sharing one name.
- **Names were not copied from the wiki.** None of the 40 most-used names appears in any page text before its first save (one exception, 2 mentions), so name reuse is not name contagion.

## 3. Proposed method

**Unit.** A *name-session*: one name's saves, split wherever the gap exceeds 6 hours. Anonymous saves are their own singleton sessions. This splits stragglers off the big names without deciding yet whether they belong.

**Step 1, scripted candidate edges** (`identity_candidates.py`, cheap, deterministic). Each edge records its type and the measured evidence:

| edge | rule | strength |
|---|---|---|
| template mint | same name after stripping trailing digits; template has a non-generic word; within 6 hours | strong |
| timestamp mint | name embeds a Unix time within an hour of the save, and the rest of the name matches another session | strong |
| signature | added text signs with another session's name | strong, after a check that the line is not quoted from older text |
| edit summary | same distinctive summary (used by 5 or fewer names), within 48 hours | medium |
| tag + topic | same date tag and a shared non-generic topic word, within 48 hours | medium |
| append chain | next save on a page extends the previous save's own added lines within 10 minutes | medium (to measure) |
| ip16 | none | dropped, measured as noise |

**Step 2, merge.** Strong edges merge sessions directly (union-find). Medium edges go to the run-identity linker, which reads the added text of both sides and judges whether they are one run: same task, same phrasing habits, references to its own earlier notes, and no contradictions. Contradictions that block a merge: two different date tags in the added text, or saves under 5 seconds apart on different pages (parallel actors).

**Step 3, store it reversibly.** Edges go in an `identity_edges` table (session_a, session_b, edge type, evidence, decided_by, status proposed/accepted/rejected, version). Run groups are a view over accepted edges, so a bad merge is undone by rejecting one edge. This follows the versioning used for reader records in reader_format section 2a.

**Step 4, report at three levels.** Every per-agent result (spreaders, adoption rate) is computed at name-session level, run-group level and cohort (date tag) level. A claim that only holds at one level is flagged. DESIGN.md issue 6 already asks for the label vs run-group comparison; cohort level is the fallback for saves no run group can claim.

**Evaluation without ground truth.**
- *Synthetic renaming:* take distinctive one-session names, give each save a fresh fake name, blank the original, and measure how many the pipeline puts back together (recall) and how many land with the wrong group (precision).
- *Contradiction rate:* share of accepted groups that contain parallel saves or conflicting date tags.
- Don't use `page_family_cohort` agreement as validation (it is derived from titles).

## 4. How far identity can get

Rough split of the 14,591 saves with the rules above (distinctiveness is a crude heuristic, so treat these as approximate):

| group | saves | share | one-off names in it |
|---|---|---|---|
| repeated distinctive name within 24 h | 4,730 | 32% | 0 |
| template cluster within 6 h | 207 | 1.4% | 74 |
| template cluster within 48 h | 161 | 1.1% | 37 |
| same date tag + topic word within 48 h | 56 | 0.4% | 41 |
| repeated distinctive name over more than 24 h (may be several runs) | 2,388 | 16% | 0 |
| repeated generic name (e.g. `ResearchHelper`, 35 variants over 28 days) | 4,970 | 34% | 0 |
| one-off name with a date tag only | 322 | 2.2% | 322 |
| one-off name, no signal | 858 | 5.9% | 858 |
| anonymous | 899 | 6.2% | 0 |

So about 35% of saves land in confident groups from scripts alone. Generic names (34%) need the linker to split them by session and content. About 14% (one-off names with no signal plus anonymous saves) can only be linked by what they wrote. Of the 1,332 one-off names, roughly 150 can be linked with some confidence and about 320 more only to a cohort.

The dump has no run key, so run identity cannot be confirmed for any save. For spread analysis this means claims like "agent X spread idea Y to agent Z" should be stated at the coarsest level they survive. On this dump, spread between *cohorts* and between *pages* is more defensible than spread between *runs*.
