---
name: inbox-loops
description: Bootstrap and run the inbox-loops system — pick loops, configure them, materialize a self-contained inbox directory (file-per-task storage with an Obsidian Bases kanban view), and spawn one cron-armed background session per loop. Use when the user wants to set up, start, re-arm, check status of, or stop the PR / Jira / vuln / dispatcher inbox loops, or wants a kanban board of in-flight inbox work.
---

# inbox-loops

Sets up the inbox-loops system: gathers config interactively, materializes a self-contained inbox directory, and spawns one cron-armed background session per selected loop (PR, Jira, Vuln, Dispatcher). Each session arms its own durable cron and runs a first cycle immediately. Tasks are stored one-file-per-task under `tasks/`, with an Obsidian Bases file (`inbox-kanban.base`) rendering Board / Table / Done-log views over them.

> **Experimental.** This skill depends on undocumented Claude Code behavior: the `claude --bg` background-session mechanism and `CronCreate` scheduling. Crons are currently session-only (see step 6), so loops do not survive a restart without re-running setup. The storage model is file-per-task (one markdown file per task under `<inbox-dir>/tasks/`); the kanban is rendered by Obsidian's core **Bases** plugin from `<inbox-dir>/inbox-kanban.base`. Interfaces may change between Claude Code versions. Use it, but expect rough edges and verify with `claude agents --json` after setup.

### 1. Round 1 — scope

Ask (via `AskUserQuestion`):

1. Which loops to run — multi-select: **PR / Jira / Vuln / Dispatcher**.
2. The inbox directory path (free-text; no default — always ask; expand a leading `~` to an absolute path).
3. Whether to use durable crons (default yes).

Watch for: the inbox-dir has no default by design. Never assume one or fill it in from context.

### 2. Detect existing state

Run `claude agents --json` and parse the output for live session names `inbox-pr`, `inbox-jira`, `inbox-vuln`, `inbox-dispatcher`. Also check whether `<inbox-dir>` already contains `config.yaml`, a `tasks/` directory, an `inbox-kanban.base` file, or any legacy `inbox-*.md` files.

For each conflict (a loop is already running, or `config.yaml` / `tasks/` / `inbox-kanban.base` already exists), ask via `AskUserQuestion`:

