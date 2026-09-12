// One chapter's carousel. Owns the slide index and nothing else: the plane
// layer (works/planes.ts) subscribes through onChange rather than reading the
// DOM itself, so WebGL can fail without taking navigation with it.
import { clampIndex, canGo, indexAfterDrag } from './slides';

type ChangeFn = (index: number, slide: HTMLElement) => void;

const DRAG_COMMIT = 8; // px before a pointer press counts as a drag, not a click

export class WorkCarouselController {
  readonly root: HTMLElement;
  readonly slides: HTMLElement[];
  private thumbs: HTMLElement[];
  private prev: HTMLButtonElement | null;
  private next: HTMLButtonElement | null;
  private status: HTMLElement | null;
  private hint: HTMLElement | null;
  private listeners: ChangeFn[] = [];
  private i = 0;
  private dragging = false;
  private startX = 0;

  constructor(root: HTMLElement) {
    this.root = root;
    this.slides = Array.from(root.querySelectorAll<HTMLElement>('[data-carousel-slide]'));
    this.thumbs = Array.from(root.querySelectorAll<HTMLElement>('[data-carousel-thumb]'));
    this.prev = root.querySelector('[data-carousel-prev]');
    this.next = root.querySelector('[data-carousel-next]');
    this.status = root.querySelector('[data-carousel-status]');
    this.hint = root.querySelector('[data-carousel-hint]');

    if (this.slides.length === 0) return;

    // The markup ships every slide visible so the page reads without JS.
    // Revealing the controls and collapsing the stack is this script's first
    // act, which means the controls never appear without something to drive.
    this.root.classList.add('is-live');
    root.querySelector('[data-carousel-arrows]')?.removeAttribute('hidden');
    root.querySelector('[data-carousel-thumbs]')?.removeAttribute('hidden');
    // A carousel of one has nothing to drag or page through.
    if (this.slides.length < 2) {
      root.querySelector('[data-carousel-arrows]')?.setAttribute('hidden', '');
      root.querySelector('[data-carousel-thumbs]')?.setAttribute('hidden', '');
    } else {
      this.hint?.removeAttribute('hidden');
    }

    this.bind();
    this.render(true);
  }

  get index() {
    return this.i;
  }

  onChange(fn: ChangeFn) {
    this.listeners.push(fn);
  }

  go(next: number) {
    const target = clampIndex(next, this.slides.length);
    if (target === this.i) return;
    this.i = target;
    this.render(false);
  }

  private bind() {
    this.prev?.addEventListener('click', () => this.go(this.i - 1));
    this.next?.addEventListener('click', () => this.go(this.i + 1));

    this.thumbs.forEach((thumb, i) => {
      thumb.addEventListener('click', () => this.go(i));
    });

    // Arrow keys page the carousel only while focus is inside it, so they
    // never steal the keys from the page.
    this.root.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowLeft') {
        e.preventDefault();
        this.go(this.i - 1);
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        this.go(this.i + 1);
      }
    });

    // Focus landing on an off-screen slide advances to it, rather than
    // leaving the user tabbing through content they cannot see.
    this.root.addEventListener('focusin', (e) => {
      const slide = (e.target as HTMLElement).closest<HTMLElement>('[data-carousel-slide]');
      if (!slide) return;
      const at = this.slides.indexOf(slide);
      if (at !== -1) this.go(at);
    });

    const stage = this.root.querySelector<HTMLElement>('.carousel__stage');
    if (!stage) return;

    stage.addEventListener('pointerdown', (e) => {
      if (e.pointerType === 'mouse' && e.button !== 0) return;
      this.dragging = true;
      this.startX = e.clientX;
      this.hint?.setAttribute('hidden', '');
    });

    stage.addEventListener('pointerup', (e) => {
      if (!this.dragging) return;
      this.dragging = false;
      const dx = e.clientX - this.startX;
      if (Math.abs(dx) < DRAG_COMMIT) return; // a click, not a drag
      this.go(indexAfterDrag(this.i, this.slides.length, dx, stage.clientWidth));
    });

    stage.addEventListener('pointercancel', () => {
      this.dragging = false;
    });
  }

  private render(initial: boolean) {
    this.slides.forEach((slide, i) => {
      const on = i === this.i;
      slide.classList.toggle('is-active', on);
      // inert keeps off-screen slides out of the tab order without hiding
      // them from the layout the plane layer measures against.
      slide.toggleAttribute('inert', !on);
    });

    this.thumbs.forEach((thumb, i) => {
      thumb.setAttribute('aria-current', String(i === this.i));
    });

    if (this.prev) this.prev.disabled = !canGo(this.i, this.slides.length, -1);
    if (this.next) this.next.disabled = !canGo(this.i, this.slides.length, 1);

    // Silent on first render: announcing "Project 1 of 4" the moment the page
    // loads is noise, not navigation.
    if (!initial && this.status) {
      this.status.textContent = `Project ${this.i + 1} of ${this.slides.length}`;
    }

    this.listeners.forEach((fn) => fn(this.i, this.slides[this.i]));
  }
}

export const mountCarousels = (): WorkCarouselController[] =>
  Array.from(document.querySelectorAll<HTMLElement>('[data-carousel]')).map(
    (root) => new WorkCarouselController(root),
  );
