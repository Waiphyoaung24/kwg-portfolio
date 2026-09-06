// Image-to-content transition, after Codrops' "Infinite Scroll Gallery and
// Flip Transitions" by Surya Aditya (src/Transition.js in
// github.com/surya-aditya/codrops-infinite-scroll-and-content-transition),
// minus the infinite slider and per-slide reveal. The clicked gallery image
// Flip-morphs into a fixed full-height preview while a canvas backdrop fades
// over the page; the matching content group then reveals its copy line by
// line, character by character. Close reverses; a close mid-open rewinds.
//
// Differences from the original: the backdrop replaces the original's
// "fade the other slides" step (their images carry a pending ScrollTrigger
// entrance that a fade would clobber), Lenis is frozen while open, focus
// moves to Back and returns to the card, and reduced motion skips the
// morph and the split.
//
// Seams: the hand-off between thumbnail and preview happens twice, and both
// must be invisible. The preview image carries no inner scale (the original
// zooms 1.2 → 1, which snaps at the swap unless the thumbnail is also scaled),
// the card is refocused without scrolling, and the sticky header fades with
// the backdrop while the overlay stacks beneath it, so nothing pops in front
// of the image on the last frame.
import { gsap } from 'gsap';
import { Flip } from 'gsap/Flip';
import { SplitText } from 'gsap/SplitText';
import { scrollStart, scrollStop } from './scroll';

gsap.registerPlugin(Flip, SplitText);

type State = 'closed' | 'opening' | 'open' | 'closing';

interface Options {
  /** the gallery cards; each must contain `img` and an index-matching group */
  items: HTMLElement[];
  /** selector for the image inside a card — the Flip source */
  img: string;
  /** the fixed overlay */
  overlay: HTMLElement;
}

const must = <T>(el: T | null, what: string): T => {
  if (!el) throw new Error(`work-detail: missing ${what}`);
  return el;
};

export class WorkTransition {
  private imgSel: string;
  private overlay: HTMLElement;
  private backdrop: HTMLElement;
  private preview: HTMLElement;
  private previewImg: HTMLImageElement;
  private groups: HTMLElement[];
  private back: HTMLElement;
  private header = document.querySelector<HTMLElement>('body > header');
  private active: {
    item: HTMLElement;
    img: HTMLImageElement;
    group: HTMLElement;
  } | null = null;
  private tl: gsap.core.Timeline | null = null;
  private split: SplitText | null = null;
  private reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  state: State = 'closed';

