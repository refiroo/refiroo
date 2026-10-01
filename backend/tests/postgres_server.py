"""The test harness's PostgreSQL server (PG-D8): private, on a local socket, started per run.

The server runs from the installed PostgreSQL 17 binaries (Homebrew's ``postgresql@17``; never
``brew services``) on the data directory ``backend/.test-postgres/data``, which is kept between
runs so the seeded template databases (``tests/seeds.py``) survive. It listens on a Unix socket
only, is created with the ICU root collation (PG-D11), and runs with durability off: its data is
disposable, and a damaged data directory is simply deleted and built again.

A run that finds the server stopped starts it and stops it when the run ends; a run that finds it
already running (another tool started it) leaves it running. ``RDM_TEST_DATABASE_SERVER``, a
superuser URL to an existing server (CI's ``postgres:17`` service), replaces the private server.
"""

import os
import shutil
import subprocess
from pathlib import Path

from sqlalchemy import URL, create_engine, make_url, text

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND / ".test-postgres"
DATA = ROOT / "data"
LOG = ROOT / "server.log"
PORT = 55432
MAJOR_VERSION = "17"
EXTERNAL_SERVER = "RDM_TEST_DATABASE_SERVER"

# Durability off and enough connections for the tests that race several of them.
SETTINGS = {
    "listen_addresses": "''",
    "unix_socket_directories": f"'{ROOT}'",
    "port": str(PORT),
    "fsync": "off",
    "synchronous_commit": "off",
    "full_page_writes": "off",
    "max_connections": "200",
}


class ServerUnavailable(RuntimeError):
    """The test server cannot be started; the message says what to install or remove."""


def _binary(name: str) -> str:
    candidates = [
        os.environ.get("RDM_POSTGRES_BIN"),
        f"/opt/homebrew/opt/postgresql@{MAJOR_VERSION}/bin",
        f"/usr/local/opt/postgresql@{MAJOR_VERSION}/bin",
        f"/usr/lib/postgresql/{MAJOR_VERSION}/bin",
    ]
    for directory in candidates:
        if directory and (Path(directory) / name).exists():
            return str(Path(directory) / name)
    found = shutil.which(name)
    if found:
        return found
    raise ServerUnavailable(
        f"The test harness needs the PostgreSQL {MAJOR_VERSION} binaries and found no '{name}'. "
        f"Install them with 'brew install postgresql@{MAJOR_VERSION}' (do not start it with "
        "'brew services'), set RDM_POSTGRES_BIN to their directory, or set "
        f"{EXTERNAL_SERVER} to a superuser URL of a running PostgreSQL {MAJOR_VERSION} server."
    )


def _run(*arguments: str) -> subprocess.CompletedProcess[str]:
    # macOS refuses to start a postmaster whose inherited locale is unset or invalid ("postmaster
    # became multithreaded during startup"); the server's own collation is ICU regardless.
    environment = {**os.environ, "LC_ALL": "C"}
    return subprocess.run(arguments, capture_output=True, text=True, check=False, env=environment)


def _initialise() -> None:
    ROOT.mkdir(exist_ok=True)
    result = _run(
        _binary("initdb"),
        "--pgdata",
        str(DATA),
        "--username",
        "postgres",
        "--auth",
        "trust",
        "--encoding",
        "UTF8",
        "--locale",
        "C",
        "--locale-provider",
        "icu",
        "--icu-locale",
        "und",
        "--no-sync",
    )
    if result.returncode != 0:
        shutil.rmtree(DATA, ignore_errors=True)
        raise ServerUnavailable(f"initdb failed for the test server:\n{result.stderr.strip()}")
    with (DATA / "postgresql.conf").open("a") as conf:
        conf.write("\n# RDM Engine test harness (tests/postgres_server.py)\n")
        for name, value in SETTINGS.items():
            conf.write(f"{name} = {value}\n")


def is_running() -> bool:
    if not DATA.exists():
        return False
    return _run(_binary("pg_ctl"), "status", "--pgdata", str(DATA)).returncode == 0


def start() -> bool:
    """Start the private server if it is not running; True when this call started it."""
    if os.environ.get(EXTERNAL_SERVER):
        return False
    version = _run(_binary("pg_ctl"), "--version").stdout
    if f"(PostgreSQL) {MAJOR_VERSION}." not in version:
        raise ServerUnavailable(
            f"The test harness needs PostgreSQL {MAJOR_VERSION}, but pg_ctl reports "
            f"'{version.strip()}'. Set RDM_POSTGRES_BIN to the PostgreSQL {MAJOR_VERSION} binaries."
        )
    if (DATA / "PG_VERSION").exists() and (DATA / "PG_VERSION").read_text().strip() != MAJOR_VERSION:
        raise ServerUnavailable(
            f"{DATA} was created by another PostgreSQL version. Delete {ROOT}; the next run "
            "creates it again and rebuilds the seeds."
        )
    if not (DATA / "PG_VERSION").exists():
        _initialise()
    if is_running():
        return False
    result = _run(
        _binary("pg_ctl"), "start", "--pgdata", str(DATA), "--log", str(LOG), "--wait", "--silent"
    )
    if result.returncode != 0:
        log_tail = LOG.read_text().strip().splitlines()[-10:] if LOG.exists() else []
        raise ServerUnavailable(
            "The test PostgreSQL server did not start:\n"
            + "\n".join([result.stderr.strip(), *log_tail]).strip()
            + f"\nIf the data directory is damaged, delete {ROOT}; the next run creates it again."
        )
    return True


def stop() -> None:
    if os.environ.get(EXTERNAL_SERVER) or not is_running():
        return
    _run(_binary("pg_ctl"), "stop", "--pgdata", str(DATA), "--mode", "fast", "--wait", "--silent")


def url(database: str = "postgres") -> URL:
    """A superuser URL for ``database`` on the test server."""
    external = os.environ.get(EXTERNAL_SERVER)
    if external:
        base = make_url(external)
        if base.drivername == "postgresql":
            base = base.set(drivername="postgresql+psycopg")
        return base.set(database=database)
    return URL.create(
        "postgresql+psycopg",
        username="postgres",
        database=database,
        query={"host": str(ROOT), "port": str(PORT)},
    )


def without_foreign_keys(session) -> None:
    """Skip foreign key checks for the rest of ``session``'s transaction (the test role is a
    superuser). Only for a test that fabricates a state the engine guards against although the
    schema forbids it, such as a publication pinned to a release that does not exist."""
    session.execute(text("SET LOCAL session_replication_role = replica"))


def collated(values, key=None, reverse: bool = False) -> list:
    """``values`` sorted as the database orders names (ICU root collation, PG-D11), where Python's
    ``sorted`` would use code points. ``key`` gives a string or a tuple; each string in it ranks
    by the server's order, any other element as itself."""
    values = list(values)
    key = key or (lambda value: value)
    keys = [key(value) for value in values]
    parts = [part for item in keys for part in (item if isinstance(item, tuple) else (item,))]
    names = sorted({part for part in parts if isinstance(part, str)})
    engine = create_engine(url())
    try:
        with engine.connect() as connection:
            rows = connection.execute(
                text("SELECT name FROM unnest(CAST(:names AS text[])) AS name ORDER BY name"),
                {"names": names},
            )
            ranks = {name: rank for rank, (name,) in enumerate(rows)}
    finally:
        engine.dispose()

    def ranked(item):
        items = item if isinstance(item, tuple) else (item,)
        return tuple(ranks[part] if isinstance(part, str) else part for part in items)

    order = sorted(range(len(keys)), key=lambda index: ranked(keys[index]), reverse=reverse)
    return [values[index] for index in order]
