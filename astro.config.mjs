// @ts-check
import { defineConfig } from 'astro/config';

import node from '@astrojs/node';
import robotsTxt from 'astro-robots-txt';
import sitemap from '@astrojs/sitemap';
import glsl from 'vite-plugin-glsl';

// https://astro.build/config
export default defineConfig({
  // TODO: replace with the final production domain before going live
  site:
    process.env.NODE_ENV === 'development'
      ? 'http://localhost:4321'
      : 'https://kwg-portfolio.example.com',
  adapter: node({ mode: 'standalone' }),
  integrations: [
    robotsTxt({
      sitemapBaseFileName: 'sitemap-index',
      // TODO: remove when going live
      // policy: [
      //   {
      //     userAgent: '*',
      //     disallow: '/',
      //   },
      // ],
    }),
    sitemap({
      // /my-portfolio frames an unmodified third-party template whose own
      // metadata still says "Your Name". It keeps its route but should not
      // compete with the Services pages in search.
      filter: (page) =>
        !page.includes('/vault') && !page.includes('/my-portfolio'),
      lastmod: new Date(),
      xslURL: '/sitemap.xsl',
    }),
  ],
  vite: {
    css: {
      preprocessorOptions: {
        scss: {
          additionalData:
            '@use "/src/styles/functions" as *; @use "/src/styles/mixins" as *;',
        },
      },
    },
    plugins: [glsl()],
  },
});

// file meta order
// -----
// import css

// import type

// type Something

// interface Something

// import package

// import astro:content

// import @content

// import @layouts
// import @components

// getStaticPaths

// Astro.Props
