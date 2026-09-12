// Chapter-boundary curtain.
//
// Chapters sit in normal document flow (WorkCarousel.astro has no
// position: sticky and nothing is pinned), so triggering off a chapter's own
// section box is correct here — no stack-anchoring workaround needed.
//
// ScrollTriggers are attached to top-level animations only, never nested in a
// parent timeline — that is unsupported and silently misbehaves.
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { disposeChapter, createChapterPlanes } from './planes';
import type { WorkCarouselController } from './carousel';

gsap.registerPlugin(ScrollTrigger);

export const mountCurtain = (controllers: WorkCarouselController[]) => {
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  if (controllers.length < 2) return;

  const sheet = document.querySelector<HTMLElement>('[data-curtain-sheet]');
  if (!sheet) return;

  controllers.forEach((controller, i) => {
    if (i === 0) return;

    const prev = controllers[i - 1];

    gsap
      .timeline({
        scrollTrigger: {
          trigger: controller.root,
          start: 'top bottom',
          end: 'top top',
          scrub: true,
          invalidateOnRefresh: true,

          // Teardown hangs off onLeave/onLeaveBack, never onUpdate. A scrub
          // trigger has no onComplete: progress is scroll-bound, so there is
          // no natural end to hang it on. Disposing on update would tear the
          // outgoing chapter mid-wipe.
          onLeave: () => {
            disposeChapter(prev.root);
            createChapterPlanes(controller);
          },
          onLeaveBack: () => {
            disposeChapter(controller.root);
            createChapterPlanes(prev);
          },
          onEnter: () => createChapterPlanes(controller),
          onEnterBack: () => createChapterPlanes(prev),
        },
      })
      // The sheet sweeps up across the boundary and off the top, so one
      // chapter is replaced rather than cross-faded.
      .fromTo(
        sheet,
        { yPercent: 100 },
        { yPercent: 0, ease: 'none', duration: 0.5 },
      )
      .to(sheet, { yPercent: -100, ease: 'none', duration: 0.5 });
  });

  // dvh changes when the mobile URL bar collapses, which moves every
  // boundary. Refresh on resize, debounced — never on scroll.
  let timer = 0;
  window.addEventListener('resize', () => {
    window.clearTimeout(timer);
    timer = window.setTimeout(() => ScrollTrigger.refresh(), 200);
  });
};
