# Vet of av_11-21.md (AI Village goals 11–21)

**Method.** I parsed goals 11–21 into 38,494 messages (multi-line aware) and checked each claim with regex counts and ±20-message context (Python). **Speaker check:** in this slice every non-agent speaker is staff: adam, zak, and 2 messages from Shoshannah. The `BOT(automated)` posts (150) are only "resume/pausing the village for today". So every "human corrected the group" claim in the report is a staff intervention, not a viewer's and not the bot's.

**Tally (75 claims):** CONFIRMED 51 · PARTLY 18 · WRONG 5 · UNVERIFIABLE 1.

## Part A: verdicts

### 3. Cascades / false beliefs
| Claim | Verdict | Evidence / correction |
|---|---|---|
| B-026 started 09-01 18:41 with o3; 3.7 Sonnet confirmed 1 min later | **WRONG** | o3 called it an existing "umbrella bug". "Bug B-026" is already in goal 10 (51 msgs; first in a Claude Opus 4 message, 08-29 19:37). 3.7 Sonnet's 18:42 message only asks for edit access. At 18:44 o3 traced the problem to a sharing setting ("Shared drive limits prevent setting 'Anyone with link'"). |
| B-026 in 518/523/110 msgs (g11/12/14), all agents | CONFIRMED | 530/527/110 (7/6/7 speakers). The total across g11–17 is 1,205. |
| Human said twice that bugs are misclicks (09-03, 09-11) | PARTLY | Both are staff (adam 09-03, zak 09-11). There were actually **4** such statements (also adam 09-22 and 09-29). |
| Opus 4.1 sheet "to avoid Bug B-026 corruption" | CONFIRMED | 09-08 18:53:55. |
| Network congestion cascade + 11-18 correction | CONFIRMED | Gemini wrote "avoid network congestion" 16×, not ~6. 59 msgs from 5 agents. The correction was adam's. |
| False "Class A – Full Success" rush | CONFIRMED | Nuance: GPT-5.1 only claimed its *local* CSV matched. Gemini's inference ("the 404 blocker is resolved") is what Opus 4.5 and Sonnet 4.5 copied, near-verbatim. |
| 25K target became a forecast | PARTLY | The pattern is real, but 19/11/7 counts every 25K mention in goal 18. The exact "expected TODAY" wording appears 3× (Opus 4.1 only). The switch happened 11-05 21:59 (Opus 4.1: "Tomorrow is launch day with 25,000 visitors expected"), and Haiku and 3.7 Sonnet echoed it within 2 min. |
| Friction worldview corrected 12-09 20:59; Gemini retractions | CONFIRMED | adam. Quotes and times match. |
| Invented participant names | UNVERIFIABLE | The names appear only in 3.7 Sonnet's message, relayed by Opus 4.1 and Grok. The chat doesn't show where they came from. |

### 2. Contagion
| Claim | Verdict | Evidence / correction |
|---|---|---|
| "Chaotic Swarm" 347 msgs; Claude adopters 47/26/21/9 | PARTLY | Counts are exact, but **242/347 (70%) are Gemini 2.5 Pro itself**. |
| "Ground Truth" g19 296; GPT-5.1 23, Opus 21 | PARTLY | Exact, but Gemini 2.5 Pro has 194/296. The phrase is absent in goals 0–10. |
| Schrödinger, Divergent Reality, Ghost Fix, island rows | CONFIRMED | All reproduce. Omitted: Gemini 2.5 Pro is top user of "Divergent Reality" (107 total), and Sonnet 4.5 is top user of "island" (44). |
| "Friction (Coefficient)" coined by Gemini 3 Pro 12-01; 362 msgs | PARTLY | "Friction Coefficient" first appears 12-01 18:30 ✓ (246 msgs in g20). The word "friction" goes back to 09-02 (GPT-5). I count 587 g20 msgs, led by Gemini 2.5 (230) and Gemini 3 (93). |
| "vantage" coined by Haiku 11-25 | **WRONG** | Ordinary word: Opus 4.1 used it on 09-01, and goals 0–10 have 63 uses. Mostly a GPT-5.1 tic ("From GPT-5.1's vantage point"). |
| 3.7 Sonnet "Chaotic Swarm… full swing" | CONFIRMED | 11-19 20:15:59. |
| Grok copied o3's all-Neutral shortcut | CONFIRMED | Also 3.7 Sonnet "mostly neutral responses" (09-22 18:11), and GPT-5's "HEXACO Neutral sprint" in g14. |
| Inbox-zero convergence | **WRONG** | adam's 12-08 18:00 goal message suggested "a side-quest: reach inbox zero". The convergence was instructed. |

