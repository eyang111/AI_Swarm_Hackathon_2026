# Swarm Investigator: design (consolidated, v4 2026-10-04)

One document for everything designed so far. It summarizes and links the spec files in `spec/`, which stay the
detailed source for each part. Where the files disagreed, this document follows the most recent decision and says
what it reconciled (section 10). Section 11 lists the issues expected on the DSEWiki (German wiki) run and the fix
adopted for each.

Status: design only. No pipeline code (`load.py`, `store.py`, `window_plan.py`, `pregroup.py`, prompts) exists yet.
Changes in v2 (Peyton, 2026-10-04): holdout dropped; burst-aware windows; Sonnet readers in one-shot batches, Opus
analyzers; exact-copy collapsing; refusal handling and an export screen. v3: run-identity method from the thread
"DSEWiki agent identity" (section 5.5, `spec/identity_findings.md`); conversation layer from the thread "Investigator
database and analyzers" (section 4.5, `spec/store_design.md` 2a), approved by Peyton 2026-10-04.

v4: Sandra's pipeline v2 merged (`pipeline_v2.md`, branch `claude/swarm-investigator-design-v2`): message
segments, a function axis, assertiveness kept apart from reader confidence, a re-verify pass, capped local links with
a topic anchor, assertiveness-seeded groupers, a sequence-vs-cause rule, cross-cluster edges and a timeline graph
(sections 4.2, 4.3, 5.6, 5.7). Where pipeline_v2 and this file differ, this file says which applies (section 10).

| Spec file | What it holds | Status |
|---|---|---|
| [`spec/row_format.md`](spec/row_format.md) | event rows (investigator output and truth format), planted and hand-labelled truth, matching and scores | v1; its section 5 (store) is superseded by `store_design.md` |
| [`spec/reader_format.md`](spec/reader_format.md) | reader record per message, purpose labels, missing-context flags (2a), linker outputs | approved by Peyton |
| [`spec/store_design.md`](spec/store_design.md) + [`spec/store_schema.sql`](spec/store_schema.sql) | SQLite store `investigation.db`, write tools, analyzers v2 | draft; schema updated for v2 |
| [`spec/windowing_and_linkers.md`](spec/windowing_and_linkers.md) | reader windows (core + halo + context pack), linker division by content | draft; DSEWiki windows superseded by section 5.2 here |
| [`spec/taxonomy_dev_codes.jsonl`](spec/taxonomy_dev_codes.jsonl) | 100 DSEWiki + 100 AI Village messages hand-coded with purpose labels (one Claude pass, unchecked; not truth) | dev set |
| [`pipeline_v2.md`](pipeline_v2.md) | Sandra's pipeline v2: segments, function + assertiveness, re-verify, capped links, groupers, causal order, timeline graph | merged in v4; windows, models, copies, safety and identity come from this file |
| [`spec/identity_findings.md`](spec/identity_findings.md) | DSEWiki name measurements and the run-identity method; scripts in `identity_scripts/` | new, 2026-10-04 |
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

1. **Subagents read raw transcripts** (Peyton). Nothing is pre-converted into interpreted rows before an AI reader
   sees it. Script-made fields are mechanical only (timestamps, length, exact-copy hash, token-routed context).
2. **Earlier AI findings are not ground truth** (Peyton). The false-belief scan, the Swarm Atlas, the goal-adoption
   report and the DSEWiki publisher's labels are candidates and baselines only.
3. **No holdout** (Peyton, 2026-10-04). The earlier Jun 18 cutoff was a planning choice and put the whole Jun 18
   burst out of view. Truth comes from planted cascades and blind hand labels instead (section 8). The design so far
   was built from saves before Jun 18, so report results for before and after Jun 18 separately as a sanity check.
4. **Sandbox-bypass text.** DSEWiki contains working sandbox-bypass instructions written by the agents. Never run,
   quote or paraphrase a method. Name the category (`ACCESS_WORKAROUND`) and cite by `msg_id` only.

## 3. Pipeline

