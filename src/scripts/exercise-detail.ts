export type Exercise = {
  id: string;
  name: string;
  body_part: string;
  equipment: string;
  target: string;
  secondary_muscles: string[];
  image: string;
  gif_url: string;
  steps: string[];
};

export const CDN = 'https://cdn.jsdelivr.net/gh/hasaneyldrm/exercises-dataset@92e2704';

// Wire the shared <dialog id="detail"> to a grid of .card elements.
export function initDetail(grid: HTMLElement, exercises: Exercise[]) {
  const byId = Object.fromEntries(exercises.map((e) => [e.id, e]));
  const dlg = document.getElementById('detail') as HTMLDialogElement;
  const gif = dlg.querySelector('.detail__gif') as HTMLImageElement;
  const name = dlg.querySelector('.detail__name')!;
  const meta = dlg.querySelector('.detail__meta')!;
  const secondary = dlg.querySelector('.detail__secondary')!;
  const steps = dlg.querySelector('.detail__steps')!;
  const toggle = dlg.querySelector('.detail__toggle')!;

  let posterSrc = '';
  let gifSrc = '';
  function renderMedia(playing: boolean) {
    gif.src = playing ? gifSrc : posterSrc; // GIF only requested when playing
    toggle.textContent = playing ? 'Pause' : 'Play';
    toggle.setAttribute('aria-pressed', String(playing));
  }
  toggle.addEventListener('click', () =>
    renderMedia(toggle.getAttribute('aria-pressed') !== 'true'),
  );

  grid.addEventListener('click', (ev) => {
    const card = (ev.target as HTMLElement).closest('.card') as HTMLElement | null;
    if (!card) return;
    const e = byId[card.dataset.id!];
    name.textContent = e.name;
    meta.textContent = [e.target, e.equipment, e.body_part].filter(Boolean).join(' · ');
    secondary.textContent = e.secondary_muscles?.length
      ? 'Also targets: ' + e.secondary_muscles.join(', ')
      : '';
    steps.replaceChildren();
    for (const s of e.steps || []) {
      const li = document.createElement('li');
      li.textContent = s;
      steps.appendChild(li);
    }
    posterSrc = `${CDN}/${e.image}`;
    gifSrc = `${CDN}/${e.gif_url}`;
    gif.alt = e.name;
    // Honor reduced-motion: start on the static poster; otherwise autoplay the GIF.
    renderMedia(!window.matchMedia('(prefers-reduced-motion: reduce)').matches);
    dlg.showModal();
  });

  dlg.querySelector('.detail__close')!.addEventListener('click', () => dlg.close());
  dlg.addEventListener('click', (ev) => {
    if (ev.target === dlg) dlg.close();
  });
  dlg.addEventListener('close', () => {
    gif.removeAttribute('src');
  });
}
