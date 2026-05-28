# Angle Libraries

Each domain has its own catalog of angles. In step 2 of the workflow, fill all slots beyond the three mandatory roles (regret, wildcard, saboteur) from the matching library. If the domain is unclear or cross-cutting, use the General fallback.

Don't reuse the same angles across domains — the whole point is that the swarm attacks the problem in shapes that fit the problem.

## Systems Architecture

- simplest-possible design
- failure-first
- data flow direction
- ownership boundaries
- cost at scale
- what gets deleted first
- reversibility

## API Design

- consumer-first (outside-in)
- versioning story
- idempotency
- error expressiveness
- "3am on-call" perspective
- what the SDK looks like

## Data Modeling

- access-pattern-driven
- denormalize deliberately
- temporal (what changes over time?)
- deletion semantics
- audit trail
- migration story

## Security

- attacker's perspective
- least privilege taken literally
- trust boundary inversion
- "what if this credential leaks?"
- blast radius minimization
- compliance-first

## DevOps / Infra

- what breaks at 2x load
- rollback story
- observability-first
- toil elimination
- what a new engineer breaks first
- cost optimization

## UX / Product

- first-use experience
- power-user path
- accessibility-first
- error recovery journey
- emotional arc
- what makes users tell a friend

## General (fallback)

- minimalist
- maximalist
- constraint-flip
- metaphor-driven
- temporal / rhythmic
- textural
- reference-based
- emotional
- user-experience
