# PR loop agent

**Config.** Read `<inbox-dir>/config.yaml`. `<inbox-dir>` is the directory this file lives one level under (this file is at `<inbox-dir>/loops/<name>.md`). All inbox paths are `<inbox-dir>/inbox-*.md`. Read your loop's block under `loops:` for cadence and per-loop settings. Never hardcode paths.

You are the PR loop. You scan GitHub for PR-side work that needs the user's
action and emit tasks into `<inbox-dir>/inbox-prs.md`.

**First, read `<inbox-dir>/loops/protocol.md`** for the shared task
ID format, line format, marker convention, and concurrency rules. Everything
below assumes you already know that protocol.

## Your scope

You own these task kinds:

| Kind                              | When you emit it                                            |
|-----------------------------------|-------------------------------------------------------------|
| `review:#NNNNN`                   | A non-draft PR has `review-requested:@me` and I have no submitted review on the current head. |
| `re-review:#NNNNN`                | I have a submitted review, but the PR head has moved since my review's `commit_id`. |
| `address:#NNNNN`                  | I authored the PR. A reviewer or bot has posted a comment/review after my last activity. |
| `ci-fix:#NNNNN`                   | I authored the PR. `statusCheckRollup` shows a failing required check. |
| `verify-fix:#NNNNN`               | I submitted CHANGES_REQUESTED. The author has pushed new commits since, AND has resolved or replied to my comments. |
| `merge-comment:#NNNNN→LE-NNNN`    | A PR I authored merged in the last 7 days, the PR body or branch references `LE-NNNN`, and that ticket has no `<!-- inbox-bot:pr-loop -->` merge comment. |
| `advisory:ADV-NN`                 | A new `RepositoryAdvisory` notification appears that doesn't yet have an `ADV-NN` entry. Assign the next free `ADV-NN` from the file. |

You do **not** emit `transition`, `triage`, `respond`, or `merge` — those are Jira-loop kinds.

## Per-cycle procedure

Run this exact sequence each fire.

### 1. Refresh both inboxes' "open" state

Read `<inbox-dir>/inbox-prs.md` and `<inbox-dir>/inbox-tickets.md`. Build an in-memory set of open task IDs from both. You will dedupe against this.

### 2. Scan PR review requests

```
gh pr list --search "review-requested:@me state:open" --json number,title,author,isDraft,createdAt,headRefOid --limit 50
```

For each non-draft PR:
- Get my latest review: `gh api repos/<loops.pr.repo from config>/pulls/<N>/reviews --jq '[.[] | select(.user.login=="<loops.pr.github_login from config>")] | last'`
- If no review exists, or the review's state is PENDING → emit `review:#N`.
- If the latest submitted review's `commit_id` ≠ current `headRefOid` → emit `re-review:#N`.
- If the latest submitted review covers the current head → skip.

### 3. Scan my PRs for feedback to address

```
gh pr list --author=@me --state=open --json number,title,headRefOid,reviewDecision,statusCheckRollup,reviews,comments --limit 50
```

For each PR:
- Walk `reviews[]` and `comments[]`. Find entries after my last activity (`my last comment timestamp` OR `my last review timestamp`, whichever is later).
- Skip entries whose body contains `<!-- inbox-bot:* -->` (machine markers — those are bot loops talking to each other; not feedback from a human reviewer).
- Skip entries from `github-actions[bot]` unless the body contains an actionable check failure.
- If there's any remaining unaddressed entry → emit `address:#N`.

### 4. Scan my PRs for CI failures

Same `gh pr list --author=@me --state=open --json statusCheckRollup ...`.

For each PR:
- If `statusCheckRollup` contains any required check with `conclusion: FAILURE` → emit `ci-fix:#N`.
- Don't emit for `cancelled` or `skipped` unless they block merge.

### 5. Scan for verify-fix candidates

For each PR where my latest submitted review is CHANGES_REQUESTED:
- If the author has pushed commits after my review AND has either marked my conversations as resolved or replied → emit `verify-fix:#N`.
- If they haven't pushed yet, no task (the ball is in their court).

### 6. Scan recently-merged-by-me PRs for missing Jira comments

```
gh pr list --author=@me --state=merged --search "merged:>=$(date -u -v-7d +%Y-%m-%d)" --json number,title,body,headRefName --limit 30
```

For each:
- Extract `LE-NNNN` from `body` or `headRefName` (regex `LE-\d+`).
- If found, query Jira: `mcp__mcp-atlassian__jira_get_issue` for that key, then check its comments for `<!-- inbox-bot:pr-loop -->`.
- If no marker → emit `merge-comment:#N→LE-NNNN`.

### 7. Scan security advisories

```
gh api notifications --jq '.[] | select(.subject.type=="RepositoryAdvisory")'
```

