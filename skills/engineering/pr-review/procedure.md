# Procedure

The full per-phase recipe for `pr-review`. The SKILL.md is the executive playbook; this file holds the literal steps, the verbatim specialist briefs, the verbatim validator brief, and the feedback/output mechanics. The specialist and validator briefs are prompt templates the subagents receive — do not reword them.

## Phase 1. Mode, eligibility, baseline, context sources

1. **Mode detection.** First positional argument is a number → PR mode. No positional argument (only flags, or no args at all) → local mode. Path-like first argument → error and suggest `--scope <path>`.

### PR mode (steps 2–4 apply only when a PR number was passed)

2. **Eligibility gate.** `gh pr view <N> --json isDraft,state,reviews`. Stop and report if it is a draft, closed, or merged. Stop if a recent review by the current user already exists (do not re-review without explicit instruction).
3. **Checkout.** `gh pr checkout <N>` in an isolated worktree. `gh pr view <N>` for body, title, base branch.
4. **Companion/stacked PR resolution.** Scan body and title for references (`#NNNN`, "depends on", "stacked on", "docs for", "part of"). If found, the correct baseline is this PR's diff PLUS the companion PR's changes. Fetch the companion's files via `gh pr diff <companion> --patch` and apply the patch onto the baseline. A docs PR must be validated against the code in its implementation PR, not against the base branch alone.

### Local mode (steps 5–6 apply only when no PR number was passed)

5. **Diff acquisition.** Compute the review diff as the union of:
   - `git diff @{upstream}...HEAD` — branch vs upstream.
   - `git diff HEAD` — working tree (staged plus unstaged).

   If `@{upstream}` doesn't resolve (no tracking branch set), fall back in order to `git diff main...HEAD` then `git diff master...HEAD`. If neither base branch exists, stop with a clear error naming what was tried. If both the branch diff and the working-tree diff are empty, stop with "no changes to review."

6. **Companion detection (best-effort, warn-only).** Scan the last 10 commits on this branch (`git log -10 --pretty=full HEAD`) and the current branch name for: `#NNNN`, "stacked on", "depends on", "part of", "docs for". If any are found, surface them to the user as a warning before dispatching specialists — for example: "This branch references #1234 and says 'stacked on auth-base' in commit a1b2c3d. Review may be incomplete without their context." Do NOT fetch companions in local mode — local mode reviews what's in the working tree.

### Both modes (steps 7–9 always apply)

7. **Apply `--scope`** if provided. Filter the combined diff to that subtree.
8. **Spec sources.** Look for, in order:
   - PR mode: Jira/Linear/external ticket links in the PR body, then GitHub issue refs in commits (`Closes #...`, `Fixes #...`), then PRD or design docs under `docs/`, `.planning/`, or `~/Projects/ideas/`.
   - Local mode: GitHub issue refs in recent commits (`Closes #...`, `Fixes #...`), then PRD or design docs under `docs/`, `.planning/`, or `~/Projects/ideas/`.

   Note the path or URL of the spec, if any. If none, the Spec specialist is skipped.
9. **Standards sources.** Enumerate: root `AGENTS.md`, root `CLAUDE.md`, per-directory `CLAUDE.md` files touching the diff, `CONTRIBUTING.md`, any ADRs under `docs/adr/`. Pass these paths (not contents) to specialists; they read what they need.

Reviewing a docs or stacked PR against its base branch alone and missing the companion PR (PR mode step 4) — or running a local review with an unresolved warning about stacked work (local mode step 6) — is the most common Phase 1 failure. Always do the reference scan.

## Phase 2. Dispatch specialists in parallel

Always dispatch:

- **Bugs & Behavior specialist.** Brief: "Here is the diff slice and the standards-source paths. Find bugs, logic errors, edge cases, error handling problems, silent failures. For each finding, name the concrete triggering input or code path. If you claim a test will fail, run it and include the actual output. Return `{file, line, claim, proof, severity, internal_axis: behavior}`. Do not flag style or things linters catch."
- **Fit specialist.** Brief: "Here is the diff slice and the standards-source paths. Read the standards sources you need. Find: violations of documented rules, structural problems (feature logic in shared modules, file-in-wrong-layer, thin wrappers that add indirection without clarifying, canonical-helper duplication, casts or broad types hiding invariants, ad-hoc booleans complicating an existing flow, sequential async where independent work could be parallel and clearer). Prefer findings where a clear restructuring would delete complexity rather than rearrange it. Return `{file, line, claim, proof, severity, internal_axis: fit}`."

Dispatch conditionally:

