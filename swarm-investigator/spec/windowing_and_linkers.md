# Reader windows and linker division (draft v1, 2026-10-03)

Answers two questions from Peyton: do chunk boundaries hurt reader records, and how should many linkers split the whole log?
Does not edit `reader_format.md`, `row_format.md`, `store_design.md` or `store_schema.sql`. Section 6 lists what it would ask of them.

**Short answer**
- Boundaries do hurt, but only a little, and a read-only halo fixes most of it. Messages that depend on earlier context mostly depend on the last few messages. A reader that sees the previous 50 messages as context (without writing records for them) loses about two thirds of the boundary damage. The rest points back days, and no window size reaches that. Those need retrieval plus a missing-context flag.
- Linkers should not be split by time. Idea spread is exactly the long-range edge a time tile cuts. Split them by **content** (claim family / entity) across the whole timeline, keep a cheap time-tiled pass for short-range links, and add one reconcile pass over claim keys to stitch families together.
- Swin's shifted windows are the right picture for the local part only. For the long-range part the better analogy is content-routed sparse attention (Routing Transformer / Reformer buckets) plus a few global tokens (Longformer / BigBird).

---

## 1. Measurements

Proxy for "this message depends on an earlier one": the message reuses a distinctive token (PR numbers, IDs, file and page names, words with digits, hyphenated identifiers) that appeared in an earlier message in the same room, used by 2 to 50 messages in total. Distance = how far back the **nearest** earlier use is. It catches named references, not pronouns ("that idea"), and some matches are coincidental, so treat the numbers as rough shape, not exact rates. Scripts: scratch, rerun in minutes.

**AI Village chat** (183,485 messages, all rooms; agent messages are long: median 403 characters, only 1% under 80, 6% open with "Agreed / Yes / Done / Thanks"-style replies)

| | value |
|---|---|
| messages with such a back-reference | 45% |
| distance to nearest earlier use, median | 5 messages (3 minutes) |
| 75th percentile | 27 messages (18 minutes) |
| 90th percentile | 591 messages (44 hours) |
| nearest earlier use more than a day back | 11% of back-referring messages |
| `general` room volume | median 335 messages/day, 90th pct 763; one gap over 2 h per day on average (sessions are daily) |

Share of back-referring messages whose nearest referent falls outside the reader's view, for window W messages and read-only halo H:

| W \ H | 0 | 50 | 100 |
|---|---|---|---|
| 100 | 25% | 16% | |
| 200 | | 15% | |
| 400 | | | 12% |

The distribution is bimodal: a big short-range mass (minutes) and a long tail (days). The halo kills most of the first; nothing window-shaped touches the second. Bigger windows buy little after a 50-message halo.

**DSEWiki build split** (5,129 revisions before 2026-06-18; held-out part not read)

| | value |
|---|---|
| pages | 1,862 on dse; median 1 revision per page, 90th pct 4; 39 pages have 20+ revisions (1,464 revisions) |
| revisions whose added text names another existing page | 16% |
| time since that other page was last saved | median 6 minutes, 90th pct 54 minutes |
| gap to the previous save of the same page | median 5 minutes, 90th pct 1.6 hours |
| volume | median 35 revisions/day, peak 2,603 |

So on DSEWiki a "page" is the wrong channel for windows: most pages are one save, and the context a save depends on is usually a **different** page saved minutes earlier. Windows there should be global time slices across all pages.

## 2. Reader windows

**Core + halo.** A window has a core (records are written for these) and a halo of earlier messages shown as context only. `write_record` rejects a msg_id outside the core, so halo messages never get two records.

| | AI Village | DSEWiki |
|---|---|---|
| unit | room x session (cut at gaps over 2 h, about one per day) | global time slice across all wikis |
| core | about 100 messages; a session over 150 is split | about 100 revisions |
| halo | previous 50 messages of the same room (crosses session cuts) | previous 50 revisions, any page |
| also attached by script | | each core revision's earlier saves of its own page (parent chain, last 3) |

Why a halo and not Swin-style shifted windows: a shifted second pass makes every message read twice and written twice, then needs a rule to pick between two records. A halo costs about 50% more input and no extra output, and every message has one record. (Shifted windows matter in Swin because every patch must be both a query and a key in each layer; readers only need earlier context, so a one-sided halo is enough.)

**Context pack (script, no AI).** For each distinctive token in the core whose nearest earlier use is outside core + halo, the script attaches one pointer: `{token, msg_id, t, speaker, first 200 chars}` of that most recent earlier use. This is cheap and covers much of the long tail with no extra reader calls. The reader can still call `search(query, before=t)` for more. Raw text only, no earlier AI records, so readers don't inherit earlier readers' interpretations (Peyton's rule against pre-interpreted data).

**Missing context: uses `reader_format.md` section 2a as is.** That section already defines `context_status` (complete / partial / missing), `uncertain_fields`, `context_needs[]` with eight gap types and `search_hints`, and versioned `context_resolutions`. This file adds no fields. Where the two connect:
- **Halo and context pack feed `context_seen`.** A reader counts halo messages and context-pack pointers as seen context, so many gaps that would otherwise be `reply_to_unseen` or `unresolved_reference` never get raised.
- **Context-pack pointers seed the resolver.** For each gap, the resolver first checks the pack pointers whose token falls inside the gap's `span` (they're already the nearest earlier use), then runs `search_hints`. Both land in `resolved_by` the normal way.
- **The resolver is a separate pass** (2a leaves the choice open): it runs right after the local linkers and before `pregroup.py`, so family linkers group version-2 records. It also takes a random 5% of `complete` records as a control, to measure gaps readers failed to flag.
- **The boundary-cost number 2a describes** (`reply_to_unseen` gaps resolved just before the window start) is the tuning signal for halo size: if many resolve 50 to 150 messages back, raise the halo; if they're mostly days back, leave it and rely on the resolver.
- `outside_transcript` and `compacted_history` gaps are left to the resolver as `unresolvable`; no window choice helps them.

