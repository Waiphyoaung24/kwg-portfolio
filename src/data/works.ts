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
  /** path under /works/, or null for the empty state */
  media: string | null;
  /** live link, or null to hide the CTA */
  url: string | null;
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
    id: 'kage',
    category: 'creative-web',
    title: 'Kage',
    client: 'Personal',
    year: 2026,
    stack: ['Three.js', 'GSAP', 'Lenis', 'Vanilla JS'],
    summary:
      'A standalone landing page built around a single idea: stillness reveals the unseen. The type sets the pace and the scene reacts to it, rather than the reverse. Runs as a self-contained document with no framework runtime.',
    media: null,
    url: '/page-2',
  },
  {
    id: 'placeholder-creative-02',
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
    id: 'placeholder-erp-01',
    category: 'erp',
    title: 'TODO — System name',
    client: 'TODO — Client',
    year: 2025,
    stack: ['TODO', 'TODO'],
    summary:
      'TODO — which modules, how many users, what the data model had to absorb. Name the hard part.',
    media: null,
    url: null,
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
];

/** Projects for one chapter, in file order. */
export const worksFor = (category: Category): Work[] =>
  works.filter((w) => w.category === category);
