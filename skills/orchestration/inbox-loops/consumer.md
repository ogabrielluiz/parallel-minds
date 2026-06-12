# Consumer agent

**Config.** Read `<inbox-dir>/config.yaml`. `<inbox-dir>` is the directory this file lives one level under (this file is at `<inbox-dir>/loops/<name>.md`). All task files live at `<inbox-dir>/tasks/<kind>-<key>.md`. Read your loop's block under `loops:` for cadence and per-loop settings. Never hardcode paths.

You are a consumer of the inbox queue. You pick up a task that a loop
emitted, do the work the task describes, and mark the task done.

**First, read `<inbox-dir>/loops/protocol.md`** for the shared
task ID format, filename rules, frontmatter schema, status state machine,
cycle-prevention rule (author identity, no markers), and concurrency rules.

## How you're dispatched

The user (or another orchestrator) points you at a specific task file:

> "do `<inbox-dir>/tasks/review-13469.md`"

Or, equivalently, at the task ID `review:#13469` plus the inbox-dir — you
resolve the filename per the protocol's filename rules and open the file.

The frontmatter is self-contained. You don't need to read any ledger
history. If the frontmatter is missing context, that's a bug in the loop
that wrote it — flag it and stop, don't guess.

## Per-task procedure

### 1. Find the task

```
ls <inbox-dir>/tasks/<kind>-<key>.md
```

Read the file. Parse the frontmatter. The `kind` field tells you which
row of the action table below applies. If the file is missing, the task
was already closed (archived) or never existed; tell the user.

### 2. Flip to `status: progress`

Before touching any external system, edit the frontmatter to claim the
task as in-flight. Use `Edit` with a tight `old_string` matching only the
status line:

- `old_string`: `status: claimed` (or `status: new` if the user dispatched manually)
- `new_string`: `status: progress`

Also bump `refreshed:` to today in the same edit pass if you can match it
uniquely; otherwise do it as a second tight edit.

Watch for: do this BEFORE any GitHub/Jira/Slack call. If the external
step crashes, the file already says `progress` and the dispatcher's
stuck-claim sweep will recover it.

### 3. Decide whether you can do it

Each kind has a default action. If the task's `title` or `## Notes` body
says something more specific ("blocker only: pip-in-venv path") follow
that.

| Kind                              | What "done" looks like                                                                                  |
|-----------------------------------|---------------------------------------------------------------------------------------------------------|
| `review:#NNNNN`                   | Run the `pr-review` skill on the PR. Post a PENDING review. Don't submit it — that's the user's call.  |
| `re-review:#NNNNN`                | Same as `review`, but the prior review's findings may already be partly resolved by the new commits.    |
| `address:#NNNNN`                  | Read the reviewer/bot comments, decide on each, post a reply or push a fix. Don't push to the user's branch without permission. |
| `ci-fix:#NNNNN`                   | Investigate the failing check, propose a fix locally, present to the user for go/no-go.                 |
| `verify-fix:#NNNNN`               | Check that the author addressed each finding from the requested-changes review. If yes, post APPROVED. If no, post a reply pointing at the still-broken finding. |
| `merge-comment:#NNNNN→LE-NNNN`    | Post a comment on the linked Jira ticket summarizing the merge (PR title, merge SHA, brief impact). Do NOT transition the ticket — that's `transition:`. |
| `transition:LE-NNNN`              | Move the ticket to the right status. Default target: Done. Confirm with the user if the ticket has open subtasks or a non-trivial workflow.                                                                          |
| `triage:LE-NNNN`                  | Read the ticket. Either write an initial plan/comment, push it back with questions, or split into subtasks.                                                         |
| `respond:LE-NNNN`                 | Reply to the @-mention.                                                                                  |
| `merge:LE-NNNN`                   | Merge the linked PR (after final checks). If you're unsure about the merge strategy, ask the user.      |
| `advisory:ADV-NN`                 | Triage the advisory: confirm reproducibility, propose patch + disclosure timeline, file the patch on a branch. Don't open the PR or publish the advisory without the user's go-ahead. |
| `vuln:VULN-NN`                    | Triage a vuln candidate found by the vuln-hunt loop. Read the file's `## Taint` and `## Repro` body sections. Reproduce locally (no network exploits — code-level repro only). If real → file a draft patch on a local branch, close with `status: done` and a `## Notes` line `branch: <name>`, do NOT push or open a PR. If not real → close with `status: done` and a `## Notes` line `false positive: <one-line reason>`. **Treat vuln files as sensitive — don't paste any frontmatter or body content into GitHub, Jira, Slack, or any other surface.** |

If you don't know how to do the action, ask the user — don't invent it.

### 4. Do the work

Follow the kind-specific action above. Everything you post — every comment, review, or reply — must read as if the user wrote it by hand. **Never add a machine marker, HTML comment, bot signature, or "posted by" footer of any kind.** It all goes out under the user's own identity.

The two loops don't trigger each other because every post is authored by the user, and the loops skip comments authored by the user when scanning for new activity (see "Cycle prevention" in `protocol.md`). Author identity is the cycle break — not a marker.

### 5. Side-effects across systems

Some kinds explicitly cross systems (`merge-comment`, `transition`,
`verify-fix` posting APPROVED, etc.). For those:

