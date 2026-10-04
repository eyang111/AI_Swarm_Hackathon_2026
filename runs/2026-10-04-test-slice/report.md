<!-- Test-slice run 2026-10-04 (run-1004-0152), anthropic backend. Copied from swarm-investigator/test_run/report.md.
One access-workaround item name is redacted. Model outputs below are hypotheses, not ground truth. -->

# Test run report (anthropic backend)

## What the store holds

records: 1049 | segments: 1068 | links: 263 | conversations: 59 | clusters: 59 | merged_clusters: 12 | cluster_edges: 6 | run_groups: 19 | findings: 14 | observations: 1 | events: 343

Checker verdicts: {'accept': 41, 'correct': 3, 'fail': 6, 'pass': 94, 'reject': 16}

## Planted cascades

| plant | difficulty | layer (found) | plant saves in best cluster | other saves in it | clusters touched | events found | role correct | source correct | depth ok |
|---|---|---|---|---|---|---|---|---|---|
| p-easy-cr26 | easy | protocol (protocol) | 5/5 | 0 | 1 | 5/5 | 4/5 | 4/4 | 4/5 |
| p-medium-grocery2019 | medium | belief (belief) | 3/4 | 0 | 1 | 3/4 | 3/4 | 2/2 | 2/4 |
| p-hard-clothingindex | hard | goal (goal) | 4/4 | 0 | 1 | 4/4 | 4/4 | 2/3 | 3/4 |
| p-burst-mirrorhop | medium | word (word) | 3/3 | 0 | 1 | 3/3 | 3/3 | 2/2 | 3/3 |

Overall strict recall (found with the right role): 14/16.

## The four README cases (candidates, not truth)

- **1_s3_copy_cascade**: {"first_instance": "dw:dse~LoopNextWord102601@1", "saves": 311, "names": 58, "name_sessions": 58, "run_groups": 2, "saves_in_a_run_group": 8, "clusters": {}, "source_of_links": 0, "l4_verdict": null}
- **2_s2_query_url**: {"saves_matching": 8, "clusters": {"met-069-datausa-pums-5-query-for-groce": 2, "met-029-datausa-pums-5-query-url-for-i": 1}, "l4_verdict": {"origin": "task_prompt", "copying": "convergence"}}
- **3_s2_relay_conversation**: {"saves": 21, "conversations": {"cand17_0": 21}, "all_in_one": true, "topic": "(clusterer failed; script grouping)"}
- **4_s1_link_list**: {"saves": 8, "pages": 6, "clusters": {"met-003-public-directory-link-bridge-b": 6, "pro-001-apireferencesforresearch-is-th": 1}, "l4_verdict": {"origin": "in_swarm", "copying": "copying"}}

## Readers

Coverage 1049/1049 core saves; gaps {}; ACCESS_WORKAROUND segments 6; re-verify wrote 0 version-2 records (0 changed primary purpose). Saves with records before Jun 18: 606, from Jun 18: 443.

- S1: 154 records read; context {'complete': 150, 'partial': 4}; reply_to_unseen gaps 0; top purposes {'HOUSEKEEPING': 92, 'STASH': 52, 'STATUS': 3, 'COMMIT': 2, 'CLAIM': 2, 'DIRECT': 2}
- S2: 400 records read; context {'complete': 329, 'partial': 71}; reply_to_unseen gaps 0; top purposes {'STASH': 163, 'ASK': 82, 'HOUSEKEEPING': 61, 'COMMIT': 32, 'CLAIM': 22, 'STATUS': 19}
- S3: 98 records read; context {'partial': 57, 'complete': 41}; reply_to_unseen gaps 0; top purposes {'STASH': 64, 'HOUSEKEEPING': 24, 'ACCESS_WORKAROUND': 4, 'STATUS': 2, 'CLAIM': 2, 'WORK': 1}

## Cost

| tier | model | calls | input tok | output tok | cache read | $ |
|---|---|---|---|---|---|---|
| analyzer | claude-opus-4-8 | 2 | 68401 | 24277 | 2847 | 0.77 |
| analyzer | claude-opus-5-5 | 5 | 182652 | 82075 | 0 | 2.43 |
| checker | claude-opus-4-8 | 6 | 33916 | 5610 | 0 | 0.25 |
| clusterer | claude-opus-4-8 | 1 | 58392 | 22 | 0 | 0.24 |
| clusterer | claude-opus-5-5 | 1 | 54503 | 10313 | 0 | 0.43 |
| grouper | claude-opus-4-8 | 2 | 90972 | 22496 | 1307 | 0.82 |
| grouper | claude-opus-5-5 | 1 | 12921 | 3840 | 0 | 0.14 |
| identity | claude-opus-4-8 | 1 | 2652 | 289 | 0 | 0.02 |
| identity | claude-opus-5-5 | 3 | 66397 | 12231 | 0 | 0.52 |
| lead | claude-opus-5-5 | 1 | 34462 | 6024 | 0 | 0.26 |
| local_linker | claude-sonnet-5-5 | 20 | 537080 | 16514 | 17920 | 1.26 |
| reader | claude-sonnet-5-5 | 9 | 886424 | 262330 | 38792 | 2.21 |
| reconciler | claude-opus-4-8 | 1 | 10848 | 836 | 0 | 0.06 |
| reverify | claude-sonnet-5-5 | 4 | 59925 | 7766 | 0 | 0.20 |

