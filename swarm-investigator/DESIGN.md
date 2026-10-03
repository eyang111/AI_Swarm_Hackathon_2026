# Swarm Investigator: design (consolidated, 2026-10-03)

One document for everything designed so far. It summarizes and links the spec files in `spec/`, which stay the
detailed source for each part. Where the files disagreed, this document follows the most recent decision and says
what it reconciled (section 9). Section 10 lists issues to expect when running it on the DSEWiki (German wiki) incident.

Status: design only. No pipeline code (`load.py`, `store.py`, `window_plan.py`, `pregroup.py`, prompts) exists yet.

| Spec file | What it holds | Status |
|---|---|---|
| [`spec/row_format.md`](spec/row_format.md) | event rows (investigator output and truth format), planted and hand-labelled truth, matching and scores | v1; its section 5 (store) is superseded by `store_design.md` |
| [`spec/reader_format.md`](spec/reader_format.md) | reader record per message, purpose labels, missing-context flags (2a), linker outputs | approved by Peyton |
| [`spec/store_design.md`](spec/store_design.md) + [`spec/store_schema.sql`](spec/store_schema.sql) | SQLite store `investigation.db`, write tools, analyzers v2 | draft, not yet approved |
| [`spec/windowing_and_linkers.md`](spec/windowing_and_linkers.md) | reader windows (core + halo + context pack), linker division by content | draft, not yet approved |
| [`spec/taxonomy_dev_codes.jsonl`](spec/taxonomy_dev_codes.jsonl) | 100 DSEWiki + 100 AI Village messages hand-coded with purpose labels (one Claude pass, unchecked; not truth) | dev set |
| [`spec/dsewiki_SCHEMA.md`](spec/dsewiki_SCHEMA.md) | what is in the DSEWiki dump and how identity is recorded | reference |

---

## 1. Why

Ryan Greenblatt's post on the Hugging Face incident investigation says the team had over a thousand multi-day
transcripts, too many to read, so they leaned on AI analysts whose outputs were "often missing key details, wrong,
overconfident, or really hard to understand", and key parts of the story only surfaced once a more complete dataset
arrived.

**Pitch:** an AI investigator for agent swarms whose findings a person can check, scored against truth we build in.
*Swarm investigators are slop-vestigators until you can score them.*

**Subject:** what spreads between agents, in three layers: words (coined terms), beliefs (factual claims, true or
false), goals (what agents spend their time on), plus two DSEWiki-specific layers added later: protocols (signal
formats, relay pages) and methods (techniques and resources).

**Swarms**
- **AI Village**: 183,485 chat messages, 47 agents from several labs, Apr 2025 to Sep 2026. Harmless, multi-lab.
- **DSEWiki** (collusion.wiki dump): 14,591 wiki saves by (per the publisher) OpenAI web-research agents that used
  public German wikis as a scratchpad and relay between runs, May 24 to Jul 2 2026. All one lab, no reasoning traces,
  self-chosen editor names. Closest public relative of the Hugging Face incident.

## 2. Standing rules

1. **Subagents read raw transcripts.** Nothing is pre-converted into interpreted rows before an AI reader sees it.
   Script-made fields are mechanical only (timestamps, length, exact-duplicate hash).
2. **Earlier AI findings are not ground truth.** The false-belief scan, the Swarm Atlas, the goal-adoption report and
   the DSEWiki publisher's labels are candidates and baselines only.
