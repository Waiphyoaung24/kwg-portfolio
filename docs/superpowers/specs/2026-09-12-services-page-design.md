# Services — sector directory

Date: 2026-09-12
Status: approved design, not yet implemented

## Problem

The site has no surface where a prospective client can locate themselves. `PRODUCT.md`
names client acquisition as an explicit second goal and describes that audience as
founders and operators who "want to know three things quickly: what kind of work gets
done here, whether it is good, and how to start a conversation."

Home answers the second and third. It does not answer the first in the visitor's own
terms. `05 — Capabilities` is cut by deliverable (Websites & Landing Pages, Product &
UI) — the seller's taxonomy. A restaurant owner and a machine exporter read the same two
stands and have to translate.

This adds a surface cut by the buyer's taxonomy instead: sector.

## Scope

In:

- `/services` — a sector index.
- `/services/<slug>` — one page per sector, nine of them, from one template.
- `src/data/services.ts` — all sector and offer content.
- `src/data/services.test.mjs` — data integrity check.
- `src/data/nav.ts` — the `Services` entry repointed to `/services`.

Out:

- The `/my-portfolio` constellation. It leaves the navbar and stays on disk at its
  current route. Retiring it is a separate decision (see Open Items).
- Any contact form, booking tool, or capture mechanism. `PRODUCT.md`: "one clear door:
  email."
- Any change to home's `05 — Capabilities` or `06 — How I work`.

## Prior decisions

Recorded because each one closed off an alternative that would otherwise look obvious
later.

1. **Route.** Services gets a new `/services`. The constellation keeps `/my-portfolio`
   but loses its nav entry. Nothing is deleted.
2. **Axis.** Sector, not situation and not deliverable. Considered and rejected:
   cutting by client situation ("your team runs the business out of spreadsheets"),
   which maps more tightly to shipped evidence. The owner chose sector. The known cost
   is that a sector list implies vertical specialisation that has not been claimed, and
   that four of nine rows carry no case study. Mitigated in the layout (section 5)
   rather than argued further.
3. **Coverage.** One flat list, proof optional. Nine sectors: five with real clients,
   four with offers only. Considered and rejected: proof-only (five rows, narrower net)
   and a visibly separated "open to" group.
4. **Depth.** Index plus a route per sector, rather than one long scrolling page.
   Since all nine pages render from a single template, the marginal cost per sector is
   copy, not code.
5. **Build-type tags reuse `works.ts`.** Offers are tagged with the three existing
   `Category` values, not a new taxonomy. A fourth vocabulary for the same three things
   would drift.

## Reference

`greatcto.systems/build` was studied as a structural reference. What is taken:

- The sector heading carries a muted qualifier that does the self-recognition work
  (`Dental practices · general dentistry, ortho, DSO`). A visitor scans qualifiers, not
  headings.
- Offer copy is written per sector, never templated across sectors. The same scheduling
  build is described in that sector's own nouns. This is what keeps a flat list from
  reading as padding.
- Offers carry a reusable build-type tag, so thirty-odd offers collapse visibly into a
  small number of things actually being built.
- Sibling links at the foot of a sector page, so a visitor who picked wrong does not
  dead-end.
- Static. Their `/build` ships zero JavaScript; self-identification is scroll and scan.

What is refused: the entire visual language. They are light-theme `#fafafa`, all
monospace, square corners, single green accent. `DESIGN.md` is near-black canvas,
Universal Sans display with Geist Mono for labels only, 8px card radius, pill
interactives, no chrome accent. Structure is borrowed; skin is not.

Their copy is not borrowed. Offer lines here are written fresh; any phrasing that
converged on theirs during drafting was rewritten.

## 1. Data model

`src/data/services.ts`. Mirrors the shape and commenting convention of `works.ts`.

