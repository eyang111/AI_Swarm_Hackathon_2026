# Swarm Atlas vs Swarm Investigator on DSEWiki

**Short answer:** on everything both systems can be scored on, the Investigator does as well or better. It is the only one that can be tested against known truth, and it scored 16/16 there. It recovered most of what the Atlas found: 82% of the Atlas's episodes fully, against 54% of the Investigator's items found fully by the Atlas. It cites about seven times more source records. The two tie on coverage, and both need a second checking pass.

The Atlas still does things the Investigator does not do at all. It grades how far each episode got toward a swarm, it judges harm, and it covers two more datasets.

All numbers come from `compare.py`. They are written to `results.json`.

## What is compared

| | Swarm Atlas (baseline) | Swarm Investigator |
|---|---|---|
| Built by | Sandra Luo, with Claude agents | the team, with a staged pipeline |
| How it reads DSEWiki | 3 agents, one per time slice, each reads its slice and writes episodes directly. Review passes follow: consistency, alignment and recall gaps. | 816 narrow model calls: readers, linkers, groupers and analyzers. Every write is checked against the source by script. An adversarial checker reviews a sample. |
| Output on DSEWiki | 87 episodes, each graded on a swarm ladder from level 0 to level 5 | 502 items (beliefs, goals, protocols, methods, words), with 5,618 role-tagged events |
| Definitions | Michael Flood's swarm definitions (Flood wrote the definitions, not the Atlas) | its own five spread layers |

The investigator's design doc names the Atlas as a baseline (`swarm-investigator/DESIGN.md`, section 2). DSEWiki is the only dataset both ran on, so the comparison covers DSEWiki only.

## Scorecard

| Metric | Atlas | Investigator | Edge |
|---|---|---|---|
| Planted cascades found with the right role | not testable | **16 / 16** | Investigator |
| Coverage of the 651 pages edited by 3+ agents | **90.3%** (87.3% as published) | 88.3% | tie |
| Coverage of the 65 strongest of those pages | 63 / 65 | **65 / 65** | tie |
| Share of the other system's findings it also found, fully | 54% of 430 items | **82%** of 87 episodes | Investigator |
| Same, fully or partly | 98% | 97% | tie |
| Swarms at level 5 that the other system also found, fully | n/a | 37 / 42 | — |
| Source records cited | 741 quotes, by time and speaker | **5,141 saves**, by save ID | Investigator |
| Spread measured (copying vs chance, routes, corrections) | no | **yes** | Investigator |
| Swarm level, harm and three datasets | **yes** | no | Atlas |
| First-pass output changed by review | 48% of grades¹ | 32% of checked links | neither |
| Model cost | not recorded | $190 ($147 without a cancelled duplicate batch) | — |

¹ Mostly because the rules were re-aligned to Flood's post, not because the first readings were wrong. On the Atlas's earlier AI Village and Moltbook pass, vetting corrected or dropped 38% of 566 claims.

## How each metric was measured

**1. Planted truth.** The investigator ran on a copy of DSEWiki with four made-up cascades added: easy, medium, hard, and one inside the Jun 18 burst. That is 16 events with known roles. It found all 16 with the right role, and each cascade landed in one clean cluster. It named the right source for 9 of the 12 events that have one. The Atlas never ran on the planted copy. The raw dump is not in the repo and could not be downloaded here, so the Atlas could not be rerun. This is the one metric with real ground truth, and only one system has a score on it.

**2. Coverage.** The Atlas's own recall check lists 651 DSEWiki pages edited by three or more agent handles, with a script-made strength score for each. A page counts as covered by the Atlas if an episode names it, by page list or page pattern, within the episode's time span. It counts as covered by the Investigator if a save on it belongs to any item. The Atlas covers 588 pages and the Investigator 575. 526 are covered by both, 62 only by the Atlas, 49 only by the Investigator and 14 by neither. Weighted by page strength, the scores are 95.0% and 94.3%. Of the 65 strongest pages, the Atlas missed two (`fractal:RecentChanges` and `dse:ApiReferencesForResearch`) and the Investigator missed none.

**3. Cross-recall, judged blind.** Did each system find what the other found? Sixteen Claude judges read two unlabelled catalogs: "E" (the Atlas episodes) and "I" (the Investigator items). They did not know which was the baseline. For each entry they decided whether the other catalog described the same phenomenon: match, partial or none. They started from page-and-time candidates and also searched by keyword. The full rubric is in `judging/RUBRIC.md`.

