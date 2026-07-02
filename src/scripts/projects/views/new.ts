import { api } from '../api';
import { esc } from '../format';

export async function renderNew(root: HTMLElement) {
  const types = await api.get('/types');
  root.innerHTML = `
    <a class="pv__back" href="#/">← Projects</a>
    <h1 class="page__title">New project</h1>
    <form id="np" class="np">
      <label class="gate__label">Client name<input class="entry__label" name="client_name" required /></label>
      <label class="gate__label">Project type
        <select class="filters__select" name="project_type_id" required>
          ${types.map((t: any) => `<option value="${t.id}">${esc(t.name)}</option>`).join('')}
        </select>
      </label>
      <button class="entry__add" type="submit">Create</button>
      <p class="gate__error" id="err" role="alert"></p>
    </form>`;
  root.querySelector('#np')!.addEventListener('submit', async (e) => {
    e.preventDefault();
    const f = e.target as HTMLFormElement;
    try {
      const { id } = await api.post('/projects', {
        client_name: (f.elements.namedItem('client_name') as HTMLInputElement).value.trim(),
        project_type_id: Number((f.elements.namedItem('project_type_id') as HTMLSelectElement).value),
      });
      location.hash = `#/p/${id}`;
    } catch (err: any) {
      root.querySelector('#err')!.textContent = err?.message ?? 'Failed';
    }
  });
}