```ts
import type { Category } from './works.ts';   // 'creative-web' | 'erp' | 'custom-build'

export interface Offer {
  /** Names the thing built, in this sector's nouns. */
  title: string;
  /** One sentence. What it does for this sector specifically. */
  body: string;
  /** Which of the three kinds of work this is. */
  category: Category;
}

export interface Sector {
  /** URL segment: /services/<slug>. Lowercase, hyphenated. */
  slug: string;
  name: string;
  /** Muted sub-label. The line a visitor scans to recognise themselves. */
  qualifier: string;
  /** One or two sentences naming what is usually broken in this sector. */
  lede: string;
  offers: Offer[]; // 3-4
  /** works.ts ids. Empty for sectors with no shipped work yet. */
  proof: string[];
}

export const sectors: Sector[] = [ /* ... */ ];
```

`Category` is imported from `works.ts` rather than redeclared.

## 2. Routes

| File | Emits |
|---|---|
| `src/pages/services/index.astro` | `/services` |
| `src/pages/services/[sector].astro` | `/services/<slug>` x 9, via `getStaticPaths` |

`src/data/nav.ts` — the `Services` entry (already renamed from `My Portfolio`) points at
`/services`.

## 3. Content

Nine sectors. Copy below is the shipping copy, subject to the owner's edit.

### 3.1 `manufacturing` — Manufacturing & Industrial

Qualifier: `machine builders, fabricators, exporters`
Proof: `miracle-cutting-machine`

Lede: You sell a machine that costs more than a car. Buyers research for months before
they call, and the site is three photographs and a phone number.

| Offer | Category | Body |
|---|---|---|
| The machine in motion | `creative-web` | The cut itself, filmed and set above the fold, with the page built around that one shot. |
| Spec sheets from one source | `creative-web` | Models, capacities, and tolerances held in one file and rendered to both the page and the PDF, so sales and the site cannot disagree. |
| Enquiries that arrive complete | `custom-build` | The form asks for material, thickness, and volume, so the first reply is a number instead of a question. |
| Production visible to the office | `erp` | What is on the floor, what is promised, and what is late, on one board. |

### 3.2 `retail-pos` — Retail & Point of Sale

Qualifier: `counters, branches, stock rooms`
Proof: `castranova-pos`, `mrspinel-staff`

Lede: Two branches and a spreadsheet works. Four branches and a spreadsheet is a daily
phone call about stock.

| Offer | Category | Body |
|---|---|---|
| A till that survives the internet | `erp` | Rings up a sale while the connection is down and reconciles when it returns. |
| One stock figure per branch | `erp` | Quantities moved by the till, not retyped into a sheet at closing. |
| The same system on the floor | `custom-build` | Inventory on a phone, so a stock check happens at the shelf. |
| Takings and margin per day | `erp` | Sales, discounts, and margin by branch, readable the next morning. |

### 3.3 `commerce` — Consumer Commerce

Qualifier: `storefronts, ordering, delivery`
Proof: `gaigai`

Lede: Selling through a marketplace or a chat account means renting the customer. The
order history belongs to the platform.

| Offer | Category | Body |
|---|---|---|
| A storefront on both stores | `custom-build` | One codebase serving the phone layout and the wider tablet grid, shipped to iOS and Android. |
| A catalogue your staff edit | `erp` | Products, stock, and prices changed by the people who know them, without a developer. |
| Orders that move in the open | `erp` | Placed, packed, dispatched, and the customer watches it happen. |
| One page whose job is the install | `creative-web` | Built for a single action, and measured against it. |

### 3.4 `studio` — Studio & Agency

Qualifier: `design, architecture, production`
Proof: `parallel`

Lede: The work is the pitch. A template flattens it into the same grid as everybody
else.

| Offer | Category | Body |
|---|---|---|
| A site the work earns | `creative-web` | Scroll-driven WebGL and typography carrying the argument, on a frame budget every effect has to justify. |
| Projects as data | `creative-web` | Adding a case study is an entry in a file, not a rebuild of a page. |
| Review without version names | `custom-build` | Comments land on the frame, versions are kept, and nothing is called final twice. |

### 3.5 `corporate` — Corporate Group

Qualifier: `holdings, multi-entity, investor-facing`
Proof: `redhorse-group`

