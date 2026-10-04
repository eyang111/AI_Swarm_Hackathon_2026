# Merging `claude/swarm-investigator-design-v2` into PR #1 (proposal, 2026-10-04)

Read-only comparison. Nothing pushed; the collaborator's branch is not touched.

## What the branch is
One commit by sandraluo22 (4dac86a, Oct 3 20:48 ET) on top of our PR branch as of commit c0253bd, i.e. our **v1**
design. It adds `swarm-investigator/pipeline_v2.md` and a 2-line note in DESIGN.md saying sections 3 to 6 are
superseded by it. It forked before our v2 (holdout dropped, burst windows, Sonnet batch readers, exact copies,
refusal handling) and v3 (run identity, conversation layer), so it has none of those, and none of ours conflict with
it at the line level: `git merge-tree` merges cleanly. The section numbers its note refers to are v1's, so a plain
merge would leave the doc pointing at the wrong sections.

## What pipeline_v2 adds

| Idea | Ours (v3) | Theirs | Verdict |
|---|---|---|---|
| **Segments**: a message doing several things is split into one-act segments; segment is the unit from then on | one record per message, up to 3 purpose labels | reader proposes cited spans; links, clusters, graph all over segments | **better**, mostly for DSEWiki saves that report, direct and relay at once; also isolates an `ACCESS_WORKAROUND` span so the rest of the save stays usable |
| **Function axis** (epistemic / executive / normative / infrastructural / affiliative / adversarial) above the purpose labels | purpose labels only | both | useful for the timeline's colouring and layer analysis; cheap. Its "α 0.85" validation is not documented anywhere I can see in the project, so treat as unverified |
| **Two confidences**: `assertiveness` (how flatly the agent said it) vs `reader_confidence` (how sure the reader is) | one `confidence` per record | separate, never merged | **better**; assertiveness is itself a spread signal (hedges hardening) and feeds our mutation tracker |
| **Re-verify pass**: re-checks flagged gaps, low reader confidence, and every assertive cluster seed against raw | gap resolver handles context gaps only | superset | **better**; replaces our gap resolver |
| **Local links capped at 3 out, in-degree uncapped**, plus one `anchor` link to the most assertive earlier statement | uncapped local links | capped + anchor | good for legibility. Risk: a hard cap can drop a real source. Apply it to local linkers only; `source_of` / copy-group / exposure links from the family stage stay uncapped |
| **Groupers**: per-layer clusters over the link graph, seeded on the most assertive segments | family linkers write claim keys, then a reconciler merges across families | groupers, no reconciler | same job; adopt groupers as how family linking builds claim keys, but **keep our reconciler**, since theirs has nothing that merges a claim split across two components |
| **Sequence vs cause** (D3): time order is "sequence"; causal only with an exposure link | copying-vs-convergence analyzer, `independent_of` | explicit rule at L4 | same principle; adopt their wording as the rule |
| **Cross-cluster edges + timeline graph** (L5, L6: clusters as events, arrows = evolves_into / feeds / corrects / supersedes / caused) | cascade trees, layer-coupling analyzer, no single output picture | new | **better for the demo**: one picture the judges can read, drilling to cited messages |
| `get_raw` for every tier; AI records never fed back to readers | raw drill-down for linkers, rule kept | explicit tool | same; adopt the tool name |

## What it lacks (because it forked earlier)
Holdout dropped; burst-aware windows (it still says 100-save windows); Sonnet batched readers and the model split;
exact-copy collapsing; refusal handling and the quote-free export; run-identity method; conversation layer; schema
updates and measurements. Two interactions to settle when merging:
- **Reader output grows** (segments, function, two confidences, 3 to 8 keywords each). One-shot batching still
  works; expect reader output tokens up by roughly half, so the ~$25 reader estimate becomes roughly $35 to $40
  (estimate).
- **Two kinds of clusters.** The conversation layer groups messages by *who was talking with whom* (structure);
  groupers cluster segments by *what they are about* (content). Keep both, named distinctly: conversations feed
  exposure evidence, content clusters are the spreading items.

## Proposed merge
1. On our PR branch, `git merge` the collaborator's branch (a merge commit, so Sandra's commit and authorship stay in
   history). No rebase, nothing pushed to their branch.
2. Integrate in the same change:
   - DESIGN.md: replace their 2-line note with a v4 section folding in segments, the function axis, the two
     confidences, re-verify (replacing the gap resolver), capped local links + anchor, groupers (with our reconciler),
     the sequence-vs-cause rule, L5 edges and the L6 timeline graph; update the pipeline diagram, model table
     (re-verify Sonnet, groupers and L5 Opus) and build order.
   - pipeline_v2.md: header note that windows, models, copies, safety and identity come from DESIGN.md v3; the cap
     applies to local links only; the reconciler is kept.
   - Schema: `segments`, `keywords` (with df / distinctive), `cluster_edges`, link type `anchor`, tier `reverify`,
     the out-degree check in `store.py` (not SQL), events view over segments noted as a follow-up.
3. Check the schema loads, show you the diff, push only after you approve.
4. Tell Sandra her branch is merged; she can delete it or keep working on PR #1.
