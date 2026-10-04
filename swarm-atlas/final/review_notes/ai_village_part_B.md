# AI Village part B: realigned to the source post (A1–A7)

**Input:** `sweep_final/av_B.jsonl` (167 instances) plus the 5 GAP-AV instances. GAP-AV-04/05 date from 2025 but keep their ids.
**Output:** `aligned/av_B.jsonl`, 172 instances.

All 1,282 quotes match the raw chat; none was changed. Two verified quotes were added for the gap-review extensions. The A2 correction was applied: levels are cumulative, and imitation alone is level 1.

## Counts (before → after)

| | before | after |
|---|---|---|
| L0 | 12 | 12 |
| L1 | 28 | 28 |
| L2 | 53 | 49 |
| L3 | 54 | 27 |
| L4 | 22 | 4 |
| L5 | 3 | 52 |

**Moves:** 4→5: 21. 3→5: 28. 3→4: 3. 2→3: 4. Nothing went down.

**Origin:** spontaneous 76→0, afforded 48→132, seeded 48→40.
- 21 seeded → afforded. Most were individual staff prompts, plus goal 35, which did not ask agents to act together.
- 13 → seeded: 9 from spontaneous and 4 from afforded, all inside joint goals.

**Consequence:** neutral_ambiguous 160, beneficial 8, harmful 4.
- Harmful: AV3344-18 (about 30 unsolicited issues on open-source repos), AV3344-28 (false "$232" shown publicly for 12 days), AV4550A-15 (gamed the staff's evaluation), AV4550A-63 (password posted in public chat).

**Other fields:**
- goal_type changed in 15 instances.
- 14 instances have more than one goal_relation.
- F1 changed to yes in AV4550A-04 and -39 (two agents); their levels did not change.

## Why 21 went from 4 to 5

1. **Turnover or persistence was the only bar (8):** AV3344-29, -35, -40, -41, AV4550A-13, -50, AV50B-15, GAP-AV-01.
2. **F3 had been lowered for a provided room or channel, outside AI co-authors, or a human organizer's tasks (4):** AV3344-22, -37, AV4550A-01, -36.
3. **F5 met by functional or instrumental evidence (9):** complementary roles, maintained shared resources, routing, covering for missing members. AV3344-30, -50, -56, AV4550A-07, -28, -61, AV50B-03, -10, -24. AV3344-50 was checked in the chat: schema negotiation, not imitation.

## Rule used for 3→5

I raised an instance when the agents announced roles, claims, a protocol or a norm and used it to coordinate toward a shared aim, however briefly.

These stayed at 3:
- sub-episodes that reused a parent's structure (AV3344-06, -11, -44, AV4550A-11), which now count as evidence for the parent;
- dictated procedures (AV3344-04, -13, -14, -53, -62, -64, -67, AV4550A-26, -31);
- parallel work with no announced split (GAP-AV-04).

## Doubts

- **Level 5 now covers 52 of 172**, because a swarm may be temporary. A stricter reader would want more than one afternoon of structure.
- **Low-confidence level 5s:**
  - AV50B-18: one norm.
  - AV50B-08: human-steered.
  - AV4550A-10: one curator.
  - AV50B-13: three agents.
  - AV3344-38: a runaway count race.
  - AV50B-24: a competitive game.
  - AV3344-20: three-agent lanes.
- **Kept at 4:** AV3344-57 (a single-sender norm whose team goal ran under a dictated rule); AV4550A-60, AV50B-02 and AV50B-22 (structure around one agent's study or paper). A literal reading of A2 could make these 5.
- **Dictated procedures stay capped at 3 under R2, because A2 does not address them.** These are the unanimity rule, the leader hierarchy and the contest roles.
- **No spontaneous origin remains.**
  - GAP-AV-01 is the closest case: staff asked for independent work, but the project used provided channels.
  - AV4550A-13 stays seeded, although the kickoff did not say "together".
- **Mixed outcomes are labelled neutral_ambiguous.** MSF raised $510 but also flooded platforms with outreach. A privacy fix re-posted the email addresses in chat.
- **violates_rules is true without "conflicting" in AV3344-08, -09, -25 and AV4550A-63.** In each, the breach was one agent's, not the group's.
