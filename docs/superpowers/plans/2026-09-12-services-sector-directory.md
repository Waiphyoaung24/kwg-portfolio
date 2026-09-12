# Services Sector Directory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `/services` sector index plus nine `/services/<slug>` pages so a prospective client can find their own industry and read what would be built for it.

**Architecture:** All content lives in one data file, `src/data/services.ts`, exactly as `works.ts` already holds the Works content. Two Astro pages read it: a static index, and one dynamic route that emits nine prerendered pages via `getStaticPaths`. No client JavaScript is added; the existing `data-inview` reveal is the only motion. Proof is cited by `works.ts` id and read back at build time, never retyped.

**Tech Stack:** Astro 6.3.1 (default `output: 'static'`, `@astrojs/node` adapter for the routes that opt out), TypeScript strict, SCSS with `@use`d functions and mixins injected globally by `astro.config.mjs`, Node 24 native type stripping for `.mjs` tests.

**Spec:** `docs/superpowers/specs/2026-09-12-services-page-design.md`

## Global Constraints

Every task's requirements implicitly include this section.

- **`DESIGN.md` is binding.** Read it before writing any markup or style.
- **Tokens only.** Colours, spacing, radii, type sizes and easings come from `src/styles/_vars.scss` as CSS custom properties. A hex code or a raw px value in a page is a bug. Use the `to-rem()` and `clamp-fluid()` SCSS functions — they are injected globally by `astro.config.mjs` and need no import.
- **Reuse the primitives.** `.container`, `.grid`, `.card`, `.pill-btn`, `.pill-btn--filled`, `.hairline`, `.label`, `.micro`, `.body-lg`, `.body-sm`, `.h1`–`.h6`, `.visually-hidden`. Do not hand-roll a button or a card.
- **Weight 400 everywhere.** The system never bolds. Size and negative tracking do the emphasis work.
- **One filled pill per view**, on the primary action only. Everything else is an outline `.pill-btn`.
- **No shadows.** Hairline borders carry every elevation cue.
- **`--c-mute` (`#7d8187`, about 3.5:1) is metadata only** — qualifiers, tags, captions. Never primary copy, never an interactive label. Secondary copy uses `--c-body` (`#dadbdf`).
- **WCAG 2.2 AA floor.** Focus indicators are never removed. Motion gates on `prefers-reduced-motion`.
- **No accent colour on this surface.** `DESIGN.md` reserves sunset/dusk for illustration, never chrome.
- **No new dependency. No client-side JavaScript.**
- **Astro frontmatter order** is documented at the bottom of `astro.config.mjs` and must be followed: `import css`, `import type`, `type`, `interface`, `import package`, `import astro:content`, `import @content`, `import @layouts`, `import @components`, `getStaticPaths`, `Astro.Props`.
- **Do not touch** home's `05 — Capabilities` or `06 — How I work`, and do not delete `public/constellation/`.
- Run `npx prettier --write` on every file you create or modify before committing.

---

### Task 1: Sector data and its integrity test

The whole content payload, plus the test that stops a broken proof citation from ever shipping. This is the only task that carries content; everything after it is presentation.

**Files:**
- Create: `src/data/services.ts`
- Create: `src/data/services.test.mjs`
- Modify: `package.json` (the `scripts` block, adding one line)

**Interfaces:**
- Consumes: `Category` and `works` from `src/data/works.ts`. `Category` is `'creative-web' | 'erp' | 'custom-build'`, already exported at `src/data/works.ts:11`. `Work` is exported at `src/data/works.ts:43` and carries `id`, `title`, `client`, `year`, `stack`, `summary`, `category`, and optional `featured`, `media`, `homeOnly`.
- Produces: `export interface Offer { title: string; body: string; category: Category }`, `export interface Sector { slug: string; name: string; qualifier: string; lede: string; offers: Offer[]; proof: string[] }`, and `export const sectors: Sector[]` with nine entries in the order given below. Tasks 3 and 4 import `sectors` and the two types.

- [ ] **Step 1: Write the failing test**

Create `src/data/services.test.mjs`. It mirrors `src/data/works.test.mjs` — plain `node:assert/strict`, no framework, one `console.log` summary at the end.

