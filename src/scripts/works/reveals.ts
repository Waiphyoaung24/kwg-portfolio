// Section entrances on /works, as stylized.cortiz.dev runs them: the title
// splits to characters that rise out of a line mask, spec rules draw in from
// the left, and [data-reveal] items fade up. Once each, when the section
// reaches 78% of the viewport. Nothing moves under reduced motion.
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { SplitText } from 'gsap/SplitText';

gsap.registerPlugin(ScrollTrigger, SplitText);

export const mountReveals = (sections: HTMLElement[]) => {
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  sections.forEach((section) => {
    const timeline = gsap.timeline({
      scrollTrigger: { trigger: section, start: 'top 78%', once: true },
    });

    const title = section.querySelector<HTMLElement>('[data-split]');
    if (title) {
      const split = new SplitText(title, {
        type: 'lines,chars',
        linesClass: 'live-line',
      });
      timeline.from(split.chars, {
        yPercent: 115,
        opacity: 0,
        duration: 0.5,
        ease: 'power3.out',
        stagger: 0.012,
      });
    }

    const rules = section.querySelectorAll('[data-rule]');
    if (rules.length) {
      timeline.from(
        rules,
        {
          scaleX: 0,
          transformOrigin: 'left center',
          duration: 0.55,
          ease: 'power3.out',
          stagger: 0.09,
        },
        0.3,
      );
    }

    const items = section.querySelectorAll('[data-reveal]');
    if (items.length) {
      timeline.from(
        items,
        {
          y: 14,
          opacity: 0,
          duration: 0.45,
          ease: 'power2.out',
          stagger: 0.07,
        },
        0.22,
      );
    }
  });
};
