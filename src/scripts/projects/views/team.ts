import { api } from '../api';
import { esc } from '../format';

export async function renderTeam(root: HTMLElement) {
  const members = await api.get('/team');
  root.innerHTML = `
    <a class="pv__back" href="#/">← Projects</a>
    <h1 class="page__title">Team</h1>
    <ul class="pv__list" role="list">
      ${members.map((m: any) => `<li class="pcard"><span class="pcard__name">${esc(m.name)}</span><span class="pcard__stage">${esc(m.role)}</span><span class="pcard__chip">${esc(m.contact)}</span></li>`).join('') || '<li class="page__caption">No team members yet.</li>'}
    </ul>
    <form id="tm" class="np">
      <input class="entry__label" name="name" placeholder="Name" required />
      <input class="entry__label" name="role" placeholder="Role (dev/designer/…)" />
      <input class="entry__label" name="contact" placeholder="Contact" />
      <button class="entry__add" type="submit">Add member</button>
    </form>`;
  root.querySelector('#tm')!.addEventListener('submit', async (e) => {
    e.preventDefault();
    const f = e.target as HTMLFormElement;
    await api.post('/team', {
      name: (f.elements.namedItem('name') as HTMLInputElement).value.trim(),
      role: (f.elements.namedItem('role') as HTMLInputElement).value.trim(),
      contact: (f.elements.namedItem('contact') as HTMLInputElement).value.trim(),
    });
    renderTeam(root);
  });
}
