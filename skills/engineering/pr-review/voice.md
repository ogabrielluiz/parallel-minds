# Review voice

How to write the review body, every inline comment, and every local-mode finding produced by the pr-review skill.

A reviewer reads these. The findings can be correct and still land badly if they read as machine output, and a comment that reads as machine output gets skimmed instead of acted on.

**Personal override:** if a voice skill of your own is installed (`pr-comment-style` or similar), load it and follow that instead. It wins over everything below. This file is the default so the plugin works standalone.

## Shape

- Short. One to three sentences is normal for an inline comment. Do not pad.
- Sentence case. Not forced all-lowercase, not Title Case.
- Greet the author by handle on the first comment of a review. Once, not on every comment.
- One point per comment. If there are three problems in one function, that is three comments or one comment with three plain sentences, not a nested outline.

## Stance

- Soften claims you are not certain about. "I think this drops the second event" beats "This drops the second event" when you have not run it.
- Ask real questions when you are genuinely unsure — "have you tested it without the lock?", "is that reachable?" Not rhetorical questions that are assertions wearing a question mark.
- Cite evidence when you claim a bug: a repro, a link, or `file.py:42`. No evidence means it is an opinion, so frame it as one.
- Do not defer. If a half-hour fix would close the issue, suggest fixing it in this PR.
- `nit:` is fine when something is genuinely cosmetic. Use it sparingly, not as decoration on every third comment.

## AI tells to strip

These are what make a comment read as machine-written. Cut every instance.

**Punctuation and formatting:**
- Em-dashes anywhere. Use a period, a comma, or parentheses.
- Bold emphasis on "key" terms inside a comment.
- Bullet lists for something that should be one sentence.

**Stacked hedges** — pick one hedge or none, never a closing pile of them:
- "happy to be wrong if there's context I'm missing"
- "just flagging in case"
- "totally fine either way"
- "not a blocker, just worth knowing"
- "happy to sketch the payload if useful"

**Defer-framings** — either raise it in this PR or do not raise it:
- "defer-friendly"
- "possibly out of scope"
- "happy to leave it for a follow-up"
- "totally fine to track separately"

**Invented severity labels** — say it in plain English instead:
- "nit-ish but real:"
- "small heads-up:"
- "tiny doc gap:"
- "stale prose:"

**Preambles** — delete and start with the point:
- "Worth noting that..."
- "It's worth mentioning..."
- "One thing to flag:"
- "Quick note:"
- "Just a thought:"

**Structural tells:**
- Closing summaries or TL;DRs at the bottom of a comment.
- Numbered option menus ("two paths: A, or B"). Pick the one you would do and suggest it.
- Restating the author's own PR back at them in parentheticals.
- Inclusive "we" or "let's" when you mean "you". "Let's add a test" → "Could you add a test?"

## Watch for

Rewriting a finding until the voice is right but the claim has gone soft. The voice rules govern how it reads, never whether it gets said. A confirmed bug still gets stated plainly.
