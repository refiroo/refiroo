# The engine image (0.12 DP2, D405, D406). Built from the repository root:
#   docker build -f backend/Dockerfile -t refiroo-engine .
FROM python:3.14-slim

# The engine runs as a user of its own, never root.
RUN useradd --system --uid 10001 --home-dir /app --shell /usr/sbin/nologin rdm \
    && mkdir -p /app /data/job-files \
    && chown rdm:rdm /data/job-files
WORKDIR /app
# Readable by the engine's user whatever the modes on the machine that builds (a file kept 600 there).
COPY --chmod=u=rwX,go=rX backend/pyproject.toml .
COPY --chmod=u=rwX,go=rX backend/app ./app
RUN pip install --no-cache-dir .
COPY --chmod=u=rwX,go=rX model/rdm-starter.json /model/rdm-starter.json

ENV RDM_MODEL_PATH=/model/rdm-starter.json \
    JOB_FILE_DIR=/data/job-files \
    PYTHONUNBUFFERED=1
# Export and import files wait here; mount a volume to keep them across a new container.
VOLUME /data/job-files
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
