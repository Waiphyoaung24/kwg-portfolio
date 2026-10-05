import {defineConfig} from 'vite';
import {fileURLToPath} from 'node:url';
import tailwindcss from '@tailwindcss/vite';
export default defineConfig({plugins:[tailwindcss()],resolve:{alias:{'@':fileURLToPath(new URL('./src',import.meta.url))}},define:{'process.env.NODE_ENV':JSON.stringify('production')},esbuild:{jsx:'automatic'},build:{outDir:'../public/dashboard-assets',emptyOutDir:true,lib:{entry:'src/main.tsx',formats:['es'],fileName:()=> 'dashboard.js',cssFileName:'dashboard'},rollupOptions:{onwarn(w,warn){if(w.code==='MODULE_LEVEL_DIRECTIVE')return;warn(w);}}}});
