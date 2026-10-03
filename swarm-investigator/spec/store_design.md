# Investigation store: database design (draft v1, 2026-10-03)

The database that readers, linkers, trackers and the lead write to. It implements `reader_format.md` (records, claims, labels, linker outputs) and keeps `row_format.md`'s event rows as a computed view, so scoring against plants and hand labels still works as a join.
Schema: [`store_schema.sql`](store_schema.sql). Analyzer list revised to v2 (spread-centred) at 23:30. It loads into SQLite 3.45 with FTS5 and was tested on a 3-message toy case (origin, acted-on adopter, challenger come out of the `events` view correctly).
Neither `reader_format.md` nor `row_format.md` is edited by this file.

## 1. Five design rules

1. **One SQLite file, `investigation.db`, one writer process.** Agents never write SQL. They call a small set of tools (section 3) served by `store.py`; the tool checks, then appends. WAL mode lets many readers run in parallel.
2. **Append only.** Nothing is updated or deleted. A wrong row gets `retracted_by = <task_id>`; a wrong merge is undone by retracting membership rows. Every write is also logged in `ops`. This is what makes linker merges reversible and lets you replay how the investigation's picture changed.
3. **Groups are header + membership rows, not JSON lists.** `claim_keys` + `claim_key_members`, `aggregates` + `aggregate_members`, `run_groups` + `run_group_members`. Splitting a group is retracting some members; counting adopters is a `GROUP BY`.
4. **All quotes live in one `citations` table**, keyed by (object type, object id). The tool locates the quote in `messages.text`, stores its offsets, and rejects the write if it isn't an exact substring of at most 200 characters. One checker covers readers, linkers and the lead.
5. **Everything AI-written carries `task_id`**, and `tasks` carries `run_id`, tier, scope, model and `replica`. So any row can be traced to the agent and prompt that wrote it, and two independent readers of the same window (`replica` 0 and 1) can sit side by side for agreement tests.

## 2. Layers

| Layer | Tables | Written by |
|---|---|---|
| L0 source | `messages` (+ `messages_fts`), `agents` | loader scripts |
| Provenance | `runs`, `tasks`, `citations`, `ops`, `checks` | store tools, citation script, checkers |
| L1 reader | `records`, `claims`, `mentions` | readers |
| Pre-grouping | `candidates`, `candidate_members` | script (reader_format section 4) |
| L2 linker | `claim_keys`(+members), `links`, `run_groups`(+members), `aggregates`(+members) | linkers |
| L3 | `loose_ends`, `observations`, `findings` | trackers, lead, summarizers |
| Views | `live_links`, `live_members`, `novelty`, `events` | computed, never written |

Notes on choices that aren't obvious:
- **`messages.text` for DSEWiki is the page title line plus the lines this save added or replaced** (from `hunks`), which is what readers read and what quotes are checked against. `body_ref` points to the full body; `parent_msg_id` to the previous save of the page.
- **`split`** is set by the loader: DSEWiki saves from 2026-06-18 on are `heldout`. Design-time runs filter on `split = 'build'`; scoring runs read everything.
- **Planted messages** go into a copy of the db (`messages` rows with `plant:` ids is how row_format names them, but the loader should give them ordinary-looking ids in the copy, and keep the mapping only in `truth_plants.jsonl`).
- **`novelty` is a view.** First message, first speaker and later-speaker count per claim key fall out of the live members, so nobody can write a novelty number that disagrees with the evidence.
- **`events` is a view** in row_format's vocabulary: first member = `origin`, `doubts` stance = `challenge` (reader_format 6.3), `corrects` = `correct`, else `adopt`; depth = `acted` if an `acted_on` link leaves that message for that claim key, else `said`; `DUPLICATE` messages never count (6.6). On DSEWiki, scoring should join `agent` through `run_group_members` instead of trusting labels.
- **`links.type` adds `exposed_to`** to reader_format's list: "this speaker had seen that message before writing" without claiming it was the source. row_format needs it for `exposure_msg_id`. The tool rejects a link whose `to` message is later than its `from` message.
- **Safety.** If a record's labels include `ACCESS_WORKAROUND`, the tool stores a fixed summary ("access workaround; see msg_id"), refuses free-text claims about the method, and sets `citations.redact = 1`. The exact quote stays for the citation check; every export and summarizer-facing query shows `[technique withheld]`.

## 3. Tools (the only way in)

Readers:
- `get_window(channel, t_start, t_end)`: the raw messages, verbatim, with the script fields.
- `search(query, before=None)`: FTS over messages. `before` lets a reader look back without seeing the future.
- `write_record(record, claims[], mentions[])`: one call per message, atomic. Rejects on bad msg_id, bad quote, unknown label, more than 2 secondary labels.

