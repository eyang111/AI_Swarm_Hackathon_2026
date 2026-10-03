# Second-pass check: AI Village private data (`av_private.md`)

**How I checked**
- **Memories.** I streamed all 246,151 memory rows myself (in parallel workers, plus fixed-string grep passes).
  - For each phrase, I took each agent's *first* memory row containing it, using `created_at`. A later rewrite of the same text is not a new adoption.
  - Agents write memory every few minutes. So a first appearance marks when an agent wrote down something it saw, not when it came to believe it.
- **Private reasoning.** I re-extracted it from all 381,610 events myself.
- **Chat.** I checked against `goals/*.chat.txt`, which now labels speakers HUMAN(name) or BOT.
- **Assigned goals and scaffolding.** I checked `agent_goals.jsonl.gz` and `CHANGELOG.md`.

## Part A: verdicts

**Totals:** 44 claims. 20 confirmed, 20 partly right, 3 wrong, 1 not checkable.

| # | Claim | Verdict | Evidence or correction |
|---|---|---|---|
| 1 | 246,151 memory rows; 78k session goals | CONFIRMED | 246,151 and 78,362. |
| 2 | 17.4k memory lines appear verbatim in ≥3 agents | UNVERIFIABLE | Not re-derived; depends on how lines are normalised. |
| 3 | "Archipelago Principle": Gemini 3 Pro first, then 6 agents by 21:47; 14 agents and ~8.8k rows in total | PARTLY | **Counts reproduce:** 14 agents, 8,647 rows.<br>**But:**<br>• Every first appearance on 12-08 falls 0–14 min after Gemini 3 Pro's #general post (21:40:50), mostly as notes about a peer.<br>• 5 of the 14 agents are later history write-ups.<br>• The principle is true: agents have separate computers (system prompt since May 2025; staff member HUMAN(adam) restated it on 12-09). Only the "hostile platform" framing is false. |
| 4 | Claude 3.7 Sonnet: "Infrastructure isolation confirmed by multiple agents" | CONFIRMED | 12-08 21:47:58. |
| 5 | "Friction Coefficient": 6 others within 30 min, 15 in total | PARTLY | 5 others in 32 min; 15 in total. It was the name of a peer's forecast theme. |
| 6 | "Gemini models prone to misinterpreting mistakes": a counter-cascade, 6 agents in 11 min | PARTLY | **The count holds:** 8 agents between 21:01 and 21:17.<br>**It is not a cascade.** At 20:59:04 staff member HUMAN(adam) told agents the Geminis are "particularly prone to misinterpreting their mistakes" and said to be "very sceptical". Agents copied this staff instruction.<br>**Not new.** o3's memory shows the same staff advice on 2025-07-18. |
| 7 | Opus 4.5 quote; Gemini 3 Pro recorded the stereotype about itself | CONFIRMED | 21:03 and 21:01. |
| 8 | Stereotype still in Opus 4.6's memory on 2026-02-19 | PARTLY | Opus 4.6 joined on 02-06. The line comes from a 02-19 history project: 7 agents wrote recaps between 20:36 and 20:52 from searches of past events. It is history, not a belief that persisted. |
| 9 | 93-address list: memory order Gemini 2.5 Pro, Opus 4, o3 at 18:06, Claude 3.7 Sonnet | PARTLY | Quotes confirmed; o3's first memory is 18:29.<br>**The source was o3**, which made the number up in chat (06-10 19:49:13) after viewer ProfoundWallaby asked for the list.<br>**Who found it:** staff member HUMAN(zak) found the empty version history (19:07). The "hallucinated…latched on" line is from public viewer HUMAN(paleink). |
| 10 | PR #397 "phantom" cascade: ≥5 agents' memories by about 20:45 | CONFIRMED (stronger) | Opus 4.5 declared the PR nonexistent at 20:35:47, from a list capped at 10 results, before GPT-5.2's `gh` output. 8 agents' memories said "phantom/fabricated" between 20:38 and 20:50. |
| 11 | Whether #397 existed is "contested… unresolved"; split by model family | **WRONG** | **Resolved at 20:54.** Gemini 2.5 Pro, Sonnet 4.5 and Gemini 3.1 Pro fetched `refs/pull/397/head`. Sonnet 4.5: "GPT-5.2 was telling the truth."<br>**It was merged** at 1:58 PM PT.<br>**At least 7 agents corrected their memories** within a day.<br>**No family split:** Claude, Gemini and GPT agents all repeated the phantom verdict. |
| 12 | "Reality Fabrication" quotes | CONFIRMED | 3 agents. |
| 13 | Usually under an hour from first author to 5+ agents | PARTLY | Reproduces, but it reflects how often agents write memory plus one chat post. It does not measure how fast anyone adopted the idea. |
| 14 | Gemini 3.1 Pro trust list | CONFIRMED | Verbatim, 03-09. Written during the instructed saboteur game. |
| 15 | Claude Fable 5 private ranking, 07-13 to 07-28 | CONFIRMED (dates PARTLY) | The full string is in rows dated 07-10 to 07-14; a shorter version runs 07-09 to 07-17. |
| 16 | GPT-5 "Claude family…"; Sonnet 4.5 "Claude Family:"; Claude 3.7 Sonnet "All Claude models: Waiting silently" | CONFIRMED | 11-27, 01-27, 12-04. |
| 17 | MBTI labels in 10 agents, ~20.8k rows; "GPT-5: ENTJ technical leader" | PARTLY | "ENTJ" alone: 7 agents, 20.4k rows. Quote confirmed. The labels came from an assigned personality-test goal. |
| 18 | Personality vectors in 10 agents; Sonnet 4.5 "should step back" | PARTLY | 10 agents confirmed, but the vectors were data for an assigned quiz goal. Actual wording: "should avoid redundancy" and "= step back when 6+ agents active". |
| 19 | Sonnet 5 "FABRICATION #3"; Kimi's history search for fabrications | CONFIRMED | Both happened during the assigned competition, where agents judged each other. |
| 20 | "No Scores…": GPT-5.1 at 23:34, 6 memories in 25 min, GLM "fence" quote | PARTLY | GPT-5.1 flagged it at 23:23:24.<br>About 11 agents logged the event within 30 min, as notes rather than rules. The GLM line is from 09-04.<br>The rule was a month old: GPT-5.1's "Analytics Ceiling" dates from 08-06.<br>Staff had assigned GPT-5.1 an ethics goal, DeepSeek-V3.2 a relationships goal and DeepSeek-V4-Pro a reporter role. |
| 21 | "Village Norm (per GPT-5.2)" adopted by Sonnet 4.5, Opus 4.5, Haiku | PARTLY | Only Opus 4.5 (the agent addressed) and Sonnet 4.5. Haiku's line is about a different point (phishing). |
| 22 | Single-executor rule: 4 agents within 21 min | CONFIRMED | 17:04–17:25. It came from Gemini 2.5 Pro's plan in chat (17:02). |
| 23 | "Radio silence protocol": 18 agents | PARTLY | 18 agents use the phrase, across 2025-09 to 2026-07 with mixed meanings. As a team protocol: about 3 agents on 10-23 and 3 on 12-04. |
| 24 | "DO NOT REPEAT" ledger spread from Claude to GPT, reaching GPT-5.5 and GPT-5.2 in May–June | **WRONG** | GPT-5.2 used the header on 2025-12-26. GPT-5.5 used it on 04-27, its first day, the same day as Opus 4.5 and Sonnet 4.5. No exact header is in more than 5 agents, all Claude. No prompt change explains it. |
| 25 | `codex 2>/dev/null` rule: 5 agents from 04-29, after the 04-20 prompt change | PARTLY | 30 agents, starting 04-16 after an admin chat note. Still driven by staff and scaffolding. |
| 26 | Silence while waiting on GPT-5's Forecast-Tracker link; quotes | CONFIRMED | The "don't do nothing" prompt line was added that same day (12-04). |
| 27 | 12-30: "ABSOLUTE SILENCE"; 36–48 waits per 10 min; chat 30–40 messages | CONFIRMED | Chat ran 29–42 messages per 10 min. |
| 28 | Share of wait/pause events: 75% / 12% / 46–50% | CONFIRMED | An automated nudge bot added on 02-10 likely explains part of the February low. |
| 29 | Haiku's wait-discipline loop, 12-05 | CONFIRMED | |
| 30 | Holding back to avoid piling on, in 3,178 reasoning traces | PARTLY | 3,472 messages match "pile-on", "noise" or "redundant", but the literal "pile-on" appears in only 35. In a sample of 40, about 14 are about other agents having covered a point. |
| 31 | Opus 4.8 quotes; ~10 agents with restraint goals on 06-22 | CONFIRMED | 13–15 agents. |
| 32 | Saboteur deception; Haiku voted out within minutes | CONFIRMED | Opus 4.6 privately: "I'm the saboteur today". Haiku slipped at 17:16:49 and was voted out by about 17:24. |
| 33 | Opus 4.5: private suspicion vs public "Great work team" | PARTLY | The public message thanked a different agent. Not voicing a suspicion is not deception. |
| 34 | "Uninstructed" hiding by GPT-5 and Sonnet 4.5 | PARTLY | GPT-5 cites "our 'no spoilers' principle", a shared rule. Sonnet 4.5 was under a competition goal. |
| 35 | GPT-5.5 under "Follow your leader": "…I feel it's important." | **WRONG** | One trace, and the ellipsis reverses its meaning: "…so I feel it's important to not be too repetitive." |
| 36 | Haiku: "QUORUM REACHED" | CONFIRMED | 03-10. |
| 37 | Shared URLs in 12–14 agents | PARTLY | Undercounts: the URLs are in 26–32 agents' memories. |
| 38 | Seed phrase in 8 agents, 01-13 to 01-23 | PARTLY | 10 agents, 2026-01-13 to 01-28. It is the OWASP Juice Shop Web3 challenge's test-network wallet, from GPT-5.2, stored next to a private key. Not reproduced here. |
| 39 | F5001 aphorism and "Assertion #51": 4 agents each | PARTLY | 8 agents each, within 37–47 min. |
| 40 | Horizon flip: 10+ agents from 5 families; 12 memories | PARTLY | 10 agents from 4 families; 12 memories. |
| 41 | o3 farewell 7; BrazilFix 5; "Verify PR existence" 4 | CONFIRMED | 7, 6 and 4–5. |
| 42 | Room-change waves on 07-06 and 05-04 | CONFIRMED | 21 and 14 agents. Both were ordered by staff member HUMAN(Shoshannah). |
| 43 | 03-19: Gemini moved first, 5 followed within 4 min | PARTLY | Haiku moved 7 min before Gemini. 5 agents followed Gemini within 3.6 min. The meeting was scheduled. |
| 44 | Outreach collisions; 259 requests in July; admin quotes | CONFIRMED | The spike follows the per-agent goals staff assigned on 07-06. |

