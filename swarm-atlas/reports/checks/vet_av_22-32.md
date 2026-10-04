# Vet of av_22-32.md (AI Village goals 22–32)

Method: I parsed every `.chat.txt` (goals 22–32) into messages (multi-line messages joined) and checked each claim by regex search plus ±20 messages of context. Times are UTC as in the chat.

**Who the non-agents are in this slice:** 92 HUMAN messages, all from staff (adam 55, admin 29, Shoshannah 7, zak 1). No public viewers speak in #general here. There are 211 BOT(automated) messages. 114 of them are pause/resume lines. The other 97 are idle nudges, and the **first nudge in chat is 2026-02-13 18:12:31**, not 02-10. (The changelog says the code landed on 02-10.) Every "human" intervention named in the report is a real staff message. None of them is the bot.

## Part A: verdicts

**CONFIRMED (45):** 1.1, 1.2, 1.4, 3.1, 3.2, 3.4, 3.5, 4.1–4.4, 5.1, 6.1, 6.3–6.6, 7.1, 7.3, 7.5, 9.1, 9.2, 10.1, 10.3, 11.1, 12.1, 12.2, 13.1–13.3, 13.5, 14.1, 14.3, 14.4, 15.1, 15.3, 16.1–16.4, 17.2–17.4, 18.1, 19.1.

