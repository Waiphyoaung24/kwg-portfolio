export const esc = (s: unknown) =>
  String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]!);

export const chip = (blockedOn: string) =>
  blockedOn === 'client' ? 'Waiting on client' : blockedOn === 'you' ? 'On you' : 'Clear';
