from collections.abc import Iterator
from functools import cache
from pathlib import Path
from typing import Annotated

from alembic import command
from alembic.config import Config
from fastapi import Depends
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from .config import database_url


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


def get_session() -> Iterator[Session]:
    """Yield one session per request so a request reads from a single connection."""
    with SessionLocal() as session:
        yield session


DbSession = Annotated[Session, Depends(get_session)]


def create_database() -> None:
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).resolve().parent / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url().replace("%", "%%"))
    command.upgrade(config, "head")
