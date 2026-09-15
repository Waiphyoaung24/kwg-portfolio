import assert from 'node:assert/strict';
import {
  nearestTargetFor,
  settleTarget,
  slotOffset,
  wrapIndex,
  wrapSpan,
} from './ring-math.ts';

assert.equal(wrapIndex(-1, 8), 7, 'wraps below zero');
assert.equal(wrapIndex(8, 8), 0, 'wraps past the end');
assert.equal(wrapIndex(11, 8), 3, 'wraps a spun position');
assert.equal(wrapIndex(3, 0), 0, 'survives an empty ring');

// The ring loops: the last card sits just left of the first.
assert.equal(slotOffset(7, 0, 8), -1, 'last card is left of the first');
assert.equal(slotOffset(0, 7, 8), 1, 'first card is right of the last');
assert.equal(
  slotOffset(1, 0.5, 8),
  0.5,
  'fractional positions stay fractional',
);
assert.equal(slotOffset(4, 0, 8), -4, 'the opposite card folds to one side');
assert.equal(
  slotOffset(2, 18, 8),
  0,
  'a position many turns round still lines up',
);

// A slow release snaps to the nearest card; a flick moves on, never back.
assert.equal(settleTarget(2.3, 0, 1), 2, 'slow release snaps to nearest');
assert.equal(settleTarget(2.3, 5, 1), 3, 'flick forward moves on');
assert.equal(
  settleTarget(2.3, -5, 1),
  2,
  'flick back lands on the card behind',
);
assert.equal(settleTarget(2, -5, 1), 1, 'flick back from rest moves one');
assert.equal(settleTarget(2.9, 5, 1), 3, 'flick forward never skips two');

// Jumping to a card takes the short way round.
assert.equal(nearestTargetFor(7, 0, 8), -1, 'last card is one step back');
assert.equal(
  nearestTargetFor(3, 9.2, 8),
  11,
  'target stays near a spun position',
);
assert.equal(
  wrapIndex(nearestTargetFor(3, 9.2, 8), 8),
  3,
  'and lands on the card asked for',
);

// A looping strip folds any offset back onto itself.
assert.equal(wrapSpan(-10, 100), 90, 'wraps a negative offset');
assert.equal(wrapSpan(250, 100), 50, 'wraps past the span');
assert.equal(wrapSpan(5, 0), 0, 'survives an empty strip');

console.log('ok: ring-math');