- **keep** — leave the running session and files untouched; do not re-spawn.
- **restart** — stop the session with `claude stop <id>` (its session-only cron dies with it), then re-spawn fresh. (Future-proof: if a build starts persisting crons to `~/.claude/scheduled_tasks.json`, also remove the loop's entry there before re-spawning.)
- **skip** — don't touch anything; don't spawn.

Handle each conflicting loop independently.

Watch for: if any legacy `inbox-prs.md` / `inbox-tickets.md` / `inbox-vulns.md` files exist at `<inbox-dir>` AND `tasks/` does not exist, the directory is on the old line-based storage model. Stop and prompt the user (via `AskUserQuestion`) to run `<inbox-dir>/migrate-from-line-based.py` before proceeding. The script is idempotent and leaves the legacy files in place; once `tasks/` exists, re-run this skill. Do not auto-run the migration without consent.

### 3. Round 2 — per-loop config

Only for selected, non-skipped loops. Collect via `AskUserQuestion` per loop:

- **PR:** `repo` (owner/name), `github_login`, `cadence` (default `13 */3 * * *`).
- **Jira:** `project_key`, `jql_prefixes` (list), `cadence` (default `43 */3 * * *`).
- **Vuln:** `target_paths` (list), `rotation` (list, may be empty), `cadence` (default `33 */6 * * *`).
- **Dispatcher:** `consumer_cap` (default 5), `routing_overrides` (map, may be empty), `cadence` (default `23 * * * *`).

Watch for: warn if a chosen cadence shares the same minute offset as another selected loop. The staggered defaults (`:13` / `:43` / `:33` / `:23`) exist specifically to prevent simultaneous file-writes; custom cadences that share a minute offset will cause edit races across `tasks/`.

### 4. Materialize the inbox-dir

1. Write `<inbox-dir>/config.yaml` using the collected answers. Follow the shape in [templates/config.example.yaml](templates/config.example.yaml). Set `inbox_dir` to the absolute path.
2. `mkdir -p <inbox-dir>/tasks` and `mkdir -p <inbox-dir>/tasks/archive`. These hold the one-file-per-task storage and the aged-out done log.
3. Copy [templates/inbox-kanban.base.tmpl](templates/inbox-kanban.base.tmpl) to `<inbox-dir>/inbox-kanban.base` (only if absent). This is the Obsidian Bases file that renders the Board / Table / Done-log views.
4. `mkdir -p <inbox-dir>/loops` and copy [templates/task-template.md.tmpl](templates/task-template.md.tmpl) to `<inbox-dir>/loops/task-template.md`. Loops read this when emitting new task files.
5. Copy [templates/migrate-from-line-based.py](templates/migrate-from-line-based.py) to `<inbox-dir>/migrate-from-line-based.py` (always; it's safe to overwrite — the script is versioned with the skill).
6. Copy the six sidecars into `<inbox-dir>/loops/`: [protocol.md](protocol.md), [pr-loop.md](pr-loop.md), [jira-loop.md](jira-loop.md), [vuln-loop.md](vuln-loop.md), [dispatcher.md](dispatcher.md), [consumer.md](consumer.md).

Watch for: never overwrite a file the user chose to **keep** in step 2. The new model has no `inbox-prs.md` / `inbox-tickets.md` / `inbox-vulns.md` to create — those files belong to the legacy line-based model and are only present on directories that haven't migrated.

### 5. Spawn one session per selected loop

For each selected, non-skipped loop, run the command below. Substitute `<loop>` from `{pr, jira, vuln, dispatcher}`, the session name `inbox-<loop>`, `<cadence>` from config, and `<inbox-dir>`.

```bash
claude --bg -n "inbox-<loop>" --dangerously-skip-permissions \
  "Read <inbox-dir>/loops/<loop-doc> and follow it. It reads config from <inbox-dir>/config.yaml. CronCreate(cron='<cadence>', recurring=true, durable=true, prompt='Re-read <inbox-dir>/loops/<loop-doc> and <inbox-dir>/loops/protocol.md fresh from disk, then run one <loop> cycle following them.'). Then run one full cycle now."
```

**The cron prompt is reconcile-first by design.** It instructs the session to re-read its loop doc and `protocol.md` from disk *every* cycle, before doing any work. The cron prompt is the one piece of text re-delivered fresh to a long-running session each fire (everything else can be cached in the session's context), so putting "re-read the docs" there is what lets a doc or config edit propagate to a live loop on its next cycle — no restart needed. Each loop's `### 0. Reconcile` step then re-reads config and re-arms its own cron if the cadence changed.

The doc filename and loop name differ by loop:

| Loop        | `<loop-doc>`    | `<loop>` (in the cron prompt)  |
|-------------|-----------------|--------------------------------|
| `pr`        | `pr-loop.md`    | `pr-loop`                      |
| `jira`      | `jira-loop.md`  | `jira-loop`                    |
| `vuln`      | `vuln-loop.md`  | `vuln-loop`                    |
| `dispatcher`| `dispatcher.md` | `dispatcher`                   |

Note: the dispatcher's doc is `dispatcher.md`, not `dispatcher-loop.md`, and its loop name in the cron prompt is `dispatcher` (no `-loop` suffix).

Capture the short session id printed by each spawn.

Watch for: `--dangerously-skip-permissions` is mandatory. Without it the spawned session hangs indefinitely on the MCP-trust modal and never arms its cron.

### 6. Report

Print a summary table:

| Loop        | Session ID | Cadence        | Next fire (approx)  |
|-------------|------------|----------------|---------------------|
| pr          | `<id>`     | `13 */3 * * *` | (next :13 mark)     |
| jira        | `<id>`     | `43 */3 * * *` | ...                 |
| vuln        | `<id>`     | `33 */6 * * *` | ...                 |
| dispatcher  | `<id>`     | `23 * * * *`   | ...                 |

Note: each loop runs as long as its background session is alive (sessions are daemon-supervised and persist for days). Recurring crons auto-expire after 7 days, but each loop self-re-arms at the end of every cycle (see the Self-rearm section in each sidecar), so a long-lived session stays on indefinitely.

Watch for: crons are currently session-only. `durable: true` is accepted but this Claude Code build does not persist crons to `~/.claude/scheduled_tasks.json`, so a full restart or machine reboot drops both the sessions and their crons. To recover, re-run this skill: step 2 detects the missing loops and re-spawns them.

### 7. Status and stop

**Status:**

```bash
claude agents --json   # filter for names starting with "inbox-"
```

Inside any running session, call `CronList` to inspect that session's registered cron.

To inspect ongoing work, open `<inbox-dir>/inbox-kanban.base` in Obsidian. The Board view groups by `status` (`new` / `claimed` / `progress` / `blocked`), the All-open table is flat across kinds, and the Done log shows recently closed tasks. Raw task files live at `<inbox-dir>/tasks/<kind>-<key>.md` for direct grep/edit if needed.

**Stop:**

```bash
claude stop <id>       # for each inbox-* session
```

Crons are session-only on current builds, so stopping the session also drops its cron (nothing to scrub). If a future build starts persisting crons to `~/.claude/scheduled_tasks.json`, remove the loop's entry there too so it cannot fire into a dead session.
