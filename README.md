# parallel-minds

A Claude Code plugin with skills that leverage parallel agent swarms for creative exploration, ideation, problem-solving, and implementation verification.

## Install

### Via skills CLI

```bash
npx skills@latest add ogabrielluiz/parallel-minds
```

Pick the skills you want when prompted. Skills are installed globally and work with any coding agent that supports SKILL.md.

### Via Claude Code plugin marketplace

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

- **Regret Agent** — "What will we regret about this approach?"
- **Wildcard** — Cross-domain angle nobody would think of
- **Saboteur** — Attacks the other proposals

#### Output

Comparison table in three tiers:

- **Conservative** — proven, low risk
- **Moderate** — novel but grounded
- **Ambitious** — high risk, high reward

Each idea includes: name, pitch, mechanism, effort, risk, reversibility, and failure mode.

### implementation-scrutiny

Dispatches parallel verification agents to investigate whether an implementation is correct. Each agent takes a different verification angle — reference implementations, empirical tests, invariant checks, documentation comparisons.

Invoke with `/parallel-minds:implementation-scrutiny` or triggered automatically when code produces wrong results and initial fix attempts fail.

#### Modes

| Mode | Agents | When to Use |
|------|--------|-------------|
| `fast` | 3 core | Default — focused problem, clear domain |
| `full` | 6-8 (core + domain) | Complex, multi-layered, or core agents disagree |
| `auto-escalate` | 3 → 6-8 | Start fast, escalate if agents conflict or leave gaps |

#### Core Agents (always dispatched)

- **Reference Hunter** — Finds known-correct implementations and documents behavioral differences
- **Empirical Tester** — Writes and executes standalone tests with known inputs/outputs
- **Invariant Auditor** — Verifies each extracted invariant independently from first principles

#### Domain-Specific Agents

Activated based on detected domain: `numerical/dsp`, `web-backend/distributed`, `frontend`, `data/ml`, `database`, `security`, or `general`.

#### Evidence Standard

Every finding must include a **validatable artifact** — an executable script or a verifiable URL. The calling agent validates every artifact before accepting it. Findings without valid artifacts are demoted to UNVERIFIED.

#### Output

Structured findings report with severity tiers:

- **Proven Bugs** — script reproduced the issue, with repro recipe
- **Likely Bugs** — reference disagrees but untested
- **Agent Disagreements** — conflicting findings shown side-by-side
- **Coverage Map** — what was checked and what wasn't

Validated test scripts persist to `scrutiny/` for regression coverage.

### inbox-loops

Bootstraps a multi-session "inbox" task system. Producer loops (PR, Jira, Vuln) each scan a source on a staggered cron and emit "needs action" tasks into shared queue files. A dispatcher loop routes each task to an auto-dispatched consumer subagent or escalates it to the user via push notification. Every loop runs as its own cron-armed background session and self-re-arms near the 7-day cron expiry to stay live indefinitely.

Invoke with `/parallel-minds:inbox-loops`, or describe intent to set up, start, check status of, or stop the inbox loops.

| Loop | Emits into | Default cadence |
|------|-----------|-----------------|
| PR | `inbox-prs.md` | `13 */3 * * *` |
| Jira | `inbox-tickets.md` | `43 */3 * * *` |
| Vuln | `inbox-vulns.md` (sensitive, local-only) | `33 */6 * * *` |
| Dispatcher | routes the three inboxes | `23 * * * *` |

**Lifecycle:** status via `claude agents --json` (filter `inbox-*`); stop via `claude stop <id>` followed by removing durable cron entries from `~/.claude/scheduled_tasks.json`.

The dispatcher spawns consumer subagents using the built-in `Agent` tool (the parallel-swarm element): multiple `Agent` calls in a single message run in parallel, capped per cycle. Vuln entries never leave the machine.

## Local Development

```bash
claude --plugin-dir ./
```

## License

MIT
