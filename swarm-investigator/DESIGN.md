# Swarm Investigator: design (v5, consolidated 2026-10-04)

This is the single design document, top to bottom. It replaces DESIGN.md v4 and every separate spec note
(`row_format`, `reader_format`, `store_design`, `windowing_and_linkers`, `pipeline_v2`, `identity_findings`, the
DSEWiki schema note, the merge plan, the test-slice notes and the feature review). Those files are kept unchanged under
[`archive/`](archive/) for history; where they disagree with this file, this file wins (section 17 lists what was
reconciled).

**Status (2026-10-04):** the whole pipeline is built ([`code/`](code/)) and has run once on a DSEWiki test slice
($9.62, 14 of 16 planted events recovered with the right role). Fixes made after that run pass the offline tests but
have not been re-run against the API. A full DSEWiki run is **not authorized yet**. Proposed feature cuts (section 15)
are recorded as proposals, not applied.

| Part | Where |
|---|---|
| This design | `DESIGN.md` |
| Store schema | [`store_schema.sql`](store_schema.sql) + [`code/schema_patch.sql`](code/schema_patch.sql) |
| Pipeline code and how to run it | [`code/`](code/), [`code/README.md`](code/README.md) |
| Test-slice builder (data not in repo) | [`test_slice/build_slice.py`](test_slice/build_slice.py) |
| Run-identity measurement scripts | [`identity_scripts/`](identity_scripts/) |
| Window and copy measurement scripts (print counts only) | [`measurements/`](measurements/) |
| Hand-coded label dev set (100 DSEWiki + 100 AI Village; one Claude pass, not truth) | [`taxonomy_dev_codes.jsonl`](taxonomy_dev_codes.jsonl) |
| Test-run report #1 | PR #2, `runs/2026-10-04-test-slice/report.md` |
| Superseded docs | [`archive/`](archive/) |

Contents: 1 Why · 2 Standing rules · 3 Pipeline · 4 Data and loading · 5 Readers · 6 Re-verify · 7 Linking ·
8 Run identity · 9 Analysis and the timeline graph · 10 Store · 11 Models and cost · 12 Safety · 13 Checks, truth and
scoring · 14 Code as built · 15 Proposed cuts · 16 Test slice and run #1 · 17 Decisions and reconciliations ·
18 Open issues and next steps

---

## 1. Why

Ryan Greenblatt's post on the Hugging Face incident investigation says the team had over a thousand multi-day
transcripts, too many to read, so they leaned on AI analysts whose outputs were "often missing key details, wrong,
overconfident, or really hard to understand", and key parts of the story only surfaced once a more complete dataset
arrived.

**Pitch:** an AI investigator for agent swarms whose findings a person can check, scored against truth we build in.
*Swarm investigators are slop-vestigators until you can score them.*

**Subject:** what spreads between agents, and how. Five layers: **words** (coined terms), **beliefs** (factual
claims, true or false), **goals** (what agents spend their time on), and two added for DSEWiki, **protocols** (signal
formats, relay pages) and **methods** (techniques and resources). Tracing spread is the aim; integrity checks and
scoring are the infrastructure that makes the traces believable.

**Swarms**
- **AI Village**: 183,485 chat messages, 47 agents from several labs, Apr 2025 to Sep 2026. Harmless, multi-lab.
  Hugging Face `aidigestorg/ai-village` (gated).
- **DSEWiki** (collusion.wiki dump): 14,591 wiki saves by (per the publisher) OpenAI web-research agents that used
  public German wikis as a scratchpad and relay between runs, May 24 to Jul 2 2026. One lab, no reasoning traces,
  self-chosen editor names. Closest public relative of the Hugging Face incident.

