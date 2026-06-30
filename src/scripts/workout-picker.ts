import type { Exercise } from './exercise-detail';

export type PickMode = 'full' | 'focus';

export interface PickOpts {
  mode: PickMode;
  equipment?: string;
  target?: string;
  count: number;
  rng?: () => number;
}

function shuffle<T>(arr: T[], rng: () => number): T[] {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

// Pick up to `count` exercises. Pure: same inputs + rng => same output.
export function pickWorkout(exercises: Exercise[], opts: PickOpts): Exercise[] {
  const { mode, equipment = '', target = '', count, rng = Math.random } = opts;
  const pool = equipment ? exercises.filter((e) => e.equipment === equipment) : exercises;

  if (mode === 'focus') {
    const filtered = target ? pool.filter((e) => e.target === target) : pool;
    return shuffle(filtered, rng).slice(0, count);
  }

  // full body: group by body part, then round-robin one random pick per part
  // until count is reached. Wraps through parts again but never repeats an exercise.
  const groups = new Map<string, Exercise[]>();
  for (const e of shuffle(pool, rng)) {
    const g = groups.get(e.body_part);
    if (g) g.push(e);
    else groups.set(e.body_part, [e]);
  }
  const parts = shuffle([...groups.keys()], rng);
  const picked: Exercise[] = [];
  let added = true;
  while (picked.length < count && added) {
    added = false;
    for (const p of parts) {
      if (picked.length >= count) break;
      const next = groups.get(p)!.shift();
      if (next) {
        picked.push(next);
        added = true;
      }
    }
  }
  return picked;
}