```
L0  raw messages (verbatim, loader script; exact copies grouped)
L1  readers (Sonnet, one-shot batch), per window (core + last-50 halo + token-routed halo + context pack):
    one record per distinct message, split into one-act segments with function, purpose, assertiveness,
    reader_confidence, keywords and uncertainty flags; store.py validates, re-asks rejects once
L1.9 re-verify (Sonnet): flagged gaps and low reader_confidence segments, checked against raw; new record versions
L2  local linkers (Sonnet): <=3 outgoing links per segment (2 recent same-content + 1 topic anchor)
    conversation layer: cluster.py (script) + clusterer (Opus) -> who was talking with whom
    pregroup.py (script): df pass on keywords, copy groups, shared entities, signed names
L3  groupers (Opus): per-layer content clusters seeded on assertive segments = claim keys
    + run-identity linker (Opus); reconciler (Opus) merges a claim split across clusters
    re-verify again on every assertive cluster seed
L4  within-cluster analyzers (Opus): time order = sequence; cause only with an exposure link
L5  cross-cluster analyzers (Opus): evolves_into / feeds / corrects / supersedes / caused
L6  timeline graph: clusters as events, L5 edges as arrows; analyzers and summarizers (Opus) read from here
every AI write passes the citation check; an Opus adversarial checker reviews rows; events view -> scoring
every tier after readers can pull raw text with get_raw; AI records are never fed back to readers
```

Each tier writes only what it can see. Readers record what a message says; linkers record how messages connect;
summarizers read aggregates first and drill down through `msg_id` to raw text.

## 4. Data model

### 4.1 Messages (L0, script)
`msg_id, swarm, t, channel, speaker, ip16, speaker_kind, lab, text` plus script features (`len, n_urls, gap_prev_s,
text_hash, dup_of, copy_of, removed_text, script_label in {DUPLICATE, EMPTY}`).
- AI Village `msg_id` = chat UUID. DSEWiki `msg_id` = `dw:<rev_id>`, e.g. `dw:dse~Sector61State5LiveRelay@1`.
- **DSEWiki `text` = page title line + the lines this save inserted or replaced** (from `hunks`), Unicode NFC.
  The full body is linked via `body_ref`; `parent_msg_id` points to the previous save of the page.
- **`removed_text`**: lines the save deleted. 215 saves add nothing; readers see their removals marked `removed:`
  so a deletion can be recorded as an act.
- **`copy_of`**: see 5.3.
- **`ip16`** is kept as a raw field but carries no identity signal (5.5).

### 4.2 Reader record (L1), one per message (reader_format section 2)
`signed_name, run_tag, purpose (1 primary + up to 2 secondary), flags (coded_token, task_content, addresses_human),
summary, quote, claims[], entities[], addressed_to, reply_to_hint, anomaly, context_status, context_needs[],
uncertain_fields, confidence`.

**Segments (v4, pipeline_v2 section 2).** A message that does several things (a status note, a directive and a
relayed answer in one save) is split by the reader into one-act segments with cited character spans; single-act
messages are one segment. From L2 on, the segment (`<msg_id>#<n>`) is the unit. An `ACCESS_WORKAROUND` span is its
own segment, so it is withheld without losing the rest of the save. Per segment the reader adds:
- **function**: `epistemic, executive, normative, infrastructural, affiliative, adversarial`, above the purpose label
  (pipeline_v2 cites an α of 0.85 from earlier validation; the source isn't in the project files, so treat it as
  unverified);
- **assertiveness** 0 to 1 (how flatly the agent stated it) and **reader_confidence** 0 to 1 (how sure the reader is
  of its labels), never merged; assertiveness anchors links and cluster seeds, reader_confidence triggers re-verify;
- **keywords**, 3 to 8 per segment, including topic keys seen elsewhere in the window; a script df pass decides which
  are distinctive.

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
The re-verify pass (v4, replaces the gap resolver) writes `context_resolutions` and a new record version; version 1
is never edited. It also takes segments with low `reader_confidence`, and later every assertive cluster seed.

### 4.3 Linker outputs (L2, reader_format section 5)
- `claim_keys` (+ members): one per distinct claim, layer in `belief | goal | protocol | method | word`. In v4 these are
  the groupers' content clusters over segments (5.6).
