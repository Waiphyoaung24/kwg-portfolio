// Slide index maths for the /works carousels. Pure: no DOM, no GSAP, no
// curtains. Everything that moves reads its target from here.

/**
 * Hold an index inside the carousel. The rail deliberately does not wrap —
 * two of the three chapters carry only two projects (spec D9), and a
 * wrapping carousel of two reads as a flicker rather than as navigation.
 */
export const clampIndex = (index: number, count: number): number =>
  count <= 0 ? 0 : Math.min(Math.max(index, 0), count - 1);

/** Whether an arrow in `dir` would actually move. Drives the disabled state. */
export const canGo = (index: number, count: number, dir: -1 | 1): boolean =>
  clampIndex(index + dir, count) !== index;

/**
 * Where a pointer drag lands. `dx` is total travel in px (positive = right),
 * `width` one slide's width. A drag shorter than `threshold` of a slide snaps
 * back; a longer one moves exactly one slide however far it travelled, so a
 * flick cannot skip past a project.
 */
export const indexAfterDrag = (
  index: number,
  count: number,
  dx: number,
  width: number,
  threshold = 0.2,
): number => {
  if (width <= 0) return index;
  const moved = -dx / width;
  const step = Math.abs(moved) < threshold ? 0 : Math.sign(moved);
  return clampIndex(index + step, count);
};
