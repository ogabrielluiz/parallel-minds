---
name: pr-review
description: Use when reviewing changes — a GitHub pull request by number, OR the current local diff (working tree plus branch vs upstream). Dispatches narrow specialist subagents (bugs and behavior, fit-to-codebase, spec adherence) in parallel, runs a validator that re-derives findings with probe scripts when feasible, filters by confidence. PR mode posts a pending (draft, unsubmitted) GitHub review; local mode presents findings in the conversation. Supports --scope to slice a large diff, --fix to apply findings as edits, and --comment (PR mode only) to submit instead of leaving pending.
---

# PR Review

Review either a remote GitHub PR or your current local diff, and surface only findings that an independent validator has re-derived. Specialists stay narrow, the validator runs probe scripts where it can, and only high-conviction findings ship.

## Philosophy

**Core principle**: a finding ships only if a separate validator subagent has independently re-derived it — by running a short probe script wherever the claim can be probed, by re-reading the code and cited rule when it cannot. Specialists stay narrow (each gets the diff slice plus its single concern, never a whole-diff generalist brief), and the default confidence threshold of 75 drops nits before they ever reach the output. The review surfaces findings, not verdicts.

## When to use

- Reviewing a GitHub PR by number, including the review-requested loop's PRs in langflow-ai/langflow.
- Reviewing your current local changes before committing, before pushing, or before opening a PR.

## Modes

The first positional argument decides the mode:

- **PR mode** — `pr-review <N>` where `<N>` is a PR number. Checks the PR out, resolves companion/stacked PRs, posts a pending review.
- **Local mode** — `pr-review` with no positional argument. Reviews the union of `git diff @{upstream}...HEAD` and `git diff HEAD`, detects companion work via branch name and recent commit messages (warn-only — does not fetch), presents findings in the conversation.

Path-like first argument is an error — use `--scope <path>` to slice the diff.

## Execution context

Run this skill from the top-level conversation, which can dispatch subagents. Reviewers and the validator are real dispatched subagents and the validator's independence depends on it being a separate agent with a clean context.

**Do not invoke this skill from inside a subagent.** Subagents cannot dispatch subagents, so the reviewers and the validator would collapse into one context and lose the independence the design exists for. A loop or batch reviewing several diffs runs this skill once per diff from the top level, one at a time. It does not hand a diff to a subagent.

## Flags

- `--scope <path>` — restrict review to a path subtree (e.g., `--scope src/backend/`). Default: entire diff. Use this on a big diff to run several targeted reviews instead of one huge run.
- `--threshold <N>` — confidence cutoff, 0-100. Default: 75. Below this, findings are dropped.
- `--fix` — after presenting findings, apply confirmed ones to the working tree as edits. Staged but not committed. Reports the resulting diff back to the caller.
- `--comment` — **PR mode only**. Submit the review as a posted comment instead of leaving pending. Default: off (pending). Error if passed in local mode.

## Workflow

### 1. Establish mode, eligibility, and baseline

