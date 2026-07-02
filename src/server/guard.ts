import { isAuthed } from './auth.mjs';

export function guard(request: Request): Response | null {
  return isAuthed(request) ? null : new Response('unauthorized', { status: 401 });
}