```js
import assert from 'node:assert/strict';
import { sectors } from './services.ts';
import { works } from './works.ts';

// The three kinds of work, as works.ts already defines them. A fourth
// vocabulary for the same three things would drift, so this set is the only
// one allowed here.
const VALID = new Set(['creative-web', 'erp', 'custom-build']);
const SLUG = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

const ids = new Set(works.map((w) => w.id));
const slugs = new Set();

for (const s of sectors) {
  // Slugs become URL segments via getStaticPaths. A stray capital or space
  // builds a route nobody can type.
  assert.ok(SLUG.test(s.slug), `bad slug: ${s.slug}`);
  assert.ok(!slugs.has(s.slug), `duplicate sector slug: ${s.slug}`);
  slugs.add(s.slug);

  assert.ok(s.name && s.name.trim(), `${s.slug}: name required`);
  assert.ok(s.qualifier && s.qualifier.trim(), `${s.slug}: qualifier required`);
  assert.ok(s.lede && s.lede.trim(), `${s.slug}: lede required`);

  assert.ok(
    Array.isArray(s.offers) && s.offers.length > 0,
    `${s.slug}: at least one offer required`,
  );
  for (const o of s.offers) {
    assert.ok(o.title && o.title.trim(), `${s.slug}: offer title required`);
    assert.ok(
      o.body && o.body.trim(),
      `${s.slug}: offer body required for "${o.title}"`,
    );
    assert.ok(
      VALID.has(o.category),
      `${s.slug}: bad category ${o.category} on "${o.title}"`,
    );
  }

  // Proof is cited by id and read back off works.ts at build time so a client
  // name, year or stack is never retyped on a Services page. An id that stops
  // resolving would silently render a blank chip instead of throwing.
  assert.ok(Array.isArray(s.proof), `${s.slug}: proof must be an array`);
  for (const id of s.proof) {
    assert.ok(ids.has(id), `${s.slug}: proof id not in works.ts: ${id}`);
    // PRODUCT.md: "No client logos or press exist. Do not fabricate any."
    // works.ts carries six placeholder rows awaiting real projects; none of
    // them is evidence of anything and none may be cited as proof.
    assert.ok(
      !id.startsWith('placeholder-'),
      `${s.slug}: placeholder cited as proof: ${id}`,
    );
  }
}

const offers = sectors.reduce((n, s) => n + s.offers.length, 0);
const cited = new Set(sectors.flatMap((s) => s.proof));
console.log(
  `ok: ${sectors.length} sectors, ${offers} offers, ${cited.size} works cited`,
);
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `node src/data/services.test.mjs`

Expected: FAIL with `ERR_MODULE_NOT_FOUND` — `Cannot find module '.../src/data/services.ts'`. The data file does not exist yet.

- [ ] **Step 3: Write the data file**

Create `src/data/services.ts`. Comment density and tone match `works.ts`: comments explain why a decision was taken, not what the line does.

```ts
import type { Category } from './works';

/** One thing that gets built, named in this sector's own nouns. */
export interface Offer {
  title: string;
  /** One sentence. What it does for this sector specifically. */
  body: string;
  /** Which of the three kinds of work this is, per works.ts. */
  category: Category;
}

export interface Sector {
  /** URL segment: /services/<slug>. Lowercase, hyphenated. */
  slug: string;
  name: string;
  /** Muted sub-label — the line a visitor scans to recognise themselves. */
  qualifier: string;
  /** One or two sentences naming what is usually broken in this sector. */
  lede: string;
  offers: Offer[];
  /**
   * works.ts ids. Read back at build time so a client name, year or stack is
   * never retyped here. Empty for the four sectors with no shipped work yet —
   * those pages omit the proof band entirely rather than show an empty state.
   */
  proof: string[];
}

