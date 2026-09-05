# AGENTS.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

## 5. Website Design — DESIGN.md Is Law

`DESIGN.md` at the repo root is the single source of visual truth. It records the
project's design system: an interpretation of x.ai's web language. `PRODUCT.md`
records durable product truth. Read both before writing or changing any markup,
style, or component.

### Rules

- **Read `DESIGN.md` first.** Tokens, type ladder, component specs, and the
  Do's and Don'ts list are binding. When a request conflicts with it, say so
  and ask rather than silently splitting the difference.
- **Use the tokens, never raw values.** Colors, spacing, radii, type sizes and
  easings all live in `src/styles/_vars.scss`. A hex code or a px value in a
  component is a bug unless the file comment explains why.
- **Reuse the primitives.** `.pill-btn`, `.pill-btn--filled`, `.card`, `.label`
  and `.micro` live in `src/styles/`. Do not hand-roll a button.
- **The hard rules from `DESIGN.md`:** near-black canvas only, no light mode.
  Weight 400 everywhere; the system never bolds. Every interactive element is a
  pill. Outline pills by default, one filled white pill for the primary action
  per view. Hairline borders carry elevation; there are no shadows. Negative
  tracking on display sizes. Mono, uppercase, positively tracked for labels.
  The sunset/dusk accent colors are for illustration only, never chrome.
- **Accessibility floor is WCAG 2.2 AA**, per `PRODUCT.md`. The `--c-mute`
  neutral is metadata only; it does not meet the body-text ratio.

### Design work

For substantive design work — building a new surface, redesigning an existing
one, auditing, or polishing — use the `impeccable` skill (`/impeccable <command>`).
It reads `PRODUCT.md` and `DESIGN.md` as its context automatically. Do not
freestyle a visual direction, and do not import an aesthetic from another
design system.

### Exhibited work is exempt

Content on display is not site chrome and keeps its own styling:
`src/catalog/kage/` and any future catalog demo. The frame around an exhibit
follows the design system; the exhibit itself does not.