Cost: if the flag rate is near the 11% long-tail rate, resolution adds about a tenth of reader cost.

## 3. Linkers

The question is which messages a linker can see at once. Swin answers it for images with local windows that shift each layer, and long range comes only from stacking layers (patch merging). Here that would mean day linkers, then week linkers, then month linkers: three tiers of AI cost, and a claim that spreads over two weeks is only joined at the top tier, after every lower tier summarized it away. The measured spread is long-range (a distinctive token's later reuses come a median 3 days after its first appearance), so that is the main case, not an edge case.

Divide the work along two axes instead:

**A. Local linkers (time-tiled, like windowed attention).** One per reader window, after its readers finish. Input: the window's records plus the halo's records and raw text. Writes the short-range links: `reply_to`, `confirms` / `doubts` / `corrects` with their targets, and `acted_on` when the target is in view. The measurement says this is where most of these links live (median 5 messages back). Also fills `reply_to_hint` ids where the reader left a description.

**B. Family linkers (content-routed, like Routing Transformer buckets).** `pregroup.py` builds a candidate graph over records: edges for shared distinctive entities (`page:`, `task:`, `value:`, `term:` with document frequency capped so generic entities can't glue everything together), same normalized claim text, `dup_of` chains, and shared `signed_name` / `run_tag`. Connected components (or communities, if one is huge) are **families**. Each family goes to one linker that sees all member records across the whole timeline in time order, plus raw text on demand and `search`. It writes `claim_keys`, `source_of`, long-range `acted_on`, and aggregates. A message can sit in several families; that's fine because groups are membership rows.
- Family over about 300 records: split by its strongest sub-entity; if still too big, by time with 25% overlap, then a merge step on the claim keys from both halves.
- Singletons (records in no family) skip linking; they can still be a claim's origin later via the reconciler.

**C. Reconciler (the global tokens).** One pass over all claim keys' canonical texts (thousands of short lines, fits one context) to catch the same claim landing in two families under different wording. It proposes merges via `merge_claim_keys` with a rationale; merges stay reversible. This is the content-space version of Swin's shift: a second partition (by claim meaning instead of by entity) so a boundary of the first partition isn't permanent.

**D. Run-identity linker.** Identity is its own axis: families keyed on `signed_name`, `run_tag`, `ip16` and page-title date tags. On DSEWiki everything per-agent depends on it, so it runs before trackers join adoption by run group.

**Order:** readers -> local linkers -> gap resolver (reader_format 2a) -> `pregroup.py` -> family linkers + run-identity linker (parallel) -> reconciler -> trackers / lead.

Novelty stays a view over live claim-key members, so it is only as good as the reconciler. The scorecard should report recall on planted cascades with and without the reconciler, since that isolates how much the family split costs.

## 4. What to build by Sunday

1. `get_window` gains a `halo` argument and `write_record` rejects non-core ids (small change in `store.py`).
2. `window_plan.py`, about 1 hour: session cuts for AI Village, global slices for DSEWiki, context pack per window.
3. Resolver prompt for section 2a gaps, using the context pack first, about 1 hour.
4. `pregroup.py` already planned: add connected components with the document-frequency cap, about 30 minutes extra.
5. Local linker, family linker and reconciler prompts.
Skip if short on time: family splitting by sub-entity (just split by time with overlap), community detection.

Reading budget note: AI Village's `general` room alone is about 400 days at a median 335 messages/day, so a full read is out of reach by Sunday; pick a few weeks around known cascades. DSEWiki's build split (5,129 revisions) is about 50 windows.

## 5. Risks

- The token proxy undercounts pronoun-only dependence ("I agree with that plan"), which is the case Peyton's teammate raised. Those cluster near the message (they're replies), so the halo covers most of them; the `partial` / `missing` rate on a real run will show whether it doesn't.
- A generic entity can create one giant family. The document-frequency cap and a component-size check in `pregroup.py` catch it before linkers run.
- The context pack is itself a bias channel if it surfaces earlier interpretations, so it carries raw text and pointers only.

## 6. Requests to other threads' files

- `reader_format.md` (Agent action taxonomy): none; section 2a is used as written. Only note: halo messages and context-pack pointers count toward `context_seen`.
- `store_design.md` / `store_schema.sql` (Investigator database and analyzers): `get_window(..., halo)`, core-only check in `write_record`, `tasks.tier` value `resolver`, a `families` + `family_members` pair (or reuse `candidates` with basis `family`), and `window_id` with `core` / `halo` ranges on `tasks.scope`.
