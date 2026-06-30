import { readFile, writeFile, mkdir } from 'node:fs/promises';
import assert from 'node:assert/strict';

const src = process.argv[2];
assert(src, 'usage: node build-fitness-data.mjs <path-to-exercises.json>');

const raw = JSON.parse(await readFile(src, 'utf8'));
assert(Array.isArray(raw), 'expected an array of exercises');

const out = raw.map((e) => ({
  id: e.id,
  name: e.name,
  body_part: e.body_part,
  equipment: e.equipment,
  target: e.target,
  secondary_muscles: e.secondary_muscles ?? [],
  image: e.image,
  gif_url: e.gif_url,
  steps: e.instruction_steps?.en ?? [],
}));

// Self-check: this is the runnable check for this task.
assert(out.length > 1300, `expected >1300 exercises, got ${out.length}`);
for (const e of out) {
  assert(e.name, `missing name for id ${e.id}`);
  assert(e.image, `missing image for ${e.name}`);
  assert(e.gif_url, `missing gif_url for ${e.name}`);
}

const destDir = new URL('../data/', import.meta.url);
await mkdir(destDir, { recursive: true });
await writeFile(new URL('fitness-exercises.json', destDir), JSON.stringify(out));
console.log(`ok: wrote ${out.length} exercises to src/data/fitness-exercises.json`);