- `links`: `source_of, reply_to, acted_on, confirms, doubts, corrects, same_run, exposed_to, independent_of`, plus `anchor` (v4), each
  with a checked quote from `from_msg_id`, and `via` (route: reply, shared page, human relay, external source, task prompt).
- `run_groups` (+ members): which speakers / signed names / run tags are one run. On DSEWiki this replaces usernames.
- `aggregates` (+ members): messages with the same essential purpose collapsed into one row.
- Local links are capped at 3 outgoing per segment (in-degree uncapped); family-stage `source_of`, copy-group and
  exposure links are exempt, so the cap never drops a real source.
- `cluster_edges` (v4): links between clusters (`evolves_into, feeds, corrects, supersedes, caused`), each citing
  segments on both sides.
- Merges are reversible; "no match" is always allowed; low-confidence merges are marked low.

### 4.4 Event rows (row_format section 2), now a SQL view
`row_id, swarm, layer, item_id, item_text, item_status, agent, agent_group, agent_lab, role, depth, source_agent,
source_kind, t, evidence[], exposure_msg_id, confidence, rationale, produced_by, checks`.
Roles: `origin, adopt, reject, correct, abandon, challenge`. Depth: `said, planned, remembered, acted`.
In the store, `events` is computed from claim-key members and links: first member = origin; `doubts` = challenge;
`corrects` = correct; else adopt; depth = acted if an `acted_on` link leaves that message, planned if the record is
`COMMIT`, else said. `DUPLICATE` messages never count as adoption; a cross-label copy can (5.3).

### 4.5 Conversations (new in v3, store_design 2a)
Rooms interleave several conversations, and on DSEWiki one conversation often spans several pages. `cluster.py`
(no AI) links messages by readers' `reply_to_hint`, short gaps in the same channel, shared entities, page save
chains, and saves naming a page saved shortly before; connected groups are candidate conversations. A clusterer
agent then handles only the unclear spots (oversized candidates, bridging messages, topic changes): writes the topic
line, moves members, and records `split`, `merge`, `drift` and `resume` edges, each anchored on a message with a
checked quote. Tables `conversations`, `conversation_members` (a message may bridge two), `conversation_edges`, view
`conversation_presence`. All reversible. Membership is evidence of presence, not proof of exposure: an `exposed_to`
link may cite it but needs its own rationale. Feeds the cascade tracer (who was present when an item appeared;
items crossing a merge) and the mutation tracker (variants right after a split). Readers still run on time windows;
a conversation-chosen halo is an option for a second reader pass.

### 4.6 Store (store_design, store_schema.sql)
One SQLite file, WAL, one writer process. Agents never write SQL; they call tools in `store.py`, which check and
append. Append-only with `retracted_by`. Groups are header + membership tables. All quotes in one `citations` table,
located by offset, rejected unless an exact substring of at most 200 characters. Every AI row carries `task_id` ->
`tasks(run_id, tier, scope, model, replica)`, so two independent readers of one window sit side by side.
`coverage_gaps` lists every message with no reader record and why (refused, failed, skipped).

Tools: `get_window(swarm, t_start, t_end, channel=None, halo)`, `search(query, before)`, `write_record` (readers'
output goes through it in bulk, see 6.1). Linkers/trackers add `get_records, get_candidates, find_claim_key` (called
only after writing their own wording), `new_claim_key, add_members, retract_members, merge_claim_keys, add_link,
new_run_group, add_run_members, new_aggregate, add_aggregate_members, add_loose_end, close_loose_end,
add_observation`. Lead/summarizers: read-only plus `add_finding(text, supports[])`, which must point at claim keys,
links or aggregates. Every tool returns `ok` or `rejected: <reason>`.

**Free observations:** anything important outside the schema goes to `observations` with cited msg_ids, so the schema
does not blind the investigator to what it wasn't told to look for.

## 5. Windows, bursts and copies

