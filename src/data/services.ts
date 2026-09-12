import type { Category } from './works';

/** One thing that gets built, named in this sector's own nouns. */
export interface Offer {
  /**
   * The product name a buyer already recognises — "Instant quoting", not
   * "Enquiries that arrive complete". PRODUCT.md puts this audience as "less
   * fluent in craft language": the craft voice belongs in the body and on the
   * peer-facing surfaces, never in the thing a client is trying to identify.
   */
  title: string;
  /** One sentence. What it does for this sector specifically. */
  body: string;
  /** Which of the three kinds of work this is, per works.ts. */
  category: Category;
  /** A Feather glyph name from src/data/icons.ts. */
  icon: string;
}

export interface Sector {
  /** URL segment: /services/<slug>. Lowercase, hyphenated. */
  slug: string;
  /** A Feather glyph name from src/data/icons.ts. */
  icon: string;
  name: string;
  /** Muted sub-label — the line a visitor scans to recognise themselves. */
  qualifier: string;
  /** One or two sentences naming what is usually broken in this sector. */
  lede: string;
  offers: Offer[];
  /**
   * works.ts ids. Read back at build time so a client name, year or stack is
   * never retyped here. Empty for the sectors with no shipped work yet —
   * those pages omit the proof band entirely rather than show an empty state.
   */
  proof: string[];
}

