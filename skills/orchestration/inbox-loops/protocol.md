# Inbox loops

> Per-user settings live in <inbox-dir>/config.yaml. This protocol is shared by all loops and consumers.

Three agents, one shared queue. Each agent runs in its own Claude Code session
and reads exactly one doc in this folder. The user points sessions at docs and
the agents take it from there.

```
┌──────────────────┐                        ┌──────────────────┐
│   PR loop agent  │   writes inbox-prs.md  │  inbox-prs.md    │
│  (pr-loop.md)    ├───────────────────────►│                  │
└────────┬─────────┘                        └────────┬─────────┘
         │                                           │
         │ reads both for dedup                      │
         ▼                                           │ read by
┌──────────────────┐                                 │
│ Jira loop agent  │   writes inbox-tickets.md       │
│ (jira-loop.md)   ├───────────────────────►┐        │
└────────┬─────────┘                        ▼        ▼
         │                          ┌──────────────────┐
         │                          │ inbox-tickets.md │
         │                          └──────────────────┘
         │                                   ▲
         └─ reads both for dedup ────────────┘
                                             │
                                  ┌──────────┴───────────┐
                                  │  consumer agent(s)   │
                                  │   (consumer.md)      │
                                  └──────────────────────┘
```

## What each doc does

| Doc                             | Who reads it                           | What they produce                       |
|---------------------------------|----------------------------------------|-----------------------------------------|
| `pr-loop.md`                    | The PR loop agent (one session)        | Tasks in `inbox-prs.md`                 |
| `jira-loop.md`                  | The Jira loop agent (one session)      | Tasks in `inbox-tickets.md`             |
| `vuln-loop.md`                  | The vuln-hunt loop agent (one session) | Tasks in `inbox-vulns.md` (sensitive)   |
| `dispatcher.md`                 | The dispatcher loop (one session)      | Consumer dispatches + push notifications to the user |
| `consumer.md`                   | Worker agents (any session)            | Completed tasks (`[x]`) + side-effects  |
| `protocol.md` (this file)       | All five — shared protocol             | —                                       |

The two loops are producers. They never read tasks they didn't write — only
their own file (for `[x]` cleanup) and the other loop's file (for dedup).
They never close tasks the other loop emitted. They never edit task lines
they didn't write.

The consumer is the only thing that closes tasks (`[x] ✅ <date>`) and
performs side-effects (post a comment, transition a ticket, write a PR
review).

## Task ID format — shared across both files

```
<kind>:<primary-key>
```

The ID is the first token on the line after `[ ]` / `[x]`. Same `kind:key` =
same task. Each loop greps **both files** for the ID before emitting; if it
exists anywhere, the loop bumps `🔁 <date>` on the existing line and moves on.

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
| `respond:LE-NNNN`                 | someone mentioned me in a ticket comment, reply          | Jira loop only  |
| `merge:LE-NNNN`                   | ticket is "Ready to Merge", merge its PR                 | Jira loop only  |
| `advisory:ADV-NN`                 | published security advisory needing triage               | PR loop only    |
| `vuln:VULN-NN`                    | vulnerability candidate found by code review (sensitive) | Vuln loop only  |

If you need a new kind, add it here AND in the relevant loop docs before emitting.

## Task line format

```
- [ ] <kind>:<key> — <short title>. via:<loop> linked:<cross-id|none> ➕ <YYYY-MM-DD> 📅 <YYYY-MM-DD>
```

- `- [ ]` open / `- [x]` done.
- `<kind>:<key>` is the task ID. First token. Stable across refreshes.
- `<short title>` — one line, self-contained. No "see context above".
- `via:` = `pr-loop` or `jira-loop` (which agent emitted).
- `linked:` = the cross-system reference, or `none`.
- `➕` = date the task first appeared. Never changes.
- `📅` = soft due-by date. Loop may bump if the underlying thing is updated.
- `🔁 <YYYY-MM-DD>` = last refresh that re-confirmed the task is still open (added by the loop when it sees the same ID still applies).
- `✅ <YYYY-MM-DD>` = added by the consumer when closing.

