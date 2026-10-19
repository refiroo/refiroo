"""Request-scoped FastAPI dependencies: one session per request and the model a request reads."""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Header, Query
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..engine.model import expected_release
from ..engine.model.registry import (
    ModelSnapshot,
    require_unchanged_releases,
    resolve_model_snapshot,
    resolve_request_model,
)


def get_session() -> Iterator[Session]:
    """Yield one session per request so a request reads from a single connection. Once the handler
    has built its answer, and before it is sent, a read whose model changed meanwhile is refused
    (the read guard, 0.11 N1); the session closes then."""
    with SessionLocal() as session:
        yield session
        require_unchanged_releases(session)


DbSession = Annotated[Session, Depends(get_session, scope="function")]


def default_model_snapshot(session: DbSession) -> ModelSnapshot:
    """The default workspace's model, for the instance-wide resources M3 binds to a workspace's
    model (drafts, release comparisons)."""
    return resolve_model_snapshot(session, None)


DefaultModelSnapshot = Annotated[ModelSnapshot, Depends(default_model_snapshot)]


def request_model_snapshot(
    session: DbSession,
    workspace_key: str | None = Query(default=None, alias="workspaceKey"),
    change_set_id: str | None = Query(default=None, alias="changeSetId"),
    publication_id: str | None = Query(default=None, alias="publicationId"),
) -> ModelSnapshot:
    """Resolve the one model authority for a live, change-set or publication read request: the
    named workspace's model, the default workspace's without one (D6), or the context's release."""
    snapshot = resolve_request_model(session, workspace_key, change_set_id, publication_id)
    expected_release.check(
        session, snapshot.workspace_key, snapshot.release_db_id, change_set_id=change_set_id
    )
    return snapshot


RequestModelSnapshot = Annotated[ModelSnapshot, Depends(request_model_snapshot)]


def expect_model_release(
    session: DbSession,
    expected_model_release_id: str | None = Header(
        default=None,
        alias="X-Expected-Model-Release-Id",
        description=(
            "The model release this request was built on (0.11 M6a). When the workspace, or the "
            "change set, the request addresses resolves another release, the request is refused "
            "with `409 MODEL_RELEASE_CHANGED` and nothing is saved. Optional."
        ),
    ),
) -> None:
    """Keep the release a request names on its session, for the write units and the request's
    snapshot to check (D63, D64)."""
    expected_release.expect(session, expected_model_release_id)


# Every route of the management API takes the header.
MANAGEMENT_DEPENDENCIES = [Depends(expect_model_release)]
