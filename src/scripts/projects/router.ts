import { renderList } from './views/list';

// ponytail: list-only for now; #/new, #/p/:id, #/team branches are wired in the next
// frontend task as those views land. Unknown hashes fall through to the list.
export function startRouter(root: HTMLElement) {
  const route = () => renderList(root);
  window.addEventListener('hashchange', route);
  route();
}