Lede: A group of companies usually reads online as one vague page about synergy. The
subsidiaries are the substance.

| Offer | Category | Body |
|---|---|---|
| Subsidiaries with their own depth | `creative-web` | Each company its own page and its own figures, under one identity. |
| A dated archive | `creative-web` | Releases, reports, and filings published by staff without opening a ticket. |
| Careers HR can run | `custom-build` | Openings posted, applications collected, and CVs where HR can read them. |
| Figures on one definition | `erp` | Each entity's numbers in one table, calculated the same way. |

### 3.6 `inventory` — Logistics & Inventory

Qualifier: `warehouses, picks, fulfilment`
Proof: none

Lede: Stock is right on the sheet and wrong on the shelf. Every correction costs
somebody an afternoon.

| Offer | Category | Body |
|---|---|---|
| Locations, picks, and counts | `erp` | Bin locations and pick lists on a handheld, without replacing the system you already run. |
| Recorded at the door | `erp` | Receipts and dispatches entered once, by the person who moved the box. |
| Where the count goes wrong | `erp` | Variance by item and by location, so the cause is visible rather than inferred. |

### 3.7 `workforce` — HR & Workforce

Qualifier: `rosters, onboarding, records`
Proof: none

Lede: Leave requests in a chat app, contracts in a drive folder, and one person who
knows where everything is.

| Offer | Category | Body |
|---|---|---|
| A rota built once | `erp` | Open shifts posted and swaps accepted, inside the coverage rules you set. |
| Leave with a balance | `erp` | Requests, approvals, and remaining days in one place, on a record that outlives the person keeping it. |
| Onboarding that closes | `erp` | Documents collected and accounts created against a checklist that finishes. |
| Records per person | `erp` | Contracts, roles, and history, with access you control. |

### 3.8 `hospitality` — Hospitality & F&B

Qualifier: `restaurants, cafes, hotels`
Proof: none

Lede: The aggregators take a share of every order and keep the customer. Your own
channel costs nothing per order.

| Offer | Category | Body |
|---|---|---|
| Ordering on your own page | `custom-build` | Table, pickup, or delivery, at your prices, through a channel you own. |
| Bookings off the phone | `erp` | Tables or rooms self-booked against real availability, confirmed and reminded automatically. |
| One screen for the kitchen | `erp` | Every channel's orders in the sequence they arrived. |
| A room that photographs well | `creative-web` | The space and the plates at the size they deserve, loading fast on a phone outside. |

### 3.9 `professional` — Professional Services

Qualifier: `clinics, firms, consultancies`
Proof: none

Lede: The calendar is the product. Most of the admin around it is still typed twice.

| Offer | Category | Body |
|---|---|---|
| Clients book themselves | `erp` | Self-scheduling against real availability, with reminders that cut no-shows. |
| Files per client | `erp` | Notes, documents, and history in one record, with access you can audit. |
| Time that becomes an invoice | `erp` | Hours booked against a matter raise the invoice, and the invoice chases itself. |
| The first three questions answered | `creative-web` | What you do, who for, and how to start, before the phone rings. |

## 4. `/services` — index page

Four bands. No client JavaScript beyond the existing `data-inview` reveal.

1. **Hero.** `.label` eyebrow `Services`. `h1` at `display-xl`:
   *Nine sectors. What I would build for each.*
   Sub in `.body-lg`, capped near 60ch: *Pick the one that describes your operation.
   Each page lists what I would build for it, and names the clients where the work
   already exists.*
2. **Sector grid.** Nine `.card`s, `repeat(auto-fit, minmax(280px, 1fr))`, one column
   below 768px. Each card, in fixed order: sector name as `h3` at `display-sm`;
   qualifier in `.micro` mono; offer titles as a plain unordered list; a meta row of
   the distinct category tags present, with a trailing arrow. The entire card is one
   `<a>` to `/services/<slug>`; tags and the arrow are text, never nested anchors.
3. **How I work.** A short line and an outline pill to home's `#process`. Home owns
   those four steps. They are linked, never restated, so the two cannot drift.
