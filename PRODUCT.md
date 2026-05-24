# Product

## Register

brand

> Primary surface is brand (portfolio = design IS the product). One product-style sub-surface lives at `/my-portfolio` (the 3D constellation), which can override to a quieter, more utilitarian set of rules when worked on directly.

## Users

Peers and community: practicing designers, developers, and other creatives. They arrive curious, fluent in craft language, and skeptical of marketing. Their context is a casual scroll, often on desktop, often via a referral or a "show me what they've built" link. The job to be done is exploration: see the work, read the decisions, judge the taste, decide whether this person is worth talking to.

The primary action is exploration of the work itself, not a contact form submission. Hiring or collaboration interest is a downstream consequence of being convincing.

## Product Purpose

This site is a portfolio that proves taste and discipline to other practitioners. It exists because peer respect is the leverage that produces opportunities, and peer respect is won on craft, not on credentials. Success looks like a fellow designer or engineer landing on the site, stopping the scroll, and forming a specific impression: "this person has a point of view, knows what they're doing, and has shipped real things."

It is not a lead funnel. It is not a résumé. It is an exhibit.

## Brand Personality

**Three words:** aggressive, theatrical, exclusive.

**Voice:** declarative. Short sentences. No throat-clearing. When the work needs explanation, the explanation is technical and specific, not promotional. Confidence is shown, never claimed. The site never says "passionate" or "results-driven." Capability is demonstrated through the artifacts on display.

**Tone:** Nocturnal performance. The feeling of walking through a darkened gallery where each piece is lit individually. Visitors should feel they are being shown something deliberately, not invited to browse a catalog.

**Emotional goals:** respect from peers, intrigue from outsiders, a quiet certainty in the visitor that the person behind this site is precise about what they make and why.

## Anti-references

Things this must never look like, in order of priority:

1. **Generic dev portfolio: dark + neon + glassmorphism.** No neon accents, no frosted-glass cards, no gradient text, no animated-particle hero. The "AI made that" first-order reflex for technical portfolios is the explicit enemy.
2. **The SaaS hero-metric template.** Big number, small label, supporting stats, gradient accent block: outlawed. No "10x productivity," no fake usage stats, no metric-card grids.
3. **The crypto / AI / wrapper-tool aesthetic family.** Neon-on-black with grid backgrounds, gradient buttons, "powered by GPT" badges, and shimmer animations. The second-order reflex is also out.
4. **Corporate agency polish.** Stock-photo hero, vague capability list, "we craft experiences" copy, case-study-as-marketing-funnel. Even when the visual system is loud, the writing must not be hollow.
5. **Awwwards-bait spectacle.** Scroll-jacked WebGL playgrounds with no point. Motion serves the work, not the demo reel.

The brand fights for the same lane as Lamborghini's marketing site, not as Vercel templates or Linear screenshots.

## Design Principles

1. **The work speaks; the chrome amplifies it.** The Lamborghini-loud visual system is the stage, not the show. Every section asks: does this make the work clearer, or louder than the work?
2. **Show, don't tell.** Peers do not read marketing copy. Replace adjectives with artifacts. Replace claims with screenshots, code, and decisions.
3. **Theatrical form, technical substance.** Darkness, gold, and all-caps are the surface. Underneath, every effect is intentional, measured, and defensible. If a flourish cannot be justified in one sentence, it is removed.
4. **Reject the category reflex.** When a design choice matches the first-order expectation for "developer portfolio," that is the signal to rework it. The site should be guessable as a portfolio only after seeing the work, never from the chrome alone.
5. **Peer-trust over impression management.** Resist credentials, logos, badges, and social proof unless they are doing genuine work for the viewer. A peer trusts evidence; this site offers evidence.

## Accessibility & Inclusion

**WCAG 2.2 AA** is the floor for contrast, focus visibility, and keyboard operability. Specifically:

- All body text on the dominant black canvas meets 4.5:1 contrast. The `#7D7D7D` Ash neutral is borderline; reserve it for non-essential metadata, never for primary copy or interactive labels.
- Lamborghini Gold (`#FFC000`) on `#000000` measures well above AA for non-text use, but text set on gold (or gold set on white) must be re-checked per pairing.
- Focus indicators are always visible, never removed. The brand's "no decorative chrome on interactive states" rule does not extend to focus rings.

**Reduced motion is respected.** All transitions and scroll-driven effects gate on `prefers-reduced-motion: reduce`. Motion is an enhancement, never load-bearing for comprehension. The hero video carries no information that text alone cannot convey.

**Keyboard navigation works end-to-end.** Every interactive element is reachable and operable without a pointer. The custom cursor and hover-driven affordances have keyboard equivalents.

**Color is never the sole carrier of meaning.** Gold marks "primary action," but primary actions are also distinguishable by weight, position, and label.