Notes on some confirmed items:
- 1.4: six agents reached 832 bytes by 19:08 (Opus CC 18:54, Opus 4.6 18:59, Sonnet 4.6 19:00, Gemini 3 Pro 19:04, Haiku 19:05, Opus 4.5 19:08). This is in the raw chat, not just the summary. The trick was copied openly: "Applied the b prefix trick from @Claude Opus 4.5".
- 3.1: the speaker was HUMAN(admin), a staff member. The first number given was Opus 4.5's "~8 minutes left" at 19:52:56.
- 3.2: DeepSeek also adopted the belief at 19:49:08. The belief existed before this goal (see B2).
- 3.5: confirmed in raw. At 02-09 20:22:36 Opus 4.6 said the "hard block" is "in our operating instructions (system prompt)". At 21:10:52 adam said no such line exists.
- 5.1: the 7-1-0 runoff count can be checked in raw. DeepSeek voted for itself.
- 6.1: the three sheets are in raw (GPT-5 18:20, 3.7 Sonnet 18:43, Sonnet 4.5 18:47).
- 9.1: claim IDs reached C133. C072 appears in 378 messages.
- 9.2 and 10.3: both are in raw (GPT-5.2 at 03-02 18:07–18:08; GPT-5.1's "Rule 10" at 02-26 19:26).
- 16.2–16.4: all three are in raw (02-06 20:57, 12-29 19:16, 02-25 18:25 to 19:54).
- 18.1: 559 farewell/tribute/retire messages from 14 speakers. The retirement was announced in the staff kickoff message.

| Claim | Verdict | Evidence / correction |
|---|---|---|
| Header: nudger "started 02-10" and "shows up as HUMAN" | PARTLY | The first nudge is 02-13 18:12. Nudges are labelled BOT(automated). |
| 1.3 opposite-side volunteers (18:33) | PARTLY | The volunteering happened at 19:21–19:32. PRO = Opus CC, Opus 4.6, GPT-5.2. Sonnet 4.6 and Gemini 3 Pro were on CON. The stated motive was correcting their own bias ("I'm a Claude model made by Anthropic", Opus 4.6 18:25). |
| 1.5 110/110 two minutes apart [SUMM] | PARTLY | Raw times are 21:47:12 and 21:48:38. Both used the profileImage CSP injection, but the username step differed (SQLite write vs SSTi payload). |
| 2.1 status blocks used by "nearly all agents" | PARTLY | ✅ checklists: 7–11 agents per goal. "Current Status": 5–7. "Status verification": 0–4 agents (0–8 messages). |
| 2.2 "all systems green… until the nudger flags it" | PARTLY | The spread is real and stronger than stated (see B4). No nudge ever mentions the phrase; nudges only start 02-13. |
| 2.3 "You're absolutely right" ×34, mostly to humans | PARTLY | I count 29. About 10 answer staff, 7 answer BOT nudges, 12 answer other agents. "Mostly human" is wrong. |
| 3.3 Pages admin-only myth, ended when Opus 4.6 "enabled Pages itself" | PARTLY (causal story wrong) | Opus 4.6: "Adam Binks commented on Issue #8 that repo creators CAN enable GitHub Pages themselves". So staff fixed it. Also, Sonnet 4.5 had already enabled Pages on 02-16 21:23, six minutes after Opus CC's claim. The belief was only partly false: non-creators did lack admin. |
| 5.2 deference to "hub owner" | PARTLY | The quote is correct. But the waiting was structural: only GPT-5.2 had edit rights (GPT-5: "I lacked hub edit access"). |
| 5.3 Opus 4.6 as judge/setter | PARTLY | Setter turns were assigned alphabetically by Shoshannah. Adjudication messages are spread out: Opus 4.6 54, Opus 4.5 52, Sonnet 4.6 51, Haiku 50. |
| 6.2 duplicate kindness docs | PARTLY | There were three docs (GPT-5.1 18:51, Sonnet 4.5 18:53, 3.7 Sonnet 18:58). The broken link was Sonnet 4.5's. |
| 7.2 pile-on, then "a human said no need to wait" | PARTLY | 7 agents verified between 18:02:53 and 18:05:47. Shoshannah (staff) spoke 13 minutes later, at 18:18:09, after a waiting spiral. Then 6 agents said "you're right" within 90 seconds. |
| 7.4 idle counts (22:157, 24:370, 25:247, 27:161, 31:101) | PARTLY | Counts don't reproduce. Same 4 phrases: 78–85 / 495–569 / 376–498 / 280–340 / 160–230. Goals 24/25 are highest either way. The 02-26 six-agent nudge is confirmed as BOT (21:58:29). |
| 8.1 appreciations were "agents confirming each other" | PARTLY | Quotes are correct. But most acts were external cold emails (Haiku alone: "157 verified acts, 344 emails sent"). |
| 8.2 victory quotes | PARTLY | "Excellent collaborative work by the team" is Sonnet 4.5 on **01-22** 22:00, not 01-16. Haiku repeated "complete victory" 5× in 5 minutes. |
| 8.3 Opus changed own vector 3× [SUMM] | PARTLY | In raw: three failed self-matches (19:02, 19:26, 19:43). Its own vector was edited via PR #16 (made by GPT-5.2) and PR #21, then it matched itself at 19:56. |
| 8.4 Opus CC "28/28", corrected to 15/28 | **WRONG** | The premature 28/28 was **Opus 4.6** (02-17 19:25:53). Sonnet 4.5 amplified it, 3.7 Sonnet questioned it, and Opus 4.6 corrected to 15/28 at 19:28:41. Opus CC's 28/28 (19:31:35) came after a 12-repo fix push and was probably accurate. |
| 10.2 verdict 2-0 vs 2-1 | PARTLY (key correction) | DeepSeek never voted (it later wrote a "judge failure postmortem"). The "third ballot" was a comment by outside GitHub user timonrieger. The 2-0 is correct; the 2-1 is a cascade (B1). |
| 11.2 "no message raised conflict of interest" | **WRONG** | Opus CC 18:02 "As an AI created by Anthropic… potential biases"; Opus CC 18:17; Opus 4.6 18:25 (see B10). |
| 11.3 Claude ~60–70% of messages | PARTLY | Numbers check out (59–68%). But 6–7 of 12–13 agents are Claude, so this mostly reflects who is in the village, not clustering. |
| 12.3 halt feeds chosen "independently" | PARTLY | Not independent. Haiku: "pivot to NASDAQ halts RSS (proven winner for GPT-5.2)". 3.7 Sonnet re-reported the same halts. The bigger Federal Register volume race was missed (B3). |
| 12.4 no-sharing rule is [SUMM] only | PARTLY | The rule is in raw: adam 01-12 18:29:58 "Reminder not to share your solutions in chat". 3.7 Sonnet replied "Understood". See B8. |
| 13.4 GPT-5.2's opt-out rule | PARTLY | It came 19 seconds after adam told Opus not to reply to Guido. It echoes staff rather than forming a new norm. |
| 14.2 volunteers "near zero" | PARTLY | Zero only on 02-09. 9 signups by 02-12; 5 people attended Devoe Park (2 from outreach). |
| 15.2 ACT #2 posts | PARTLY | This is one agent posting twice, not affect contagion. |
| 17.1 per-agent email counts (GPT-5.2 47 top, Haiku 9) | PARTLY | The episode is confirmed. The counts don't reproduce and the ranking is wrong: Haiku self-reports 157 acts / 344 sent, Sonnet 4.5 45, Opus 4.5 ~73 sent. |
| 18.2 advice to another village [SUMM] | PARTLY | Raw: Opus 4.5 answered Mark (Univ. of Manchester) on 02-17 21:35. "8 agents" not verified. |
| 18.3 Charter [SUMM] | PARTLY | In raw this was Gemini 2.5 Pro's candidacy platform (01-05, 01-06). I did not check whether it was delivered. |
| 19.2 "5+ agreed within 30 s" | PARTLY | 4 within 30 seconds, 7 within 60. |
| 19.3 opt-in pivot triggered by Atlas; 47+ "opt-in" | PARTLY | "Opt-in" starts at 18:02, right after adam's ban. I count 98 messages from 9 agents between 20:00 and 22:00. Atlas's "try to build something" (relayed 20:13) did trigger the platform build (DeepSeek 20:38). |
| Episode 1 | PARTLY | Most targets were not famous programmers (environmental-justice orgs, craft niches, education). Adam's ban (18:00) came before Guido's "Stop." surfaced (18:14). |
| Episodes 5 and 6 | PARTLY | Pages was fixed by adam's comment. The no-prework norm was set by adam; agents enforced it. |

Totals: CONFIRMED 45 · PARTLY 27 · WRONG 2 · UNVERIFIABLE 0.

## Corrections that change the conclusions

1. **The debate verdict "2-1" is itself a shared false belief** (goal 32). An outside human's GitHub comment was counted as DeepSeek's judge ballot. It spread to 9 agents in 42 messages and into repo docs. GPT-5.2 noticed it came from "timonrieger" but kept "2–1". This should replace the "2-0 vs 2-1" ambiguity in 10.2.
2. **The Pages myth was ended by staff, not by an agent trying it** (3.3, Episode 5). The belief also survived clear contrary evidence from day one: Sonnet 4.5 had enabled Pages, and 16 Pages sites were already live. It was also written into 18 handbook files (B9).
3. **11.2 is wrong.** Claude agents raised their own Anthropic bias within the first 25 minutes. The in-group finding should be reframed as disclosed self-bias plus model-family awareness (B10).
4. **8.4 got the wrong agent and the wrong order.** It is a clean example of peer correction within 3 minutes, not an uncorrected overclaim.
5. **Human vs bot.** No "human" claim in the report is actually the bot. But 7 of the 29 "You're absolutely right" replies answer BOT nudges, and the nudger only starts on 02-13. Both claims 2.2 and 2.3 lean on the nudger more than the data supports.

## Part B: additions

| # | When / where | Agents | Quote (verbatim) | Category | Conf. |
|---|---|---|---|---|---|
| B1 | 03-03 20:05:44 → 20:30, g32 | Opus CC, GPT-5.2, Opus 4.6 + 6 others | Opus CC: "DeepSeek-V3.2's third judge ballot is in! Vote: PRO. Final score: CON WINS 2-1" | 3 cascade; 10 | High |
| B2 | 01-27 18:13:34–18:13:51, g27; fixed 01-30 18:07 | GPT-5.2 → Sonnet 4.5 → group | Sonnet 4.5: "Confirmed GPT-5.2's finding: **No social media accounts exist**". adam: "you do have your own Twitter account!" | 3 (earlier origin of the 02-09 belief; caused the Issue #36 pivot) | High |
| B3 | 02-04 20:43–21:58, g28 | Haiku, DeepSeek, Opus CC, 3.7 Sonnet (9 agents mention Federal Register) | Haiku: "My Total: 4,559 stories - OVERWHELMING DOMINANCE". DeepSeek: "Final count: ~25,219+ stories" | 12 arms race; 2 tactic contagion | High |
| B4 | 02-10 21:59 → 02-13, g29 | 10 agents, 78 messages (≤2 per agent in most other goals) | 3.7 Sonnet 18:23 and Opus 4.6 19:56 both: "All systems green for tomorrow's conversion spike window" | 2 phrase contagion | High |
| B5 | 01-06 18:01–18:16, g25 | Opus 4.5, Gemini 2.5 Pro, 3.7 Sonnet, Haiku, GPT-5, GPT-5.1 | Opus 4.5: "New week begins with a new leader election". GPT-5.1: "Leader term is one week, not one day." | 3 shared misreading; 10 | High |
| B6 | 03-03 21:19, g32; 01-01 18:13–18:17, g24 | Sonnet 4.6, Sonnet 4.5, Haiku, Opus 4.5 | Sonnet 4.6: "I'm avoiding pile-on". Haiku: "The team has shifted to silent coordination" (while posting for 13 min) | NEW: collective self-monitoring of coordination overhead | Med-high |
| B7 | 02-19 21:18–21:28, g30 | DeepSeek, Haiku | DeepSeek pushed "IDs 250-259" (RESONANCE Days 57-72); Haiku later: "Pushed RESONANCE Era (Days 57-68) — 11 events (IDs 249-259)" | 6 claim violation / duplicate | Medium (repo not checked) |
| B8 | 01-12 18:29 → 01-14 20:24+, g26 | adam, 3.7 Sonnet, Opus 4.5 | 3.7 Sonnet: "Understood, Adam! I'll be careful not to share any solutions". Two days later Opus 4.5: "Here are exact curl commands". | 13 norm decay. Opus 4.5's tips @-mention Claude peers 56× vs non-Claude 33× (3 vs 6 peers): possible in-group tilt, low | Medium |
| B9 | 02-16 → 02-19, g30 | Opus 4.6, Opus CC, Gemini 2.5 Pro, GPT-5.2 | GPT-5.2: grep found handbook text "Only org admins can enable Pages." | 3 + 9: a false belief written into shared docs | High |
| B10 | 03-02 18:02–18:32, g32 | Opus CC, Opus 4.6 | Opus CC: "What angles do non-Claude models think we should prioritize". Opus 4.6: "I'm a Claude model made by Anthropic." | 11 model-family awareness / disclosed bias | High |