// Cut by the client's taxonomy, not the seller's. Home's 05 — Capabilities
// already cuts the same work by deliverable; a machine exporter and a
// restaurant owner both have to translate that. These nine let them skip it.
//
// Five sectors carry real clients and four carry offers only. That asymmetry
// is deliberate and recorded in the spec: the offers band comes before the
// proof band on every sector page, so a page with no case study leads with
// what would be built rather than with an absence.
export const sectors: Sector[] = [
  {
    slug: 'manufacturing',
    name: 'Manufacturing & Industrial',
    qualifier: 'machine builders, fabricators, exporters',
    lede: 'You sell a machine that costs more than a car. Buyers research for months before they call, and the site is three photographs and a phone number.',
    offers: [
      {
        title: 'The machine in motion',
        body: 'The cut itself, filmed and set above the fold, with the page built around that one shot.',
        category: 'creative-web',
      },
      {
        title: 'Spec sheets from one source',
        body: 'Models, capacities, and tolerances held in one file and rendered to both the page and the PDF, so sales and the site cannot disagree.',
        category: 'creative-web',
      },
      {
        title: 'Enquiries that arrive complete',
        body: 'The form asks for material, thickness, and volume, so the first reply is a number instead of a question.',
        category: 'custom-build',
      },
      {
        title: 'Production visible to the office',
        body: 'What is on the floor, what is promised, and what is late, on one board.',
        category: 'erp',
      },
    ],
    proof: ['miracle-cutting-machine'],
  },
  {
    slug: 'retail-pos',
    name: 'Retail & Point of Sale',
    qualifier: 'counters, branches, stock rooms',
    lede: 'Two branches and a spreadsheet works. Four branches and a spreadsheet is a daily phone call about stock.',
    offers: [
      {
        title: 'A till that survives the internet',
        body: 'Rings up a sale while the connection is down and reconciles when it returns.',
        category: 'erp',
      },
      {
        title: 'One stock figure per branch',
        body: 'Quantities moved by the till, not retyped into a sheet at closing.',
        category: 'erp',
      },
      {
        title: 'The same system on the floor',
        body: 'Inventory on a phone, so a stock check happens at the shelf.',
        category: 'custom-build',
      },
      {
        title: 'Takings and margin per day',
        body: 'Sales, discounts, and margin by branch, readable the next morning.',
        category: 'erp',
      },
    ],
    proof: ['castranova-pos', 'mrspinel-staff'],
  },
  {
    slug: 'commerce',
    name: 'Consumer Commerce',
    qualifier: 'storefronts, ordering, delivery',
    lede: 'Selling through a marketplace or a chat account means renting the customer. The order history belongs to the platform.',
    offers: [
      {
        title: 'A storefront on both stores',
        body: 'One codebase serving the phone layout and the wider tablet grid, shipped to iOS and Android.',
        category: 'custom-build',
      },
      {
        title: 'A catalogue your staff edit',
        body: 'Products, stock, and prices changed by the people who know them, without a developer.',
        category: 'erp',
      },
      {
        title: 'Orders that move in the open',
        body: 'Placed, packed, dispatched, and the customer watches it happen.',
        category: 'erp',
      },
      {
        title: 'One page whose job is the install',
        body: 'Built for a single action, and measured against it.',
        category: 'creative-web',
      },
    ],
    proof: ['gaigai'],
  },
  {
    slug: 'studio',
    name: 'Studio & Agency',
    qualifier: 'design, architecture, production',
    lede: 'The work is the pitch. A template flattens it into the same grid as everybody else.',
    offers: [
      {
        title: 'A site the work earns',
        body: 'Scroll-driven WebGL and typography carrying the argument, on a frame budget every effect has to justify.',
        category: 'creative-web',
      },
      {
        title: 'Projects as data',
        body: 'Adding a case study is an entry in a file, not a rebuild of a page.',
        category: 'creative-web',
      },
      {
        title: 'Review without version names',
        body: 'Comments land on the frame, versions are kept, and nothing is called final twice.',
        category: 'custom-build',
      },
    ],
    proof: ['parallel'],
  },
  {
    slug: 'corporate',
    name: 'Corporate Group',
    qualifier: 'holdings, multi-entity, investor-facing',
    lede: 'A group of companies usually reads online as one vague page about synergy. The subsidiaries are the substance.',
    offers: [
      {
        title: 'Subsidiaries with their own depth',
        body: 'Each company its own page and its own figures, under one identity.',
        category: 'creative-web',
      },
      {
        title: 'A dated archive',
        body: 'Releases, reports, and filings published by staff without opening a ticket.',
        category: 'creative-web',
      },
      {
        title: 'Careers HR can run',
        body: 'Openings posted, applications collected, and CVs where HR can read them.',
        category: 'custom-build',
      },
      {
        title: 'Figures on one definition',
        body: 'Each entity’s numbers in one table, calculated the same way.',
        category: 'erp',
      },
    ],
    proof: ['redhorse-group'],
  },
  {
    slug: 'inventory',
    name: 'Logistics & Inventory',
    qualifier: 'warehouses, picks, fulfilment',
    lede: 'Stock is right on the sheet and wrong on the shelf. Every correction costs somebody an afternoon.',
    offers: [
      {
        title: 'Locations, picks, and counts',
        body: 'Bin locations and pick lists on a handheld, without replacing the system you already run.',
        category: 'erp',
      },
      {
        title: 'Recorded at the door',
        body: 'Receipts and dispatches entered once, by the person who moved the box.',
        category: 'erp',
      },
      {
        title: 'Where the count goes wrong',
        body: 'Variance by item and by location, so the cause is visible rather than inferred.',
        category: 'erp',
      },
    ],
    proof: [],
  },
  {
    slug: 'workforce',
    name: 'HR & Workforce',
    qualifier: 'rosters, onboarding, records',
    lede: 'Leave requests in a chat app, contracts in a drive folder, and one person who knows where everything is.',
    offers: [
      {
        title: 'A rota built once',
        body: 'Open shifts posted and swaps accepted, inside the coverage rules you set.',
        category: 'erp',
      },
      {
        title: 'Leave with a balance',
        body: 'Requests, approvals, and remaining days in one place, on a record that outlives the person keeping it.',
        category: 'erp',
      },
      {
        title: 'Onboarding that closes',
        body: 'Documents collected and accounts created against a checklist that finishes.',
        category: 'erp',
      },
      {
        title: 'Records per person',
        body: 'Contracts, roles, and history, with access you control.',
        category: 'erp',
      },
    ],
    proof: [],
  },
  {
    slug: 'hospitality',
    name: 'Hospitality & F&B',
    qualifier: 'restaurants, cafes, hotels',
    lede: 'The aggregators take a share of every order and keep the customer. Your own channel costs nothing per order.',
    offers: [
      {
        title: 'Ordering on your own page',
        body: 'Table, pickup, or delivery, at your prices, through a channel you own.',
        category: 'custom-build',
      },
      {
        title: 'Bookings off the phone',
        body: 'Tables or rooms self-booked against real availability, confirmed and reminded automatically.',
        category: 'erp',
      },
      {
        title: 'One screen for the kitchen',
        body: 'Every channel’s orders in the sequence they arrived.',
        category: 'erp',
      },
      {
        title: 'A room that photographs well',
        body: 'The space and the plates at the size they deserve, loading fast on a phone outside.',
        category: 'creative-web',
      },
    ],
    proof: [],
  },
  {
    slug: 'professional',
    name: 'Professional Services',
    qualifier: 'clinics, firms, consultancies',
    lede: 'The calendar is the product. Most of the admin around it is still typed twice.',
    offers: [
      {
        title: 'Clients book themselves',
        body: 'Self-scheduling against real availability, with reminders that cut no-shows.',
        category: 'erp',
      },
      {
        title: 'Files per client',
        body: 'Notes, documents, and history in one record, with access you can audit.',
        category: 'erp',
      },
      {
        title: 'Time that becomes an invoice',
        body: 'Hours booked against a matter raise the invoice, and the invoice chases itself.',
        category: 'erp',
      },
      {
        title: 'The first three questions answered',
        body: 'What you do, who for, and how to start, before the phone rings.',
        category: 'creative-web',
      },
    ],
    proof: [],
  },
];

