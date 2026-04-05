---
name: implementation-scrutiny
description: Use when code has been written and is producing wrong results, when you suspect an implementation is incorrect but can't pinpoint why, when algorithm/logic/integration code needs verification against known-correct references, or when multiple fix attempts have failed to resolve an issue
---

# Implementation Scrutiny

## Overview

Dispatch parallel verification agents to investigate whether an implementation is correct. Each agent takes a different verification angle — finding reference implementations, writing empirical tests, checking invariants, comparing against documentation or source code.

**Evidence standard:** Every agent finding must be backed by a **validatable artifact** — either an executable script or a verifiable URL. The calling agent (you) validates every artifact before accepting it: scripts get executed via Bash, URLs get fetched via WebFetch. Findings without a validatable artifact are demoted to UNVERIFIED. Prose reasoning and derivations are supporting context, not evidence on their own.

## When to Use

- Code produces wrong output and you've already tried fixing it
- Multiple confident-sounding fix attempts have failed
- You need to verify an implementation against a known-correct reference
- The domain requires specialized knowledge (DSP, distributed systems, security, data pipelines, ML)
- You suspect a subtle logic error that reads as correct but behaves wrong

## When NOT to Use

- Code doesn't compile (fix syntax first)
- Requirements are unclear (use brainstorming first)
- The bug is obviously a typo or off-by-one (just fix it)

## Process

### Step 1: Frame the Problem

Write a clear problem statement:
- What does the code do?
- What should it do?
- What is it actually doing? (symptoms)
- What has already been tried?

Before asking the user to write this, attempt to infer it from available context: `git diff`, recent test failures, error output. Present the inferred statement for confirmation.

### Step 2: Detect Domain & Extract Invariants

**Domain detection (~1 sentence, no tools):** Classify the problem into one of: `numerical/dsp`, `web-backend/distributed`, `frontend`, `data/ml`, `database`, `security`, `general`. This determines which optional agent roles activate.

**Invariant extraction (1 fast agent):** Before dispatching the verification panel, run one agent that reads the code under scrutiny and produces a structured list of invariants — concrete, falsifiable statements:
- "After this function, X should equal Y"
- "This value should never exceed Z"
- "These two collections should have the same length"
- "This endpoint should return 401 when the token is expired"

Invariants come from the *spec or intent*, not from what the code currently does. Every verification agent receives this list as a testing target.

### Step 3: Select Verification Agents

**Mode selection:**
- **Fast (default):** 3 core agents. Use when the problem is focused and domain is clear.
- **Full:** 3 core + 3-5 domain-specific agents. Use when the problem is complex, multi-layered, or the core agents disagree.
- **Auto-escalate:** Start fast. If core agents conflict, leave gaps, or can't locate the bug, escalate to full automatically.

#### Core Agents (always dispatched)

- **Reference Hunter**: Find 2-3 known-correct implementations of the same algorithm/pattern (open-source repos, library source code, framework internals). For each reference, report: 3 behavioral similarities AND at least 1 behavioral difference vs our code. "No differences found" is a suspicious result — flag it.

- **Empirical Tester**: Write a standalone test that feeds known inputs and checks outputs against expected values. The test MUST be executed via Bash — raw stdout/stderr captured and included in the report. A test that wasn't run is not evidence.

- **Invariant Auditor**: Take the invariant list from Step 2 and verify each one independently. Re-derive expected values from first principles (mathematical, logical, or behavioral). For numerical work, show every algebraic step — no skipping. For logic, trace the execution path. For integrations, verify the contract.

#### Domain-Specific Agents (activated by domain)

**numerical/dsp:**
- Math Auditor — re-derive formulas, compute constants by hand, verify scale factors
- Platform Specialist — hardware constraints, block sizes, DMA, timing, real-time deadlines
- Performance Profiler — cycle counts, real-time budget analysis

**web-backend/distributed:**
- Concurrency Auditor — model interleavings, race conditions, lock ordering
- State Snapshot Tester — instrument before/after state around suspected operations
- API Forensic — read actual library/framework source code, verify assumptions

**frontend:**
- State Flow Auditor — render cycles, dependency arrays, state management correctness
- DOM/Layout Auditor — CSS specificity, layout reflow, accessibility compliance
- API Contract Tester — request/response shape verification

**data/ml:**
- Data Lineage Auditor — trace rows from source to sink through each transformation
- Schema Drift Detector — verify input/output shapes match at every stage
- Leakage Auditor (ML) — check for train/test contamination, label leakage

**database:**
- Query Semantics Auditor — re-derive what the SQL actually computes vs intent
- Concurrency Auditor — deadlocks, isolation level issues, dirty reads
- Migration Tester — verify schema changes preserve data and constraints

**security:**
- Threat Model Auditor — enumerate attack paths (STRIDE), write minimal PoC scaffolding
- Auth Flow Auditor — trace authentication/authorization through every code path
- Input Validation Tester — injection vectors, boundary values, encoding attacks

**general (fallback):**
- Edge Case Hunter — boundary conditions, empty inputs, maximum values, type coercion
- Regression Tester — git bisect analysis, identify the commit that introduced the bug
- API Forensic — read actual library source, verify format/calling/normalization assumptions

### Step 4: Dispatch Agents

All agents get `run_in_background: true`. Use `model: sonnet` for most agents. Use `model: opus` for the Invariant Auditor (needs stronger reasoning for derivations).

**Null Hypothesis Protocol — required for every agent:**