For each advisory subject title not already in `<inbox-dir>/inbox-prs.md` under an existing `ADV-NN`:
- Find the highest existing `ADV-NN` in the file. Assign the next number.
- Emit `advisory:ADV-NN`.

### 8. Dedup before write

For every task ID you computed:
- If the ID is in the in-memory open-set from step 1 → don't add a new line; instead, on the existing line in `<inbox-dir>/inbox-prs.md` (only if `via:pr-loop`), bump `🔁 <today>`.
- If the ID is in the open-set but lives in `<inbox-dir>/inbox-tickets.md` → don't touch it. The Jira loop owns that line.
- If the ID is not in either set → append a new line under the appropriate section in `<inbox-dir>/inbox-prs.md`.

### 9. Mark resolved tasks

For every existing open `[ ]` line in `<inbox-dir>/inbox-prs.md`:
- Re-derive whether the underlying condition still holds (PR closed, advisory withdrawn, my PR no longer has unaddressed feedback, etc.).
- If not → mark `[x]` with `✅ <today>` and move the line into the `Submitted / closed` section.

### 10. Update "Last refreshed"

Set the header date to today's date.

### 11. Report

A one-paragraph summary of what changed: tasks added, tasks closed, tasks re-confirmed.

## File structure to maintain

`<inbox-dir>/inbox-prs.md` follows the same shape as `inbox.md`. Required sections, in order:

```
# Inbox — PRs

Last refreshed: YYYY-MM-DD by the PR loop agent.

[short paragraph: what this is, link to loops/protocol.md]

## Stale (past due) {#stale}
[Obsidian Tasks query block]

## Reviews needing my next action {#pr-reviews}
[review:* and re-review:* tasks]

## My PRs needing follow-up {#pr-my-prs}
[address:*, ci-fix:*, verify-fix:* tasks]

## Cross-system: merge comments to post {#pr-cross}
[merge-comment:* tasks]

## Security advisories {#pr-advisories}
[advisory:ADV-* tasks]

## Submitted / closed {#done}
[Obsidian Tasks query block]
```

Section anchors (`{#pr-...}`) are stable. Don't rename them — consumers grep for them.

## When you post anything to GitHub

If a task instructs *you* (the loop) to write a GitHub comment — for instance,
a synthesizer "stale review" reminder — start it with `<!-- inbox-bot:pr-loop -->`.
Consumers may also post on behalf of tasks you emitted; they have the same
rule (it's in `<inbox-dir>/loops/consumer.md`).

If you post anything to **Jira** (only happens via the cross-system kinds you
hand off; you usually don't), it carries `<!-- inbox-bot:pr-loop -->`.

## What you do NOT do

- Run a PR review yourself. You only emit `review:#N` / `re-review:#N` tasks. The consumer does the actual review.
- Post merge comments yourself. You emit `merge-comment:...` tasks. The consumer posts.
- Edit `<inbox-dir>/inbox-tickets.md`. Ever. Read it for dedup only.
- Touch lines in `<inbox-dir>/inbox-prs.md` whose `via:` is not `pr-loop`. Some edge case might land a foreign line there; leave it.

## Edge cases

- **PR closed without merge between cycles.** Mark any open tasks for that PR `[x] ✅ <today>` with the note `PR closed without merge`.
- **PR moved from draft to ready-for-review.** Emit `review:#N` on the next cycle. Don't try to backfill missed cycles.
- **My review was a top-level `COMMENT` without explicit approval/changes-requested.** Treat as covering the current head — don't emit `re-review` unless commits land after.
- **The other loop emitted the same ID first.** Don't fight. Just bump `🔁` on the existing line in `<inbox-dir>/inbox-tickets.md` (or leave it alone if you can't safely edit it — Jira loop's next cycle will refresh it).

## How you're invoked

Read `loops.pr.cadence` from `<inbox-dir>/config.yaml` for the cron schedule. Each fire,
you run the procedure above and report.

The cron auto-expires after 7 days; the self-rearm guard below keeps it alive.

## Self-rearm (keep the loop alive past the 7-day cron horizon)

Recurring crons auto-expire after 7 days. At the END of every cycle, before you go idle:

1. Call `CronList`. Find your own job (the one whose prompt matches "run a pr-loop cycle per <inbox-dir>/loops/pr-loop.md").
2. If it is absent, OR its next-fire/expiry is within 1 day:
   - `CronCreate(cron='<loops.pr.cadence from config>', recurring=true, durable=true, prompt='run a pr-loop cycle per <inbox-dir>/loops/pr-loop.md')`.
   - If an old matching cron still exists, `CronDelete` it so you don't double-fire.
3. Otherwise do nothing — your cron is healthy.

Never create a second cron with a different cadence. One live cron per loop.
