"""The database: PostgreSQL only (0.9.0-alpha.1, PG-D2), one pooled engine, and the startup checks.

:func:`create_database` runs at every start. It refuses, each with what failed, why, the service's
state and the operator's next step, a ``DATABASE_URL`` that is missing or not PostgreSQL, a server
it cannot reach, a database whose default collation is not ICU ``und`` (PG-D11), a revision this
version does not know and a missing ``pg_trgm`` extension (PG-D7), and then migrates to the Alembic
head. PostgreSQL runs DDL in the migration's transaction, so an interrupted upgrade leaves the
database at its previous revision.
"""

import logging
from functools import cache
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from alembic.util.exc import CommandError
from psycopg.pq import TransactionStatus
from sqlalchemy import URL, Connection, Engine, create_engine, make_url, text
from sqlalchemy.exc import ArgumentError, DBAPIError
from sqlalchemy.orm import Session, sessionmaker

from .config import database_url

logger = logging.getLogger(__name__)

DRIVER = "postgresql+psycopg"
# PG-D11: the language-independent Unicode root order, the same on every platform.
COLLATION_PROVIDER, COLLATION_LOCALES = "i", frozenset({"und", "root"})
REQUIRED_EXTENSION = "pg_trgm"

_MAINTENANCE = (
    "RDM Engine startup will remain in maintenance mode and /health will return HTTP 503."
)
_ESCALATE = (
    "If it still fails, report this complete message, the application version and the PostgreSQL "
    "server version."
)


class DatabaseStartupError(RuntimeError):
    """An operator-actionable reason the database cannot be used, safe to show without a traceback."""


class DatabaseMigrationError(DatabaseStartupError):
    """An operator-actionable database migration failure."""


def configured_url() -> URL:
    """The configured ``DATABASE_URL`` as a psycopg URL, or a refusal saying how to set it."""
    raw = database_url()
    if raw is None:
        raise DatabaseStartupError(
            "DATABASE_URL is not set. RDM Engine runs on PostgreSQL only. " + _MAINTENANCE + " "
            "Set DATABASE_URL to the database's URL, for example "
            "postgresql+psycopg://rdm@localhost:5432/rdm. For development, start the local server "
            "with 'scripts/postgres.sh start' from the repository root; it prints the URL to use."
        )
    try:
        url = make_url(raw)
    except ArgumentError:
        raise DatabaseStartupError(
            "DATABASE_URL is not a database URL. " + _MAINTENANCE + " Set it to a PostgreSQL URL "
            "such as postgresql+psycopg://rdm@localhost:5432/rdm."
        ) from None
    if url.get_backend_name() != "postgresql":
        raise DatabaseStartupError(
            f"DATABASE_URL names a {url.get_backend_name()} database "
            f"('{url.render_as_string(hide_password=True)}'), but RDM Engine runs on PostgreSQL "
            "only since 0.9.0-alpha.1; SQLite is no longer supported. " + _MAINTENANCE + " Set "
            "DATABASE_URL to a PostgreSQL URL (postgresql+psycopg://…). An existing SQLite database "
            "is carried over with the copy command described in docs/POSTGRESQL_RUNTIME_PLAN.md "
            "(PG-D10)."
        )
    if url.drivername == "postgresql":
        return url.set(drivername=DRIVER)
    if url.drivername != DRIVER:
        raise DatabaseStartupError(
            f"DATABASE_URL uses the driver '{url.drivername}', but RDM Engine connects with "
            f"psycopg 3. " + _MAINTENANCE + f" Start the URL with '{DRIVER}://' or 'postgresql://'."
        )
    return url


@cache
def _engine_for_url(url: str) -> Engine:
    return create_engine(url, pool_pre_ping=True)


def get_engine() -> Engine:
    """Return the pooled engine for the configured database URL."""
    return _engine_for_url(configured_url().render_as_string(hide_password=False))


@cache
def _sessionmaker_for_url(url: str) -> sessionmaker[Session]:
    return sessionmaker(bind=_engine_for_url(url), expire_on_commit=False)


def get_sessionmaker() -> sessionmaker[Session]:
    return _sessionmaker_for_url(configured_url().render_as_string(hide_password=False))


class _SessionFactory:
    """Callable session factory that resolves the engine lazily on each call."""

    def __call__(self) -> Session:
        return get_sessionmaker()()


SessionLocal = _SessionFactory()


def begin_snapshot_read(session: Session) -> None:
    """Hold one database snapshot for the rest of a multi-statement read (REPEATABLE READ).

    PostgreSQL sets the isolation level before a transaction's first statement. A read request has
    often run statements already (resolving its model in a dependency); that read-only transaction
    ends here and the snapshot starts with the next statement, as each earlier read stood alone.
    """
    if session.new or session.dirty or session.deleted:
        raise RuntimeError("A snapshot read cannot begin in a session holding unsaved changes")
    if session.connection().connection.driver_connection.info.transaction_status != (
        TransactionStatus.IDLE
    ):
        session.rollback()
    session.connection().exec_driver_sql("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")


def begin_transaction(session: Session) -> None:
    """Open the session's transaction before its first savepoint.

    PostgreSQL begins at the first statement. SQLite's legacy transaction mode begins only before
    a write, so a SAVEPOINT issued first starts a transaction of its own, which releasing the
    savepoint commits. A transaction whose first write is inside a savepoint (a job's chunk) opens
    here, so it commits or rolls back as one; on SQLite as a writer at once, since a transaction
    that reads first and writes later is refused when another connection writes meanwhile.
    """
    connection = session.connection()
    if (
        connection.dialect.name == "sqlite"
        and not connection.connection.driver_connection.in_transaction
    ):
        connection.exec_driver_sql("BEGIN IMMEDIATE")


