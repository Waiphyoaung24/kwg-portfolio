import assert from 'node:assert/strict';
import { sectors } from './services.ts';
import { works } from './works.ts';
import { icons } from './icons.ts';

// The three kinds of work, as works.ts already defines them. A fourth
// vocabulary for the same three things would drift, so this set is the only
// one allowed here.
const VALID = new Set(['creative-web', 'erp', 'custom-build']);
const SLUG = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

const ids = new Set(works.map((w) => w.id));
const slugs = new Set();

for (const s of sectors) {
  // Slugs become URL segments via getStaticPaths. A stray capital or space
  // builds a route nobody can type.
  assert.ok(SLUG.test(s.slug), `bad slug: ${s.slug}`);
  assert.ok(!slugs.has(s.slug), `duplicate sector slug: ${s.slug}`);
  slugs.add(s.slug);

  assert.ok(s.name && s.name.trim(), `${s.slug}: name required`);
  assert.ok(s.qualifier && s.qualifier.trim(), `${s.slug}: qualifier required`);
  assert.ok(s.lede && s.lede.trim(), `${s.slug}: lede required`);

  // A name that is not in the set renders an empty box, which reads as a
  // spacing bug rather than as an error. Icon.astro throws on it too, but this
  // fails first and names the sector.
  assert.ok(icons[s.icon], `${s.slug}: icon not in icons.ts: ${s.icon}`);

  assert.ok(
    Array.isArray(s.offers) && s.offers.length > 0,
    `${s.slug}: at least one offer required`,
  );
  for (const o of s.offers) {
    assert.ok(o.title && o.title.trim(), `${s.slug}: offer title required`);
    assert.ok(
      o.body && o.body.trim(),
      `${s.slug}: offer body required for "${o.title}"`,
    );
    assert.ok(
      VALID.has(o.category),
      `${s.slug}: bad category ${o.category} on "${o.title}"`,
    );
    assert.ok(
      icons[o.icon],
      `${s.slug}: icon not in icons.ts: ${o.icon} on "${o.title}"`,
    );
  }

  // Proof is cited by id and read back off works.ts at build time so a client
  // name, year or stack is never retyped on a Services page. An id that stops
  // resolving would silently render a blank chip instead of throwing.
  assert.ok(Array.isArray(s.proof), `${s.slug}: proof must be an array`);
  for (const id of s.proof) {
    assert.ok(ids.has(id), `${s.slug}: proof id not in works.ts: ${id}`);
    // PRODUCT.md: "No client logos or press exist. Do not fabricate any."
    // works.ts carries six placeholder rows awaiting real projects; none of
    // them is evidence of anything and none may be cited as proof.
    assert.ok(
      !id.startsWith('placeholder-'),
      `${s.slug}: placeholder cited as proof: ${id}`,
    );
  }
}

const offers = sectors.reduce((n, s) => n + s.offers.length, 0);
const cited = new Set(sectors.flatMap((s) => s.proof));
const used = new Set([
  ...sectors.map((s) => s.icon),
  ...sectors.flatMap((s) => s.offers.map((o) => o.icon)),
]);
console.log(
  `ok: ${sectors.length} sectors, ${offers} offers, ${cited.size} works cited, ${used.size} of ${Object.keys(icons).length} icons used`,
);
