---
name: plan-scrutiny
description: Use when an implementation plan is about to be executed, especially by parallel agents or a fresh session with no context, when tasks in a plan keep getting done wrong or half-done, or when you need to find which steps of a written plan are ambiguous before anyone starts building
---

# Plan Scrutiny

Dispatch a panel of independent cold readers at a written plan, then measure where their interpretations diverge. Divergence is the evidence: two agents that read the same task and describe incompatible work have located an ambiguity that no style review would catch.

This skill does not write plans. It takes one that already exists and reports which parts of it will be executed inconsistently.

## Philosophy

**Core principle**: ambiguity is proven by divergence, not asserted by opinion. "This step is unclear" is a critique. "Reader A would edit the registry, reader B would create a new module" is a measurement.

Plan ambiguity is amplified by parallelism. A solo executor reading a vague step guesses once and stays internally consistent. Five agents executing five tasks from the same plan guess independently, and the guesses drift apart — so a plan that reads fine to its author produces divergent work the moment it is fanned out.

Two consequences fall out of this:

- **Cold readers must commit, never ask.** An executor in a swarm cannot stop and request clarification. A reader that answers "I would ask what X means" has skipped the measurement. Force a decision.
- **Convergence is not correctness.** Three readers can agree on the same wrong reading of a confidently-wrong plan. Report a coverage map of what was probed, not a passing grade.

## When to Use

Use before executing a plan with parallel agents or subagent-driven development, when a previous run of the same plan produced work that missed or misread steps, when the plan will be handed to a fresh session with no conversation context, or when the plan is long enough that its author can no longer read it cold.

Skip it when the plan is three obvious steps, when requirements are still unsettled (brainstorm first), or when you are the one executing it immediately in the same session that wrote it — you carry the context that the probe is designed to remove.

## Workflow

### 1. Load and segment the plan

Read the plan file and split it into numbered tasks. Preserve the plan's own task boundaries if it has them; otherwise segment on headings. Record the total count — it sets probe cost, since each reader reports on every task.

If the plan references a design doc or ticket, note the path but **do not** hand it to the readers. The probe measures what the plan alone communicates. Feeding readers the background is how a plan's gaps get papered over.

### 2. Run the STE audit

Mechanically check every task's prose against the nine-rule ASD-STE100 subset in [ste-rules.md](ste-rules.md): one instruction per sentence, imperative and active, one verb per action, condition before command, no cross-sentence pronouns, no dropped articles or subjects, three-word noun clusters, twenty-word instructions, vertical lists for sequences.

This pass is cheap and runs before the panel. It produces candidate violations, not findings — a rule violation only matters if the panel diverges there. Carry the violation list into the report so confirmed divergence can be attributed to a specific rule.

Watch for: treating the audit as the deliverable. A plan can pass all nine rules and still be ambiguous about which file to touch. The rules explain divergence; they do not detect it.

### 3. Dispatch the cold-read panel

Mode selects panel size: `fast` (3 readers) for plans under ten tasks, `full` (5 readers) for longer plans or plans that already failed a run, `auto-escalate` to start at 3 and add 2 when the first round splits on more than a third of the tasks.

All readers dispatch in parallel with `run_in_background: true` and `model: sonnet`. Every reader receives the plan text and nothing else — no conversation history, no repo tour, no sibling output. The full prompt template and required output format are in [cold-read-protocol.md](cold-read-protocol.md).

Watch for: readers that critique instead of interpret. A reader reporting "task 4 is vague" has become an opinion generator and its output is unusable as a divergence signal. Re-dispatch it with the commitment clause enforced.

### 4. Measure divergence

Collect the panel output and compare readers task by task. Classify each task:

- **CONVERGENT** — all readers describe the same files, the same action, and the same completion condition.
- **SPLIT** — readers name different files, different actions, or different done-conditions. Quote the conflicting interpretations verbatim; the quotes are the artifact.
- **HEDGED** — one or more readers committed but flagged low confidence, or invented a detail the plan never stated. Invention is the tell that the plan left a hole the reader filled.

Attribute each SPLIT and HEDGED task to the STE rule it violates where one applies. Some splits trace to a missing fact rather than a language rule — label those `underspecified` instead of forcing a rule onto them.

Watch for: resolving a split yourself because you know which reading is right. You have the author's context; the executors will not. Record the split.

### 5. Report

Open with a verdict — `REWRITE` (a third or more of tasks split), `PATCH` (isolated splits), or `READY` (no splits, hedges noted) — then the per-task table with the quoted divergences, then the coverage map naming what the probe did not cover: tasks with no code references to check, external dependencies the readers could not see, ordering assumptions between tasks.

Only after presenting the report, ask: "Want me to rewrite the split tasks?" Rewrites go through the same nine rules, and a re-probe of just the rewritten tasks confirms the fix.

Watch for: rewriting the whole plan when three tasks split. Patch the tasks the panel actually disagreed on.

## Example: Migration Plan Fan-Out

**Plan:** eleven-task adapter extraction, intended for five parallel agents.

**STE audit found:** task 3 joins two actions with "and", task 6 opens with "It should then", task 9 stacks a five-word noun cluster.

**Panel (fast, 3 readers) found:** task 3 SPLIT — reader A moved the converter and left the adapter, reader B moved both, reader C created a new module and re-exported. Task 6 SPLIT — "it" resolved to the adapter for two readers and to the registry for one. Task 9 CONVERGENT despite the noun cluster; all three readers landed on the same file. Task 7 HEDGED — every reader invented a different test path, because the plan never named one.

**Result:** `PATCH`. Two rule-attributable splits (dropped conjunction, cross-sentence pronoun), one `underspecified` task. The noun-cluster violation was real and harmless — evidence that the audit alone would have sent us rewriting a task that three independent readers already agreed on.
