# The web image (0.12 DP2, D405–D407): the application built once, then served by nginx, which
# forwards the engine's paths to the engine. Built from the repository root:
#   docker build -f frontend/Dockerfile -t refiroo-web .
FROM node:22-alpine AS build
# The repository's layout: the type check reads the starter model from beside the frontend folder.
WORKDIR /repo/frontend
COPY model/rdm-starter.json /repo/model/rdm-starter.json
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/index.html frontend/tsconfig.json frontend/vite.config.ts ./
COPY frontend/public ./public
COPY frontend/src ./src
# No VITE_API_URL: the application calls the address it is opened at (D404), so one build serves
# every installation.
RUN npm run build

# Not root: this nginx listens on 8080 (HTTP) and 8443 (HTTPS); publish them as 80 and 443.
FROM nginxinc/nginx-unprivileged:1.28-alpine
USER root
COPY --from=build /repo/frontend/dist /opt/refiroo/rdm-engine/frontend/dist
COPY frontend/nginx/tls.conf.template frontend/nginx/proxy.conf.template /opt/refiroo/rdm-engine/frontend/nginx/
COPY frontend/nginx/snippets /etc/nginx/templates/snippets
COPY frontend/nginx/05-choose-mode.sh /opt/refiroo/rdm-engine/frontend/nginx/05-choose-mode.sh
# The entrypoint runs what lies in /docker-entrypoint.d: a link to the script kept with the application.
RUN chmod +x /opt/refiroo/rdm-engine/frontend/nginx/05-choose-mode.sh \
    && ln -s /opt/refiroo/rdm-engine/frontend/nginx/05-choose-mode.sh /docker-entrypoint.d/05-choose-mode.sh \
    && mkdir -p /opt/refiroo/rdm-engine/frontend/certs \
    && chown -R nginx:nginx /etc/nginx/templates /opt/refiroo/rdm-engine/frontend/nginx
USER nginx

# WEB_TLS=files (default): HTTPS ended here with certs/fullchain.pem and certs/privkey.pem under /opt/refiroo/rdm-engine/frontend, plain
# HTTP redirected to PUBLIC_URL. WEB_TLS=proxy: plain HTTP on 8080 behind a load balancer that ends HTTPS.
ENV WEB_TLS=files \
    ENGINE_UPSTREAM=http://engine:8000 \
    WEB_MAX_BODY=256m
EXPOSE 8080 8443
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=6 \
    CMD ["wget", "-q", "-O", "/dev/null", "http://127.0.0.1:8080/web-health"]
