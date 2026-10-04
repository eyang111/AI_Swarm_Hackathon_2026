# Swarm Investigator: pipeline code (test-slice build, 2026-10-04)

Implements DESIGN.md v4 end to end on the DSEWiki test slice. Python 3.11, `anthropic` SDK 1.x, SQLite with FTS5.

## Run

```
cd swarm-investigator/code
python3 run.py --backend mock                          # offline, no API calls; heuristic stand-ins; prints a cost estimate
SI_FAKE_API=1 python3 run.py --backend anthropic        # offline test of the real API code path (fake HTTP server)
python3 run.py --backend anthropic --budget 25          # the real run; needs ANTHROPIC_API_KEY in the environment
python3 run.py --backend anthropic --from l4            # resume from a stage on the existing db
python3 run.py --backend anthropic --batch-all          # every tier via the Batch API (half price, slower)
```
`SI_RUN_DIR` moves the outputs (default `../test_run/`). `SI_MOCK_REFUSE_IDS=<msg_id,...>` makes the mock or fake API
refuse any request containing those ids, to exercise the refusal bisection.

Outputs in `test_run/`: `investigation.db` (the store), `report.md` + `scores.json` (scoring and costs),
`timeline.json` + `timeline.html` (L6 graph, no quotes), `calls/<tier>/*.json` (every response and its usage),
`stage_log.json`. Truth for the plants is in `test_run/truth/` and is read only by `score.py`.

## Stages (DESIGN.md 3 and 5.4 order)

| Stage | File | Model | What it writes |
|---|---|---|---|
| plant | `plant.py` | script | 4 planted cascades (16 saves) into a copy of the slice; truth to `truth/` |
| load | `load.py` | script | `messages`: title + added lines, `removed_text`, `copy_of`, DUPLICATE/EMPTY, features, FTS rebuild |
| windows | `window_plan.py` | script | scheme D windows: 100 saves / 60k chars core, last-50 + token-routed halo, context pack |
| readers | `readers.py` | Sonnet 5.5, Batch API | records, segments, claims, keywords, task_content flag, citations; copies cloned; re-ask once; refusal bisection -> `coverage_gaps` |
| keyword_df | `pregroup.py` | script | `keyword_df` (distinctive = df 2..50) |
| local_linker | `local_linker.py` | Sonnet 5.5 | local links, max 3 outgoing per segment |
| conversations | `cluster.py` | script | conversations and members (script grouping) |
| pregroup | `pregroup.py` | script | candidates (copy groups, same claim text, shared keywords, signed names, run tags) |
| identity | `identity.py` | script | name-sessions, `identity_edges` (medium edges stay proposed), run groups |
| groupers | `groupers.py` | Opus 5.5 | clusters (claim keys) over segments, seeds, copies expanded |
| reconciler | `groupers.py` | Opus 5.5 | merges across families |
| l4 | `analyzers.py` | Opus 5.5 | causal/sequence steps as links, copy-group `source_of`, origin, mutations, copying vs convergence |
| l5 | `analyzers.py` | Opus 5.5 | `cluster_edges` citing both sides |
| script_analyzers | `analyzers.py` | script | routes, spreaders at three identity levels, stopping points, shuffle baseline |
| checker | `analyzers.py` | Opus 5.5 | accept/correct/reject on L4 links and L5 edges; rejected rows retracted |
| lead | `analyzers.py` | Opus 5.5 | findings (must cite store objects), observations (must cite quotes) |
| timeline | `timeline.py` | script | L6 graph + HTML viewer behind the export screen |
| score | `score.py` | script | plant recall, the four README cases, reader stats, cost |

Shared: `config.py` (models, prices, caps), `store.py` (schema + checked write tools), `llm.py` (calls, batch,
cost ledger, budget guard), `common.py` (prompt views), `schema_patch.sql`, `fake_api.py`.

## Where the code differs from the spec

1. **Every model tier is one-shot structured output**, not a tool loop. The script assembles each call's raw context
   up front (`store.get_raw`, FTS search on the readers' search hints, page neighbours, candidate targets). Same
   reason as DESIGN 6.1 for readers: cost and predictability. Tool loops can be added per tier later.
2. **Clusters are over segments** (pipeline_v2 10): `claim_key_segments` holds membership; `live_members`,
   `novelty` and `events` are rebuilt over segments in `schema_patch.sql`.
3. **Citation check** accepts a quote that differs only in whitespace or Unicode normalization, then stores the exact
   span from the message, so every stored citation is still an exact substring. Quotes over 200 characters are cut.
4. **Reader fields kept only in reader_format.md** (versions, cloned_from) are added as columns on `records`.
5. **Segment spans** come from a `start_quote` per segment (models are poor at character offsets); a segment runs to
   the next segment's start.
6. **Halo** is also capped at 120k characters, which keeps the Jun 18 peak windows near 55k input tokens.
7. **Run groups** are built over name-sessions (`member_kind = 'session'` added to the check constraint).
8. The **checker retracts** links and cluster edges it rejects; the `checks` table keeps the verdicts.
9. Not built: `aggregates` (same-purpose collapse), replica reader agreement, AI Village loading, blind hand labels
   (Peyton's to make before looking at output).

## Changes after run #1 (2026-10-04)

- **Cut** (DESIGN 15, approved by Peyton): seed and record re-verify (`reverify.py` moved to `archive/`), the Opus
  conversation clusterer (script grouping only), the Opus run-identity linker (medium identity edges stay `proposed`),
  reader fields nothing read (`entities`, `addressed_to`, keyword `distinctive`/`from_context`, `secondary_purposes`,
  claim `about`, flags `coded_token`/`addresses_human`, `context_status`, `context_needs`, `uncertain_fields`,
  `reader_confidence`), and write-only tables (`loose_ends`, `mentions`, `conversation_edges`,
  `conversation_presence`, `aggregates`; dropped in `schema_patch.sql`). Mock estimate for the slice: $8.54 -> $6.97.
- **Kept and used**: the reader's `task_content` flag now goes to L4, which treats task-produced matches as independent.
- **L4 evidence rule**: co-presence (same page or conversation) is sequence, not cause; it allows at most a
  low-confidence `exposed_to` when backed by a non-task match.
- **Copying baseline**: members exposed to an earlier member (other editor, same page or conversation) vs 200 random
  same-segment draws, with a p-value. The old version shuffled order of an order-free count, so it always matched.
- **Model calls**: one retry, then halving up to 3 levels for any failed non-reader call; text after a server-side
  fallback boundary is parsed; declined hops are billed. Opus 4.8 / Opus 5 prices added for fallbacks.
- **Error log**: `errlog.log(stage, kind, detail, **ctx)` appends to `test_run/errors.jsonl`; report.md has an Errors section.
