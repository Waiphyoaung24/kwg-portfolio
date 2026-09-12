import assert from 'node:assert/strict';
import { clampIndex, canGo, indexAfterDrag } from './slides.ts';

// The rail does NOT wrap. With two slides a wrapping carousel reads as a
// flicker between the same two frames, and the arrows stop meaning anything.
assert.equal(clampIndex(-1, 4), 0, 'clamps below zero');
assert.equal(clampIndex(4, 4), 3, 'clamps above the last');
assert.equal(clampIndex(2, 4), 2, 'leaves an in-range index alone');
assert.equal(clampIndex(0, 0), 0, 'survives an empty carousel');

assert.equal(canGo(0, 2, -1), false, 'no previous at the first slide');
assert.equal(canGo(0, 2, 1), true, 'next exists at the first slide');
assert.equal(canGo(1, 2, 1), false, 'no next at the last slide');
assert.equal(canGo(0, 1, 1), false, 'a single slide goes nowhere');

// A drag shorter than the threshold snaps back rather than committing.
assert.equal(indexAfterDrag(1, 4, -60, 1000), 1, 'short drag does not commit');
assert.equal(indexAfterDrag(1, 4, -300, 1000), 2, 'drag left advances');
assert.equal(indexAfterDrag(1, 4, 300, 1000), 0, 'drag right retreats');

// One drag is one slide however far it travels: a flick must not skip work.
assert.equal(indexAfterDrag(0, 4, -3000, 1000), 1, 'a long drag still moves one');
assert.equal(indexAfterDrag(3, 4, -3000, 1000), 3, 'cannot drag past the last');
assert.equal(indexAfterDrag(0, 4, -300, 0), 0, 'zero width is a no-op, not NaN');

console.log('ok: slides');
