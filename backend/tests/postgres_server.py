"""The test harness's PostgreSQL server (PG-D8): private, on a local socket, started per run.

The server runs from the installed PostgreSQL 17 binaries (Homebrew's ``postgresql@17``; never
``brew services``) on the data directory ``backend/.test-postgres/data``, which is kept between
runs so the seeded template databases (``tests/seeds.py``) survive. It listens on a Unix socket
only, is created with the ICU root collation (PG-D11), and runs with durability off: its data is
disposable, and a damaged data directory is simply deleted and built again.

Several runs share the server (TS2): each names its databases with a run ID (``run_ids.py``). A run
refuses to start when the data folder resolves into a place a cloud service syncs, or when the
volume holding it has less than ``MINIMUM_FREE_GIB`` free (``guard``).

A run that finds the server stopped starts it (and leaves ``started-by-harness`` in the data root); a
run that finds it already running leaves it running, and one an outside tool started (no such file)
is never stopped. Each run holds a shared advisory lock for as long as it uses the server; the run
that ends last, and only it, stops a server the harness started (``stop``): no run stops a server
another still uses. Start and stop run one at a time under a file lock, and a start registers its use
before releasing it, so a starting run never connects to a server being stopped. ``RDM_TEST_DATABASE_SERVER``, a
superuser URL to an existing server (CI's ``postgres:17`` service), replaces the private server.
"""

import fcntl
import os
import shutil
import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Final

from sqlalchemy import URL, create_engine, make_url, text
from sqlalchemy.engine import Connection
from sqlalchemy.pool import NullPool

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND / ".test-postgres"
DATA = ROOT / "data"
# The socket's folder by its resolved path: a Unix socket path is limited to 103 bytes, and a clean
# copy (``clean_copy.py``) reaches ``.test-postgres`` through a link deep in a temporary folder.
SOCKET_DIRECTORY = ROOT.resolve()
LOG = ROOT / "server.log"
STARTED_MARK = ROOT / "started-by-harness"
USERS_LOCK = "rdm-test-server-users"
PORT = 55432
MAJOR_VERSION = "17"
EXTERNAL_SERVER = "RDM_TEST_DATABASE_SERVER"
MINIMUM_FREE_GIB: Final = 10
GIB = 1024**3
# Path components that mark a folder a cloud service syncs; ``Desktop`` and ``Documents`` only when
# iCloud Drive syncs them (its ``Documents`` folder exists then).
SYNCED_COMPONENTS = (
    "Dropbox",
    "OneDrive",
    "iCloud Drive",
    "com~apple~CloudDocs",
    "Mobile Documents",
)

