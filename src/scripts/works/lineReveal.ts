// Heading reveal: split to lines, mask each, translate them up on a stagger.
// Mechanism from stylized.cortiz.dev (spec §7.3), which wraps each line in an
// overflow-hidden box with a little bottom padding so descenders are not
// clipped by the mask.
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { SplitText } from 'gsap/SplitText';

gsap.registerPlugin(ScrollTrigger, SplitText);

export const mountLineReveals = () => {
  // Reduced motion keeps the text exactly as the server rendered it: no
  // split, no mask, no trigger. Splitting and then not animating would still
  // rewrite the DOM for a reader who asked for none of it.
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  const targets = gsap.utils.toArray<HTMLElement>('[data-line-reveal]');

  targets.forEach((el) => {
    const split = new SplitText(el, {
      type: 'lines',
      linesClass: 'reveal-line',
      // Each line gets its own mask element, which is what we translate
      // against. Without this the lines slide over one another.
      mask: 'lines',
    });

    gsap.from(split.lines, {
      yPercent: 110,
      duration: 0.9,
      ease: 'expo.out',
      stagger: 0.08,
      scrollTrigger: {
        trigger: el,
        start: 'top 85%',
        once: true,
      },
    });
  });
};
