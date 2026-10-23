"""Request-scoped FastAPI dependencies: one session per request, the caller, and the model a request
reads."""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Header, Query, Request
from fastapi.openapi.models import OAuthFlowClientCredentials, OAuthFlows
from fastapi.security import OAuth2
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..engine.identity.authentication import Principal, authenticate, require_started
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


# The scheme the OpenAPI document declares: a client obtains a token with its credentials at the
# token endpoint (ADR-043); the browser's sign-in (I2) issues the same token.
bearer = OAuth2(
    flows=OAuthFlows(
        clientCredentials=OAuthFlowClientCredentials(
            tokenUrl="/oauth/token",
            scopes={
                "management": "The management API (the default)",
                "consumer": "The consumer APIs",
            },
        )
    ),
    scheme_name="engineOAuth",
    description=(
        "An access token issued by the engine: `Authorization: Bearer <token>`. Every route needs "
        "one except /health, /health/live, /openapi.json, /docs and the OAuth endpoints."
    ),
    auto_error=False,
)


def authenticated(
    request: Request,
    session: DbSession,
    authorization: Annotated[str | None, Depends(bearer)],
) -> Principal:
    """The caller of a management route, from its ``management`` token (0.12 I1). Until Z1 every
    active principal may use every route."""
    principal = authenticate(
        session, request.app.state.identity_settings, authorization, "management"
    )
    request.state.principal = principal
    return principal


CurrentPrincipal = Annotated[Principal, Depends(authenticated)]


# Every route of the management API needs a token and takes the header. In maintenance mode it
# answers 503 before a session is opened or a token read.
MANAGEMENT_DEPENDENCIES = [
    Depends(require_started),
    Depends(authenticated),
    Depends(expect_model_release),
]
