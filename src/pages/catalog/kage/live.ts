// Serves the vendored page as-is, so the catalog shows the same file it runs.
import html from '../../../catalog/kage/index.html?raw';

// Rendered per-request. A prerendered endpoint writes only its body to
// `dist/client/catalog/kage/live` — an extensionless file — and discards these
// headers, so the static server falls back to application/octet-stream and the
// browser downloads the page instead of showing it.
export const prerender = false;

export const GET = () =>
  new Response(html, {
    headers: { 'content-type': 'text/html; charset=utf-8' },
  });
