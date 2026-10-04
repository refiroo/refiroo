"""The consumer API's routes (Base 0.9 C2 onward).

Each route resolves the definition from the active release (``{apiKey}`` and ``v{contractVersion}``),
checks the request's parameters against the names it serves, resolves the workspace and reads live
data through ``engine/reads/consumer_objects`` and ``consumer_lists``. Every response names the
workspace it read in the ``RDM-Workspace`` header (C-D23). The routes stay out of the management
OpenAPI document; C6 generates one document per definition.
"""

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from ..common.pagination import PageRequest
from ..db import SessionLocal
from ..engine.model.registry import resolve_model_snapshot
from ..engine.reads.consumer_lists import consumer_list, read_consumer_list
from ..engine.reads.consumer_objects import consumer_definition, read_consumer_object
from ..engine.reads.consumer_parameters import consumer_filter, split_values
from ..engine.workspaces.catalogue import resolve_workspace
from ..errors import ApiError, api_error
from ..models.database import Workspace
from ..models.schema import ConsumerApiDefinition, ConsumerList

PREFIX = "/api/consumer"
WORKSPACE_HEADER = "RDM-Workspace"
# The names that select a list's page (ADR-030, C-D30).
_PAGING = frozenset({"pageSize", "cursor", "position", "from", "seek", "includeTotal"})
_DEFAULT_PAGE_SIZE = 20
_MAX_PAGE_SIZE = 100
# The shared paging refusals answer 400 here, the consumer tier's status for a request error.
_PAGING_CODES = frozenset({"INVALID_CURSOR", "CONFLICTING_PAGE_PARAMETERS", "INVALID_POSITION", "INVALID_SEEK"})


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
    """Get by ID: the definition's shared object for the record with this object ID, narrowed by the
    definition's parameters (C-D31)."""
    model = resolve_model_snapshot(session).model
    definition = consumer_definition(model, api_key, contract_version)
    parameters = _Parameters.check(request, definition, None)
    workspace = _workspace(session, parameters.single("workspace"))
    return _answer(
        response,
        workspace,
        lambda: read_consumer_object(
            session,
            model,
            definition,
            workspace.key,
            object_id,
            consumer_filter(model, definition, workspace.key, parameters.definition),
        ),
    )


@router.get("/{api_key}/v{contract_version}/lists/{list_key}")
@reads_own_parameters
def get_list(
    api_key: str, contract_version: str, list_key: str, request: Request, response: Response, session: DbSession
) -> dict[str, Any]:
    """A page of the definition's list ``list_key``: the records of its type, below the parent
    values when given, narrowed by the definition's parameters (C-D27–C-D31)."""
    model = resolve_model_snapshot(session).model
    definition = consumer_definition(model, api_key, contract_version)
    declared = consumer_list(definition, list_key)
    parameters = _Parameters.check(request, definition, declared)
    page_size, page = _page(parameters)
    workspace = _workspace(session, parameters.single("workspace"))
    return _answer(
        response,
        workspace,
        lambda: read_consumer_list(
            session,
            model,
            definition,
            declared,
            workspace_key=workspace.key,
            parent_ids=parameters.parents,
            narrowed=consumer_filter(model, definition, workspace.key, parameters.definition),
            parameters=parameters.definition,
            page=page,
            page_size=page_size,
        ),
    )


