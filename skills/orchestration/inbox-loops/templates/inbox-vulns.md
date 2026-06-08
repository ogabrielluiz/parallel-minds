# Inbox — vulnerability candidates (sensitive, local only)

Last refreshed: <!-- set by vuln-loop agent --> by the vuln-hunt loop agent.
last_diff_sha: <!-- set by vuln-loop agent -->
area_cycle_index: <!-- set by vuln-loop agent -->

This file holds vulnerability candidates surfaced by the vuln-hunt loop
(`loops/vuln-loop.md`). Each entry is a code-review
finding that an independent validator agent has confirmed has a real
taint path or repro.

**SENSITIVE.** Don't paste contents of this file into any public surface —
GitHub comments, Jira tickets, Slack, gists, anything. Disclosure path runs
through the user.

Format and routing: see `loops/protocol.md`. Each
active entry spans **two lines** — the task line plus an indented `taint:`
and `repro:` block.

## Routing guide (for agents)

| To find...                            | grep for                       |
|---------------------------------------|--------------------------------|
| A specific vuln by ID                 | `vuln:VULN-NN`                 |
| All active candidates                 | `## Active candidates`         |
| Closed entries                        | `## Reviewed / closed`         |
| Findings from a specific area sweep   | `source:sweep:<area-name>`     |
| Findings from a specific merged PR    | `source:diff:#NNNNN`           |

## Stale (past due) {#stale}

```tasks
not done
path includes inbox-vulns
due before today
sort by due
```

## Active candidates {#vuln-active}

## Reviewed / closed {#vuln-done}

```tasks
done
path includes inbox-vulns
sort by done reverse
```
