// Curtains planes for the /works carousels.
//
// Budget (spec D7): textures cap at 1600x900 and planes exist only for the
// chapter in view plus one lookahead. Eight simultaneous 2048x1152 RGBA
// textures is ~75MB of VRAM, which is not safe on mid-range mobile.
//
// Films are never textured. A video texture re-uploads every frame and costs
// more than the effect returns; the plane carries the poster and the film
// plays in a DOM <video> above the canvas.
import { Plane } from 'curtainsjs';
import type { Curtains, PlaneParams } from 'curtainsjs';
import { gsap } from 'gsap';
import { lenis } from '../scroll';
import type { WorkCarouselController } from './carousel';
import vertexShader from '../../shader/carousel.vert.glsl';
import fragmentShader from '../../shader/carousel.frag.glsl';

// Declared here rather than in src/env.d.ts: that file's ambient `.glsl` and
// `.sql?raw` module declarations are shorthand (bodyless/global) and only
// resolve project-wide while the file has no top-level import of its own.
// Adding `import type { Curtains }` there to type this global turns the
// whole file into a module, which silently un-resolves those declarations
// everywhere else. This file is already a module, so the augmentation is
// safe here.
declare global {
  interface Window {
    __curtains: Curtains | null;
  }
}

const params: PlaneParams = {
  vertexShader,
  fragmentShader,
  // The bulge needs vertices to bend. 40x40 is enough for a smooth curve at
  // this size; Canvas.astro's background plane runs 100x100 because it is
  // full-screen.
  widthSegments: 40,
  heightSegments: 40,
  transparent: true,
  uniforms: {
    time: { name: 'uTime', type: '1f', value: 0 },
    velocity: { name: 'uVelocity', type: '1f', value: 0 },
  },
};

const chapters = new Map<HTMLElement, Plane[]>();
let velocity = 0;

export const disposeChapter = (root: HTMLElement) => {
  const planes = chapters.get(root);
  if (!planes) return;
  planes.forEach((plane) => plane.remove());
  chapters.delete(root);
  // Hand the element back to its <img>. Disposing without this leaves a blank
  // box where a poster should be.
  root
    .querySelectorAll<HTMLElement>('[data-carousel-plane]')
    .forEach((el) => el.classList.remove('is-planed'));
};

const createChapter = (root: HTMLElement) => {
  const curtains = window.__curtains;
  if (!curtains || chapters.has(root)) return;

  const planes = Array.from(root.querySelectorAll<HTMLElement>('[data-carousel-plane]')).map(
    (el) => {
      const plane = new Plane(curtains, el, params);
      plane.onRender(() => {
        plane.uniforms.time.value = (plane.uniforms.time.value as number) + 1;
        plane.uniforms.velocity.value = velocity;
      });
      // Hide the <img> only once its plane is confirmed ready. Before this
      // fires — and if it never fires — the poster is what shows.
      plane.onReady(() => el.classList.add('is-planed'));
      return plane;
    },
  );

  chapters.set(root, planes);
};

export const mountPlanes = (controllers: WorkCarouselController[]) => {
  if (!window.__curtains) return; // no WebGL: .no-curtains already showed the imgs
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  // Scroll velocity, normalised and decayed. Lenis reports px/frame; 60 is
  // about the fastest a real scroll goes, so it maps to roughly -1..1.
  lenis.on('scroll', ({ velocity: v }: { velocity: number }) => {
    velocity = gsap.utils.clamp(-1, 1, v / 60);
  });

  gsap.ticker.add(() => {
    // Relax toward rest every frame, so the plane settles when nothing moves.
    velocity *= 0.92;
  });

  controllers.forEach((controller, i) => {
    // Budget (D7): only the first chapter is planed at mount. The curtain's
    // boundary triggers create and dispose the rest as they come into view,
    // so the resident set never exceeds two chapters.
    if (i === 0) createChapter(controller.root);

    controller.onChange(() => {
      // A slide change re-measures: curtains positions a plane from its
      // element's box, and the outgoing slide's box is about to change.
      chapters.get(controller.root)?.forEach((plane) => plane.updatePosition());
    });
  });
};

export const createChapterPlanes = createChapter;
