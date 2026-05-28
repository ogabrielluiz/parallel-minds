# parallel-minds

A Claude Code plugin distributing skills that orchestrate parallel agent swarms.

## Repo layout

- `skills/<category>/<name>/SKILL.md` — installable skills. Categories in use: `design/`, `engineering/`.
- Each skill folder may contain sidecar `.md` files (e.g., `recipes.md`, `domain-agents.md`) that the SKILL.md references via relative links. The SKILL.md stays lean; sidecars hold reference material.
- `.claude-plugin/plugin.json` + `marketplace.json` — Claude Code plugin marketplace metadata.
- `CONTEXT.md` — domain glossary. Read this before writing about recipes, modes, panels, angles, or null hypotheses, so naming stays consistent across skills.

## Install (downstream consumers)

Two routes:

- `npx skills@latest add ogabrielluiz/parallel-minds` — the [skills CLI](https://github.com/vercel-labs/skills). Discovers SKILL.md files via the catalog layout (`skills/<category>/<name>/SKILL.md`).
- `claude plugin marketplace add https://github.com/ogabrielluiz/parallel-minds` then `claude plugin install parallel-minds` — the Claude Code plugin marketplace.

## When editing skills

- Frontmatter must be exactly `name` + `description`. No `version`, no `metadata` block, no `author` — the skills CLI is strict, and Claude Code's plugin loader treats extra fields as noise.
- Keep the SKILL.md the executive playbook. Long lists, tables, agent prompt templates, and protocols belong in sidecar files referenced by relative link.
- Reshape guidance into workflow steps rather than freestanding `## Key Rules` / `## Anti-Patterns` blocks. Anti-patterns and rules become inline "Watch for:" callouts inside the step where they apply. Match the tone of the existing skills in this repo.
- New skills go under an existing category folder (`design/` or `engineering/`), or a new sibling category if neither fits.
- After editing, do not delete the old skill location until you've verified the new one parses cleanly with `npx skills find` locally.
