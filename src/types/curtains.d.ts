// Lives in its own module file, not src/env.d.ts, on purpose: this needs a
// top-level import to type Curtains, and a top-level import turns a .d.ts
// into a module — which would silently un-resolve env.d.ts's shorthand
// `declare module '*.glsl'` project-wide (verified: adding an import there
// breaks every .glsl import in the codebase). Keeping env.d.ts a script and
// this augmentation in its own module file avoids the coupling entirely.
import type { Curtains } from 'curtainsjs';

declare global {
  interface Window {
    __curtains: Curtains | null;
  }
}
