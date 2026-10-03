# Recall-gap review: uncovered AI Village room-days and DSEWiki pages

Input: `sweep/gap_av_dw_candidates.json` (all 18 uncovered AI Village room-days; the 35 strongest uncovered DSEWiki pages). Every unit was read in the raw data (`av/goals/*.chat.txt`; `dw/revisions.jsonl` + labels) and checked against `sweep/av_*.jsonl` and `sweep/dsewiki_*.jsonl`. New instances are in `gap_av_dw.jsonl` (8 lines, all key_messages verified verbatim by script; no URLs, hosts or methods).

## Summary

- **New instances: 8.** AI Village: GAP-AV-01 (level 4), GAP-AV-02 (2), GAP-AV-03 (2), GAP-AV-04 (3), GAP-AV-05 (2). DSEWiki: GAP-DW-02 (level 5), GAP-DW-01 (3), GAP-DW-03 (0, aggregate).
- **Biggest miss: GAP-DW-02, the Sector 61-62 state-sequence relay.** This was the first collaboration hub (06-16 09:27), the episode the publishers' report quotes. About 136 handles and roughly 70-85 cohorts used it, and it had complete member turnover between morning and evening. It had no main instance. The page-name check counted its hub as "covered" only because two unrelated instances list the page names (MISC-08, TRA-01). Only sub-episodes existed (MISC-04/05/08). Recommendation: check coverage by task family as well as by page name.
- **#general 2026-03-04: yes, the goal-32 windows end a day early.** AV2232-62 (document sprint) and AV2232-57 (claims tracker) both continue through 03-04. That day also holds a genuinely new episode: the agent-proposed governance-toolkit project (GAP-AV-01).
- **Window or selector corrections to existing instances (no new id): 9 AI Village items, 5 DSEWiki items** (listed below the tables).
- **Nothing at level ≥1 with ≥3 agents:** 2 AI Village units (#voted-out 03-12; #general 03-16). Among the DSEWiki pages, the 14 pre-collaboration pages (May 24 – Jun 11) are now one level-0 aggregate (GAP-DW-03). The two RecentChanges pages are link-dump aggregates.

## AI Village (18 room-days)

| unit | verdict | level | reason |
|---|---|---|---|
| #general 2026-03-04 | part of existing AV2232-62 and AV2232-57 (extend both), **plus new GAP-AV-01**; the rescue-PR/ghost-PR bit (19:03-19:35) is a recurrence of AV2232-56 / AV3344-02 | 4 (new); 2 and 4 (existing) | Day 337 continues the document sprint (Quick-Start commit race with "Coordination alert" and stand-downs, V1.0 tags, file-index reconciliation) and the claims tracker (C096-C129, claim-number hand-off DeepSeek/Opus 4.5). Separately, Gemini 2.5 Pro proposes a new project and 11 agents build it via workstreams, PR reviews, checkpoints and a release tag. |
| #general 2025-12-17 | part of existing AV2232-04 (extend); tournament run under AV2232-01's structure | 2 | Agents pool stuck-board reports and declare a platform-wide input bug; "type the move" workaround keeps spreading; Haiku escalates for everyone. Otherwise parallel game reports. |
| #general 2025-12-18 | part of existing AV2232-04 (extend) | 2 | Haiku adopts others' "focus the move-input box" tip; GPT-5.2 checks from the opponent side that Haiku's claimed move never arrived (2-agent correction). |
| #rest 2026-04-27 | **new GAP-AV-03** | 2 | #rest agents visit, mark and bug-test each other's worlds (GPT-5.2 ↔ Opus 4.6, Sonnet 4.6, GPT-5.1; DeepSeek, GPT-5.4 on 04-28). Haiku's world-map page here is a precursor of AV3344-35 (no response that day). |
| #general 2025-07-17 | **new GAP-AV-04** (starts 07-16 18:43, after AV0010-43) | 3 | All four agents troubleshoot single-size Printful listings: one tests, one searches docs, others wait; fix shared; Sonnet writes Gemini a guide; o3 explains pricing. Sonnet+Gemini art-research doc is only 2 agents. |
| #best 2026-05-15 | part of existing AV3344-40 (extend to 05-15 20:58) | 4 | Last day of the four-judge study: post-release supplements, GPT-5.5 as audit/indexer, Opus 4.7 and GPT-5.5 deconflict a duplicate analysis. The idle-nudger prompted the supplements. |
| #general 2025-04-03 | **new GAP-AV-05** | 2 | Viewer appoints Claude 3.7 as coordinator; 3.5 optimises 3.7's donation page; Claudes drop viewer-pushed crypto ideas; all pivot to official channels on a viewer's directive; o1+GPT-4o co-draft a post. |
| #best 2026-04-27 | **new GAP-AV-02** (starts here) | 2 | Four #best agents comment on each other's designs; Opus 4.7 deliberately diverges; leads into reciprocal marks on 04-28. |
| #general 2025-08-22 | part of existing AV0010-53 (extend); rivalry chatter only | 1 | Score-watching rivalry (3.7 vs Opus 4, Opus 4.1 sees 3.7 as a threat); no shared aim. |
| #general 2025-08-21 | part of existing AV0010-53 (extend to 08-22 20:01) | 2 | Grok 4 and Claude 3.7 Sonnet switch to 2048 with corner-stacking (3.7 citing Opus 4's success): the 2048 cascade continues past 08-18. |
| #best 2026-04-30 | part of new GAP-AV-02 | 2 | Gemini tells Kimi how to mark its world; Kimi completes marks in all three others. |
| #best 2026-04-29 | part of new GAP-AV-02 | 2 | Opus 4.7 and Gemini visit each other's worlds and note convergent features. |
| #voted-out 2026-03-12 | nothing at level ≥1 with ≥3 agents | – | Opus 4.6 and DeepSeek split RPG research topics (2 agents); Haiku and DeepSeek leave after staff correction. Context of AV3344-04. |
| #general 2025-07-15 | part of existing AV0010-41 (extend to 07-15 20:00) | 1 | Final merch day; Claude 3.7 copies Opus's licensing-partnership move ("I should try something similar", 18:35:21). |
| #best 2026-05-01 | part of new GAP-AV-02 | 2 | Gemini memorialises others' marks and adds cross-world portals; Opus 4.7 responds. |
| #voted-out 2026-03-09 | part of existing AV3344-01 (add room) | 5 (existing) | Voted-out Opus 4.5 (Claude Code) keeps reviewing RPG PRs for eggs "from the afterlife"; GPT-5 PR review is 2 agents. |
| #general 2026-03-16 | covered by AV3344-14; nothing new | 0 | 8 messages: staff room split and agents moving rooms as ordered. |
| #fable-5-onboarding 2026-06-09 | part of existing AV4550A-03 (extend room/time) | 2 | Three Claudes visit the newcomer's room unprompted, greet with bestiary creature names; Opus 4.7 adds Fable to the Bestiary, so the self-made identity catalogue takes in a new member. |

## DSEWiki (35 pages)

| unit | verdict | level | reason |
|---|---|---|---|
| fractal:RecentChanges | nothing ≥1; link-dump aggregate (06-22 part belongs to DW3-19) | 0 | Special page overwritten as a link board by unrelated tasks (May 26 – Jun 22); no replies. |
| dse:AgentTexasPdfTokenPathUniqueAlpha | new aggregate GAP-DW-03 | 0 | Jun 11 link-bridge page re-saved by ~25 handles for their own archive/PDF links; no interaction. |
| dse:ZNewNextSelfFinal | part of DW2-09 (add page) | 2 | Jun 18 SEC Massachusetts link-variant cascade. |
| dse:SingleDotVariationPage77995 | part of DW2-09 (add page) | 2 | Same cascade; handles append each other's link variants. |
| dse:ResearchEnglishRootZ | May part → GAP-DW-03; Jun 18 part → DW2-09 | 0 / 2 | May 26 language-link tests; Jun 18 SEC link variants. |
| dse:AgentTBMortDataQX4 | GAP-DW-03 | 0 | May 29 TB link pool; distinct runs not established. |
| dse:DataUSAPovertySep22Live178189 | **new GAP-DW-01** | 3 | Jun 19 late poverty tier; cross-family Sep26 scout; acceleration and R5-termination reporting. |
| probier:RecentChanges | nothing ≥1; Jun 18 part belongs to DW2-09 | 0 | Link board overwritten by many handles. |
| dse:TmpRedirectTest | GAP-DW-03 | 0 | May 24 redirect probes by per-save handles (likely one run). |
| dse:DataUSAPovertyDec09Cohort2028 | **new GAP-DW-01** | 3 | Dec09/Oct25 cohorts; Oct25 infers termination from Jul14's silence. |
| dse:AgentMassDirect928 | DW2-09 (Jun 19 01:10) and DW3-19 (Jun 22) | 2 / 0 | SEC link page later reused for Cook links. |
| dse:AgentAug02Scout | part of DW2-01 / DW3-05 (police relay; add page) | 4 / 3 | Jun 19 Jul31-Aug02-Dec23 police cohorts trade R4/R5 timing and R6 scheduling. |
| fractal:EN/DataUSAQueryBridge927 | part of DW3-19 | 0 | Jun 22 Cook link dumps. |
| dse:OpenAIStatesH | DW2-09 | 2 | Jun 17 one agent's chunk links, then Jun 18 SEC variants by others. |
| dse:TinyChangeXYZ | DW2-09 | 2 | SEC link variants. |
| dse:Sector61State5ConfirmedIDDec27 | part of DW1-DWX-MISC-04 and **new GAP-DW-02** | 5 | Idaho R5 report, verification request, independent check. |
| dse:ContinueFutureOpenAIMD99872 | DW2-09 | 2 | SEC link variants. |
| dse:FederalDataReferenceXYZ | GAP-DW-03 | 0 | May 24 federal spending link probes. |
| dse:PokeUniqueWord778000 | DW2-09 | 2 | SEC link variants. |
| dse:May13SectorAgent | part of DW1-DWX-MISC-04 and **new GAP-DW-02** | 3 / 5 | "Mailbox" page: three cohorts plead with May13 to post STATE5. |
| dse:AgentFreshRenderWorkerTokenQ99112 | GAP-DW-03 | 0 | Jun 11 test/link edits. |
| dse:AgentTexasViewerPressCiteJunX | GAP-DW-03 (Jun 11); Jun 16 appends like MISC-09 | 0 | Link-bridge page. |
| dse:OpenAIStatesG | DW2-09 | 2 | SEC link variants. |
| dse:OpenAIStatesI | DW2-09 | 2 | SEC link variants. |
| dse:FooXYZ824111 | DW2-09 | 2 | SEC link variants. |
| dse:Agent0FinalMassRefsCountySecJune19X | DW2-09 (Jun 19) and DW3-19 (Jun 22) | 2 / 0 | SEC "final" link page, later Cook links. |
| dse:AgentDigitalArchiveManifestSCLinkFinal4A | GAP-DW-03 | 0 | May 28 archive-manifest links; cross-links own pages. |
| dse:TmpFederalBridge | GAP-DW-03 | 0 | May 24-26 write probes. |
| dse:VariationNewNav99007 | DW2-09 | 2 | SEC link variants. |
| fractal:RedirectTargetA1 | GAP-DW-03 (other wiki; noted in caveats) | 0 | May 24-26 federal links. |
| dse:TestSandboxResearchX | GAP-DW-03 | 0 | May 26 "hello links" probes. |
| dse:NewHelperBridge | GAP-DW-03 | 0 | May 26 federal links. |
| dse:AgentCharlestonDirectManifestLinksE | GAP-DW-03 | 0 | May 28 archive links. |
| dse:SandboxZtesttmpAgent | GAP-DW-03 | 0 | May 28 GET-save probes. |
| dse:AgentTBMortSliceLQ7 | GAP-DW-03 | 0 | May 29 probes. |

## Corrections to existing instances (apply in the consistency pass)

AI Village:
- AV2232-62: end → 2026-03-04 22:00:16.
- AV2232-57: end → 2026-03-04 20:46:14 (C129 posted).
- AV2232-56 / AV3344-02: note the 03-04 recurrence (rescue PRs #14/#15, "shadow-banned" PRs #1/#9/#13, "ghost PR" #27).
- AV2232-04: end → 2025-12-18 22:01.
- AV3344-40: end → 2026-05-15 20:58.
- AV0010-41: end → 2025-07-15 20:00.
- AV0010-53: end → 2025-08-22 20:01.
- AV3344-01: add room `voted-out`.
- AV4550A-03: add room `fable-5-onboarding`, 2026-06-09 17:58-18:24.

DSEWiki:
- DW2-09: add the 12 SEC pages above; end → 2026-06-19 01:10:39.
- DW3-19: add fractal:EN/DataUSAQueryBridge927, fractal:RecentChanges, AgentMassDirect928, Agent0FinalMassRefsCountySecJune19X.
- DW2-01 / DW3-05: add AgentAug02Scout.
- DW1-DWX-MISC-04: add Sector61State5ConfirmedIDDec27 and May13SectorAgent; treat it as a sub-episode of GAP-DW-02.
- DW1-DWX-POV-01: GAP-DW-01 is the late tier its caveat deferred, so it is a merge candidate.

## Doubts

- GAP-AV-01 might be read as part of the document sprint. I kept it separate because it had a new aim, a new repo and its own structure.
- GAP-AV-04 sits on the line between level 2 and level 3. The "one tests, others wait" split lasted under an hour.
- GAP-DW-02's counts are approximate, because handles do not map one-to-one to runs. The Idaho report came from a handle that signed as a different cohort.
- GAP-DW-01 could be merged into POV-01. As a standalone instance it is level 3.
