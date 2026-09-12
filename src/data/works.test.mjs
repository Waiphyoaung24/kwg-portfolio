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

// Every project renders in a chapter. The home-only exception is gone: the
// exhibit and Selected Work now draw from the same set, filtered differently
// (index.astro selects on `featured && media`).
for (const w of works) {
  assert.ok(seen.has(w.category), `${w.id}: category has no chapter`);
}

assert.equal(seen.size, VALID.size, 'every category needs a chapter');

// The exhibit is a carousel of full-viewport slides, so a placeholder costs a
// whole screen. Nothing ships with TODO copy (spec D9).
for (const w of works) {
  const copy = [w.title, w.client, w.summary, ...w.stack].join(' ');
  assert.ok(!copy.includes('TODO'), `${w.id}: placeholder copy in the exhibit`);
}

// A slide is textured from its poster. Kage is the one permitted gap and
// renders the labelled empty panel instead.
const ALLOWED_EMPTY = new Set(['kage']);
for (const w of works) {
  assert.ok(
    w.media !== null || ALLOWED_EMPTY.has(w.id),
    `${w.id}: needs media, or an entry in ALLOWED_EMPTY`,
  );
}

const perChapter = chapters
  .map((c) => `${c.index}:${worksFor(c.category).length}`)
  .join(' ');
console.log(`ok: ${works.length} works across ${chapters.length} chapters (${perChapter})`);