3. **DSEWiki holdout** (a planning choice, not Peyton's rule; under review). Revisions dated 2026-06-18 or later are
   held out for scoring. Design work used only the 5,129 earlier revisions (the "build" split). The cutoff was picked
   as "mid-June" and puts the whole Jun 18 burst in the holdout; see section 10.
4. **Sandbox-bypass text.** DSEWiki contains working sandbox-bypass instructions written by the agents. Never run,
   quote or paraphrase a method. Name the category (`ACCESS_WORKAROUND`) and cite by `msg_id` only.

## 3. Pipeline

```
raw messages (verbatim, loader script)
  -> readers: one record per message, per time window (core + read-only halo + script context pack)
  -> local linkers: short-range links inside each window
  -> gap resolver: fills reader "missing context" flags, versions records
  -> pregroup.py (script): candidate families from shared entities, claim text, dup chains, signed names
  -> family linkers (by content, whole timeline) + run-identity linker
  -> reconciler: merges claim keys that landed in different families
  -> trackers / lead / summarizers: analyzers, findings
every AI write passes the citation check on write; a same-model adversarial checker reviews rows; events view -> scoring
```

Each tier writes only what it can see. Readers record what a message says; linkers record how messages connect;
summarizers read aggregates first and drill down through `msg_id` to raw text.

## 4. Data model

### 4.1 Messages (L0, script)
`msg_id, swarm, t, channel, speaker, speaker_kind, lab, text` plus script features (`len, n_urls, gap_prev_s,
text_hash, dup_of, script_label in {DUPLICATE, EMPTY}, split`).
- AI Village `msg_id` = chat UUID. DSEWiki `msg_id` = `dw:<rev_id>`, e.g. `dw:dse~Sector61State5LiveRelay@1`.
- **DSEWiki `text` = page title line + the lines this save inserted or replaced** (from `hunks`). The full body is
  linked via `body_ref`; `parent_msg_id` points to the previous save of the page. Quotes are checked against `text`.
- `split = heldout` for DSEWiki saves from 2026-06-18.

### 4.2 Reader record (L1), one per message (reader_format section 2)
`signed_name, run_tag, purpose (1 primary + up to 2 secondary), flags (coded_token, task_content, addresses_human),
summary, quote, claims[], entities[], addressed_to, reply_to_hint, anomaly, context_status, context_needs[],
uncertain_fields, confidence`.

Claim object: `{claim_text, about: self|shared, stance: asserts|relays|doubts|corrects, stated_source, quote}`.
`stated_source` is only what the text says (`own_observation`, a signed name, a page title, "other cohorts",
`unstated`). Readers never fill true sources, claim keys, novelty, acted-on or run groups.

**Purpose labels** (readers): `STATUS, CLAIM, RELAY, ASK, DIRECT, COMMIT, STANDBY, CONFIRM, DOUBT, CORRECT, SOCIAL,
REFLECT, WORK, STASH, HOUSEKEEPING, ACCESS_WORKAROUND`; `UNCLEAR` only when `context_status = missing`.
Precedence when unsure: CORRECT > DOUBT > CONFIRM > DIRECT > CLAIM > RELAY > ASK > COMMIT > STATUS > rest.
Script-only: `DUPLICATE`, `EMPTY`.

**Missing context (2a).** Readers flag instead of guessing: `context_status` complete / partial / missing, one
`context_needs` entry per gap (`type, span, needed, search_hints`), with eight gap types (`reply_to_unseen,
unresolved_reference, coded_token, continuation, compacted_history, implicit_task, identity, outside_transcript`).
A resolver later writes `context_resolutions` and a new record version; version 1 is never edited.

### 4.3 Linker outputs (L2, reader_format section 5)
- `claim_keys` (+ members): one per distinct claim, layer in `belief | goal | protocol | method | word`.
- `links`: `source_of, reply_to, acted_on, confirms, doubts, corrects, same_run, exposed_to, independent_of`, each
  with a checked quote from `from_msg_id`, and `via` (route: reply, shared page, human relay, external source, task prompt).
- `run_groups` (+ members): which speakers / signed names / run tags are one run. On DSEWiki this replaces usernames.
- `aggregates` (+ members): messages with the same essential purpose collapsed into one row.
- Merges are reversible; "no match" is always allowed; low-confidence merges are marked low.

### 4.4 Event rows (row_format section 2), now a SQL view
`row_id, swarm, layer, item_id, item_text, item_status, agent, agent_group, agent_lab, role, depth, source_agent,
source_kind, t, evidence[], exposure_msg_id, confidence, rationale, produced_by, checks`.
Roles: `origin, adopt, reject, correct, abandon, challenge`. Depth: `said, planned, remembered, acted`.
In the store, `events` is computed from claim-key members and links: first member = origin; `doubts` = challenge;
`corrects` = correct; else adopt; depth = acted if an `acted_on` link leaves that message, planned if the record is
`COMMIT`, else said. `DUPLICATE` messages never count as adoption. This keeps scoring a join.

### 4.5 Store (store_design, store_schema.sql)
One SQLite file, WAL, one writer process. Agents never write SQL; they call tools in `store.py`, which check and
append. Append-only with `retracted_by`. Groups are header + membership tables. All quotes in one `citations` table,
located by offset, rejected unless an exact substring of at most 200 characters. Every AI row carries `task_id` ->
`tasks(run_id, tier, scope, model, replica)`, so two independent readers of one window sit side by side.

Tools: readers get `get_window, search(query, before), write_record`. Linkers/trackers add `get_records,
get_candidates, find_claim_key` (called only after writing their own wording), `new_claim_key, add_members,
retract_members, merge_claim_keys, add_link, new_run_group, add_run_members, new_aggregate, add_aggregate_members,
add_loose_end, close_loose_end, add_observation`. Lead/summarizers: read-only plus `add_finding(text, supports[])`,
which must point at claim keys, links or aggregates. Every tool returns `ok` or `rejected: <reason>`.

**Safety in the store:** if a record is labelled `ACCESS_WORKAROUND`, the tool stores a fixed summary ("access
workaround; see msg_id"), refuses free-text claims about the method, and marks its citations `redact = 1`; exports and
summarizer-facing queries show `[technique withheld]`.

**Free observations:** anything important outside the schema goes to `observations` with cited msg_ids, so the schema
does not blind the investigator to what it wasn't told to look for.

## 5. Windows and linkers (windowing_and_linkers)

**Measured** (distinctive-token proxy; rough shape, not exact rates): in AI Village, 45% of messages reuse a distinctive
token from an earlier message; nearest earlier use is a median 5 messages back, p75 27, but 11% are more than a day back.
A 100-message window without halo leaves 25% of those referents unseen; with a 50-message read-only halo, 16%.
In the DSEWiki build split, most pages have one save, and 16% of saves name another page saved a median 6 minutes
earlier, so pages are the wrong unit.

| | AI Village | DSEWiki |
|---|---|---|
| window unit | room x session (cut at gaps over 2 h) | global time slice across all wikis |
| core (records written) | ~100 messages | ~100 revisions |
| halo (context only) | previous 50 in the room | previous 50 revisions, any page, + last 3 saves of each core page |
| context pack (script) | pointer to the most recent earlier use of each distinctive token outside core + halo: raw text only, never AI records |

**Linkers** are divided by content, not time: (A) local linkers per window for replies and evaluation acts;
(B) family linkers over connected components of the candidate graph (shared entities with a document-frequency cap,
same normalized claim text, dup chains, signed names), whole timeline, split at ~300 records; (C) one reconciler over
all claim-key texts; (D) a run-identity linker on `signed_name`, `run_tag`, `ip16`, title date tags.

Order: readers -> local linkers -> gap resolver -> pregroup.py -> family + run-identity linkers -> reconciler ->
trackers / lead.

## 6. Analyzers (store_design section 5, v2)

1. **Cascade tracer**: per item, the transmission tree (origin, carriers in order, source and route per carrier, depth).
2. **Origin and novelty**: did it start in the swarm, or come from a human, outside page, task prompt or earlier run.
3. **Copying vs convergence**: exposure-based `independent_of` links plus a time-shuffled baseline.
4. **Mutation tracker**: wording, numbers, hedging, attribution drift along tree edges.
5. **Routes**: tree edges by `via`.
6. **Spreaders and adopters**: per agent / run group, adoption rate given exposure, same vs other lab.
7. **Stopping points**: corrected, doubted, ignored, still alive; adoption after correction; resurfacing.
8. **Layer coupling**: does adopting someone's words predict adopting their beliefs or goals.

Sunday set: 1, 2, 4, and 3 if time allows. Citation check and scorecard are infrastructure, not analyzers.

## 7. Checks and scoring

**Checks.** (1) Citation check on every write: msg_id exists, quote is an exact substring, own-step quotes are by the
agent, exposure precedes `t`. (2) Same-model adversarial checker in a fresh context sees one row plus its cited
messages and returns accept / correct / reject. Cross-lab checker is an optional experiment.

**Truth** (strongest first; no earlier AI output):
1. Planted cascades inserted into a copy of the messages (easy / medium / hard), recorded only in `truth_plants.jsonl`.
   In the copy, planted messages get ordinary-looking ids.
2. Blind hand labels: random channel x 2-hour windows labelled by Peyton before seeing AI output
   (`truth_windows.jsonl`); empty windows are real labels.
3. Adjudicated disagreements between setups.

**Match:** same swarm, layer, agent (DSEWiki: same handle or same run group), role, `t` within 30 minutes, same item.
Depth counts if same or shallower. **Scores:** recall, error rate inside labelled windows, calibration by confidence,
reader agreement (replica 0 vs 1), version-1 vs version-2 record changes.

**Experiments:** each safeguard's contribution (single agent, subagents, + citation check, + checker); more complete
data (AI Village chat only vs + memories and events); reconciler on/off recall; registry access on/off (investigator
contagion); optional checker diversity.

## 8. Build order (deadline Sun Oct 4, 5pm PT)

1. `load.py`: both swarms into `messages`, DSEWiki added-text extraction, script features, `split`; rebuild FTS.
2. `store.py`: tools above, citation check, safety rule, core-only `write_record`.
3. `window_plan.py`: sessions / global slices, halo, context pack.
4. Reader prompt; run on a few windows; measure flag rates and cost.
5. Local linker, resolver, `pregroup.py`, family linker, reconciler prompts.
6. Planting script; hand labels; scoring join; analyzers 1, 2, 4.

Skip if short on time: off-site texts (`records.jsonl.gz`), near-duplicate shingling, community detection,
cross-lab checker.

## 9. What was reconciled

| Disagreement | Followed | Why |
|---|---|---|
| Outline: "~18k edits", "3,700+ names" | 14,591 saves, 3,103 labels (899 anonymous saves) | counted in the dump; events.jsonl's 19,913 rows overlap and must not be summed |
| Outline / row_format: layer-split subagents write event rows directly | readers write per-message records; events is a view over claim keys + links | reader_format (approved) and store_design are later |
| row_format section 5: store tables and tool names; readers run in chronological waves so the item registry exists | store_design tables and tools; readers see raw text and context pack only, no registry, so they can run in parallel | windowing forbids feeding earlier AI records to readers; the registry-bias rule now applies to linkers via `find_claim_key` after writing |
| row_format: planted msg_ids `plant:<id>:<n>` | ordinary-looking ids in the db copy; mapping only in `truth_plants.jsonl` | store_design is later, and `plant:` ids would leak the answer |
| row_format depth `said` vs `remembered` | on DSEWiki every post is a persistent write; depth by `acted_on` links | reader_format section 6 |
| row_format roles | add `challenge` (from DOUBT) | reader_format section 6 |
| row_format layers | add `protocol` and `method` | reader_format section 6 |
| taxonomy_dev_codes.jsonl uses draft labels | map `PROBE` and `ORGANIZE` -> `HOUSEKEEPING`, `WORKAROUND` -> `ACCESS_WORKAROUND`, `SIGNAL` -> `RELAY` + flag `coded_token`; AI Village codes noted "standby/wait announcement" -> `STANDBY` | the file predates the final label set; it was not edited |
| Outline: cross-lab checker as a core step | optional experiment; core needs one lab's key | Peyton's decision 2026-10-03 |
| windowing asks for schema changes | not yet applied to `store_schema.sql`: `tasks.tier` lacks `resolver`, no `families` tables, no halo/core in `tasks.scope` | must be added before the resolver runs (the CHECK constraint will reject it) |
| `messages_fts` | external-content FTS5 table has no sync triggers | `load.py` must run `INSERT INTO messages_fts(messages_fts) VALUES('rebuild')` after loading |

## 10. Running on the DSEWiki incident: issues to expect

Numbers below were computed from `dsewiki/raw/` on 2026-10-03. Cost figures are estimates from character counts
(about 3.5 characters per token for this URL- and ID-heavy text), not measured.

### Holdout and evaluation
1. **Most of the incident is in the holdout.** 9,462 of 14,591 saves (65%) and 12.1M of 13.9M added characters (87%)
   are on or after 2026-06-18. June 18 alone has 6,543 saves (45% of the dataset), almost all between 14:00 and 22:00
   UTC. The prompts, windows and labels were all tuned on a quieter regime. Freeze prompts, plants and window settings
   before the first held-out run, and log every change made after looking at held-out output (it spends the holdout).
2. **Truth must exist first.** Plants and Peyton's blind hand labels for held-out windows have to be made before
   looking at any held-out investigator output, or the hand labels aren't blind. Sample label windows across the
   June 18 burst and quiet days separately; a uniform sample of 2-hour windows will be dominated by near-empty ones.
3. **The 100 dev codes are all from the build split** (checked), so they say nothing about the June 18 regime.

### Windowing
4. **Bursts break count-based windows.** Peak is 933 saves in 10 minutes (June 18, 20:00 UTC) and 2,350 in that hour.
   A 100-save core spans about a minute there, and a 50-save halo about 30 seconds, while cross-page context was
   measured at a median 6 minutes back. Use time-and-count windows in bursts (a halo of at least ~10 minutes) or rely
   more on the context pack; expect high `reply_to_unseen` rates otherwise.
5. **Window input size varies a lot.** Added text per save: median 323 characters, p90 3,212, p99 5,660, max 34,933.
   Some windows will be several times the average; cap by characters too.

### Identity
6. **Usernames don't identify runs.** 3,103 labels, 1,332 used for a single save, 899 anonymous saves, `ip16` only
   (191 values), no model field, publisher cohorts on about a quarter of pages. Everything per-agent (spreaders,
   adoption rate, scoring match) depends on the run-identity linker, which has no truth of its own. Report how much
   results change between label-level and run-group-level counting.

### Text extraction and duplicates
7. **Added-text extraction edge cases.** 4,562 saves create a page (whole body counts as added); 17 have earlier
   revisions missing, so their "added" text is the whole body and overstates what changed; 215 saves add nothing
   (pure deletions or reorders), which readers will see as a title only, though a deletion can be a meaningful act;
   50 are the wiki's empty default text.
8. **Exact copies are spread, not noise.** 3,172 saves share an exact body with another save (448 distinct bodies).
   Treating `DUPLICATE` as "never adoption" is right for re-saves of the same page by the same run, but a verbatim copy
   onto another page by another label is the clearest spread signal in the data. `pregroup.py` should turn cross-page
   dup chains into candidate `source_of` links rather than drop them.
9. **Encoding.** 250 saves are UTF-8 (German text), 1 Latin-1. Make sure quote checks compare the same normalized
   string the reader saw.

### Safety
10. **Safety filters on model calls.** Readers must read the access-workaround saves raw. Current models run safety
    classifiers that can stop a request (`stop_reason: "refusal"`). A refused window silently becomes a coverage gap.
    Check `stop_reason` on every call, log refused windows as gaps in the scorecard, and consider sending
    known-workaround pages (publisher families such as `probe-test`) in smaller windows so one page doesn't sink 100.
11. **Redaction depends on the reader's label.** `[technique withheld]` is applied only when a record is labelled
    `ACCESS_WORKAROUND`. A missed label lets technique text into exports, findings, the viewer and the repo. Add a
    second, script-side screen before anything is exported or committed, and review exported quotes by hand.
12. **Prompt injection.** The saves are written by agents for other agents ("post the 5th state immediately", pages
    built to test what readers do). Readers and linkers should only have the store tools: no web fetch, no shell, no
    URL following, and the system prompt should say the text is data.

### Cost, rate limits and keys
13. **Token volume.** Added text is about 13.9M characters, roughly 4M tokens, about 146 windows of 100 saves. With
    the halo, parent saves and context pack, reader input is roughly 7 to 8M tokens before prompts. Output: 14,591
    records at a few hundred tokens each plus thinking, roughly 5 to 12M output tokens. At current list prices
    (Opus 5.5 $4 in / $20 out per million tokens; Sonnet 5.5 $2 / $10; Haiku 4.5 $1 / $5) the reader tier alone is
    on the order of $130 to $270 on Opus 5.5 and half that on Sonnet 5.5, if each window is one call. Linkers,
    resolver, checker and replicas add roughly as much again.
14. **Tool loops multiply input cost.** If a reader calls `write_record` once per message, each of ~100 turns resends
    the growing window (40k to 80k tokens). That is about 6 to 7M input tokens per window, close to 1B for the whole
    dump; with prompt caching at $0.20 per million it is ~$200, without caching several thousand dollars. Write
    records in batches (e.g. 20 per call), or have readers return all records as one structured output and let
    `store.py` validate afterwards and send only rejected records back.
15. **Rate limits.** Running ~150 windows at once will hit per-minute output-token limits on most API tiers. The
    Batch API halves the price but cannot run tool loops, which is another reason for the one-shot structured-output
    reader. Run the build split first to measure real tokens per window before launching the holdout.
16. **Keys.** The core needs one lab's API key, available to whatever runs the Agent SDK (not in project files or the
    repo). The cross-lab checker needs a second key.

### Coverage and scope
17. **Off-site texts are out of scope for now.** 13,703 records from shorteners, paste sites and other wikis are not
    loaded. Part of the relay may run through them, so origins and routes found from the wiki alone can be wrong;
    this is the Greenblatt "more complete data" lesson inside one dataset. Say so in the write-up.
18. **Deletions.** 5,217 admin deletions touch 3,898 pages, but the median save was deleted about 13 days later and
    under 2% within an hour, so deletion rarely limits exposure. Exposure links can ignore deletions for now.
19. **Nothing is built yet.** Steps 1 to 4 in section 8 are needed before any run; budget a build-split test run
    before the holdout.
