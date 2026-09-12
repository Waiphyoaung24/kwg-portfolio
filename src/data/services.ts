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
    // CastraNova only. Mr Spinel is also an inventory system, but citing both
    // here and on `inventory` showed a visitor the same two summaries twice
    // across neighbouring sectors. Split by what each build leads with: the
    // till and the counter here, the stock ledger there.
    proof: ['castranova-pos'],
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
    // Mr Spinel only, as the counterpart to retail-pos keeping CastraNova.
    // works.ts records it as "a gemstone inventory book" tracking loose stones
    // and parcels, goods out on consignment, and partial lot sales — a stock
    // ledger, which is what this sector is about.
    proof: ['mrspinel-staff'],
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
