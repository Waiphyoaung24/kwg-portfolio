import assert from 'node:assert/strict';
import { chapters, works } from './works.ts';

const VALID = new Set(['creative-web', 'erp', 'custom-build']);

// Ids are the card anchors (/works#work-<id>) the home overlay deep-links to;
// a duplicate silently lands on the wrong card rather than throwing.
const ids = new Set();
for (const w of works) {
  assert.ok(!ids.has(w.id), `duplicate work id: ${w.id}`);
  ids.add(w.id);

  assert.ok(VALID.has(w.category), `${w.id}: bad category ${w.category}`);
  assert.ok(w.title && w.title.trim(), `${w.id}: title required`);
  // Placeholders never ship: /works renders every entry in this file.
  assert.ok(!w.title.startsWith('TODO'), `${w.id}: placeholder title`);
  assert.ok(w.client && w.client.trim(), `${w.id}: client required`);
  assert.ok(Number.isInteger(w.year), `${w.id}: year must be an integer`);
  assert.ok(
    Array.isArray(w.stack) && w.stack.length > 0,
    `${w.id}: stack required`,
  );
  assert.ok(w.summary && w.summary.trim(), `${w.id}: summary required`);
  assert.ok(
    w.media === null || typeof w.media === 'object',
    `${w.id}: bad media`,
  );
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
      assert.ok(
        w.media.landscape.endsWith('.mp4'),
        `${w.id}: bad landscape video`,
      );
      assert.ok(
        w.media.portrait.endsWith('.mp4'),
        `${w.id}: bad portrait video`,
      );
    }
  }

  // The flag only changes the home overlay's CTA, so it is meaningless on
  // work that never reaches the overlay.
  if (w.homeOnly) assert.ok(w.featured, `${w.id}: homeOnly needs featured`);
  assert.ok(w.url === null || typeof w.url === 'string', `${w.id}: bad url`);
}

// Every filter pill must match at least one card, or it empties the grid.
const seen = new Set();
for (const c of chapters) {
  assert.ok(VALID.has(c.category), `bad chapter category ${c.category}`);
  assert.ok(!seen.has(c.category), `duplicate chapter for ${c.category}`);
  seen.add(c.category);
  assert.ok(c.heading && c.heading.trim(), `${c.category}: heading required`);
  assert.ok(
    works.some((w) => w.category === c.category),
    `${c.category}: no projects`,
  );
}

// No project may sit outside every filter; the page groups cards by chapter,
// so it would not render at all.
for (const w of works) {
  assert.ok(seen.has(w.category), `${w.id}: category has no chapter`);
}

assert.equal(seen.size, VALID.size, 'every category needs a chapter');

const homeOnly = works.filter((w) => w.homeOnly).length;
console.log(
  `ok: ${works.length} works across ${chapters.length} chapters ` +
    `(${homeOnly} home-only)`,
);
