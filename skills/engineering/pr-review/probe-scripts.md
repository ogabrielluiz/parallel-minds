# Probe scripts

Probe scripts are the validator's primary verification tool. A probe is a short throwaway script — typically 5-20 lines of Python, Bash, or Node — that executes the claimed failure mode and reports the result. The validator decides `confirmed` / `rejected` / `unproven` based on the probe's output, not on re-reading the code.

## Examples

- Claim "calling `foo(None)` raises AttributeError at file:L42" → probe imports `foo`, calls `foo(None)`, prints exception type.
- Claim "this branch is unreachable" → probe constructs the input the branch should handle, runs the function, prints whether the branch was hit (add a temp print in the branch).
- Claim "the test `test_x` will fail after this change" → no probe needed; the validator just runs the test.
- Claim "this regex backtracks on input Y" → probe runs the regex against Y with a timeout, reports.

## When a finding cannot be probed

Some findings don't have a runnable failure mode:

- Style findings (formatting, naming conventions linters don't catch).
- Missing-spec-requirement findings (the spec asked for X, the diff doesn't have X — there's nothing to execute).
- Structural cleanup proposals (this would read better restructured, this wrapper adds indirection without clarifying).
- Spec-adherence findings where the wrongness is semantic, not behavioral.

For these the validator falls back to re-reading the relevant code and the cited rule. Note in the validator's response which findings were probed vs read-only — that distinction matters when the caller is deciding which findings to take action on.

## Script storage

Probe scripts live under `$CLAUDE_JOB_DIR` (or `$TMPDIR` if not in a job context). They are never committed. They are throwaway by design — the goal is the validator's verdict, not a regression suite.
