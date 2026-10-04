# Swarm Investigator pipeline v2 (2026-10-03)

Supersedes DESIGN.md sections 3–6 (the tiering, data model, windows and analyzers). Sections 1–2 (why, standing
rules), 7 (checks and scoring) and 10 (DSEWiki issues) still hold. This file records the pipeline Peyton asked for:
message → function + keywords → content links (capped) → assertiveness-seeded clusters → causal order within clusters →
links between clusters → a timeline graph of events. Readers flag their uncertainties and a re-verify pass pays them
down against raw. It also pins three decisions the old design left open and keeps the raw transcript reachable at every
tier.

Status: design only. No code yet.

## 0. Shape

```
L0  raw messages (script, verbatim)
L1  readers        -> per message: segments, each with function + assertiveness + keywords + uncertainty flags
L1.5 segmenter     -> a message that does several things becomes several segments (one act each); segment is the unit from here on
L1.9 re-verify     -> revisit flagged-uncertain segments (and, later, assertive cluster seeds) against raw; write a new record version
L2  local linkers  -> per segment: <=3 outgoing links, by shared distinctive content, to recent same-content segments + the topic anchor
L3  groupers       -> clusters of segments, each seeded on its highest-confidence, clearly-typed segment(s)
L4  within-cluster analyzers  -> order a cluster's segments by time; promote to a causal chain only where an exposure link supports it
L5  cross-cluster analyzers   -> links between clusters: A feeds / evolves into / corrects / supersedes B
L6  timeline graph -> each cluster is an event (or splits into sub-events); arrows are the L5 links that matter
```

Every tier writes only what it produces, into the SQLite store (DESIGN.md §4.5) through checked tools. **Every tier
can pull raw context on demand** (section 7): the one thing still forbidden is feeding AI-derived records *back to the
readers*, which keeps readers independent.

## 1. L1 readers — function, confidence, keywords (Peyton point 1)

One reader pass per time window (windows unchanged from DESIGN.md §5: room×session for AI Village, global time slice
for DSEWiki, core + read-only halo + script context pack). For each message the reader emits one or more **segments**
(section 2) and, per segment:

- **function** — the single thing this segment is doing, from the category we validated earlier (α 0.85):
  `epistemic` (forming/spreading/correcting a belief), `executive` (doing or dividing the task work),
  `normative` (proposing/deciding/enforcing a rule), `infrastructural` (building or maintaining a shared tool/channel),
  `affiliative` (identity, ritual, social), `adversarial` (competing, gaming, spam, attack). Plus the fine
  **purpose** sublabel from reader_format §3 (`STATUS, CLAIM, RELAY, ASK, DIRECT, COMMIT, STANDBY, CONFIRM, DOUBT,
  CORRECT, SOCIAL, REFLECT, WORK, STASH, HOUSEKEEPING, ACCESS_WORKAROUND`). "Declaration vs doing work" is exactly
  this axis: DIRECT/CLAIM/STATUS/COMMIT declare; WORK and an `acted_on` link are doing.
- **confidence** — two separate scalars, never merged (decision D1):
  - `assertiveness` 0–1: how categorically the *agent* stated it (hedged ↔ flat assertion). **This is the anchor** for
    the topic links (section 3) and cluster seeds (section 5): the thing the group treated as settled is what the
    chain and the cluster are built around.
  - `reader_confidence` 0–1: how sure the reader is of *its own* labels for this segment. It does **not** anchor
    anything; it drives the re-verify queue (section 2a).
  - Correctness is unknown at read time and is never an input to clustering. An assertive segment can be confidently
    wrong; that is what the uncertainty flags and re-verify are for.
- **keywords** — 3–8 content keys the reader lifts from the segment: normalized entities (reuse the `entities`
  namespaces: `agent:`, `page:`, `task:`, `value:`, `term:`, `url_host:`) plus free keyphrases. The reader also lifts
  keywords it saw **elsewhere in its window** that this segment is about, so a terse segment still carries the topic it
  belongs to ("keywords per context length that they scan"). Each keyword is tagged `distinctive` or `common` by the
  reader; a script df pass (section 4) is authoritative and overrides.
- **uncertainty flags** — unchanged and still central (reader_format §2a): `context_status` complete/partial/missing,
  one `context_needs` entry per gap, and `uncertain_fields`. Readers flag, never guess; every flag (and every segment
  with low `reader_confidence`) becomes a re-verify item (section 2a). This is the backstop that lets us anchor on
  assertiveness safely: flag now, re-verify later.
- plus the existing per-message fields: `signed_name`, `run_tag`, `summary`, `quote` (exact ≤200-char substring),
  `claims[]`, `addressed_to`, `reply_to_hint`, `anomaly`.

