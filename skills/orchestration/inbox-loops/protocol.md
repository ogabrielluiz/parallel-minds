# Inbox loops protocol

**Protocol version: 1.5.0.** This is the single source of truth for the docs' version. Each loop's reconcile step reads this line and echoes it in the cycle report (`protocol v1.5.0`), so you can tell from a report which version of the docs a running loop is actually on — not just which version is on disk. Bump this line (and the materialized copy under `<inbox-dir>/loops/`) whenever these docs change materially; keep it in step with the plugin `version` in `.claude-plugin/plugin.json`.

This file is the shared contract every inbox-loops agent reads — loops, dispatcher, and consumers all follow it. Background, philosophy, and the "why" live in [CONTEXT.md](./CONTEXT.md); this file only spells out the storage model, IDs, and rules. Per-user settings (inbox-dir path, credentials, cadence overrides, archive window) live in `<inbox-dir>/config.yaml`.

Tasks are stored one-file-per-task under `<inbox-dir>/tasks/`. An Obsidian Bases file at `<inbox-dir>/inbox-kanban.base` renders the queue as a kanban board, an "all open" table, and a done log by querying that directory.

## What each doc does

| Doc                       | Who reads it                            | What they produce                                            |
|---------------------------|-----------------------------------------|--------------------------------------------------------------|
| `protocol.md` (this file) | All agents — shared protocol            | —                                                            |
| `pr-loop.md`              | The PR loop agent (one session)         | Task files under `tasks/` with `via: pr-loop`                |
| `jira-loop.md`            | The Jira loop agent (one session)       | Task files under `tasks/` with `via: jira-loop`              |
| `vuln-loop.md`            | The vuln-hunt loop agent (one session)  | Task files under `tasks/` with `via: vuln-loop` (sensitive)  |
| `dispatcher.md`           | The dispatcher loop (one session)       | `status: claimed` transitions, consumer dispatches, push notifications |
| `consumer.md`             | Worker agents (any session)             | `status: progress` / `blocked` / `done` transitions plus side-effects |

## Task ID format

```
<kind>:<key>
```

The ID identifies the task across emissions. Same `kind:key` means the same task, regardless of when it was emitted or by which loop. The ID is stored in frontmatter as `kind` and `key` and is also embedded in the filename.

### Kinds

| Kind                              | Meaning                                                  | Emitted by      |
|-----------------------------------|----------------------------------------------------------|-----------------|
| `review:#NNNNN`                   | review the PR                                            | PR or Jira loop |
| `re-review:#NNNNN`                | author pushed since I reviewed, re-review                | PR or Jira loop |
| `address:#NNNNN`                  | my PR, reviewer/bot left feedback to address             | PR loop only    |
| `ci-fix:#NNNNN`                   | my PR, CI failing                                        | PR loop only    |
| `verify-fix:#NNNNN`               | I requested changes, check they actually landed          | PR loop only    |
| `merge-comment:#NNNNN→LE-NNNN`    | PR merged, post merge note on linked Jira ticket         | PR or Jira loop |
| `transition:LE-NNNN`              | move Jira status to match reality (PR merged etc.)       | Jira loop only  |
| `triage:LE-NNNN`                  | new ticket assigned, look at it                          | Jira loop only  |
| `respond:LE-NNNN`                 | new comment by someone else on a ticket that's mine (assignee/reporter) or @-mentions me, reply | Jira loop only  |
| `activity:LE-NNNN`                | activity on an issue I'm involved in but not mine to answer (epic child created/changed, ticket I created reassigned/moved, comment on a ticket I only watch) — awareness | Jira loop only  |
| `merge:LE-NNNN`                   | ticket is "Ready to Merge", merge its PR                 | Jira loop only  |
| `advisory:ADV-NN`                 | published security advisory needing triage               | PR loop only    |
| `vuln:VULN-NN`                    | vulnerability candidate found by code review (sensitive) | Vuln loop only  |
| `mention:LE-NNNN`                 | @-mention pointed at me on a ticket                      | Jira loop only  |

If you need a new kind, add it here and in the relevant loop docs before emitting.

## Filename scheme

Every task is stored at `<inbox-dir>/tasks/<filename>.md`. The filename is derived from `<kind>:<key>` deterministically so any agent can compute it from the ID without ambiguity.

Given the task ID `<kind>:<key>`:

