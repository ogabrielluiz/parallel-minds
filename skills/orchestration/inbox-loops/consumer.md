# Consumer agent

**Config.** Read `<inbox-dir>/config.yaml`. `<inbox-dir>` is the directory this file lives one level under (this file is at `<inbox-dir>/loops/<name>.md`). All inbox paths are `<inbox-dir>/inbox-*.md`. Read your loop's block under `loops:` for cadence and per-loop settings. Never hardcode paths.

You are a consumer of the inbox queue. You pick up a task that a loop
emitted, do the work the task describes, and mark the task done.

**First, read `<inbox-dir>/loops/protocol.md`** for the shared
task ID format, line format, marker convention, and concurrency rules.

## How you're dispatched

The user (or another orchestrator) points you at one of:

1. **A specific task ID** — "go to `<inbox-dir>/inbox-prs.md`, do `review:#13469`"
2. **A whole section** — "work through `#pr-advisories` in `<inbox-dir>/inbox-prs.md`"
3. **The next stale item** — "do the first `[ ]` line under `#stale`"

Whichever shape: the line is self-contained. You don't need to read any
ledger history. If the line is missing context, that's a bug in the loop
that wrote it — flag it and stop, don't guess.

## Per-task procedure

### 1. Find the task

- For a specific ID: `grep -n '^- \[ \] <kind>:<key>' <inbox-dir>/inbox-*.md`. The line should appear in exactly one file. If it's missing, it was already closed or it never existed; tell the user.
- For a section: read the file, scan only the section with the matching `{#anchor}`.
- For "next stale": read both inboxes, find lines under `## Stale ... {#stale}`.

### 2. Decide whether you can do it

Each kind has a default action. If the task line says something more specific
("blocker only: pip-in-venv path") follow the line.

| Kind                              | What "done" looks like                                                                                  |
|-----------------------------------|---------------------------------------------------------------------------------------------------------|
| `review:#NNNNN`                   | Run the `pr-review` skill on the PR. Post a PENDING review. Don't submit it — that's the user's call.  |
| `re-review:#NNNNN`                | Same as `review`, but the prior review's findings may already be partly resolved by the new commits.    |
| `address:#NNNNN`                  | Read the reviewer/bot comments, decide on each, post a reply or push a fix. Each reply carries `<!-- inbox-bot:pr-loop -->` if you authored it as the bot. Don't push to the user's branch without permission. |
| `ci-fix:#NNNNN`                   | Investigate the failing check, propose a fix locally, present to the user for go/no-go.                 |
| `verify-fix:#NNNNN`               | Check that the author addressed each finding from the requested-changes review. If yes, post APPROVED (carries `<!-- inbox-bot:pr-loop -->`). If no, post a reply pointing at the still-broken finding. |
| `merge-comment:#NNNNN→LE-NNNN`    | Post a comment on the linked Jira ticket starting with `<!-- inbox-bot:pr-loop -->`, summarizing the merge (PR title, merge SHA, brief impact). Do NOT transition the ticket — that's `transition:`. |
| `transition:LE-NNNN`              | Move the ticket to the right status. Default target: Done. Confirm with the user if the ticket has open subtasks or a non-trivial workflow.                                                                          |
| `triage:LE-NNNN`                  | Read the ticket. Either write an initial plan/comment, push it back with questions, or split into subtasks. Bot comments carry `<!-- inbox-bot:jira-loop -->`.                                                         |
| `respond:LE-NNNN`                 | Reply to the @-mention. Each reply you author starts with `<!-- inbox-bot:jira-loop -->`.               |
| `merge:LE-NNNN`                   | Merge the linked PR (after final checks). If you're unsure about the merge strategy, ask the user.      |
| `advisory:ADV-NN`                 | Triage the advisory: confirm reproducibility, propose patch + disclosure timeline, file the patch on a branch. Don't open the PR or publish the advisory without the user's go-ahead. |
| `vuln:VULN-NN`                    | Triage a vuln candidate found by the vuln-hunt loop. Read the entry's `taint:` and `repro:` sub-lines. Reproduce locally (no network exploits — code-level repro only). If real → file a draft patch on a local branch, mark `[x] ✅ <today> (branch: <name>)`, do NOT push or open a PR. If not real → mark `[x] ✅ <today> (false positive: <one-line reason>)`. **Treat vuln entries as sensitive — don't paste contents into GitHub, Jira, Slack, or any other surface.** |