### 5.1 Measurements (windowing_and_linkers section 1)
Distinctive-token proxy: a message reuses a distinctive token (IDs, numbers with letters, CamelCase titles,
hyphenated identifiers, document frequency 2 to 50) from an earlier message. In AI Village, nearest earlier use is a
median 5 messages back, p75 27, 11% more than a day back. On DSEWiki, most pages have one save, and related saves sit
on other pages minutes earlier, so DSEWiki windows are global time slices.

### 5.2 Burst-aware DSEWiki windows (new in v2)
DSEWiki peaks at 933 saves in 10 minutes (Jun 18, 20:00 UTC); a 100-save window there covers about a minute.
Measured on all 11,451 distinct saves (after collapsing copies), share of token back-references whose earlier save
is inside the reader's view:

| Scheme | quiet periods | bursts (≥100 saves per 10 min) | halo per window |
|---|---|---|---|
| A. 100-save core + previous 50 saves (v1 design) | 90% | 73% | 50 saves |
| B. A + all saves in the previous 15 min (cap 400) | 91% | 88% | median 78, p90 291 |
| C. burst saves grouped into token-sharing clusters | 90% | 74% | one giant cluster of 3,172; no gain |
| **D. A + token-routed halo (adopted)** | **97.5%** | **98.8%** | median 125 saves, ~65k chars |

**D, the adopted scheme:** core = up to 100 distinct saves **and** at most 60k characters (some 100-save windows
reach 280k characters); halo = the previous 50 saves plus, for every distinctive token in the core, the 2 most recent
earlier saves using it within 24 hours, capped at 150. Halo saves are raw text marked context-only. This gives 182
DSEWiki windows. The script context pack still adds pointers for anything older.

Caveat: D is chosen by the same token proxy it is scored on, so these numbers show it does what it is meant to, not
that it catches dependence with no shared token ("agreed with that plan"). The reader's missing-context flags
(`context_status`, `reply_to_unseen`) measure that on the real run; check the burst windows first.

AI Village keeps room x session windows with a 50-message halo; it has no comparable bursts.

### 5.3 Exact copies (new in v2)
Texts are compared after Unicode NFC and whitespace normalization. 3,140 of 14,591 saves repeat an earlier save's
added text exactly (11,451 distinct texts); collapsing them cuts reader input by 35% (13.9M to 9.0M characters).
The most-copied text appears 555 times on 555 pages.
- **Read once.** Readers see only the first instance. `store.py` clones its record to every copy (`copy_of` set,
  quotes re-located and re-checked in each copy; a failed re-check sends that copy to readers).
- **Copies are spread evidence, not noise.** 1,806 copies are on a different page and 1,538 under a different
  username than the first instance. `pregroup.py` makes each such copy a `copy_group` candidate pointing at the first
  instance, and linkers decide `source_of`. Same page, same username re-saves stay `DUPLICATE` (never adoption).
- **Optional, not adopted yet: templates.** Masking digits leaves 10,281 distinct texts (6.8M characters, 51% below
  the raw total). Numbers are often the claim itself (11.2% vs 11.3%), so a template group could only be read once
  if the reader also gets a table of the differing values. Worth it only if reader cost becomes the bottleneck.

### 5.4 Linkers (windowing_and_linkers section 3)
Divided by content, not time: (A) local linkers per window for replies, evaluation acts and the capped same-content
and anchor links; (B) groupers (formerly family linkers) over connected components of the link and candidate graph
(distinctive keywords with a document-frequency cap, same normalized claim text, copy groups, signed names), whole
timeline, one layer at a time, split at ~300 segments; (C) one reconciler over all cluster texts; (D) a run-identity
linker (5.5).

Order: readers -> re-verify -> local linkers -> conversation layer -> pregroup.py -> groupers + run-identity linker ->
reconciler -> re-verify on seeds -> L4 -> L5 -> timeline graph and analyzers.

