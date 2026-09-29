import logging
from functools import cache
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, create_engine, make_url
from sqlalchemy.orm import Session, sessionmaker

from .config import database_url

logger = logging.getLogger(__name__)


@cache
def _engine_for_url(url: str) -> Engine:
    return create_engine(url)


def get_engine() -> Engine:
    """Return the engine for the currently loaded database URL."""
    return _engine_for_url(database_url())


@cache
def _sessionmaker_for_url(url: str) -> sessionmaker[Session]:
    return sessionmaker(bind=_engine_for_url(url), expire_on_commit=False)


def get_sessionmaker() -> sessionmaker[Session]:
    return _sessionmaker_for_url(database_url())


class _SessionFactory:
    """Callable session factory that resolves the engine lazily on each call."""

    def __call__(self) -> Session:
        return get_sessionmaker()()


SessionLocal = _SessionFactory()


def begin_snapshot_read(session: Session) -> None:
    """Hold one database snapshot for the rest of a multi-statement read.

    SQLite's legacy transaction mode does not BEGIN on SELECT, so a read that resolves its model,
    rows, counts and concurrency tokens in several statements begins explicitly; PostgreSQL reads
    under repeatable read.
    """
    connection = session.connection()
    if connection.dialect.name == "sqlite":
        if not connection.connection.driver_connection.in_transaction:
            connection.exec_driver_sql("BEGIN")
    elif connection.dialect.name == "postgresql":
        connection.exec_driver_sql("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")


class DatabaseMigrationError(RuntimeError):
    """An operator-actionable database migration failure safe to show without a traceback."""


def _migration_config() -> Config:
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).resolve().parent / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url().replace("%", "%%"))
    return config


def _database_label() -> str:
    url = make_url(database_url())
    if url.get_backend_name() == "sqlite":
        database = url.database or ":memory:"
        if database != ":memory:":
            database = str(Path(database).resolve())
        return f"SQLite database '{database}'"
    host = url.host or "configured host"
    database = url.database or "configured database"
    return f"{url.get_backend_name()} database '{database}' at '{host}'"


def _failure_reason(exc: Exception) -> str:
    current: BaseException = exc
    seen: set[int] = set()
    while id(current) not in seen:
        seen.add(id(current))
        next_exception = current.__cause__ or current.__context__
        if next_exception is None:
            break
        current = next_exception
    message = " ".join(str(current).split()) or type(current).__name__
    return message[:1000]


def create_database() -> None:
    config = _migration_config()
    target_revision = ScriptDirectory.from_config(config).get_current_head() or "unknown"
    try:
        with get_engine().connect() as connection:
            current_revision = (
                MigrationContext.configure(connection).get_current_revision() or "unversioned"
            )
    except Exception:  # noqa: BLE001 - this boundary must describe unreadable databases
        current_revision = "unreadable"
    try:
        command.upgrade(config, "head")
    except Exception as exc:
        logger.debug("Database migration diagnostic traceback", exc_info=exc)
        reason = _failure_reason(exc).rstrip(".")
        raise DatabaseMigrationError(
            f"Database migration failed for {_database_label()}. Current revision: "
            f"{current_revision}; target revision: {target_revision}. Reason: "
            f"{reason}. RDM Engine startup will remain in maintenance mode and /health "
            "will return HTTP 503. Stop every process using this database, take a consistent backup, "
            "then run 'python -m app.cli.database_upgrade' from the backend directory in the same "
            "configured environment. If that command still fails, do not edit or stamp the schema "
            "manually; report this complete message, the application version, database engine, and "
            "the command output."
        ) from None
