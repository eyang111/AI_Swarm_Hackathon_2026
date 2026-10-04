# Pipeline features that may be unnecessary (review of run #1, 2026-10-04)

Evidence: `code/` as of 05:10, `test_run/investigation.db`, `stage_log.json`, `report.md`, `calls/reader/*.json`.
I read only; nothing was edited or run against the API. The bar for each item was whether it changes what the
pipeline says about **how ideas spread**. Costs are from run #1 on the test slice ($9.62 in total).

## Cut (no effect on the spread results)

| Feature | What it does now | Evidence it adds nothing | Run #1 cost |
|---|---|---|---|
| **Seed re-verify** (`reverify.run_seeds`) | Sonnet checks 100 seed segments and, on a fail, clears `is_seed` and writes a loose end | 94 supported, 0 unsupported, 6 unclear. Nothing reads `loose_ends`. `is_seed` only appears as `seed=` in the L4 view, and the L4 prompt never mentions seeds. | $0.20 |
| **Opus conversation clusterer** (`cluster.py`, model part) | Writes topic lines and splits script conversation groups | It failed on the 4 largest conversations, which fell back to the script grouping. It made 5 splits and 1 conversation edge. Topics go only to the lead's stats list and score case 3. L4 and the copying baseline use the script membership, which exists without this call. | $0.67 |
| **Unused reader output fields** | `entities`, `addressed_to` (to the `mentions` table), keyword `distinctive`/`from_context`, `secondary_purposes`, claim `about`, flags `coded_token`/`addresses_human` | No downstream module reads them: `mentions` is write-only, and keyword distinctiveness is recomputed by the `keyword_df` script. Together they are about 18% of reader output characters (measured on the 9 reader calls). | ~10% of reader cost |
| **Write-only schema** | `loose_ends`, `mentions`, `conversation_edges`, the `conversation_presence` view, the empty `aggregates` tables | Never read by any stage. Dropping them is cleanup, not a saving. | $0 |

## Cut unless a rerun shows value

- **Record re-verify pass** (`reverify.run`) and the reader fields that exist only to feed it: `context_status`, `context_needs`, `uncertain_fields`, `reader_confidence` (about 3.5% of reader output). In run #1 all 7 calls failed, so it has never shown any value. The halo and context pack already gave 1049/1049 coverage with 0 `reply_to_unseen` gaps. If the fixed version is never run on a slice, nobody has evidence it is needed.
- **Opus run-identity linker** (`identity.py`, model part). It accepted 10 of 77 medium edges. The script's strong edges (79 template mints and 7 signatures) produce most of the 19 run groups. Lead finding F13 says run-group-level spread was thin either way. $0.54. You could keep it just for the cross-run claims, but it is the weakest Opus tier per dollar.

## Keep (checked because they looked cuttable, but they earn their place)

- **Local linker** ($1.26, 13% of spend). 49 of its 103 links join segments that keywords and claim text leave in separate families, and the two ends of 36 of those land in the same final cluster. Without it there are 68 families instead of 78. Most of these links are `reply_to` (61 of 103).
- **Reconciler** ($0.06). 12 merges out of 71 clusters.
- **Checker** ($0.25). It rejected 16 L4/L5 rows, mostly cases where a shared page or a shared task answer was claimed as exposure.
- **L5 cross-cluster edges** ($0.26). Lead findings F06 and F10 cite them, and they are the timeline's only arrows.
- **L4 mutations and phases.** Mutations carry F04, the hedging finding. Phases split the timeline nodes.
- **Script conversations.** 277 pairs of cluster members share a conversation across different pages, which is exposure candidates that same-page checks miss. One flag: `cand0_0` holds 71 saves across 57 pages, which looks like an over-merged S3 group.

## Other things the review turned up (not cuts)

- `flag_task_content` is unused, yet "shared task answer read as exposure" is the checker's most common rejection. Passing it into the L4 view would put that field to work instead of dropping it.
- L4 lists `same_run_group` as exposure evidence. In spread terms a shared run means self-relay (F07), not spread between agents.
- The timeline draws only cluster-to-cluster edges (6 in run #1), so the within-cluster spread links (154 L4 links) don't appear in the main visual.
