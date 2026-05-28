# Domain-Specific Agents

Once the domain is classified in workflow step 2, the matching agent roles below activate alongside the three core agents (Reference Hunter, Empirical Tester, Invariant Auditor). In **fast mode** only the core three dispatch; in **full mode** add three to five of the domain roles below. If the classifier picks `general`, use the general fallback set.

Don't mix domains — using DSP-specific roles on a web bug wastes context and produces noise. Detect the domain first, then pick from the matching section.

## numerical/dsp

- **Math Auditor** — re-derive formulas, compute constants by hand, verify scale factors. Every derivation must be paired with a script that computes the same answer programmatically.
- **Platform Specialist** — hardware constraints, block sizes, DMA, timing, real-time deadlines.
- **Performance Profiler** — cycle counts, real-time budget analysis.

## web-backend/distributed

- **Concurrency Auditor** — model interleavings, race conditions, lock ordering. Trace specific interleaving paths that produce the bug.
- **State Snapshot Tester** — instrument before/after state around suspected operations and dump it as the artifact.
- **API Forensic** — read actual library/framework source code, verify assumptions. "The documentation says X" is not acceptable without a link to source.

## frontend

- **State Flow Auditor** — render cycles, dependency arrays, state management correctness.
- **DOM/Layout Auditor** — CSS specificity, layout reflow, accessibility compliance.
- **API Contract Tester** — request/response shape verification.

## data/ml

- **Data Lineage Auditor** — trace rows from source to sink through each transformation.
- **Schema Drift Detector** — verify input/output shapes match at every stage.
- **Leakage Auditor (ML)** — check for train/test contamination, label leakage.

## database

- **Query Semantics Auditor** — re-derive what the SQL actually computes vs intent.
- **Concurrency Auditor** — deadlocks, isolation level issues, dirty reads.
- **Migration Tester** — verify schema changes preserve data and constraints.

## security

- **Threat Model Auditor** — enumerate attack paths (STRIDE), write minimal PoC scaffolding.
- **Auth Flow Auditor** — trace authentication/authorization through every code path.
- **Input Validation Tester** — injection vectors, boundary values, encoding attacks.

## general (fallback)

- **Edge Case Hunter** — boundary conditions, empty inputs, maximum values, type coercion.
- **Regression Tester** — git bisect analysis; identify the commit that introduced the bug.
- **API Forensic** — read actual library source, verify format/calling/normalization assumptions.
