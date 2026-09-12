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
import type { PlaneParams } from 'curtainsjs';
import { gsap } from 'gsap';
import { lenis } from '../scroll';
import type { WorkCarouselController } from './carousel';
import vertexShader from '../../shader/carousel.vert.glsl';
import fragmentShader from '../../shader/carousel.frag.glsl';

// window.__curtains is declared in src/types/curtains.d.ts.

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

// Velocity is per chapter, not global: Task 8 plants a second chapter's
// planes immediately, and without this a drag on one chapter would lean the
// other chapter's plane too, since they'd share one number.
type ChapterEntry = { planes: Plane[]; velocity: number };

const chapters = new Map<HTMLElement, ChapterEntry>();

export const disposeChapter = (root: HTMLElement) => {
  const chapter = chapters.get(root);
  if (!chapter) return;
  chapter.planes.forEach((plane) => plane.remove());
  chapters.delete(root);
  // Hand the element back to its <img>. Disposing without this leaves a blank
  // box where a poster should be.
  root
    .querySelectorAll<HTMLElement>('[data-carousel-plane]')
    .forEach((el) => el.classList.remove('is-planed'));
};

const createChapter = (controller: WorkCarouselController) => {
  const curtains = window.__curtains;
  const root = controller.root;
  // .gl, not truthiness — see mountPlanes's gate below for why a live
  // instance proves nothing on its own.
  if (!curtains?.gl || chapters.has(root)) return;

  const chapter: ChapterEntry = { planes: [], velocity: 0 };

  chapter.planes = Array.from(root.querySelectorAll<HTMLElement>('[data-carousel-plane]')).map(
    (el) => {
      const plane = new Plane(curtains, el, params);
      // Slides share one grid cell (WorkCarousel.astro's .is-live block) and
      // are hidden from a visitor by opacity/visibility, which WebGL does
      // not read — every plane in the chapter would otherwise draw into the
      // same rectangle at once. Visibility has to be driven explicitly from
      // the active slide.
      plane.visible = el.closest('[data-carousel-slide]') === controller.slides[controller.index];
      plane.onRender(() => {
        plane.uniforms.time.value = (plane.uniforms.time.value as number) + 1;
        plane.uniforms.velocity.value = chapter.velocity;
      });
      // Hide the <img> only once its plane is confirmed ready. Before this
      // fires — and if it never fires — the poster is what shows.
      plane.onReady(() => el.classList.add('is-planed'));
      return plane;
    },
  );

  chapters.set(root, chapter);
};

export const mountPlanes = (controllers: WorkCarouselController[]) => {
  // A truthy window.__curtains is not evidence of a working context: on a
  // renderer error curtainsjs leaves the instance itself alive but with
  // gl === null, and reports the error asynchronously (setTimeout(0)), so
  // by the time curtains:ready fires the object can still look live. Gating
  // on .gl catches that state directly, upstream of constructing any plane.
  if (!window.__curtains?.gl) return; // no WebGL: .no-curtains already showed the imgs
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  // Scroll velocity, normalised and decayed. Lenis reports px/frame; 60 is
  // about the fastest a real scroll goes, so it maps to roughly -1..1. Lenis
  // can report a non-finite value between frames (e.g. right after a resize);
  // an unguarded NaN would multiply through the 0.92 decay below forever and
  // permanently collapse the geometry. Scroll genuinely moves every chapter
  // on the page, so it broadcasts to all of them, not just the one in view.
  lenis.on('scroll', ({ velocity: v }: { velocity: number }) => {
    const scrollVelocity = gsap.utils.clamp(-1, 1, Number.isFinite(v) ? v / 60 : 0);
    chapters.forEach((chapter) => {
      chapter.velocity = scrollVelocity;
    });
  });

  gsap.ticker.add(() => {
    // Relax toward rest every frame, so the plane settles when nothing moves.
    // Once per chapter, not once per plane — a chapter's planes share one
    // velocity.
    chapters.forEach((chapter) => {
      chapter.velocity *= 0.92;
    });
  });

  controllers.forEach((controller, i) => {
    // Budget (D7): only the first chapter is planed at mount. The curtain's
    // boundary triggers create and dispose the rest as they come into view,
    // so the resident set never exceeds two chapters.
    if (i === 0) createChapter(controller);

    controller.onChange((index) => {
      const active = controller.slides[index];
      chapters.get(controller.root)?.planes.forEach((plane) => {
        // Re-derive visibility from the plane's own element rather than
        // trusting array position: not every slide has a plane (a slide with
        // no media has none), so a plane's index in this array does not line
        // up with the slide index.
        plane.visible = plane.htmlElement.closest('[data-carousel-slide]') === active;
        // A slide change re-measures: curtains positions a plane from its
        // element's box, and the outgoing slide's box is about to change.
        plane.updatePosition();
      });
    });

    // Drag speed, read directly off the pointer rather than through
    // carousel.ts: that controller owns which slide a drag commits to, not
    // how fast the pointer is moving right now, and duplicating its drag
    // state machine here just to get a speed number would be needless.
    controller.root.addEventListener('pointermove', (e) => {
      if (e.buttons !== 1) return;
      const chapter = chapters.get(controller.root);
      if (!chapter) return;
      const drag = gsap.utils.clamp(-1, 1, Number.isFinite(e.movementX) ? e.movementX / 60 : 0);
      // A touch pan fires this alongside a genuine vertical scroll — the
      // stage's touch-action: pan-y lets both happen at once — with
      // movementX near zero while the scroll-driven value carries the real
      // motion. Overwriting unconditionally would flatten the bulge for as
      // long as a finger rests on the carousel, so keep whichever signal is
      // actually larger instead of trusting the most recent write.
      chapter.velocity = Math.abs(drag) > Math.abs(chapter.velocity) ? drag : chapter.velocity;
    });
  });
};

export const createChapterPlanes = createChapter;
