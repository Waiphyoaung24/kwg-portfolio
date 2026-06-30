import assert from 'node:assert/strict';
import { pickWorkout } from './workout-picker.ts';

// Deterministic PRNG (mulberry32) so picks are reproducible across runs.
function rng32(seed) {
  return () => {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const ex = (id, body_part, equipment, target) => ({
  id,
  name: 'ex' + id,
  body_part,
  equipment,
  target,
  secondary_muscles: [],
  image: '',
  gif_url: '',
  steps: [],
});

const data = [
  ex('1', 'chest', 'dumbbell', 'pectorals'),
  ex('2', 'chest', 'dumbbell', 'pectorals'),
  ex('3', 'back', 'dumbbell', 'lats'),
  ex('4', 'legs', 'dumbbell', 'quads'),
  ex('5', 'legs', 'barbell', 'quads'),
  ex('6', 'waist', 'dumbbell', 'abs'),
];

// focus: filters to target, respects count, never exceeds available
const focus = pickWorkout(data, { mode: 'focus', target: 'quads', count: 5, rng: rng32(1) });
assert.equal(focus.length, 2, 'only 2 quads exercises exist');
assert.ok(focus.every((e) => e.target === 'quads'), 'all focus picks match target');

// focus + equipment narrows the pool
const focusEq = pickWorkout(data, {
  mode: 'focus', target: 'quads', equipment: 'dumbbell', count: 5, rng: rng32(1),
});
assert.equal(focusEq.length, 1, 'only 1 dumbbell quads exercise');

// full body: spans distinct body parts, no dupes, respects count
const full = pickWorkout(data, { mode: 'full', count: 4, rng: rng32(2) });
assert.equal(full.length, 4, 'returns count');
assert.equal(new Set(full.map((e) => e.body_part)).size, 4, 'four distinct body parts');
assert.equal(new Set(full.map((e) => e.id)).size, 4, 'no repeated exercise');

// full body wraps when count > distinct parts, still no repeats, caps at pool size
const wrap = pickWorkout(data, { mode: 'full', equipment: 'dumbbell', count: 10, rng: rng32(3) });
assert.equal(wrap.length, 5, 'capped at the 5 available dumbbell exercises');
assert.equal(new Set(wrap.map((e) => e.id)).size, 5, 'no repeats when wrapping parts');

console.log('ok: pickWorkout focus + full-body behavior');
