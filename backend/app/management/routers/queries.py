"""The model-aware object query (Base 0.9 Q3, INTEGRATION_API §Q3)."""

from fastapi import APIRouter

from ...engine.model.registry import resolve_request_model
from ...engine.workspaces.catalogue import resolve_workspace
from ...models.queries import ModelQuery
from ..access import (
    WORKSPACE_PATH,
    AuthorizedRoute,
    requires,
)
from ..dependencies import DbSession
from ..projections.model_query import query_objects
from ..schemas.queries import ObjectQueryPage

router = APIRouter(route_class=AuthorizedRoute, prefix="/api/v1", tags=["objects", "queries"])


@router.post("/workspaces/{workspace_key}/queries/objects", response_model=ObjectQueryPage)
@requires("records.read", at=WORKSPACE_PATH)
def query_workspace_objects(
    workspace_key: str, payload: ModelQuery, session: DbSession
) -> ObjectQueryPage:
    """Records of one object type matching criteria over their fields, their ancestors and one
    relation hop, with the fields and related records each item returns. A read: it changes
    nothing. Model-dependent mistakes are ``422 INVALID_QUERY`` with ``details.path``, a JSON
    pointer into the body."""
    workspace = resolve_workspace(session, workspace_key)
    snapshot = resolve_request_model(
        session, workspace.key, payload.context.changeSetId, payload.context.publicationId
    )
    return query_objects(session, snapshot.model, payload, workspace_key=workspace.key)
