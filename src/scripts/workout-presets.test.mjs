import assert from 'node:assert/strict';
import { PRESETS } from './workout-presets.ts';
import exercises from '../data/fitness-exercises.json' with { type: 'json' };

const ids = new Set(exercises.map((e) => e.id));

assert.ok(PRESETS.length >= 3, 'expected at least 3 presets');
for (const p of PRESETS) {
  assert.ok(p.name && p.name.trim(), 'preset must have a name');
  assert.ok(Array.isArray(p.ids) && p.ids.length > 0, `${p.name} must have ids`);
  for (const id of p.ids) {
    assert.ok(ids.has(id), `${p.name}: id ${id} not found in dataset`);
  }
}

// Spot-check the three routines are present and the right size.
const byName = Object.fromEntries(PRESETS.map((p) => [p.name, p.ids.length]));
assert.equal(byName['Upper Body A'], 6, 'Upper Body A has 6 exercises');
assert.equal(byName['Lower Body A'], 5, 'Lower Body A has 5 exercises');
assert.equal(byName['Upper Body B'], 8, 'Upper Body B has 8 exercises');

console.log('ok: all preset ids resolve in the dataset');