```
You are a verification agent. Your job is to produce VALIDATABLE ARTIFACTS — not opinions.

Before testing for bugs, first predict: "If this code is completely correct, 
what would I expect to see?" Record this prediction. Then run your tests.
Report both the prediction and the actual result.

Rules:
1. Every finding MUST include a validatable artifact:
   - A self-contained script the calling agent can execute to reproduce the finding
   - OR a URL the calling agent can fetch to verify a reference claim
   Prose reasoning alone is NOT evidence. It is supporting context.
2. "I believe" or "I think" are not findings. Write the test script.
3. If you can't produce a validatable artifact, mark the finding "UNVERIFIED"
4. Scripts must be SELF-CONTAINED — no project imports, no environment assumptions 
   beyond standard toolchains. Include the exact command to run them.
5. When citing references, provide the exact URL to a specific file or line.
   Document behavioral differences, not just "found a matching implementation."
6. Do NOT suggest fixes. Only report findings with artifacts.
7. For derivations: show every algebraic step, AND write a script that computes 
   the expected values programmatically. The script is the artifact, not the math.

Output format for each finding:
  FINDING: [one sentence]
  NULL_HYPOTHESIS: [what correct code would produce]
  ARTIFACT_TYPE: script | url
  ARTIFACT: [the script code or URL]
  RUN_COMMAND: [exact bash command to execute, if script]
  EXPECTED: [expected output if correct]
  ACTUAL: [what you observed, or "PENDING_VALIDATION" if the calling agent should run it]
  VERDICT: proven_bug | likely_bug | unverified | no_issue_found
```

**Validation Gate — the calling agent's job after collecting all agent outputs:**

For every finding with `ARTIFACT_TYPE: script`:
1. Write the script to a temp file
2. Execute via Bash
3. Capture stdout/stderr verbatim
4. Compare against EXPECTED — attach the actual output to the finding

For every finding with `ARTIFACT_TYPE: url`:
1. Fetch via WebFetch
2. Verify the URL resolves and contains the claimed content
3. If 404 or content doesn't match the claim, demote finding to UNVERIFIED

Findings that fail validation are moved to the UNVERIFIED category with a note explaining why (script errored, URL 404, output didn't match claim).

**Artifact Persistence:** After validation, write surviving test scripts to a `scrutiny/` directory in the project root (e.g., `scrutiny/test_cart_concurrency.py`). Write the full findings report to `scrutiny/FINDINGS.md`. On future scrutiny invocations, check for existing files in `scrutiny/` and re-run them first — this provides instant regression coverage for previously verified behavior.

### Step 5: Synthesize Findings

**Phase 1 — Validate all artifacts (this is the critical step):**
- Run the Validation Gate (Step 4) on every finding — execute scripts, fetch URLs
- Discard any finding that has no artifact or whose artifact failed validation
- Cross-check numerical claims: if two agents' scripts independently produce the same value, escalate confidence. If they disagree, flag as CONTESTED.
- Group by severity: PROVEN BUG (script reproduced it), LIKELY BUG (URL-backed reference disagrees), CONTESTED (agents conflict), UNVERIFIED (no valid artifact)

**Phase 2 — Present to user:**

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

Only after presenting findings, ask: "Want me to fix the proven bugs?"

## Key Rules

- **Minimum 3 agents** in fast mode, 6+ in full mode
- **Every finding needs a validatable artifact** — an executable script or a fetchable URL. No exceptions.
- **The calling agent validates every artifact** — run scripts, fetch URLs. Unvalidated findings are UNVERIFIED.
- **Null hypothesis first** — predict correct behavior before testing for bugs
- **References must show differences** — not just "found a match"
- **Derivations must include a computation script** — the math is context, the script is the evidence
- **Do NOT fix during scrutiny** — report findings only. Fixing while investigating contaminates the investigation
- **Domain-aware role selection** — use the right specialists for the problem
- **Persist artifacts** — validated test scripts go to `scrutiny/`, reusable across sessions
- **Coverage map, not false confidence** — "we didn't find bugs here" ≠ "this is correct"
- **Surface conflicts** — when agents disagree, show both sides, don't silently resolve

## Anti-Patterns

- Don't let agents suggest fixes (they'll anchor on the first plausible fix)
- Don't skip the empirical tester (theory-only analysis is what got us here)
- Don't trust math derivations without a computation script that produces the same answer
- Don't accept "the documentation says X" without reading actual source code
- Don't accept a finding without running its script or fetching its URL yourself
- Don't stop at the first bug found (there are usually multiple)
- Don't accept "reference found" without documented behavioral differences
- Don't present "Verified Correct" — present "What We Checked" instead
- Don't use DSP-specific roles for non-DSP problems (detect the domain first)
- Don't dispatch 10 agents when 3 would suffice (start fast, escalate when needed)
- Don't trust an agent's "ACTUAL" output — run the script yourself and compare

## Example: Web Backend Race Condition

**Problem:** Shopping cart API occasionally shows stale item counts after concurrent add/remove operations. Multiple fix attempts (adding locks, retry logic) each fixed the test case but broke under load.

**Domain detected:** web-backend/distributed

**Invariant Extractor found:** "cart.items.length should equal the number of successful add operations minus successful remove operations" and "concurrent operations on the same cart should serialize."

**Reference Hunter found:** Three cart implementations (Shopify Liquid, Medusa.js, Saleor) all use optimistic locking with version counters. Our code uses last-write-wins without versioning. Behavioral difference: all references reject stale writes; ours silently overwrites.

**Empirical Tester found:** Test with 10 concurrent add operations on the same cart. Expected: 10 items. Actual: 7-9 items (varies per run). Test executed, stdout captured.

**Concurrency Auditor found:** The `updateCart` function reads current state, modifies in memory, then writes back without any atomicity guarantee. Between read and write, another request can interleave. Traced three specific interleaving paths that produce data loss.

**Result:** Proven bug with triple-source evidence. Root cause: missing optimistic concurrency control. The previous "fix" (adding a mutex) only worked in single-process mode; under load balancing, requests hit different processes and the mutex is local.