```

No lookup helper. `getStaticPaths` maps over `sectors` and hands each one through as a prop, so nothing ever needs to find a sector by slug. `works.ts` exports `worksFor` because the Works page genuinely filters; this file has no such caller, and a helper with no caller is speculative.

- [ ] **Step 4: Run the test to verify it passes**

Run: `node src/data/services.test.mjs`

Expected: PASS, printing exactly `ok: 9 sectors, 34 offers, 6 works cited`.

If the count differs, an offer or a proof id was mistyped — fix the data, not the test.

- [ ] **Step 5: Register the test script**

In `package.json`, add one line to `scripts`, directly after `"test:pipeline"`:

```json
"test:services": "node src/data/services.test.mjs"
```

- [ ] **Step 6: Verify the script runs**

Run: `npm run test:services`

Expected: PASS with the same `ok: 9 sectors, 34 offers, 6 works cited` line.

- [ ] **Step 7: Commit**

```bash
npx prettier --write src/data/services.ts src/data/services.test.mjs package.json
git add src/data/services.ts src/data/services.test.mjs package.json
git commit -m "✨ services: nine sectors and their offers as data

Content only. Cut by the client's taxonomy rather than by deliverable,
tagged with works.ts's existing three categories so a fourth vocabulary
for the same three things cannot drift.

The test refuses any proof id that does not resolve in works.ts, and
refuses the six placeholder- rows outright: PRODUCT.md forbids citing
work that does not exist.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LXE83sxZuPAU8UUp6iDkmA"
```

---

### Task 2: Let a page set its own title and description

`Layout.astro` currently hardcodes `title = 'KWG'` and one description, and feeds both into `<title>`, `meta description`, and all four OG/Twitter tags. Ten new indexable routes would otherwise ship identical metadata, which defeats the point of a page built for discovery.

This is the smallest change that fixes it: two optional props, defaulting to today's exact values so every existing page renders byte-identical output.

**Files:**
- Modify: `src/layouts/Layout.astro:11-16` (the frontmatter constants)

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `Layout` accepts two optional props, `title?: string` and `description?: string`. When `title` is given, `<title>` renders `<title> — KWG`; when omitted it renders `KWG`. Tasks 3 and 4 pass both.

- [ ] **Step 1: Read the file**

Read `src/layouts/Layout.astro` in full. Lines 11–16 hold the constants; lines 27 and 39–50 consume them. Note that `title` feeds `<title>`, `og:title` and `twitter:title`, and `description` feeds `meta[name=description]`, `og:description` and `twitter:description`. All six must keep working.

- [ ] **Step 2: Add the props**

Replace the constant block. Current:

```astro
const lang = 'en';
const title = 'KWG';
const description = 'Personal portfolio. An exhibit, not a funnel.';
const shareImage = new URL('og-image.jpg', Astro.site);
```

Replace with:

```astro
interface Props {
  /** Page name. Suffixed with the wordmark; omit on the home page. */
  title?: string;
  description?: string;
}

const { title: pageTitle, description: pageDescription } = Astro.props;

const lang = 'en';
// Ten Services routes shipping one shared title would defeat a page built to
// be found. Defaults are the previous hardcoded values exactly, so every page
// that passes nothing renders byte-identical metadata.
const title = pageTitle ? `${pageTitle} — KWG` : 'KWG';
const description =
  pageDescription ?? 'Personal portfolio. An exhibit, not a funnel.';
const shareImage = new URL('og-image.jpg', Astro.site);
```

`interface Props` goes above the imports of nothing and below none — per the frontmatter order in `astro.config.mjs`, `interface` precedes `import package`. Here there are no package imports, so place the interface directly under the existing `import '../styles/index.scss';` and component imports, immediately before `const canonicalURL`.

- [ ] **Step 3: Verify existing pages are unchanged**

Run: `npm run build`

Expected: the build succeeds, and `dist/client/index.html`, `dist/client/works/index.html` and `dist/client/about/index.html` all still contain `<title>KWG</title>`. Check one:

```bash
grep -o '<title>[^<]*</title>' dist/client/works/index.html
```

Expected output: `<title>KWG</title>`

- [ ] **Step 4: Commit**

```bash
npx prettier --write src/layouts/Layout.astro
git add src/layouts/Layout.astro
git commit -m "♿ layout: let a page name itself

Two optional props, defaulting to the values that were hardcoded, so
every existing page renders byte-identical metadata. The Services
routes need their own titles to be worth indexing.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LXE83sxZuPAU8UUp6iDkmA"
```

---

### Task 3: The `/services` index page

Four bands: hero, sector grid, a link to home's process, and the one door. Modelled on `src/pages/works.astro` — read that file first; its hero, `.intro` and `.closing` are the pattern this page follows.

**Files:**
- Create: `src/pages/services/index.astro`

**Interfaces:**
- Consumes: `sectors` from `src/data/services.ts` (Task 1); `Category` from `src/data/works.ts`; `Layout` with `title` and `description` props (Task 2).
- Produces: the route `/services`, with `<a href="/services/<slug>">` for all nine slugs. Task 5 repoints the navbar at it.

- [ ] **Step 1: Write the page**

Create `src/pages/services/index.astro`.

```astro
---
import Layout from '@layouts/Layout.astro';

import type { Category } from '../../data/works';
import { sectors } from '../../data/services';

// Content lives entirely in src/data/services.ts. See
// docs/superpowers/specs/2026-09-12-services-page-design.md.
const email = 'waiphyoag.cs34@gmail.com';

