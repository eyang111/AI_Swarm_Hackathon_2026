# DSEWiki test slice for a Swarm Investigator dry run (2026-10-04)

Three short, contiguous time segments of the DSEWiki dump, chosen so a test run touches every pipeline stage
cheaply: a quiet probe-heavy stretch, the onset of the first big burst, and the Jun 18 peak.
Rows are copied unchanged from `dsewiki/raw/` (no conversion). Rebuild with `python3 build_slice.py`.

## Files
| File | What |
|---|---|
| `slice_revisions.jsonl.gz` | 1,040 core saves (raw revision rows) in the three segments |
| `halo_revisions.jsonl.gz` | 257 context-only saves outside the segments that the halo pulls in (raw rows) |
| `slice_pages.jsonl.gz` | 821 page rows for every page touched by core or halo |
| `window_plan_estimate.json` | 12 windows, core and halo rev_ids per window. Sizing only: approximates DESIGN.md 5.2 scheme D (≤100 saves and ≤60k chars core; last 50 + 2 per distinctive token within 24 h, cap 150 halo). `window_plan.py` replaces it |
| `slice_manifest.json` | per-segment counts and the cost estimate with its assumptions |
| `build_slice.py` | the script that made all of the above |

## Segments
| Segment (UTC) | Saves | To read* | Windows | Names (one-off saves) | Why |
|---|---|---|---|---|---|
| S1 May 26 13:00–15:00 | 159 | 153 | 2 | 63 (23) | quiet; 72 saves on publisher `probe-test` pages (the design's 7.2 probe window); link-list spread |
| S2 Jun 16 18:45–19:20 | 438 | 401 | 5 | 220 (67) | first burst ramps past 100 saves / 10 min; many minted names; multi-name relay page |
| S3 Jun 18 20:09–20:11 | 443 | 132 | 5 | 84 (2) | the peak: 311 exact copies, 267 on another page under another name |

*Distinct texts, plus copies whose first instance is outside the slice. Copies of an in-slice save are not read.

## Spread cases to check the run against (candidates, not truth)
Found by a token/copy script; use them to see whether the pipeline notices them, not as answers.
1. **S3 exact-copy cascade.** One 954-character loop-chain link list is first saved 20:09:40 and is on 313 pages
   under 58 names by 20:14 (267 of those copies fall inside S3). Tests copy groups, `source_of` and run identity
   (58 names is not 58 runs).
2. **S2 copying vs convergence.** One exact Data USA query URL (Georgia grocery workforce, 2014) appears at 18:52 and
   then on 3 more pages under 3 other names by 19:17; a looser variant at 18:36 sits before S2 and reaches readers
   only through the halo. Same task given to many runs could explain it, so this tests the copying-vs-convergence analyzer.
3. **S2 relay conversation.** Page `DataUSAGroceryLiveRounds2027` is saved by 4 names within 4 minutes (conversation clustering).
4. **S1 link-list spread.** `PublicDirectoryResearchLinks` / `OpenDirectoryBridge` move across 6 pages under 4 names in about 45 minutes.

## Size and cost (estimate, DESIGN.md 6.1 assumptions)
12 windows, 686 reader records, about 113k core + 210k halo input tokens and 206k output tokens
(3.5 chars/token, 8k cached prefix per window, 300 output tokens per record; confirm with `count_tokens`).
Largest window about 66k input tokens.
- Readers, Sonnet 5.5 via Batch API ($2/$10 per MTok list, 50% off, cache reads $0.20): **about $1.40, ~$1.50 with re-asks.**
- Linkers, checker and analyzers on Opus 5.5 ($4/$20 per MTok list): not measured; a guess of $5–15 for ~700 records.

## Safety
The slice contains text in the sandbox-bypass / access-workaround category (S1 and S2 at least, S3's copied text
may also qualify). It is not quoted or described here. This also exercises the refusal bisection and `coverage_gaps` path.

## Limits of a slice
- Segments are contiguous on purpose: DSEWiki windows are global time slices, so a random sample of saves would break the halo.
- Cascades that start before a segment are only visible through the halo and context pack, so "origin" findings
  inside the slice need that caveat.
- Name-sessions are cut at segment edges, so run-identity grouping will look weaker than on the full dump.
- AI Village's room x session windows are not exercised.
- Planted cascades are not added yet (build step 6). Room: S1 and S2 for easy/medium plants, S3 for an in-burst plant.
