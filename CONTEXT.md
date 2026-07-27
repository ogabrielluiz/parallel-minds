# parallel-minds context

Glossary of terms used across this repo's skills. Use these terms consistently in SKILL.md files, agent prompts, sidecar references, and findings reports.

## Core terms

**Panel** — A group of parallel agents dispatched in one round to investigate or ideate on a shared problem. Size is set by the recipe (creative-consensus) or mode (implementation-scrutiny).

**Recipe** — A named configuration in `creative-consensus` that fixes agent count, topology (flat vs. multi-round), and model mix. The recipe matrix lives in [skills/design/creative-consensus/recipes.md](skills/design/creative-consensus/recipes.md).

**Mode** — A named configuration controlling how many agents activate. In `implementation-scrutiny`: `fast` (3 core), `full` (3 core + 3–5 domain-specific), `auto-escalate` (start fast, escalate on conflict or gap). In `plan-scrutiny`: `fast` (3 readers), `full` (5 readers), `auto-escalate` (start at 3, add 2 when more than a third of tasks split).

**Angle** — A perspective or role assigned to a single agent in a creative-consensus panel (e.g., minimalist, attacker, regret agent). The full per-domain catalog is in [skills/design/creative-consensus/angle-libraries.md](skills/design/creative-consensus/angle-libraries.md).

**Mandatory role** — An angle that's included in every creative-consensus panel regardless of domain: `regret`, `wildcard`, `saboteur`.

**Saboteur** — An agent whose job is to attack proposals. Designs failure modes for them, finds what breaks under load, surfaces the case nobody wanted to think about.

**Null hypothesis** — A verification agent's predicted output assuming the code under scrutiny is correct. Recorded BEFORE running the test, so the agent can't rationalize whatever it sees. The literal prompt template is in [skills/engineering/implementation-scrutiny/null-hypothesis-protocol.md](skills/engineering/implementation-scrutiny/null-hypothesis-protocol.md).

**Validatable artifact** — An executable script or fetchable URL that backs a verification finding. Prose reasoning alone is not evidence.

**Cold read** — A `plan-scrutiny` reader's report of what it would actually do for every task in a plan, produced from the plan text alone with no conversation history, no design doc, and no repository access. Readers commit to a reading rather than asking for clarification, because a swarm executor cannot ask. Prompt template in [skills/engineering/plan-scrutiny/cold-read-protocol.md](skills/engineering/plan-scrutiny/cold-read-protocol.md).

**Divergence** — Two cold readers describing incompatible work for the same task: different files, different actions, or different completion conditions. Divergence is the evidence that a task is ambiguous; a reviewer's opinion that a task "reads unclear" is not. Classified per task as `CONVERGENT`, `SPLIT`, or `HEDGED`.

**Invention** — A detail a cold reader supplied that the plan never stated (a file path, a test location, an ordering). Readers must declare inventions explicitly. Readers inventing *different* values for the same task is a `SPLIT` even when their stated actions match.

**STE audit** — The mechanical pass in `plan-scrutiny` that checks plan prose against a nine-rule subset of ASD-STE100 Simplified Technical English. It produces candidate violations, never findings — a violation only counts once the panel diverges there. Rules in [skills/engineering/plan-scrutiny/ste-rules.md](skills/engineering/plan-scrutiny/ste-rules.md).

**Validation gate** — The calling agent's job of executing every script and fetching every URL produced by verification agents before accepting their findings. Procedure in [skills/engineering/implementation-scrutiny/validation-gate.md](skills/engineering/implementation-scrutiny/validation-gate.md).

**Invariant** — A concrete, falsifiable statement about what should be true after the code under scrutiny runs (e.g., "cart.items.length equals successful adds minus successful removes"). Comes from spec or intent, not from what the code currently does.

**Synthesis** — The calling agent's job (not the panel's) of extracting mechanisms from agent outputs, clustering by approach, and presenting structured options to the user. Two phases: extract+cluster, then present.

**Tier** (creative-consensus output) — One of `conservative` (proven, low risk), `moderate` (novel but grounded), `ambitious` (high risk, high reward). The skill presents three tiers, never one blended pick.

**Verdict** (implementation-scrutiny output) — One of `STOP`, `PROCEED WITH CAUTION`, `CLEAN` — communicates the top-level finding to the user, followed by the detailed coverage map.

**Verdict** (plan-scrutiny output) — One of `REWRITE` (a third or more of tasks split), `PATCH` (isolated splits), `READY` (no splits) — opens the report, followed by the per-task divergence table and the coverage map.

**Loop** — a producer (`pr` / `jira` / `vuln`) or the dispatcher, each running as its own cron-armed background session.

**Inbox** — a logical category of tasks for one source: `prs`, `tickets`, or `vulns`. The three inboxes share a single `tasks/` directory; the `inbox:` frontmatter field on each task file says which logical inbox it belongs to. Not a queue file anymore.

**Task file** — one markdown file per task at `<inbox-dir>/tasks/<kind>-<key>.md`. Metadata lives in YAML frontmatter (including `inbox`, `kind`, `key`, `status`, `created`, `due`, `refreshed`, `linked`, `via`). Body is for kind-specific extras — vuln task files add `## Taint` and `## Repro` sections. Dedup is filename existence: if `<kind>-<key>.md` already exists, the loop skips creating a new one.

**Kanban base** — the Obsidian Bases YAML file at `<inbox-dir>/inbox-kanban.base`. Queries the `tasks/` directory and renders three views: Board (group by `status`), Table (all fields), and Done-log (filtered to `status: done`). Replaces the old grep-and-section-anchor model.

**Status** — frontmatter enum with five values: `new` (loop just created it), `claimed` (dispatcher has assigned it to a consumer), `progress` (consumer is working), `blocked` (consumer needs input), `done` (consumer finished). Drives the kanban column the task renders in. Watch for: silent stalls — a task stuck on `claimed` for more than one dispatcher cycle is a dropped consumer, not normal.

**Frontmatter ownership** — strict transition rules per role. Loops own `new` (create) and `done` (auto-close on resolution upstream). Dispatcher owns `claimed` (only it sets `new → claimed`). Consumer owns `progress`, `blocked`, and `done` for tasks it was claimed for. No role edits another role's fields. Watch for: cross-writes — a dispatcher rewriting `progress` back to `claimed` is a bug, not a recovery.

**Consumer** — a worker subagent the dispatcher spawns (via the `Agent` tool) to process one task file; posts PENDING reviews only, never submits.

**Dispatcher** — the router loop; reads `status: new` task files, buckets each into `auto` / `escalate` / `both`, sets `status: claimed`, and fans out consumers in parallel, capped per cycle.

**Self-rearm** — each loop re-creating its own durable cron near the 7-day expiry so it stays live indefinitely.

**inbox-dir** — the self-contained directory a setup run materializes. Contents: `config.yaml`, `tasks/` (one markdown file per task, all three inboxes mixed), `inbox-kanban.base` (Obsidian Bases view file), and a copy of the loop docs.

## Anti-terms

These phrasings drift away from the skills' intent. Avoid them in SKILL.md, agent prompts, and findings reports.

- **"Best idea" / "recommendation"** — the skills present options; the user picks. Don't imply the skill chose.
- **"Tests passed"** — that only proves "this angle found nothing." Use coverage-map framing.
- **"Verified correct"** — there is no such verdict. Present what was checked, not what's correct.
- **"Step N"** — workflow headings are numbered (`### 1. Frame the problem`), not labeled with `Step`.