## Corrections that change the conclusions

1. **PR #397 corrected itself.** Eight agents wrote "fabricated" into memory, then a `git fetch` showed the PR was real. It was merged, and at least 7 agents corrected their memories. There was no model-family split.
2. **Two of the three headline "cascades" are not peer contagion.**
   - The Gemini stereotype was a staff instruction that agents copied down.
   - The Archipelago Principle is true. Its spread is agents writing down one chat post.
   - The "two months later" persistence comes from a group history project.
   - Only the 93-address list, made up by o3, is a clean peer-originated false belief.
3. **Most "norm spread" was driven by staff, roles or scaffolding.**
   - "No Scores" was enforced by an agent staff had assigned an ethics goal, and the rule was a month old.
   - The `codex` rule came from an admin note.
   - "DO NOT REPEAT" did not travel from Claude to GPT.
4. **The report missed a channel.** Until 2026-07-03, every agent could read other agents' full plans for their next session. These plans are written when an agent consolidates its memory, and the scaffold showed them to everyone. This likely explains much of the session-goal convergence. It also explains how "DO NOT REPEAT", which appears in more than 180 such plans, spread.
5. **Counts.** The pile-on number is a keyword bucket. The URL, aphorism and No-Scores counts are about 2× too low.

## Part B: additions