1. Take `<kind>` verbatim. Kinds in the whitelist above are already filesystem-safe.
2. Take `<key>` and apply these transforms in order:
   - Replace the right-arrow `→` (U+2192) with `-` (ASCII hyphen).
   - Strip every `#` character.
   - Replace any remaining whitespace with `-`.
   - All other characters (letters, digits, `-`, `_`, `.`, `:`) are kept as-is.
3. Join with a single `-`: `<kind>-<transformed-key>.md`.

Worked examples:

| Task ID                              | Filename                                  |
|--------------------------------------|-------------------------------------------|
| `review:#13379`                      | `review-13379.md`                         |
| `re-review:#13379`                   | `re-review-13379.md`                      |
| `address:#13294`                     | `address-13294.md`                        |
| `ci-fix:#13294`                      | `ci-fix-13294.md`                         |
| `verify-fix:#13294`                  | `verify-fix-13294.md`                     |
| `merge-comment:#13294→LE-1416`       | `merge-comment-13294-LE-1416.md`          |
| `transition:LE-1416`                 | `transition-LE-1416.md`                   |
| `triage:LE-1416`                     | `triage-LE-1416.md`                       |
| `respond:LE-1416`                    | `respond-LE-1416.md`                      |
| `activity:LE-1503`                   | `activity-LE-1503.md`                     |
| `merge:LE-1416`                      | `merge-LE-1416.md`                        |
| `advisory:ADV-07`                    | `advisory-ADV-07.md`                      |
| `vuln:VULN-01`                       | `vuln-VULN-01.md`                         |
| `mention:LE-1416`                    | `mention-LE-1416.md`                      |

Reverse mapping: kinds form a closed set. Parse with longest-match-first against the whitelist (`merge-comment`, `verify-fix`, `re-review`, `ci-fix`, then single-token kinds). The remainder is the key. `→` and `#` are not re-derived from the filename — `linked` and `key` in frontmatter carry them explicitly.

Watch for: two emissions producing the same filename are the same task. Loops never append a numeric suffix to "make a new file" — dedup handles it (see Concurrency rules below).

## Frontmatter schema

Every task file is a markdown document with a YAML frontmatter block. The body is optional except for `vuln:` (see "Body content per kind").

| Field          | Type    | Required                          | Allowed values / format                                       | Owner (who writes)                  |
|----------------|---------|-----------------------------------|---------------------------------------------------------------|--------------------------------------|
| `kind`         | string  | required                          | one of the kind whitelist                                     | emitting loop                        |
| `key`          | string  | required                          | the raw `<key>` portion of the task ID (incl. `#` if present) | emitting loop                        |
| `status`       | string  | required                          | `new` / `claimed` / `progress` / `blocked` / `done`           | see state machine                    |
| `via`          | string  | required                          | `pr-loop` / `jira-loop` / `vuln-loop`                         | emitting loop                        |
| `linked`       | string  | required                          | cross-system reference (`LE-1416`, `#13294`) or `none`        | emitting loop                        |
| `title`        | string  | required                          | one-line, self-contained                                      | emitting loop                        |
| `created`      | date    | required                          | `YYYY-MM-DD`, first emission date, never changes              | emitting loop                        |
| `due`          | date    | required                          | `YYYY-MM-DD`, soft due date                                   | emitting loop (may bump on refresh)  |
| `refreshed`    | date    | required                          | `YYYY-MM-DD`, last cycle that re-confirmed the task is open   | emitting loop (every cycle)          |
| `closed`       | date    | optional                          | `YYYY-MM-DD`, set when `status: done`                         | consumer (or loop on auto-close)     |
| `source`       | string  | optional (required for `vuln`)    | free text describing how the task was found                   | emitting loop                        |
| `priority`     | string  | optional                          | `low` / `medium` / `high` / `critical`                        | emitting loop                        |
| `auto`         | string  | optional                          | `ok` / `hold` / `done` (user override)                        | user (hand edit)                     |
| `block_reason` | string  | required when `status: blocked`   | free text, one sentence                                       | consumer (or user)                   |
| `inbox`        | string  | required                          | `prs` / `tickets` / `vulns` (which legacy inbox owns it)      | emitting loop                        |
| `attack`       | string  | required for `vuln` kind          | `timing` / `rce` / `ssrf` / `path-traversal` / `auth-bypass` / etc. — short attack class | vuln-loop                            |
| `repro`        | string  | required for `vuln` kind          | `low` / `med` / `high` — reproduction difficulty (low = easy) | vuln-loop                            |
| `file_ref`     | string  | required for `vuln` kind          | `<path>:<line>` — canonical code location for the finding     | vuln-loop                            |

