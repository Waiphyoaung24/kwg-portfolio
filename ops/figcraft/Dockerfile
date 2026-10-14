# Use the unmodified browser release; no Rust toolchain or source fork.
FROM alpine:3.22 AS download
RUN apk add --no-cache curl unzip \
    && curl --fail --show-error --location --retry 3 \
       https://github.com/storytold/figcraft/releases/download/v0.5.1/figcraft-web-0.5.1.zip \
       --output /tmp/figcraft.zip \
    && echo 'b8faba80bfdee94254c9bb78e45977ecb4ff44de9915b34cfb51979a77c89e09  /tmp/figcraft.zip' | sha256sum -c - \
    && unzip -q /tmp/figcraft.zip -d /tmp/figcraft

FROM nginx:1.30-alpine
COPY --from=download /tmp/figcraft/figcraft-web-0.5.1/ /usr/share/nginx/html/
COPY nginx.conf /etc/nginx/conf.d/default.conf