Example open task:
```
- [ ] review:#13379 — feat(ci) nightly fresh-install, by @lice-reis. via:jira-loop linked:LE-1416 ➕ 2026-06-05 📅 2026-06-06 🔁 2026-06-05
```

Example closed task:
```
- [x] review:#13379 — feat(ci) nightly fresh-install, by @lice-reis. via:jira-loop linked:LE-1416 ➕ 2026-06-05 📅 2026-06-06 ✅ 2026-06-05
```

## Cycle prevention — markers on machine-posted comments

When either loop (or the consumer acting on a loop-emitted task) posts a
comment in the *other* system, the comment **must** carry an HTML marker:

- PR loop / its consumer posting to Jira: `<!-- inbox-bot:pr-loop -->`
- Jira loop / its consumer posting to GitHub: `<!-- inbox-bot:jira-loop -->`

Loops ignore any comment with `<!-- inbox-bot:* -->` when scanning for
"new activity that needs a response" (`respond:`, `address:`). This breaks
the cycle "PR merged → bot Jira comment → Jira loop sees activity → emits
respond → posts bot GitHub comment → PR loop sees activity → ...".

## File layout

Everything lives in `<inbox-dir>/`, the directory chosen at setup (recorded as `inbox_dir` in `config.yaml`).

```
<inbox-dir>/
├── config.yaml                    # per-user settings (inbox_dir, credentials refs, etc.)
├── inbox.md                       # human-readable digest (auto-generated, optional)
├── inbox-prs.md                   # PR loop's queue
├── inbox-tickets.md               # Jira loop's queue
├── inbox-vulns.md                 # vuln-hunt loop's queue (SENSITIVE, local only)
└── loops/
    ├── protocol.md                # this file (shared protocol)
    ├── dispatcher.md              # dispatcher (router) agent's instructions
    ├── pr-loop.md                 # PR loop agent's instructions
    ├── jira-loop.md               # Jira loop agent's instructions
    ├── vuln-loop.md               # vuln-hunt loop agent's instructions
    └── consumer.md                # consumer agent's instructions
```

**`<inbox-dir>/inbox-vulns.md` is sensitive.** Don't surface its contents to any
external system (GitHub comments, Jira tickets, Slack, etc.) without
explicit go-ahead from the user. Disclosure flow runs through the user, not
through the inbox.

## Concurrency

Each loop runs as a recurring cron in its own Claude Code session. Two loops
+ N consumers all touching the same files means edits will race. Rules:

1. **Loops only edit their own file.** PR loop writes only `<inbox-dir>/inbox-prs.md`.
   Jira loop writes only `<inbox-dir>/inbox-tickets.md`. Either may *read* the other.
2. **Consumers only mark `[x]` and add `✅`.** They never re-order, re-format,
   or rewrite other lines. They never touch other consumers' in-progress
   items.
3. **The loop never deletes an unrecognized line.** If the loop sees a line
   it didn't write and the ID format is valid, leave it. Only flag if the ID
   is malformed.
4. **Before any edit, re-read the file.** Don't cache the file contents
   across tool calls.

If you need to do many edits to the same file, do them in one `Edit` call
with `replace_all: false` and a tight `old_string`, not a `Write`.

## Cadence

Staggered cron times to avoid simultaneous grep races:
- PR loop fires at `13 */3 * * *` (every 3h)
- Jira loop fires at `43 */3 * * *` (every 3h)
- Vuln-hunt loop fires at `33 */6 * * *` (every 6h)
- Dispatcher fires at `23 * * * *` (every hour)

The dispatcher runs hourly so newly-emitted tasks get routed within ~30 min
on average. The vuln-hunt loop runs less often because each cycle is heavier
(real code review + a validator pass per candidate).

Consumers run on demand — when the user (or another orchestrator) dispatches
a session at `consumer.md`.

## What "needs action" means (the bar)

A task only enters the inbox if it's something **the user personally has to
do or decide**. Not "the user might find this interesting". Not "the user is
on the watcher list". The test:

> If I do nothing about this item for 2 days, does something measurably
> worse happen? (review goes stale, ticket misses sprint, advisory ages out
> of SLA, bot keeps re-pinging.)

If yes → emit. If no → don't.
