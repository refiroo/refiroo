# The engine image (0.12 DP2, D405, D406). Built from the repository root:
#   docker build -f backend/Dockerfile -t refiroo-engine .

# The guide (0.13 DOC1): built here, so the engine image carries the built files and no Node.
# The telemetry setting keeps the build from reaching the internet beyond the package registry.
FROM node:22-alpine@sha256:5b05da3f938f1c604b24c633646d48805a6667f378cb4908438616f3cc48a0bf AS guide
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

FROM python:3.14-slim@sha256:9aaa474097d094040649f2162a627c0049b408f52138d980916788d80f04802f

# The Claude Code version the image installs (0.17 RF4): a named version, never the newest at build time.
# Move it with --build-arg CLAUDE_CODE_VERSION=<version> or by changing this default (docs/OPERATIONS.md, Deploying).
ARG CLAUDE_CODE_VERSION=2.1.295

# The engine runs as a user of its own, never root.
# The AI assistant's session (AI_AGENT_COMMAND): Claude Code, with curl for the API. It stays unused
# until that setting is given. Set AI_AGENT_SANDBOX=container here: its own sandbox cannot run in a
# container, so this container is the boundary. The session runs as `assistant`, a user of its own
# that cannot read the engine's environment or its job files (the engine starts it through sudo, which
# the sudoers rule below lets run the Claude Code binary and nothing else).
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates nodejs npm sudo iptables \
    && npm install -g "@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}" && test -x /usr/local/bin/claude \
    && apt-get purge -y npm && apt-get clean && rm -rf /var/lib/apt/lists/*

# The network rule of the assistant's session users (SR-D6): the start step sets it when the container has
# NET_ADMIN, and the proxy that is the session's only way out runs as a user of its own, none of the sessions'.
RUN useradd --system --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin refiroo-proxy
COPY --chown=root:root --chmod=0755 backend/refiroo_session_proxy.py /usr/local/lib/refiroo/session_proxy.py
COPY --chown=root:root --chmod=0755 backend/refiroo-engine-start /usr/local/bin/refiroo-engine-start

# Everything of the application lies under one folder that mirrors the repository: backend/, guide/dist,
# model/ and data/ (the job files and the assistant's folders). Nothing is added at /.
RUN useradd --system --uid 10001 --home-dir /opt/refiroo/rdm-engine/backend --shell /usr/sbin/nologin rdm \
    && mkdir -p /opt/refiroo/rdm-engine/backend /opt/refiroo/rdm-engine/data/job-files \
    && chown rdm:rdm /opt/refiroo/rdm-engine/data/job-files && chmod 0700 /opt/refiroo/rdm-engine/data/job-files
# The sessions' users (0.17 RF5): a pool, `assistant-1` to `assistant-N`, each with a home of its own and a
# group of its own (`assistant-N`, the engine's user a member of every one) and all in the common group
# `assistant`. A turn takes one for its length (a lock file in data/assistant-slots, which only the engine
# enters), so two sessions at once are two different users, which cannot read each other's processes or
# environment. One engine process runs one session at a time: N is at least the number of engine processes
# (WEB_CONCURRENCY). Move it with --build-arg ASSISTANT_USERS=<N>. A task's folder (its gate) lies in
# data/assistant under a long random name and belongs to the engine alone; for the length of a turn the engine
# gives it to the group of the user that runs the turn, so no other session user, and no one between turns,
# can enter it. Inside it `work` and `claude` are the common group's (set-group-ID). The job files stay the
# engine's alone.
ARG ASSISTANT_USERS=8
RUN test "$ASSISTANT_USERS" -ge 1 \
    && groupadd --system assistant \
    && usermod --append --groups assistant rdm \
    && mkdir -p /opt/refiroo/rdm-engine/data/assistant /opt/refiroo/rdm-engine/data/assistant-slots \
    && chown rdm:assistant /opt/refiroo/rdm-engine/data/assistant && chmod 2710 /opt/refiroo/rdm-engine/data/assistant \
    && chown rdm:rdm /opt/refiroo/rdm-engine/data/assistant-slots && chmod 0700 /opt/refiroo/rdm-engine/data/assistant-slots \
    && for i in $(seq 1 "$ASSISTANT_USERS"); do \
        groupadd --system "assistant-$i" \
        && useradd --system --gid "assistant-$i" --groups assistant --create-home --home-dir "/home/assistant-$i" \
            --shell /usr/sbin/nologin "assistant-$i" \
        && chmod 0700 "/home/assistant-$i" \
        && usermod --append --groups "assistant-$i" rdm; \
    done
# What runs between turns, as the session user and never as root: it makes that user's files in the task
# readable by the next user, empties its home and ends every process it runs. Root's, not writable.
COPY --chown=root:root --chmod=0755 backend/refiroo-session-reset /usr/local/bin/refiroo-session-reset
# The engine's user may run the Claude Code binary and that script as a user of the pool and nothing else;
# the environment is reset and only what the engine passes is kept (HOME is the session user's own).
# The names in `env_keep` are the engine's own list (`PASSED_NAMES`, `LC_*` and `BEDROCK_NAMES` in
# backend/app/engine/tasks/agent/sandbox.py), which a unit test holds equal to this line. Mode 0440 as sudo requires.
RUN users="$(getent passwd | cut -d: -f1 | grep -E '^assistant-[0-9]+$' | paste -sd, - | sed 's/,/, /g')" \
    && test -n "$users" \
    && printf '%s\n' \
    "Runas_Alias ASSISTANTS = $users" \
    'Defaults:rdm env_reset, always_set_home, secure_path="/usr/local/bin:/usr/bin:/bin", umask=0007, umask_override' \
    'Defaults:rdm env_keep = "REFIROO_TOKEN LANG LC_* TMPDIR CLAUDE_CONFIG_DIR ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN CLAUDE_CODE_OAUTH_TOKEN ANTHROPIC_BASE_URL ANTHROPIC_MODEL ANTHROPIC_DEFAULT_OPUS_MODEL ANTHROPIC_DEFAULT_SONNET_MODEL ANTHROPIC_DEFAULT_HAIKU_MODEL NODE_EXTRA_CA_CERTS HTTPS_PROXY NO_PROXY CLAUDE_CODE_USE_BEDROCK AWS_REGION AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN AWS_PROFILE"' \
    'rdm ALL=(ASSISTANTS) NOPASSWD: /usr/local/bin/claude, /usr/local/bin/refiroo-session-reset' \
    > /etc/sudoers.d/rdm-assistant \
    && chmod 0440 /etc/sudoers.d/rdm-assistant && visudo -cf /etc/sudoers.d/rdm-assistant
WORKDIR /opt/refiroo/rdm-engine/backend
# Readable by the engine's user whatever the modes on the machine that builds (a file kept 600 there).
COPY --chmod=u=rwX,go=rX backend/pyproject.toml backend/constraints.txt ./
COPY --chmod=u=rwX,go=rX backend/app ./app
# Every dependency at the version backend/constraints.txt names (regenerated from pyproject.toml).
RUN pip install --no-cache-dir -c constraints.txt .
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
    AI_AGENT_SANDBOX=container \
    PYTHONUNBUFFERED=1
# Export and import files wait here; mount a volume to keep them across a new container.
VOLUME /opt/refiroo/rdm-engine/data/job-files /opt/refiroo/rdm-engine/data/assistant
# Started as root, so that the start step can set the session users' network rule (SR-D6); it starts the engine
# as `rdm` with NET_ADMIN removed from what the engine and its children can hold. Started as another user, or
# without NET_ADMIN, the engine runs as before and the session's network is not restricted.
ENTRYPOINT ["/usr/local/bin/refiroo-engine-start"]
EXPOSE 8000

# Alive, not ready: a database that is down or a migration that failed puts the engine in
# maintenance mode, which /health reports with 503 and an operator reads there.
HEALTHCHECK --interval=10s --timeout=3s --start-period=30s --retries=6 \
    CMD ["python", "-c", "import urllib.request as r; r.urlopen('http://127.0.0.1:8000/health/live', timeout=2)"]

# Behind the web image or an organisation's proxy, the caller's address is the one the proxy forwards
# (the sign-in throttle counts per address, D271). Uvicorn trusts forwarded addresses only from
# FORWARDED_ALLOW_IPS (127.0.0.1 unless set): name the proxy's address there.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--timeout-graceful-shutdown", "10"]