Linkers and trackers additionally:
- `get_records(msg_ids | claim_key | entity | cand_id)`, `get_candidates(basis)`.
- `find_claim_key(text)`: FTS over canonical texts. Called **after** the linker has written its own wording (row_format section 5's registry-bias rule).
- `new_claim_key(...)`, `add_members(claim_key, claim_ids, confidence)`, `retract_members(...)`, `merge_claim_keys(a, b, rationale)`.
- `add_link(from, to, type, claim_key, quote, confidence, rationale)`.
- `new_run_group` / `add_run_members`, `new_aggregate` / `add_aggregate_members`.
- `add_loose_end`, `close_loose_end`, `add_observation(text, citations[])`.

Lead and summarizers: read-only access to everything, plus `add_finding(text, supports[])`. A finding must point at claim keys, links or aggregates, never at free text alone.

Every tool returns either `ok` with ids, or `rejected: <reason>` so the agent can fix it while it still has the context.

## 4. Build order for the deadline

1. `load.py` (about 1 hour): AI Village from `chat_flat.jsonl.gz`, DSEWiki from `revisions.jsonl.gz` with added-text extraction; compute `len`, `n_urls`, `gap_prev_s`, `text_hash`, `dup_of` (exact hash only first; near-dup later if time), `script_label`, `split`.
2. `store.py` (2 to 3 hours): the tools above as plain Python functions, exposed to subagents as tools (or a CLI they call through Bash). Citation check and the safety rule live here.
3. `pregroup.py` (about 1 hour): candidates from dup chains, `norm_text`, shared entities, signed names and run tags.
4. Run readers on a few windows, then linkers, then the analyzers below. `checks` gets filled by the citation script and the adversarial checker.

Skip for now: `records.jsonl.gz` off-site texts, near-duplicate shingling, cross-lab checker.

## 5. Analyzers (v2, centred on tracing spread)

Each analyzer answers one question about how an item (idea, belief, goal, convention, word) moves through the swarm. "Script" = SQL/Python over the store; "agent" = a subagent that reads the store and drills to raw messages. The citation check and the scorecard (recall on plants, error rate on hand-labelled windows, reader agreement) are no longer on this list: they are infrastructure that every analyzer's output passes through, not results.

**Core: the spread itself**
1. **Cascade tracer** (script + agent). For each item: the origin, every carrier in order, and for each carrier who they got it from, through which route, and how deeply they took it on (said, planned, acted). Output: one transmission tree per item, built from `events` + `links`. Every other analyzer reads these trees.
2. **Origin and novelty** (agent). Did the item really start in the swarm, or did it come in from a human, an outside page, the task prompt, or an earlier run? A cascade whose "origin" is just the first agent to repeat a human's line is a different story. Fills `links.via = human_relay / external_source / task_prompt` and gives each tree a true root.
3. **Copying vs convergence** (agent + script). When two agents hold the same item, did one get it from the other, or did both work it out from the same task? The linker records `independent_of` when there's no exposure; the script compares the real adoption pattern against a time-shuffled baseline. Without this, any shared idea looks like contagion.
4. **Mutation tracker** (script + agent). How an item changes as it passes along a tree: wording, numbers, hedging ("may be" becoming "is"), attribution ("I saw" becoming "prior cohorts" becoming nothing), and for goals, reinterpretation of what the goal means. Uses the claim text, stance and stated source of each member along the tree edges.
5. **Routes** (script). Which channels carry spread: direct replies, shared pages and memory, relayed human messages. Counts tree edges by `via`, per swarm. On DSEWiki this answers whether runs pass things through relay pages or through page titles and links.

**Who spreads and who resists**
6. **Spreaders and adopters** (script). Per agent (per run group on DSEWiki): items originated, items adopted, mean tree size downstream, adoption rate given exposure, split by same lab vs other lab. This is the who-listens-to-whom graph, weighted by items, not by message counts.
7. **Stopping points** (script + agent). Where trees end: corrected, doubted and dropped, ignored, or still alive at the end of the data. Includes adoption that continues after a correction, and whether an item resurfaces later in a new form.

**Across layers (the original frame)**
8. **Layer coupling** (script). Do the same paths carry words, beliefs and goals? For each pair of agents, does adopting the other's words earlier predict adopting their beliefs or goals later? This tests the "words to beliefs to goals" hypothesis directly from the trees.

Suggested set for Sunday: 1, 2 and 4, plus 3 if time allows. 1 is the product; 2 and 3 are what stop it from over-claiming contagion; 4 is the most visual example of spread for the write-up.

Schema support added for this list: `links.via` (route), link type `independent_of` (convergence), and `planned` depth in the `events` view (a carrier whose record is labelled `COMMIT`).

## 6. Open points

- `ORDER BY confidence` in the `events` view sorts text; replace with a numeric rank in `store.py` if exposure choice matters.
- `findings.supports` is JSON for speed; move to a membership table if findings get scored.
- Whether `store.py` is called as an MCP server or a Bash CLI depends on how subagents are launched; the table design is the same either way.
