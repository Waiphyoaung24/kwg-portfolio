import { readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { resolve } from 'node:path';
import { build } from 'esbuild';

const root = resolve(fileURLToPath(new URL('../..', import.meta.url)));
const client = resolve(root, 'dist/client');
for (const page of ['trading', 'trading-bot']) {
  const html = await readFile(resolve(client, `vault/${page}/index.html`), 'utf8');
  if (/href=["']https?:\/\/(?:localhost|127\.0\.0\.1|\[::1\]):8899(?=[/"'])/i.test(html)) {
    throw new Error('Production trading page must not link to local Vibe');
  }
  const stylesheets = [...html.matchAll(/<link rel="stylesheet" href="(\/_astro\/[^\"]+\.css)">/g)];
  if (!stylesheets.length) throw new Error('Trading page stylesheet not found');
  let standalone = html;
  for (const stylesheet of stylesheets) {
    const css = await readFile(resolve(client, stylesheet[1].slice(1)), 'utf8');
    if (css.includes('</style>')) throw new Error('Stylesheet cannot be inlined safely');
    standalone = standalone.replace(stylesheet[0], `<style>${css}</style>`);
  }
  // The private service serves HTML files without Astro's asset directory.
  for (const script of html.matchAll(/<script type="module" src="(\/_astro\/[^\"]+\.js)"><\/script>/g)) {
    // Astro can share chunks between the two pages; bundle those local imports.
    const bundled = await build({ entryPoints: [resolve(client, script[1].slice(1))],
      bundle: true, write: false, format: 'iife', platform: 'browser', minify: true });
    const js = bundled.outputFiles[0].text;
    if (js.includes('</script>')) throw new Error('Status script cannot be inlined safely');
    standalone = standalone.replace(script[0], `<script type="module">${js}</script>`);
  }
  await writeFile(resolve(root, `ops/trading/${page}.html`), standalone);
}
