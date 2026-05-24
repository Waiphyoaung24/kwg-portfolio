# CLAUDE.md

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

## 5. Website Design — Use Taste Skills

When the task involves **designing, redesigning, building, or styling a website / page / UI component**, invoke the relevant skill(s) from `.agents/skills/` (installed from `Leonxlnx/taste-skill`) BEFORE writing markup or styles. Don't freestyle — these skills encode the intended visual taste for this project.

### Skill → trigger mapping

Pick by intent. Multiple skills can compose (e.g. `brandkit` + `industrial-brutalist-ui` + `full-output-enforcement`).

| Skill | Use when… |
|---|---|
| `brandkit` | Establishing or applying brand tokens (color, type, spacing, logo usage) across the site. |
| `industrial-brutalist-ui` | User asks for a brutalist, raw, high-contrast, industrial, or editorial aesthetic. |
| `minimalist-ui` | User asks for minimal, clean, whitespace-driven, "less is more" design. |
| `high-end-visual-design` | Premium / luxury / agency-grade polish: refined type, motion, micro-detail. |
| `gpt-taste` | Need a balanced, modern, "good-default" aesthetic when no strong direction is given. |
| `stitch-design-taste` | Crafted, hand-finished, tactile feel — when stitch/craft visual language fits. |
| `design-taste-frontend` | General frontend-flavored taste pass on existing markup/components. |
| `image-to-code` | User supplies a reference image / screenshot / mockup to translate into code. |
| `imagegen-frontend-web` | Generating web/desktop UI imagery or visual references before implementing. |
| `imagegen-frontend-mobile` | Generating mobile UI imagery or visual references before implementing. |
| `redesign-existing-projects` | Refreshing or overhauling an existing page/component while preserving structure. |
| `full-output-enforcement` | Apply on any design task to enforce complete, production-ready output (no stubs, no TODOs, no partial returns). |
| `impeccable` | Final-pass polish for typography, spacing, alignment, and visual rhythm. |

### Workflow for any design task

1. **Identify aesthetic direction** from the user's wording. If unclear, ask before picking a skill.
2. **Invoke the matching skill(s)** via the Skill tool. Always include `full-output-enforcement` for build tasks and `impeccable` for the final pass.
3. **Apply project brand** with `brandkit` whenever site-wide consistency matters.
4. **Then** write the Astro/CSS/component code, following the skill's guidance.

If none of the above clearly fits, say so and ask the user which direction to take rather than silently defaulting.
