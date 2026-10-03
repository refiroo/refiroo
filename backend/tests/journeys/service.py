"""The service as an operator runs it (J12): started with settings on a database, its operator output
read from its log, its commands run as processes.

``serve`` starts the application with ``DATABASE_URL``, the configuration's model as ``RDM_MODEL_PATH``
and any other settings, runs its startup (the lifespan, with the job worker), and yields a
:class:`Service`: the client, the operator output so far, and a :class:`scenario.World` for the API.
"""

import logging
import os
import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from pathlib import Path

from configurations import Configuration
from fastapi.testclient import TestClient
from scenario import Api, World, model_path
from sqlalchemy import URL, create_engine, make_url, text
from sqlalchemy.pool import NullPool

BACKEND = Path(__file__).resolve().parents[2]


class _Output(logging.Handler):
    """The application's log as the operator reads it: one entry per record, at INFO and above."""

    def __init__(self) -> None:
        super().__init__(logging.INFO)
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


@dataclass
class Service:
    client: TestClient
    output: _Output
    world: World
    url: URL | None = None

    def errors(self) -> list[logging.LogRecord]:
        return [r for r in self.output.records if r.levelno >= logging.ERROR]

    def health(self) -> int:
        return self.client.get("/health").status_code


def render(url: URL) -> str:
    return url.render_as_string(hide_password=False)


@contextmanager
def serve(
    configuration: Configuration, url: URL | str | None, **settings: str
) -> Iterator[Service]:
    """The application started on ``url`` (unset when ``None``) with ``settings``."""
    from app.config import reload_settings
    from app.db import DatabaseStartupError, get_engine
    from app.engine.model.registry import model_registry
    from app.main import create_app

    wanted = {
        "DATABASE_URL": render(url) if isinstance(url, URL) else url,
        "RDM_MODEL_PATH": str(model_path(configuration)),
        **settings,
    }
    saved = {key: os.environ.get(key) for key in wanted}
    output = _Output()
    logger = logging.getLogger("app")
    level = logger.level
    logger.addHandler(output)
    logger.setLevel(logging.INFO)
    for key, value in wanted.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
    model_registry.clear()
    try:
        app = create_app()
        # A served process answers an unexpected error with its handler's response; so does this.
        with TestClient(app, raise_server_exceptions=False) as client:
            parsed = make_url(wanted["DATABASE_URL"]) if wanted["DATABASE_URL"] else None
            yield Service(client, output, World(configuration, Api(client), parsed), parsed)
    finally:
        # No engine for a refused URL, and no settings at all for a refused setting.
        with suppress(DatabaseStartupError, RuntimeError):
            get_engine().dispose()
        logger.removeHandler(output)
        logger.setLevel(level)
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        reload_settings()
        model_registry.clear()


def command(module: str, url: URL, *args: str) -> subprocess.CompletedProcess[str]:
    """``python -m <module> <args>`` from the backend directory, as the operator runs it."""
    env = {**os.environ, "DATABASE_URL": render(url)}
    return subprocess.run(
        [sys.executable, "-m", module, *args],
        cwd=BACKEND,
        env=env,
        capture_output=True,
        check=False,
        text=True,
        timeout=120,
    )


def scalar(url: URL, statement: str, **params: object) -> object:
    engine = create_engine(url, poolclass=NullPool)
    try:
        with engine.connect() as connection:
            return connection.scalar(text(statement), params)
    finally:
        engine.dispose()


def execute(url: URL, statement: str, **params: object) -> None:
    engine = create_engine(url, poolclass=NullPool)
    try:
        with engine.begin() as connection:
            connection.execute(text(statement), params)
    finally:
        engine.dispose()
