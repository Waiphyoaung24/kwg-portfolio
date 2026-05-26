import Lenis from 'lenis';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

// autoRaf is intentionally OFF: we drive lenis from gsap.ticker below so
// Lenis's smoothed scroll value, ScrollTrigger.update, and any
// scroll-linked GSAP animations all commit in the SAME rAF tick. Per the
// official Lenis README's GSAP integration recipe — without this, Lenis
// and GSAP each run their own rAFs and scroll animations sit ~1 frame
// behind the cursor (visible as jitter / drag).
export const lenis = new Lenis({
  autoRaf: false,
  lerp: 0.07,
});

lenis.on('scroll', ScrollTrigger.update);

gsap.ticker.add((time) => {
  // gsap.ticker time is in seconds; lenis.raf expects milliseconds.
  lenis.raf(time * 1000);
});

// Disable GSAP's built-in lag smoothing: when GSAP detects a slow frame
// it normally fast-forwards animations to "catch up" — but that would
// desync from Lenis's own scroll lerp and cause a hitch.
gsap.ticker.lagSmoothing(0);

export const scrollStop = () => {
  if (!lenis.isStopped) {
    const scrollBarWidth = window.innerWidth - document.body.offsetWidth;
    document.body.style.setProperty(
      '--scroll-bar-width',
      `${scrollBarWidth}px`,
    );
    document.body.style.paddingRight =
      document.body.style.getPropertyValue('--scroll-bar-width') ||
      scrollBarWidth + 'px';
  }

  document.body.style.overflowY = 'clip';
  lenis.stop();
};

export const scrollStart = () => {
  lenis.start();
  document.body.style.removeProperty('--scroll-bar-width');
  document.body.style.paddingRight = '';
  document.body.style.overflowY = '';
};
