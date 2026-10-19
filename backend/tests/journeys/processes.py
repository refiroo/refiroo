"""The engine as separate server processes on one database (0.11 N1): each started with
``python -m uvicorn`` as an operator starts it, reached over HTTP on a port of its own, and stopped
when the block ends. Two processes on one database stand for two nodes; one process with
``--workers 2`` for ``WEB_CONCURRENCY=2``.
"""

import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import httpx
from configurations import Configuration
from scenario import Api, World, model_path
from service import BACKEND, render
from sqlalchemy import URL

STARTUP_SECONDS = 90
# The part of a process's log a failure shows.
LOG_TAIL = 4000


@dataclass
class Process:
    base: str
    log: Path
    world: World
    # The server's process ID: with one worker, the process that serves and runs the jobs.
    pid: int

    def output(self) -> str:
        return self.log.read_text(errors="replace")


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


@contextmanager
def run(
    configuration: Configuration,
    url: URL,
    ids: dict[str, str] | None = None,
    workers: int = 1,
    **settings: str,
) -> Iterator[Process]:
    """A server process on ``url`` with ``workers`` workers and ``settings`` (model administration
    on, ``WEB_CONCURRENCY`` as given or 2), serving once ``/health`` answers 200."""
    files = Path(tempfile.mkdtemp(prefix="rdm-n1-"))
    log = files / "server.log"
    port = _free_port()
    env = {
        **os.environ,
        "DATABASE_URL": render(url),
        "RDM_MODEL_PATH": str(model_path(configuration)),
        "JOB_FILE_DIR": str(files / "jobs"),
        "MODEL_ADMIN_MUTATIONS_ENABLED": "true",
        "WEB_CONCURRENCY": "2",
        **settings,
    }
    command = [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1"]
    command += ["--port", str(port), "--workers", str(workers), "--log-level", "info"]
    with log.open("w") as sink:
        server = subprocess.Popen(
            command, cwd=BACKEND, env=env, stdout=sink, stderr=subprocess.STDOUT
        )
    base = f"http://127.0.0.1:{port}"
    client = httpx.Client(base_url=base, timeout=60)
    try:
        _wait_until_serving(server, client, log)
        world = World(configuration, Api(client), url, ids=dict(ids or {}))
        yield Process(base, log, world, server.pid)
    finally:
        client.close()
        server.terminate()
        try:
            server.wait(20)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(10)
        shutil.rmtree(files, ignore_errors=True)


def _wait_until_serving(server: subprocess.Popen, client: httpx.Client, log: Path) -> None:
    deadline = time.monotonic() + STARTUP_SECONDS
    while time.monotonic() < deadline:
        if server.poll() is not None:
            raise AssertionError(f"the server exited: {log.read_text()[-LOG_TAIL:]}")
        try:
            if client.get("/health").status_code == 200:
                return
        except httpx.TransportError:
            pass
        time.sleep(0.2)
    raise AssertionError(f"the server did not serve: {log.read_text()[-LOG_TAIL:]}")
