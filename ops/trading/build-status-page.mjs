import { readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { resolve } from 'node:path';

const root = resolve(fileURLToPath(new URL('../..', import.meta.url)));
const client = resolve(root, 'dist/client');
const html = await readFile(resolve(client, 'vault/trading/index.html'), 'utf8');
const stylesheets = [...html.matchAll(/<link rel="stylesheet" href="(\/_astro\/[^\"]+\.css)">/g)];
if (!stylesheets.length) throw new Error('Trading page stylesheet not found');
let standalone = html;
for (const stylesheet of stylesheets) {
  const css = await readFile(resolve(client, stylesheet[1].slice(1)), 'utf8');
  if (css.includes('</style>')) throw new Error('Stylesheet cannot be inlined safely');
  standalone = standalone.replace(stylesheet[0], `<style>${css}</style>`);
}
// The private status service serves one HTML file, without Astro's asset directory.
for (const script of html.matchAll(/<script type="module" src="(\/_astro\/[^\"]+\.js)"><\/script>/g)) {
  const js = await readFile(resolve(client, script[1].slice(1)), 'utf8');
  if (js.includes('</script>') || /\b(?:import|export)\b/.test(js)) throw new Error('Status script must be self-contained');
  standalone = standalone.replace(script[0], `<script type="module">${js}</script>`);
}
await writeFile(resolve(root, 'ops/trading/trading.html'), standalone);