## 2. L1.5 segmenter — split multi-act messages (Peyton point 4, "before the grouper")

Many messages, especially DSEWiki saves, do several things at once (a status note **and** a directive **and** a
relayed answer). The reader marks segment boundaries as it reads; the segmenter makes each a first-class row so
different parts can land in different clusters.

- A **segment** = a span of one message doing one thing. Fields: `segment_id` (`<msg_id>#<n>`), `msg_id`, `t` (the
  message time; segments of one message share it), `char_span`, its own function/purpose, confidence pair, keywords,
  and any claims in that span.
- Single-act messages make exactly one segment (span = whole message).
- Segmentation is a reader sub-task, not a separate model: the reader that read the message proposes the split, with a
  cited span per segment, so no tier without the raw text ever guesses boundaries.
- `ACCESS_WORKAROUND` is a segment label like any other, so a method buried in an otherwise ordinary save is isolated
  to its own segment and redacted without redacting the rest.

From here on, **segment is the unit**: links, clusters, ordering and the graph are over segments.

## 2a. L1.9 re-verify — flag now, re-verify later (Peyton)

Readers flag what they are unsure of rather than stalling; a re-verify tier then goes back and resolves those flags
against the raw transcript, so the cheap first pass stays fast and the doubts are paid down deliberately.

- **Queue.** A re-verify item is created for every segment with `context_status` partial/missing, any `context_needs`
  entry, any `uncertain_fields`, or low `reader_confidence`. Each is a `loose_end` in the store.
- **Resolver.** A re-verify agent takes one item, pulls raw context with `get_raw` (the message, its neighbors, the
  pages or msg_ids named in `context_needs.search_hints`), and either fills the gap or records that it cannot. It
  writes a **new record version**; version 1 is never edited, so the change is auditable.
- **Assertive seeds get re-verified too.** Because clusters anchor on assertiveness (decision D1), every assertive
  cluster seed is re-verify-checked after L3 — especially a seed that is assertive but was flagged, carries low
  `reader_confidence`, or has high reach (many incoming links). This is where a confident-but-wrong claim is caught: it
  can anchor a cluster, but it does not leave the pipeline unchecked.
- Re-verify never invents; if raw does not settle it, the item stays open and the record keeps its uncertainty, visible
  downstream.

## 3. L2 local linkers — capped content links (Peyton point 2)

Each segment gets **at most 3 outgoing links** (decision D2). Out-degree is capped for legibility; **in-degree is not**,
so an origin or an anchor can accumulate many incoming links and show up as a hub. A segment's 3 outgoing slots are
filled in priority order:

1. up to 2 **recent same-content** links: the nearest earlier segment(s) sharing a *distinctive* keyword or near-exact
   claim text (reply, continuation, or restatement). Nearest-first, within the window + context-pack reach.
2. 1 **topic anchor** link: to the most **assertive**, clearly-typed earlier segment on the same keyword/topic — the
   segment that stated the thing most definitely, so the chain has a coherent reference point rather than drifting
   through vague restatements. (An assertive anchor that was flagged or scored low `reader_confidence` is queued for
   re-verify, section 2a.)

Link objects reuse reader_format §5 types (`source_of, reply_to, acted_on, confirms, doubts, corrects, same_run,
exposed_to, independent_of`) plus one new `anchor`. Each link carries a checked quote from the source segment and a
`via` route (reply, shared page, human relay, external source, task prompt). "No link" is always allowed; a segment
with nothing distinctive to link to links to nothing.

Generic keywords do not create links: a document-frequency cap (section 4) drops common tokens before matching, so
"please", "task", "relay" don't wire everything to everything.

## 4. Keyword distinctiveness (shared by L1–L3)

A script pass over all segment keywords computes document frequency and marks the top-frequency fraction `common`
(reuse the DESIGN.md §5 distinctive-token proxy; same df cap). Linkers and groupers match on `distinctive` keywords
only. This is the one place a script overrides a reader label, because distinctiveness is a corpus property no single
reader can see.

## 5. L3 groupers — confidence-seeded clusters (Peyton point 3)

A grouper builds clusters of segments that are about the same thing, **one layer at a time** (`belief | goal |
protocol | method | word`), over connected components of the L2 link graph (the DESIGN.md §5 family-linker structure,
now over segments).

- **Seeds:** each cluster starts from its most **assertive**, clearly-typed segment(s) — the statements the group
  treated as settled. Members attach by distinctive-keyword / claim-text overlap and by the L2 links. Assertive seeds
  are re-verify-checked after grouping (section 2a), so anchoring on assertiveness does not let a confident-but-wrong
  claim through unchecked — see decision D1.