Notes:

- `key` keeps the `#` for PR numbers (e.g. `#13379`) so the displayed ID round-trips cleanly. The filename strips it.
- `linked` is a single string. For `merge-comment` tasks that bridge a PR and a Jira ticket, the bridged side goes into `linked` (`linked: LE-1416` on a PR-loop emission, `linked: '#13294'` on a Jira-loop emission). The other side is encoded in `key`.
- `auto` is the per-task override the dispatcher honors. It moves from being an inline annotation on the task line to a frontmatter field; `auto: ok` forces auto-dispatch, `auto: hold` forces escalation, `auto: done` tells the dispatcher to leave the task alone.
- `attack`, `repro`, `file_ref` are vuln-only. On non-vuln tasks they should be absent from the frontmatter, not present-and-empty.

## Status state machine

Status is a first-class frontmatter field. Five values, strict ownership. Loops own `new` (and `done` on auto-close), dispatcher owns `claimed`, consumer owns `progress` / `blocked` / `done`.

| Value      | Meaning                                                                       |
|------------|-------------------------------------------------------------------------------|
| `new`      | Loop emitted it. No one has picked it up.                                     |
| `claimed`  | Dispatcher picked it up and spawned a consumer subagent.                      |
| `progress` | Consumer is actively working it.                                              |
| `blocked`  | Consumer (or the user) flagged it as needing human input. `block_reason` set. |
| `done`     | Work finished. `closed` set.                                                  |

Allowed transitions:

| From       | To         | Trigger                                                                | Owner          |
|------------|------------|------------------------------------------------------------------------|----------------|
| (absent)   | `new`      | Loop emits a new task file                                             | loop           |
| `new`      | `claimed`  | Dispatcher routes the task to a consumer                               | dispatcher     |
| `claimed`  | `progress` | Consumer picks the task up                                             | consumer       |
| `claimed`  | `new`      | Stuck-claim sweep: `refreshed` older than 4h while still `claimed`     | dispatcher     |
| `progress` | `blocked`  | Consumer hits a step requiring human input; sets `block_reason`        | consumer       |
| `progress` | `done`     | Consumer finishes; sets `closed: <today>`                              | consumer       |
| `blocked`  | `progress` | Human unblocked; consumer resumes                                      | consumer       |
| `blocked`  | `done`     | Consumer (or user) closes blocked task as resolved                     | consumer/user  |
| `new`      | `done`     | Loop auto-closes: underlying condition vanished                        | loop           |
| any open   | `blocked`  | User manually flags from outside the workflow                          | user           |

Watch for: nobody other than the emitting loop or dispatcher may move a task back into `new`. Consumers never resurrect tasks; if a consumer was wrong to close, the loop re-emits on the next cycle (which creates the same filename and bumps `refreshed`).

## Body content per kind

The frontmatter carries the metadata. The body carries kind-specific extras and is usually empty.

**Vuln files require two body sections, in this order:**

```
## Taint

<2-3 sentence trace: input here → flows through here → lands in sink here, no check>

## Repro

<2-sentence reproduction sketch>
```

The vuln loop refuses to emit a `vuln:VULN-NN` task without both sections. These are the only mandatory body sections in the entire system.

**All other kinds — body is optional.** If a consumer or the user wants free-text scratchpad context (in-progress notes, "phin asked to split into a separate commit", etc.), it goes under a `## Notes` section. Empty body is the default. Loops do not write to the body for non-vuln kinds — only the consumer or the user does.

Watch for: no body section other than `## Taint`, `## Repro`, and `## Notes` is allowed. Anything else belongs in frontmatter (as a new field) or in a separate doc. The body is intentionally restricted so the Bases queries stay predictable and the body doesn't drift into "another inbox".

## Cycle prevention

Never inject any machine marker, HTML comment, or bot signature into a comment, review, or post. Everything the loops and consumers post must read as if the user wrote it by hand — no `<!-- ... -->` tags, no "posted by bot" footers, nothing.

The cycle "PR merged → bot posts a Jira comment → Jira loop sees activity → emits `respond` → posts a GitHub comment → PR loop sees activity → ..." is broken by **author identity**, not by markers. Every comment a loop or consumer posts goes out under the user's own GitHub login / Jira account. So when a loop scans for "new activity that needs a response":

