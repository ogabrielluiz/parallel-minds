---
name: creative-consensus
description: Use when you want to generate and explore a wide range of ideas for a creative or design challenge -- dispatches 10-20 parallel agents with dynamic, domain-adapted angles to produce diverse proposals, then presents them with structured evaluation for the user to choose from
---

# Creative Consensus

Dispatch a swarm of parallel agents at a creative or design problem, each attacking it from a different angle, then surface the proposals as a structured comparison the user can pick from. This is for problems where taste matters and the design space is large: sound design, UI directions, architecture options, feature framing.

## Philosophy

**Explore, don't decide.** The skill's job is to widen the option space, not to converge on an answer. Ten agents is the floor — below that, proposals collapse into the same handful of obvious takes and you lose the diversity that makes the whole exercise worth running.

Synthesis is the caller's job, not the agents'. Agents propose; you cluster, stress-test, and present. The user picks. Output ships in three distinct tiers — conservative, moderate, ambitious — never blended into a single averaged recommendation.

See [recipes.md](recipes.md) for the recipe matrix and multi-round flow. See [angle-libraries.md](angle-libraries.md) for the per-domain angle catalog.

## Workflow

### 1. Analyze the problem

Before dispatching, take a couple of seconds to classify:

- **Domain**: systems architecture / API design / data modeling / security / DevOps / UX / general
- **Complexity**: scope breadth, irreversibility, constraint count, ambiguity
- **Recipe**: pick from [recipes.md](recipes.md) — default is `standard`

Tell the user: "This reads as a [recipe] problem ([domain] domain). [N] agents. Want me to go bigger/smaller?" If they already specified a recipe or agent count, use that.

Use this skill when you want to explore widely before committing, when taste matters, or when the user says "make it interesting/creative" or "brainstorm this."

### 2. Select angles

Pull angles from the matching domain library in [angle-libraries.md](angle-libraries.md). If the domain is unclear, use the General fallback. Adapt angles to the problem — the same set for every domain is a smell.

Always include these three mandatory roles regardless of domain:

- **Regret Agent**: "What will we regret about this approach?"
- **Wildcard**: a cross-domain or random-perturbation angle nobody would think of
- **Saboteur**: "How would you design this to fail spectacularly? Now attack the other proposals."

Watch for: skipping the saboteur. Unattacked ideas are the most dangerous ones in the pile.

### 3. Write the shared context block

Write one comprehensive context block with all constraints, references, and requirements. It goes to every agent unchanged — agents diverge through their angle, not through different framings of the problem.

### 4. Dispatch agents

Use the selected recipe's topology. All agents run with `run_in_background: true`.

- Default to `model: sonnet`. Use `haiku` for large divergent swarms (e.g. R1 of `thorough`). Reserve `opus` for synthesis only.
- Agents are research-only — no file writes. The `research` recipe explorers may read files but not write.
- Don't ask agents to implement. Ideation only.

Request structured output from each agent:

```
For each idea you propose, include:
- Name (short)
- Pitch (1 sentence, max 100 chars)
- Mechanism (the core design primitive, 1-2 sentences)
- Effort: S / M / L / XL
- Risk: low / medium / high
- Reversibility: easy / hard / permanent
- Failure mode (how this could go wrong)
```

### 5. Synthesize in two phases

**Extract & cluster.** Read all agent outputs. Pull the core mechanism out of each proposal — strip articulation quality so a terse good idea ranks equal to a verbose good idea. Group by approach type and pick the strongest variant from each cluster.

Watch for: letting articulation quality drive selection, or copying one proposal wholesale. Synthesize across clusters.

**Present to user.** Build a comparison table with the structured fields (name, pitch, effort, risk, reversibility, failure mode). Organize into three tiers:

- **Conservative**: proven, low risk
- **Moderate**: novel but grounded
- **Ambitious**: high risk, high reward

Include a known-failure-modes section drawn from the saboteur and every agent's `failure_mode` field.

Watch for: blending into mush. Keep the tiers distinct. Let the user override your picks, combine ideas across tiers, or send you back for a deeper pass on a direction.
