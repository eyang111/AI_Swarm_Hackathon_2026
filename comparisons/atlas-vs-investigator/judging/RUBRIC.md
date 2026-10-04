# Cross-catalog matching task

Two analysis methods were run independently over the same log: 14,591 saves on a public wiki that many AI research
agents edited between May 24 and Jul 2 2026. Each method produced a catalog of what happened.

- `catalog_E.json`: 87 entries ("episodes"). Each has a title, a summary, a time span, the wiki pages it covers
  (`pages` and/or a `page_pattern` regex), key quotes and notes.
- `catalog_I.json`: 502 entries ("items"). Each has a kind (belief, goal, protocol, method, word), a one-line text,
  a time span, the number of saves and editors, the top pages, phase names, an analysis note and member summaries.

The catalogs differ in granularity: episodes are often broad (a whole relay network), items are often narrow (one
belief, one convention, one link list). That is expected. Judge content, not format.

## Your job
For every entry in your batch file, decide whether the OTHER catalog also captured the same phenomenon.

- **match**: the other catalog has one or more entries that explicitly describe the same specific phenomenon, meaning
  the same relay, convention, belief, method or behavior, in the same task family and period. Different framing or
  granularity is fine. For a broad entry, it is a match when entries in the other catalog together describe its
  central phenomenon (its core relay, convention or belief), not just incidental content on the same pages. For a
  narrow entry, a broad entry counts as a match only if its text explicitly mentions this specific thing.
- **partial**: the other catalog covers the same activity (same task family, pages and period) but does not describe
  this specific phenomenon, or describes only a minor part of it.
- **none**: nothing in the other catalog covers it.

The batch file lists candidates found by page and time overlap. They are a starting point only: also search the
other catalog by keywords (task family, page names, distinctive tokens, values), because overlap can miss real
matches and include irrelevant ones. Be strict and consistent. Do not give credit for shared page names alone.

## Rules
- Use only the files in this folder. Do not open any other files or repositories.
- Some entries concern ways agents got around access limits. Never describe a technique in your output; refer to
  such entries only by id.
- Keep each reason under 25 words.

## Output
Write a JSON array to the output path you were given, one object per batch entry, in batch order:
`{"id": "<entry id>", "verdict": "match" | "partial" | "none", "matched_ids": ["<ids in the other catalog>"], "reason": "<short>"}`
Then reply with only the counts of each verdict.
