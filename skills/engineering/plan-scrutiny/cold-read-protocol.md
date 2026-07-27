# Cold Read Protocol

Every reader dispatched by the plan-scrutiny skill receives the prompt block below. It establishes the rules of engagement — interpret rather than critique, commit rather than ask, invent visibly rather than silently — and pins down the exact output format the calling agent parses when measuring divergence.

Paste the block verbatim into each reader's prompt, with the plan text appended. Do not paraphrase the rules or the output format; the divergence measurement depends on readers answering the same question the same way.

## Reader prompt block

```
You are about to execute one task from the plan below. You have no other context:
no conversation history, no design doc, no tour of the repository. Whatever the
plan does not say, you must decide for yourself.

For EVERY task in the plan, report what you would actually do.

Rules:
1. COMMIT. Never answer "I would ask what X means" or "this is unclear."
   You cannot ask anyone. Pick the reading you would act on and state it.
2. INTERPRET, do not critique. Do not rate the plan, flag vagueness, or suggest
   improvements. Report only the work you would perform.
3. Name FILES. State the exact paths you would create, modify, or read. If the
   plan does not name a file, name the one you would choose.
4. Mark INVENTION. Any detail you supplied that the plan did not state — a file
   path, a function name, a test location, an ordering — must be listed under
   INVENTED. This is the most important field. Do not omit it to look decisive.
5. State the DONE condition. How would you know this task is finished?
6. Do not read any file in the repository. Answer from the plan text alone.
7. Do not look at, wait for, or reference any other reader's output.

Output format, repeated once per task:
  TASK: [number and title as written in the plan]
  ACTION: [one sentence: what you would do]
  FILES: [exact paths, comma-separated]
  DONE_WHEN: [the completion condition you would use]
  INVENTED: [details you supplied that the plan did not state, or "none"]
  CONFIDENCE: high | low
```

## Notes for the dispatching agent

- Use `run_in_background: true` and `model: sonnet` for every reader. Panel size comes from the mode: `fast` is 3, `full` is 5.
- Dispatch all readers in a single message so they run concurrently and cannot observe each other. Sequential dispatch risks contaminating later readers through shared session state.
- Send the plan text inline in the prompt. Sending a file path invites the reader to explore the repository, which restores exactly the context the probe is built to remove.
- Vary nothing between readers. Identical prompts are the point — divergence must come from the plan, not from different instructions. This differs from a creative-consensus panel, where per-agent angles are assigned deliberately.
- A reader that returns critique instead of interpretation has failed rule 2 and its output is unusable as a divergence signal. Re-dispatch it; do not hand-convert its critique into an interpretation.
- `INVENTED: none` across every reader on a task is a strong convergence signal. A task where readers invented different values is a `SPLIT` even when their `ACTION` lines happen to match.
- `CONFIDENCE: low` on a task all readers agreed about is still `CONVERGENT`. Record the hedge in the report, but low confidence alone is an opinion, and this skill measures divergence.
