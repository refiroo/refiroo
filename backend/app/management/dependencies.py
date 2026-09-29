"""Request-scoped FastAPI dependencies: one session per request and the model a request reads."""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Query
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..engine.model.registry import ModelSnapshot, resolve_model_snapshot, resolve_request_model


def get_session() -> Iterator[Session]:
    """Yield one session per request so a request reads from a single connection."""
    with SessionLocal() as session:
        yield session


DbSession = Annotated[Session, Depends(get_session)]


def active_model_snapshot(session: DbSession) -> ModelSnapshot:
    return resolve_model_snapshot(session)


ActiveModelSnapshot = Annotated[ModelSnapshot, Depends(active_model_snapshot)]


def request_model_snapshot(
    session: DbSession,
    workspace_key: str | None = Query(default=None, alias="workspaceKey"),
    change_set_id: str | None = Query(default=None, alias="changeSetId"),
    publication_id: str | None = Query(default=None, alias="publicationId"),
) -> ModelSnapshot:
    """Resolve the one model authority for a live, change-set or publication read request."""
    return resolve_request_model(session, workspace_key, change_set_id, publication_id)


RequestModelSnapshot = Annotated[ModelSnapshot, Depends(request_model_snapshot)]
