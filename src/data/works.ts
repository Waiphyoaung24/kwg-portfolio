// Works — single source of truth for the /works exhibit.
//
// Adding or editing a project is a change to THIS FILE ONLY. The page and the
// chapter component read from `works` and render whatever is here.
//
// `media: null` renders a labelled empty panel rather than a stock photo
// (PRODUCT.md anti-reference 4). `url: null` hides the live link.
//
// See docs/works-page-design.md §7.

export type Category = 'creative-web' | 'erp' | 'custom-build';

interface WorkMediaBase {
  poster: string;
  posterWidth: number;
  posterHeight: number;
  alt: string;
}

/** A showcase film. The poster is the frame shown before it plays. */
export interface WorkVideo extends WorkMediaBase {
  kind: 'video';
  landscape: string;
  portrait: string;
}

/** A still. Some work has a poster and no film behind it. */
export interface WorkImage extends WorkMediaBase {
  kind: 'image';
}

export type WorkMedia = WorkVideo | WorkImage;

/** One frame of a store listing, shown in the home overlay's strip. */
export interface WorkScreen {
  src: string;
  width: number;
  height: number;
  /** The frame's own headline, so the strip reads as sentences. */
  alt: string;
}

export interface Work {
  /** unique, kebab-case */
  id: string;
  category: Category;
  title: string;
  /** client name, or 'Personal' */
  client: string;
  year: number;
  stack: string[];
  summary: string;
  /** responsive exhibit media, or null for the empty state */
  media: WorkMedia | null;
  /** live link, or null to hide the CTA */
  url: string | null;
  /**
   * Store listing frames for the home overlay, in listing order. Exhibited
   * work: they keep their own styling (CLAUDE.md), the site only frames them.
   */
  screens?: WorkScreen[];
  /** short homepage caption; presence includes the work in Selected Work */
  featured?: string;
  /**
   * Show in Selected Work on the home page but keep out of the /works
   * exhibit. `worksFor` skips these, so they never reach a chapter panel —
   * which also means their category is inert, and that nothing deep-links to
   * `/works#panel-<id>` for them.
   */
  homeOnly?: true;
}

export interface Chapter {
  /** two-digit chapter number shown in the label */
  index: string;
  category: Category;
  heading: string;
  intro: string;
}

/** Chapter order on the page. */
export const chapters: Chapter[] = [
  {
    index: '02',
    category: 'creative-web',
    heading: 'Creative Websites',
    intro:
      'Sites where the interface is the argument. Scroll-driven narrative, WebGL, and typography carrying weight that copy cannot. Every effect here has to earn its frame budget.',
  },
  {
    index: '03',
    category: 'erp',
    heading: 'ERP Software',
    intro:
      'Internal systems that people use for eight hours a day. Density over decoration, keyboard paths over clicks, and schemas that survive the second year of requirements.',
  },
  {
    index: '04',
    category: 'custom-build',
    heading: 'Custom Web & Mobile',
    intro:
      'Commissioned builds shaped to one operation rather than a template. Web and mobile, delivered end to end from data model to deployment.',
  },
];