// Cut by the client's taxonomy, not the seller's. Home's 05 — Capabilities
// already cuts the same work by deliverable; a machine exporter and a
// restaurant owner both have to translate that. These nine let them skip it.
//
// Four offers per sector, so the nine cards carry the same weight and no row
// reads as padding.
export const sectors: Sector[] = [
  {
    slug: 'manufacturing',
    icon: 'tool',
    name: 'Manufacturing & Industrial',
    qualifier: 'machine builders, fabricators, exporters',
    lede: 'You sell a machine that costs more than a car. Buyers research for months before they call, and the site is three photographs and a phone number.',
    offers: [
      {
        title: 'Product film & landing page',
        body: 'Your machine filmed running, on a page built around that one shot.',
        category: 'creative-web',

        icon: 'play-circle',
      },
      {
        title: 'Spec & model catalogue',
        body: 'Every model, capacity and tolerance on the site and in the downloadable PDF, out of one file.',
        category: 'creative-web',

        icon: 'file-text',
      },
      {
        title: 'Instant quoting',
        body: 'The enquiry form captures material, thickness and volume, so your reply is a price instead of a question.',
        category: 'custom-build',

        icon: 'dollar-sign',
      },
      {
        title: 'Production tracking',
        body: 'What is on the floor, what is promised and what is late, on one board the office can read.',
        category: 'erp',

        icon: 'activity',
      },
    ],
    proof: ['miracle-cutting-machine'],
  },
  {
    slug: 'retail-pos',
    icon: 'credit-card',
    name: 'Retail & Point of Sale',
    qualifier: 'counters, branches, stock rooms',
    lede: 'Two branches and a spreadsheet works. Four branches and a spreadsheet is a daily phone call about stock.',
    offers: [
      {
        title: 'Point of sale',
        body: 'Rings up sales offline when the connection drops, and reconciles when it returns.',
        category: 'erp',

        icon: 'credit-card',
      },
      {
        title: 'Multi-branch stock',
        body: 'One quantity per item per location, moved by the till rather than by a sheet at closing.',
        category: 'erp',

        icon: 'layers',
      },
      {
        title: 'Stock app for staff',
        body: 'The same inventory on a phone, so a stock check happens at the shelf.',
        category: 'custom-build',

        icon: 'smartphone',
      },
      {
        title: 'Daily sales & margin',
        body: 'Takings, discounts and margin by branch, ready the next morning.',
        category: 'erp',

        icon: 'trending-up',
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
    icon: 'shopping-cart',
    name: 'Consumer Commerce',
    qualifier: 'storefronts, ordering, delivery',
    lede: 'Selling through a marketplace or a chat account means renting the customer. The order history belongs to the platform.',
    offers: [
      {
        title: 'Storefront app',
        body: 'One build shipped to iOS and Android, serving the phone layout and the wider tablet grid.',
        category: 'custom-build',

        icon: 'smartphone',
      },
      {
        title: 'Catalogue & pricing',
        body: 'Products, stock and prices edited by your own staff, live, without a developer.',
        category: 'erp',

        icon: 'tag',
      },
      {
        title: 'Order & delivery tracking',
        body: 'An order moves from placed to packed to out for delivery, and the customer watches it move.',
        category: 'erp',

        icon: 'truck',
      },
      {
        title: 'App install page',
        body: 'One landing page built for a single action, and measured against it.',
        category: 'creative-web',

        icon: 'download',
      },
    ],
    proof: ['gaigai'],
  },
  {
    slug: 'studio',
    icon: 'pen-tool',
    name: 'Studio & Agency',
    qualifier: 'design, architecture, production',
    lede: 'The work is the pitch. A template flattens it into the same grid as everybody else.',
    offers: [
      {
        title: 'Portfolio site',
        body: 'Scroll-driven WebGL and typography carrying the argument, on a frame budget every effect has to justify.',
        category: 'creative-web',

        icon: 'monitor',
      },
      {
        title: 'Project CMS',
        body: 'Adding a case study is an entry in a file, not a rebuild of the page.',
        category: 'creative-web',

        icon: 'folder',
      },
      {
        title: 'Client review & approvals',
        body: 'Comments land on the frame, versions are kept, and nothing gets called final twice.',
        category: 'custom-build',

        icon: 'message-square',
      },
      {
        title: 'Proposal & contract builder',
        body: 'The scope you already wrote becomes the document the client signs, no retyping.',
        category: 'custom-build',

        icon: 'file-text',
      },
    ],
    proof: ['parallel'],
  },
  {
    slug: 'corporate',
    icon: 'briefcase',
    name: 'Corporate Group',
    qualifier: 'holdings, multi-entity, investor-facing',
    lede: 'A group of companies usually reads online as one vague page about synergy. The subsidiaries are the substance.',
    offers: [
      {
        title: 'Group & subsidiary site',
        body: 'Each company its own page and its own figures, under one identity.',
        category: 'creative-web',

        icon: 'layers',
      },
      {
        title: 'News & reports archive',
        body: 'Releases, reports and filings published by staff without opening a ticket.',
        category: 'creative-web',

        icon: 'archive',
      },
      {
        title: 'Careers & applications',
        body: 'Openings posted, applications collected, and CVs where HR can actually read them.',
        category: 'custom-build',

        icon: 'user-plus',
      },
      {
        title: 'Group reporting',
        body: 'Each entity’s numbers in one table, calculated the same way.',
        category: 'erp',

        icon: 'bar-chart-2',
      },
    ],
    proof: ['redhorse-group'],
  },
  {
    slug: 'inventory',
    icon: 'package',
    name: 'Logistics & Inventory',
    qualifier: 'warehouses, picks, fulfilment',
    lede: 'Stock is right on the sheet and wrong on the shelf. Every correction costs somebody an afternoon.',
    offers: [
      {
        title: 'Warehouse & bin locations',
        body: 'Bin locations, pick lists and cycle counts on a handheld, without replacing the system you already run.',
        category: 'erp',

        icon: 'grid',
      },
      {
        title: 'Goods in & goods out',
        body: 'Receipts and dispatches entered once, at the door, by whoever moved the box.',
        category: 'erp',

        icon: 'truck',
      },
      {
        title: 'Stock accuracy reporting',
        body: 'Variance by item and by location, so you can see where the count goes wrong.',
        category: 'erp',

        icon: 'pie-chart',
      },
      {
        title: 'Purchase orders',
        body: 'Orders to suppliers approved in one place, with what is still outstanding visible against each one.',
        category: 'erp',

        icon: 'clipboard',
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
    icon: 'users',
    name: 'HR & Workforce',
    qualifier: 'hiring, rosters, payroll, records',
    lede: 'Leave requests in a chat app, contracts in a drive folder, and one person who knows where everything is.',
    // These four are what Parallel HRM below actually ships, read off its
    // schema rather than guessed at. Performance reviews and attrition scoring
    // are the two real modules left out for want of a fifth slot.
    offers: [
      {
        title: 'Applicant tracking',
        body: 'Candidates from CV to offer, with interviews scheduled and CVs matched rather than read one at a time.',
        category: 'erp',

        icon: 'user-check',
      },
      {
        title: 'Onboarding & employee records',
        body: 'Contracts, roles and history per person, behind a joining checklist that actually closes.',
        category: 'erp',

        icon: 'user-plus',
      },
      {
        title: 'Leave, shifts & attendance',
        body: 'One rota covers the month, staff claim open shifts themselves, and a swap only goes through if cover holds.',
        category: 'erp',

        icon: 'calendar',
      },
      {
        title: 'Payroll & payslips',
        body: 'Salary structures, payroll runs and payslips, calculated from the attendance you already record.',
        category: 'erp',

        icon: 'dollar-sign',
      },
    ],
    proof: ['parallel-hrm'],
  },
  {
    slug: 'hospitality',
    icon: 'coffee',
    name: 'Hospitality & F&B',
    qualifier: 'restaurants, cafes, hotels',
    lede: 'The aggregators take a share of every order and keep the customer. Your own channel costs nothing per order.',
    offers: [
      {
        title: 'Online ordering',
        body: 'Dine-in, pickup or delivery through a channel you own, at your prices.',
        category: 'custom-build',

        icon: 'shopping-bag',
      },
      {
        title: 'Reservations & waitlist',
        body: 'Guests pick a table or a room from live availability, and the confirmations and reminders send themselves.',
        category: 'erp',

        icon: 'calendar',
      },
      {
        title: 'Kitchen display',
        body: 'Every channel’s orders on one screen, in the sequence they arrived.',
        category: 'erp',

        icon: 'monitor',
      },
      {
        title: 'Venue website',
        body: 'The room and the plates at the size they deserve, loading fast on a phone outside.',
        category: 'creative-web',

        icon: 'image',
      },
    ],
    proof: [],
  },
  {
    slug: 'professional',
    icon: 'clipboard',
    name: 'Professional Services',
    qualifier: 'clinics, firms, consultancies',
    lede: 'The calendar is the product. Most of the admin around it is still typed twice.',
    offers: [
      {
        title: 'Appointment booking',
        body: 'Clients pick a slot from your real calendar, and no-show reminders go out without anyone sending them.',
        category: 'erp',

        icon: 'calendar',
      },
      {
        title: 'Client records & files',
        body: 'Notes, documents and history per client, with access you can audit.',
        category: 'erp',

        icon: 'folder',
      },
      {
        title: 'Time tracking & invoicing',
        body: 'Hours booked against a matter raise the invoice, and the invoice chases itself.',
        category: 'erp',

        icon: 'clock',
      },
      {
        title: 'Practice website',
        body: 'What you do, who for, and how to start, answered before the phone rings.',
        category: 'creative-web',

        icon: 'globe',
      },
    ],
    proof: [],
  },
];