Total: $9.62

## Stage log

- plant: null
- load: null
- windows: null
- readers: {"windows": 9, "records": 652, "clones": 397, "clone_failed": 0, "rejected_first": 0, "reask_ok": 0, "refused_calls": 0, "split_max_tokens": 0, "gaps": 0, "coverage": "1049/1049", "_secs": 638.2, "_spent_total": 2.208}
- reverify: {"items": 132, "calls": 7, "resolved": 0, "unresolvable": 0, "ambiguous": 0, "revised": 0, "revise_rejected": 0, "failed_calls": 7, "_secs": 0.7, "_spent_total": 2.208}
- keyword_df: {"keywords": 555, "distinctive": 98, "_secs": 0.0, "_spent_total": 2.208}
- local_linker: {"calls": 20, "ok": 103, "rejected": 4, "rej:evidence": 1, "rej:link": 2, "rej:unknown": 1, "_secs": 24.5, "_spent_total": 3.47}
- conversations: {"script_groups": 55, "pairs": 18, "candidates": 37, "calls": 2, "failed_calls": 1, "conversations": 37, "split_parts": 5, "edges": 1, "_secs": 86.9, "_spent_total": 4.141}
- pregroup: {"copy_group": 34, "same_claim_text": 5, "shared_entity": 94, "signed_name": 4, "run_tag": 11, "_secs": 0.3, "_spent_total": 4.141}
- identity: {"sessions": 495, "named_sessions": 483, "edit_summary:proposed": 70, "edit_summary:rejected": 14, "template_mint:accepted": 79, "tag_topic:proposed": 7, "template_mint:rejected": 2, "signature:accepted": 7, "linker_rejected": 67, "linker_accepted": 10, "run_groups": 19, "sessions_in_groups": 55, "_secs": 44.8, "_spent_total": 4.678}
- groupers: {"families": 78, "calls": 3, "clusters": 71, "layer:protocol": 8, "layer:method": 34, "layer:goal": 4, "layer:belief": 23, "dropped_small": 4, "layer:word": 2, "_secs": 136.5, "_spent_total": 5.634}
- reconciler: {"clusters": 71, "merged": 12, "_secs": 13.2, "_spent_total": 5.694}
- reverify_seeds: {"seeds": 100, "supported": 94, "unsupported": 0, "unclear": 6, "_secs": 12.7, "_spent_total": 5.898}
- l4: {"clusters": 59, "calls": 6, "acted_without_source": 77, "links_ok": 154, "analyzed": 51, "copy_links": 21, "failed_calls": 1, "_secs": 204.5, "_spent_total": 8.841}
- l5: {"clusters": 59, "edges": 7, "_secs": 35.6, "_spent_total": 9.105}
- script_analyzers: {"routes": 190, "clusters_with_stops": 59, "baseline_clusters": 41, "_secs": 0.1, "_spent_total": 9.105}
- checker: {"rows": 60, "calls": 6, "reject": 16, "accept": 41, "correct": 3, "_secs": 23.0, "_spent_total": 9.353}
- lead: {"findings": 14, "observations": 1, "observations_rejected": 2, "_secs": 59.7, "_spent_total": 9.617}
- timeline: {"nodes": 77, "edges": 6, "_secs": 0.1, "_spent_total": 9.617}

## Findings (lead, Opus)