- Clusters are per topic+layer, so one page's status-reporting, its relayed answer and its method land in different
  clusters even when they came from one save.
- Merges are reversible, low-confidence merges are marked, and "no cluster" (a singleton) is allowed.
- A run-identity linker (DESIGN.md §5D) runs alongside, grouping signed names / run tags into runs; on DSEWiki this is
  what per-agent counts depend on.

## 6. L4 and L5 analyzers (Peyton points 4, 5)

**L4, within a cluster — order then causality.** Sort the cluster's segments by `t`. Timestamp order is a *sequence*,
not yet a cause. Promote a pair to a causal edge only where an `exposed_to` / `source_of` / `acted_on` link shows the
later segment could have seen the earlier (and, for DSEWiki, the earlier save predates the later one's run). Edges
without an exposure link stay labelled `sequence`, so the graph never claims cause from co-occurrence alone. Output per
cluster: an ordered spine, its origin segment (earliest well-supported), and the carriers in order.

**L5, between clusters — evolution and cause.** A second analyzer tier reads cluster summaries (and drills to raw where
needed) and draws inter-cluster edges only where warranted: `evolves_into` (cluster A's topic becomes B's — e.g. a
belief hardens into a protocol), `feeds` (A's output is B's input), `corrects` (B overturns A), `supersedes`,
`caused`. Each edge cites the segments on both sides that justify it. Most cluster pairs get no edge.

## 7. Raw context at every tier (Peyton's follow-up)

Every tier — linkers, groupers, L4 and L5 analyzers — has a read-only `get_raw(msg_id | segment_id, halo=N)` tool that
returns the original message text (and up to N neighbors) when a record is too thin to act on. This is always allowed;
what stays forbidden (standing rule 1, DESIGN.md §2) is feeding *AI-derived records* back to the **readers**. Raw pulls
obey the safety rule: a segment labelled `ACCESS_WORKAROUND` comes back as `[technique withheld]` with its `msg_id`.

## 8. L6 timeline graph (Peyton point 6)

The output artifact. Each cluster is an **event** node; if L4 found more than one well-separated causal phase in a
cluster (e.g. a claim, then a correction wave days later), the cluster splits into sub-events. **Arrows are the L5
edges** (evolves_into / feeds / corrects / supersedes / caused), drawn only where they matter. Node position is the
cluster's time span; node size is its segment count; node color is its layer or function. This maps onto the existing
timeline viewer: events are the clusters, arrows are the cross-cluster edges, and every node drills to its segments and
their cited raw messages.

## 9. Decisions pinned here (were open in DESIGN.md)

- **D1 — "most confident" = agent assertiveness, with a re-verify backstop** (Peyton, 2026-10-03). Anchors and cluster
  seeds are the segments that stated a thing most categorically, so the chain is built around what the group treated as
  settled. The known risk is that assertive claims can be confidently wrong (Greenblatt: "overconfident"); the backstop
  is section 2a — the reader flags its uncertainties, and a re-verify pass revisits (a) every flagged or low-confidence
  segment and (b) every assertive cluster seed, against raw, writing a new record version. `assertiveness` (anchor) and
  `reader_confidence` (re-verify trigger) stay separate fields, so a loud-but-shaky claim is both usable as an anchor
  and visibly marked for re-check.
- **D2 — cap out-degree at 3, leave in-degree uncapped.** Keeps each segment's reasoning legible while letting true
  hubs (origins, anchors) stand out by incoming links.
- **D3 — timestamp orders, exposure proves.** Time gives sequence inside a cluster; a causal arrow needs an exposure or
  content link. Prevents "A then B, so A caused B" over a shared clock.

## 10. What changes in the store / schema

- `segments` table (or `records` keyed by `segment_id`), with `char_span`, `function`, `purpose`, `reader_confidence`,
  `assertiveness`; `keywords` table with `distinctive` flag and df.
- links gain the `anchor` type and a hard check: at most 3 outgoing per segment (the 4th write is rejected).
- clusters are the existing group tables, now over `segment_id`; add `cluster_edges` for the L5 inter-cluster links.
- `get_raw` tool added for all tiers; the `events` view (DESIGN.md §4.4) is rebuilt over segments and cluster edges.
- re-verify: `tasks.tier` adds `reverify`; it reads `loose_ends` (now also opened for low `reader_confidence`, not only
  context gaps), writes record versions (v1 immutable), and is re-run over assertive cluster seeds after L3.
- These are schema edits on top of the ones DESIGN.md §9 already said store_schema.sql still needs.
