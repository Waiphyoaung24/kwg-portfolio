import { api } from '../api';
import { esc, chip } from '../format';

export async function renderList(root: HTMLElement) {
  const projects = await api.get('/projects');
  root.innerHTML = `
    <header class="pv__head">
      <h1 class="page__title">Projects</h1>
      <nav class="pv__nav">
        <a href="#/team">Team</a>
        <button id="new" type="button">+ New project</button>
      </nav>
    </header>
    <ul class="pv__list" role="list">
      ${projects.length ? projects.map((p: any) => `
        <li class="pcard pcard--${p.blocked_on}">
          <a class="pcard__link" href="#/p/${p.id}">
            <span class="pcard__name">${esc(p.client_name)}${p.warn ? ' <span class="pcard__warn" title="Work started before contract signed">⚠</span>' : ''}</span>
            <span class="pcard__stage">${esc(p.current_stage ?? 'Complete')}</span>
            <span class="pcard__chip">${chip(p.blocked_on)}${p.days_waiting ? ` · ${p.days_waiting}d` : ''}</span>
          </a>
        </li>`).join('') : `<li class="page__caption">No projects yet. Create your first one.</li>`}
    </ul>`;
  root.querySelector('#new')!.addEventListener('click', () => (location.hash = '#/new'));
}