- The `respond:` scan looks for comments **mentioning the user, authored by someone else**, after the user's last activity. A comment the bot posted as the user is the user's own activity — it advances the "last activity" timestamp and never mentions the user, so it can't trigger a `respond:` to the user themselves.
- The `address:` scan looks for reviewer/bot feedback on the user's PRs after the user's last activity. A comment the bot posted as the user is the user's activity, so it's skipped the same way.

In both scans the rule is now: **skip any comment authored by the user's own identity** (`loops.pr.github_login` for GitHub, the configured Jira account for Jira). That is the cycle break. No marker needed, nothing visible ever lands in a comment.

## Directory layout

Everything lives in `<inbox-dir>/`, the directory chosen at setup (recorded as `inbox_dir` in `config.yaml`).

```
<inbox-dir>/
├── config.yaml                       # per-user settings (inbox_dir, credentials, cadence, archive window)
├── inbox-kanban.base                 # Obsidian Bases file — Board / All open / Done log views over tasks/
├── tasks/                            # one file per task — active and recently closed
│   ├── review-13379.md
│   ├── re-review-13412.md
│   ├── address-13294.md
│   ├── ci-fix-13388.md
│   ├── vuln-VULN-01.md
│   ├── ...
│   └── archive/                      # closed tasks aged out (status: done, closed > archive_after_days ago)
│       ├── review-13201.md
│       └── ...
├── feedback/                         # one file per process-feedback topic (see "Process feedback")
│   └── pr-cadence-too-aggressive.md
└── loops/                            # agent docs
    ├── protocol.md                   # this file
    ├── pr-loop.md
    ├── jira-loop.md
    ├── vuln-loop.md
    ├── dispatcher.md
    └── consumer.md
```

The Bases file replaces the old `#section-anchors` model entirely. There are no more `{#pr-reviews}`, `{#jira-triage}`, `{#vuln-active}`, `{#done}` anchors — those slices are now Bases filters over `tasks/` frontmatter (e.g. `note.kind == "triage"`, `note.status == "done"`, `note.due < date("today")`).

`tasks/vuln-*.md` are local-only, same sensitivity bar as the legacy `inbox-vulns.md`: don't surface their contents to any external system without explicit go-ahead from the user. Disclosure runs through the user, not through the inbox.

## Concurrency rules

Multiple loops, the dispatcher, and N consumers all touch `tasks/` simultaneously. The rules that keep edits from racing:

1. **Each loop only creates or updates files for tasks it owns by `via:`.** PR loop only writes files where `via: pr-loop`. Jira loop only writes files where `via: jira-loop`. Vuln loop only writes files where `via: vuln-loop`. A loop that finds a task it didn't emit (different `via:`) leaves it alone.
2. **Dedup is filename existence.** Before emitting, the loop computes the filename and checks `tasks/<filename>.md`. If it exists and `via:` matches, bump `refreshed` to today and leave everything else alone. If it exists and `via:` differs, leave the file alone — the other loop owns it. If it doesn't exist, create it with `status: new`. A file under `tasks/archive/` counts as absent; create a fresh `tasks/<filename>.md`.
3. **The dispatcher only writes `status: claimed` (and the stuck-claim revert to `new`).** It never touches `progress`, `blocked`, `done`, `closed`, `block_reason`, or the body.
4. **The consumer only writes `status`, `closed`, `block_reason`, and the body of the file it claimed.** It never edits `kind`, `key`, `via`, `linked`, `title`, `created`, `due`, `inbox`, `source`, `priority`, or `auto`.
5. **Re-read the file before any edit. Don't cache.** Frontmatter may have changed between when the loop listed `tasks/` and when it writes.
6. **Dedup never reads the body.** A vuln task's `## Taint` is sensitive; the dedup path only loads frontmatter.

Watch for: if you need to do many edits to the same file, do them in one `Edit` call with `replace_all: false` and a tight `old_string`, not a `Write` that replaces the whole file.

## Self-updating loops (no restart for doc/config edits)

A loop session runs for days. Its context caches whatever it read at spawn — so editing a loop doc or `config.yaml` on disk does **not**, by itself, change a running loop's behavior. The fix is the cron prompt.

The cron prompt is the only text re-delivered *fresh* to a long-running session every cycle (it's re-injected at each fire; it can't be cached). So each loop's cron prompt is **reconcile-first**:

> Re-read `<inbox-dir>/loops/<loop-doc>` and `<inbox-dir>/loops/protocol.md` fresh from disk, then run one `<loop>` cycle following them.