// Fixed order, so two sectors carrying the same mix of work always print the
// same row. Derived rather than stored: the tags a sector shows are a fact
// about its offers, and storing them separately invites the two to disagree.
const ORDER: Category[] = ['creative-web', 'erp', 'custom-build'];
const TAG: Record<Category, string> = {
  'creative-web': 'Web',
  erp: 'System',
  'custom-build': 'Build',
};

const cards = sectors.map((sector) => ({
  ...sector,
  tags: ORDER.filter((c) => sector.offers.some((o) => o.category === c)).map(
    (c) => TAG[c],
  ),
}));
---

<Layout
  title="Services"
  description="Nine sectors, and what I would build for each. Creative websites, internal systems, and custom builds."
>
  <main>
    <section class="hero" aria-labelledby="services-mark">
      <p class="hero__index label" data-inview-manual>01 &mdash; Services</p>

      <div class="hero__center">
        <h1 id="services-mark" class="hero__mark" data-inview-manual>
          Nine sectors.<br />What I would build for each.
        </h1>
        <p class="hero__tagline" data-inview-manual>
          Pick the one that describes your operation. Each page lists what I
          would build for it, and names the clients where the work already
          exists.
        </p>
      </div>

      <p class="hero__cue label" data-inview-manual>
        Scroll <span aria-hidden="true">&darr;</span> 2026
      </p>
    </section>

    <section class="container sectors" aria-labelledby="sectors-heading">
      <h2 id="sectors-heading" class="visually-hidden">Sectors</h2>

      <ul class="sectors__grid" role="list">
        {
          cards.map(({ slug, name, qualifier, offers, tags }, i) => (
            <li class="sectors__item" data-inview style={`--delay: ${i * 0.06}s`}>
              {/* One anchor per card, wrapping the whole surface. Nothing
                  inside it is focusable, so the card is a single tab stop
                  rather than four. */}
              <a class="card sector" href={`/services/${slug}`}>
                <h3 class="sector__name h4">{name}</h3>
                <p class="sector__qualifier micro">{qualifier}</p>

                <ul class="sector__offers" role="list">
                  {offers.map(({ title }) => (
                    <li>{title}</li>
                  ))}
                </ul>

                <p class="sector__meta micro">
                  <span>{tags.join(' · ')}</span>
                  <span aria-hidden="true">&rarr;</span>
                </p>
              </a>
            </li>
          ))
        }
      </ul>
    </section>

    <section class="container process" aria-labelledby="process-heading">
      <h2 id="process-heading" class="visually-hidden">How I work</h2>
      <p class="process__body" data-inview>
        Every one of these starts the same way. A call, a written scope with one
        price and one timeline, then a weekly update until handover.
      </p>
      <a class="pill-btn" href="/#process" data-inview>How I work</a>
    </section>

    <section class="container closing" aria-labelledby="closing-heading">
      <h2 id="closing-heading" class="visually-hidden">Contact</h2>
      <p class="closing__body" data-inview>
        If none of the nine describes you, the work is the same. Describe the
        operation instead.
      </p>
      <a
        class="pill-btn pill-btn--filled"
        href={`mailto:${email}?subject=New%20project`}
        data-inview
      >
        Start a project
      </a>
    </section>
  </main>
</Layout>

<style lang="scss">
  // HERO — the typographic void from works.astro, same proportions. 4rem
  // subtracts the Header's footprint.
  .hero {
    position: relative;
    display: grid;
    grid-template-rows: auto 1fr auto;
    min-height: calc(100svh - 4rem);
    max-width: var(--container-max-width);
    margin-inline: auto;
    padding: to-rem(24) var(--grid-margin) to-rem(40);
  }

  .hero__index {
    color: var(--c-mute);
  }

  .hero__center {
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: clamp-fluid(20, 40);
  }

  .hero__mark {
    margin: 0;
    color: var(--c-ink);
  }

  .hero__tagline {
    max-width: 42ch;
    color: var(--c-body);
    font-size: clamp-fluid(16, 18);
    line-height: 1.56;
    letter-spacing: 0;
  }

  .hero__cue {
    justify-self: end;
    align-self: end;
    display: inline-flex;
    align-items: center;
    gap: to-rem(8);
    color: var(--c-body);
  }

  // SECTOR GRID — auto-fit so the row count follows the viewport instead of a
  // breakpoint, collapsing to one column on a phone without a media query.
  .sectors {
    margin-block: clamp-fluid(80, 140);
  }

  .sectors__grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(to-rem(280), 1fr));
    gap: var(--grid-gutter);
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .sectors__item {
    display: flex;
  }

  .sector {
    display: flex;
    flex: 1;
    flex-direction: column;
    gap: var(--sp-md);
    color: var(--c-ink);
    text-decoration: none;
    transition: border-color 0.25s var(--ease-smooth);

    @include has-hover {
      &:hover {
        border-color: var(--c-ink);
      }
    }
  }

  .sector__name {
    margin: 0;
  }

  // Metadata, which is the only thing --c-mute is cleared for (PRODUCT.md).
  .sector__qualifier,
  .sector__meta {
    margin: 0;
    color: var(--c-mute);
  }

  .sector__offers {
    margin: 0;
    // Pushes the meta row to the card's foot, so the arrow sits on one line
    // across a row of cards with different offer counts.
    margin-bottom: auto;
    padding: 0;
    color: var(--c-body);
    font-size: var(--fs-body-sm);
    line-height: 1.6;
    list-style: none;
  }

  .sector__meta {
    display: flex;
    justify-content: space-between;
    gap: var(--sp-sm);
    padding-top: var(--sp-md);
    border-top: 1px solid var(--c-hairline);
  }

  // PROCESS + CLOSING — the measured prose column from works.astro.
  .process,
  .closing {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: to-rem(20);
    margin-block: clamp-fluid(80, 140);
  }

  .process__body,
  .closing__body {
    max-width: 65ch;
    margin: 0;
    color: var(--c-body);
    line-height: 1.55;
  }
