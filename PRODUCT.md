# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Register

brand

> Primary surface is brand (portfolio = design IS the product). One product-style sub-surface lives at `/my-portfolio` (the 3D constellation), which can override to a quieter, more utilitarian set of rules when worked on directly. The `/vault` tools are private operate-mode surfaces behind an obscurity gate.

## Users

Two audiences, in priority order.

**Peers and community:** practicing designers, developers, and other creatives. They arrive curious, fluent in craft language, and skeptical of marketing. Their context is a casual scroll, often on desktop, often via a referral or a "show me what they've built" link. The job to be done is exploration: see the work, read the decisions, judge the taste, decide whether this person is worth talking to.

**Prospective clients:** founders, operators, and teams who need a site, an internal system, or a commissioned build. They arrive from a referral or a search, less fluent in craft language, and want to know three things quickly: what kind of work gets done here, whether it is good, and how to start a conversation. Their job is to reach a confident "send the email" moment without being sold to.

## Product Purpose

This site is a portfolio that proves taste and discipline to other practitioners, and that turns that proof into client conversations. Peer respect is the leverage that produces opportunities, and it is won on craft, not on credentials. Client acquisition is the second explicit goal: the same evidence that earns peer respect is what a prospective client needs to trust the work.

Success looks like a fellow designer or engineer landing on the site, stopping the scroll, and forming a specific impression: "this person has a point of view, knows what they're doing, and has shipped real things." For a prospective client, success is a short email that opens with "I saw the X project."

It is not a lead funnel with gates, forms, and follow-up sequences. It is an exhibit with one clear door: email.

## Positioning

Three kinds of work sit here: sites where the interface carries the argument, internal systems built for people who live in them all day, and commissioned builds shaped to one operation rather than a template. The distinguishing mechanism is that every piece on display is accompanied by its decisions, its stack, and where it runs. Evidence replaces claims.

## Operating Context

- Built with Astro on Node, deployed via Docker Compose to Dokploy. Postgres backs the vault tools.
- Public surfaces: Home, Works, Catalog (copyable components and demos), My Portfolio (3D constellation), About.
- Private surfaces under `/vault`: Fitness reference browser and workout generator, Projects tracker, and links out to self-hosted Notes and Finance tools.
- Contact is a single email address. There is no CRM integration, booking tool, or contact form on the site.

## Capabilities and Constraints

- The Catalog exhibits real components with copyable source. Each entry frames a live demo; the demo keeps its own styling because it is the exhibited artifact, not site chrome.
- The Kage landing page under Catalog is a standalone piece of exhibited work with its own typeface and palette. It does not adopt the site design system.
- Vault pages own their own `<html>` and do not use the shared Layout. They share the global tokens and typography but render no site header or footer.
- Social profile URLs are not yet supplied. Footer links to GitHub and LinkedIn are placeholders until they are.
- Undecided: whether a booking link or contact form will ever be added. Until decided, email is the only contact path.

## Brand Commitments

**Name:** KWG. The wordmark is the three letters set in the display face; there is no logo mark.

**Three words:** precise, restrained, engineered.

**Voice:** declarative. Short sentences. No throat-clearing. When the work needs explanation, the explanation is technical and specific, not promotional. Confidence is shown, never claimed. The site never says "passionate" or "results-driven." Capability is demonstrated through the artifacts on display.

**Tone:** a research lab announcing its work. Sparse, unmarketed, exact. Visitors should feel they are being shown something deliberately, with nothing added for effect.

**Visual world:** the design system recorded in DESIGN.md is binding. It is an interpretation of x.ai's web language: a single near-black canvas, white as the only brand colour, outline pills as the interactive vocabulary, a geometric sans at weight 400 with tight negative tracking for display, and an uppercase tracked monospace for eyebrows and labels.

**Emotional goals:** respect from peers, trust from prospective clients, a quiet certainty in the visitor that the person behind this site is precise about what they make and why.

## Anti-references

Things this must never look like, in order of priority:

1. **Generic dev portfolio: dark + neon + glassmorphism.** No neon accents, no frosted-glass cards, no gradient text, no animated-particle hero. The "AI made that" first-order reflex for technical portfolios is the explicit enemy.
2. **The SaaS hero-metric template.** Big number, small label, supporting stats, gradient accent block: outlawed. No "10x productivity," no fake usage stats, no metric-card grids.
3. **The crypto / AI-wrapper aesthetic family.** Grid backgrounds, gradient buttons, "powered by" badges, and shimmer animations. Sharing a canvas colour with AI labs is not a licence to borrow their marketing tropes.
4. **Corporate agency polish.** Stock-photo hero, vague capability list, "we craft experiences" copy, case-study-as-marketing-funnel. The writing must not be hollow.
5. **Awwwards-bait spectacle.** Scroll-jacked WebGL playgrounds with no point. Motion serves the work, not the demo reel.

## Evidence on Hand

- Works page lists real projects by chapter with stack and deployment notes (`src/data/works.ts`).
- Catalog entries ship real, copyable source (`src/catalog/`).
- Home page gallery and capability imagery are placeholders from Pexels and Pinterest. They must be replaced with real work before launch and must not be described as real work.
- No testimonials, client logos, metrics, or press exist. Do not fabricate any.

## Product Principles

1. **The work speaks; the chrome recedes.** The visual system is the stage, not the show. Every section asks: does this make the work clearer, or louder than the work?
2. **Show, don't tell.** Peers and clients alike do not read marketing copy. Replace adjectives with artifacts. Replace claims with screenshots, code, and decisions.
3. **Restraint is the signal.** Sparse layout, weight 400, one canvas, one accent (white). If a flourish cannot be justified in one sentence, it is removed.
4. **Reject the category reflex.** When a design choice matches the first-order expectation for "developer portfolio," that is the signal to rework it.
5. **One door, clearly marked.** Client acquisition means a visible, honest path to email on every public page, never gates, popups, or forms that harvest.

## Accessibility & Inclusion

**WCAG 2.2 AA** is the floor for contrast, focus visibility, and keyboard operability. Specifically:

- All body text on the near-black canvas meets 4.5:1 contrast. The `#7d8187` mute neutral measures about 3.5:1 on `#0a0a0a`; reserve it for non-essential metadata, never for primary copy or interactive labels. Use `#dadbdf` body for secondary copy.
- Translucent white outline borders are decorative. Interactive pills must also be distinguishable by label and position.
- Focus indicators are always visible, never removed.

**Reduced motion is respected.** All transitions and scroll-driven effects gate on `prefers-reduced-motion: reduce`. Motion is an enhancement, never load-bearing for comprehension.

**Keyboard navigation works end-to-end.** Every interactive element is reachable and operable without a pointer. The custom cursor and hover-driven affordances have keyboard equivalents.

**Color is never the sole carrier of meaning.** The single filled white pill marks the primary action, and primary actions are also distinguishable by position and label.
