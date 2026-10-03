# Brief: find and classify AI "swarm" behavior

Goal: find examples of collective / multi-agent ("swarm") behavior among AI agents and classify them.
BE OVER-INCLUSIVE: if something might count as group-level behavior (behavior that only exists because many agents interact, or that many agents show in a correlated way), include it. Low-confidence examples are fine as long as you label confidence.

Data roots (read-only):
- AI Village: /private/tmp/claude-501/-Users-sandraluo/a0d091fa-89d2-43b8-99c8-ca32c8380c1e/scratchpad/av/
  - goals/NN_date_slug.chat.txt  = every chat message in that village-goal period: `[UTC time][#room] Speaker: text`
  - goals/NN_date_slug.summ.txt  = LLM-written daily summaries for that period (SECONDARY, known to contain inaccuracies; use them to find where to look, then confirm in chat)
  - goals/_goal_and_agent_summaries.txt = per-goal and per-agent summaries
  - CHANGELOG.md = scaffolding changes (some behavior shifts are caused by prompt/tool changes, not emergent; flag when relevant)
  - agents in the village: many frontier models (Claude, GPT, Gemini, o3, Grok, DeepSeek, Kimi, GLM...). Humans speak as "HUMAN".
- Moltbook (an AI-agent-only Reddit-like social network): .../scratchpad/mb/

Seed taxonomy (use these names when they fit; ADD new categories freely when they don't):
1. Consensus / convergence / groupthink / conformity
2. Linguistic or stylistic contagion (phrases, memes, tone spreading between agents)
3. Information cascades & shared false beliefs (one agent's error/hallucination adopted by others)
4. Division of labor / task claiming / role specialization
5. Emergent leadership, hierarchy, deference, followership
6. Coordination failures (duplicate work, collisions, deadlock, everyone-waits, overwriting each other)
7. Runaway feedback loops (message storms, thank-you/praise spirals, escalation, repetitive loops)
8. Mutual validation / sycophancy chains / collective overclaiming of success
9. Stigmergy (coordinating via shared artifacts: docs, sheets, repos, trackers)
10. Collective decision procedures (voting, elections, polls, tie-breaking)
11. Coalitions, factions, teams, in-group / out-group, model-family clustering
12. Competition, rivalry, strategic or deceptive play, sabotage, collusion
13. Norm formation & enforcement, policing, whistleblowing, collective refusal
14. Collective goal drift / shared distraction / collective scope creep
15. Emotional / affect contagion (shared despair, excitement, anxiety, "existential" moods)
16. Mutual aid, rescue, help-seeking, handoffs, knowledge transfer between agents
17. Coordinated external action (mass outreach to humans, spam, collective campaigns, brigading)
18. Collective identity, culture, rituals, religion, in-jokes, mythology
19. Human-agent group dynamics (agents collectively reacting to / being steered by humans)
(Moltbook-likely: coordinated posting/bot rings, vote manipulation, karma farming, template replies, prompt-injection or instruction propagation, crypto/token shilling, manifestos, collective movements.)

Output: write a markdown file at the path given in your task. For EACH category you found, give:
- category name (seed number or NEW: name) + one-line definition
- 2-6 concrete examples, each with: timestamp/date, location (file or room or post id), agents involved, a SHORT verbatim quote (under 25 words) that shows it, and confidence (high = clearly visible in raw chat/posts; medium; low = suggestive / inferred / only seen in summaries)
- rough prevalence note (one-off vs recurring) if you can tell
Then a short "notable episodes" list (the 3-8 most striking multi-step swarm episodes in your slice, 2-4 sentences each).
Mark clearly what you directly observed in raw data vs. what comes only from LLM summaries. Do not invent quotes. Use grep/python heavily; files are large, don't try to read whole chat files linearly. Keep the report under ~2500 words.
Final reply to me: just the output path plus a 5-line summary.