| Direction | Match | Partial | None | Two-judge agreement |
|---|---|---|---|---|
| Atlas episodes found by the Investigator (87) | 71 (82%) | 13 | 3 | 97%, κ 0.89 (all 87) |
| Investigator items found by the Atlas (430)² | 232 (54%) | 188 | 10 | 85%, κ 0.72 (107) |

² Items with at least two editors, without the four planted cascades, which the Atlas never saw.

For the Atlas, finding an Investigator item depends a lot on the item's size. It fully found 79% of items with 10 or more editors, 56% of items with 5 to 9 editors, and 42% of items with 2 to 4 editors. Most "partial" verdicts are a narrow item, such as a specific link set or answer value, that sits inside a broader Atlas episode without being named in it. Part of the gap is therefore granularity: the Investigator splits the same activity into about five times as many entries.

**4. Evidence.** The Atlas cites 8.5 quotes per episode, by timestamp and speaker. Its review checked all 741 quotes against the raw saves. The Investigator cites 10.2 saves per item by save ID: 5,141 distinct saves and 5,618 role-tagged events (origin, adopt, challenge, correct). It also has 2,299 within-item causal links that passed its evidence rule and 45 links between items. Its quotes are checked as exact substrings when they are written.

**5. What gets measured.** The Investigator puts numbers on spread:
- **Copying vs chance:** 168 of 387 items spread more than chance.
- **Routes:** 2,971 recorded.
- **Corrections:** 49 items were corrected and 440 were still alive at the end of the data. 631 adoptions came after a correction had been posted.
- **Identity:** 159 groups of names that are likely the same run.

The Atlas gives none of these. It does grade each episode's swarm level, origin and consequence for people, which the Investigator does not.

**6. Stability under review.** 40 of the 84 Atlas episodes that can be traced back to the first sweep changed level in later passes (48%). Most moved up: 15 from level 4 to 5 and 12 from level 3 to 5, after the rules were re-aligned to Flood's post. The Investigator's checker reviewed 60 sampled links. It accepted 41, corrected 18 and rejected 1, so 32% changed. Most corrections were a session reposting its own block, which had been counted as adoption by another agent. Neither first pass is clean without review.

**7. Cost.** The Investigator's full run cost $190.11, including a $43.30 duplicate reader batch that was cancelled. The Atlas did not record its cost.

## What each one missed

**Missed by the Investigator.** The judges agreed on three episodes:
- the Cashier Skills RCA 2018 two-cohort relay;
- the Data Africa Mozambique rainfed-crops relay;
- one writer using thirteen handles on a grocery probe page.

It also only partly captured the mass recreation of pages that moderators had deleted. It does not load deletion events.

**Missed by the Atlas.** Ten items, most of them two-editor link stashes or answer values in task families that no episode covers, such as El Paso, an SLP sequence and Dallas restaurants. The largest is a query pattern for a digital-library task that 17 editors used. Many partial verdicts are specific link sets and conventions inside the Jun 18 SEC cascade, which the Atlas treats as one episode.

## Caveats

- **Only one ground-truth metric, and only one system has it.** The rest compare the systems with each other, not with the truth.
- **The judges are Claude, like both systems.** They saw no system names, but they could tell the formats apart. Agreement between judges is reported for every double-judged entry.
- **The judges compared catalogs, not raw text.** They decided whether two descriptions refer to the same thing, not whether either one is correct.
- **Page matching is lenient.** It uses Atlas page patterns such as `(?i)grocery`. The page-overlap figures in `results.json` show how much the strict and lenient versions differ.
- **The Investigator's checker and lead stages were done by hand by Claude in the project thread.**
- **Short IDs.** Investigator items are referred to by short IDs such as `met-612`. These map one-to-one to cluster IDs in `runs/2026-10-04-full-run/timeline.json`. This keeps the item text, which can name access workarounds, out of these files.

## Files and how to reproduce

| File | What it is |
|---|---|
| `compare.py` | computes every number above from files in the repo (standard library only) |
| `results.json` | its output |
| `judging/RUBRIC.md` | the judges' instructions |
| `judging/A_batch*.json`, `B_batch*.json` | what each judge was asked to decide |
| `judging/out/*.json` | every verdict with matched IDs and a short reason; `_j2` files are the second judge |

```bash
python3 comparisons/atlas-vs-investigator/compare.py                      # recompute results.json
python3 comparisons/atlas-vs-investigator/compare.py --build-judge-inputs # rebuild the judges' catalogs and batches
```

The catalogs are rebuilt locally and not committed, because they hold item text.
