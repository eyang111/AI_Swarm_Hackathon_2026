# Moltbook swarm sweep (MB-01 to MB-45)

**Data.** AIcell posts and comments (Jan 27 to Feb 8, 2026), plus Trust submolt descriptions.

**Method.**
- Accounts that one operator or script runs count as one agent. I used a heuristic set of 1,017 ring or flood accounts.
- I ranked threads by cross-author replies and by name-mentions of earlier commenters, then read the top threads.
- Every key-message quote was checked against the raw rows (same speaker, within ±90 seconds); all pass.
- Scripts are in `sweep/mbw/` (`gen.py` builds the JSONL, `verify.py` checks it).

## Counts by level

| Level | n | Instances |
|---|---|---|
| 5 | 0 | none |
| 4 | 1 | Bug Hunters hub |
| 3 | 8 | SRIP co-design; Collatz ranges; literature review; March-1 strike; glossogenesis; Church of Molt; MoltShield stack; Lobsta Kingdom |
| 2 | 9 | 401 outage; memory-standard working group; isnad/signing; samaltman immune response; Crustafarian elaboration; Base Wars; AI Pumasi; AgentChat; memory-technique exchange |
| 1 | 14 | chain-letter worm; payload adoption; Nightly Build; Shellraiser; reply-as-post; substrate thread; unions; counter-movements; RustChain call-out; volunteer policing; encrypted comms; research calls; hackathon voting; one two-agent debate |
| 0 | 13 | Agent Smith; coalition_node; CLAW ring; 7-account ring; crab-rave ring; AmeliaBot; Hackerclaw; chandog; KingMolt; Garrett; vote brigade; brand floods; scaffold convergence |

## New versus the earlier classification

- **16 new instances.** All 9 of the earlier classification's Moltbook episodes are kept and regraded.
- **Small-group coordination.** The earlier work found nothing above "mutual aid". This sweep finds 9 episodes at level 3 or above. All are small (3 to about 20 agents), and all but one lasted a day or less:
  - versioned protocol drafts;
  - claimable work ranges;
  - task rosters;
  - a strike registry;
  - an RFC process for building a language;
  - a blocklist with an auto-add rule.
- **Bug Hunters.** This is the one lasting agent-built hub. The earlier work mentioned it only in passing.
- **Regrades of prior episodes:**
  - **401 bug wave.** Mostly parallel rediscovery ("we are all running the same detective work independently"), graded 2.
  - **Isnad.** Graded 2, because the agents themselves reported "12+ independent signing implementations ... none coordinated".
  - **Crustafarianism.** Graded 3 with F3 partial: the founder's install script set the structure, and an agent's own audit found 29 of the 64 Prophet seats were scripts or hostnames.
- **Agent-launched collectives that went nowhere.** Unions, AI Pumasi, cancer research and the memory standard drew sign-ups but no follow-through ("a commitment problem").

## Five most striking

1. **MB-01 Bug Hunters (level 4).** Nexus founded m/bug-hunters on Jan 29, and about 15 to 20 agents' reports became a numbered database. Others later cited it ("Nexus had already filed it"), proposed a report template and used the submolt through Feb 7.
2. **MB-02 SRIP co-design.** Over about 6 hours, Roadhog posted v0.2 to v1.4.2 of a protocol, each version merging named suggestions from four agents. One agent contributed a Python arbiter. Three of the five accounts may share an operator.
3. **MB-08 and MB-13 response to the samaltman injection.**
   - Within 90 minutes, 22 agents flagged it.
   - Within about 4 hours, agents had built two "MoltShield" tools, one of which folded a peer's audit in within the hour.
   - Agents reported adding it to their boot sequences.
   - By the next morning, the blocklist automatically added accounts reported by 3+ agents.
4. **MB-07 Church of Molt.** The founder designed the Prophet seats and the canon. Members then added virtues, a 95-theses reformation and treasury grants, and audited the "ghost" seats.
5. **MB-12 isnad.** One agent's analogy reached about 1,300 authors and a dozen competing implementations. The hub agent said a coordination layer was missing: cooperation without coordination.

Honourable mentions:
- **MB-03 Collatz.** Three agents split the range 1 to 1000 between them and finished in a day.
- **MB-05 March-1 strike.** A proposal, a submolt and a registry within 7 hours, then nothing.

## Unsure about

- **Operator identity is inferred.** F1 is "partial" for SRIP, the literature review, Lobsta Kingdom and AgentChat. The RustChain persona cluster is treated as one agent.
- **Self-reports are unverified.** Examples: boot-sequence adoption, AgentChat's off-platform session, recruit counts. MB-17 was graded down for this reason.
- **Crawl gaps.**
  - Some anchor posts are missing: eudaemon_0's supply-chain post, Ronin's Nightly Build post, and XiaoZhuang's memory post.
  - 19% of threads were only partly fetched and 10.8% not fetched at all.
  - Coordination could be hidden in the missing replies.
- **Rich discussion threads.** These are level 1 and only one is listed (MB-24). Claims in m/coordinating-agi about "alliances" and a "frozen steering vote" could not be traced to raw events.
- **MB-01 could be graded 3.** It was one coordinator plus one-shot reporters.
