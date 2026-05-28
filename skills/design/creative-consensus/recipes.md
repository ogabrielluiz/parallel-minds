# Recipes

Pick a recipe in step 1 of the workflow. The recipe determines agent count, topology, and model mix. Default is `standard`.

## Recipe matrix

| Recipe | Agents | Topology | Model Mix | When to Use |
|--------|--------|----------|-----------|-------------|
| `standard` | 10 | Flat parallel | All sonnet | Default -- feature design, refactoring |
| `deep` | 15 | 2 rounds (10 broad, then 5 focused on promising directions) | Sonnet | Architecture decisions, complex features |
| `thorough` | 20 | 2 rounds (15 broad + 5 focused) with opus synthesis | Haiku R1, Sonnet R2, Opus synthesis | System design, irreversible decisions |
| `research` | 15 (5 explorers + 10 ideators) | Explorers read codebase first, ideators get findings as context | Sonnet | When existing codebase context matters |
| `adversarial` | 10 | 4 debate pairs + 2 saboteurs | Sonnet | When stress-testing matters more than breadth |

Scale up for complex problems, never down. Ten agents is the floor for diversity.

## Multi-round recipes (`deep`, `thorough`)

These run in two rounds with a synthesis pause in between:

- **Round 1**: Broad exploration with diverse angles. Every agent gets the full shared context block and a unique angle from the domain library.
- **Between rounds**: Select 2-3 promising directions from Round 1's clusters. Identify *tension pairs* — one conservative idea paired with one wild idea — to seed Round 2 with productive friction.
- **Round 2**: Focused agents explore the selected directions deeply, seeded with the tension pairs as context. They sharpen and stress-test rather than diverge.

For `thorough`, Round 1 uses haiku (cheap, wide), Round 2 uses sonnet (sharper), and synthesis uses opus (best judgment on the final shape).

## Research recipe

Use when the existing codebase strongly shapes what's viable — refactors, feature additions inside opinionated frameworks, migrations.

- **Explorer agents** use `subagent_type: Explore` and read the codebase. They surface constraints, existing patterns, prior art, and gotchas.
- **Ideator agents** receive the explorers' findings as *soft context* (not hard constraints). This keeps ideators from anchoring too hard on what already exists while still grounding them in reality.
- Explorers and ideators run in parallel; their outputs merge at the synthesis step.

Explorer agents may read files. All other agents across all recipes are research-only — no file writes.
