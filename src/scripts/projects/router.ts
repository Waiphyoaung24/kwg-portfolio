import { renderList } from './views/list';
import { renderNew } from './views/new';
import { renderProject } from './views/project';
import { renderTeam } from './views/team';

export function startRouter(root: HTMLElement) {
  const route = async () => {
    try {
      const hash = location.hash || '#/';
      const m = hash.match(/^#\/p\/(\d+)$/);
      if (m) return await renderProject(root, Number(m[1]));
      if (hash === '#/new') return await renderNew(root);
      if (hash === '#/team') return await renderTeam(root);
      return await renderList(root);
    } catch (e: any) {
      root.innerHTML = `<p class="page__caption">Error: ${e?.message ?? e}</p>`;
    }
  };
  window.addEventListener('hashchange', route);
  route();
}