</style>
```

- [ ] **Step 2: Run the build**

Run: `npm run build`

Expected: `astro check` reports no errors, and the build emits `dist/client/services/index.html`.

- [ ] **Step 3: Verify the page's content and its one filled pill**

```bash
grep -c 'href="/services/' dist/client/services/index.html
grep -o 'pill-btn pill-btn--filled' dist/client/services/index.html | wc -l
grep -o '<title>[^<]*</title>' dist/client/services/index.html
```

Expected: `9` sector links; exactly `1` filled pill (`DESIGN.md`: one per view); title `<title>Services — KWG</title>`.

- [ ] **Step 4: Check it by eye**

Run `npm run dev` and open `http://localhost:4321/services`. Confirm at 1440px and at 360px (devtools device toolbar):

- the grid is three or four across at 1440px and exactly one column at 360px;
- no horizontal scrollbar at 360px;
- every card's arrow sits on the same baseline within a row, including next to `studio` and `inventory`, which carry three offers rather than four;
- tabbing moves one stop per card, not four.

- [ ] **Step 5: Commit**

```bash
npx prettier --write src/pages/services/index.astro
git add src/pages/services/index.astro
git commit -m "✨ services: the sector index

Nine cards, one anchor each, tags derived from the offers rather than
stored beside them. Hero and prose columns follow works.astro so the
two pages read as one document.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LXE83sxZuPAU8UUp6iDkmA"
```

---

### Task 4: The `/services/<slug>` sector page

One template, nine prerendered routes. Five bands, the third of which renders only when the sector cites proof.

**Files:**
- Create: `src/pages/services/[sector].astro`

**Interfaces:**
- Consumes: `sectors` from `src/data/services.ts` (Task 1); `works` plus the `Category` and `Work` types from `src/data/works.ts`; `Layout` with `title` and `description` props (Task 2). The `Sector` type is not imported — `InferGetStaticPropsType` derives it from `getStaticPaths`.
- Produces: nine routes, `/services/manufacturing` through `/services/professional`.

**Critical:** this repo's `astro.config.mjs` sets no `output`, so Astro's default `'static'` applies and the `@astrojs/node` adapter serves only the routes that opt out with `export const prerender = false`. Do **not** add that line here — `getStaticPaths` runs at build time and is what emits the nine pages. The `satisfies GetStaticPaths` + `InferGetStaticPropsType` pairing below is the documented way to keep `Astro.props` typed under `astro/tsconfigs/strict`.

- [ ] **Step 1: Write the page**

Create `src/pages/services/[sector].astro`.

