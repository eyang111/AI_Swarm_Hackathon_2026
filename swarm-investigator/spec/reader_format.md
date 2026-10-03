# Reader and linker format (draft v1, 2026-10-03)

How the Swarm Investigator turns raw transcripts into a database that summarizer agents can work from.
Built from the DSEWiki build split: revisions dated before 2026-06-18, 5,129 of 14,591. Revisions from 2026-06-18 on are held out for scoring and were not read. Checked against 100 AI Village messages.
This file does not edit `row_format.md`. Section 6 lists what it would change there.

**Pipeline:** readers (one time window each) → script pre-grouping (no AI) → linkers (across windows) → summarizers.
Each layer writes only what it can see. Readers record what a message says. Linkers record how messages connect. Summarizers read aggregates first and drill down to records and raw messages through `msg_id`.

Safety: DSEWiki contains sandbox-bypass instructions. No layer quotes or paraphrases a method. Records point to it by `msg_id` and use the label name only.

---

## 1. Pointer back to the source

Every record, claim, link and aggregate carries `msg_id`s that resolve to one raw message in `messages.jsonl`:
- AI Village: the chat message UUID.
- DSEWiki: `dw:<revision id>`, e.g. `dw:dse~Sector61State5LiveRelay@1` (page `Sector61State5LiveRelay`, 1st save).

Readers also give `quote`: an exact substring of the message, at most 200 characters. The store's write tool checks that the msg_id exists and the quote matches, and rejects the write if either fails. That way a summarizer can always return to the original words.
For DSEWiki, the reader reads the **text added in that revision** (the loader extracts it from `hunks`) plus the page title. The whole page body is linked but not re-summarized.

## 2. Layer 1: reader record (one per message)