4. **One door.** The page's single `.pill-btn--filled` white pill, to the email
   address. `DESIGN.md`: one filled pill per view.

## 5. `/services/<slug>` — sector page

Five bands, the third conditional.

1. **Hero.** Mono eyebrow `Services / <name>`. `h1` at `display-lg` is the sector name.
   The lede in `.body-lg`.
2. **What I would build.** Three or four offer cards. Each: category tag in `.micro`
   mono, title as `h3` at `display-xs`, body at `body-md`.
3. **Proof.** Renders only when `proof` is non-empty. Each entry's client, year, and
   stack are read from `works.ts` by id and never retyped. Chips are plain text, not
   links: four of the six cited ids — `parallel`, `redhorse-group`, `mrspinel-staff`,
   `gaigai` — carry `homeOnly: true` and have no page on `/works` to point at. Only
   `miracle-cutting-machine` and `castranova-pos` could link. Rather than let the
   treatment vary by the accident of where an entry happens to live, no chip links.
   The four sectors with no proof omit this band entirely — no empty state, no
   "coming soon".
4. **Adjacent sectors.** Three sibling outline pills, so a wrong pick does not
   dead-end.
5. **Closing.** An outline pill back to `/services`, and the email pill.

This band order is the mitigation for decision 2's known cost: the offers come before
the proof, so a sector page leads with what would be built rather than with an absence.

## 6. Reuse

Existing primitives only: `.container`, `.grid`, `.card`, `.pill-btn`,
`.pill-btn--filled`, `.label`, `.micro`, `.h1` through `.h6`, `.body-lg`,
`Layout.astro`, `Header.astro`, `Footer.astro`, and the `data-inview` reveal. No new
dependency, no new style primitive, no hand-rolled button. Colours, spacing, radii, and
type come from `src/styles/_vars.scss` as tokens; no literal hex or px value in either
page.

## 7. Accessibility

WCAG 2.2 AA, per `PRODUCT.md`.

- `--c-mute` (about 3.5:1) carries qualifiers and category tags only, which are
  metadata. All lede and offer copy uses `--c-body` `#dadbdf`.
- Heading order: `h1`, then `h2` per band, then `h3` per card or offer.
- One anchor per sector card; nothing nested inside it is focusable.
- Focus indicators inherited from `_base.scss`, unmodified.
- Category is conveyed by its text label, never by colour alone. There is no accent
  colour on this surface: `DESIGN.md` reserves sunset and dusk for illustration.
- No motion is load-bearing. The `data-inview` reveal already gates on
  `prefers-reduced-motion`.

## 8. Verification

`src/data/services.test.mjs`, modelled on `works.test.mjs`, asserting:

- every `slug` is unique and matches `/^[a-z0-9-]+$/`;
- every `name`, `qualifier`, and `lede` is present and non-blank;
- every sector has at least one offer, and every offer has a non-blank title and body;
- every offer `category` is one of the three `works.ts` values;
- every id in `proof` resolves to a real entry in `works.ts`, **and does not begin with
  `placeholder-`** — `works.ts` holds six placeholder entries and none may ever be cited
  as evidence.

Registered in `package.json` as `test:services`, alongside the four existing `test:*`
scripts.

Also required to pass:

- `npm run build` (which runs `astro check` first) emits ten new routes.
- Layout checked by eye at 360px and 1440px.

## 9. Open items

Neither blocks implementation.

1. **The constellation's metadata.** `public/constellation/index.html` is an unmodified
   static export of a third-party Next.js template. It ships
   `<title>Your Name — Design / Engineering / Product</title>`, an `og:url` of
   `https://yourdomain.com/`, a `twitter:creator` of `@yourusername`, and
   `robots: index, follow`. It is currently indexable. Once it leaves the navbar it
   should at minimum be set `noindex`, and arguably retired: it also sits against
   `PRODUCT.md` anti-reference 5.
2. **`PRODUCT.md` needs updating** once this ships: its public-surface list names
   "My Portfolio (3D constellation)" and should name Services instead.
