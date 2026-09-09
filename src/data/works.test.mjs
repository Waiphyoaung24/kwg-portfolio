import assert from 'node:assert/strict';
import { chapters, works, worksFor } from './works.ts';

const VALID = new Set(['creative-web', 'erp', 'custom-build']);

// Ids address panels and tabs via aria-controls; a duplicate silently breaks
// the tablist wiring rather than throwing, so assert it here.
const ids = new Set();
for (const w of works) {
  assert.ok(!ids.has(w.id), `duplicate work id: ${w.id}`);
  ids.add(w.id);

  assert.ok(VALID.has(w.category), `${w.id}: bad category ${w.category}`);
  assert.ok(w.title && w.title.trim(), `${w.id}: title required`);
  assert.ok(w.client && w.client.trim(), `${w.id}: client required`);
  assert.ok(Number.isInteger(w.year), `${w.id}: year must be an integer`);
  assert.ok(Array.isArray(w.stack) && w.stack.length > 0, `${w.id}: stack required`);
  assert.ok(w.summary && w.summary.trim(), `${w.id}: summary required`);
  assert.ok(w.media === null || typeof w.media === 'object', `${w.id}: bad media`);
  if (w.media) {
    assert.ok(
      w.media.kind === 'video' || w.media.kind === 'image',
      `${w.id}: unsupported media kind`,
    );
    assert.ok(w.media.poster.startsWith('/works/'), `${w.id}: bad poster`);
    assert.ok(w.media.posterWidth > 0, `${w.id}: poster width required`);
    assert.ok(w.media.posterHeight > 0, `${w.id}: poster height required`);
    assert.ok(w.media.alt.trim(), `${w.id}: media alt required`);
    // Only a film carries the two edits; a still has a poster and nothing else.
    if (w.media.kind === 'video') {
      assert.ok(w.media.landscape.endsWith('.mp4'), `${w.id}: bad landscape video`);
      assert.ok(w.media.portrait.endsWith('.mp4'), `${w.id}: bad portrait video`);
    }
  }

  // Home-only work is reachable ONLY through Selected Work, so without both a
  // caption and a poster it renders in neither place.
  if (w.homeOnly) {
    assert.ok(w.featured, `${w.id}: homeOnly needs featured`);
    assert.ok(w.media, `${w.id}: homeOnly needs media`);
  }
  assert.ok(w.url === null || typeof w.url === 'string', `${w.id}: bad url`);
}

// Every chapter must render at least one panel, or its tablist is empty.
const seen = new Set();
for (const c of chapters) {
  assert.ok(VALID.has(c.category), `bad chapter category ${c.category}`);
  assert.ok(!seen.has(c.category), `duplicate chapter for ${c.category}`);
  seen.add(c.category);
  assert.ok(c.heading && c.heading.trim(), `${c.category}: heading required`);
  assert.ok(c.intro && c.intro.trim(), `${c.category}: intro required`);
  assert.ok(worksFor(c.category).length > 0, `${c.category}: no projects`);
}

// No project may be orphaned from a chapter — it would never render. Home-only
// work is the deliberate exception: it renders in Selected Work instead, and
// `worksFor` keeps it out of the exhibit.
for (const w of works) {
  if (w.homeOnly) continue;
  assert.ok(seen.has(w.category), `${w.id}: category has no chapter`);
}

assert.equal(seen.size, VALID.size, 'every category needs a chapter');

const homeOnly = works.filter((w) => w.homeOnly).length;
console.log(
  `ok: ${works.length} works across ${chapters.length} chapters ` +
    `(${homeOnly} home-only)`,
);
