# parallel-minds context

Glossary of terms used across this repo's skills. Use these terms consistently in SKILL.md files, agent prompts, sidecar references, and findings reports.

## Core terms

**Panel** — A group of parallel agents dispatched in one round to investigate or ideate on a shared problem. Size is set by the recipe (creative-consensus) or mode (implementation-scrutiny).

**Recipe** — A named configuration in `creative-consensus` that fixes agent count, topology (flat vs. multi-round), and model mix. The recipe matrix lives in [skills/design/creative-consensus/recipes.md](skills/design/creative-consensus/recipes.md).

**Mode** — A named configuration in `implementation-scrutiny` controlling how many verification agents activate. Values: `fast` (3 core), `full` (3 core + 3–5 domain-specific), `auto-escalate` (start fast, escalate on conflict or gap).

**Angle** — A perspective or role assigned to a single agent in a creative-consensus panel (e.g., minimalist, attacker, regret agent). The full per-domain catalog is in [skills/design/creative-consensus/angle-libraries.md](skills/design/creative-consensus/angle-libraries.md).

**Mandatory role** — An angle that's included in every creative-consensus panel regardless of domain: `regret`, `wildcard`, `saboteur`.

**Saboteur** — An agent whose job is to attack proposals. Designs failure modes for them, finds what breaks under load, surfaces the case nobody wanted to think about.

**Null hypothesis** — A verification agent's predicted output assuming the code under scrutiny is correct. Recorded BEFORE running the test, so the agent can't rationalize whatever it sees. The literal prompt template is in [skills/engineering/implementation-scrutiny/null-hypothesis-protocol.md](skills/engineering/implementation-scrutiny/null-hypothesis-protocol.md).

**Validatable artifact** — An executable script or fetchable URL that backs a verification finding. Prose reasoning alone is not evidence.

**Validation gate** — The calling agent's job of executing every script and fetching every URL produced by verification agents before accepting their findings. Procedure in [skills/engineering/implementation-scrutiny/validation-gate.md](skills/engineering/implementation-scrutiny/validation-gate.md).

**Invariant** — A concrete, falsifiable statement about what should be true after the code under scrutiny runs (e.g., "cart.items.length equals successful adds minus successful removes"). Comes from spec or intent, not from what the code currently does.

**Synthesis** — The calling agent's job (not the panel's) of extracting mechanisms from agent outputs, clustering by approach, and presenting structured options to the user. Two phases: extract+cluster, then present.

**Tier** (creative-consensus output) — One of `conservative` (proven, low risk), `moderate` (novel but grounded), `ambitious` (high risk, high reward). The skill presents three tiers, never one blended pick.

**Verdict** (implementation-scrutiny output) — One of `STOP`, `PROCEED WITH CAUTION`, `CLEAN` — communicates the top-level finding to the user, followed by the detailed coverage map.

**Loop** — a producer (`pr` / `jira` / `vuln`) or the dispatcher, each running as its own cron-armed background session.

**Inbox** — a shared queue file (`inbox-prs.md` / `inbox-tickets.md` / `inbox-vulns.md`) of "needs action" tasks in `<kind>:<key>` format.

**Consumer** — a worker subagent the dispatcher spawns (via the `Agent` tool) to process one inbox task; posts PENDING reviews only, never submits.

**Dispatcher** — the router loop; buckets each task into `auto` / `escalate` / `both` and fans out consumers in parallel, capped per cycle.

**Self-rearm** — each loop re-creating its own durable cron near the 7-day expiry so it stays live indefinitely.

**inbox-dir** — the self-contained directory (`config.yaml` + inbox files + a copy of the loop docs) a setup run materializes.

## Anti-terms

These phrasings drift away from the skills' intent. Avoid them in SKILL.md, agent prompts, and findings reports.

- **"Best idea" / "recommendation"** — the skills present options; the user picks. Don't imply the skill chose.
- **"Tests passed"** — that only proves "this angle found nothing." Use coverage-map framing.
- **"Verified correct"** — there is no such verdict. Present what was checked, not what's correct.
- **"Step N"** — workflow headings are numbered (`### 1. Frame the problem`), not labeled with `Step`.
