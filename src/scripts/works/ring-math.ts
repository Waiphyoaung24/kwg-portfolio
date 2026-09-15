// Index maths for the /works ring. Pure: no DOM, no three.
//
// `position` is the fractional index of the card facing the camera. It grows
// without bound as the ring spins; every card's place is folded back into the
// ring from it, which is what lets the ring loop without a seam.

/** Any integer, wrapped into 0..count-1. */
export const wrapIndex = (i: number, count: number): number =>
  count <= 0 ? 0 : ((Math.round(i) % count) + count) % count;

/**
 * Signed slot offset of card `i` from `position`, folded into
 * [-count/2, count/2). 0 faces the camera, +1 is the next card to the right.
 */
export const slotOffset = (
  i: number,
  position: number,
  count: number,
): number => {
  if (count <= 0) return 0;
  const d = (((i - position) % count) + count) % count;
  return d >= count / 2 ? d - count : d;
};

/**
 * Where a released drag settles. A slow release lands on the nearest card; a
 * flick faster than `flick` moves one card on in its direction, measured from
 * where the drag already is, so a flick never lands behind the release.
 */
export const settleTarget = (
  position: number,
  velocity: number,
  flick: number,
): number => {
  if (Math.abs(velocity) <= flick) return Math.round(position);
  return velocity > 0 ? Math.floor(position) + 1 : Math.ceil(position) - 1;
};

/** The unbounded target that brings card `index` to the front the short way round. */
export const nearestTargetFor = (
  index: number,
  position: number,
  count: number,
): number => {
  const from = Math.round(position);
  return from + slotOffset(index, from, count);
};

/** Any offset, wrapped into 0..span. For strips that loop. */
export const wrapSpan = (x: number, span: number): number =>
  span <= 0 ? 0 : ((x % span) + span) % span;