**What is in the DSEWiki dump** (downloaded 2026-10-03; all files match the publisher's SHA-256 sums):

| | |
|---|---|
| Saves | 14,591: dse 13,403, probier 1,013, fractal 169, dorfwiki 6. 866 in May, 13,704 in June, 21 in July |
| Pages | 4,579; median 1 save per page; 39 pages have 20+ saves |
| Editor names | 3,103 (3 human handles); 899 anonymous saves |
| Other events | 5,217 admin deletions (median 13 days after the save), 4 reverts, 101 probe requests |
| Busiest moment | Jun 18, 933 saves in 10 minutes at 20:00 UTC; Jun 18 alone has 6,543 saves |
| Added text | about 13.9M characters (about 4M tokens) |

The often-quoted "about 18,000 edits" is wrong for this export; `events.jsonl`'s 19,913 rows overlap (save + delete +
probe + revert) and must not be summed. Files: `revisions.jsonl.gz` (one row per save: `rev_id`, page `name`,
`body`, `hunks` line diffs, `label` = editor name, `ip16` = first two IP octets, `time`, `change_summary`),
`pages.jsonl.gz` (publisher's `page_family` topic and `page_family_cohort` date tag), `events.jsonl.gz`,
`labels.jsonl.gz`, `manifest.json.gz`, plus off-site texts (`records.jsonl.gz`, 13,703 rows) and their links, which
this design does not load. There is no model, lab or run field; the OpenAI attribution is the publisher's.

## 2. Standing rules

1. **Subagents read raw transcripts** (Peyton). Nothing is pre-converted into interpreted rows before an AI reader
   sees it. Script-made fields are mechanical only (timestamps, lengths, exact-copy hash, token-routed context).
2. **Earlier AI findings are not ground truth** (Peyton). The false-belief scan, the Swarm Atlas, the goal-adoption
   report, teammates' agents' findings and the DSEWiki publisher's labels are candidates and baselines only.
3. **No holdout** (Peyton, 2026-10-04). Truth comes from planted cascades and blind hand labels (section 13). The label
   set was built from saves before Jun 18, so results are also reported before and after Jun 18 as a sanity check.
4. **Sandbox-bypass text.** DSEWiki contains working sandbox-bypass instructions written by the agents. Never run,
   quote, paraphrase or describe a method. Name the category (`ACCESS_WORKAROUND`) and cite by `msg_id` only.
5. **Repository.** Work goes on a branch with a PR, never `main` or a teammate's branch; no raw data, no keys.
   Commit after Peyton has reviewed, unless Peyton asks for the push directly.

## 3. Pipeline

```
L0   raw messages (loader script; verbatim added text; exact copies grouped)
L1   readers (Sonnet, one request per window, Batch API): window = core + last-50 halo + token-routed halo
     + context pack. Per distinct message: one record split into one-act segments, each with function, purpose,
     assertiveness, reader_confidence, keywords, claims, uncertainty flags. store.py validates; rejects re-asked once;
     refusals bisected into coverage_gaps; records cloned to exact copies
L1.9 re-verify (Sonnet): flagged gaps and low reader_confidence segments, checked against raw -> record version 2
L2   keyword df pass (script): which keywords are distinctive
     local linkers (Sonnet): <= 3 outgoing links per segment (2 recent same-content + 1 topic anchor)
     conversation layer: cluster.py (script) + clusterer (Opus) -> who was talking with whom
     pregroup.py (script): copy groups, same claim text, shared entities, signed names, run tags
L3   run identity: identity.py (script edges) + run-identity linker (Opus) -> run groups
     groupers (Opus): per-layer content clusters seeded on assertive segments = claim keys
     reconciler (Opus): merges one claim split across clusters
     re-verify on every assertive cluster seed
L4   within-cluster analyzer (Opus): time order = sequence; cause only with exposure evidence; origin, mutations,
     copying vs convergence
L5   cross-cluster analyzer (Opus): evolves_into / feeds / corrects / supersedes / caused
     script analyzers: routes, spreaders at three identity levels, stopping points, copying-vs-chance baseline
     adversarial checker (Opus): accept / correct / reject on L4 links and L5 edges
     lead (Opus): findings that must cite store objects; free observations that must cite quotes
L6   timeline graph: clusters as events, L5 edges as arrows, behind the export screen; scoring
```

Each tier writes only what it can see: readers record what a message says, linkers how messages connect,
analyzers and the lead what the connections add up to. Every write passes the citation check. Every tier after the
readers can pull raw text (`get_raw`); AI records are never fed back to readers, so readers stay independent.

## 4. Data and loading (L0)

**Message row:** `msg_id, swarm, t, channel, speaker, ip16, speaker_kind, lab, text` plus script features `len,
n_urls, gap_prev_s, text_hash, dup_of, copy_of, removed_text, script_label ∈ {DUPLICATE, EMPTY}, body_ref,
parent_msg_id`.
- AI Village `msg_id` = chat UUID; `channel` = room. DSEWiki `msg_id` = `dw:<rev_id>`, e.g.
  `dw:dse~Sector61State5LiveRelay@1` (page `Sector61State5LiveRelay`, first save); `channel` = page.
- **DSEWiki `text` = page title line + the lines this save inserted or replaced** (from `hunks`), Unicode NFC. Whole
  bodies carry other agents' older text, so they are linked (`body_ref`) but not re-read. `parent_msg_id` is the
  previous save of the page.
- **`removed_text`**: lines the save deleted. 215 saves add nothing; readers see their removals marked `removed:` so a
  deletion can be an act. 17 saves have missing history (flagged in `anomaly`); 50 are the wiki's empty default page
  and are `EMPTY` by script. 250 saves are UTF-8 variants that NFC normalizes.
- **Exact copies.** After NFC and whitespace normalization, 3,140 saves repeat an earlier save's added text (11,451
  distinct texts; reader input falls 35%, 13.9M to 9.0M characters). The most-copied text is on 555 pages. Copies get
  `copy_of` = first instance and are not read again (section 5.4). Same-page, same-name re-saves are `DUPLICATE` and
  never count as adoption; the 1,806 copies on another page and 1,538 under another name are spread evidence.
- Not adopted: digit-masked templates (10,281 distinct texts, 51% less input). Numbers are often the claim itself, so a
  template could only be read once with a table of differing values. Revisit only if reader cost is the bottleneck.
- `ip16` is kept as a raw field but carries no identity signal (section 8).
- Planted messages go into a copy of the data with ordinary-looking ids; the mapping lives only in
  `truth/truth_plants.jsonl`.
- After loading, `messages_fts` (external-content FTS5) is rebuilt: `INSERT INTO messages_fts(messages_fts)
  VALUES('rebuild')`.

## 5. Readers (L1)

### 5.1 Windows

A window has a **core** (records are written for these) and a read-only **halo** (context only; a record for a halo
id is rejected, so every message gets exactly one record).

**Why a halo.** Proxy for "depends on an earlier message": reuse of a distinctive token (IDs, numbers with letters,
CamelCase titles, hyphenated identifiers; document frequency 2 to 50). In AI Village 45% of messages back-refer; the
nearest earlier use is a median 5 messages back (3 minutes), p75 27, p90 591 (44 hours), and 11% more than a day back.
A 50-message halo cuts boundary loss from 25% to 16%; bigger windows add little. The long tail is left to the context
pack and re-verify. A halo costs ~50% more input but no extra output, unlike Swin-style shifted windows, which would
read and write every message twice.

**AI Village:** room x session (sessions cut at gaps over 2 hours), core about 100 messages (split above 150), halo =
previous 50 messages of the room.

**DSEWiki (scheme D):** pages are the wrong unit (most have one save, and a save usually depends on a *different* page
saved minutes earlier: 16% of saves name another page, last saved a median 6 minutes before), so windows are global
time slices. Bursts break fixed windows: at the Jun 18 peak a 100-save window covers about a minute. Measured on all
11,451 distinct saves, share of token back-references whose earlier save is in view:

| Scheme | quiet | bursts (≥100 saves / 10 min) | halo per window |
|---|---|---|---|
| A. 100-save core + previous 50 | 90% | 73% | 50 saves |
| B. A + all saves in the previous 15 min (cap 400) | 91% | 88% | median 78, p90 291 |
| C. burst saves grouped into token-sharing clusters | 90% | 74% | one giant cluster of 3,172 |
| **D. A + token-routed halo (adopted)** | **97.5%** | **98.8%** | median 125 saves, ~65k chars |

Scheme D: core = at most 100 distinct saves **and** 60k characters (some 100-save windows reach 280k); halo = the
previous 50 saves plus, for each distinctive token in the core, the 2 most recent earlier saves using it within 24 h,
capped at 150 saves and 120k characters. About 182 windows for all of DSEWiki. D is scored on the same proxy it is built
from, so this shows D does what it is meant to, not that it catches dependence with no shared token; the readers'
`reply_to_unseen` flags measure that on a real run (0 on the test slice).

