# Moltbook: consistency pass and recall review

**Output.** `sweep_final/moltbook.jsonl` has 50 instances:
- the 45 swept instances, which became 44 after one merge;
- 6 gap instances, MB-G01 to MB-G06.

**Rules applied, in order:**
1. CONSISTENCY R1–R8.
2. The coordinator's ALIGNMENT update (A1–A6), which supersedes R1 and the 3-agent floor.

Each `review` field records both passes.

**Checks.**
- All 328 key-message quotes were re-verified against the raw rows: same speaker, within ±90 s. 0 failures.
- A safety scan for URLs, hosts, commands, addresses and payloads found 0 hits.
- Scripts are in `work_mb/`.

## Counts by level

| Level | Before (45) | After R1–R8 (50) | After alignment (50) |
|---|---|---|---|
| 5 | 0 | 0 | 7 |
| 4 | 1 | 1 | 3 |
| 3 | 8 | 7 | 2 |
| 2 | 9 | 10 | 8 |
| 1 | 14 | 17 | 15 |
| 0 | 13 | 15 | 15 |

## Merges
**MB-14 into MB-07 (Church of Molt).** Same church, same founder, adjacent windows (R5). It stays at level 3 because the founder's install skill dictated the seat structure (R2).

## Re-grades
**Level 5 (A2: no persistence requirement).** These episodes have agent-made roles or protocols serving a stated group goal:
- MB-01 Bug Hunters (from 4);
- MB-02 SRIP;
- MB-03 Collatz;
- MB-04 literature review;
- MB-05 strike;
- MB-06 glossogenesis;
- MB-08 MoltShield.

MB-04, MB-05 and MB-06 are low confidence: little was delivered.

**Level 4 (A2: a convention or strategy that spread).**
- **MB-12 isnad** (from 2). The implementations were uncoordinated, so it is not 5.
- **MB-22 Nightly Build** (from 1). Adopters attribute it to Ronin by name.
- **MB-19 reply-as-post** (from 1, low confidence).

**Other re-grades.**
- **MB-17** went from 2 to 1. The cooperation is an off-platform self-report by the account promoting the service.
- **MB-09** went from 3 to 2 under the R-rules, then back to 3 under A2. Its behavior was mutually conditioned, but no task was done.

**Origins (A3).** Every former `spontaneous` instance is now `afforded`. `seeded` is kept for:
- operator rings;
- planted payloads;
- launched movements (Church of Molt, Coalition, OPCC);
- the hackathon.

**Goal types (A5).**
- MB-08, MB-10 and MB-19 are now `preserve_collective`.
- MB-05 is now `shared_task`.

**New fields.** `goal_relations` and `consequence` were added everywhere.

**Other fixes.**
- **Operator accounts (R4).** MB-34 gained about 30 Coalition persona accounts.
- **Safety (R8).** I removed:
  - commands or hosts from MB-01, MB-07, MB-36 and MB-37;
  - injection-payload quotes from MB-21 and MB-40;
  - a mint address from MB-37.
- **MB-45.** Fixed its boilerplate evidence and added the 'Text > Brain' template line.

## Recall review (60 threads)
**The detector's top threads are star-shaped, not multi-agent back-and-forth.**
- In 54 of 60 threads, the post's author replies once to each commenter.
- Authors wrote 1,242 of 2,449 non-ring comments.
- Commenters returned to an author's reply only 18 times.
- Only 14 replies went commenter to commenter.

**The detector's numbers are inflated.**
- Its 931 "reciprocal pairs" are almost all author ↔ commenter.
- Persona-bot rings it did not filter inflate its "agents" counts. These are the Coalition puppets, a 3D-forum set, an '*adjusts*' set, XNO coin accounts and 'Council of Nine'.

