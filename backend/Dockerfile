# The engine image (0.12 DP2, D405, D406). Built from the repository root:
#   docker build -f backend/Dockerfile -t refiroo-engine .

# The guide (0.13 DOC1): built here, so the engine image carries the built files and no Node.
# The telemetry setting keeps the build from reaching the internet beyond the package registry.
FROM node:22-alpine AS guide
WORKDIR /repo/guide
ENV ASTRO_TELEMETRY_DISABLED=1
COPY guide/package.json guide/package-lock.json ./
RUN npm ci
COPY guide/astro.config.mjs ./
COPY guide/sidebar ./sidebar
COPY guide/src ./src
COPY guide/public ./public
COPY guide/tools ./tools
# The shared header's stylesheet, which astro.config.mjs reads from ../frontend/public/brand/.
COPY frontend/public/brand /repo/frontend/public/brand
RUN npm run build

FROM python:3.14-slim

# The engine runs as a user of its own, never root.
# The AI assistant's session (AI_AGENT_COMMAND): Claude Code, with curl for the API. It stays unused
# until that setting is given. Set AI_AGENT_SANDBOX=container here: its own sandbox cannot run in a
# container, so this container is the boundary. The session runs as `assistant`, a user of its own
# that cannot read the engine's environment or its job files (the engine starts it through sudo, which
# the sudoers rule below lets run the Claude Code binary and nothing else).
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates nodejs npm sudo \
    && npm install -g @anthropic-ai/claude-code && test -x /usr/local/bin/claude \
    && apt-get purge -y npm && apt-get clean && rm -rf /var/lib/apt/lists/*

# Everything of the application lies under one folder that mirrors the repository: backend/, guide/dist,
# model/ and data/ (the job files and the assistant's folders). Nothing is added at /.
RUN useradd --system --uid 10001 --home-dir /opt/refiroo/rdm-engine/backend --shell /usr/sbin/nologin rdm \
    && mkdir -p /opt/refiroo/rdm-engine/backend /opt/refiroo/rdm-engine/data/job-files \
    && chown rdm:rdm /opt/refiroo/rdm-engine/data/job-files && chmod 0700 /opt/refiroo/rdm-engine/data/job-files
# The session's user, with a home of its own. Its folders and Claude Code's transcripts lie in two
# folders shared by the group of the two users (set-group-ID, so what either creates is the group's);
# the job files stay the engine's alone.
RUN groupadd --system assistant \
    && useradd --system --gid assistant --home-dir /opt/refiroo/rdm-engine/data/assistant-home \
        --no-create-home --shell /usr/sbin/nologin assistant \
    && usermod --append --groups assistant rdm \
    && mkdir -p /opt/refiroo/rdm-engine/data/assistant /opt/refiroo/rdm-engine/data/assistant-claude /opt/refiroo/rdm-engine/data/assistant-home \
    && chown rdm:assistant /opt/refiroo/rdm-engine/data/assistant /opt/refiroo/rdm-engine/data/assistant-claude \
    && chmod 2770 /opt/refiroo/rdm-engine/data/assistant /opt/refiroo/rdm-engine/data/assistant-claude \
    && chown assistant:assistant /opt/refiroo/rdm-engine/data/assistant-home && chmod 0750 /opt/refiroo/rdm-engine/data/assistant-home
# The engine's user may run the Claude Code binary as `assistant` and nothing else; the environment is
# reset and only what the engine passes is kept (never HOME: the session gets its own). Mode 0440 as
# sudo requires.
RUN printf '%s\n' \
    'Defaults:rdm env_reset, secure_path="/usr/local/bin:/usr/bin:/bin", umask=0007, umask_override' \
    'Defaults:rdm env_keep = "REFIROO_TOKEN LANG LC_* TMPDIR ANTHROPIC_* CLAUDE_* AWS_* NODE_*"' \
    'rdm ALL=(assistant) NOPASSWD: /usr/local/bin/claude' \
    > /etc/sudoers.d/rdm-assistant \
    && chmod 0440 /etc/sudoers.d/rdm-assistant && visudo -cf /etc/sudoers.d/rdm-assistant
WORKDIR /opt/refiroo/rdm-engine/backend
# Readable by the engine's user whatever the modes on the machine that builds (a file kept 600 there).
COPY --chmod=u=rwX,go=rX backend/pyproject.toml .
COPY --chmod=u=rwX,go=rX backend/app ./app
RUN pip install --no-cache-dir .
COPY --chmod=u=rwX,go=rX model/rdm-starter.json /opt/refiroo/rdm-engine/model/rdm-starter.json
# The built guide, served at /docs (app/management/guide_site.py finds guide/dist beside backend/).
COPY --from=guide --chmod=u=rwX,go=rX /repo/guide/dist /opt/refiroo/rdm-engine/guide/dist

# Which commit and tag the image was built from (0.13 BR); the image has no .git.
ARG REFIROO_BUILD_COMMIT=
ARG REFIROO_BUILD_TAG=
ENV REFIROO_BUILD_COMMIT=$REFIROO_BUILD_COMMIT \
    REFIROO_BUILD_TAG=$REFIROO_BUILD_TAG \
    RDM_MODEL_PATH=/opt/refiroo/rdm-engine/model/rdm-starter.json \
    JOB_FILE_DIR=/opt/refiroo/rdm-engine/data/job-files \
    AI_AGENT_FOLDERS=/opt/refiroo/rdm-engine/data/assistant \
    CLAUDE_CONFIG_DIR=/opt/refiroo/rdm-engine/data/assistant-claude \
    PYTHONUNBUFFERED=1
# Export and import files wait here; mount a volume to keep them across a new container.
VOLUME /opt/refiroo/rdm-engine/data/job-files /opt/refiroo/rdm-engine/data/assistant /opt/refiroo/rdm-engine/data/assistant-claude
USER rdm
EXPOSE 8000

# Alive, not ready: a database that is down or a migration that failed puts the engine in
# maintenance mode, which /health reports with 503 and an operator reads there.
HEALTHCHECK --interval=10s --timeout=3s --start-period=30s --retries=6 \
    CMD ["python", "-c", "import urllib.request as r; r.urlopen('http://127.0.0.1:8000/health/live', timeout=2)"]

# Behind the web image or an organisation's proxy, the caller's address is the one the proxy forwards
# (the sign-in throttle counts per address, D271). Uvicorn trusts forwarded addresses only from
# FORWARDED_ALLOW_IPS (127.0.0.1 unless set): name the proxy's address there.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--timeout-graceful-shutdown", "10"]
