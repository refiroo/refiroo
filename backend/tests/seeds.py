"""Seeded databases built once and reused (TEST_HARNESS_PLAN H1).

A seed is a template database on the test server (``tests/postgres_server.py``) built by a seed
function: ``schema`` is the empty schema at the Alembic head, and ``volume-…`` the Track S volume
fixture at one shape. Each seed carries a fingerprint of what it was built from (the migrations, the
model, the source of its seed function and of the fixture code it calls, and its base seed's
fingerprint). On use a matching fingerprint is reused as it is; a different one rebuilds that seed
once, so a schema, model or seed code change rebuilds only the seeds it affects, and later runs
reuse them. A test gets a clone (``CREATE DATABASE … TEMPLATE``) and never writes to a seed.

Run from ``backend/``::

    .venv/bin/python -m tests.seeds list    # each seed, its fingerprint and whether it is current
    .venv/bin/python -m tests.seeds build   # build every stale seed up front
"""

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import engine_writer  # noqa: F401
import harness_identity
import postgres_server
from sqlalchemy import URL, create_engine, text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

TESTS = Path(__file__).resolve().parent
BACKEND = TESTS.parent
APP = BACKEND / "app"
HARNESS_DATABASE = "rdm_harness"
PREFIX = "seed_"
# Every scale a volume module uses; ``build`` prebuilds these.
VOLUME_SCALES = (0.005, 0.01, 0.02, 0.04)

# What this process did with each seed it used, for the run's summary: (name, "reused" | "built", s).
ACTIVITY: list[tuple[str, str, float]] = []


@dataclass(frozen=True)
class Seed:
    """A named database built by ``build`` into the database at the URL it is given.

    ``inputs`` names what the seed is built from (source files, the model, the shape); their content
    is the fingerprint, with the base seed's fingerprint when the seed starts from one.
    """

    name: str
    build: Callable[[URL], dict[str, Any]]
    inputs: Callable[[], list[str | Path]]
    base: str | None = None


SEEDS: dict[str, Seed] = {}


def register(seed: Seed) -> Seed:
    SEEDS.setdefault(seed.name, seed)
    return SEEDS[seed.name]


def fingerprint(name: str) -> str:
    seed = SEEDS[name]
    digest = hashlib.sha256()
    if seed.base is not None:
        digest.update(fingerprint(seed.base).encode())
    for item in seed.inputs():
        if isinstance(item, Path):
            digest.update(str(item.relative_to(BACKEND)).encode())
            digest.update(item.read_bytes())
        else:
            digest.update(item.encode())
        digest.update(b"\0")
    return digest.hexdigest()


# --- The server and its catalogue --------------------------------------------------------------


def admin() -> Connection:
    """An autocommit superuser connection to the server's maintenance database."""
    # No pool: a pooled connection left open to a database would block cloning or dropping it.
    engine = create_engine(postgres_server.url(), isolation_level="AUTOCOMMIT", poolclass=NullPool)
    return engine.connect()


@contextmanager
def _catalogue() -> Iterator[Connection]:
    """A connection to the harness database, which records each seed's fingerprint and payload."""
    with admin() as server:
        exists = server.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": HARNESS_DATABASE}
        )
        if not exists:
            server.execute(text(f'CREATE DATABASE "{HARNESS_DATABASE}"'))
    engine = create_engine(
        postgres_server.url(HARNESS_DATABASE), isolation_level="AUTOCOMMIT", poolclass=NullPool
    )
    try:
        with engine.connect() as connection:
            connection.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS seeds (name text PRIMARY KEY, fingerprint text "
                    "NOT NULL, payload jsonb NOT NULL, built_at timestamptz NOT NULL, "
                    "build_seconds double precision NOT NULL)"
                )
            )
            yield connection
    finally:
        engine.dispose()


