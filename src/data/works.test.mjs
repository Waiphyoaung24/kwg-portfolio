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
  assert.ok(w.media === null || typeof w.media === 'string', `${w.id}: bad media`);
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

// No project may be orphaned from a chapter — it would never render.
for (const w of works) {
  assert.ok(seen.has(w.category), `${w.id}: category has no chapter`);
}

assert.equal(seen.size, VALID.size, 'every category needs a chapter');

console.log(`ok: ${works.length} works across ${chapters.length} chapters`);
