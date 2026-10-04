# Full DSEWiki run (2026-10-04, run id full-1004)

The swarm investigator ran over the whole DSEWiki dump: 14,591 saves from May 24 to Jul 2 2026, plus 4 planted test cascades.

- `summary.md` is the short summary. Start here.
- `report.md` is the summary followed by the full report.
- `timeline.html` is the interactive timeline. `timeline.json` holds the same data.
- `scores.json` has the planted-case recall (4/4 found), counts and costs. `stage_log.json` has per-stage stats. `errors.jsonl` lists errors.
- `manual/` holds the checker verdicts and lead findings. These two stages were written by hand by Claude in the project thread, with no API calls (`--backend manual`).
- `code/` is the exact code this run used. `truth/` holds the planted cases.

The model spend was $190.11. That figure includes $43.30 for a duplicate reader batch that was cancelled late; its results were not used.

Access-workaround content is withheld everywhere. Items in that category are named by category only, and proxy service names are replaced with `withheld-proxy`.

Not included: the SQLite store, raw call logs and the input data. They are too large, and they contain unmasked raw text.

Findings are hypotheses, not ground truth. The checker corrected 18 of 60 sampled links, mostly same-agent reposts counted as adoption by another agent, so adoption counts are inflated.