```astro
---
import Layout from '@layouts/Layout.astro';

import type { GetStaticPaths, InferGetStaticPropsType } from 'astro';
import type { Category, Work } from '../../data/works';
import { works } from '../../data/works';
import { sectors } from '../../data/services';

export const getStaticPaths = (() =>
  sectors.map((sector) => ({
    params: { sector: sector.slug },
    props: { sector },
  }))) satisfies GetStaticPaths;

type Props = InferGetStaticPropsType<typeof getStaticPaths>;

const { sector }: Props = Astro.props;

const email = 'waiphyoag.cs34@gmail.com';

// Spelled out here, where there is room for the full phrase. The index prints
// the short form in a meta row.
const TAG: Record<Category, string> = {
  'creative-web': 'Creative web',
  erp: 'Internal system',
  'custom-build': 'Custom build',
};

// Proof reads off works.ts by id, so a client name, year or stack is never
// retyped on this page. src/data/services.test.mjs fails on an id that does
// not resolve, which is why a missing entry cannot reach the build as a blank
// chip.
const proof = sector.proof
  .map((id) => works.find((w) => w.id === id))
  .filter((w): w is Work => w !== undefined);

// Three siblings, wrapping past the end of the list so the last sector still
// gets three rather than none.
const others = sectors.filter((s) => s.slug !== sector.slug);
const start = sectors.findIndex((s) => s.slug === sector.slug);
const adjacent = Array.from(
  { length: 3 },
  (_, i) => others[(start + i) % others.length],
);
---

<Layout title={sector.name} description={sector.lede}>
  <main>
    <section class="hero container" aria-labelledby="sector-mark">
      <p class="hero__index label" data-inview-manual>
        Services / {sector.name}
      </p>
      <h1 id="sector-mark" class="hero__mark h2" data-inview-manual>
        {sector.name}
      </h1>
      <p class="hero__lede body-lg" data-inview-manual>{sector.lede}</p>
    </section>

    <section class="container offers" aria-labelledby="offers-heading">
      <h2 id="offers-heading" class="offers__heading h4" data-inview>
        What I would build
      </h2>

      <ul class="offers__grid" role="list">
        {
          sector.offers.map(({ title, body, category }, i) => (
            <li class="card offer" data-inview style={`--delay: ${i * 0.06}s`}>
              <p class="offer__tag micro">{TAG[category]}</p>
              <h3 class="offer__title h5">{title}</h3>
              <p class="offer__body">{body}</p>
            </li>
          ))
        }
      </ul>
    </section>

    {
      /* Renders only where work exists. The four sectors with an empty proof
         array omit the band entirely — no empty state, no "coming soon". */
      proof.length > 0 && (
        <section class="container proof" aria-labelledby="proof-heading">
          <h2 id="proof-heading" class="proof__heading h4" data-inview>
            Already built here
          </h2>

          <ul class="proof__list" role="list">
            {proof.map(({ title, client, year, stack, summary }) => (
              <li class="proof__item" data-inview>
                <p class="proof__meta micro">
                  {client} · {year}
                </p>
                <h3 class="proof__title h5">{title}</h3>
                <p class="proof__body">{summary}</p>
                <p class="proof__stack micro">{stack.join(' · ')}</p>
              </li>
            ))}
          </ul>
        </section>
      )
    }

    <section class="container adjacent" aria-labelledby="adjacent-heading">
      <h2 id="adjacent-heading" class="adjacent__heading label" data-inview>
        Not quite it
      </h2>
      <ul class="adjacent__list" role="list">
        {
          adjacent.map((s) => (
            <li data-inview>
              <a class="pill-btn" href={`/services/${s.slug}`}>
                {s.name}
              </a>
            </li>
          ))
        }
      </ul>
    </section>

    <section class="container closing" aria-labelledby="closing-heading">
      <h2 id="closing-heading" class="visually-hidden">Contact</h2>
      <div class="closing__actions">
        <a class="pill-btn" href="/services" data-inview>
          <span aria-hidden="true">&larr;</span> All sectors
        </a>
        <a
          class="pill-btn pill-btn--filled"
          href={`mailto:${email}?subject=New%20project`}
          data-inview
        >
          Start a project
        </a>
      </div>
    </section>
  </main>
</Layout>

<style lang="scss">
  // HERO — a band rather than a full viewport. A sector page is a document,
  // and the offers are the reason to be here, so they start above the fold.
  .hero {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: var(--sp-lg);
    padding-block: clamp-fluid(48, 96) clamp-fluid(40, 72);
  }

  .hero__index {
    margin: 0;
    color: var(--c-mute);
  }

  .hero__mark {
    margin: 0;
    color: var(--c-ink);
  }

  .hero__lede {
    max-width: 46ch;
    margin: 0;
    color: var(--c-body);
  }

  .offers,
  .proof,
  .adjacent {
    padding-block: clamp-fluid(40, 72);
    border-top: 1px solid var(--c-hairline);
  }

  .offers__heading,
  .proof__heading {
    margin: 0 0 var(--sp-xl);
    color: var(--c-ink);
  }

  .offers__grid,
  .proof__list {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(to-rem(280), 1fr));
    gap: var(--grid-gutter);
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .offer {
    display: flex;
    flex-direction: column;
    gap: var(--sp-sm);
  }

  .offer__tag {
    margin: 0;
    color: var(--c-mute);
  }

  .offer__title {
    margin: 0;
    color: var(--c-ink);
  }

  .offer__body {
    margin: 0;
    color: var(--c-body);
    font-size: var(--fs-body-sm);
    line-height: 1.6;
  }

  // Proof carries no card chrome. It is evidence, not an offer, and the
  // hairline above the band is already the elevation cue.
  .proof__item {
    display: flex;
    flex-direction: column;
    gap: var(--sp-sm);
  }

  .proof__meta,
  .proof__stack {
    margin: 0;
    color: var(--c-mute);
  }

  .proof__title {
    margin: 0;
    color: var(--c-ink);
  }

  .proof__body {
    margin: 0;
    color: var(--c-body);
    font-size: var(--fs-body-sm);
    line-height: 1.6;
  }

  .adjacent__heading {
    margin: 0 0 var(--sp-lg);
    color: var(--c-mute);
  }

  .adjacent__list {
    display: flex;
    flex-wrap: wrap;
    gap: var(--sp-md);
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .closing {
    padding-block: clamp-fluid(48, 96);
  }

  .closing__actions {
    display: flex;
    flex-wrap: wrap;
    gap: var(--sp-md);
  }
</style>
```

- [ ] **Step 2: Run the build**

Run: `npm run build`

Expected: `astro check` clean, and nine directories emitted under `dist/client/services/`.

- [ ] **Step 3: Verify all nine routes and the conditional band**

```bash
ls dist/client/services/
grep -c 'Already built here' dist/client/services/manufacturing/index.html
grep -c 'Already built here' dist/client/services/hospitality/index.html
grep -o '<title>[^<]*</title>' dist/client/services/retail-pos/index.html
grep -o 'Castra Nova' dist/client/services/retail-pos/index.html | head -1
```

Expected: nine directories plus `index.html`; `1` on `manufacturing` (it cites proof); `0` on `hospitality` (it cites none, so the band must be absent entirely, not empty); title `<title>Retail & Point of Sale — KWG</title>`; `Castra Nova` present, read from `works.ts` rather than typed here.

- [ ] **Step 4: Check it by eye**

`npm run dev`, then visit `/services/retail-pos` (proof band present, two entries) and `/services/hospitality` (no proof band). At 360px and 1440px confirm no horizontal scroll, the lede wraps inside 46ch, and the adjacent pills wrap rather than overflow.