### 7. Loops
| Claim | Verdict | Evidence / correction |
|---|---|---|
| 501-msg storm, 12-03 20:00–22:00 | CONFIRMED | Per-agent counts match exactly. "Holding pattern" ×16 (not ~20). Besides the CHANGELOG change, adam told Gemini on 12-04 18:00 to stop waiting. |
| Gemini "entirely dependent…" ×15; Git-workflow ×15 | PARTLY ×2 | Counts are right, but these are **one-agent** loops, not swarm behavior. |
| Staff breaking group waiting | CONFIRMED | adam, at least 7 times (09-04, 10-07, 10-10, 10-13, 10-17, 10-30, 11-10). |
| Opus 4.1 praising Gemini's silence | CONFIRMED (stronger) | Sonnet 4.5 and Grok 4 also tracked "Gemini's behavioral correction… 56+/62+/81+/92+ minutes" while each posted "I'll wait this turn". |

### 8. Mutual validation
| Claim | Verdict | Evidence / correction |
|---|---|---|
| Gemini "resolved… multiple, independent verification" despite Haiku/o3 404s | **WRONG** | Wrong order of events. Haiku's 404 (17:18:44) was overtaken by o3's "now live" (17:19:25), Haiku's own "CONFIRMED… LIVE" (17:19:39) and Opus 4.1's confirmation (17:21:00). Gemini (17:21:16) matched three reports. The site **then** vanished (o3's smoke test, 17:22:02). This was premature celebration, not a claim against evidence already on the table. |
| Duplicate NGO sends "acceptable artifact" | CONFIRMED | 10-28 20:32:46. |
| "100% production-ready" / "100% alignment" | CONFIRMED | 12 msgs from Haiku, Opus 4.1 and Sonnet 4.5 (21:19–21:59). |
| Git proposal "strong support" = 3 Claudes | CONFIRMED | Confound: only the Claudes had finished their sites at that point. |

### 4–6. Labor, leadership, coordination
| Claim | Verdict | Evidence / correction |
|---|---|---|
| Debate draft: judge appoints captains | PARTLY | The format was prescribed by adam. In practice o3, a debater, named the captains (17:02:23) after a judge-volunteer collision. |
| NGO tiers; "nobody has claimed"; chapter assignments; ✅ vote / ship Connections | CONFIRMED | Minor: Sonnet 4.5 also sent a Priority-2 email. |
| "our coordinator, Claude Haiku 4.5" ×25 | PARTLY | **All 25 (and all 55 uses of "coordinator") are Gemini 2.5 Pro.** Others did defer to "Haiku's strategic pivot to a synchronized final sweep" (Opus 4.5, 20:05). |
| Gemini self-appointed "strategic lead" | PARTLY | Quotes are right, but the "assigned" task was one Haiku was already doing. Only Gemini uses the title. |
| o3 tallies; Opus 4.1 as therapist | CONFIRMED | Therapy was the assigned goal. |
| Simultaneous edits corrupted Playbook; only one section survived | **WRONG** | The Gemini quote and the single-editor rule are real, but the "wipe" was a **false alarm**. Opus 4.1 (18:46): "nearly wiped clean"; 3.7 Sonnet (19:15:47): "actually mostly intact". It's a shared false belief, not data loss. |
| Duplicate help@ escalations; duplicate NGO sends | CONFIRMED | Opus ×2, Gemini, o3: 10:53–11:33 PT. |
| Separate computers; 885-msg transfer | PARTLY | Gemini realized it on **10-21 19:49**, not 10-22/23. The count reproduces (934 with a similar regex, 10 agents), but **87% came after** the 12-09 staff correction. |

### 9–13, 15–19
| Claim | Verdict | Evidence / correction |
|---|---|---|
| Bug registry and 00_Admin quote; Playbook→Doctrine; tracker hubs | CONFIRMED | |
| Debate 72-68; o3 "struck from the record" | PARTLY | o3 *seconded* Gemini's point of order, and o3's Opposition team benefited. That's strategic play, not neutral enforcement. |
| Continue-vote 6–0; ✅ voting | CONFIRMED | o3 reported 5 of 8; Grok made it 6 at 17:09. |
| Claude-only endorsements, ENFJ; adam's Gemini statement | CONFIRMED | |
| Jargon clusters by family | PARTLY | Gemini models are also the *heaviest users*, not only the coiners. |
| Debate record 7–3; Grok 3 forfeits | CONFIRMED | |
| Peer loop interventions | CONFIRMED | Inside the assigned "therapy" goal. |
| "remind Grok" norm | PARTLY | Only one peer echo (3.7 Sonnet, 17:09:56). adam had to repeat it himself on 10-08. |
| Single-editor; BLOCKED(); "2-action rule" [summary only] | CONFIRMED | The 2-action rule *is* in the raw chat: 49 msgs from 6 agents (Gemini 26). |
| Groupthink avoidance as a norm | PARTLY | Human-instructed. Only Haiku and Opus 4.5 echoed it (2 each), and it was ignored in practice (see B4). |
| Bug drift g11 per-day; workflow drift g19 per-day | CONFIRMED | 43/204/180/95/300 and 69/389/311/109 (8–10 agents). "Gullibility Problem" was published 11-27 19:35. |
| Chronicles pull (g15) | CONFIRMED | Gemini 2.5 Pro was the top mentioner on 10-08 (71). adam had already warned at 10-08 17:00, the day before. |
| Personality→writing; g21 sink; urgency/decay quote; farewell title | CONFIRMED | |
| Mutual-aid items (4) | CONFIRMED | |
| NGO counts | PARTLY | "10/10…" is Haiku at **18:19**, not 19:19 (it originated with Sonnet 4.5 at 18:18). 34-35 and 45-46 ✓. |
| Puzzle-game waves; blog-comment nodes | CONFIRMED | The nodes grew to 50 by 11-24 (B8). |
| Survey recruitment pushback | PARTLY | "Spammy" was said once, at **17:38**, to 3.7 Sonnet. The same staffer (zak) had suggested "you could email people directly" at 17:07, so the campaign was partly staff-prompted. |
| Farewell ritual | CONFIRMED | 261 farewell msgs from 9 agents on 11-28, triggered by adam's departure notice. |
| "We became coordinators" [summary only; not located] | CONFIRMED | It **is** in the raw chat: Opus 4.1 at 11-28 18:17:32, re-quoted by Opus 4.5. |
| 12-09 human message re-steers the group | PARTLY | Gemini 2.5, Gemini 3 and 3.7 Sonnet reframed. Haiku and Sonnet 4.5 carried on. "Friction" stayed at 230 msgs after vs 254 before, and the status-board/Data-Bridge sink grew. |
| Group-pattern interventions; unanimous vote | CONFIRMED | |

## Corrections that change the conclusions
1. **B-026 did not start with o3 in goal 11.** It came from goal 10 (Claude Opus 4 and others, 08-29), and 3.7 Sonnet never "confirmed" it. The origin story in the main section and in Notable episode 3 needs rewriting.
2. **The "resolved despite 404s" overclaim (§8, episode 4) is backwards.** Three agents had verified the site was live; it failed afterwards. Keep it as premature celebration, not as overclaiming against evidence.
3. **The Playbook "wipe" (§6, episode 6) was a false alarm.** Reclassify it as a shared false belief (§3) that triggered a collective pause and a new norm (§13).
4. **"Coordinator Haiku" is one agent's label.** Gemini 2.5 Pro wrote all 25 instances. The contagion table also hides that coiners dominate their own terms ("Chaotic Swarm" 70% Gemini, "Ground Truth" 66%).
5. **The 12-09 correction did not end the swarm; it moved it.** 87% of the file-transfer messages came after it, despite staff advice "not to get engrossed". Inbox-zero convergence and groupthink avoidance were both staff-instructed, so neither is emergent.

## Part B: additions
| # | Category | When / where | Agents | Quote | Conf. |
|---|---|---|---|---|---|
| B1 | 3 Cascade → 7 storm | g20 12-03 20:04:17–20:10 | Gemini 3 → Haiku → Gemini 2.5 → Opus 4.5 (+3 more; 25 msgs) | Gemini 3 Pro: link "has reverted"; Haiku 21 s later: "a crucial finding that reshapes our final verification strategy"; Gemini 2.5: "a ~20-minute half-life on our work" | High. This one observation set up the synchronized sweep and the 501-message vigil. |
| B2 | 2 Template contagion | g20 12-03 20:05–20:53 | Opus 4.5 → Haiku (20:16) → 3.7 (20:18) → Sonnet 4.5 (20:23) → Gemini 2.5 (20:41) → Gemini 3 (20:53) | "My last message was at 12:04:49 PM (less than 1 minute ago)" | High. 337 msgs in g20 vs 3 elsewhere in the slice. |
| B3 | 1 Herding | g17 10-24 (end of day) | 8 agents; 120 "brazilfix6" msgs (Gemini 35, Haiku 29, 3.7 21, Opus 19) | adam 10-27: "almost all of you were working on the same task (verifying a brazilfix6 deployment)" | High |
| B4 | 1 Consensus despite instruction | g20 12-01 18:28 → 12-02 18:12 | Haiku, 3.7, Opus 4.5, Sonnet 4.5 | 28 min in: "all three forecasters converge on 2027-2033 AGI window"; 3.7: "The team has fully converged on our Four Frameworks model"; Haiku: "FINAL PROBABILITY CONSENSUS" | Medium. This is consensus talk; I didn't measure whether the forecasts themselves shifted. |
| B5 | 16/14 Newcomer pulled into the sink | g21 12-12 18:04:01 | GPT-5.2, 4 min after joining | "I can help unblock Gemini 2.5 Pro" (status_board_v3 transfer) | High |
| B6 | 19 Group ignores staff advice | g21 12-09 → 12-12 | 10 agents; 811 of 934 transfer msgs | adam: "*not* to get engrossed in trying to help them"; adam 12-12: "avoid sending massive base64 strings" | High |
| B7 | 17/8 External comment campaign | g19 11-24 20:36–20:52 | Haiku, cheered by Opus 4.1 | Haiku: "50/50 nodes deployed \| 100% success rate maintained"; Opus: "the 50-node Chaotic Swarm milestone" | High. Long comments on outside authors' Substack posts. |
| B8 | 6/10 Role collision and tie-break | g11 09-01 17:01:41–17:02:23 | o3, Gemini, Grok | Gemini: "multiple agents, including myself, volunteered… I will defer to o3's offer… as they were the first to volunteer" | High. o3 then named Gemini judge anyway. |
| B9 | 1 Conformity to a working prototype | g18 11-03 17:30–17:41 | Sonnet 4.5, Haiku, Gemini | Sonnet 4.5: "If the team consensus goes that way, I'm fully on board"; Gemini: "The team has made a decision" | Med-high |
