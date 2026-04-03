---
name: creative-consensus
description: Use when you want to generate and explore a wide range of ideas for a creative or design challenge -- dispatches 10-20 parallel agents with dynamic, domain-adapted angles to produce diverse proposals, then presents them with structured evaluation for the user to choose from
---

# Creative Consensus v2

## Overview

Generate a wide range of ideas for a creative or design challenge by dispatching 10-20 parallel agents, each exploring the problem from a different angle adapted to the domain. Collect structured proposals, cluster by approach, stress-test with saboteur agents, and present them in a comparison table with multiple tiers (conservative/moderate/ambitious). The user picks, combines, or redirects -- the skill explores, it does not decide.

## When to Use

- You want to explore a wide range of ideas before committing to an approach
- Designing something where taste matters (sound design, UI, architecture)
- The problem space is large and you want diverse proposals to choose from
- The user says "make it interesting/creative/inspiring" or "brainstorm this"
- You need to map out possibilities quickly -- feature ideas, architecture options, design directions

## Process

### Step 1: Analyze the Problem (~2 seconds, no tools)

Before dispatching agents, analyze the problem to determine:

1. **Domain**: systems architecture / API design / data modeling / security / DevOps / UX / general
2. **Complexity**: scope breadth, irreversibility, constraint count, ambiguity
3. **Recipe**: select from the recipes table below (default: `standard`)

Tell the user: "This reads as a [recipe] problem ([domain] domain). [N] agents. Want me to go bigger/smaller?"

If the user specified a recipe or agent count, use that instead.

### Step 2: Select Angles Dynamically

Based on the detected domain, select angles from the domain-specific libraries below. Always include these three mandatory roles regardless of domain:

- **Regret Agent**: "What will we regret in 1 year if we pick this approach?"
- **Wildcard**: A cross-domain or random-perturbation angle that nobody would think of
- **Saboteur**: "How would you design this to fail spectacularly? Now attack the other proposals."

Fill remaining slots from the domain-specific angle library. If the domain is unclear, use the General library.

### Step 3: Write the Shared Context Block

Write a comprehensive context block with all constraints, references, and requirements. This goes to every agent unchanged.

### Step 4: Dispatch Agents

Use the selected recipe's topology. All agents get `run_in_background: true`.

**Request structured output** from each agent:

```
For each idea you propose, include:
- Name (short)
- Pitch (1 sentence, max 100 chars)
- Mechanism (the core design primitive, 1-2 sentences)
- Effort: S / M / L / XL
- Risk: low / medium / high
- Reversibility: easy / hard / permanent
- Failure mode (how this could go wrong)
- Time horizon this optimizes for: 2h / 1w / 1m / 1y
```

### Step 5: Synthesize (Two-Phase)

**Phase 1 -- Extract & Cluster:**
- Read all agent outputs
- Extract the core mechanism from each proposal (strip articulation quality -- a terse good idea ranks equal to a verbose good idea)
- Group proposals by approach type (similar mechanisms cluster together)
- Pick the strongest variant from each cluster

**Phase 2 -- Present to User:**
- Comparison table with structured fields (name, pitch, effort, risk, reversibility, failure mode)
- Three tiers: **conservative** (proven, low risk), **moderate** (novel but grounded), **ambitious** (high risk, high reward)
- Known failure modes section (from saboteur + all agents' failure_mode fields)
- Horizon labels: "This recommendation optimizes for [timeframe]. The [other timeframe] answer differs in [way]."

Let the user override your picks. They may combine ideas or request deeper exploration on a direction.

## Recipes

| Recipe | Agents | Topology | Model Mix | When to Use |
|--------|--------|----------|-----------|-------------|
| `standard` | 10 | Flat parallel | All sonnet | Default -- feature design, refactoring |
| `deep` | 15 | 2 rounds (10 broad, then 5 focused on promising directions) | Sonnet | Architecture decisions, complex features |
| `thorough` | 20 | 2 rounds (15 broad + 5 focused) with opus synthesis | Haiku R1, Sonnet R2, Opus synthesis | System design, irreversible decisions |
| `research` | 15 (5 explorers + 10 ideators) | Explorers read codebase first, ideators get findings as context | Sonnet | When existing codebase context matters |
| `adversarial` | 10 | 4 debate pairs + 2 saboteurs | Sonnet | When stress-testing matters more than breadth |

For multi-round recipes (`deep`, `thorough`):
- **Round 1**: Broad exploration with diverse angles
- **Between rounds**: Select 2-3 promising directions, identify tension pairs (1 conservative + 1 wild idea)
- **Round 2**: Focused agents explore those directions deeply, seeded with tension pairs

For `research` recipe:
- Explorer agents use `subagent_type: Explore` and read the codebase
- Their findings are injected as soft context (not hard constraints) into ideator prompts
- Explorers and ideators run in parallel; findings merged at synthesis

## Domain-Specific Angle Libraries

Select angles based on detected domain. Fill all slots beyond the 3 mandatory roles (regret, wildcard, saboteur).

**Systems Architecture**: simplest-possible design, failure-first, data flow direction, ownership boundaries, cost at scale, what gets deleted first, reversibility

**API Design**: consumer-first (outside-in), versioning story, idempotency, error expressiveness, "3am on-call" perspective, what the SDK looks like

**Data Modeling**: access-pattern-driven, denormalize deliberately, temporal (what changes over time?), deletion semantics, audit trail, migration story

**Security**: attacker's perspective, least privilege taken literally, trust boundary inversion, "what if this credential leaks?", blast radius minimization, compliance-first

**DevOps/Infra**: what breaks at 2x load, rollback story, observability-first, toil elimination, what a new engineer breaks first, cost optimization

**UX/Product**: first-use experience, power-user path, accessibility-first, error recovery journey, emotional arc, what makes users tell a friend

**General (fallback)**: minimalist, maximalist, constraint-flip, metaphor-driven, temporal/rhythmic, textural, reference-based, emotional, user-experience, time-horizon

## Key Rules

- **Minimum 10 agents** -- below that you lose diversity. Scale up for complex problems, never down.
- Use `model: sonnet` for agents by default. Use `model: haiku` for large divergent swarms (R1 of `thorough`). Reserve opus for synthesis only.
- Each agent is research-only -- no file writes (except `research` recipe explorers which may read files).
- Request structured output from agents (name, pitch, mechanism, effort, risk, reversibility, failure mode, horizon).
- The synthesis is YOUR job, not the agents'. Use two-phase extraction + clustering.
- Always present the comparison table -- let the user override your picks.
- Always include the three mandatory roles: regret, wildcard, saboteur.
- Present three tiers (conservative/moderate/ambitious), not a single blended recommendation.
- Include horizon labels on recommendations.

## Anti-Patterns

- Don't use fewer than 10 agents -- below that you lose diversity
- Don't use the same angles for every domain -- adapt to the problem
- Don't skip the saboteur -- unattacked ideas are the most dangerous
- Don't blend into mush -- present distinct tiers, not one averaged recommendation
- Don't let articulation quality drive selection -- extract mechanisms first
- Don't forget the horizon label -- "this optimizes for 1 week; the 1-year answer differs"
- Don't copy one proposal wholesale -- synthesize across clusters
- Don't ask agents to implement -- just ideate