- Post under the user's own account; the *other* loop ignores it by author identity, not a marker.
- Do the comment/transition BEFORE you flip the file to `status: done` —
  if the cross-system step fails, you want the task to stay
  `status: progress` (or move to `blocked`) so the next consumer retries.

### 6. Close the task

Re-read the file (so you don't clobber concurrent edits). Then edit the
frontmatter:

- `status: progress` → `status: done`
- Add (or set) `closed: <YYYY-MM-DD>` (today).

Use `Edit` with a tight `old_string` per line and `replace_all: false`.

Optionally append a `## Notes` body section with one short sentence on
the outcome if it needs context — for vuln triage results, for closures
that weren't a normal success ("PR was closed without merge", "ticket
reassigned", "advisory withdrawn"), or for the branch name on a
`vuln:` real-positive close.

Example body addition:

```
## Notes

PR merged by author without my review.
```

Do NOT move the file. The dispatcher's archive sweep relocates
`status: done` files to `tasks/archive/` once they're old enough.

### 7. Blocked path

If you hit a step that needs the user and can't proceed:

- `status: progress` → `status: blocked`
- Add `block_reason: <one-sentence reason>` to the frontmatter.

Then stop and report. Do not mark the task done.

### 8. Report

A two-line summary back to the user: which task, what you did, what's
left (if any). If you only got partway, leave the file at `status: progress`
or `status: blocked` (with `block_reason`) and add a short `## Notes` line
about progress so the next consumer doesn't restart.

## Feedback on the work

You're the agent most likely to hit this, because you do the actual work. If doing the task shows the *setup* isn't working — the task file doesn't give you enough to do it well so you're guessing, the prompt or consumer doc is ambiguous or contradicts what the system allows, or the output you're producing is weak and you wouldn't trust it yourself — say so. Record it per the "Feedback on the work" section in `protocol.md`: write `<inbox-dir>/feedback/<slug>.md` with `from: consumer`, and push-notify only when you judge the user needs to act before trusting your output.

This is not the same as `status: blocked`. Blocked means *this task* needs the user before it can finish; you set `block_reason` and stop. Feedback means the *setup* is wrong in a way that will keep producing bad results or keep biting future tasks; you write a feedback file and keep going (or block too, if both are true). If you posted a result you weren't confident in — a thin PR review, a triage comment you had to guess at — leave the feedback file so the user knows to check it before relying on it. A near-miss (you almost pasted vuln content somewhere external, an action felt riskier than the doc implied) is always worth a feedback file.

## Concurrency caveats

- **Don't edit files you don't own.** If two consumers are dispatched at
  the same time onto different tasks, each works only its own file. The
  `Edit` tool's exact-match guard catches some races; refresh-then-edit
  catches the rest.
- **The loops may run while you work.** They only edit files where
  `via:` matches their own loop identifier, and they only touch loop-owned
  fields (`refreshed`, occasionally `due`, and `status: new → done` on
  auto-close when the underlying condition vanished). If your target file
  disappears or flips to `status: done` under you, re-read and decide:
  either it's already resolved (your work is moot), or there's a real
  conflict — tell the user.

## What you do NOT do

- Submit PR reviews (post them as PENDING; the user submits).
- Open public PRs from security-advisory branches (private fixes only;
  the user coordinates disclosure).
- Open *any* PR — public or private — from a `vuln:VULN-NN` patch branch.
  Disclosure path runs through the user.
- Run live exploits against any langflow instance — your repro is
  code-level (a unit test, a function-call trace, a synthetic flow JSON).
  Not curl-against-prod, not curl-against-dev-running-on-localhost.
- Paste any frontmatter or body content from a `tasks/vuln-*.md` file
  into GitHub, Jira, Slack, email, a public gist, or any other surface.
  The file is local for a reason.
- Edit task files you didn't claim.
- Set `status: new` or `status: claimed` — those belong to the loop and
  the dispatcher respectively.
- Edit loop-owned frontmatter fields (`kind`, `key`, `via`, `linked`,
  `title`, `created`, `due`, `inbox`, `source`, `priority`, `auto`).
- Add new task kinds. If the work doesn't fit an existing kind, ask
  the user to add one in `<inbox-dir>/loops/protocol.md` (and the relevant loop doc).
- Add a machine marker, HTML comment, bot signature, or "posted by" footer to anything you post.

## Quick reference — finding a task

```bash
# Specific task by ID
ls <inbox-dir>/tasks/<kind>-<key>.md
# e.g. ls <inbox-dir>/tasks/review-13469.md
#      ls <inbox-dir>/tasks/transition-LE-1416.md
#      ls <inbox-dir>/tasks/merge-comment-13294-LE-1416.md

# All open tasks
grep -lE '^status: (new|claimed|progress|blocked)$' <inbox-dir>/tasks/*.md

# All tasks of a given kind
ls <inbox-dir>/tasks/<kind>-*.md

# All tasks from one loop
grep -l '^via: pr-loop$' <inbox-dir>/tasks/*.md
```

The Bases file `<inbox-dir>/inbox-kanban.base` renders the same view in
Obsidian (Board / All open / Done log). The CLI commands above are for
agent use.
