// One row per catalog entry. Source files live in src/catalog/<slug>/ and are
// read at build time by CatalogEntry.astro, so this list only carries metadata.

export type CatalogKind = 'Component' | 'Section' | 'Page';

export interface CatalogEntry {
  slug: string;
  title: string;
  kind: CatalogKind;
  description: string;
  stack: string;
  credit: { name: string; url: string };
  /** Article, repo or live route the code came from. */
  source: string;
  license: string;
}

export const entries: CatalogEntry[] = [
  {
    slug: 'ascii-logo',
    title: 'Shape-aware ASCII renderer',
    kind: 'Component',
    description:
      'A draggable 3D solid printed in ASCII on the GPU. Each cell samples shape data and searches all 95 printable glyphs for the best match, instead of mapping luminance to a character ramp.',
    stack: 'three.js · GLSL · custom element',
    credit: { name: 'Edoardo Lunardi', url: 'https://www.edoardolunardi.dev/' },
    source:
      'https://tympanus.net/codrops/2026/09/04/beyond-the-luminance-ramp-a-shape-aware-ascii-renderer-in-three-js/',
    license: 'MIT',
  },
  {
    slug: 'kage',
    title: 'Kage',
    kind: 'Page',
    description:
      'A five-chapter night walk through a Kyoto mountain temple. Procedural Three.js sanctuary scene, scroll-driven camera rig, post stack and live scissored card viewports, in one self-contained HTML file.',
    stack: 'HTML · Three.js r149 · GLSL',
    credit: { name: 'ThreeUI', url: 'https://threeui.dev/' },
    source: '/catalog/kage/live',
    license: 'Adapted from a ThreeUI template',
  },
];