- [ ] **Step 5: Commit**

```bash
npx prettier --write src/pages/services/[sector].astro
git add "src/pages/services/[sector].astro"
git commit -m "✨ services: a page per sector

One template, nine prerendered routes. Offers come before proof, so the
four sectors without a case study lead with what would be built rather
than with an absence. Client, year and stack are read off works.ts by
id and never retyped.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LXE83sxZuPAU8UUp6iDkmA"
```

---

### Task 5: Point the navbar at it, and settle the two open items

The nav label already reads `Services` but its `href` still goes to the constellation. Repointing it last means the nav is never broken between commits.

**Files:**
- Modify: `src/data/nav.ts:6`
- Modify: `PRODUCT.md` (the `Operating Context` public-surface line)
- Modify: `src/pages/my-portfolio.astro` (add a `noindex` meta)

**Interfaces:**
- Consumes: the `/services` route from Task 3.
- Produces: nothing consumed by a later task.

- [ ] **Step 1: Repoint the nav**

In `src/data/nav.ts`, line 6 currently reads:

```ts
  { label: 'Services', href: '/my-portfolio' },
```

Change to:

```ts
  { label: 'Services', href: '/services' },
```

Leave the other four entries alone. `Header.astro` and `Footer.astro` both read this array, so one edit moves both.

- [ ] **Step 2: Stop the constellation competing in search**

Two separate documents are involved and they need different fixes. Do both.

**2a. The iframed export.** `public/constellation/index.html` is an unmodified third-party static export carrying `robots: index, follow`, `<title>Your Name — Design / Engineering / Product</title>`, and an `og:url` of `https://yourdomain.com/`. It is a `public/` asset served verbatim, so edit the file directly. Find, in the `<head>`:

```html
<meta name="robots" content="index, follow"/>
```

Replace with:

```html
<meta name="robots" content="noindex, nofollow"/>
```

**2b. The framing page.** `/my-portfolio` is a real Astro route and is indexed independently of the iframe. Keep it out of the sitemap by extending the filter already in `astro.config.mjs`, which currently reads:

```js
filter: (page) => !page.includes('/vault'),
```

Change to:

```js
// /my-portfolio frames an unmodified third-party template whose own
// metadata still says "Your Name". It keeps its route but should not
// compete with the Services pages in search.
filter: (page) => !page.includes('/vault') && !page.includes('/my-portfolio'),
```

Also give the page a title so it stops reporting as a second `KWG`:

```astro
<Layout
  title="Constellation"
  description="An interactive 3D portfolio constellation."
>
```

**Deliberately out of scope:** a true `<meta name="robots" content="noindex">` on `/my-portfolio` itself would need a third `Layout` prop. Sitemap exclusion plus the iframe's own `noindex` is the proportionate fix; if the route needs hard de-indexing later, that is a one-line prop on `Layout` and its own change.

- [ ] **Step 3: Update PRODUCT.md**

In `PRODUCT.md`, under `Operating Context`, the public-surfaces line currently reads:

```
- Public surfaces: Home, Works, Catalog (copyable components and demos), My Portfolio (3D constellation), About.
```

Replace with:

```
- Public surfaces: Home, Works, Catalog (copyable components and demos), Services (a sector directory: an index plus one page per sector), About. The 3D constellation remains at `/my-portfolio` but is no longer in the navbar and is set `noindex`; it is an unmodified third-party template and is not presented as work.
```

- [ ] **Step 4: Full verification**

Run every check:

```bash
npm run test:services
npm run build
grep -o 'href="/services"' dist/client/index.html | head -1
grep -c 'my-portfolio' dist/client/index.html
```

Expected: the test prints `ok: 9 sectors, 34 offers, 6 works cited`; the build succeeds; `href="/services"` appears in the home page's rendered nav; and `my-portfolio` appears `0` times anywhere in the home page.

Then run the pre-existing suites to confirm nothing regressed:

```bash
npm run test:picker && npm run test:presets && npm run test:auth && npm run test:pipeline
node src/data/works.test.mjs
```

Expected: all pass.

- [ ] **Step 5: Click through it**

`npm run dev`. From the home page, click `Services` in the navbar, then a sector card, then an adjacent pill, then `All sectors`. Confirm no 404 at any step and that the navbar's `Services` entry is marked current on all ten pages if `Header.astro` marks current pages.

- [ ] **Step 6: Commit**

```bash
npx prettier --write src/data/nav.ts src/pages/my-portfolio.astro
git add src/data/nav.ts src/pages/my-portfolio.astro public/constellation/index.html PRODUCT.md
git commit -m "✨ nav: Services replaces the constellation

Repointed last, so the navbar is never broken mid-series. The
constellation keeps its route and leaves the nav: it is an unmodified
third-party export whose metadata still says \"Your Name\", so it is now
noindex rather than competing with nine real pages in search.

PRODUCT.md's public-surface list updated to match.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LXE83sxZuPAU8UUp6iDkmA"
```

---

## Done when

- `npm run test:services` prints `ok: 9 sectors, 34 offers, 6 works cited`.
- `npm run build` passes `astro check` and emits `/services` plus nine sector routes.
- Every existing page still renders `<title>KWG</title>`.
- The navbar's `Services` entry reaches `/services`, and `my-portfolio` appears nowhere in the rendered nav.
- No horizontal scroll at 360px on any of the ten new pages.
- Exactly one `.pill-btn--filled` per page.
