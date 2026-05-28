# Specialist catalog

The specialists `pr-review` dispatches in Phase 2. Always-on specialists run on every PR. Conditional specialists run only when their trigger condition is met. Narrower specialists spawn only when the diff has substantial presence in their area — otherwise the always-on agents cover that ground.

All specialists return findings into the same pool and go through the same validator in Phase 3.

## Always-on

- **Bugs & Behavior** — bugs, logic errors, edge cases, error handling, silent failures, tests of changed code. Concrete triggering input required per finding.
- **Fit** — repo standards (`AGENTS.md`, `CLAUDE.md`, ADRs) + structural quality (no spaghetti growth, no thin wrappers, no canonical-helper duplication, no feature logic in shared modules, no casts hiding invariants, prefer restructurings that delete complexity).

## Conditional

- **Spec** — only when a spec source exists (ticket, PRD, design doc surfaced in Phase 1.5). Missing requirements, scope creep, wrong implementation. Each finding quotes the spec line it's checking against.

## Narrower specialists

Spawn only when the diff has substantial presence in their area; otherwise the always-on agents cover it. The thresholds below are guidelines, not hard rules — the dispatcher decides based on the diff shape.

- **Error-handling** — broad `except`/`catch`, swallowed errors, fallbacks to mocks. Spawn when the diff adds 5+ exception-handling blocks.
- **Type design** — new types/dataclasses/Pydantic/Zod models. Spawn when the diff adds substantial type definitions.
- **Test quality** — coverage of new behavior, no-mock convention, test correctness. Spawn when the diff adds or modifies a substantial number of tests without corresponding production changes (or vice versa).

The narrower specialists return findings to the same pool as the always-on ones and go through the same validator.
