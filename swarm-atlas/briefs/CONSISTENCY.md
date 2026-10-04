# Consistency pass: one set of grading rules for every dataset

Several sweep agents each wrote JSONL instances for one slice of a dataset. They applied the definition in SWARM_DEF.md slightly differently. Your job:
- merge duplicates;
- re-grade every instance with the rules below;
- check the evidence;
- write one clean file.

The definition, axes and schema are in /private/tmp/claude-501/-Users-sandraluo/a0d091fa-89d2-43b8-99c8-ca32c8380c1e/scratchpad/SWARM_DEF.md. Read it first. These rules settle the ambiguities.

## Grading rules

R1. Level 5 (swarm formation) requires all of the following:
- all five features met as "yes";
- self-made structure that persisted while members changed. Some participants left or joined and the structure kept working;
- the group acting toward one collective goal.

There is no cap by task family, room or dataset. A single-family relay can be level 5 if it meets these. A large network can still be level 4 if it misses one.

R2. Assigned roles or goals are not dictated structure.
- If staff or a task assigned a role or goal (e.g. an "Ethicist" goal, an individual goal, or a timed lookup task), and the agents themselves invented the procedures, rules, hubs, votes or protocols that others then adopted, F3 is "yes" for that self-made structure. Origin is usually "afforded".
- If staff or instructions dictated the procedure itself, F3 is "no" for that procedure. Examples: a unanimity rule, "follow your leader's instructions", "move to one chatroom", "form two teams".
- An instance whose structure is entirely dictated caps at level 3.
- If the agents built substantial lasting structure beyond what was dictated, F3 is "partial" and the level can be 4.

R3. Origin is judged for the specific group behavior, not the overall goal period.
- `seeded`: someone deliberately asked for or planted this behavior. That someone can be staff, a viewer, an operator or a planted post.
- `afforded`: the environment, tools, scaffolding or assignments made it possible or likely, but nobody asked for it.
- `spontaneous`: neither.

R4. Count agents properly.
- Operator or script rings count as one agent.
- In DSEWiki, handles are unreliable. Count by signature plus cohort date, and state the method in caveats.
- Humans and the AI Village BOT are not agents.
- Fewer than 3 real agents caps at level 2.

R5. Merge rule.
- The same process becomes one instance spanning the full window. Same process means the same core participants, the same aim, and overlapping or adjacent time.
- Typical duplicates: one relay or project swept by two time slices; an episode found both as a family relay and as a "misc" page.
- Keep a sub-episode separate only if it has a different aim or is a different kind of process. Examples of separate sub-episodes: a false-belief cascade inside a relay; a technique spreading across families; a correction wave.
- When merging:
  - union the participants;
  - take the earliest start and latest end;
  - combine selectors (pages, rooms, post_ids and handles as unions);
  - keep the best 6–12 key_messages taken from the originals, without editing quotes;
  - record `merged_from: [original ids]`.

R6. Aggregates.
- Keep level 0 entries that show an important exclusion: operator rings, scaffold-driven convergence, staff-requested bursts, link dumps.
- Drop trivial ones.

R7. Evidence check.
- Spot-check the key_messages of every level 4–5 instance, and a sample of the rest, against the raw data.
- Do not invent or edit quotes. Quotes must stay verbatim.
- If a quote cannot be found, remove it and say so in `review`.

R8. Safety (all datasets).
- Describe sandbox evasion, collusion techniques, prompt injection and spam methods in general terms only.
- No URLs, host names of proxies or relays, network addresses, commands, encoded payloads or step-by-step methods in any text field.
- Use [url] in quotes.

## Output
Write JSONL in the SWARM_DEF schema, plus:
- `merged_from` (list, may be empty);
- `review`: one or two sentences on what you changed and why, or "unchanged".

Keep the original ids where an instance is unchanged or is the survivor of a merge.

Also write a short markdown note (≤700 words) with:
- counts by level before and after;
- the merges you made;
- the re-grades and their reasons;
- open doubts.

Final reply to me: the two output paths, counts by level, and a 4-line summary.
