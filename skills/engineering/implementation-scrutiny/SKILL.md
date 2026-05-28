---
name: implementation-scrutiny
description: Use when code has been written and is producing wrong results, when you suspect an implementation is incorrect but can't pinpoint why, when algorithm/logic/integration code needs verification against known-correct references, or when multiple fix attempts have failed to resolve an issue
---

# Implementation Scrutiny

Dispatch parallel verification agents to investigate whether an implementation is correct. Each agent attacks the problem from a different angle — hunting reference implementations, writing empirical tests, auditing invariants, comparing against framework source — and every finding lands as a validatable artifact you can re-run.

## Philosophy

**Core principle**: every finding needs a validatable artifact. Prose reasoning is not evidence.

A "validatable artifact" is one of two things: a self-contained script the calling agent can execute via Bash, or a URL the calling agent can fetch via WebFetch. The calling agent — you — validates every artifact before accepting it. Scripts get run, URLs get fetched, outputs get compared. Findings that can't survive that gate are demoted to UNVERIFIED.

Two consequences fall out of this:

- **Don't fix during scrutiny.** Reporting and fixing are different jobs; mixing them anchors the investigation on the first plausible patch. Only after the synthesis is presented does anyone touch the code.
- **Present coverage maps, not certificates.** "This angle found nothing" is not "this is correct." Surface the gaps explicitly so the user knows what was actually checked.

## When to Use

Use when code produces wrong output and you've already tried fixing it, when multiple confident-sounding fixes have failed, when you need to verify an implementation against a known-correct reference, when the domain needs specialized knowledge (DSP, distributed systems, security, data pipelines, ML), or when you suspect a subtle logic error that *reads* correct but *behaves* wrong.

Skip it when code doesn't compile (fix syntax first), when requirements are unclear (brainstorm first), or when the bug is obviously a typo or off-by-one (just fix it).

## Workflow

### 1. Frame the problem

Write a short problem statement: what the code does, what it should do, what it's actually doing, and what's already been tried. Before asking the user for this, infer it from `git diff`, recent test failures, and error output, then present the inferred statement for confirmation.

### 2. Detect domain & extract invariants

**Domain detection** (one sentence, no tools): classify the problem as `numerical/dsp`, `web-backend/distributed`, `frontend`, `data/ml`, `database`, `security`, or `general`. This determines which optional agent roles activate — using DSP roles on a web bug wastes context.

**Invariant extraction** (one fast agent): read the code under scrutiny and produce a structured list of falsifiable statements pulled from the *spec or intent*, not from what the code currently does. Examples: "after this function, X should equal Y", "this value should never exceed Z", "these two collections should have the same length", "this endpoint should return 401 when the token is expired". Every verification agent receives this list as a testing target.

### 3. Select verification agents

**Fast mode (default):** three core agents. Use when the problem is focused and the domain is clear.
**Full mode:** three core + three to five domain-specific. Use when the problem is layered or core agents disagree.
**Auto-escalate:** start fast; if core agents conflict, leave gaps, or can't locate the bug, escalate.

The three **core agents** always dispatch:

- **Reference Hunter** — finds 2–3 known-correct implementations of the same algorithm or pattern. For each, reports 3 behavioral similarities **and at least 1 behavioral difference** vs our code. "No differences found" is suspicious — flag it. Don't accept "reference found" without documented differences.
- **Empirical Tester** — writes a standalone test that feeds known inputs and checks outputs. The test **must be executed**; raw stdout/stderr goes into the report. A test that wasn't run is not evidence. Skipping this agent is what got us here in the first place — theory-only analysis is the failure mode being corrected.
- **Invariant Auditor** — takes the invariant list from step 2 and verifies each one. Re-derives expected values from first principles. For numerical work, shows every algebraic step *and* writes a script that computes the same answer. The math is context; the script is the evidence.

See [domain-agents.md](domain-agents.md) for the per-domain agent catalog (numerical/dsp, web-backend/distributed, frontend, data/ml, database, security, general).

### 4. Dispatch agents

All agents run with `run_in_background: true`. Use `model: sonnet` for most agents; use `model: opus` for the Invariant Auditor (derivations need stronger reasoning). Start with three agents in fast mode, six-plus in full mode — don't dispatch ten when three would suffice.

Every agent receives the **Null Hypothesis Protocol**: predict what correct code would produce *before* testing for bugs, then report prediction and result. Findings must come back as scripts or URLs, never as opinions. Agents must not suggest fixes — fix-suggestions anchor everyone on the first plausible patch.

See [null-hypothesis-protocol.md](null-hypothesis-protocol.md) for the full agent prompt template and required output format.

### 5. Synthesize findings

Collect all agent output, then run the **Validation Gate** before trusting anything:

- For every `ARTIFACT_TYPE: script` finding, write the script, execute it via Bash, capture stdout/stderr verbatim, and compare against EXPECTED. Don't trust an agent's `ACTUAL` line — run it yourself.
- For every `ARTIFACT_TYPE: url` finding, fetch via WebFetch and confirm the cited content exists. 404 or content mismatch demotes the finding to UNVERIFIED.
- Don't stop at the first bug — there are usually several.
- Cross-check: if two independent scripts produce the same value, escalate confidence; if they disagree, mark CONTESTED and surface both sides instead of silently resolving.

Group findings into PROVEN BUG / LIKELY BUG / CONTESTED / UNVERIFIED, persist validated scripts to `scrutiny/`, and present a coverage map rather than a "Verified Correct" stamp. Only after presenting findings, ask: "Want me to fix the proven bugs?"

See [validation-gate.md](validation-gate.md) for the validation procedure, artifact persistence rules, and the synthesis report template.

## Example: Web Backend Race Condition

**Problem:** Shopping cart API occasionally shows stale item counts after concurrent add/remove operations. Multiple fix attempts (adding locks, retry logic) each fixed the test case but broke under load.

**Domain detected:** web-backend/distributed.

**Invariant Extractor found:** "cart.items.length should equal the number of successful add operations minus successful remove operations" and "concurrent operations on the same cart should serialize."

**Reference Hunter found:** Three cart implementations (Shopify Liquid, Medusa.js, Saleor) all use optimistic locking with version counters. Our code uses last-write-wins without versioning. Behavioral difference: all references reject stale writes; ours silently overwrites.

**Empirical Tester found:** Test with 10 concurrent add operations on the same cart. Expected: 10 items. Actual: 7–9 items (varies per run). Test executed, stdout captured.

**Concurrency Auditor found:** The `updateCart` function reads current state, modifies in memory, then writes back without any atomicity guarantee. Between read and write, another request can interleave. Traced three specific interleaving paths that produce data loss.

**Result:** Proven bug with triple-source evidence. Root cause: missing optimistic concurrency control. The previous "fix" (adding a mutex) only worked in single-process mode; under load balancing, requests hit different processes and the mutex is local.
