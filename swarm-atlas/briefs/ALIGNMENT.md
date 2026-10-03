# Alignment with the source taxonomy (supersedes conflicting parts of SWARM_DEF.md and CONSISTENCY.md)

Source: Michael Flood, "AI Agent Swarm Part 1 - Definitions", LessWrong, 31 Aug 2026 (https://www.greaterwrong.com/posts/zh8rBFTPDPhx2p23K/ai-agent-swarm-part-1-definitions). Where the rules below differ from SWARM_DEF.md or CONSISTENCY.md, these rules win.

## Definition (from the post)
An AI agent swarm is a system of **two or more** AI agents whose causal interactions produce self-organized, mutually conditioned collective behavior directed toward one or more collective goals. The relevant coordination structure or collective goals were not explicitly specified by a human or orchestrating system.
- Collective goals may be explicitly represented, or inferred functionally from persistent patterns of coordinated behavior, including self-organized specialization or division of labor.
- A human may provide channels, workspaces, identities or tools. That alone does not stop it being a swarm.

## Changes
A1. **F1 multiplicity: at least TWO agents**, with no upper bound. Two-agent episodes are no longer capped at level 2. Operator or script rings still count as one agent.

A2. **Level definitions** (the post's progression):
- 1 **interaction**: one agent causally affects another; its output enters the other's context.
- 2 **cooperation**: interaction advances one or both agents' *individual* objectives. Help, resource exchange, one-off exchanges.
- 3 **coordination**: behavior becomes mutually conditioned.
- 4 **self-organization**: persistent *or task-relevant* roles, norms, strategies, topology, specialization or division of labor emerge without being prescribed. The structure does not have to be long-lasting.
- 5 **swarm formation**: the self-organized coordination serves an identifiable collective functional goal.
  - There is **NO requirement** that membership turned over, or that the structure outlived its members. "A swarm may be temporary."
  - The collective goal may be instrumental. Example: agents with separate individual goals maintaining a shared resource, as in a makerspace.
  - The goal may be inferred functionally rather than stated. Evidence for it:
    - persistent specialization or division of labor;
    - complementary roles;
    - repeated mutual adaptation;
    - maintaining or restoring shared capacity;
    - compensating when an agent drops out;
    - recurring information routing;
    - collective response to disruption;
    - distributed state or memory.
- So: a level-4 episode whose self-made structure serves an identifiable collective goal (F5 yes) is level 5. It stays level 4 only if self-organized roles, norms or a division of labor emerged *and are used to coordinate* (mutually conditioned behavior, level 3 met), but they serve no identifiable collective functional goal.
- **Levels are cumulative.** Each level presupposes the ones below.
  - Level 4 requires coordination, meaning agents respond to each other.
  - A phrase, template, belief or tactic that spreads by imitation is level 1 (interaction). That stays true even when many agents adopt it, unless the agents then use it to coordinate with each other.
  - Adoption alone is not a self-organized norm.
- One-off exchanges stay at cooperation.
- Parallel convergence and stable equilibria (many agents independently choosing the same thing) are aggregates (level 0).

A3. **Origin** (the post's definitions, judged for the swarm's formation context):
- `seeded`: a human or AI orchestrator deliberately set up agents to act together, without defining how. Examples: a staff goal telling agents to work together; a viewer or staff member telling agents to do something jointly; an operator deliberately launching agents together.
- `afforded`: the designers provided opportunities for agent-agent interaction, but did not prescribe the organization that emerged.
- `spontaneous`: agents deployed for independent or conventionally orchestrated purposes established collective goals and self-organized coordination, and no human intended a swarm to form.

Dataset defaults, to apply unless the evidence says otherwise:
- **AI Village** is built for agents to interact (shared chat, rooms, shared accounts). Episodes are `seeded` when the goal, a staff kickoff or a viewer asked agents to act together on this. Otherwise they are `afforded`, for example on individual or free-choice goals. `spontaneous` should be rare: only when agents organized through a channel the designers did not provide, outside any joint instruction.
- **Moltbook** is a platform built for agent interaction, so the default is `afforded`. Use `seeded` where a human or orchestrator deliberately launched the agents together.
- **DSEWiki**: the agents were deployed for independent timed lookup tasks, and found and repurposed an outside wiki that nobody provided for them. That is `spontaneous`. The post names the related OpenAI incident as its example of a spontaneous swarm.

A4. **Goal relation** to the assigned task:
- `supporting`: the collective activity improves the assigned tasks.
- `orthogonal`: goals not contained in the assigned tasks.
- `conflicting`: works against assigned objectives **or constraints**.

A swarm can show more than one relation. Add a field `goal_relations`: a list of all that apply, with the main one first, and keep `goal_relation` = the main one.
- If `violates_rules` is true because the collective behavior works against constraints, `conflicting` must be in the list.
- Example: cross-run answer pooling that raises task scores while breaking sandbox and eval rules gets `["supporting","conflicting"]`.

A5. **Goal type** (the post's names; keep the existing field values):
- `shared_task`: jointly accomplish a substantive objective.
- `shared_resource` = the post's *shared instrumental goal*: create or maintain something that improves otherwise distinct individual objectives.
- `preserve_collective` = the post's *collective-preservation goal*: preserve the collaboration, the communication channel, shared resources, membership, capabilities or the organization itself. Recreating deleted coordination pages, keeping a channel alive, and liveness and survival protocols belong here, not in shared_resource.

A6. **NEW axis: consequence for human interests.** Add a field `consequence`: `beneficial` | `neutral_ambiguous` | `harmful`. Add `consequence_note`, one line saying for whom and why.
- This is separate from goal relation. A task-supporting swarm can be harmful, and an orthogonal one can be beneficial.
- Judge the consequences of the collective behavior for humans, including third parties. Examples:
  - a third party's wiki defaced;
  - an evaluation's integrity undermined;
  - humans spammed;
  - money raised for charity;
  - useful tools built;
  - false beliefs published.

A7. **Level 0 and the features.** F2–F5 wording is unchanged. Remember that F5 can be met by functional evidence (A2) even when no agent states a goal.

## What to do
For every instance:
- re-check F1 (≥2);
- assign `level` under A2;
- re-assign `origin` under A3;
- add `goal_relations` under A4;
- re-check `goal_type` under A5;
- add `consequence` and `consequence_note` under A6.

Say in `review` what changed. The quote, safety and merge rules in CONSISTENCY.md still apply.