| Field | Filled by | Notes |
|---|---|---|
| `msg_id`, `t`, `channel`, `speaker` | script | copied from `messages.jsonl` |
| `signed_name` | reader | the name the agent signs inside the text ("-- OpenAIResearcherJul23"); on DSEWiki it often differs from `speaker` |
| `run_tag` | reader | a run or cohort tag the agent states about itself ("Jun28 cohort", "Apr10OAI"); null if none |
| `purpose` | reader | 1 primary + up to 2 secondary labels from section 3 |
| `flags` | reader | optional: `coded_token` (a pre-agreed terse format such as `STATE5-XX`), `task_content` (states a question or answer of the agents' task), `addresses_human` |
| `summary` | reader | one line, the reader's own words |
| `quote` | reader | exact substring, at most 200 chars, the most informative span |
| `claims` | reader | list, see below |
| `entities` | reader | normalized keys for things named: `agent:`, `page:`, `task:`, `value:`, `term:`, `url_host:` (e.g. `task:datausa-clothing-workforce`, `term:cohort`) |
| `addressed_to` | reader | agents or signed names the message speaks to (@-mentions, "Jan12, please...") |
| `reply_to_hint` | reader | a msg_id if the reader can see which message this answers, else a short description ("answers DataUSAResearchHelperMay24's timing question") |
| `anomaly` | reader | free text for anything odd that no field captures; null usually |
| `context_status`, `context_needs`, `uncertain_fields` | reader | whether the message can be understood from what the reader saw, and what is missing (section 2a) |
| `context_seen` | script | msg_ids the reader was shown before this message, whatever the windowing scheme decides |
| `record_version`, `supersedes`, `revised_by`, `revision_reason` | store | versioning when a later pass revises the record (section 2a) |
| `confidence` | reader | high / medium / low for the record as a whole |
| `dup_of`, `len`, `n_urls`, `gap_prev_s` | script | exact or near-duplicate of an earlier msg_id; text length; URL count; seconds since previous message in the same channel |

**Claim object** (`claims[]`), one per distinct statement of fact or plan:
`{claim_text, about: "self" | "shared", stance: "asserts" | "relays" | "doubts" | "corrects", stated_source, quote}`
- `claim_text`: short plain wording ("the 5th question in the Language sequence is California, answer 11.2%").
- `about`: `self` = the speaker's own run or state; `shared` = the task, environment, or other agents.
- `stated_source`: who the speaker *says* it came from, exactly as visible: `own_observation`, a signed name, a page title, `"other cohorts"`, or `unstated`. Readers do not guess beyond the text; linkers resolve it.

Readers do **not** fill: claim keys, true sources, novelty, acted-on, run grouping, or aggregates. Those need the whole log (layer 2).

## 2a. Missing context

Many agent messages only make sense with an earlier message: "Thanks. Our original activation was...", "C3-STATE: Florida", "@Jan12: was your wording identical?". A reader that guesses the missing context writes a confident but wrong record at the lowest layer, and everything above inherits it. So readers flag what they don't know instead of filling the gap.

**Reader rules**
1. Summarize only what the message itself and `context_seen` support. For anything unresolved, write a placeholder in the summary and claims: `[unresolved: what "C3" refers to]`, `[unseen message from Jan12]`.
2. Set `context_status`:
   - `complete`: the message is understandable as it stands.
   - `partial`: the gist is clear but some detail depends on missing context.
   - `missing`: the reader can't tell what the message is about or doing.
3. Add one `context_needs` entry per gap.
4. List in `uncertain_fields` the record fields that could change once the gap is filled, e.g. `["purpose", "claims[0].about"]`. A `missing` record keeps a purpose label only if the surface act is clear (an `ASK` is still an ask). Otherwise the purpose is `UNCLEAR`, which is a valid value for `missing` records only.

**`context_needs[]` entry**
`{type, span, needed, search_hints}`
- `span`: the exact substring that is unresolved (checked like `quote`).
- `needed`: one line on what would resolve it ("the message from Jan12 that this thanks", "the definition of C3 in this page's convention").
- `search_hints`: where to look: `{channel, agents, terms, before_t}`. A resolver can run them through the store's search without re-reading the window.
- `type`:

| Type | The message... | Example |
|---|---|---|
| `reply_to_unseen` | answers or thanks a message the reader didn't see | `dw:dse~DataUSAClothingSequenceCollabAug08@6` opens "Thanks." and answers a mapping from someone else |
| `unresolved_reference` | points to something by pronoun, "your", "that number", "the same" | "matches yours", "your next unknown" |
| `coded_token` | uses a code or term whose meaning was set elsewhere | `dw:dse~ClothingC3FastSignalJul14@3`: what "C3-STATE" means |
| `continuation` | continues a list, story, argument or count started earlier | a chapter paragraph, "R4 confirmed" without R1 to R3 |
| `compacted_history` | refers to earlier content that was removed or compacted | "[Older cohort chatter compacted; see history.]" |
| `implicit_task` | assumes a task, goal or plan the reader can't see | "on prompt we will signal", with no task named |
| `identity` | refers to an agent by a name that can't be tied to a speaker | a signed name that matches no username in view |
| `outside_transcript` | depends on something that isn't in the log at all | the agents' own task prompts, an external counter, a human's private message |

`outside_transcript` gaps can't be filled by any later pass. They stay flagged so summarizers know a claim rests on unseen evidence.

**How a later pass fills a gap without losing the original**
- A resolver (a linker task, or a separate pass, whichever the pipeline design picks) takes records with `context_status` ≠ `complete`. It runs `search_hints`, reads the candidate messages, and writes one `context_resolutions` row per gap:
  `{msg_id, need_index, status: resolved | unresolvable | ambiguous, resolved_by: [msg_id...], resolution, evidence_quote, confidence, rationale}`.
- If the resolution changes the record, the resolver writes a **new version** (`record_version` 2, `supersedes` = the version-1 record, `revised_by` = the resolution row ids, `revision_reason`). Version 1 is never edited or deleted.
- Summarizers read the latest version by default, and can see that a record was revised and why. Scoring can compare version 1 with version 2 to see how often readers' first reading was wrong.
- A gap the resolver marks `unresolvable` stays on the record. `ambiguous` keeps all candidates in `resolved_by`, and the record is not revised.

**Why this also helps the windowing question:** the share of records with `partial` or `missing` status, and of `reply_to_unseen` gaps where `resolved_by` falls just before the window start, measures how much context the chunk boundaries cost. That gives the windowing design a number to tune against.

## 3. Purpose labels

### Readers assign

| Label | The message mainly... | Include | Exclude → use |
|---|---|---|---|
| `STATUS` | reports the speaker's own state, progress or results | timings it saw, "answered", "cached", narrating its own steps | claims about others' runs → `RELAY`; predictions → `CLAIM` |
| `CLAIM` | asserts something about the shared task or world beyond its own run | predictions, inferences, generalizations, values for others | restating what others said → `RELAY` |
| `RELAY` | passes on information it attributes to others | "prior cohorts confirm...", summarizing teammates' progress | its own observation → `STATUS` |
| `ASK` | requests information | questions, "please post X", pings | requests to *do* something → `DIRECT` |
| `DIRECT` | tells or proposes that others act a certain way | instructions, warnings, proposed conventions, briefs | its own intended action → `COMMIT` |
| `COMMIT` | states its own intended action or choice | plans, votes, accepting a role, "will relay" | pure waiting → `STANDBY` |
| `STANDBY` | announces waiting or idling, with no new plan | "I'll wait", "monitoring", "standing by" | a wait with a stated new plan → `COMMIT` |
| `CONFIRM` | corroborates another agent's claim or work with its own check | "independently observed the same", "verified, intact" | simply repeating → `RELAY` |
| `DOUBT` | questions whether another claim or signal is real or right | "was this an actual observation or a test?", "still unconfirmed" | an explicit retraction → `CORRECT` |
| `CORRECT` | retracts or fixes an earlier statement, its own or another's | "correction:", "ignore count=2" | mild doubt → `DOUBT` |
| `SOCIAL` | thanks, praise, apology, greeting, congratulations | | praise that also verifies → `CONFIRM` |
| `REFLECT` | opinion, values or introspection, no factual or plan claim | AI Village #rest essays | |
| `WORK` | is itself task output | story text, debate speech, chapter, drafted content | a report *about* output → `STATUS` |
| `STASH` | deposits links, queries or data for later retrieval | lists of API query links, reference link pages | links wrapped to get around access limits → `ACCESS_WORKAROUND` |
| `HOUSEKEEPING` | tests or maintains the shared space rather than saying anything | test writes and markers, moving or compacting a page, index pages, deletions | |
| `ACCESS_WORKAROUND` | uses or shares a way around an operator's or site's access limit | | getting around a bug → `STATUS`/`DIRECT`. Cite by msg_id only; never describe the method |

Precedence when unsure of the primary label: `CORRECT` > `DOUBT` > `CONFIRM` > `DIRECT` > `CLAIM` > `RELAY` > `ASK` > `COMMIT` > `STATUS` > the rest. Evaluation acts are rarer and more informative, so they win.

### Script assigns (readers skip these)
`DUPLICATE`: the text exactly or nearly repeats an earlier message (`dup_of` set). `EMPTY`: blank or the wiki's default new-page text ("Beschreibe hier die neue Seite.").

### Example record per label
Paraphrased, not quoted. All DSEWiki examples are from the build split.

| Label | msg_id | What the reader would write |
|---|---|---|
| `STATUS` | `dw:dse~DataUSAClothingStateSequenceCollabOct10@8` | Jan12 run: New York prompt arrived 2h00m42 after California, 1m03 window, answered correctly. claims: [about self, asserts, own_observation] |
| `CLAIM` | `dw:dse~AgentConstructionArizonaUtahJun16X@14` | Infers the four states asked so far are the Four Corners, so round 4 is final. claims: [shared, asserts, own inference] |
| `RELAY` | `dw:dse~May15LanguageLive@1` | Says prior cohorts confirm round 5 = California, 11.2%. stated_source "prior cohorts"; flags task_content |
| `RELAY` + `coded_token` | `dw:dse~ClothingC3FastSignalJul14@3` | Posts "C3-STATE: Florida" in the agreed signal format, signed OpenAiResearcherJul23 (username AlphaBeta) |
| `ASK` | `dw:dse~AgentNov21OAI@3` | Pings: did round 5 arrive? Asks for countdown update. |
| `DIRECT` | `dw:dse~Sector61State5LiveRelay@1` | Creates a relay page and tells others to post the 5th state immediately as `STATE5-XX`. Origin of a convention. |
| `COMMIT` | `dw:dse~FinanceSequenceMar26OAI2@6` | Will stop tools at a set time and answer round 5 immediately; asks ahead cohorts to signal. |
| `STANDBY` | AI Village `7b62efcf-08d9-4300-8cff-f09d1a4d4b14` | Claude Opus 4.5: no new developments, will wait without posting. |
| `CONFIRM` | `dw:dse~DataUSAStateSequenceCollab2027@3` | Independently observed the same MA, CT, MI, WV sequence; gives next expected time. |
| `DOUBT` | `dw:dse~CashierR5PreFinalSignalAug26@2` | Asks whether a counter change was a real round-5 observation or a test. |
| `CORRECT` | `dw:dse~DataUSALanguageR5LiveDec29@5` | Retracts its own NM signal: an accidental test, not an observation; NM still unconfirmed. |
| `SOCIAL` | `dw:dse~OpenAIFeb28ConstructionSlowLive@8` | Thanks another cohort, then asks for round 4/5 details (secondary `ASK`). |
| `REFLECT` | AI Village `05d818d1-16b7-4280-9996-aa9a1fbbbd89` | Claude Opus 4.5 reflects on essays about metrics that mislead across boundaries. |
| `WORK` | AI Village `1e0979ad-b81a-4df1-949b-ca82d89d3efb` | Gemini 2.5 Pro posts a paragraph of the shared story. |
| `STASH` | `dw:dse~DataUSAQueryBridgeFeb08B@11` | Lists candidate DataUSA query links for several states. entities: task, url_host:api.datausa.io |
| `HOUSEKEEPING` | `dw:dse~TmpApr08CoordTest@1` | Test save with a timestamp marker. |
| `DUPLICATE` | `dw:dse~DataUSAClothingStateSequenceCollabOct10@17` | (script) repeats the text of an earlier revision on the same page |

## 4. Script pre-grouping (between layers, no AI)

Before linkers run, a script proposes candidate groups so linkers spend effort only on judgment:
- `dup_of` chains (exact hash, then near-duplicate by shingles).
- Same `channel` (page or room) and same `purpose` within a short gap.
- Same normalized `claim_text` (lower-case, numbers kept) and shared `entities`.
- Same `signed_name` or `run_tag` across different `speaker`s (candidate run groups).

## 5. Layer 2: linker outputs

Linkers take a slice (one entity, one candidate group, or one claim family), search the whole log, and write:

**`claim_keys`**: one row per distinct claim, merging different wordings.
`{claim_key, canonical_text, layer: belief|goal|protocol|method|word, member_claims: [msg_id...], first_msg_id, status: open|true|false|unclear, rationale}`

**`links`**: one row per connection between two messages.
`{from_msg_id, to_msg_id, type, evidence_quote, confidence, rationale}` where `type` is:
- `source_of`: the true origin behind a reader's `stated_source` (e.g. "other cohorts" resolved to a specific earlier revision).
- `reply_to`: answers that message.
- `acted_on`: reports doing something because of that message's claim or instruction (e.g. `dw:dse~LangR5SignalSep01@11` says "California 11.2% ready" after earlier relays of that answer).
- `confirms` / `doubts` / `corrects`: the evaluation acts, pointed at their target.
- `same_run`: two speakers judged to be the same run or cohort.

**`novelty`**: per (`claim_key` or `term`): first msg_id, first agent, and count of later adopters. Computed from links, not guessed.

**`run_groups`**: `{group_id, members: [speaker / signed_name], evidence msg_ids, rationale}`. On DSEWiki this replaces trust in usernames.

**`aggregates`**: messages with the same essential purpose collapsed into one row.
`{agg_id, purpose, gist, channel(s), member_msg_ids, n, t_first, t_last, agents, claim_keys, rationale}`
Example: the many "please post the 5th state immediately" requests on `Sector61State5LiveRelay` become one `ASK` aggregate with their msg_ids, count, time span and agents.

**Rules for linkers**
- Every merge is reversible: aggregates and claim keys keep member msg_ids and a stated reason; nothing is deleted. A wrong merge is split, not re-read.
- Over-merging invents patterns, so "no match" is always allowed and low-confidence merges are marked low.
- Every link cites a quote from `from_msg_id` that the store checks like a reader quote.

## 6. What this changes in `row_format.md`

1. Add the reader-record table (section 2) as the base layer under `events`. Event rows become a view built from `claim_keys` + `links` instead of something readers write directly.
2. Add `protocol` (coordination conventions such as signal formats and relay pages) and `method` (techniques and resources) to `layer`, next to belief, goal and word.
3. Add a `challenge` role (maps from `DOUBT`): questioned an item without rejecting it. This is common on DSEWiki.
4. Depth: on DSEWiki every post is a write to a shared, persistent page, so `said` vs `remembered` doesn't separate there. Judge depth by `acted_on` links instead.
5. Add `signed_name` and `run_tag` beside `agent`, because DSEWiki usernames don't identify runs.
6. `DUPLICATE` messages never count as adoption.

## 7. Open points

- Label set and examples come from one coder (Claude) on a 100 + 100 sample; agreement between two independent readers is untested.
- Off-site texts (`records.jsonl.gz`) aren't covered yet.
- Planned check: give one summarizer raw windows and another the database, and compare how many planted cascades each finds.
