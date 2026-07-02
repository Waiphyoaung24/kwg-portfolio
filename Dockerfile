# Builds and runs the Astro SSR server (@astrojs/node standalone).
# This is a Node app, NOT a static site — it serves the pages, the /api routes,
# and talks to Postgres. Do NOT serve dist/ with a static file server (`serve`).

# --- build stage ---
FROM node:24-alpine AS build
WORKDIR /app
COPY package.json yarn.lock ./
RUN yarn install --frozen-lockfile
COPY . .
# `astro build` (skip `astro check` — type-checking isn't needed just to deploy).
RUN yarn astro build

# --- runtime stage ---
FROM node:24-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production
# The standalone server reads HOST and PORT. HOST MUST be 0.0.0.0 so the
# container accepts external traffic (the default 'localhost' refuses it).
ENV HOST=0.0.0.0
ENV PORT=3000
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/dist ./dist
COPY --from=build /app/package.json ./
EXPOSE 3000
CMD ["node", "./dist/server/entry.mjs"]
