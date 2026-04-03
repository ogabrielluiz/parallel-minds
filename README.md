# creative-consensus

A Claude Code plugin that dispatches 10-20 parallel agents with domain-adapted creative angles, then synthesizes the best ideas with structured evaluation and stress-testing.

Turns "pick the first idea" into "pick from the best of 10-20 competing ideas, stress-tested and ranked."

## Install

```bash
claude plugin marketplace add https://github.com/ogabrielluiz/creative-consensus
claude plugin install creative-consensus
```

## Usage

Invoke with `/creative-consensus:creative-consensus` or just describe a creative/design challenge — the skill triggers automatically when multiple valid approaches exist.

### Recipes

| Recipe | Agents | When to Use |
|--------|--------|-------------|
| `standard` | 10 | Default — feature design, refactoring |
| `deep` | 15 | Architecture decisions, complex features |
| `thorough` | 20 | System design, irreversible decisions |
| `research` | 15 | When existing codebase context matters |
| `adversarial` | 10 | When stress-testing matters more than breadth |

### Domain Detection

The skill automatically detects the problem domain (systems architecture, API design, data modeling, security, DevOps, UX) and selects appropriate creative angles. Three mandatory roles are always included:

- **Regret Agent** — "What will we regret in 1 year?"
- **Wildcard** — Cross-domain angle nobody would think of
- **Saboteur** — Attacks the other proposals

### Output

Results are presented as a comparison table in three tiers:

- **Conservative** — proven, low risk
- **Moderate** — novel but grounded
- **Ambitious** — high risk, high reward

Each idea includes: name, pitch, mechanism, effort, risk, reversibility, failure mode, and time horizon.

## Local Development

```bash
claude --plugin-dir ./
```

## License

MIT
