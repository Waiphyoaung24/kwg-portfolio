// Serves the vendored page as-is, so the catalog shows the same file it runs.
import html from '../../../catalog/kage/index.html?raw';

export const prerender = true;

export const GET = () =>
  new Response(html, { headers: { 'content-type': 'text/html; charset=utf-8' } });