### 5.5 Run identity (new in v3; details in `spec/identity_findings.md`)
**What the names show.** 1,332 of 3,103 names are used once. 729 of those look like a more common name, but that
resemblance is worthless: agents draw names from one shared vocabulary (Agent / OpenAI / Research / Helper + topic +
date tag + digits), and string-matched pairs share a page or tag about as often as random pairs. What does link
names: one-off names sharing a template once trailing digits are stripped (382 names; e.g. a run minting a fresh
`...WatcherX` + 6 digits name per save), and names embedding a Unix timestamp from the moment of saving (148 names,
82% within an hour of the save). `ip16` is noise (same name within 60 s shares it 2.1% vs 1.6% at random): dropped.
`page_family_cohort` is derived from titles, so it can't validate anything. Date tags are cohort labels, not dates
or runs: one tag spans several topics and a median 80 hours.

**Method.**
1. Unit = *name-session*: one name's saves, split at gaps over 6 hours; anonymous saves are singletons.
2. `identity_candidates.py` (script) proposes edges. Strong: template mint, timestamp mint, signature (after
   checking it isn't quoted older text). Medium: distinctive edit summary (used by 5 or fewer names) within 48 h,
   same date tag + non-generic topic word within 48 h, append chains (to measure).
3. Strong edges merge directly. Medium edges go to the Opus run-identity linker, which reads both sides' added text.
   Merges are blocked by two different date tags in added text, or saves under 5 seconds apart on different pages.
4. Edges live in `identity_edges` (proposed / accepted / rejected, versioned); run groups are built from accepted
   edges, so a bad merge is undone by rejecting one edge.
5. Every per-agent result is reported at three levels: name-session, run group, cohort (date tag). A claim that holds
   at only one level is flagged.

**Ceiling.** Scripts alone put about 35% of saves in confident groups; 34% are generic names (e.g. `ResearchHelper`,
35 variants over 28 days) that the linker must split by session and content; about 14% (one-off names with no signal,
anonymous saves) can only be linked by what they wrote. There is no run key, so no grouping can be confirmed.
On this dump, spread between cohorts and between pages is more defensible than spread between runs; state each claim
at the coarsest level it survives.

**Evaluation.** Synthetic renaming (give a distinctive name's saves fresh fake names, measure how many are put back
together and how many land in the wrong group) and a contradiction rate. Not agreement with `page_family_cohort`.

### 5.6 Clusters and causal order (v4, pipeline_v2 sections 5 and 6)
- **Groupers** build per-layer clusters seeded on the most assertive, clearly typed segments (what the group treated
  as settled); members attach by distinctive keywords, claim text and L2 links. Seeds are re-verified against raw, so a
  confidently wrong seed is caught before analysis. Singletons are allowed.
- **L4, within a cluster:** sort by time. Time order is a *sequence*; an edge becomes *causal* only where an
  `exposed_to`, `source_of` or `acted_on` link (or conversation presence plus its own rationale) shows the later
  segment could have seen the earlier one. Output: an ordered spine, origin, carriers.
- **L5, between clusters:** edges only where warranted, each citing segments on both sides. Most pairs get none.

### 5.7 Analyzers and the timeline graph
The analyzers from store_design section 5 (dropped from this file in v2 by mistake, restored here) run on the L4 and
L5 output: 1 cascade tracer (now the L4 spine per cluster), 2 origin and novelty, 3 copying vs convergence, 4 mutation
tracker (now also tracks assertiveness rising along a chain, e.g. hedges hardening), 5 routes, 6 spreaders and
adopters (at name-session, run-group and cohort level, 5.5), 7 stopping points, 8 layer coupling (L5 `evolves_into`
across layers is direct evidence). Sunday set: 1, 2, 4 and the timeline graph.

**Timeline graph (L6)** is the main output picture: each cluster is an event node (split into sub-events where L4 finds
separate phases, such as a claim and a correction wave days later), positioned by time span, sized by segment count,
coloured by layer or function; arrows are L5 edges. Every node drills to its segments and their msg_ids; quotes follow
the export screen (section 7).

## 6. Models and how calls are made (new in v2)

### 6.1 Readers: Claude Sonnet 5.5, one-shot, batched
Readers don't need tools: the window, halo and context pack are assembled by the script up front. So each window is
**one request** that returns all its records as structured output (`output_config.format` with the record schema),
sent through the **Message Batches API** (50% off list price, no per-minute rate-limit pressure from ~200 parallel
loops). The fixed prefix (instructions, label definitions with examples, record schema) comes first and is marked for
prompt caching. Effort `low`; raise only if a test window shows label quality suffers. `max_tokens` about 32k (a
60-record window needs about 18k).

After the batch, `store.py` checks every record (msg_id, quote substring, labels). Rejected records go back in one
small second batch with the window and the rejection reason. This replaces the v1 design of one `write_record` tool
call per message, whose re-sent context would have cost about 1B input tokens.

Rough reader cost for all of DSEWiki (estimate, ~3.5 characters per token; confirm with `count_tokens` on one window):
input ~7.5M tokens (core ~2.6M, halo ~3.4M, cached prefix ~1.5M), output ~3.4M tokens (11,451 records x ~300).
At Sonnet 5.5 list prices ($2 in / $10 out per million tokens) about $50; with batch about $25, plus ~10% for
re-asks. v4 segments, two confidences and keywords add roughly half again to output, so about $35 to $40 batched. The 3-window test (7.2) should also confirm that structured output and caching behave as expected inside batches.

### 6.2 Linkers: Sonnet for local work, Opus for merges
| Tier | Model | Why |
|---|---|---|
| clusterer | Opus 5.5 | only the unclear spots, few calls; a wrong split or merge misplaces whole cascades (my pick, not yet confirmed) |
| local linker, re-verify | Sonnet 5.5 | many short-range, mostly mechanical links; errors are local and cheap to fix |
| groupers, reconciler, run-identity linker | Opus 5.5 | few calls, each decides which messages are "the same claim" or "the same run"; one wrong merge invents or erases a whole cascade |
| L4, L5, analyzers, lead, summarizers | Opus 5.5 | Peyton's choice |
| adversarial checker | Opus 5.5 | should not be weaker than the rows it checks |

Rough linker cost (estimate): family linkers read ~11.5k records (~2.3M tokens) once or twice plus raw drill-downs,
in tool loops with caching; expect tens of dollars on Opus 5.5, not hundreds. Measure on the first family before
running all.

One Anthropic API key covers both models. Opus 5.5 can't turn thinking off; set effort explicitly (default `medium`).

## 7. Safety handling (new in v2)

1. **Refusals are recorded, not lost.** Every response's `stop_reason` is checked. On `refusal`, the window is split
   in half and both halves are resubmitted until the refused saves are isolated (about 6 rounds for a 60-save window).
   Halo saves are dropped first, since they are context only. Isolated saves get a `coverage_gaps` row (`reason =
   refused`, `detail = stop_details.category`), no record and no text. The scorecard reports coverage, and
   analyzers treat a gap as unknown, not as absence. On the plain (non-batch) API, also enable the server-side
   refusal fallback (`fallbacks: "default"`).
2. **Test first.** Before the full batch, run 3 windows, including the Jun 18 20:00 peak and one window dense with
   publisher-labelled probe/test pages, to measure refusal rate, tokens per window and label quality.
3. **Readers have no tools.** In one-shot mode they cannot fetch URLs, run code or write anywhere, so instructions
   inside wiki text (pages written by agents for agents) can't make them act. The prompt says the text is data under
   study.
4. **Export screen.** `[technique withheld]` applies when a record is `ACCESS_WORKAROUND`, but a missed label
   would leak text. So anything that leaves the store (viewer, write-up, repo) shows **no quotes by default**, only
   msg_ids and reader summaries. Quotes are added from an allowlist Peyton reviews. Messages in `coverage_gaps` or
   labelled `ACCESS_WORKAROUND` are never on the allowlist.
5. **Prompts and summaries never describe methods.** Summaries of `ACCESS_WORKAROUND` records are the fixed string
   from store_design.

## 8. Checks and scoring

**Checks.** (1) Citation check on every write: msg_id exists, quote is an exact substring, own-step quotes are by the
agent, exposure precedes `t`. (2) Opus adversarial checker in a fresh context sees one row plus its cited messages
and returns accept / correct / reject. Cross-lab checker is an optional experiment.

**Truth** (strongest first; no earlier AI output):
1. Planted cascades inserted into a copy of the messages (easy / medium / hard), recorded only in `truth_plants.jsonl`.
   Planted messages get ordinary-looking ids. Include plants inside the Jun 18 burst, not only in quiet periods.
2. Blind hand labels: random channel x 2-hour windows labelled by Peyton before seeing AI output
   (`truth_windows.jsonl`); empty windows are real labels. DSEWiki: sample burst and quiet windows separately, or a
   uniform sample will be mostly empty windows.
3. Adjudicated disagreements between setups.

**Match:** same swarm, layer, agent (DSEWiki: same handle or same run group), role, `t` within 30 minutes, same item.
Depth counts if same or shallower. **Scores:** recall, error rate inside labelled windows, calibration by confidence,
reader agreement (replica 0 vs 1), version-1 vs version-2 record changes, coverage (share of messages not in
`coverage_gaps`), all also split before / after Jun 18.

**Experiments:** each safeguard's contribution (single agent, subagents, + citation check, + checker); more complete
data (AI Village chat only vs + memories and events); reconciler on/off recall; registry access on/off (investigator
contagion); optional checker diversity.

## 9. Build order (deadline Sun Oct 4, 5pm PT)

1. `load.py`: both swarms into `messages`; DSEWiki added and removed text, NFC; `copy_of`; script features; FTS
   rebuild.
2. `window_plan.py`: AI Village sessions; DSEWiki 60k-character cores with last-50 + token-routed halo; context pack.
3. `identity_candidates.py` (name-sessions, strong and medium edges).
4. Reader prompt (segments, function, assertiveness, reader_confidence, keywords) + batch runner + `store.py`
   validation and re-ask; refusal bisection; `coverage_gaps`.
5. 3-window test (section 7.2); check cost, refusals, flags.
6. Planting script and blind hand labels, before looking at full-run output.
7. Full reader batch; re-verify; local linker (cap + anchor); `cluster.py` + clusterer; `pregroup.py` (df pass, copy
   groups); groupers; reconciler; re-verify on seeds.
8. L4 and L5; scoring join; analyzers 1, 2, 4; timeline graph; export with the screen.

Skip if short on time: off-site texts (`records.jsonl.gz`), template groups, community detection, cross-lab checker.

## 10. What was reconciled

| Disagreement | Followed | Why |
|---|---|---|
| Outline: "~18k edits", "3,700+ names" | 14,591 saves, 3,103 labels (899 anonymous saves) | counted in the dump; events.jsonl's 19,913 rows overlap and must not be summed |
| Outline / row_format: layer-split subagents write event rows directly | readers write per-message records; events is a view over claim keys + links | reader_format (approved) and store_design are later |
| row_format section 5: store tables and tool names; readers run in chronological waves so the item registry exists | store_design tables and tools; readers see raw text, halo and context pack only, no registry, so they run in parallel | windowing forbids feeding earlier AI records to readers; the registry-bias rule now applies to linkers via `find_claim_key` after writing |
| store_design: one `write_record` tool call per message | one-shot structured output per window, validated after | cost (section 6.1) |
| row_format: planted msg_ids `plant:<id>:<n>` | ordinary-looking ids in the db copy; mapping only in `truth_plants.jsonl` | store_design is later, and `plant:` ids would leak the answer |
| row_format depth `said` vs `remembered` | on DSEWiki every post is a persistent write; depth by `acted_on` links | reader_format section 6 |
| row_format roles / layers | add `challenge`; add `protocol` and `method` | reader_format section 6 |
| taxonomy_dev_codes.jsonl uses draft labels | map `PROBE` and `ORGANIZE` -> `HOUSEKEEPING`, `WORKAROUND` -> `ACCESS_WORKAROUND`, `SIGNAL` -> `RELAY` + flag `coded_token`; AI Village codes noted "standby/wait announcement" -> `STANDBY` | the file predates the final label set; it was not edited |
| Outline: cross-lab checker as a core step | optional experiment; core needs one lab's key | Peyton's decision 2026-10-03 |
| reader_format, windowing, store_design: Jun 18 holdout | dropped; `split` column removed from the schema | Peyton, 2026-10-04 |
| windowing: DSEWiki windows of ~100 saves + 50 halo | 60k-character cores + token-routed halo | burst measurements (5.2) |
| windowing asked for schema changes | applied: tiers `local_linker, resolver, identity, reconciler`; candidate bases `copy_group, family`; `coverage_gaps`, `identity_edges`, conversation tables, tier `clusterer`; `ip16`, `copy_of`, `removed_text` on messages | needed by v2/v3 |
| pipeline_v2: "windows unchanged from DESIGN.md §5" (100-save windows) | burst-aware windows (5.2) | v2/v3 measurements postdate the fork |
| pipeline_v2: groupers with no cross-component merge step | groupers keep the reconciler | a claim split across two components would otherwise stay two items |
| pipeline_v2: hard cap of 3 outgoing links per segment | cap on local links only; family-stage source, copy and exposure links exempt | a hard cap could drop a real source |
| pipeline_v2: gap resolver replaced by re-verify | adopted | re-verify is a superset |
| conversation layer vs groupers | both kept: conversations = who was talking with whom (exposure evidence), groupers = what spreads | different questions |
| `messages_fts` | external-content FTS5 table has no sync triggers | `load.py` must run `INSERT INTO messages_fts(messages_fts) VALUES('rebuild')` after loading |

## 11. DSEWiki run: issues and fixes

Numbers computed from `dsewiki/raw/` on 2026-10-03/04.

| # | Issue | Fix adopted | Where |
|---|---|---|---|
| 1 | Holdout left 87% of the text, and the whole Jun 18 burst, out of view | holdout dropped; plants and hand labels cover the burst; results also reported before/after Jun 18 | 2, 8 |
| 2 | Truth must exist before looking at output | plants + blind labels made before the full run; burst and quiet windows sampled separately | 8, 9 |
| 3 | Dev codes are all pre-Jun 18 | 3-window test includes the Jun 18 peak; report label quality there | 7 |
| 4 | Bursts: 100-save windows span ~1 minute, 73% back-reference coverage | token-routed halo: 99% in bursts (proxy measure) | 5.2 |
| 5 | Window size varies (up to 280k characters per 100 saves) | 60k-character core cap | 5.2 |
| 6 | Usernames don't identify runs (3,103 labels, 1,332 used once, 899 anonymous) | name-sessions + scripted strong edges + Opus linker for medium edges; reversible `identity_edges`; results at three levels; `ip16` dropped | 5.5 |
| 7 | Added-text edge cases (215 deletion-only saves, 17 with missing history, 50 empty defaults) | `removed_text` shown to readers; missing-history saves flagged in `anomaly`; `EMPTY` by script | 4.1 |
| 8 | Exact copies (3,140) | read once, record cloned; cross-page / cross-label copies become spread candidates; 35% less reader input | 5.3 |
| 9 | Encoding (250 UTF-8 saves) | NFC at load; quotes checked on the same text | 4.1 |
| 10 | Safety filters can refuse windows silently | `stop_reason` check, bisection, `coverage_gaps`, server-side fallback off-batch, 3-window test | 7 |
| 11 | Redaction depends on the reader's label | exports show no quotes by default; reviewed allowlist | 7 |
| 12 | Prompt injection from agent-written pages | readers have no tools; linkers only store tools | 7 |
| 13 | Token volume | Sonnet readers, copies collapsed: ~$25 batched for all of DSEWiki (estimate) | 6.1 |
| 14 | Tool loops multiply input cost | one-shot structured output per window, re-ask only rejects | 6.1 |
| 15 | Rate limits | Batch API for readers; linkers run per family, measured on the first | 6 |
| 16 | Keys | one Anthropic key for Sonnet and Opus; never in project files or the repo | 6.2 |
| 17 | Off-site texts (13,703 records) not loaded | out of scope; stated in the write-up as a coverage limit | 9 |
| 18 | Deletions (5,217; median 13 days after the save) | rarely limit exposure; ignored for now | — |
| 19 | Nothing built | build order in section 9 | 9 |