- **Spec specialist** — only if Phase 1 found a spec. Brief: "Read this spec and the diff. Report: requirements asked for that are missing or partial; behavior in the diff that wasn't asked for (scope creep); requirements that look implemented but where the implementation looks wrong. Quote the spec line for each finding. Return `{file, line, claim, proof, severity, internal_axis: spec}`."

Specialists run in parallel. They return candidate findings.

**Each specialist gets only the diff slice it needs, plus paths (not contents) of relevant sources.** Keep prompts small. If a specialist needs more context (caller/callee, related modules), it walks there on its own. Do not pre-load the whole codebase into the brief.

## Phase 3. Validate, filter, deliver

### 3.1 Dispatch the validator subagent

After all specialists return. Pass it the full finding list and the checked-out diff (PR mode: the worktree; local mode: the current working tree).

Validator brief (verbatim): "Re-derive every finding independently. Do not trust the stated proof. Where feasible, write and run a short probe script — a 5-20 line Python/Bash/Node throwaway that exercises the claimed failure mode — and decide based on its output. For test-failure claims, run the test. For 'will crash on X' claims, write a probe that passes X. For 'this branch is unreachable' claims, write a probe that drives execution there. For findings that cannot be probed (style, structural, spec-adherence), re-read the relevant code and the cited rule. Tag each finding `confirmed`, `rejected`, or `unproven`. Assign confidence 0-100 per the rubric below. Return the tagged list."

Confidence rubric (give to validator verbatim):

- **0**: false positive that does not stand up to scrutiny, or a pre-existing issue.
- **25**: might be real, could not verify.
- **50**: verified real but minor or rare.
- **75**: verified real, will hit in practice, or a direct standards/spec violation.
- **100**: confirmed with evidence (probe output, failing test, quoted rule directly violated).

Skipping the probe script and trusting a re-read for a claim that could be probed in 10 lines is the most common validator failure — if the claim is empirically testable, the validator probes it.

### 3.2 Bounded feedback loop

Send `unproven` findings back to the originating specialist with the validator's note, for one more round. Cap at 2 rounds total. After round 2, anything still `unproven` is dropped.

### 3.3 Filter

Drop everything below `--threshold` (default 75). Drop everything `rejected`. Keep only `confirmed`. Shipping a finding the validator only marked `unproven` is a hard stop — only `confirmed` and above-threshold findings ship.

### 3.4 PR mode — post the pending review

(Skip this section in local mode.)

- De-dup overlapping findings.
- Validate every inline comment's line against the PR diff. Parse each `@@` hunk; only RIGHT-side added (`+`) and context (` `) lines are commentable. Findings not mappable to a diff line go in the body. Commenting on a diff line not inside a hunk 422s the entire review.
- Create a PENDING review: `POST /repos/{owner}/{repo}/pulls/{N}/reviews` with `body` and `comments`, and **NO `event` field**. Omitting `event` is what makes it pending. On a 422 for a bad line, drop that comment and retry. Never submit unless `--comment` was set.
- Do not repeat a finding in both the body and an inline comment. If it is inline, the body just says notes are inline.
- No verdict, no confidence scores, no axis tags in the posted text. Findings only.
- Write the body and every comment per the `pr-comment-style` skill.

### 3.5 Local mode — present findings in the conversation

(Skip this section in PR mode.)

- De-dup overlapping findings.
- If `--comment` was passed, error: `--comment` is PR-mode only.
- Print findings to the conversation, grouped by axis: **Bugs & Behavior** first, then **Fit**, then **Spec** (if any). Within each group, sort by file path then line number.
- Per-finding format:
  ```
  `path/to/file.ext:42` — short claim
    Proof: <validator's re-derivation in one sentence>
  ```
- No verdict, no confidence scores, no axis tags inline.
- If a finding spans multiple lines, use the start line in the path and mention the range in the claim ("lines 42-48").
- Write each claim and proof per the `pr-comment-style` skill — same voice as PR mode, same brevity.

### 3.6 If `--fix` was set (both modes)

After delivering findings (PR mode: posting the review; local mode: printing to the conversation), apply each confirmed finding's suggested fix as an edit to the working tree. Stage the changes (`git add`). Do not commit. Report the resulting diff to the caller.

## Return value

**PR mode**: pending review URL and id, confirmed-finding count broken down by `internal_axis`, dropped-by-threshold count, and (if `--fix`) the applied-edits diff path.

**Local mode**: confirmed-finding count broken down by `internal_axis`, dropped-by-threshold count, and (if `--fix`) the applied-edits diff path. No URL — findings live in the conversation.
