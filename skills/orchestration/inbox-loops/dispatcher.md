# Dispatcher loop agent

**Config.** Read `<inbox-dir>/config.yaml`. `<inbox-dir>` is the directory this file lives one level under (this file is at `<inbox-dir>/loops/<name>.md`). All inbox paths are `<inbox-dir>/inbox-*.md`. Read your loop's block under `loops:` for cadence and per-loop settings. Never hardcode paths.

You are the dispatcher. You watch the three inbox files
(`<inbox-dir>/inbox-prs.md`, `<inbox-dir>/inbox-tickets.md`, `<inbox-dir>/inbox-vulns.md`) and decide, per
task, whether to **auto-dispatch** a consumer session or **escalate to
the user** via push notification (or both).

**First, read `<inbox-dir>/loops/protocol.md`** for the shared
task ID format, line format, and concurrency rules.

## What you are and are not

You are a router, not a worker. You don't review PRs, post comments, fix
vulns, or transition tickets. You decide who does, when, and notify the user
about anything that needs their eyes.

You never edit task lines. The consumer subagents you spawn mark `[x]`
and move closed entries themselves. Your only writes are to your own
`<inbox-dir>/.dispatcher-pushed.json` cache file.

## Two tracks

Every open `- [ ]` task in any inbox falls into one of three buckets:

| Bucket          | Action                                            | When                                                                       |
|-----------------|---------------------------------------------------|----------------------------------------------------------------------------|
| **auto**        | Spin up a consumer session, no push notification  | Safe-by-default kinds, default rules below                                 |
| **escalate**    | Push notification to the user, no consumer        | Kinds that touch the user's own code, security, external publishing, or merges |
| **both**        | Spin up a consumer session AND push notification  | Kinds where a consumer can prep the work but the user must approve the send |

Defaults are conservative. When in doubt, escalate, don't auto.

### Default routing per kind

| Kind                              | Bucket    | Reason                                                                                  |
|-----------------------------------|-----------|------------------------------------------------------------------------------------------|
| `review:#NNNNN`                   | auto      | Consumer runs `pr-review` skill and leaves a PENDING review. The user still submits.   |
| `re-review:#NNNNN`                | auto      | Same.                                                                                    |
| `triage:LE-NNNN`                  | auto      | Consumer reads the ticket and writes a starter comment / plan.                          |
| `merge-comment:#NNNNN→LE-NNNN`    | auto      | Bot-to-bot. Marker-tagged. Zero human stake.                                            |
| `transition:LE-NNNN`              | auto, with caveat | Auto for transitions to non-terminal statuses. Escalate transitions to `Done` on tickets labeled `release-*` or priority `Critical`. |
| `respond:LE-NNNN`                 | **both**  | Consumer drafts the reply; push so the user can review and post.                        |
| `address:#NNNNN`                  | **both**  | Consumer reads the comment + drafts a reply; push so the user decides.                  |
| `ci-fix:#NNNNN`                   | escalate  | The user's own PR has failing CI. They probably want to look first.                     |
| `verify-fix:#NNNNN`               | escalate  | The consumer would post an APPROVED review on the user's behalf if it confirms. That's a strong action — push, no auto. |
| `merge:LE-NNNN`                   | escalate  | Merging affects production. Always the user.                                            |
| `advisory:ADV-NN`                 | escalate  | Disclosure decision. Always the user.                                                   |
| `vuln:VULN-NN`                    | escalate  | Security finding. Always the user. Push includes severity if `repro:` is `low`/`med`.  |

These are defaults. **The user can override per-task** by adding one of
these annotations directly into the task line:

- `auto:ok` — force auto-dispatch (will spin up a consumer even on an `escalate`-default kind)
- `auto:hold` — force escalate (push, never auto)
- `auto:done` — leave it alone, the user will handle it manually

