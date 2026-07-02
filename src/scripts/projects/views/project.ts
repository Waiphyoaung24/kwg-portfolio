import { api } from '../api';
import { esc, chip } from '../format';

const STATUSES = ['not_started', 'in_progress', 'waiting_on_client', 'blocked_internal', 'done', 'skipped'];

export async function renderProject(root: HTMLElement, id: number) {
  const data = await api.get(`/projects/${id}`);
  const { project, stages, documents, activity, rollup } = data;

  root.innerHTML = `
    <a class="pv__back" href="#/">← Projects</a>
    <h1 class="page__title">${esc(project.client_name)}</h1>
    <p class="page__caption">${chip(rollup.blocked_on)}${rollup.warn ? ' · ⚠ work started before contract signed' : ''}</p>
    <ul class="stages" role="list">
      ${stages.map((s: any) => stageRow(s, documents.filter((d: any) => d.project_stage_id === s.id))).join('')}
    </ul>
    <h2 class="pv__subhead">Activity</h2>
    <ul class="activity" role="list">
      ${activity.map((a: any) => `<li><span>${esc(a.action)}</span><time>${new Date(a.timestamp).toLocaleDateString()}</time></li>`).join('') || '<li class="page__caption">No activity yet.</li>'}
    </ul>`;

  root.querySelectorAll<HTMLSelectElement>('.stage__status').forEach((sel) => {
    sel.addEventListener('change', () => onStatus(id, Number(sel.dataset.stage), sel.value, root));
  });
  root.querySelectorAll<HTMLFormElement>('.docform').forEach((f) => {
    f.addEventListener('submit', (e) => onDoc(e, id, root));
  });
}

function stageRow(s: any, docs: any[]) {
  const req = (s.required_documents ?? []) as string[];
  return `
    <li class="stage stage--${s.owner_type} stage--${s.status}">
      <div class="stage__head">
        <span class="stage__name">${s.ord}. ${esc(s.name)}</span>
        <span class="stage__owner">${s.owner_type}</span>
        <select class="stage__status" data-stage="${s.id}">
          ${STATUSES.map((st) => `<option value="${st}" ${st === s.status ? 'selected' : ''}>${st.replace(/_/g, ' ')}</option>`).join('')}
        </select>
      </div>
      ${s.blocked_reason ? `<p class="stage__blocked">⛔ ${esc(s.blocked_reason)}</p>` : ''}
      ${req.length ? `<p class="stage__req">Expected: ${req.map(esc).join(', ')}</p>` : ''}
      ${docs.length ? `<ul class="stage__docs">${docs.map((d: any) => `<li>${esc(d.filename)}${d.version_number ? ' r' + d.version_number : ''} <em>${esc(d.doc_type)}</em></li>`).join('')}</ul>` : ''}
      <form class="docform" data-stage="${s.id}">
        <input name="filename" placeholder="Document name" class="entry__label" />
        <select name="doc_type" class="filters__select">
          ${['proposal', 'brs', 'quotation', 'contract', 'wireframe', 'other'].map((t) => `<option>${t}</option>`).join('')}
        </select>
        <input name="version_number" type="number" min="1" placeholder="rev" class="entry__amount" />
        <button class="row__del" type="submit" title="Add document record">+</button>
      </form>
    </li>`;
}

async function onStatus(projectId: number, stageId: number, status: string, root: HTMLElement) {
  const body: any = { status };
  if (status === 'waiting_on_client' || status === 'blocked_internal') {
    const reason = prompt('Reason for blocking?'); // ponytail: native prompt; replace with inline field if it grates.
    if (!reason) return renderProject(root, projectId);
    body.blocked_reason = reason;
  }
  if (status === 'skipped') {
    body.skip_reason = prompt('Why skip this stage?');
    body.approved_by = prompt('Who approved skipping it?');
    if (!body.skip_reason || !body.approved_by) return renderProject(root, projectId);
  }
  try {
    await api.patch(`/stages/${stageId}`, body);
  } catch (e: any) {
    alert(e?.message ?? 'Update failed');
  }
  renderProject(root, projectId);
}

async function onDoc(e: Event, projectId: number, root: HTMLElement) {
  e.preventDefault();
  const f = e.target as HTMLFormElement;
  const filename = (f.elements.namedItem('filename') as HTMLInputElement).value.trim();
  if (!filename) return;
  const v = (f.elements.namedItem('version_number') as HTMLInputElement).value;
  try {
    await api.post('/documents', {
      project_stage_id: Number(f.dataset.stage),
      filename,
      doc_type: (f.elements.namedItem('doc_type') as HTMLSelectElement).value,
      version_number: v ? Number(v) : null,
    });
  } catch (err: any) {
    alert(err?.message ?? 'Failed');
  }
  renderProject(root, projectId);
}