def _answer(response: Response, workspace: Workspace, read: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    """The read's answer, naming the workspace in the header, on a refusal as well."""
    response.headers[WORKSPACE_HEADER] = workspace.key
    try:
        return read()
    except ApiError as exc:
        if exc.status == 422 and exc.code in _PAGING_CODES:
            exc.status = 400
        exc.headers = {**(exc.headers or {}), WORKSPACE_HEADER: workspace.key}
        raise


@dataclass(frozen=True)
class _Parameters:
    """A request's query parameters, checked against the names its route serves."""

    raw: dict[str, list[str]]
    # Definition parameter name to its values, split (C-D32).
    definition: dict[str, list[str]]
    parents: list[str]

    @classmethod
    def check(
        cls, request: Request, definition: ConsumerApiDefinition, declared: ConsumerList | None
    ) -> _Parameters:
        """Refuse a name the API does not know (``UNKNOWN_PARAMETER``), then one it knows that this
        route does not apply (``PARAMETER_NOT_SUPPORTED``): a paging name on get by ID, or a list's
        parent parameter on get by ID or on another list."""
        parent = declared.parentParameter.name if declared and declared.parentParameter else None
        applied = {"workspace", *definition.parameters}
        if declared is not None:
            applied |= _PAGING
        if parent is not None:
            applied.add(parent)
        known = applied | _PAGING | {
            item.parentParameter.name for item in definition.lists if item.parentParameter is not None
        }
        raw = {name: request.query_params.getlist(name) for name in sorted(set(request.query_params))}
        unknown = [name for name in raw if name not in known]
        if unknown:
            raise api_error(
                400,
                "UNKNOWN_PARAMETER",
                f"Unknown query parameter '{unknown[0]}'",
                {"parameters": unknown, "path": f"/query/{unknown[0]}"},
            )
        unsupported = [name for name in raw if name not in applied]
        if unsupported:
            raise api_error(
                400,
                "PARAMETER_NOT_SUPPORTED",
                f"Parameter '{unsupported[0]}' is not supported on this read",
                {"parameters": unsupported, "path": f"/query/{unsupported[0]}"},
            )
        # On its list, a parent parameter sharing a definition parameter's name addresses the parent.
        return cls(
            raw=raw,
            definition={
                name: split_values(values)
                for name, values in raw.items()
                if name in definition.parameters and name != parent
            },
            parents=list(dict.fromkeys(split_values(raw[parent]))) if parent in raw else [],
        )

    def single(self, name: str) -> str | None:
        values = self.raw.get(name)
        return values[-1] if values else None


def _page(parameters: _Parameters) -> tuple[int, PageRequest]:
    """The page size and the page a list read asks for (C-D30)."""
    raw_size = parameters.single("pageSize")
    try:
        page_size = _DEFAULT_PAGE_SIZE if raw_size is None else int(raw_size)
    except ValueError:
        page_size = 0
    if not 1 <= page_size <= _MAX_PAGE_SIZE:
        raise api_error(
            400,
            "INVALID_PAGE_SIZE",
            f"pageSize must be a whole number from 1 to {_MAX_PAGE_SIZE}",
            {"path": "/query/pageSize"},
        )
    raw_position = parameters.single("position")
    try:
        position = None if raw_position is None else int(raw_position)
    except ValueError:
        raise api_error(
            400, "INVALID_POSITION", "position must be a whole number", {"path": "/query/position"}
        ) from None
    start = _choice(parameters, "from", {"start": False, "end": True}, False)
    include_total = _choice(parameters, "includeTotal", {"false": False, "true": True}, False)
    try:
        page = PageRequest(
            cursor=parameters.single("cursor"),
            position=position,
            seek=parameters.single("seek"),
            from_end=start,
            include_total=include_total,
        )
    except ApiError as exc:
        exc.status = 400
        raise
    return page_size, page


def _choice(parameters: _Parameters, name: str, choices: dict[str, bool], default: bool) -> bool:
    raw = parameters.single(name)
    if raw is None:
        return default
    if raw not in choices:
        raise api_error(
            400,
            "INVALID_PAGE_PARAMETER",
            f"{name} must be one of {', '.join(choices)}",
            {"path": f"/query/{name}"},
        )
    return choices[raw]


def _workspace(session: Session, key: str | None) -> Workspace:
    """The named workspace, or the deployment's default; a retired one is not served."""
    workspace = resolve_workspace(session, key)
    if workspace.status == "retired":
        raise api_error(404, "WORKSPACE_NOT_FOUND", f"Workspace '{workspace.key}' not found")
    return workspace