**PR mode**: Gate on `gh pr view <N> --json isDraft,state,reviews` — stop if the PR is draft, closed, merged, or already has a recent review by the current user (don't re-review without explicit instruction). Check the PR out in an isolated worktree, then scan body and title for companion references (`#NNNN`, "depends on", "stacked on", "docs for", "part of") and apply the companion's patch on top of the baseline before reviewing. A docs PR validated against its base branch alone misses the implementation it documents — always do the reference scan.

**Local mode**: Acquire the diff as the union of `git diff @{upstream}...HEAD` (branch vs upstream) and `git diff HEAD` (working tree — staged plus unstaged). If both are empty, stop with "no changes to review." If `@{upstream}` doesn't resolve, fall back to `git diff main...HEAD` then `git diff master...HEAD`. Detect companion work by scanning recent commit messages and the branch name for `#NNNN`, "stacked on", "depends on", "part of" — surface what you find as a warning ("this branch references #1234 / says 'stacked on auth-base' — review may be incomplete") but do not fetch.

**Both modes**: apply `--scope` if provided, then enumerate spec sources (tickets, `Closes #...` in commits, PRDs under `docs/`, `.planning/`, or `~/Projects/ideas/`) and standards sources (root `AGENTS.md`, root `CLAUDE.md`, per-directory `CLAUDE.md`s touching the diff, `CONTRIBUTING.md`, ADRs under `docs/adr/`). Pass paths to specialists, not file contents — they read what they need.

See [procedure.md](procedure.md) for the full per-phase recipe and verbatim specialist briefs.

### 2. Dispatch specialists in parallel

Always dispatch **Bugs & Behavior** and **Fit**. Dispatch **Spec** only if a spec source was found in step 1. Each specialist gets only the diff slice it needs plus paths (not contents) of relevant standards/spec sources — keep prompts small and let specialists walk to more context on their own. Findings come back as `{file, line, claim, proof, severity, internal_axis}`. Watch for: pre-loading the whole codebase into a brief (specialists pull what they need), and asking a specialist for style findings the linter already catches.

See [specialists.md](specialists.md) for the specialist catalog, including narrower specialists (Error-handling, Type design, Test quality) that spawn only when the diff has substantial presence in their area.

### 3. Validate, filter, present

Dispatch the validator subagent after all specialists return. The validator re-derives every finding independently — writing and running a 5-20 line probe script wherever the claim can be probed (test-failure claims → run the test; "crashes on X" → probe that passes X; "branch unreachable" → probe that drives execution there), and falling back to re-reading the code only for findings that cannot be probed. Each finding is tagged `confirmed`, `rejected`, or `unproven` and scored 0-100 against the rubric in [procedure.md](procedure.md). Send `unproven` findings back to their originating specialist for one more round (cap at 2 rounds total); anything still `unproven` after round 2 is dropped.

Then filter: drop everything below `--threshold` (default 75), drop everything `rejected`, keep only `confirmed`. **Watch for: shipping anything the validator only marked `unproven` — that's a hard stop.**

**PR mode output**: Post a PENDING review (`POST /repos/{owner}/{repo}/pulls/{N}/reviews` with `body` and `comments` and **no `event` field** — omitting `event` is what makes it pending). Watch for: including an `event` field when `--comment` wasn't set (submits instead of leaving pending); commenting on a line outside a hunk (422s the whole review — only RIGHT-side added `+` and context ` ` lines are commentable); putting a verdict line or confidence score in the body (findings only); repeating a finding in both body and inline comment.

**Local mode output**: Present findings in the conversation, grouped by axis (Bugs & Behavior first, then Fit, then Spec if any). Within each group, sort by file path then line. Per finding: `` `path/to/file.ext:42` — short claim `` on the first line, validator's one-sentence proof on the indented next line. No verdict, no confidence scores, no axis tags inline. Watch for: padding the output with low-conviction findings the filter already dropped — don't re-add them.

Write the body and every comment (or every local-mode finding) per [voice.md](voice.md) — voice rules live there.

If `--fix` was set (both modes), apply each confirmed finding's suggested fix to the working tree, stage it, and report the diff to the caller without committing.

See [probe-scripts.md](probe-scripts.md) for probe templates and when probes don't apply.

## Big diffs

There is no file-size or diff-size cap. A big diff is fine if it is one coherent feature. To keep specialist contexts small, run targeted reviews scoped to subtrees: `pr-review <N> --scope src/backend/`, then `pr-review <N> --scope src/frontend/` (or `pr-review --scope src/backend/` in local mode). In PR mode, each scoped review posts to the same PR as a separate pending review. In local mode, each prints to the conversation as a separate findings block.

## Voice

Write the review body and every comment (or local-mode finding) per [voice.md](voice.md). Load it and follow it. The voice rules live there, not in this skill.

If you have your own PR voice skill installed (`pr-comment-style` or similar), it overrides [voice.md](voice.md) entirely. The sidecar is the default so the plugin works standalone.
