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
  {
    id: 'placeholder-erp-02',
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
];

/** Projects for one chapter, in file order. Home-only work is excluded. */
export const worksFor = (category: Category): Work[] =>
  works.filter((w) => w.category === category && !w.homeOnly);
