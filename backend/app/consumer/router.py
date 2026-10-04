"""The consumer API's routes (Base 0.9 C2 onward).

Each route resolves the definition from the active release (``{apiKey}`` and ``v{contractVersion}``),
checks the request's parameters against the definition, resolves the workspace and reads live data
through ``engine/reads/consumer_objects``. Every response names the workspace it read in the
``RDM-Workspace`` header (C-D23). The routes stay out of the management OpenAPI document; C6
generates one document per definition.
"""

from collections.abc import Iterator
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..engine.model.registry import resolve_model_snapshot
from ..engine.reads.consumer_objects import consumer_definition, read_consumer_object
from ..engine.workspaces.catalogue import resolve_workspace
from ..errors import ApiError, api_error
from ..models.database import Workspace
from ..models.schema import ConsumerApiDefinition

PREFIX = "/api/consumer"
WORKSPACE_HEADER = "RDM-Workspace"
# The parameters get by ID reads itself.
_OBJECT_PARAMETERS = frozenset({"workspace"})


def _session() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session


DbSession = Annotated[Session, Depends(_session)]

router = APIRouter(prefix=PREFIX, tags=["consumer"], include_in_schema=False)


def reads_own_parameters[F](endpoint: F) -> F:
    """Mark a route that checks its query parameters itself, against its definition: the app-wide
    unknown-parameter check (``management/query_parameters``) leaves it alone."""
    endpoint.reads_own_parameters = True  # type: ignore[attr-defined]
    return endpoint


@router.get("/{api_key}/v{contract_version}/objects/{object_id}")
@reads_own_parameters
def get_object(
    api_key: str, contract_version: str, object_id: str, request: Request, response: Response, session: DbSession
) -> dict[str, Any]:
    """Get by ID: the definition's shared object for the record with this object ID."""
    model = resolve_model_snapshot(session).model
    definition = consumer_definition(model, api_key, contract_version)
    _check_parameters(request, definition, _OBJECT_PARAMETERS)
    workspace = _workspace(session, request.query_params.get("workspace"))
    response.headers[WORKSPACE_HEADER] = workspace.key
    try:
        return read_consumer_object(session, model, definition, workspace.key, object_id)
    except ApiError as exc:
        exc.headers = {**(exc.headers or {}), WORKSPACE_HEADER: workspace.key}
        raise


def _check_parameters(request: Request, definition: ConsumerApiDefinition, accepted: frozenset[str]) -> None:
    """Refuse a parameter the route does not know, then a declared one it does not apply yet."""
    names = sorted(set(request.query_params))
    unknown = [name for name in names if name not in accepted and name not in definition.parameters]
    if unknown:
        raise api_error(
            400,
            "UNKNOWN_PARAMETER",
            f"Unknown query parameter '{unknown[0]}'",
            {"parameters": unknown, "path": f"/query/{unknown[0]}"},
        )
    # C2 applies no parameter kind yet; C3 applies them, and from then on only a parameter that does
    # not apply to the route is refused.
    unsupported = [name for name in names if name in definition.parameters]
    if unsupported:
        raise api_error(
            400,
            "PARAMETER_NOT_SUPPORTED",
            f"Parameter '{unsupported[0]}' is not supported on this read",
            {"parameters": unsupported, "path": f"/query/{unsupported[0]}"},
        )


def _workspace(session: Session, key: str | None) -> Workspace:
    """The named workspace, or the deployment's default; a retired one is not served."""
    workspace = resolve_workspace(session, key)
    if workspace.status == "retired":
        raise api_error(404, "WORKSPACE_NOT_FOUND", f"Workspace '{workspace.key}' not found")
    return workspace