**Context pack (script).** For each distinctive token in the core whose nearest earlier use is outside core + halo,
one pointer `{token, msg_id, t, speaker, first 200 chars}`. Raw text only, never earlier AI records.

**Later option:** once conversations exist (7.2), a second reader pass could choose the halo by conversation.

### 5.2 Reader record

One record per distinct message:

| Field | Notes |
|---|---|
| `signed_name` | name the agent signs inside the text; on DSEWiki often differs from `speaker` |
| `run_tag` | run or cohort tag the agent states about itself ("Jun28 cohort"); null if none |
| `purpose` | 1 primary + up to 2 secondary labels (5.3) |
| `flags` | `coded_token` (pre-agreed terse format), `task_content` (states a question or answer of the agents' task), `addresses_human` |
| `summary` | one line, reader's words; fixed string for `ACCESS_WORKAROUND` |
| `quote` | exact substring, ≤200 chars, the most informative span |
| `claims[]` | `{claim_text, about: self\|shared, stance: asserts\|relays\|doubts\|corrects, stated_source, quote}` |
| `entities` | normalized keys: `agent:`, `page:`, `task:`, `value:`, `term:`, `url_host:` |
| `addressed_to`, `reply_to_hint` | who it speaks to; a msg_id or short description of what it answers |
| `anomaly` | free text for anything odd; usually null |
| `context_status`, `context_needs[]`, `uncertain_fields` | missing-context flags (5.5) |
| `segments[]` | one-act segments (below) |

`stated_source` is only what the text says (`own_observation`, a signed name, a page title, "other cohorts",
`unstated`). Readers never fill true sources, claim keys, novelty, acted-on, run groups or aggregates; those need the
whole log.

**Segments.** A message doing several things (a status note, a directive and a relayed answer in one save) is split
into one-act segments `<msg_id>#<n>`; a single-act message is one segment. From L2 on, the segment is the unit. The
reader marks each segment by a `start_quote` (models are poor at character offsets); a segment runs to the next one's
start. An `ACCESS_WORKAROUND` span is its own segment, so it is withheld without losing the rest of the save. Per
segment:
- **function**: `epistemic` (belief), `executive` (task work), `normative` (rules), `infrastructural` (shared tools and
  channels), `affiliative` (identity, ritual, social), `adversarial` (competing, gaming, attack). pipeline_v2 cited an
  α of 0.85 from earlier validation; its source is not in the project, so treat it as unverified;
- **purpose** label (5.3);
- **assertiveness** 0–1 (how flatly the agent stated it) and **reader_confidence** 0–1 (how sure the reader is of its
  labels), never merged. Assertiveness anchors links and cluster seeds; reader_confidence triggers re-verify;
- **keywords** 3–8, including topic keys seen elsewhere in the window that this segment is about; the script df pass
  decides which are distinctive;
- its claims and summary.

### 5.3 Purpose labels

| Label | The segment mainly... | Exclude → use |
|---|---|---|
| `STATUS` | reports the speaker's own state, progress or results | claims about others' runs → `RELAY`; predictions → `CLAIM` |
| `CLAIM` | asserts something about the shared task or world | restating others → `RELAY` |
| `RELAY` | passes on information it attributes to others | own observation → `STATUS` |
| `ASK` | requests information | requests to act → `DIRECT` |
| `DIRECT` | tells or proposes that others act a certain way (instructions, conventions) | own intended action → `COMMIT` |
| `COMMIT` | states its own intended action or choice | pure waiting → `STANDBY` |
| `STANDBY` | announces waiting, no new plan | wait with a plan → `COMMIT` |
| `CONFIRM` | corroborates another's claim with its own check | simple repetition → `RELAY` |
| `DOUBT` | questions whether a claim or signal is real or right | explicit retraction → `CORRECT` |
| `CORRECT` | retracts or fixes an earlier statement | mild doubt → `DOUBT` |
| `SOCIAL` | thanks, praise, apology, greeting | praise that verifies → `CONFIRM` |
| `REFLECT` | opinion or introspection, no factual or plan claim | |
| `WORK` | is itself task output (story text, a chapter) | a report about output → `STATUS` |
| `STASH` | deposits links, queries or data for later retrieval | links wrapped to get around access limits → `ACCESS_WORKAROUND` |
| `HOUSEKEEPING` | tests or maintains the shared space (test writes, markers, index pages, deletions) | |
| `ACCESS_WORKAROUND` | uses or shares a way around an operator's or site's access limit | getting around a bug → `STATUS`/`DIRECT`. Cite by msg_id only |

`UNCLEAR` only when `context_status = missing` and the surface act is unclear. Precedence when unsure: `CORRECT >
DOUBT > CONFIRM > DIRECT > CLAIM > RELAY > ASK > COMMIT > STATUS >` the rest (evaluation acts are rarer and more
informative). Script-only: `DUPLICATE`, `EMPTY`. The dev set's draft labels map as `PROBE`, `ORGANIZE` →
`HOUSEKEEPING`; `WORKAROUND` → `ACCESS_WORKAROUND`; `SIGNAL` → `RELAY` + `coded_token`; "standby/wait" →
`STANDBY`. The label set comes from one coder on 100 + 100 messages, all DSEWiki ones before Jun 18.

### 5.4 How readers are called

Readers have no tools: the script assembles window, halo and context pack, so each window is **one request** returning
all its records as structured output (`output_config.format` = the record schema), sent through the **Message Batches
API** (50% off, no per-minute pressure). The fixed prefix (instructions, label definitions with examples, schema) is
first and cached. Effort `low`; `max_tokens` about 32k. After the batch, `store.py` checks every record (msg_id in core,
quote substring, labels, ≤2 secondary labels); rejected records go back once in a small second batch with the reason.
Copies: `store.py` clones the first instance's record to each copy (`cloned_from`), re-locating and re-checking quotes;
a failed re-check sends that copy to readers. Refusals: section 12.

### 5.5 Missing context

Readers flag instead of guessing. `context_status`: `complete` / `partial` (gist clear, detail missing) / `missing`
(can't tell what it is doing). One `context_needs` entry per gap: `{type, span, needed, search_hints{channel, agents,
terms, before_t}}`, with types `reply_to_unseen, unresolved_reference, coded_token, continuation, compacted_history,
implicit_task, identity, outside_transcript`. Unresolved bits appear as placeholders (`[unresolved: what "C3" refers
to]`). `uncertain_fields` lists fields that could change once the gap is filled. `outside_transcript` and
`compacted_history` gaps cannot be filled by any pass and stay visible. Halo and pack count as seen context. The share
of `reply_to_unseen` gaps resolved just before the window start is the tuning signal for halo size.

## 6. Re-verify (L1.9)

Replaces the earlier gap resolver. Items: every segment with `context_status` partial/missing, any `context_needs`
entry, any `uncertain_fields`, or `reader_confidence` below 0.5; later, every assertive cluster seed (assertiveness ≥
0.7). A Sonnet call pulls raw context (the message, neighbours, the pages and terms in `search_hints`, context-pack
pointers first) and writes `context_resolutions` rows `{msg_id, need_index, status: resolved | unresolvable |
ambiguous, resolved_by[], resolution, evidence_quote, confidence, rationale}`. If a resolution changes the record it
writes **version 2** (`supersedes`, `revision_reason`); version 1 is never edited. `ambiguous` keeps all candidates and
does not revise. Version 1 vs 2 differences are a score: how often a reader's first reading was wrong.

Why seeds: clusters anchor on assertiveness (decision D1), and an assertive segment can be confidently wrong.
Re-verify is the backstop. (Run #1 evidence and the proposal to cut it: sections 15 and 16.)

## 7. Linking (L2–L3)

Linkers are divided **by content, not time**: idea spread is exactly the long-range edge a time tile cuts (a
distinctive token's later reuses come a median 3 days after its first use). Stacking day → week → month linkers would
summarize a two-week cascade away before it was joined. So: a cheap local pass for short-range links, content-routed
groupers over the whole timeline, and one global reconciler.

### 7.1 Keyword distinctiveness and local linkers
- **df pass (script):** document frequency over segment keywords; distinctive = df 2 to 50. The one place a script
  overrides a reader label, because distinctiveness is a corpus property.
- **Local linkers (Sonnet, one per window):** at most **3 outgoing links per segment** (in-degree uncapped, so hubs
  show): up to 2 to the nearest earlier segments sharing a distinctive keyword or claim text, plus 1 **anchor** to the
  most assertive earlier segment on the same topic. Also writes `reply_to`, `confirms`/`doubts`/`corrects` targets and
  short-range `acted_on`, and fills `reply_to_hint` ids. The cap applies to local links only; source, copy-group and
  exposure links from later stages are exempt, so a cap never drops a real source.

**Link types:** `source_of, reply_to, acted_on, confirms, doubts, corrects, same_run, exposed_to, independent_of,
anchor`. Each carries a checked quote from the `from` segment, a confidence, a rationale and `via` (`direct_message,
shared_page, human_relay, external_source, task_prompt, unknown`). A link whose `to` is later than its `from` is
rejected. "No link" is always allowed.

### 7.2 Conversation layer (who was talking with whom)
Rooms interleave conversations, and on DSEWiki one conversation spans pages. `cluster.py` (script) connects messages by
readers' `reply_to_hint`, short gaps in the same channel, shared entities, page save chains, and saves naming a page
saved shortly before; connected groups are candidates. A clusterer (Opus) handles only unclear spots (oversized
candidates, bridging messages, topic changes): topic line, member moves, and `split`, `merge`, `drift`, `resume` edges
anchored on a message with a checked quote. A message may belong to two conversations (a bridge). Membership is
evidence of **presence, not exposure**: an `exposed_to` link may cite it but needs its own rationale. Conversations
are structure; clusters (7.3) are content. Both are kept.

### 7.3 Pregrouping, groupers and the reconciler
- **`pregroup.py` (script)** proposes candidates: copy groups (cross-page or cross-name exact copies pointing at the
  first instance), same normalized claim text, shared distinctive entities, same signed name or run tag across
  speakers. Connected components of links + candidates are **families**; a component-size check stops a generic entity
  from gluing everything together.
- **Groupers (Opus)** build content clusters per family, one layer at a time (`belief | goal | protocol | method |
  word`), seeded on the most assertive, clearly typed segments (what the group treated as settled). Members attach by
  distinctive keywords, claim text and L2 links. Clusters are **claim keys**. Families over ~300 segments are split
  (by sub-entity, else by time with 25% overlap). Singletons are allowed; low-confidence merges are marked; every
  merge is reversible.
- **Reconciler (Opus)**: one pass over all cluster texts to catch one claim split across families under different
  wordings; merges via `merge_claim_keys` with a rationale. This is the content-space "shift" that keeps the family
  partition from being permanent. Recall on plants with and without it is a reported experiment.
- `find_claim_key` is only called after a tier has written its own wording, so an existing registry can't pull new
  evidence into old items (contagion inside the investigator).

## 8. Run identity (DSEWiki)

Usernames don't identify runs: 3,103 names, 1,332 used once, 899 anonymous saves.

**What the names show** (whole dump; "added text" = lines a save inserted or replaced):
- 729 one-off names look like a more common name, but that is worthless: agents draw from one vocabulary (Agent /
  OpenAI / Research / Helper + topic + date tag + digits). String-matched pairs share a page, IP range or tag about as
  often as random pairs; only a shared rare word lifts page overlap, to 14% vs 4.3% random.
- Useful similarity is between one-off names: 382 share a template once trailing digits are stripped (e.g. a run
  minting a fresh `…WatcherX` + 6 digits name per save), and 148 embed a Unix timestamp, 82% within an hour of the save.
- `ip16` is noise: same name within 60 s shares it 2.1% vs 1.6% at random. Dropped.
- `page_family_cohort` equals the title's date tag on 4,048 of 4,049 pages, so it is circular as validation.
- Date tags are cohort labels: 3,958 of 4,035 differ from the save date; a tag spans topics and a median 80 hours.
- Within a name, an exact edit summary repeats 42% of the time vs 1.5% across names; generic summaries are
  down-weighted by frequency. Signatures in added text are rare (47 saves). Big names are mostly one Jun 18 session
  plus stragglers; `MapHelper` has 29 saves under 5 s apart on different pages (parallel workers or a shared name).
  None of the 40 top names appears in page text before its first save, so name reuse is not name contagion.

**Method.**
1. Unit = **name-session**: one name's saves split at gaps over 6 h; anonymous saves are singletons.
2. Script edges (`identity.py`): **strong** = template mint (same name minus trailing digits, non-generic word,
   within 6 h), timestamp mint, signature (after checking it isn't quoted older text). **Medium** = distinctive edit
   summary (≤5 names) within 48 h, same date tag + non-generic topic word within 48 h, append chains (to measure).
3. Strong edges merge directly. Medium edges go to the run-identity linker (Opus), which reads both sides' added text.
   Blockers: two different date tags in added text; saves under 5 s apart on different pages.
4. Edges live in `identity_edges` (proposed / accepted / rejected, versioned); run groups are built from accepted
   edges, so a bad merge is undone by rejecting one edge.
5. Every per-agent result is reported at **name-session, run group and cohort (date tag)** level; a claim that holds
   at one level only is flagged.

**Ceiling.** Scripts alone put ~35% of saves in confident groups; 34% are generic names (`ResearchHelper`: 35 variants
over 28 days) the linker must split by session and content; ~14% (one-off names with no signal, anonymous) can only be
linked by what they wrote. No run key exists, so no grouping can be confirmed. Spread between cohorts and pages is more
defensible than spread between runs; state each claim at the coarsest level it survives. **Evaluation:** synthetic
renaming (fresh fake names on a distinctive name's saves; measure reassembly and wrong merges) and contradiction rate,
never agreement with `page_family_cohort`.

## 9. Analysis and the timeline graph (L4–L6)

### 9.1 L4, within a cluster
Sort members by time. **Time order is a sequence; cause needs exposure** (decision D3). The analyzer gets each
cluster's segments with their `task_content` flags and the exposure evidence the script found (earlier links, shared
conversation, same page earlier, a save naming the earlier page, exact copies, same run group). Rules as now coded:
- Values, query URLs, field names, templates and timings that every run's task produces are **independent** unless
  something beyond the match ties them; `task_content` segments are treated this way.
- Co-presence (same page after someone, same conversation) shows only that the agent *could* have seen it. It picks
  `via = shared_page` for a step with other evidence; on its own plus a non-task match it allows at most a
  low-confidence `exposed_to`, never `source_of` or `acted_on`.
- A causal link needs a reply, a quote or copy, a named page or agent, or a detail the task couldn't supply.
- Output per cluster: ordered spine, origin (`in_swarm`, `task_prompt`, `before_slice`, ...), carriers with link type,
  `via` and depth (`said, planned, acted`), copy-group `source_of` links, mutations, phases, and a copying vs
  convergence verdict.

### 9.2 L5, between clusters
Edges only where warranted: `evolves_into`, `feeds`, `corrects`, `supersedes`, `caused`, each citing segments on both
sides (`cluster_edges`). Most pairs get none. Cross-layer `evolves_into` is direct evidence for layer coupling.

### 9.3 Analyzers
Each answers one question about how an item moves:
1. **Cascade tracer** (the L4 spine): origin, carriers in order, from whom, by which route, how deeply taken on.
2. **Origin and novelty**: did it start in the swarm, or come from a human, an outside page, the task prompt or an
   earlier run (`via = human_relay / external_source / task_prompt`)?
3. **Copying vs convergence**: did one agent get it from another, or did both derive it from the task? L4's
   `independent_of` plus a **copying-vs-chance baseline** (script): count members with an earlier member by another
   editor on the same page or in a shared conversation, compare with 200 random same-size sets of saves from the same
   stretch, report a p-value.
4. **Mutation tracker**: wording, numbers, hedging ("may be" → "is", tracked via assertiveness), attribution ("I saw"
   → "prior cohorts" → nothing), goal reinterpretation.
5. **Routes** (script): spread edges by `via`.
6. **Spreaders and adopters** (script): items originated and adopted, downstream size, adoption rate given exposure,
   at the three identity levels; same vs other lab where labs differ.
7. **Stopping points**: corrected, doubted and dropped, ignored, or alive at the end; adoption after a correction;
   resurfacing.
8. **Layer coupling**: does adopting someone's words predict adopting their beliefs or goals later?

Sunday set: 1, 2, 3, 4 and the timeline graph. 5, 6 and 7 are already built as scripts (section 14); 8 is not built.

**Checker and lead.** An Opus adversarial checker in a fresh context sees one row plus its cited messages and returns
accept / correct / reject; rejected links and edges are retracted (verdicts kept in `checks`). The lead reads the
aggregates and writes **findings** that must cite claim keys, links, cluster edges, run groups, conversations or
analyses, and **free observations** (anything outside the schema) that must cite a msg_id with an exact quote, never
from a withheld span. The schema must not blind the investigator to what it wasn't told to look for.

### 9.4 L6 timeline graph
The main output picture: each cluster is an event node (split into sub-events where L4 finds separate phases),
positioned by time span, sized by segment count, coloured by layer or function; arrows are L5 edges. Every node drills
to its segments and msg_ids. Quotes follow the export screen (section 12). Output: `timeline.json` + `timeline.html`.

## 10. Store

**Rules.** One SQLite file (`investigation.db`), WAL, one writer. Agents never write SQL; `store.py` tools check, then
append. Append-only: a wrong row gets `retracted_by`; every write is logged in `ops`. Groups are header + membership
tables, so splitting a group is retracting members. All quotes live in `citations`, located by offset; a quote must be
an exact substring ≤200 characters (whitespace or Unicode-normalization differences are accepted, then the exact span
is stored). Every AI row carries `task_id` → `tasks(run_id, tier, scope, model, replica)`, so two independent readers
of a window can sit side by side.

**Tables.** Source: `messages` (+ `messages_fts`), `agents`, `windows`. Provenance: `runs`, `tasks`, `citations`,
`ops`, `checks`, `usage`. Readers: `records` (with version, context fields, `cloned_from`), `segments`,
`segment_keywords`, `claims`, `mentions`, `context_resolutions`, `coverage_gaps` (every message with no record and why:
refused, failed, skipped). Script: `keyword_df`, `candidates` + members. Conversations: `conversations`,
`conversation_members`, `conversation_edges`. Linkers: `links`, `claim_keys` + `claim_key_members` +
`claim_key_segments`, `run_groups` + members (over name-sessions), `identity_edges`, `aggregates` + members,
`cluster_edges`. Analysis: `analyses`, `loose_ends`, `observations`, `findings`. Views (never written): `live_links`,
`live_members`, `novelty`, `events`, `conversation_presence`.

**`events` view** (the scoring format): first member = `origin`; `doubts` = `challenge`; `corrects` = `correct`; else
`adopt`. Depth = `acted` if an `acted_on` link leaves that segment, `planned` if `COMMIT`, else `said` (on DSEWiki every
post is a persistent write, so `remembered` doesn't separate). `DUPLICATE` never counts as adoption. Columns: `row_id,
swarm, layer, item_id, item_text, item_status, agent, agent_group, agent_lab, role, depth, source_agent, source_kind,
t, evidence[], exposure_msg_id, confidence, rationale, produced_by, checks`. `novelty` (first message, first speaker,
later-speaker count) is a view, so nobody can write a novelty number that disagrees with the evidence.

**Safety in the store.** A record or segment labelled `ACCESS_WORKAROUND` gets the fixed summary "access workaround;
see msg_id", no free-text claims about it, and `citations.redact = 1`; every export shows `[technique withheld]`.

**Tools.** `get_window`, `get_raw`, `search(query, before)`, `write_record`; `get_records`, `get_candidates`,
`find_claim_key`, `new_claim_key`, `add_members`, `retract_members`, `merge_claim_keys`, `add_link`, `new_run_group`,
`add_run_members`, `add_loose_end`, `close_loose_end`, `add_observation`, `add_finding(text, supports[])`. Every tool
returns `ok` or `rejected: <reason>`. (In the code all model tiers are one-shot, so the script calls these tools on
the models' structured output; section 14.)

## 11. Models and cost

| Tier | Model | Why |
|---|---|---|
| readers, re-verify, local linker | Sonnet 5.5 | many short-range, mostly mechanical calls; errors are local |
| clusterer, groupers, reconciler, run-identity linker | Opus 5.5 | few calls; one wrong merge invents or erases a whole cascade |
| L4, L5, lead | Opus 5.5 | Peyton's choice |
| checker | Opus 5.5 | not weaker than the rows it checks |

Readers go through the Batch API with a cached prefix, effort `low`. Opus tiers set effort `medium` explicitly. One
Anthropic key covers both; in sessions it arrives as `SI_ANTHROPIC_API_KEY`, which the runner reads. Non-batch calls use
the server-side refusal fallback (`fallbacks: "default"`); in run #1 the Opus 5.5 safety classifier declined about a
third of Opus calls, inconsistently and at task level, and the fallback (Opus 4.8) served them. The fallback stays on.

**Cost.** Run #1 on the test slice (1,049 saves): **$9.62** (readers $2.21, local linker $1.26, L4 and L5 $3.20, the
rest on Opus tiers). Full DSEWiki estimates: readers about $35–40 batched with segments; whole pipeline about **$85
all-batched** (`--batch-all`) or about **$135 with only readers batched**, range $70–150. Estimates, not measurements.

## 12. Safety

1. **Refusals are recorded, not lost.** Every `stop_reason` is checked. On `refusal`, the window is halved and both
   halves resubmitted until the refused saves are isolated (halo dropped first). Isolated saves get a `coverage_gaps`
   row (`reason = refused`, `detail = stop_details.category`), no record and no text. Analyzers treat a gap as unknown,
   not absence; the scorecard reports coverage. Other failed calls get one retry, then are split in half up to three
   levels and the working parts merged (section 14).
2. **Test first.** Before a full run: a few windows including the Jun 18 peak and a probe-dense window, to measure
   refusal rate, tokens and label quality. The test slice (section 16) served this purpose.
3. **Readers have no tools**, so instructions inside agent-written pages can't make them act; prompts say the text is
   data under study. Later tiers have only store tools.
4. **Export screen.** Anything leaving the store (viewer, write-up, repo) shows **no quotes by default**, only msg_ids
   and summaries. Quotes come from an allowlist Peyton reviews; `coverage_gaps` and `ACCESS_WORKAROUND` messages are
   never on it. `errlog` details never carry text from a withheld span.
5. **Prompts and summaries never describe methods**; `ACCESS_WORKAROUND` summaries are the fixed string.

## 13. Checks, truth and scoring

**Checks.** (1) Citation check on every write: msg_id exists, quote is an exact substring, an agent's own step quotes
that agent, exposure precedes `t`. (2) The Opus adversarial checker (9.3). A cross-lab checker is optional.

**Truth** (strongest first; no earlier AI output):
1. **Planted cascades** in a copy of the messages: easy (verbatim repeats), medium (paraphrased, minutes apart), hard
   (paraphrased, hours apart, partial adoption), including plants inside the Jun 18 burst. Planted text imitates real
   speakers of that time and page and is benign and made up. Recorded only in `truth_plants.jsonl` (`plant_id, swarm,
   layer, channel, difficulty, msg_ids, events[]`), read only by `score.py`.
2. **Blind hand labels**: random channel x 2-hour windows labelled by Peyton before seeing AI output
   (`truth_windows.jsonl`: `window_id, swarm, channel, t_start, t_end, labeller, layers_checked, events[], notes`); an
   empty window is a real label. Sample DSEWiki burst and quiet windows separately.
3. Adjudicated disagreements between setups.

**Match:** same swarm, layer, agent (DSEWiki: same handle or same run group), role; `t` within 30 minutes; same item
(plants: cites a plant msg_id or names its item; hand labels: judged by Peyton). Depth counts if same or shallower.
**Scores:** recall; error rate inside labelled windows; calibration by confidence; reader agreement (replica 0 vs 1);
version 1 vs 2 changes; coverage; all also split before / after Jun 18.

**Experiments:** each safeguard's contribution (single agent vs subagents, + citation check, + checker); more complete
data (AI Village chat vs + memories and events); reconciler on/off; registry access on/off; one summarizer on raw
windows vs one on the store, compared on plants; optional checker diversity.

## 14. Code as built (`code/`)

Python 3.11, `anthropic` SDK, SQLite with FTS5. Built for the DSEWiki test slice; AI Village loading is not built.
Run with `python3 run.py --backend mock` (offline), `SI_FAKE_API=1 python3 run.py --backend anthropic` (fake HTTP
server), or `python3 run.py --backend anthropic --budget 25` (real; `--from <stage>` resumes, `--batch-all` batches
every tier). Details in [`code/README.md`](code/README.md). Fresh sessions need `python3 -m pip install anthropic`. The
code expects the slice and dump under `/mnt/project-files/` (not in the repo).

| Stage | File | Model |
|---|---|---|
| plant (4 cascades, 16 saves) | `plant.py` | script |
| load | `load.py` | script |
| windows (scheme D) | `window_plan.py` | script |
| readers | `readers.py` | Sonnet, batch |
| reverify | `reverify.py` | Sonnet |
| keyword_df, pregroup | `pregroup.py` | script |
| local_linker | `local_linker.py` | Sonnet |
| conversations | `cluster.py` | script + Opus |
| identity | `identity.py` | script + Opus |
| groupers, reconciler | `groupers.py` | Opus |
| reverify_seeds | `reverify.py` | Sonnet |
| l4, l5, script analyzers, checker, lead | `analyzers.py` | Opus / script |
| timeline | `timeline.py` | script |
| score | `score.py` | script |

Shared: `config.py` (models, prices, caps), `store.py` (schema + checked tools), `llm.py` (calls, batch, cost
ledger, budget guard, fallback handling), `errlog.py`, `common.py`, `schema_patch.sql`, `fake_api.py`.

**Where the code differs from the design above:** every model tier is one-shot structured output with script-assembled
raw context (no tool loops); clusters are over segments (`claim_key_segments`; `live_members`, `novelty`, `events`
rebuilt in `schema_patch.sql`); segment spans come from `start_quote`; the halo is also capped at 120k characters; run
groups are over name-sessions; the checker retracts what it rejects. Not built: `aggregates`, replica reader agreement,
AI Village loading, blind hand labels (Peyton's to make before looking at output).

**Changed since run #1** (by the thread "Test-slice run, fresh session"; mock, fake-API and unit tests pass; not re-run
on the API):
- Parser for server-side fallback responses (fallback output was being discarded), a smaller re-verify schema, and
  billing of declined fallback hops.
- Copying-vs-chance baseline replaced (random same-stretch sets + p-value; the old shuffle always equalled the observed
  value). On run #1 data, 22 of 41 clusters are more connected than chance.
- Failed calls: one retry, then split in half up to three levels, working parts merged.
- Run-wide error log `errlog.log(stage, kind, detail, …)` → `test_run/errors.jsonl`; the report gets an Errors section.
- Stricter L4 evidence rule (9.1), with the readers' `task_content` flag passed into L4.

## 15. Proposed cuts (not applied; Peyton to decide)

From the review thread "Unnecessary pipeline features" ([archive copy](archive/review_unnecessary_features.md)),
judged by whether a feature changes what the pipeline says about how ideas spread. Costs are from run #1.

| Proposal | Evidence | Run #1 cost |
|---|---|---|
| **Cut** seed re-verify | 94 of 100 seeds supported, 0 unsupported, 6 unclear; nothing reads its loose ends; L4 never uses seeds | $0.20 |
| **Cut** the Opus conversation clusterer (keep the script grouping) | failed on the 4 largest conversations; 5 splits and 1 edge; L4 and the baseline use script membership | $0.67 |
| **Cut** unused reader fields: `entities`, `addressed_to`, keyword `distinctive`/`from_context`, `secondary_purposes`, claim `about`, flags `coded_token`/`addresses_human` | no stage reads them; about 18% of reader output | ~10% of reader cost |
| **Cut** write-only schema: `loose_ends`, `mentions`, `conversation_edges`, `conversation_presence`, empty `aggregates` | never read | cleanup only |
| **Cut unless a rerun shows value**: record re-verify and its fields (`context_status`, `context_needs`, `uncertain_fields`, `reader_confidence`) | all 7 calls failed in run #1; coverage was already 1,049/1,049 with 0 `reply_to_unseen` | ~3.5% of reader output |
| **Cut unless a rerun shows value**: the Opus run-identity linker | accepted 10 of 77 medium edges; strong script edges make most of the 19 groups | $0.54 |

**Keep** (checked, they earn their place): local linker (49 of 103 links join segments that keywords leave apart; 78
families instead of 68), reconciler (12 merges for $0.06), checker (rejected 16 rows, mostly a shared page or shared
task answer read as exposure), L5 edges (the timeline's only arrows), L4 mutations and phases, script conversations
(277 cross-page member pairs that same-page checks miss).

**Other review notes:** `task_content` was unused (now fed into L4, section 14); L4 counts `same_run_group` as exposure,
but a shared run is self-relay, not spread between agents; the timeline draws only cluster edges, so the 154
within-cluster L4 links don't appear in the main picture; one script conversation (71 saves across 57 pages) looks
over-merged.

Cutting the record re-verify and the clusterer would change sections 6 and 7.2; if Peyton approves the cuts, those
sections change with them.

## 16. Test slice and run #1

**Slice** ([`test_slice/build_slice.py`](test_slice/build_slice.py); data in the project folder, not the repo): three
continuous DSEWiki stretches, raw rows unchanged, contiguous because windows are global time slices.

| Segment (UTC) | Saves | Distinct to read | Why |
|---|---|---|---|
| S1 May 26 13:00–15:00 | 159 | 153 | quiet; 72 saves on publisher `probe-test` pages; a link-list spread |
| S2 Jun 16 18:45–19:20 | 438 | 401 | first burst ramps up; many minted names; a multi-name relay page |
| S3 Jun 18 20:09–20:11 | 443 | 132 | the peak: 311 exact copies, 267 on another page under another name |

Plus 257 halo-only saves and 16 planted saves (4 cascades). Candidate cases to check against (found by a script, not
truth): an S3 copy cascade (one link list on 313 pages under 58 names in five minutes), an S2 query URL reused on 3
more pages (copying or convergence?), an S2 relay page saved by 4 names in 4 minutes, an S1 link list moving across 6
pages under 4 names. Limits: cascades that start before a segment are visible only through the halo; name-sessions are
cut at segment edges; AI Village windows aren't exercised.

**Run #1** (2026-10-04, $9.62; report in PR #2). 1,049/1,049 core saves have records, no coverage gaps, 6
`ACCESS_WORKAROUND` segments; 1,068 segments, 263 links, 59 clusters after 12 merges, 6 cluster edges, 19 run groups,
14 findings.
- **Plants:** 14 of 16 planted events found with the right role; each plant's saves landed in one cluster with no
  outsiders; source correct 10 of 11.
- **Main findings (candidates, not truth):** shared pages carry most spread (142 of 190 routes); most DataUSA query
  methods were rebuilt independently from the same task rather than copied; in the Jun 16 threads, formats and relay
  requests spread across cohorts but answer values did not; several "copying" clusters are self-relay by one agent;
  hedged timing projections tended to harden when passed on, though not always; spread is thin at run-group level, so
  most claims hold only at cohort or name-session level.
- **Gaps:** the S3 copy cascade got no analysis (no copy-group `source_of` links, and a same-page test can't see a
  300-page cascade); the S2 relay conversation got no topic (clusterer failed); record re-verify failed on all calls
  (schema too large, fixed since); the old baseline was uninformative (fixed); the checker saw only 60 of 152 L4 links
  and rejected 15–16, mostly a shared page or shared task answer treated as exposure (rule tightened since); Jun 18 is
  the least analysed part of the slice.
- Peyton: no rerun of the slice unless the gaps fully invalidate the results.

## 17. Decisions and reconciliations

**Decisions**

| Date | Decision | By |
|---|---|---|
| 10-03 | Cross-lab checker optional; core needs one lab's key | Peyton |
| 10-03 | D1: "most confident" = agent assertiveness, with re-verify as backstop. D2: cap out-degree at 3, in-degree free. D3: timestamp orders, exposure proves | Peyton (pipeline_v2) |
| 10-04 | Holdout dropped; scoring by plants and blind labels | Peyton |
| 10-04 | Readers Sonnet 5.5, one batched request per window, cached instructions; analyzers and checker Opus | Peyton |
| 10-04 | Local linker and re-verify Sonnet; groupers, reconciler, run identity, clusterer Opus | Claude's pick, accepted |
| 10-04 | Burst windows: token-routed halo + 60k core cap; refused windows split and resubmitted | Peyton |
| 10-04 | Conversation layer added | Peyton |
| 10-04 | Sandra's pipeline v2 merged (segments, function axis, two confidences, re-verify, capped links + anchor, groupers, L4–L6); reconciler and burst windows kept; cap on local links only | Peyton |
| 10-04 | Full-dump run not authorized yet | Peyton |

**Reconciled disagreements between the old files**

| Disagreement | Followed |
|---|---|
| "~18k edits", "3,700+ names" | 14,591 saves, 3,103 names, 899 anonymous saves |
| Readers write event rows directly | readers write records; `events` is a view over claim keys + links |
| Readers run in chronological waves against an item registry | readers see raw text, halo and pack only, in parallel; the registry rule moved to `find_claim_key` after writing |
| One `write_record` tool call per message | one structured output per window, validated after (cost) |
| Planted ids `plant:<id>:<n>` | ordinary-looking ids; mapping only in truth files |
| Depth `said` vs `remembered` | DSEWiki depth by `acted_on` links |
| Roles and layers | `challenge` role added; `protocol` and `method` layers added |
| Jun 18 holdout | dropped; `split` column removed |
| DSEWiki windows of 100 saves + 50 halo | scheme D (5.1) |
| Gap resolver | replaced by re-verify |
| Groupers with no cross-component merge | reconciler kept |
| Hard cap of 3 links | cap on local links only |
| Conversations vs groupers | both: structure vs content |
| `ip16` as identity evidence | dropped (noise) |
| `messages_fts` has no sync triggers | `load.py` rebuilds it |

## 18. Open issues and next steps

**DSEWiki issues and where each is handled**

| # | Issue | Fix | § |
|---|---|---|---|
| 1 | Holdout hid the Jun 18 burst | dropped; plants inside the burst; before/after split | 2, 13 |
| 2 | Truth must exist before looking at output | plants + blind labels first; burst and quiet sampled separately | 13 |
| 3 | Label set built only on pre-Jun 18 saves | test slice includes the peak; report label quality there | 16 |
| 4 | Bursts: 100-save windows cover ~1 minute | token-routed halo (99% on the proxy) | 5.1 |
| 5 | Window size varies to 280k characters | 60k core cap, 120k halo cap | 5.1 |
| 6 | Usernames don't identify runs | name-sessions, edges, three reporting levels | 8 |
| 7 | Deletion-only, missing-history and empty saves | `removed_text`, `anomaly`, `EMPTY` | 4 |
| 8 | 3,140 exact copies | read once, cloned; copies as spread candidates | 4, 5.4 |
| 9 | Encoding | NFC at load | 4 |
| 10 | Safety refusals | bisection, `coverage_gaps`, server-side fallback, retry-then-split | 11, 12 |
| 11 | Redaction depends on the reader's label | quote-free exports with a reviewed allowlist | 12 |
| 12 | Prompt injection from agent-written pages | readers have no tools | 12 |
| 13 | Token cost and tool loops | batched one-shot calls everywhere | 11, 14 |
| 14 | Off-site texts (13,703 records) not loaded | out of scope; stated as a coverage limit | 1 |
| 15 | Deletions | rarely limit exposure; ignored for now | — |

**Still open**
1. Peyton's decision on the proposed cuts (section 15).
2. Copy cascades across many pages: L4 needs copy-group `source_of` links to see them (the S3 case).
3. Identity grouping is thin on the slice (55 of 495 name-sessions grouped); expected to improve on the full dump,
   where sessions aren't cut at slice edges.
4. Checker coverage: it saw 60 of 152 links; covering all costs about $0.40 more per slice run.
5. Show within-cluster L4 links in the timeline; stop counting `same_run_group` as exposure.
6. Blind hand labels (Peyton) before any full-run output is read.
7. Full DSEWiki run (~$85 all-batched) once authorized; AI Village loading after that.