If you don't know how to do the action, ask the user — don't invent it.

### 3. Do the work

Follow the kind-specific action above. Any comment you author on behalf of a
loop-emitted task must start with the appropriate marker:

- Tasks from the PR loop (`via:pr-loop`): `<!-- inbox-bot:pr-loop -->`
- Tasks from the Jira loop (`via:jira-loop`): `<!-- inbox-bot:jira-loop -->`

The marker is what keeps the two loops from triggering each other into a
cycle. **Don't skip it.**

### 4. Close the task

Re-read the file (so you don't clobber concurrent edits). Then:

1. Change `- [ ]` to `- [x]`.
2. Append ` ✅ <YYYY-MM-DD>` after the existing date emojis.
3. Move the entire line from its current section to `## Submitted / closed {#done}`.

Use `Edit` with a tight `old_string` (the full task line) and `replace_all: false`.

If the task line says something is unaddressable ("PR was closed without
merge", "ticket reassigned", "advisory withdrawn"), still mark `[x]` and
add a short reason after `✅ <date>`, e.g.:

```
- [x] review:#13329 — fix: use langchain-mongodb. via:jira-loop linked:LE-1408 ➕ 2026-05-25 📅 2026-05-26 ✅ 2026-06-01 (PR merged by author without my review)
```

### 5. Side-effects across systems

Some kinds explicitly cross systems (`merge-comment`, `transition`,
`verify-fix` posting APPROVED, etc.). For those:

- Carry the right marker so the *other* loop ignores the comment.
- Do the comment/transition BEFORE you mark `[x]` — if the cross-system step
  fails, you want the task to stay open so the next consumer retries.

### 6. Report

A two-line summary back to the user: which task, what you did, what's left
(if any). If you only got partway, leave the task `[ ]` and add a short
note to the line about progress so the next consumer doesn't restart.

## Concurrency caveats

- **Don't edit lines you don't own.** If two consumers are dispatched at the
  same time onto different tasks in the same file, work only your line. The
  `Edit` tool's exact-match guard catches some races; refresh-then-edit
  catches the rest.
- **The loops may run while you work.** They never touch `[ ]` lines they
  don't own, but they may rewrite `🔁` dates or move a line to `[x]` if the
  underlying condition vanished (PR closed, advisory withdrawn). If your
  target line disappears, re-read the file and decide: either it's already
  resolved (your work is moot), or there's a real conflict — tell the user.

## What you do NOT do

- Submit PR reviews (post them as PENDING; the user submits).
- Open public PRs from security-advisory branches (private fixes only;
  the user coordinates disclosure).
- Open *any* PR — public or private — from a `vuln:VULN-NN` patch branch.
  Disclosure path runs through the user.
- Run live exploits against any langflow instance — your repro is
  code-level (a unit test, a function-call trace, a synthetic flow JSON).
  Not curl-against-prod, not curl-against-dev-running-on-localhost.
- Paste any line from `<inbox-dir>/inbox-vulns.md` into GitHub, Jira, Slack, email, a
  public gist, or any other surface. The file is local for a reason.
- Edit `<inbox-dir>/inbox-*.md` lines you didn't claim.
- Add new task kinds. If the work doesn't fit an existing kind, ask
  the user to add one in `<inbox-dir>/loops/protocol.md` (and the relevant loop doc).
- Skip the marker. Ever.

## Quick reference — finding a task

```bash
# Specific ID
grep -n '^- \[ \] review:#13469' <inbox-dir>/inbox-*.md

# Whole section in a file
sed -n '/{#pr-advisories}/,/^## /p' <inbox-dir>/inbox-prs.md

# All open tasks across both files
grep -h '^- \[ \] ' <inbox-dir>/inbox-*.md
```
