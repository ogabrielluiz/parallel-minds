# The nine-rule STE subset

The audit rules used by step 2 of [SKILL.md](SKILL.md). Each rule below states the check, the failure it causes in a fanned-out plan, and a rewrite.

## Provenance and scope

These nine rules are a subset of ASD-STE100 Simplified Technical English (Issue 9, January 2025), a controlled language maintained by the Aerospace, Security and Defence Industries Association of Europe. The full standard is 53 rules plus a dictionary of roughly 900 approved words.

The dictionary is deliberately out of scope. It bans terms like "instantiate", "coroutine", and "migrate", which costs precision in an engineering plan. So is the rule against `-ing` forms, which fights code and package naming. What remains is the part that survives translation from aircraft maintenance to agent execution: the rules that remove more than one reading from a sentence.

Nothing here certifies STE compliance. This is a clarity audit, not an authoring system.

## The rules

**1. One instruction per sentence.** Never join two actions with "and" or "then".

A reader executes the first action and drops the second. In a swarm, different readers drop different halves.

- Violation: "Move the converter to `lfx` and update the registry."
- Rewrite: "Move the converter to `lfx`. Update the registry."

**2. Imperative and active.** No passive voice, no "should", no "needs to be".

Passive hides the actor. "Should" reads as optional to one agent and mandatory to another.

- Violation: "The adapter should be registered."
- Rewrite: "Register the adapter."

**3. One verb per action, reused.** Do not rotate synonyms for the same operation.

Rotating update / adjust / tweak / refactor / clean up across tasks makes a reader ask whether those are four different operations. Pick one verb and repeat it, even when the repetition reads flat.

- Violation: task 2 "update the schema", task 5 "adjust the schema", task 8 "clean up the schema".
- Rewrite: all three say "update the schema".

**4. Condition before command.**

A reader processes the sentence in order and commits to the action before reaching the guard.

- Violation: "Revert the migration if the tests fail."
- Rewrite: "If the tests fail, revert the migration."

**5. No cross-sentence pronouns.** Repeat the noun instead of "it", "this", "that", "the former".

Pronoun resolution across sentences is where independent readers split most often, and the split is silent — each reader is confident.

- Violation: "Load the adapter from the registry. It must be idempotent."
- Rewrite: "Load the adapter from the registry. The adapter must be idempotent."

**6. Keep articles and subjects.** Do not compress by dropping words.

- Violation: "Add handler to registry."
- Rewrite: "Add the handler to the task registry in `src/lfx/registry.py`."

**7. Noun clusters of three words maximum.**

Four or more stacked nouns have no unambiguous parse. "The agent task queue priority handler" could be five different objects.

- Violation: "the agent task queue priority handler"
- Rewrite: "the priority handler for the agent task queue"

**8. Twenty words maximum per instruction.**

Past twenty words a reader starts partially executing. Split the sentence rather than trimming words, which usually means violating rule 6.

**9. Vertical list for any sequence of three or more steps.**

Procedural steps buried in prose get collapsed or reordered. A numbered list is read as a numbered list.

## Rules deliberately not enforced

- The ~900-word approved dictionary. Loses technical precision.
- The ban on `-ing` forms. Conflicts with code identifiers and package names.
- American-only spelling. Irrelevant to machine readers.
- The 25-word cap on descriptive (non-instruction) prose. Loose enough that it never binds; rule 8 covers what matters.

## Where this applies

Plans, specs, task descriptions, tool descriptions, and error messages — text whose reader cannot ask a follow-up question.

It does not apply to PR comments, code review, commit messages, or chat. Those have a human reader who can ask, and STE's flatness reads as brusque.
