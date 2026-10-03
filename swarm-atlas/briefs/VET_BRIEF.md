# Vetting brief: second-pass check of a swarm-behavior report

A first-pass agent wrote a report classifying AI "swarm" (multi-agent / collective) behavior. Your job is an independent, skeptical check of that report against the RAW data, plus a gap-fill.
Read /private/tmp/claude-501/-Users-sandraluo/a0d091fa-89d2-43b8-99c8-ca32c8380c1e/scratchpad/BRIEF.md first for the original task and taxonomy.

IMPORTANT data note (new since the first pass): the AI Village chat files av/goals/*.chat.txt were regenerated. Non-agent speakers are now labelled `HUMAN(<name>)` or `BOT(automated)`. `BOT(automated)` is an automatic system/nudger, NOT a person (2,230 messages). Staff accounts include zak, adam, admin, Larissa Schiavo, Shoshannah; most other HUMAN names are public viewers. The first pass saw every non-agent as "HUMAN", so any claim like "a human corrected the group" must be re-checked for who actually spoke.

## Part A: verify every concrete claim
For each concrete claim in the report (a quote, a timestamp, a speaker, a count, a sequence of events, "X happened before Y"):
1. Does the quote exist (verbatim or near-verbatim) from that speaker at about that time? grep for it.
2. Do counts reproduce? Re-count with your own method and state the method. Small differences are fine; flag anything off by more than ~25% or with a wrong direction.
3. Does the interpretation hold? Look at surrounding context (±20 messages). Is it really group-level (several agents interacting / correlated), or is it one agent, a direct human/staff instruction, the automated bot, or a scaffolding change listed in av/CHANGELOG.md? Is the causal story (A copied B, belief spread from X) supported by order of timestamps?
4. For claims marked as summary-only, try to confirm or refute them in raw data.
Give each claim a verdict: CONFIRMED / PARTLY (state the correction) / WRONG (state what the data shows) / UNVERIFIABLE (say why). Be specific and terse.

## Part B: gap-fill (the user wants OVER-inclusive detection)
Within the same slice, look for swarm behaviors the report missed or covered thinly: categories with no or weak examples, and possible new categories. Add up to ~10 new examples, each with timestamp, location, agents, a short verbatim quote (<25 words) and confidence. Do not invent quotes.

## Output
Write markdown to the path given in your task: a table or list of verdicts (claim → verdict → evidence/correction), then "Corrections that change the conclusions" (the few that matter most), then the Part B additions. Keep under ~2000 words.
Final reply to me: the output path, counts of CONFIRMED/PARTLY/WRONG/UNVERIFIABLE, and the 3-5 most important corrections or additions.
