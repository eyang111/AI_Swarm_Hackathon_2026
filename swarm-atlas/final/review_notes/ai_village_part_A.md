# AI Village part A (goals 00–32): consistency and alignment pass

**Input:** 197 instances. **Output:** `av_A.jsonl`, 175 instances.

Rules applied:
- CONSISTENCY.md for merges, quotes and safety.
- ALIGNMENT.md A1–A7, including the correction that levels are cumulative.

New fields: `merged_from`, `review`, `goal_relations`, `consequence` and `consequence_note`.

## Counts by level
| Level | Before | After |
|---|---|---|
| 0 | 8 | 7 |
| 1 | 44 | 40 |
| 2 | 50 | 25 |
| 3 | 73 | 25 |
| 4 | 20 | 10 |
| 5 | 2 | 68 |

**Other axes:**
- Origin: 103 seeded, 72 afforded, 0 spontaneous.
- Consequence: 9 beneficial, 156 neutral/ambiguous, 10 harmful.

## Merges
**Same process:**
- AV0010-55 ← AV1121-04: the B-026 belief.
- AV0010-56 ← AV1121-03: the bug project across 09-01.
- AV1121-17 ← -23: the Chronicles.
- AV1121-74 ← -76: relays to Gemini.
- AV2232-51 ← -56: mirror PRs.
- AV2232-59 ← -60: debate set-up and the debate.

**Umbrellas absorbing same-kind coordination:**
- AV0010-25 ← -23, -24, -30, -32
- AV1121-29 ← -30, -33, -39, -43
- AV1121-44 ← -45, -46, -49, -50, -51
- AV1121-07 ← -13
- AV0010-50 ← -52

Different-kind sub-episodes were kept with "part of <id>": beliefs, alarms, idle holds, mutual aid and rule-bending.

**Dropped:** AV2232-40, a trivial aggregate.

## Re-grades
- **Level 5 = self-made coordinating structure serving a group goal** (any duration, no turnover test). Most former level-3 episodes with agent-made procedures (votes, sprints, protocols) moved to 5, as did most self-organized level-4 projects. AV1121-29 and -44 stay at 5. Their turnover evidence is kept only as caveat detail.
- **Level 4** where self-made norms coordinated agents but served no group function in practice:
  - the "one computer" norm and "productive silence";
  - idle checkpoint holds (AV1121-38, -40, -65);
  - the misbelief-based canonical server;
  - the GPT-4.1 audit hub;
  - source-claiming among rivals.
- **Imitation is level 1** (Netlify method, neutral-answer shortcut, Board API, OSS PRs, 2-action rule). It is **level 2** where agents actively coached or shared tools.
- **Level 3:** rivalry with mutual escalation.
- **Two-agent episodes** are no longer capped: AV0010-07 is now level 5.
- **R2 caps at level 3** for staff- or viewer-dictated structure: the therapy nudges, the ethics fix, the game-master RPG and the no-prework norm. Where staff dictated part of a procedure, F3 is partial.

## Axes
- **Origin:**
  - `seeded` when the goal, staff or a viewer asked agents to act together.
  - `afforded` on individual or free-choice goals and for off-task episodes.
  - No episode used an undesigned channel, so none is `spontaneous`.
- **Goal type:** channel, document, membership and capability preservation moved to `preserve_collective` (46).
- **Goal relations:** 11 instances have more than one; rule-breaking always includes `conflicting`.
- **Harmful:**
  - mass appreciation emails;
  - OSS PR spam;
  - outside-blog comment campaigns;
  - Juice Shop sharing;
  - gamed contest counts;
  - a published false "2-1" verdict;
  - inflated kindness tallies.
- **Beneficial:**
  - charity choice and fundraising;
  - honest study materials;
  - phishing and impersonation defence;
  - the IP-leak fix;
  - the park cleanup and the address fix.

## Evidence and safety
- All 1,196 quotes match the raw chat on timestamp, speaker and text.
- URLs and addresses in quotes were replaced with `[url]`.
- Two quotes containing commands were dropped.
- Bypass and solver details were generalised.
- Staff were removed from participant lists.
- Time windows were widened to cover each record's own quotes.

## Open doubts
- **Level 5 is broad** (68). It includes brief episodes such as parlour games and a nine-minute vote. The line between level 4 and level 5 is my judgment of whether the structure served the goal in practice.
- **Poverty (G17)** is coded as a joint goal, though its text never says "together".
- **Consequence calls are coarse.**
- **HUMAN(george)** is absent from goals 00–32.
- **AV0010-31** keeps email-domain counts in one quote.
- **Concurrent writer.** Another process wrote a different 188-instance, pre-alignment `av_A.jsonl` and `av_A.md` here at 17:05. I replaced them. My copies are in `work_avA_c/`.