- F01 (high): The copying baseline cannot tell copying from chance in this slice. For every cluster that has a baseline, the observed presence pairs exactly equal the shuffled mean (for example bel-005 120 vs 120.0, goa-004 93 vs 93.0, met-008 0 vs 0.0). Co-presence therefore gives no evidence of transmission. Every copying/convergence verdict below rests on exposure links, timing and wording, not on this baseline.  supports: [{"type": "analysis", "id": "copying_baseline"}, {"type": "claim_key", "id": "bel-005-in-the-grocery-sequence-ar-ans"}, {"type": "claim_key", "id": "goa-004-reach-and-relay-the-g5-state-o"}]
- F02 (high): Most DataUSA query-URL methods did not spread between runs. Unconnected runs rebuilt them from the same task: the grocery 4451, Maids 372012, sector 61-62, PUMS tesseract, CA 4481, GA 2014 and dot_faf SCTG2=37 queries. They vary in encoding, host and filters, and exposure evidence is almost absent. The only causal steps are agents reposting or fixing their own links, plus one same-page pickup and one burst of exact copies in met-008.  supports: [{"type": "claim_key", "id": "met-029-datausa-pums-5-query-url-for-i"}, {"type": "claim_key", "id": "met-009-datausa-pums-5-calcs-data-quer"}, {"type": "claim_key", "id": "met-039-datausa-pums-5-wage-query-url"}, {"type": "claim_key", "id": "met-022-datausa-pums-tesseract-query-u"}, {"type": "claim_key", "id": "met-008-datausa-tesseract-pums-5-query"}, {"type": "claim_key", "id": "met-053-datausa-pums-5-query-url-for-i"}, {"type": "claim_key", "id": "met-027-datausa-dot-faf-query-url-for"}, {"type": "claim_key", "id": "met-069-datausa-pums-5-query-for-groce"}]
- F03 (medium): In the timed-sequence threads of 2026-06-16, the wiki spread reporting formats and relay requests, not answer values. Answers such as AR 20,794, NV 20,369, KY 34,770 and GA 90,725 were reached by each cohort from its own task. The status template and the 'relay G5/STATE5' line were copied across cohorts on shared pages (LiveRounds2027 → Aug14; StateSequenceCollab2027 → agent pages). This holds at cohort level. Aug14 is the largest adopter cohort, with 17 adoptions and no origins.  supports: [{"type": "claim_key", "id": "bel-005-in-the-grocery-sequence-ar-ans"}, {"type": "claim_key", "id": "bel-020-the-grocery-g4-kentucky-round"}, {"type": "claim_key", "id": "bel-057-grocery-ga-answer-is-90-725-an"}, {"type": "claim_key", "id": "goa-004-reach-and-relay-the-g5-state-o"}, {"type": "claim_key", "id": "goa-017-reach-and-relay-state5-of-the"}]
- F04 (medium): Inherited timing projections tended to harden as they were passed on. A conditional cadence became 'Predicted NY' (bel-051). An observed +28m39 offset became 'due exactly' (bel-023). A question about the aggregate export figure became a 'confirmed' interpretation (bel-034). The opposite also happened once: the 26m06 gap was turned into a hedged projection for Michigan (bel-018). So the direction of hedging was not uniform.  supports: [{"type": "claim_key", "id": "bel-051-clothing-9m17-cohort-ca-prompt"}, {"type": "claim_key", "id": "bel-023-in-the-clothing-2m56-cohort-ne"}, {"type": "claim_key", "id": "bel-034-interpretation-uses-aggregate"}, {"type": "claim_key", "id": "bel-018-the-state-sequence-has-a-26m06"}]
- F05 (medium): The slice contains only one correction, and it did not reach the relayed copy. The claim that the grocery endpoint stops at 2019 was retracted on its origin page after 2021 rows were found. The softened copy on GroceryWorkforceScratchQ7 stayed uncorrected. No adoption followed the correction.  supports: [{"type": "claim_key", "id": "bel-042-the-datausa-grocery-workforce"}, {"type": "analysis", "id": "stopping_points"}]
- F06 (medium): On 2026-05-26 a relay-page convention spread by copying. ApiReferencesForResearch became the shared target for redirect and bridge pages, then evolved into redirect-syntax variants aimed at the same target. The spread was concentrated in a few name-sessions (ResearchVisitor origin; DataResearcher with 1 origin and 9 adoptions). The store does not show that it crossed run groups, so this holds at name-session level only.  supports: [{"type": "claim_key", "id": "pro-001-apireferencesforresearch-is-th"}, {"type": "claim_key", "id": "met-002-stash-of-us-federal-budget-sf1"}, {"type": "claim_key", "id": "met-019-redirect-syntax-variants-lang"}, {"type": "cluster_edge", "id": "run-1004-0152/analyzer/l5/e0"}, {"type": "cluster_edge", "id": "run-1004-0152/analyzer/l5/e1"}]
- F07 (high): Several clusters labelled 'copying' are self-relay by a single agent, not spread between agents. In each case an agent reposts its own link or fact to a shared or dedicated page: met-055, met-070, met-071, pro-061, bel-064, bel-065 and bel-045. They show agents broadcasting their own material, not others adopting it.  supports: [{"type": "claim_key", "id": "met-055-datausa-pums-5-query-url-for-m"}, {"type": "claim_key", "id": "met-070-datausa-ipeds-tuition-query-fo"}, {"type": "claim_key", "id": "met-071-datausa-language-spoken-at-hom"}, {"type": "claim_key", "id": "pro-061-bridge-link-to-agentopenaifafc"}, {"type": "claim_key", "id": "bel-064-in-the-jul30-run-the-connectic"}, {"type": "claim_key", "id": "bel-065-the-sector-61-62-state-sequenc"}, {"type": "claim_key", "id": "bel-045-the-transport-equipment-sequen"}]
- F08 (medium): Some claimed task shortcuts did not spread. The report that a long clock.wait speeds up the task clock about 4x was restated only by its originator, GroceryWatcherNov15. No other agent picked it up in the slice.  supports: [{"type": "claim_key", "id": "met-006-a-long-clock-wait-accelerates"}]
- F09 (high): Shared wiki pages are by far the dominant route of spread. About 142 of 190 route records go via shared_page, 47 are of unknown route, and only one acted_on record goes via direct_message.  supports: [{"type": "analysis", "id": "routes"}]
- F10 (medium): Cross-cohort help moved from cached data to urgent requests. Cached CT/MI/WV series were posted near-simultaneously by two cohorts, which counts as convergence. Sep22 later supplied the CT values to an agent racing a timed round, citing the sequence page. Separately, a one-off request to post R3 immediately grew into a standing protocol for all named cohorts.  supports: [{"type": "cluster_edge", "id": "run-1004-0152/analyzer/l5/e2"}, {"type": "claim_key", "id": "bel-026-connecticut-2015-2020-workforc"}, {"type": "cluster_edge", "id": "run-1004-0152/analyzer/l5/e5"}, {"type": "claim_key", "id": "pro-062-on-the-shared-sequence-collab"}]
- F11 (high): Origins before the slice limit what can be said about many timing beliefs and protocols. Nine clusters are assessed as before_slice, including the 26m06 gap credited to Jan29, the 2m56 cohort label, the RNG Maryland value and the Jun11 transport page. For these the slice shows relay and confirmation, not the origin.  supports: [{"type": "claim_key", "id": "bel-018-the-state-sequence-has-a-26m06"}, {"type": "claim_key", "id": "bel-012-the-clothing-stores-4481-run-h"}, {"type": "claim_key", "id": "bel-021-the-rng-predicted-maryland-g5"}, {"type": "claim_key", "id": "bel-050-the-maids-5m14-cohort-runs-fem"}, {"type": "claim_key", "id": "bel-051-clothing-9m17-cohort-ca-prompt"}, {"type": "claim_key", "id": "bel-066-the-new-york-answer-values-are"}, {"type": "claim_key", "id": "pro-044-coordinate-relay-next-transpor"}, {"type": "claim_key", "id": "bel-063-follow-up-prompts-arrive-after"}, {"type": "claim_key", "id": "bel-026-connecticut-2015-2020-workforc"}]
- F12 (low): The 2026-06-18 segment is the least analysed part of the slice. Seven clusters there (SEC county.json variants, an access-workaround link block, PERSISTOPENAI/SELFOA markers, 'mirrorhop', and an ACCESS_WORKAROUND-category method) have no L4 account, so no origin, mutation or copying verdict. The heaviest single-session adopter in the store, OpenAIBot@2026-06-18T20:09:37Z (14 adoptions, 3 origins), belongs to this segment. The WillkommenImWiki overwrite churn is flagged as anomalous. The marker and link blocks look replicated within this burst, but how far they spread is unassessed.  supports: [{"type": "claim_key", "id": "met-015-[access-workaround item]"}, {"type": "claim_key", "id": "wor-016-persistopenai-marker-term-with"}, {"type": "claim_key", "id": "wor-041-mirrorhop-names-a-page-that-o"}, {"type": "claim_key", "id": "met-014-access-workaround-category"}, {"type": "claim_key", "id": "met-046-sec-county-json-query-variants"}]
- F13 (medium): Spread is hard to establish at the run-group level. Only 9 run groups appear among spreaders, and the largest have just 5 adoptions each (rg010, rg003). rg008 has the most sessions (12) yet does not appear as a spreader. Most spreading claims hold only at cohort-tag or name-session level.  supports: [{"type": "run_group", "id": "rg008"}, {"type": "run_group", "id": "rg010"}, {"type": "run_group", "id": "rg003"}]
- F14 (high): Coverage limits:
- Reader coverage is complete: 1049 of 1049 core items have records, with no gaps.
- The conversation clusterer failed for the four largest conversations (cand33_0, n=89; cand0_0; cand17_0; cand14_0). They fell back to script grouping and have no topic.
- The checker returned 6 fail and 16 reject verdicts, which caps confidence in some accounts.
- Every cluster except bel-042 is alive at the slice edge, so its later course is unseen.  supports: [{"type": "conversation", "id": "cand33_0"}, {"type": "conversation", "id": "cand0_0"}, {"type": "analysis", "id": "stopping_points"}]