def migration_config(url: URL | None = None) -> Config:
    """Alembic's configuration for ``url``, by default the configured database."""
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).resolve().parent / "migrations"))
    rendered = (url or configured_url()).render_as_string(hide_password=False)
    config.set_main_option("sqlalchemy.url", rendered.replace("%", "%%"))
    return config


def _database_label(url: URL) -> str:
    host = url.host or url.query.get("host") or "the default socket"
    return f"PostgreSQL database '{url.database or 'default'}' at '{host}'"


def _failure_reason(exc: BaseException) -> str:
    current: BaseException = exc
    seen: set[int] = set()
    while id(current) not in seen:
        seen.add(id(current))
        next_exception = current.__cause__ or current.__context__
        if next_exception is None:
            break
        current = next_exception
    message = " ".join(str(current).split()) or type(current).__name__
    return message[:1000].rstrip(".")


def _check_collation(connection: Connection, label: str) -> None:
    provider, locale, collate = connection.execute(
        text(
            "SELECT datlocprovider, datlocale, datcollate FROM pg_database "
            "WHERE datname = current_database()"
        )
    ).one()
    if provider == COLLATION_PROVIDER and locale in COLLATION_LOCALES:
        return
    found = {"c": "libc", "b": "builtin", "i": "ICU"}.get(provider, provider)
    raise DatabaseStartupError(
        f"The {label} has the default collation {found} '{locale or collate}', but RDM Engine requires "
        "the ICU root collation 'und', the language-independent Unicode order it sorts and "
        "matches names by (PG-D11). " + _MAINTENANCE + " Create the database with "
        "\"CREATE DATABASE <name> TEMPLATE template0 LOCALE_PROVIDER icu ICU_LOCALE 'und' "
        "LOCALE 'C'\" (or a server initialised with 'initdb --locale-provider=icu "
        "--icu-locale=und'), carry the data over, and point DATABASE_URL at it."
    )


def _check_revision(
    connection: Connection, script: ScriptDirectory, label: str
) -> str | None:
    current = MigrationContext.configure(connection).get_current_revision()
    if current is None:
        return None
    try:
        known = script.get_revision(current) is not None
    except CommandError:
        known = False
    if not known:
        raise DatabaseStartupError(
            f"The {label} is at schema revision '{current}', which this version of RDM Engine "
            f"does not know (its newest is '{script.get_current_head()}'). It was written by a "
            "newer version, or by a SQLite-era revision. " + _MAINTENANCE + " Run the RDM Engine "
            "version that wrote this database, or restore the backup taken before it was "
            "upgraded. Do not edit or stamp the schema manually. " + _ESCALATE
        )
    return current


def _ensure_extension(connection: Connection, label: str) -> None:
    installed = connection.scalar(
        text("SELECT 1 FROM pg_extension WHERE extname = :name"), {"name": REQUIRED_EXTENSION}
    )
    connection.rollback()
    if installed:
        return
    try:
        with connection.begin():
            connection.execute(text(f"CREATE EXTENSION IF NOT EXISTS {REQUIRED_EXTENSION}"))
        return
    except DBAPIError as exc:
        reason = _failure_reason(exc)
    available = connection.scalar(
        text("SELECT 1 FROM pg_available_extensions WHERE name = :name"),
        {"name": REQUIRED_EXTENSION},
    )
    if not available:
        action = (
            "Install the PostgreSQL contrib modules on the database server (pg_trgm ships with "
            "them), then restart RDM Engine."
        )
    else:
        action = (
            f"Run 'CREATE EXTENSION {REQUIRED_EXTENSION};' in this database as its owner or a "
            "superuser, or grant the RDM Engine role CREATE on the database, then restart RDM Engine."
        )
    raise DatabaseStartupError(
        f"The {label} lacks the {REQUIRED_EXTENSION} extension that search indexes need, and RDM "
        f"Engine could not create it. Reason: {reason}. " + _MAINTENANCE + " " + action
    )


def create_database() -> None:
    """Check the configured database and migrate it to the Alembic head (see the module docstring)."""
    url = configured_url()
    label = _database_label(url)
    config = migration_config(url)
    script = ScriptDirectory.from_config(config)
    target_revision = script.get_current_head() or "unknown"
    try:
        with get_engine().connect() as connection:
            _check_collation(connection, label)
            current_revision = _check_revision(connection, script, label) or "unversioned"
            _ensure_extension(connection, label)
    except DatabaseStartupError:
        raise
    except DBAPIError as exc:
        logger.debug("Database connection diagnostic traceback", exc_info=exc)
        raise DatabaseStartupError(
            f"RDM Engine cannot connect to the {label}. Reason: {_failure_reason(exc)}. "
            + _MAINTENANCE
            + " Check that the PostgreSQL server is running (for development: "
            "'scripts/postgres.sh start' from the repository root), that the database exists and "
            "that DATABASE_URL names it with a role allowed to connect, then restart RDM Engine."
        ) from None
    try:
        command.upgrade(config, "head")
    except Exception as exc:
        logger.debug("Database migration diagnostic traceback", exc_info=exc)
        raise DatabaseMigrationError(
            f"Database migration failed for {label}. Current revision: {current_revision}; "
            f"target revision: {target_revision}. Reason: {_failure_reason(exc)}. "
            + _MAINTENANCE
            + " The migration ran in one transaction, so the database is still at its current "
            "revision. Stop every process using this database, take a consistent backup "
            "(pg_dump), then run 'python -m app.cli.database_upgrade' from the backend directory "
            "in the same configured environment. If that command still fails, do not edit or "
            "stamp the schema manually; report this complete message, the application version, "
            "the PostgreSQL server version and the command output."
        ) from None
