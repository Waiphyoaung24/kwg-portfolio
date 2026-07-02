const j = async (r: Response) => {
  if (r.status === 401) throw { unauth: true };
  if (!r.ok) throw new Error((await r.text()) || r.statusText);
  return r.status === 204 ? null : r.json();
};

export const api = {
  get: (p: string) => fetch('/api' + p).then(j),
  post: (p: string, body: unknown) =>
    fetch('/api' + p, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) }).then(j),
  patch: (p: string, body: unknown) =>
    fetch('/api' + p, { method: 'PATCH', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) }).then(j),
};