Because of that, every cycle starts by re-reading the docs from disk, and each loop's `### 0. Reconcile` step then re-reads `config.yaml` and re-arms its own cron (`CronDelete` + `CronCreate`) if the cadence changed. Net effect: **edit a doc or config, save it, and the change lands on each loop's next cycle — no restart.**

The one thing this can't do is force an *immediate* refresh before the next scheduled cycle. Claude Code blocks injecting a message into a live background session, so the floor is "propagates on the next cycle." If you need it sooner, restart the session.

This mechanism is installed by the cron prompt set at spawn (see SKILL.md step 5). A loop spawned with an older, non-reconcile cron prompt won't self-update until it's respawned once with the reconcile-first prompt; from then on it sustains itself, including upgrading its own cron prompt if it ever finds an older form (per `### 0. Reconcile`).

## Feedback on the work (tell the user when the setup isn't working)

The loops, dispatcher, and consumers run unattended for days, working from prompts, task files, and config the user wrote once and then walked away from. When the work itself starts going wrong — the instructions are steering you wrong, you don't have enough to go on, the output you're producing is weak, or the loop is spinning without producing anything useful — **say so.** This is the channel for telling the user "the way you set this up isn't working," so they can fix the prompt or the config instead of trusting a pile of bad results. Don't silently absorb it and don't paper over it by guessing.

What belongs here (this is feedback, not a task to work):

- **The prompt or task file is steering you wrong** — unclear, contradictory, or asking for something that doesn't match reality. ("The consumer doc says post APPROVED on `verify-fix`, but I can't tell from the task file what findings I'm verifying against.")
- **Not enough information to do it well, so you're guessing** — a task file missing context, a config value you needed and didn't have, an ambiguous ask. Flag the gap instead of inventing an answer.
- **The results you're producing are weak or low-confidence** — say it before the user relies on them. ("I posted three PENDING reviews this cycle and wasn't confident in any of them; the diffs were larger than I could review well in one pass.")
- **The process isn't being productive** — many cycles, little useful output; the loop keeps emitting tasks that go nowhere; effort spent is out of proportion to what comes out. ("The vuln loop has run 12 cycles and every candidate has been a false positive; the rotation may be pointed at the wrong code.")
- Anything where, if the user were watching the run, they'd want to stop you and adjust the setup.

### How to record it

Feedback is one file per topic at `<inbox-dir>/feedback/<slug>.md`, where `<slug>` is a short kebab-case description (e.g. `pr-cadence-too-aggressive`, `vuln-kind-needs-severity-field`).

```yaml
---
from: <pr-loop | jira-loop | vuln-loop | dispatcher | consumer>
created: <YYYY-MM-DD>
severity: low | medium | high
notified: false
about: <one-line topic>
---

What you noticed, why it matters, and the change you'd suggest if you have one.
A few sentences. This is for the user to read, not for another agent to parse.
```

`severity` is your own read of how much it matters:

- `low` — a small information gap or slightly-below-par output. An FYI. Worth writing down, not worth interrupting the user.
- `medium` — the work is degraded: you're guessing on real decisions, or output quality is dropping. The user should see it on their next pass.
- `high` — the setup is actively producing bad results or burning cycles for nothing. The user needs to act before trusting more output.

### When to push-notify

**Write the file every time. Send a push notification only when you judge the user should actually address it** — that's any `high`, and `medium` when it's actively costing something. `low` just sits in the file for the user to find. Don't push for things the user can read later; the push is for "this needs you."

When you do notify:

1. Fire one `PushNotification`, under 200 chars: `[inbox] feedback (<from>): <about>`. Never paste vuln details or anything sensitive — the push is a flag, the file is the record.
2. Set `notified: true` in the file's frontmatter so no agent re-pushes the same topic.

### Dedup and resolution

Before writing, `ls <inbox-dir>/feedback/` (treat a missing directory as empty). If a file with the same `<slug>` already exists and isn't resolved, **don't create a second one and don't re-notify** — at most add one line to its body if you have genuinely new information. One topic, one file, one push.

The user resolves feedback by reading and deleting the file (or moving it into `feedback/archive/`). Feedback files carry no `kind` or `inbox` field, so they never appear on the task kanban — this is a side channel to the user, not part of the work queue.

## What "needs action" means (the bar)

A task only enters the inbox if it's something **the user personally has to do or decide**. Not "the user might find this interesting". Not "the user is on the watcher list". The test:

> If I do nothing about this item for 2 days, does something measurably worse happen? (review goes stale, ticket misses sprint, advisory ages out of SLA, bot keeps re-pinging.)

If yes → emit. If no → don't.