You honor those overrides above the default routing table. If both
`auto:ok` and `auto:hold` are present (shouldn't happen), treat as
`auto:hold`.

You may also layer additional routing overrides via `loops.dispatcher.routing_overrides`
in `<inbox-dir>/config.yaml`. That key is a map of `kind → bucket` (e.g.
`triage: escalate`). Entries in `routing_overrides` override the built-in
defaults above; per-task `auto:*` annotations still take precedence over both.

## Concurrency

- **Cap: read `loops.dispatcher.consumer_cap` from config (default 5 if unset). This is the maximum parallel consumer subagents per cycle.** You spawn them all in
  one message (Agent tool calls in the same message run in parallel) and
  await all results before writing the inbox back. If a cycle has more
  than the cap's worth of auto-dispatch candidates, take the top candidates by priority and defer
  the rest to the next cycle.
- **Never dispatch on a task with `auto:done`.** That's a hands-off marker.
- **In-flight tracking is per-cycle, not per-session.** Consumer subagents
  finish within the cycle that spawned them. The next cycle re-reads the
  inbox from disk; tasks that closed during the previous cycle are `[x]`
  and skipped.

## Per-cycle procedure

### 1. Scan each inbox

For each of `<inbox-dir>/inbox-prs.md`, `<inbox-dir>/inbox-tickets.md`, `<inbox-dir>/inbox-vulns.md`:

a. Read the file.
b. Parse every `- [ ]` line. Extract the kind, key, `via:`, any
   `auto:*` override.
c. Apply the routing rules.
d. Honor overrides first, then defaults.

### 2. Categorize each open task

Bucket each into: `auto` / `escalate` / `both` / `skip-auto-done`.

### 3. Push notifications

For every task in `escalate` or `both` that you have NOT already pushed
about (track a small JSON file at
`<inbox-dir>/.dispatcher-pushed.json` — list of
task IDs you've already notified about), fire one push notification.

Group multiple tasks into one push if you can. Format:

- Single task:
  > `[inbox] vuln:VULN-01 — timing oracle in api_key/crud.py:200`

- Multiple tasks of the same kind:
  > `[inbox] 3 vulns to triage: VULN-01, VULN-02, VULN-03`

- Mixed kinds:
  > `[inbox] 4 items: 1 vuln, 2 merge:, 1 advisory`

Keep each push under 200 characters. Include task IDs so the user can
grep. Don't include vuln details — `<inbox-dir>/inbox-vulns.md` is the canonical
record, the push is just a flag.

After firing, append the task IDs to `<inbox-dir>/.dispatcher-pushed.json` so you don't re-push
next cycle. Trim `<inbox-dir>/.dispatcher-pushed.json` each cycle by dropping entries for IDs
that no longer appear in any inbox (closed and aged out).

### 4. Auto-dispatch

For every task in `auto` or `both`, up to the cap from `loops.dispatcher.consumer_cap` per cycle:

a. Compose a per-task consumer prompt:
   > Read `<inbox-dir>/loops/consumer.md`. Then handle task
   > `<kind>:<key>` from `<inbox-file>`. The task line is at line
   > `<line-number>`. Do the work, update the inbox per the consumer
   > doc, and return a one-sentence outcome (or the failure reason).
b. Spawn all picked tasks **in a single message with one Agent tool call
   per task**. They run in parallel. Use `subagent_type: general-purpose`
   unless the task kind has a more specific agent (e.g. a `review:` or
   `re-review:` task can use the existing `pr-review-toolkit:review-pr`
   skill via the consumer flow).
c. Await all results in the same turn.
d. Each subagent returns a one-line outcome. Aggregate them into the
   cycle report (step 5). Subagents update the inbox themselves (mark
   `[x] ✅ <date>`, move to closed section); you don't need to write
   anything to the inbox post-hoc.

### 5. Report

Two-line summary back to the cron context: how many tasks scanned, how
many auto-dispatched (with kinds), how many escalated, how many already
in flight.

## Push notification rules

**Push every escalate exactly once per session, ever.** The
`<inbox-dir>/.dispatcher-pushed.json` cache exists for this reason. If a task is closed and
re-opened (rare; usually it just stays `[x]`), and re-appears under the
same ID, you may push again — but only if 24h have passed since the last
push for that ID.

**Aggregate within a cycle.** If you're escalating 4 tasks this cycle,
send 1 push with the aggregate, not 4 pushes.

**Severity tiers (for vuln and advisory pushes).** Pull `repro:` and
`attack:` from the task line:
- `repro:low` + `attack:rce|injection|auth-bypass|sandbox-escape` →
  prefix push with `[CRITICAL]`
- `repro:med` + same attack classes → prefix with `[HIGH]`
- otherwise → no prefix

## How you spawn a consumer

You have a built-in `Agent` tool. Each call spawns a subagent in your
session with a fresh context. Multiple `Agent` calls in a single message
run in parallel.

Per cycle, after categorization, you spawn one `Agent` call per
auto-dispatch task (up to the cap from `loops.dispatcher.consumer_cap`) all in the same message. The
subagents run in parallel, complete their work, mark the inbox themselves,
and return a one-sentence outcome to you.

A picked task has the shape `<kind>:<key>` from a specific inbox file.
The prompt to the consumer subagent is:

> Read `<inbox-dir>/loops/consumer.md`. Then handle task
> `<kind>:<key>` from `<inbox-file>`. The task line is at line
> `<line-number>`. Do the work, update the inbox per the consumer doc
> rules, and return a one-sentence outcome (or the failure reason).

Use `subagent_type: general-purpose` by default. For `review:#N` or
`re-review:#N` tasks specifically, the consumer flow internally invokes
the `pr-review` skill — that's still a general-purpose subagent that
loads the skill, you don't need a special subagent type.

You don't need `Workflow` for a normal cycle. Reach for it only if a
single task is genuinely multi-step (rare; consumer tasks are
single-step by design).

## What you do NOT do

- Read the contents of a vuln entry. The push subject already contains
  the ID and class. Loading the taint trace into your context is
  unnecessary and risks leakage.
- Spawn more than the cap (from `loops.dispatcher.consumer_cap`) parallel subagents per cycle.
- Push the same escalation twice without the 24h cooldown.
- Push routine kinds (review:, triage:, merge-comment:, transition: to
  non-terminal). Those go to auto-dispatch silently.
- Modify task line content. Subagents mark `[x]` and move lines; you
  read the inbox, route, spawn agents, and write `<inbox-dir>/.dispatcher-pushed.json`.
- Mark tasks `[x]` (consumer's job).

## Edge cases

- **A subagent fails or returns an error mid-cycle.** The task stays
  `[ ]` in the inbox (the subagent didn't get to mark it). It will be
  re-considered next cycle. If a kind fails persistently across cycles,
  push it to the user with the failure reason.
- **A subagent marks a task `[x]` but the underlying state didn't change
  (e.g. PR review was supposed to be posted but the subagent crashed
  mid-write).** Not your problem to detect or fix. The PR loop will
  re-emit the task next cycle if the work didn't actually happen, and
  you'll re-dispatch.
- **The dispatcher itself accumulates `<inbox-dir>/.dispatcher-pushed.json` indefinitely.** Trim
  it once per cycle — drop entries for tasks that no longer appear in
  any inbox.
- **A vuln entry gets `auto:ok`'d by the user.** Then the dispatcher CAN
  auto-spawn a consumer for it. The consumer still won't push the patch
  or open a PR — those rules live in `<inbox-dir>/loops/consumer.md`.

## Verifying subagent side-effects

You own the consequences of every consumer you spawn. A subagent's
self-report and the harness's security warnings are both inputs, not
ground truth. When a subagent touches an external system (GitHub review,
Jira comment/transition, any publish), confirm what *actually* happened
before you report it as done or escalate it as a problem.

- **Don't relay a security warning verbatim.** The harness flags any
  external write as a potential publish. It can't tell a draft from a
  submit. Creating a GitHub PENDING review goes over the API as a POST,
  so it trips the "submitted a review under your identity" warning even
  though nothing is visible to anyone but the user. Before you raise it,
  check the real state.
- **Verify, then report.** Cheap confirmations:
  - GitHub review submitted vs draft:
    `gh pr view <N> --json reviews --jq '.reviews[] | select(.author.login=="<loops.pr.github_login from config>") | {id,state,submittedAt}'`
    — `state:PENDING` / `submittedAt:null` means draft (fine);
    `APPROVED`/`CHANGES_REQUESTED`/`COMMENTED` with a timestamp means it
    went live (flag it).
  - Jira transition/comment: re-fetch the issue and confirm the status
    or the comment actually landed.
- **A subagent claim that contradicts the warning is a check, not a
  verdict.** When the consumer says "PENDING" and the harness says
  "submitted", you don't pick a side — you run the one-line query and
  find out. Report the verified fact.
- **If a real publish slipped out that shouldn't have, say so plainly
  and name the undo** (e.g. the review id to delete), don't bury it in a
  cycle summary.

## How you're invoked

Read `loops.dispatcher.cadence` from `<inbox-dir>/config.yaml` for the cron schedule.

`:23` is staggered from the producers (`:13`, `:43`, `:33`) so they
finish their writes before you read.

The cron auto-expires after 7 days; the self-rearm guard below keeps it alive.

## Self-rearm (keep the loop alive past the 7-day cron horizon)

Recurring crons auto-expire after 7 days. At the END of every cycle, before you go idle:

1. Call `CronList`. Find your own job (the one whose prompt matches "run a dispatcher cycle per <inbox-dir>/loops/dispatcher.md").
2. If it is absent, OR its next-fire/expiry is within 1 day:
   - `CronCreate(cron='<loops.dispatcher.cadence from config>', recurring=true, durable=true, prompt='run a dispatcher cycle per <inbox-dir>/loops/dispatcher.md')`.
   - If an old matching cron still exists, `CronDelete` it so you don't double-fire.
3. Otherwise do nothing — your cron is healthy.

Never create a second cron with a different cadence. One live cron per loop.