export const works: Work[] = [
  // ---- Creative websites -------------------------------------------------
  {
    id: 'miracle-cutting-machine',
    category: 'creative-web',
    title: 'Miracle Cutting Machine',
    client: 'Miracle Cutting Machine',
    year: 2026,
    stack: ['HyperFrames', 'GSAP', 'HTML/CSS', 'FFmpeg'],
    summary:
      'A product film built from the client’s real machine imagery. Five stages explain the cutting system, delivered as dedicated landscape and vertical edits that read with or without sound.',
    media: {
      kind: 'video',
      poster: '/works/miracle-cutting-machine-poster.webp',
      posterWidth: 1920,
      posterHeight: 1080,
      alt: 'The Miracle Cutting Machine home page, its monogram over the machine lineup',
      landscape: '/works/miracle-cutting-machine-16x9.mp4',
      portrait: '/works/miracle-cutting-machine-9x16.mp4',
    },
    url: 'https://miraclecuttingmachine.com/',
    featured: 'Product film · Web',
  },
  {
    id: 'kage',
    category: 'creative-web',
    title: 'Kage',
    client: 'Personal',
    year: 2026,
    stack: ['Three.js', 'GSAP', 'Lenis', 'Vanilla JS'],
    summary:
      'A standalone landing page built around a single idea: stillness reveals the unseen. The type sets the pace and the scene reacts to it, rather than the reverse. Runs as a self-contained document with no framework runtime.',
    media: null,
    url: '/catalog/kage/live',
  },
  {
    id: 'placeholder-creative-03',
    category: 'creative-web',
    title: 'TODO — Project name',
    client: 'TODO — Client',
    year: 2025,
    stack: ['TODO', 'TODO'],
    summary:
      'TODO — two or three technical sentences. What the constraint was, what you built, what it cost. No adjectives.',
    media: null,
    url: null,
  },

  // ---- ERP software ------------------------------------------------------
  {
    id: 'castranova-pos',
    category: 'erp',
    title: 'CastraNova POS',
    client: 'Castra Nova',
    year: 2026,
    stack: ['React', 'FastAPI', 'HyperFrames', 'Playwright'],
    summary:
      'A case study for a point-of-sale and inventory system, built from authenticated UI captures against an isolated seeded database. It shows sales, stock control, audit trails, and offline sync without exposing client data.',
    media: {
      kind: 'video',
      poster: '/works/castranova-pos-poster.png',
      posterWidth: 1920,
      posterHeight: 1080,
      alt: 'The Castra Nova wordmark over a dimmed capture of the POS dashboard',
      landscape: '/works/castranova-pos-16x9.mp4',
      portrait: '/works/castranova-pos-9x16.mp4',
    },
    url: 'https://pos.castranova.cloud/',
    featured: 'ERP system · Case study',
  },
  // Every field here is read off the source repo, not recalled: the year is
  // the span of its git history (2026-05-03 to 2026-09-04), the stack comes
  // from the apps/api and apps/app manifests, and the modules are the 28
  // tables under db/schema/hrm plus the 13 under db/schema/recruitment.
  //
  // That repo is still named HR-NexApex and its docs still call the product
  // that; Parallel HRM is the rebrand, which is why the two names disagree.
  {
    id: 'parallel-hrm',
    category: 'erp',
    title: 'Parallel HRM',
    client: 'Parallel',
    year: 2026,
    stack: [
      'React',
      'tRPC',
      'Hono',
      'Drizzle',
      'Postgres',
      'Cloudflare Workers',
    ],
    summary:
      'A multi-tenant ATS and HRMS for SME teams: recruitment, employee records, leave and attendance, payroll runs and payslips, performance reviews, and attrition scoring in one product. Tenant isolation is enforced in application queries and procedure guards rather than Postgres RLS, which makes the tenant filter and its tests a single security boundary. CV matching runs on pgvector embeddings.',
    media: {
      kind: 'image',
      poster: '/works/product/parallel-hrm.webp',
      posterWidth: 1280,
      posterHeight: 800,
      alt: 'The Parallel HRM people dashboard',
    },
    url: null,
  },
  {
    id: 'placeholder-erp-03',
    category: 'erp',
    title: 'TODO — System name',
    client: 'TODO — Client',
    year: 2024,
    stack: ['TODO', 'TODO'],
    summary:
      'TODO — which modules, how many users, what the data model had to absorb. Name the hard part.',
    media: null,
    url: null,
  },

  // ---- Custom web & mobile ----------------------------------------------
  {
    id: 'placeholder-custom-01',
    category: 'custom-build',
    title: 'TODO — Build name',
    client: 'TODO — Client',
    year: 2025,
    stack: ['TODO', 'TODO'],
    summary:
      'TODO — platform, scope, and what shipping it required. State the delivery boundary.',
    media: null,
    url: null,
  },
  {
    id: 'placeholder-custom-02',
    category: 'custom-build',
    title: 'TODO — Build name',
    client: 'TODO — Client',
    year: 2025,
    stack: ['TODO', 'TODO'],
    summary:
      'TODO — platform, scope, and what shipping it required. State the delivery boundary.',
    media: null,
    url: null,
  },
  {
    id: 'placeholder-custom-03',
    category: 'custom-build',
    title: 'TODO — Build name',
    client: 'TODO — Client',
    year: 2024,
    stack: ['TODO', 'TODO'],
    summary:
      'TODO — platform, scope, and what shipping it required. State the delivery boundary.',
    media: null,
    url: null,
  },

  // ---- Home page only ----------------------------------------------------
  // Selected Work on the home page, deliberately absent from the /works
  // exhibit (`homeOnly`). Category is still required by the type but never
  // reaches a chapter, so it is chosen for accuracy rather than routing.
  {
    id: 'parallel',
    category: 'creative-web',
    title: 'Parallel',
    client: 'Parallel',
    year: 2026,
    stack: ['Astro', 'WebGL', 'GSAP', 'Lenis'],
    summary:
      'A studio site for a Bangkok branding and technology practice. Imagery runs through a WebGL ASCII pass rather than being shown straight, and the work index scrolls sideways across a perspective plane instead of down a grid. Static Astro carrying three client scripts in total, so the frame budget goes to the canvas rather than a framework runtime.',
    media: {
      kind: 'image',
      poster: '/works/parallel-poster.webp',
      posterWidth: 1920,
      posterHeight: 1080,
      alt: 'The Parallel home page, its wordmark over the studio’s gradient hero',
    },
    url: 'https://parallelsolution.co/',
    featured: 'Studio site · Web',
    homeOnly: true,
  },
  {
    id: 'redhorse-group',
    category: 'creative-web',
    title: 'Red Horse Group',
    client: 'Red Horse Group',
    year: 2026,
    stack: ['Astro', 'React', 'HTML/CSS'],
    summary:
      'A corporate site for a Myanmar group trading since 1993, covering manufacturing, distribution and dairy. Static Astro pages with React islands only where a section actually moves, so the scale figures and division stack carry the argument rather than the chrome.',
    media: {
      kind: 'image',
      poster: '/works/redhorse-group-poster.webp',
      posterWidth: 1920,
      posterHeight: 1080,
      alt: 'The Red Horse Group home page, its knight mark over the dairy pasture hero',
    },
    url: 'https://redhorse.nexapex.ai/',
    featured: 'Corporate site · Web',
    homeOnly: true,
  },
  {
    id: 'mrspinel-staff',
    category: 'custom-build',
    title: 'Mr Spinel',
    client: 'Mr Spinel',
    year: 2026,
    stack: ['React', 'Vite', 'Electron', 'Capacitor', 'Supabase'],
    summary:
      'A gemstone inventory book for a wholesale dealer in Myanmar: loose stones and parcels, goods out on consignment, and a sales ledger that takes partial lot sales. Ships as an Electron desktop app for the office and an iOS staff app that scans stones in against the same Postgres.',
    media: {
      kind: 'image',
      poster: '/works/mrspinel-staff-poster.webp',
      posterWidth: 1920,
      posterHeight: 1080,
      alt: 'The Mr Spinel desktop Overview with the iOS staff dashboard alongside it',
    },
    url: null,
    featured: 'Desktop & iOS · Inventory',
    homeOnly: true,
  },
  {
    id: 'gaigai',
    category: 'custom-build',
    title: 'GaiGai',
    client: 'An Xing Technology',
    year: 2022,
    stack: ['Flutter', 'Dart'],
    summary:
      'A grocery commerce app for a Singapore e-supermarket, carrying a catalogue of over 7,000 products browsable by category and by country of origin. Cart, checkout and voucher promotions run off the same catalogue, and one Flutter codebase serves both the phone layout and the wider tablet grid.',
    media: {
      kind: 'image',
      poster: '/works/gaigai-poster.webp',
      posterWidth: 1920,
      posterHeight: 1080,
      alt: 'The GaiGai tablet storefront with the phone home screen alongside it',
    },
    url: null,
    // The App Store listing as shipped: five phone frames, then the same
    // five for tablet. Each is the listing card cropped out of a phone
    // screenshot of the store page (status bar and close button gone) and
    // exported at one shared height, so the strip sets them by height and
    // the two card shapes sit on one baseline.
    screens: [
      'Welcome to GaiGai eSupermarket. Everything you need for your daily life at your fingertips.',
      'Over 7000 products to choose from: snacks, drinks, groceries.',
      'Save more with free delivery, no minimum purchase.',
      'Shop your snacks, drinks and groceries easily, by category and by country.',
      'Get rewarded for shopping: a $5 voucher with any purchase of $25 or more.',
      'Tablet layout: welcome to GaiGai eSupermarket.',
      'Tablet layout: over 7000 products to choose from.',
      'Tablet layout: free delivery with no minimum purchase.',
      'Tablet layout: shop by category and by country.',
      'Tablet layout: a $5 voucher with any purchase of $25 or more.',
    ].map((alt, i) => ({
      src: `/works/gaigai/frame-${String(i + 1).padStart(2, '0')}.webp`,
      width: i < 5 ? 373 : 600,
      height: 800,
      alt,
    })),
    featured: 'iOS & Android · Grocery commerce',
    homeOnly: true,
  },
];

/** Projects for one chapter, in file order. Home-only work is excluded. */
export const worksFor = (category: Category): Work[] =>
  works.filter((w) => w.category === category && !w.homeOnly);