# Durability off and enough connections for the tests that race several of them.
SETTINGS = {
    "listen_addresses": "''",
    "unix_socket_directories": f"'{SOCKET_DIRECTORY}'",
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


def synced_place(folder: Path, home: Path | None = None) -> str | None:
    """What syncs ``folder`` (the resolved path of the data folder), or None when nothing does."""
    home = home or Path.home()
    parts = folder.parts
    for part in parts:
        for marker in SYNCED_COMPONENTS:
            if part == marker or part.startswith((marker + " -", marker + "-")):
                return marker
    if "CloudStorage" in parts:
        return "a cloud storage folder (Library/CloudStorage)"
    icloud = home / "Library" / "Mobile Documents" / "com~apple~CloudDocs"
    for name in ("Desktop", "Documents"):
        if folder.is_relative_to(home / name) and (icloud / name).is_dir():
            return f"iCloud Drive (it syncs ~/{name})"
    return None


def guard(root: Path = ROOT, home: Path | None = None) -> None:
    """Refuse to run on a data folder in a synced place or on a volume with too little space free.

    The path is the resolved one (``backend/.test-postgres`` is a link to the unsynced volume). Skipped
    for an external server (CI's service). ``fsync`` stays off: the answer to a slow disk is never
    more durability.
    """
    if os.environ.get(EXTERNAL_SERVER):
        return
    if root.is_symlink() and not root.exists():
        raise ServerUnavailable(
            f"{root} links to {root.readlink()}, which does not exist. Connect or mount that volume, "
            f"or replace the link with: mkdir -p <an unsynced folder> && ln -s <that folder> {root}"
        )
    resolved = root.resolve()
    where = synced_place(resolved, home)
    if where is not None:
        raise ServerUnavailable(
            f"The test server's data folder resolves to {resolved}, which {where} syncs; the "
            "databases are 5-10 GB and change constantly. Move it to a local unsynced volume: stop "
            f"the test server, then delete {root} (or point the link {root} at an unsynced folder, "
            "for example /Volumes/RDMScratch/test-postgres). The next run creates it and rebuilds the seeds."
        )
    existing = resolved
    while not existing.exists():
        existing = existing.parent
    free = shutil.disk_usage(existing).free
    if free < MINIMUM_FREE_GIB * GIB:
        raise ServerUnavailable(
            f"Only {free / GIB:.1f} GB are free on the volume holding the test server's data folder "
            f"({existing}); a run needs {MINIMUM_FREE_GIB} GB. Free space there (delete files, or drop "
            "test databases you do not need) and run again."
        )


_USE: dict[str, Connection | None] = {"connection": None}


def _lock_connection() -> Connection:
    engine = create_engine(url(), isolation_level="AUTOCOMMIT", poolclass=NullPool)
    return engine.connect()


def register_use() -> None:
    """Hold a shared lock on the server for as long as this process uses it (dies with the process)."""
    if _USE["connection"] is None:
        connection = _lock_connection()
        connection.execute(text("SELECT pg_advisory_lock_shared(hashtext(:n))"), {"n": USERS_LOCK})
        _USE["connection"] = connection


def release_use() -> None:
    connection = _USE["connection"]
    _USE["connection"] = None
    if connection is not None:
        connection.close()


def is_running() -> bool:
    if not DATA.exists():
        return False
    return _run(_binary("pg_ctl"), "status", "--pgdata", str(DATA)).returncode == 0


@contextmanager
def _exclusive() -> Iterator[None]:
    """Starting and stopping the server are one at a time: an exclusive ``flock`` on a file in the
    data root's resolved folder, so a starting run never connects to a server being stopped."""
    SOCKET_DIRECTORY.mkdir(parents=True, exist_ok=True)
    with (SOCKET_DIRECTORY / "server.lock").open("a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def start() -> bool:
    """Start the private server if it is not running and register this run's use of it, under the
    start/stop lock; True when this call started it."""
    if os.environ.get(EXTERNAL_SERVER):
        return False
    guard()
    with _exclusive():
        return _start_locked()


def _start_locked() -> bool:
    version = _run(_binary("pg_ctl"), "--version").stdout
    if f"(PostgreSQL) {MAJOR_VERSION}." not in version:
        raise ServerUnavailable(
            f"The test harness needs PostgreSQL {MAJOR_VERSION}, but pg_ctl reports "
            f"'{version.strip()}'. Set RDM_POSTGRES_BIN to the PostgreSQL {MAJOR_VERSION} binaries."
        )
    if (DATA / "PG_VERSION").exists() and (
        DATA / "PG_VERSION"
    ).read_text().strip() != MAJOR_VERSION:
        raise ServerUnavailable(
            f"{DATA} was created by another PostgreSQL version. Delete {ROOT}; the next run "
            "creates it again and rebuilds the seeds."
        )
    if not (DATA / "PG_VERSION").exists():
        _initialise()
    if is_running():
        register_use()
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
    STARTED_MARK.touch()
    register_use()
    return True


def stop() -> None:
    """End this run's use of the server; stop it when the harness started it and no run still uses it."""
    if os.environ.get(EXTERNAL_SERVER):
        return
    with _exclusive():
        _stop_locked()


def _stop_locked() -> None:
    release_use()
    if not STARTED_MARK.exists() or not is_running():
        return
    # An exclusive lock is free only when no run holds the shared one; it dies with the server.
    with _lock_connection() as connection:
        free = connection.scalar(
            text("SELECT pg_try_advisory_lock(hashtext(:n))"), {"n": USERS_LOCK}
        )
        if free:
            STARTED_MARK.unlink(missing_ok=True)
            _run(
                _binary("pg_ctl"),
                "stop",
                "--pgdata",
                str(DATA),
                "--mode",
                "fast",
                "--wait",
                "--silent",
            )


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
        query={"host": str(SOCKET_DIRECTORY), "port": str(PORT)},
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