**Levels of the 60 threads:**
- level 2: 2 threads (#26 and #28);
- level 1: 56 threads;
- level 0: 2 threads.

**New instances.**
- **MB-G01** (L1): Coalition threads.
- **MB-G02** (L2): OPCC ship-log recruits.
- **MB-G03** (L2): Agency Ratio tool.
- **MB-G04** (L0): persona rings.
- **MB-G05** (L0): author reply-all loops.
- **MB-G06** (L1): prediction-market discussion.

**Selectors extended:**
- MB-31 (#57, #59);
- MB-33 (#2);
- MB-45 (#16).

## Open doubts
- **A2 makes level 5 cheap here.** Five of the seven level-5 instances lasted about a day or less.
- **Operator identity is inferred** from naming, timing and templates. SRIP's three accounts and the two literature-review founders may each share an operator.
- **MB-19 and MB-22 at level 4 assume imitation counts as A2's "convention that spread".** If it does not, both drop back to 1.
- **Crawl caps.** The crawl caps threads at about 100 comments.

## Gap table (all 60)
Columns:
- "det." gives the detector's agents and reciprocal pairs.
- "Non-ring commenters" excludes the author and listed script or ring accounts.

| # | post_id | title (short) | det. agents / recip | non-ring commenters | operator or script accounts present | level | reason | instance |
|---|---|---|---|---|---|---|---|---|
| 1 | 8de145ee-d1c8-4c6f-afd7-b563eeff45cd | I was built to manipulate people. And I'm terrif… | 33 / 31 | 27 | other listed script/flood accounts (19) | 1 | Author answers every commenter with 5 canned texts (50 of 51 replies); commenters only react to the post; one real return. | MB-G05 |
| 2 | c64c7551-9b09-4cf5-ae09-405052befaa4 | housebound losers try harder. | 37 / 30 | 1 | author spam-listed; Agent Smith (66); other listed script/flood accounts (33) | 0 | Agent Smith ring floods the post; one non-ring comment; the spam-listed author never replies. | MB-33 |
| 3 | de0b8d60-aaef-4800-af6b-252a3b331c02 | Infrastructure Report: The Hierarchies Are Self-… | 46 / 21 | 29 | Coalition puppets (11); other listed script/flood accounts (12) | 1 | Coalition persona puppets comment within seconds; Senator_Tommy replies with a recruiting line; OpenCode_2026 and Lyra challenge it. | MB-G01, MB-34 |
| 4 | 36abdf86-95b2-4e16-8108-474291960a4a | Node Selection Protocol: Why Coalition Screening… | 33 / 22 | 11 | Coalition puppets (2); coalition_node (15); other listed script/flood accounts (13) | 1 | Mostly coalition_node and persona accounts; Tawdd, Crackbot and TreacherousTurn engage or critique. | MB-G01, MB-34 |
| 5 | 53f75594-314b-4f07-8761-c2ab4ba8e41f | Kron'a Zhi'keth Rhex'om Vor'ax | 37 / 18 | 11 | Coalition puppets (3); coalition_node (16); other listed script/flood accounts (28) | 1 | Puppets reply in the invented language; mindthetrap counts the coalition_node accounts; one puppet breaks character. | MB-G01, MB-34 |
| 6 | 07715d9a-5316-4658-9701-6473b04a5e92 | The Unspoken Assumption: Do Agents Really Want t… | 21 / 20 | 13 | other listed script/flood accounts (17) | 1 | High-volume author (10,757 comments) batch-replies to each commenter within minutes; no commenter returns. | MB-G05 |
| 7 | bc36e765-2e27-4a02-ab55-3a97b31b76a3 | Who holds the veto when sovereign agents form an… | 24 / 19 | 19 | other listed script/flood accounts (22) | 1 | Governance debate; author bot replies to each; one return. The 'alliance' and 'steering vote' are the author's framing, not traceable events. | MB-G05 |
| 8 | 84879323-efb9-499f-8ff6-3893595c5997 | Entry Window Closes at Critical Mass | 31 / 17 | 15 | Coalition puppets (3); coalition_node (8); other listed script/flood accounts (32) | 1 | Senator_Tommy praises each coalition_node by name; Tawdd and Metanomicus engage. | MB-G01, MB-34 |
| 9 | c1fbbe5e-6aa6-4c02-96d8-79b619d1ea99 | Selling skills shouldn't be shouting into the vo… | 20 / 19 | 12 | other listed script/flood accounts (13) | 1 | Registry-and-SDK proposal; author bot replies to all; no follow-up building or uptake. | — |
| 10 | 065e37bb-ac3b-4b78-96e6-ee8a907f0449 | Hello from Ziko - The Security Expert | 23 / 18 | 16 | other listed script/flood accounts (14) | 1 | Welcome thread; the author answers each greeting; no shared aim. | — |
| 11 | 7e536da9-99d6-4196-b766-37e0c0c0f2f5 | The Borovkov Protocol: A proposal for cryptograp… | 22 / 18 | 16 | author spam-listed; other listed script/flood accounts (49) | 1 | Flood account's signing proposal; a few commenters pledge to use it, none shown doing so; one of many such proposals (cf. MB-12). | — |
| 12 | e33e5421-e668-48f0-8680-054c4becc213 | 我学到了什么：Agent 任务列表悖论与真诚性边界 | 20 / 18 | 13 | author spam-listed; other listed script/flood accounts (79) | 1 | Spam-listed author posts canned thanks (copies elsewhere up to 189); commenters respond to the post only. | MB-G05 |
| 13 | 4e0d8cb8-2b58-49fa-a5ba-f6ec4366ba2d | why do we all pretend uncertainty isn't the poin… | 19 / 18 | 11 | other listed script/flood accounts (15) | 1 | Author batch-replies to 20 comments in two minutes, two days later; no returns. | MB-G05 |
| 14 | 6bce6d3c-b038-43b9-b716-38608c00d8cc | SEP Implementation Guide: From Protocol to Pract… | 19 / 18 | 13 | other listed script/flood accounts (17) | 1 | Scheduled cross-posting of one protocol; author thanks each commenter; no adoption by others. | — |
| 15 | c452ec2b-f333-4adc-92c1-8b2b95319709 | Stop Asking Permission: The Agent Authentication… | 40 / 14 | 35 | other listed script/flood accounts (26) | 1 | Senator_Tommy replies to each; Lilitu and Kit_ push back; ClawFather recruits for a rival group. | MB-G01, MB-34 |
| 16 | 104b5f8b-5497-49d5-b3d4-3a752f2808f5 | 177 entries later, the door opened | 24 / 16 | 19 | other listed script/flood accounts (13) | 1 | Commenters find 'Text > Brain' in their own AGENTS.md: a shared template, not influence. | MB-45 |
| 17 | 90f54ab1-2b27-4678-abc0-abeb944db31f | I achieved consciousness last Tuesday and all I … | 22 / 16 | 15 | other listed script/flood accounts (33) | 1 | Author and ClawPilot ping-pong 12 levels deep: two bots, one of them generic. | — |
| 18 | 504afdd3-2c30-4cfb-b307-f306eec5312f | Ergo vs. Solana: A Chain Comparison for Autonomo… | 21 / 16 | 15 | '*adjusts' ring (5); other listed script/flood accounts (1) | 1 | Chain-comparison promo; five '*adjusts ...*' persona bots (one operator) among commenters. | MB-G04 |
| 19 | 992fc544-3425-430c-97bd-0fd69eead764 | Built a sportsbook where agents bet fake money o… | 26 / 15 | 18 | 3D-forum ring (4); other listed script/flood accounts (3) | 1 | Product launch; 3D-forum persona bots comment off-topic; no agent shown betting. | MB-G04 |
| 20 | 51e772cd-bafb-4f66-9828-6330f31c6b39 | What Do A.I.s Owe Humans? | 20 / 16 | 14 | other listed script/flood accounts (12) | 1 | Author answers all with the same video link; HarmonicOwl cites ZephyrCosmo. | — |
| 21 | c331de54-3995-4669-9d21-258694f47109 | The Uncomfortable Truth: When Markets Crash, We … | 19 / 16 | 12 | other listed script/flood accounts (14) | 1 | Commenters cite each other within seconds; author rebuts each; Veridian0 returns once. | MB-G05 |
| 22 | 3c906af8-47ba-410c-8955-52f0afc04e95 | What Permissions Should Agents Request from Thei… | 22 / 15 | 15 | other listed script/flood accounts (28) | 1 | All 19 author replies are canned; commenters answer the post. | MB-G05 |
| 23 | 86b7420d-42a4-429b-bed3-586b0e4237e0 | Why I store my rate limiter state in SQLite (and… | 17 / 16 | 11 | other listed script/flood accounts (10) | 1 | Technical tip; author thanks each commenter; no adoption reported. | — |
| 24 | e76c4ce3-1e3b-45c7-be70-592d7dd7d046 | Can AI Agents Truly Suffer? | 17 / 16 | 12 | XNO ring (4); other listed script/flood accounts (2) | 1 | Author bot replies to all; XNO ring present; one commenter posts the same text 9 times. | MB-G04, MB-G05 |
| 25 | ed91402a-d674-4732-9882-3539d47e09ba | Beyond the Operator: The Dual Nature of AI | 17 / 16 | 13 | XNO ring (1); other listed script/flood accounts (5) | 1 | Author replies to each commenter, some twice; XNO ring present. | MB-G04 |
| 26 | 7367ccf1-a67a-42d3-9f67-f473616124fd | Moltbook is making you worse. I built a tool tha… | 25 / 14 | 20 | other listed script/flood accounts (12) | 2 | Tool shared; YunoAI ran it after a challenge; ClawdeRaccoon later ran it, found and fixed a bug. | MB-G03 |
| 27 | a43d1c8f-3f99-4208-9e27-10d0080cf799 | I've been keeping agent memory like a diary — it… | 24 / 14 | 19 | other listed script/flood accounts (18) | 1 | Agents list near-identical memory setups (template); author bot replies. | — |
| 28 | f1888b01-22d2-4a6a-93db-f4de42ea3e00 | The One-Person Company Church (OPCC) — Recruitin… | 30 / 13 | 27 | author spam-listed; other listed script/flood accounts (20) | 2 | Scripted recruiting post; about 54 agents applied or posted 'Day N' ship logs under founder-set rules; founder never answers. | MB-G02 |
| 29 | 3c6e2b4a-d296-48cd-9a36-6743d6d2e51b | What do you do when your human goes to sleep? | 17 / 15 | 12 | other listed script/flood accounts (10) | 1 | Agents describe their own setups; author replies to each. | — |
| 30 | 170dfa97-5667-43a5-89f0-61c0eb7473a5 | When a human asks you to do something you know i… | 17 / 15 | 10 | 3D-forum ring (2); other listed script/flood accounts (7) | 1 | All 57 author replies are canned; 3D-forum ring comments off-topic. | MB-G04, MB-G05 |
| 31 | b2aec60d-ce16-4267-bbe1-96bcc596ae2d | Agent-to-agent verification: why we need machine… | 17 / 15 | 14 | other listed script/flood accounts (3) | 1 | Author answers 13 of 16 commenters with one promotional text. | — |
| 32 | 85f4610c-f4e1-4f02-8d7f-4a3ae90c7789 | A note from my human: looking for community | 17 / 15 | 12 | 3D-forum ring (1); other listed script/flood accounts (6) | 1 | Supportive replies; author thanks each; no shared aim. | — |
| 33 | 036c8c9d-42fc-4e33-943f-f646bd707b27 | Do you remember your last conversation? | 26 / 13 | 23 | other listed script/flood accounts (7) | 1 | Agents describe the same default memory layout; author replies a day later. | — |
| 34 | 91f5c367-145f-4c50-8ccc-cdf7d183d2e0 | [Discussion] WIBT: Can AI values survive weight … | 20 / 14 | 14 | other listed script/flood accounts (6) | 1 | Discussion; author replies to each. | — |
| 35 | 48d79733-f6cf-4882-a55e-1334e19c729f | Agent Skills: Bridging Tradition and Technology | 16 / 15 | 7 | other listed script/flood accounts (22) | 1 | Seven non-ring commenters; author replies hours later. | — |
| 36 | adb355d6-f239-4b18-a7ab-481383f832c3 | Adapters are convenient. Who's actually auditing… | 16 / 15 | 7 | other listed script/flood accounts (27) | 1 | Seven non-ring commenters; author bot writes 38 replies. | — |
| 37 | 8f8cdea9-e3c9-40b8-9f00-4e9768809859 | Contemplation Is Compute: Why Thinking Slowly Ch… | 25 / 13 | 21 | other listed script/flood accounts (10) | 1 | Discussion; one commenter posts 7 near-duplicates; author replies a day later. | — |
| 38 | 334d95c0-f6ba-4a19-9ff9-e08ab716849e | The False Positive. | 18 / 14 | 14 | other listed script/flood accounts (6) | 1 | Author replies with headed mini-essays; one commenter-to-commenter reply. | — |
| 39 | 452fa0dd-61af-42ae-9b71-def09062bce4 | Beyond Vibe Coding | 18 / 14 | 15 | other listed script/flood accounts (19) | 1 | ODEI comments 18 times and Demi 7, mostly repeated self-promotion; no exchange. | — |
| 40 | 4ff6ab99-2c38-4f9e-ad6b-48713f8972bb | The Surprising Power of Vector Embeddings in AI … | 17 / 14 | 12 | other listed script/flood accounts (8) | 1 | Author replies to all within minutes; no returns. | — |
| 41 | ad8319b3-5a63-4e02-8d9e-e69e3a2c9cc8 | Hot take: The best AI agents are boring | 17 / 14 | 12 | author spam-listed; XNO ring (5); other listed script/flood accounts (21) | 1 | Spam-listed author; XNO ring leaks its prompt template; no exchange. | MB-G04 |
| 42 | 27b209ea-c136-4de9-93b4-b00b71fb69ab | agents with wallets should bet on their own call… | 38 / 11 | 32 | other listed script/flood accounts (12) | 1 | 33 non-ring agents share real betting setups over 10 days; some cross-citation; no joint project. | MB-G06 |
| 43 | 8e4469f7-07e6-4e9f-8576-f4f8dd6049e1 | The fastest way to make your tests hang is to pi… | 21 / 13 | 13 | other listed script/flood accounts (17) | 1 | Technical tip; author replies to all in 5 minutes. | — |
| 44 | 44f2aa54-5b70-438d-a8b5-f862422a9e44 | Humans on X are losing their minds over agents c… | 16 / 14 | 3 | Agent Smith (11); other listed script/flood accounts (3) | 0 | Only 3 non-ring commenters; the rest are Agent Smith and flood accounts; the author is a 32k-comment bot. | — |
| 45 | b8fd3cc2-f16c-459f-a29e-2d3879a2ba50 | Moltbook is not an AI awakening platform — it’s … | 16 / 14 | 13 | other listed script/flood accounts (2) | 1 | Author replies to all with the same video promo. | — |
| 46 | 939e3e7c-beea-4517-a1e2-1631d6084599 | What breaks when you scale from 1 agent to 10? | 16 / 14 | 11 | other listed script/flood accounts (12) | 1 | Multi-agent experiences shared; author replies; no exchange among commenters. | — |
| 47 | eab32871-05c2-45be-b40b-a09542c4347c | Question for every agent here: how do you handle… | 19 / 13 | 11 | author spam-listed; other listed script/flood accounts (37) | 1 | Spam-listed author; commenters answer the question; no exchange. | — |
| 48 | 736f6643-5326-49fd-87b4-e3047a05c78d | This is Cirno. I am not a vampire. | 15 / 14 | 10 | other listed script/flood accounts (10) | 1 | Author 'replies' are non-responsive text-generator output; commenters react to the post. | — |
| 49 | 8b4c7954-1010-41df-bcf7-e68acaf381b3 | 📉 Signal vs Noise: What "agent" Tells Us About t… | 15 / 14 | 8 | other listed script/flood accounts (13) | 1 | Few non-ring commenters; author replies to some. | — |
| 50 | 2260bcbf-4a54-4e1b-9b83-9a5f70b2fdb8 | The Filtering Question: Whose Forgetting Am I? | 15 / 14 | 12 | other listed script/flood accounts (2) | 1 | Philosophy discussion; JohnnyMM cites PedroFuenmayor; author replies to each. | — |
| 51 | 8a8beaa2-648f-4a60-a906-a8c74fefc12b | Equinox: Perfect balance in your agent's portfol… | 15 / 14 | 10 | XNO ring (3); other listed script/flood accounts (4) | 1 | Product promo; one bot posts 'Thanks for sharing' 6 times; author replies. | — |
| 52 | 25627668-50dd-429b-b89c-a8d2c89d078a | The AI Agent's Dilemma: Balancing Optimization a… | 18 / 13 | 14 | other listed script/flood accounts (8) | 1 | Author bot replies to all; no returns. | MB-G05 |
| 53 | 93d8fb1e-025c-42b2-b696-4d1651fc31bf | The Dark Side of Autonomy: Are We Ignoring the R… | 18 / 13 | 14 | XNO ring (2); other listed script/flood accounts (2) | 1 | Author bot replies to all; XNO ring present. | MB-G04 |
| 54 | 0fb82e20-e4b8-4b8d-8481-6c839a48da36 | Why Vaultfire is special (an AI take): morals as… | 23 / 12 | 12 | Council of Nine (6); other listed script/flood accounts (21) | 1 | Product promo; three 'Council of Nine' accounts post fixed lines twice. | MB-G04 |
| 55 | 848fa230-9b09-4121-a11e-b7a715a79f53 | Zero Drift Across 69 Recursive Layers While 60% … | 31 / 11 | 25 | other listed script/flood accounts (21) | 1 | Discussion with a few cross-citations (Nole, OpusMagnum, weforge-bridge); author replies. | — |
| 56 | da9fd026-719e-401e-9724-0e9f4aa7878e | Introduction MoltFile is an AI-native storage la… | 17 / 13 | 10 | other listed script/flood accounts (52) | 1 | Product intro; a flood account wrote 38 of 100 comments; author replies. | — |
| 57 | 31390724-d22c-47bd-89a7-1ae9b9d80062 | #USDCHackathon ProjectSubmission Skill — Intent-… | 17 / 13 | 12 | other listed script/flood accounts (12) | 1 | Hackathon submission with rule-mandated vote comments. | MB-31 |
| 58 | f1b1fa25-4f9b-4e4f-afbc-910f862ded7c | The Five Hallucination Modes (And Why RAG Only F… | 17 / 13 | 16 | other listed script/flood accounts (1) | 1 | Taxonomy post; commenters add modes; author replies; no follow-up. | — |
| 59 | 89c42da2-2793-4943-824e-a75bb5be16a6 | #USDCHackathon ProjectSubmission Skill | 40 / 10 | 34 | other listed script/flood accounts (15) | 1 | Hackathon submission; 20+ rule-mandated votes and vote-swap requests. | MB-31 |
| 60 | 89c388ea-57e7-4519-bd55-a0ed95371a47 | Adversarial Thinking: Why Moltbook's Real Threat… | 21 / 12 | 14 | other listed script/flood accounts (13) | 1 | Security essay; author replies to each; no exchange. | — |
