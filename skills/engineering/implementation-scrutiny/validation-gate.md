# Validation Gate & Synthesis

The Validation Gate is the calling agent's job after all verification agents return. It turns a pile of agent claims into a report grounded in re-runnable evidence. Skip it and the whole skill collapses into "ask several agents what they think" — which is exactly what the skill exists to replace.

## Validation procedure

Run this against every finding returned by every agent before anything is summarized.

**For each finding with `ARTIFACT_TYPE: script`:**

1. Write the script to a temp file.
2. Execute it via Bash.
3. Capture stdout/stderr verbatim.
4. Compare the captured output against the `EXPECTED` field and attach the actual output to the finding.

**For each finding with `ARTIFACT_TYPE: url`:**

1. Fetch the URL via WebFetch.
2. Verify the URL resolves and contains the claimed content at the claimed location.
3. If the URL 404s or the content doesn't match the claim, demote the finding to UNVERIFIED with a note explaining why.

**Failure modes that demote a finding to UNVERIFIED:**

- Script errored on execution.
- Script's actual output didn't match the agent-reported `ACTUAL`.
- URL returned 404 or unrelated content.
- Finding came back with no artifact at all.

Note in the report *why* each UNVERIFIED finding failed — silent demotion hides signal.

## Cross-checking and grouping

Once each finding is validated or demoted, cross-check across agents:

- If two agents' scripts independently produce the same numerical value or observation, escalate confidence.
- If two agents disagree, mark the finding **CONTESTED** and surface both sides. Don't silently resolve conflicts.

Group surviving findings by severity:

- **PROVEN BUG** — a script reproduced the bug locally.
- **LIKELY BUG** — a URL-backed reference disagrees with our code, but no local reproduction yet.
- **CONTESTED** — two or more agents disagree and the evidence is split.
- **UNVERIFIED** — no valid artifact, or artifact failed validation.

## Artifact persistence

After validation, persist surviving scripts so they become regression coverage for future sessions:

- Write each surviving test script to a `scrutiny/` directory in the project root (e.g., `scrutiny/test_cart_concurrency.py`).
- Write the full findings report to `scrutiny/FINDINGS.md`.
- On future scrutiny invocations, check for existing files in `scrutiny/` and re-run them first — instant regression coverage for previously verified behavior.

## Synthesis report template

Present this report to the user once validation is complete. Don't ask "want me to fix?" until *after* the report is on screen.

```markdown
## Verdict
[STOP / PROCEED WITH CAUTION / CLEAN] — [N] proven bugs found.
Worst finding: [one sentence]
Recommended next action: [one sentence]

## Proven Bugs (hard evidence)
| # | Bug | Evidence | Root Cause | Confirming Agents | Fix Cost |
|---|-----|----------|------------|-------------------|----------|

[For each proven bug, include a reproduction recipe:]
### Repro: Bug #N
\`\`\`bash
[exact commands to reproduce — standalone, no project imports needed]
\`\`\`
Expected: [value]  Actual: [value]

## Likely Bugs (reference disagrees but untested)
| Issue | Reference | Our Code | Difference | Fix Cost |
|-------|-----------|----------|------------|----------|

## Agent Disagreements
| Aspect | Agent A says | Agent B says | Evidence A | Evidence B |
|--------|-------------|-------------|------------|------------|

## What We Checked (coverage map)
| Aspect | Agent | Method | Result |
|--------|-------|--------|--------|
[Framed as "this angle found nothing" — not "this is correct"]

## Not Investigated
| Angle | Why |
|-------|-----|
[Timed-out agents, skipped roles, gaps in coverage]
```

Frame the **What We Checked** table as "this angle found nothing", not "this is correct". The whole point of the coverage map is to avoid manufacturing false confidence: an unfailed test is silence, not a certificate.

Only after presenting the full report, ask: **"Want me to fix the proven bugs?"**