def _database_exists(server: Connection, database: str) -> bool:
    return bool(
        server.scalar(text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": database})
    )


def _drop(server: Connection, database: str) -> None:
    server.execute(text(f'DROP DATABASE IF EXISTS "{database}" WITH (FORCE)'))


def _create(server: Connection, database: str, template: str) -> None:
    server.execute(text(f'CREATE DATABASE "{database}" TEMPLATE "{template}" STRATEGY FILE_COPY'))


def template_name(name: str) -> str:
    return PREFIX + name.replace("-", "_").replace(".", "_")


# --- Using a seed --------------------------------------------------------------------------------


def status(name: str) -> tuple[str, dict[str, Any] | None]:
    """``current``, ``stale`` or ``missing``, with the stored row when there is one."""
    with _catalogue() as catalogue:
        row = catalogue.execute(
            text("SELECT fingerprint, payload, built_at, build_seconds FROM seeds WHERE name = :n"),
            {"n": name},
        ).one_or_none()
    with admin() as server:
        present = _database_exists(server, template_name(name))
    if row is None or not present:
        return "missing", None
    stored = dict(row._mapping)
    return ("current" if row.fingerprint == fingerprint(name) else "stale"), stored


def ensure(name: str) -> dict[str, Any]:
    """Build ``name`` if it is missing or stale and return its payload."""
    seed = SEEDS[name]
    if seed.base is not None:
        ensure(seed.base)
    expected = fingerprint(name)
    with _catalogue() as catalogue:
        # One builder at a time per seed, should two runs ever share the server.
        catalogue.execute(text("SELECT pg_advisory_lock(hashtext(:n))"), {"n": name})
        try:
            row = catalogue.execute(
                text("SELECT fingerprint, payload, built_at FROM seeds WHERE name = :n"),
                {"n": name},
            ).one_or_none()
            # A base rebuilt with the same inputs holds new content (a schema seed's harness client
            # is made anew), so a seed built on it before is stale too (found in 0.12 HM1).
            base_built = (
                catalogue.execute(
                    text("SELECT built_at FROM seeds WHERE name = :n"), {"n": seed.base}
                ).scalar_one_or_none()
                if seed.base is not None
                else None
            )
            with admin() as server:
                present = _database_exists(server, template_name(name))
            fresh = base_built is None or (row is not None and row.built_at >= base_built)
            if row is not None and present and row.fingerprint == expected and fresh:
                ACTIVITY.append((name, "reused", 0.0))
                return row.payload
            started = time.perf_counter()
            payload = _build(seed)
            seconds = time.perf_counter() - started
            catalogue.execute(
                text(
                    "INSERT INTO seeds VALUES (:n, :f, CAST(:p AS jsonb), :at, :s) ON CONFLICT "
                    "(name) DO UPDATE SET fingerprint = excluded.fingerprint, payload = "
                    "excluded.payload, built_at = excluded.built_at, build_seconds = "
                    "excluded.build_seconds"
                ),
                {
                    "n": name,
                    "f": expected,
                    "p": json.dumps(payload),
                    "at": datetime.now(UTC),
                    "s": seconds,
                },
            )
            ACTIVITY.append((name, "built", seconds))
            return payload
        finally:
            catalogue.execute(text("SELECT pg_advisory_unlock(hashtext(:n))"), {"n": name})


def _build(seed: Seed) -> dict[str, Any]:
    target = template_name(seed.name)
    building = target + "__build"
    with admin() as server:
        _drop(server, building)
        if seed.base is None:
            server.execute(text(f'CREATE DATABASE "{building}" TEMPLATE template0'))
        else:
            _create(server, building, template_name(seed.base))
    try:
        payload = seed.build(postgres_server.url(building))
    except BaseException:
        with admin() as server:
            _drop(server, building)
        raise
    with admin() as server:
        if _database_exists(server, target):
            server.execute(text(f'ALTER DATABASE "{target}" IS_TEMPLATE false'))
            _drop(server, target)
        server.execute(text(f'ALTER DATABASE "{building}" RENAME TO "{target}"'))
        server.execute(text(f'ALTER DATABASE "{target}" IS_TEMPLATE true'))
    return payload


def clone(name: str, database: str | None = None) -> URL:
    """A new database copied from seed ``name`` (built first if needed); drop it with :func:`drop`."""
    ensure(name)
    database = database or f"t_{uuid4().hex[:16]}"
    with admin() as server:
        _drop(server, database)
        _create(server, database, template_name(name))
    return postgres_server.url(database)


@contextmanager
def schema_session() -> Iterator[Session]:
    """A session on a new clone of the ``schema`` seed (the baseline's default workspace and no
    model release), dropped when the block ends. For engine tests that run without the application."""
    url = clone("schema")
    engine = create_engine(url)
    try:
        with Session(engine) as session:
            yield session
    finally:
        engine.dispose()
        drop(url.database)


def create_empty(options: str = "") -> URL:
    """A new database with no schema, from ``template0`` with ``options`` (for example a locale)."""
    database = f"t_{uuid4().hex[:16]}"
    with admin() as connection:
        connection.execute(text(f'CREATE DATABASE "{database}" TEMPLATE template0 {options}'))
    return postgres_server.url(database)


def drop(database: str) -> None:
    with admin() as server:
        _drop(server, database)


def drop_clones() -> None:
    """Drop every test database a run left behind (an interrupted run skips its teardown)."""
    with admin() as server:
        names = server.scalars(
            text("SELECT datname FROM pg_database WHERE datname LIKE 't\\_%' OR datname LIKE :b"),
            {"b": f"{PREFIX}%__build"},
        ).all()
        for database in names:
            _drop(server, database)


# --- Building with the application --------------------------------------------------------------


@contextmanager
def application_environment(url: URL, model_path: Path | None = None) -> Iterator[None]:
    """Point the application's configuration at ``url`` (and a model) while the block runs."""
    from app.config import reload_settings
    from app.db import get_engine
    from app.engine.model.registry import model_registry

    saved = {key: os.environ.get(key) for key in ("DATABASE_URL", "RDM_MODEL_PATH", "JOB_FILE_DIR")}
    os.environ["DATABASE_URL"] = url.render_as_string(hide_password=False)
    if model_path is not None:
        os.environ["RDM_MODEL_PATH"] = str(model_path)
    # Job files (0.9 J1) of an application started outside a test session (a seed build, the
    # volume script) go to a directory of their own, never the project's var/.
    files = None if saved["JOB_FILE_DIR"] else tempfile.mkdtemp(prefix="rdm-job-files-")
    if files is not None:
        os.environ["JOB_FILE_DIR"] = files
    reload_settings()
    model_registry.clear()
    try:
        yield
    finally:
        get_engine().dispose()
        if files is not None:
            shutil.rmtree(files, ignore_errors=True)
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        reload_settings()
        model_registry.clear()


# The identity modules the harness's client, person and signing key are made by.
_HARNESS_MAKERS = ("clients.py", "keys.py", "passwords.py", "settings.py", "users.py")


def _migrations() -> list[str | Path]:
    # With the harness's client, person and signing key (0.12 I1, D263): what makes them is an input
    # too. Only the modules that make them (harness_identity.create_harness_client), not the whole
    # identity package: an edit to sign-in, sessions or resets changes nothing a seed holds, and
    # counting it rebuilt every seed under the runs using them (0.17 RF, 2026-11-11).
    identity = APP / "engine" / "identity"
    return [
        *sorted((APP / "migrations").rglob("*.py")),
        *(identity / name for name in _HARNESS_MAKERS),
        *sorted((APP / "engine" / "authorization").glob("*.py")),
        TESTS / "harness_identity.py",
    ]


def _build_schema(url: URL) -> dict[str, Any]:
    from app.db import create_database

    with application_environment(url):
        create_database()
        return {"harness": harness_identity.create_harness_client()}


register(Seed("schema", _build_schema, _migrations))


def volume_seed(shape: Any) -> str:
    """The name of the seed holding the volume fixture at ``shape``, registered on first use."""
    import volume_fixture

    shape_text = json.dumps(asdict(shape), sort_keys=True)
    digest = hashlib.sha256(shape_text.encode()).hexdigest()[:6]
    name = f"volume-{shape.groups}x{shape.items}-{digest}"

    def build(url: URL) -> dict[str, Any]:
        from harness_identity import TestClient

        from app.db import get_engine
        from app.main import create_app

        with tempfile.TemporaryDirectory() as directory:
            model_path = Path(directory) / "volume-model.json"
            model_path.write_text(json.dumps(volume_fixture.volume_model()))
            with application_environment(url, model_path), TestClient(create_app()):
                dataset = volume_fixture.seed_volume(get_engine(), shape)
        return {"shape": asdict(shape), "dataset": asdict(dataset)}

    def inputs() -> list[str | Path]:
        return [
            shape_text,
            json.dumps(volume_fixture.volume_model(), sort_keys=True),
            TESTS / "volume_fixture.py",
            APP / "engine" / "indexes" / "matrix_states.py",
            APP / "engine" / "indexes" / "snapshot_values.py",
            APP / "engine" / "model" / "bootstrap.py",
        ]

    register(Seed(name, build, inputs, base="schema"))
    return name


def register_volume_seeds() -> None:
    import volume_fixture

    for scale in VOLUME_SCALES:
        volume_seed(volume_fixture.scaled_shape(scale))


# --- Command line --------------------------------------------------------------------------------


def _list() -> None:
    register_volume_seeds()
    for name in SEEDS:
        state, row = status(name)
        built = ""
        if row is not None:
            built = f"built {row['built_at']:%Y-%m-%d %H:%M} in {row['build_seconds']:.1f} s"
            shape = row["payload"].get("shape")
            if shape:
                built += f", {shape['groups']} groups, {shape['items']} items"
        print(f"{name:20} {fingerprint(name)[:12]}  {state:8} {built}")


def _build_all() -> None:
    register_volume_seeds()
    for name in SEEDS:
        ensure(name)
    for name, outcome, seconds in ACTIVITY:
        print(f"{name:20} {outcome}" + (f" in {seconds:.1f} s" if outcome == "built" else ""))


def main() -> None:
    parser = argparse.ArgumentParser(description="The test harness's seeded databases (H1).")
    parser.add_argument("command", choices=("list", "build"))
    arguments = parser.parse_args()
    started = postgres_server.start()
    # A seed build imports app.main, which starts an application: its job files (0.9 J1) go to a
    # directory of this command's, never the project's var/.
    files = tempfile.mkdtemp(prefix="rdm-job-files-")
    os.environ.setdefault("JOB_FILE_DIR", files)
    try:
        _list() if arguments.command == "list" else _build_all()
    finally:
        shutil.rmtree(files, ignore_errors=True)
        if started:
            postgres_server.stop()


if __name__ == "__main__":
    main()