  constructor({ items, img, overlay }: Options) {
    this.imgSel = img;
    this.overlay = overlay;
    this.backdrop = must(
      overlay.querySelector<HTMLElement>('.work-detail__backdrop'),
      'backdrop',
    );
    this.preview = must(
      overlay.querySelector<HTMLElement>('.work-detail__preview'),
      'preview',
    );
    this.previewImg = must(this.preview.querySelector('img'), 'preview img');
    this.groups = gsap.utils.toArray<HTMLElement>(
      '.work-detail__group',
      overlay,
    );
    this.back = must(
      overlay.querySelector<HTMLElement>('.work-detail__back'),
      'back',
    );

    // The preview's Flip identity; the clicked image borrows it while open.
    this.preview.dataset.flipId = 'preview';

    items.forEach((item, index) => {
      item.setAttribute('tabindex', '0');
      item.setAttribute('role', 'button');
      item.addEventListener('click', () => this.open(item, index));
      item.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          this.open(item, index);
        }
      });
    });

    this.back.addEventListener('click', () => this.close());
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') this.close();
    });
  }

  /** Morph the clicked image into the preview and reveal its copy. */
  async open(item: HTMLElement, index: number) {
    if (this.state !== 'closed') return;
    this.state = 'opening';

    const img = must(
      item.querySelector<HTMLImageElement>(this.imgSel),
      'image',
    );
    const group = must(this.groups[index] ?? null, `group ${index}`);
    this.active = { item, img, group };

    this.previewImg.src = img.src;
    this.previewImg.alt = img.alt;
    this.groups.forEach((g) => g.classList.toggle('is-active', g === group));
    // Undecoded, the preview paints blank for the first frames of the morph.
    try {
      await this.previewImg.decode();
    } catch {
      // Rejects if the src is swapped mid-flight; the transition still runs.
    }
    // A close() landing while the preview decoded has already reset us.
    if (this.state !== 'opening') return;

    // Capture the thumbnail's bounds before anything moves.
    img.dataset.flipId = 'preview';
    const state = Flip.getState(img);

    scrollStop();
    gsap.set(this.overlay, { display: 'block' });
    gsap.killTweensOf(img);
    gsap.set(img, { autoAlpha: 0 });

    const pills = group.querySelectorAll('.pill-btn');
    const copy = group.querySelectorAll(
      '.work-detail__eyebrow, .work-detail__title, .work-detail__body',
    );

    const tl = gsap.timeline({
      onComplete: () => {
        this.state = 'open';
        this.back.focus();
      },
      // Fires when a cancelled open finishes rewinding.
      onReverseComplete: () => this.reset(),
    });
    this.tl = tl;

    tl.fromTo(
      this.backdrop,
      { autoAlpha: 0 },
      { autoAlpha: 1, duration: 0.5, ease: 'power2.out' },
      0,
    );
    if (this.header) {
      tl.to(
        this.header,
        { autoAlpha: 0, duration: 0.5, ease: 'power2.out' },
        0,
      );
    }

    if (this.reduce) {
      tl.fromTo(
        [this.preview, this.back, group],
        { autoAlpha: 0 },
        { autoAlpha: 1, duration: 0.3 },
        0.1,
      );
      return;
    }

    tl.add(
      Flip.from(state, {
        targets: this.preview,
        duration: 1.2,
        ease: 'power4.inOut',
        absolute: true,
      }),
      0,
    ).fromTo(
      [this.back, ...pills],
      { autoAlpha: 0 },
      { autoAlpha: 1, duration: 0.6, ease: 'power2.out' },
      1,
    );

    this.split = new SplitText(copy, {
      type: 'lines,chars',
      charsClass: 'char',
    });
    this.split.lines.forEach((line, i) => {
      tl.fromTo(
        line.querySelectorAll('.char'),
        { autoAlpha: 0 },
        { autoAlpha: 1, duration: 1, ease: 'power3.out', stagger: 0.01 },
        // Preview delay + line index * stagger delay.
        0.8 + i * 0.06,
      );
    });
  }

  /** Morph the preview back into its card. */
  close() {
    if (this.state === 'opening') {
      this.state = 'closing';
      // Still waiting on the decode, so there is no timeline to rewind.
      if (!this.tl) {
        this.reset();
        return;
      }
      this.tl.reverse();
      return;
    }
    if (this.state !== 'open' || !this.active) return;
    this.state = 'closing';

    const { img, group } = this.active;
    const pills = group.querySelectorAll('.pill-btn');

    const tl = gsap.timeline({ onComplete: () => this.reset() });
    this.tl = tl;

    if (this.reduce) {
      tl.to([this.backdrop, this.preview, this.back, group], {
        autoAlpha: 0,
        duration: 0.3,
      });
      if (this.header) tl.to(this.header, { autoAlpha: 1, duration: 0.3 }, 0);
      return;
    }

    tl.to(
      this.split?.lines ?? [],
      { autoAlpha: 0, duration: 0.4, stagger: 0.04, ease: 'power1.out' },
      0,
    )
      .to([this.back, ...pills], { autoAlpha: 0, duration: 0.3 }, 0)
      .add(
        Flip.fit(this.preview, img, {
          duration: 1,
          ease: 'power3.inOut',
          absolute: true,
        }) as gsap.core.Tween,
        0,
      )
      .to(
        this.backdrop,
        { autoAlpha: 0, duration: 0.5, ease: 'power2.out' },
        0.5,
      );
    if (this.header) {
      tl.to(
        this.header,
        { autoAlpha: 1, duration: 0.5, ease: 'power2.out' },
        0.5,
      );
    }
  }

  /** Restore the DOM and hand scrolling back. */
  private reset() {
    if (!this.active) return;
    const { item, img, group } = this.active;

    // The thumbnail only carries the Flip id while its card is expanded.
    delete img.dataset.flipId;

    this.split?.revert();
    this.split = null;

    gsap.set(this.overlay, { display: 'none' });
    gsap.set(
      [
        this.preview,
        this.backdrop,
        this.back,
        img,
        group,
        ...group.querySelectorAll('.pill-btn'),
      ],
      { clearProps: 'all' },
    );
    // Only the two props we touched; the header is not ours.
    if (this.header) {
      gsap.set(this.header, { clearProps: 'opacity,visibility' });
    }

    scrollStart();
    this.active = null;
    this.tl = null;
    this.state = 'closed';
    // The card is where the visitor already was; a scroll here reads as a jump.
    item.focus({ preventScroll: true });
  }
}
