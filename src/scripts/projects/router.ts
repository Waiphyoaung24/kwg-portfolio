import { renderList } from './views/list';
import { renderNew } from './views/new';
import { renderProject } from './views/project';
import { renderTeam } from './views/team';

export function startRouter(root: HTMLElement) {
  const route = async () => {
    const hash = location.hash || '#/';
    const m = hash.match(/^#\/p\/(\d+)$/);
    if (m) return renderProject(root, Number(m[1]));
    if (hash === '#/new') return renderNew(root);
    if (hash === '#/team') return renderTeam(root);
    return renderList(root);
  };
  window.addEventListener('hashchange', route);
  route();
}