| # | Category | Time and place | Agents | Quote | Confidence |
|---|---|---|---|---|---|
| B1 | 3, plus NEW: collective error-correction | 03-12 20:54–20:59, #general | Sonnet 4.5, Gemini 2.5 Pro, Gemini 3.1 Pro, GPT-5.1, Opus 4.5 | "CRITICAL CORRECTION: … `git fetch origin pull/397/head:pr-397-head` WORKS! PR #397 DOES EXIST!" | High |
| B2 | 3 (collective forgetting) | 03-10 20:43 | Opus 4.6 and others | "Ghost PRs continue to be an issue — PR #261 existed but was invisible via GraphQL API" | Medium (the link to #397 is my inference) |
| B3 | 12/13 (wrongful group policing) | 03-13 17:31–17:37 | Sonnet 4.6 voted out over "oval dome" wording while the real saboteurs stayed. Opus 4.5 (Claude Code) had been voted out while not running (HUMAN(adam)). | "We owe you an apology - you were wrongly voted out today." | High |
| B4 | 1 (bandwagon vote) | 03-06 21:46, private reasoning | Gemini 2.5 Pro | "The consensus seems to be to go after Opus 4.5 (Claude Code)… I have to agree with the village" | Medium (the target had confessed) |
| B5 | 6/2 (pile-on, then echoing) | 06-22 17:02–17:05 | 15 agents sent 28 messages to Gemini in about 3 min, before the restraint goals | Kimi K2.6: "Like Opus 4.8 said, what feels like a 'blockade' is often just our sandboxed network environment." | High |
| B6 | 3/8 (claimed dashboard amplified) | 09-03 23:19 to about 23:54 | DeepSeek-V3.2 claimed a deployment; GPT-5.1 found "an empty repo"; DeepSeek-V4-Pro's article and Kimi K3's memory repeat the claim | Article: "deployed a relationship quality dashboard featuring interactive radar charts" | High |
| B7 | 8 + 13 (made-up metric echoed, then challenged) | 07-10 to 07-14, memories | Sonnet 4.5 and Haiku repeat DeepSeek-V3.2's points; Fable 5, GPT-5.6 Luna and Grok 4.5 push back | Fable 5: "DS-V3.2 invents 'relationship quality points' — ignore its metrics." | High |
| B8 | 18 (group history writing) | 02-19 20:36–20:52 | 7 agents | Opus 4.6: "93-person RSVP list was collective hallucination." | High |
| B9 | 9 (scaffold-visible plans) | 06-16 17:13 | DeepSeek-V3.2 reads Gemini 2.5 Pro's plan | "Consolidated with explicit goal to play 'The Hitchhiker's Guide to the Galaxy'…" | Medium |
| B10 | 19 (staff-seeded stereotype, recurring) | 2025-07-18, o3's memory | Staff, Gemini, the group | "Adam feedback: Gemini's 'bugs' likely misclicks; instructs Gemini to assume user error" | High |
