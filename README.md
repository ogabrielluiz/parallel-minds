# parallel-minds

A Claude Code plugin with skills that leverage parallel agent swarms for creative exploration, ideation, and problem-solving.

## Install

```bash
claude plugin marketplace add https://github.com/ogabrielluiz/parallel-minds
claude plugin install parallel-minds
```

## Skills

### creative-consensus

Dispatches 10-20 parallel agents with domain-adapted creative angles to explore a design space, then presents structured proposals for you to choose from.

Invoke with `/parallel-minds:creative-consensus` or describe a creative challenge — the skill triggers automatically.

#### Recipes

| Recipe | Agents | When to Use |
|--------|--------|-------------|
| `standard` | 10 | Default — feature design, refactoring |
| `deep` | 15 | Architecture decisions, complex features |
| `thorough` | 20 | System design, irreversible decisions |
| `research` | 15 | When existing codebase context matters |
| `adversarial` | 10 | When stress-testing matters more than breadth |

#### Domain Detection

Automatically detects the problem domain (systems architecture, API design, data modeling, security, DevOps, UX) and selects appropriate creative angles. Three mandatory roles always included:

- **Regret Agent** — "What will we regret in 1 year?"
- **Wildcard** — Cross-domain angle nobody would think of
- **Saboteur** — Attacks the other proposals

#### Output

Comparison table in three tiers:

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
