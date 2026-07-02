import { api } from './api';
import { startRouter } from './router';

const app = document.getElementById('app')!;

function loginScreen() {
  app.innerHTML = `
    <form class="gate__form" id="login">
      <p class="gate__eyebrow">KWG</p>
      <h1 class="gate__title">Projects</h1>
      <label class="gate__label" for="pw">Password</label>
      <input class="gate__input" id="pw" type="password" autocomplete="current-password" />
      <p class="gate__error" id="err" role="alert"></p>
      <button class="gate__submit" type="submit">Enter</button>
    </form>`;
  app.querySelector('#login')!.addEventListener('submit', async (e) => {
    e.preventDefault();
    const pw = (app.querySelector('#pw') as HTMLInputElement).value;
    const res = await fetch('/api/login', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ password: pw }) });
    if (res.ok) boot();
    else app.querySelector('#err')!.textContent = 'Incorrect password.';
  });
}

export async function boot() {
  try {
    await api.get('/projects'); // 401 → show login
    startRouter(app);
  } catch (e: any) {
    if (e?.unauth) loginScreen();
    else app.innerHTML = `<p class="page__caption">Error: ${e?.message ?? e}</p>`;
  }
}

boot();
