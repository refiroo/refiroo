"""The consumer API's routes (Base 0.9 C2 onward).

Each route resolves the definition from the active release (``{consumerApi}`` and ``v{contractVersion}``),
checks the request's parameters against the names it serves, resolves the workspace and reads its
live data, or with ``publication`` one of its publications (C6a), through
``engine/reads/consumer_objects``, ``consumer_lists``, ``consumer_xref`` and ``consumer_resolve``.
Every response names the workspace it read in the ``RDM-Workspace`` header (C-D23), and a pinned
read's the publication in ``RDM-Publication`` (C-D63), and a read dated by ``asOf`` the dated types
in ``RDM-As-Of-Applied`` (C16, C-D78). A ``GET`` answers an ``ETag`` and honours
``If-None-Match`` (C-D65). The routes stay out of the management OpenAPI document: each definition
serves its own at ``…/openapi.json``, and ``GET /api/consumer`` lists them (C6b, C-D69).
"""

import json
import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field, replace
from datetime import date
from typing import Annotated, Any
from urllib.parse import unquote_plus, urlencode

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..common.cursors import decode_cursor, signed_scope
from ..common.pagination import PageRequest, paginate_sequence
from ..common.route_markers import reads_own_parameters
from ..db import SessionLocal
from ..engine.authorization.permissions import permissions_of
from ..engine.identity.authentication import authenticate, require_started
from ..engine.model.consumer_definitions import consumer_api as declared_api
from ..engine.model.consumer_definitions import consumer_apis
from ..engine.model.consumer_openapi import consumer_openapi, consumer_openapi_path
from ..engine.model.registry import (
    ModelSnapshot,
    require_unchanged_releases,
    resolve_model_snapshot,
    resolve_pinned_release,
)
from ..engine.reads.consumer_events import (
    AFTER_POSITION,
    PAGE_SIZES,
    SORT,
    EventsRequest,
    cursor_filters,
    cursor_scope,
    derived_head,
    read_consumer_events,
)
from ..engine.reads.consumer_lists import PAGE_SIZE, consumer_list, read_consumer_list
from ..engine.reads.consumer_objects import consumer_definition, read_consumer_object
from ..engine.reads.consumer_parameters import TARGET_PREFIX, consumer_filter, target_names
from ..engine.reads.consumer_publications import read_publications
from ..engine.reads.consumer_resolve import ResolveItem, item_error, read_resolve
from ..engine.reads.consumer_source import PUBLICATION_SCOPE, ConsumerSource
from ..engine.reads.consumer_xref import read_xref, xref_terms
from ..engine.workspaces.catalogue import resolve_workspace
from ..errors import ApiError, api_error
from ..models.database import Publication, Workspace
from ..models.schema import ConsumerApiDefinition, EngineModel
from .etag import entity_tag, none_match

PREFIX = "/api/consumer"
WORKSPACE_HEADER = "RDM-Workspace"
# The release the index and an OpenAPI document describe (0.11 D27), as GET /api/v1/model names it.
RELEASE_HEADER = "X-Model-Release-Id"
PUBLICATION_HEADER = "RDM-Publication"
AS_OF_HEADER = "RDM-As-Of-Applied"
# A business date: a calendar day, written YYYY-MM-DD and nothing else (C-D79).
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# The value of ``publication`` that reads the workspace's active publication (C-D61).
LATEST = "latest"
# The names that select a list's page (ADR-030, C-D30).
_PAGING = frozenset({"pageSize", "cursor", "position", "from", "seek", "includeTotal"})
# The names each route serves besides the definition's parameters. XREF pages by score, which no
# caller seeks, and always counts its total (C-D39); with expect=one it reads no page (C-D40).
_OBJECT = frozenset({"workspace", "publication", "asOf"})
_LIST = _OBJECT | _PAGING
_XREF_ONE = _OBJECT | {"query", "expect"}
_XREF = _XREF_ONE | (_PAGING - {"seek", "includeTotal"})
# The publications list reads live data in the order of publication, which no caller seeks (C-D66).
_PUBLICATIONS = frozenset({"workspace"}) | (_PAGING - {"seek"})
# The pull feed pages by position and cursor (C-D91) and chooses its payload (C-D7 revised).
_EVENTS = frozenset({"workspace", "event", "after", "cursor", "pageSize", "payload"})
# Every name a route of the API serves.
_ROUTE_NAMES = _LIST | _XREF | _EVENTS
# The names a batch resolve item holds besides the definition's parameters (C-D47).
_ITEM = frozenset({"ref", "query", "id"})
_REF_LENGTH = (1, 200)
_MIN_PAGE_SIZE, _MAX_PAGE_SIZE, _DEFAULT_PAGE_SIZE = PAGE_SIZE
# The shared paging refusals answer 400 here, the consumer tier's status for a request error.
_PAGING_CODES = frozenset({"INVALID_CURSOR", "CONFLICTING_PAGE_PARAMETERS", "INVALID_POSITION", "INVALID_SEEK"})


def _session() -> Iterator[Session]:
    """One session per request; a read whose model changed meanwhile is refused before it answers
    (the read guard, 0.11 N1)."""
    with SessionLocal() as session:
        yield session
        require_unchanged_releases(session)


async def _body(request: Request) -> bytes:
    return await request.body()


DbSession = Annotated[Session, Depends(_session, scope="function")]
Body = Annotated[bytes, Depends(_body)]

def _started(request: Request) -> None:
    require_started(request.app.state.maintenance)


# The routes that describe the consumer APIs rather than serve their data. The index takes a
# management token too, so the browser, holding one, shows it (D266). Each definition's OpenAPI
# document needs no token at all (D412), like the management API's: it is the contract a client
# needs before it can ask for one, and the API reference page (``/docs``) loads it unauthenticated.
OPENAPI_DOCUMENT = f"{PREFIX}/{{consumer_api}}/v{{contract_version}}/openapi.json"
DESCRIBING = {PREFIX}


def _authenticated(request: Request, session: DbSession) -> None:
    """Every consumer route needs a ``consumer`` token (0.12 I1, D260), the index a
    ``consumer`` or ``management`` one (D266), an OpenAPI document none (D412). After the token,
    the workspace (its own ``404``), then the grant (0.12 Z3, D307–D309): a ``consumer`` token reads ``{consumerApi}`` only with a
    grant of it in the workspace; a ``management`` token reads the describing routes with Browse
    there, as the model reads do. The index filters what it lists itself (``request.state``)."""
    route = request.scope.get("route")
    if getattr(route, "path", None) == OPENAPI_DOCUMENT:
        return
    describing = getattr(route, "path", None) in DESCRIBING
    principal = authenticate(
        session,
        request.app.state.identity_settings,
        request.headers.get("Authorization"),
        ("consumer", "management") if describing else "consumer",
    )
    workspace = _workspace(session, request.query_params.get("workspace"))
    permissions = permissions_of(session, principal.kind, principal.row_id, principal.generation)
    # What the index lists: every API for a management caller, the granted ones for a consumer.
    request.state.listed_apis = (
        None if principal.audience == "management" else permissions.consumer_apis_in(workspace.key)
    )
    if principal.audience == "management":
        if not permissions.allows("browse", workspace.key):
            raise api_error(
                403,
                "FORBIDDEN",
                f"Reading the model in workspace '{workspace.key}' needs Browse",
                {"action": "model.read", "groups": ["browse"], "workspaceKey": workspace.key},
            )
        return
    consumer_api = request.path_params.get("consumer_api")
    if consumer_api is not None and not permissions.reads_consumer_api(consumer_api, workspace.key):
        raise api_error(
            403,
            "FORBIDDEN",
            f"Reading consumer API '{consumer_api}' in workspace '{workspace.key}' needs a grant of it",
            {"consumerApi": consumer_api, "workspaceKey": workspace.key},
        )


router = APIRouter(
    prefix=PREFIX, tags=["consumer"], include_in_schema=False,
    dependencies=[Depends(_started), Depends(_authenticated)],
)


@dataclass(frozen=True)
class _Read:
    """What a read reads: the model and definition that shape it, the source of its rows, its
    parameters as checked against that definition, and its entity tag."""

    model: EngineModel
    definition: ConsumerApiDefinition
    source: ConsumerSource
    parameters: _Parameters
    tag: str
    # The filter, once built: the answer's ``RDM-As-Of-Applied`` header reads it.
    built: dict[str, Any] = field(default_factory=dict, compare=False)

    def narrowed(self, session: Session) -> Any:
        if "filter" not in self.built:
            self.built["filter"] = consumer_filter(
                session, self.model, self.definition, self.source, self.parameters.definition, self.parameters.as_of
            )
        return self.built["filter"]


def _reading(
    session: Session,
    active: ModelSnapshot,
    definition: ConsumerApiDefinition,
    parameters: _Parameters,
    workspace: Workspace,
    recheck: Callable[[ConsumerApiDefinition], _Parameters],
) -> Callable[[], _Read]:
    """How the read is resolved, run where its refusals name the workspace: live data, shaped by the
    active release; or the publication ``publication`` names, shaped by the release it was published
    under, which must declare this API at this contract version (C-D60). ``recheck`` checks the
    parameters against that release's definition when it differs from the active one."""

    def resolve() -> _Read:
        value = parameters.single("publication")
        if value is None:
            tag = entity_tag(
                ("live", workspace.key, str(workspace.feed_position), active.release_id), definition.contractVersion
            )
            return _Read(active.model, definition, ConsumerSource(workspace.key), parameters, tag)
        publication = _publication(session, workspace, value, parameters.single("cursor"))
        pinned = resolve_pinned_release(session, publication.model_release_id)
        declared = declared_api(pinned.model, definition.key)
        if declared is None or declared.contractVersion != definition.contractVersion:
            declared_version = declared.contractVersion if declared is not None else None
            raise api_error(
                409,
                "PUBLICATION_CONTRACT_MISMATCH",
                f"Publication '{publication.id}' was published under a model release that "
                + (
                    f"declares contract version {declared_version} of this API"
                    if declared is not None
                    else "does not declare this API"
                )
                + f", not version {definition.contractVersion}; read a publication made under this version",
                {"publication": publication.id, "contractVersion": declared_version},
            )
        checked = parameters if declared == definition else recheck(declared)
        tag = entity_tag(("publication", publication.id, pinned.release_id), declared.contractVersion)
        return _Read(pinned.model, declared, ConsumerSource(workspace.key, publication.id), checked, tag)

    return resolve


def _publication(session: Session, workspace: Workspace, value: str, cursor: str | None) -> Publication:
    """The publication of the workspace that ``value`` names (C-D62). ``latest`` is the workspace's
    active one (C-D61), except that a cursor issued by a pinned read continues in its own publication
    (C-D64)."""
    publication_id = value
    if value == LATEST:
        scope = signed_scope(cursor) if cursor is not None else None
        if scope is not None and PUBLICATION_SCOPE in scope:
            publication_id = scope.rsplit(PUBLICATION_SCOPE, 1)[1]
        elif workspace.active_publication_id is None:
            raise api_error(
                404,
                "PUBLICATION_NOT_FOUND",
                f"Workspace '{workspace.key}' has no current publication to read as '{LATEST}'",
                {"publication": LATEST},
            )
        else:
            publication_id = workspace.active_publication_id
    publication = session.scalar(
        select(Publication).where(Publication.id == publication_id, Publication.workspace_key == workspace.key)
    )
    if publication is None:
        raise api_error(
            404,
            "PUBLICATION_NOT_FOUND",
            f"Publication '{value}' not found in workspace '{workspace.key}'",
            {"publication": value},
        )
    return publication


@router.get("/{consumer_api}/v{contract_version}/objects/{object_id}", response_model=None)
@reads_own_parameters
def get_object(
    consumer_api: str, contract_version: str, object_id: str, request: Request, response: Response, session: DbSession
) -> dict[str, Any] | Response:
    """Get by ID: the definition's shared object for the record with this object ID, narrowed by the
    definition's parameters (C-D31)."""
    active = resolve_model_snapshot(session, request.query_params.get("workspace"))
    definition = consumer_definition(active.model, consumer_api, contract_version)
    _offered(definition, "objects")

    def check(declared: ConsumerApiDefinition) -> _Parameters:
        return _Parameters.check(request, declared, serves=_OBJECT)

    parameters = check(definition)
    workspace = _workspace(session, parameters.single("workspace"))
    return _answer(
        request,
        response,
        workspace,
        _reading(session, active, definition, parameters, workspace, check),
        lambda read: read_consumer_object(
            session, read.model, read.definition, read.source, object_id, read.narrowed(session)
        ),
        dated=lambda _read, body: [body["objectType"]],
    )


@router.get("/{consumer_api}/v{contract_version}/lists/{list_key}", response_model=None)
@reads_own_parameters
def get_list(
    consumer_api: str, contract_version: str, list_key: str, request: Request, response: Response, session: DbSession
) -> dict[str, Any] | Response:
    """A page of the definition's list ``list_key``: the records of its type, below the parent
    values when given, narrowed by the definition's parameters (C-D27–C-D31)."""
    active = resolve_model_snapshot(session, request.query_params.get("workspace"))
    definition = consumer_definition(active.model, consumer_api, contract_version)

    def check(declared: ConsumerApiDefinition) -> _Parameters:
        listed = consumer_list(declared, list_key)
        parent = listed.parentParameter.name if listed.parentParameter else None
        return _Parameters.check(request, declared, serves=_LIST, parent=parent)

    parameters = check(definition)
    page_size, page = _page(parameters)
    workspace = _workspace(session, parameters.single("workspace"))

    def read(current: _Read) -> dict[str, Any]:
        return read_consumer_list(
            session,
            current.model,
            current.definition,
            consumer_list(current.definition, list_key),
            source=current.source,
            parent_ids=current.parameters.parents,
            narrowed=current.narrowed(session),
            parameters=current.parameters.definition,
            page=page,
            page_size=page_size,
        )

    return _answer(
        request, response, workspace, _reading(session, active, definition, parameters, workspace, check), read
    )


@router.get("/{consumer_api}/v{contract_version}/xref", response_model=None)
@reads_own_parameters
def get_xref(
    consumer_api: str, contract_version: str, request: Request, response: Response, session: DbSession
) -> dict[str, Any] | Response:
    """XREF: the exposed objects the query's terms match, scored by the definition's ``match`` and
    narrowed by its parameters, a page of them or with ``expect=one`` the single best (C-D34–C-D43)."""
    active = resolve_model_snapshot(session, request.query_params.get("workspace"))
    definition = consumer_definition(active.model, consumer_api, contract_version)
    _offered(definition, "xref")
    expect = request.query_params.getlist("expect")
    expect_one = _expect_one(expect[-1] if expect else None)

    def check(declared: ConsumerApiDefinition) -> _Parameters:
        return _Parameters.check(request, declared, serves=_XREF_ONE if expect_one else _XREF)

    parameters = check(definition)
    terms = xref_terms(parameters.listed.get("query", []))
    page_size, page = (_DEFAULT_PAGE_SIZE, PageRequest()) if expect_one else _page(parameters)
    workspace = _workspace(session, parameters.single("workspace"))
    return _answer(
        request,
        response,
        workspace,
        _reading(session, active, definition, parameters, workspace, check),
        lambda read: read_xref(
            session,
            read.model,
            read.definition,
            source=read.source,
            terms=terms,
            narrowed=read.narrowed(session),
            parameters=read.parameters.definition,
            expect_one=expect_one,
            page=page,
            page_size=page_size,
        ),
        dated=lambda read, body: body.get("asOfApplied", list(read.built["filter"].as_of_applied)),
    )


@router.post("/{consumer_api}/v{contract_version}/resolve", response_model=None)
@reads_own_parameters
def post_resolve(
    consumer_api: str, contract_version: str, request: Request, response: Response, session: DbSession, body: Body
) -> dict[str, Any] | Response:
    """Batch resolve: each item as ``xref?expect=one`` (by ``query``) or get by ID (by ``id``), with
    the definition's parameters from ``defaults`` and the item, its outcome the single read's answer
    (C-D47–C-D50). A read: the body only carries the items. It answers no ETag: HTTP answers ``304``
    to ``GET`` only (C-D65)."""
    active = resolve_model_snapshot(session, request.query_params.get("workspace"))
    definition = consumer_definition(active.model, consumer_api, contract_version)
    _offered(definition, "resolve")

    def check(declared: ConsumerApiDefinition) -> _Parameters:
        return _Parameters.check(request, declared, serves=_OBJECT, applies_definition=False)

    parameters = check(definition)
    workspace = _workspace(session, parameters.single("workspace"))
    return _answer(
        request,
        response,
        workspace,
        _reading(session, active, definition, parameters, workspace, check),
        lambda read: read_resolve(
            session,
            read.model,
            read.definition,
            read.source,
            _resolve_items(body, read.definition, request.app.state.consumer_resolve_max_items),
            read.parameters.as_of,
        ),
        tagged=False,
    )


@router.get("/{consumer_api}/v{contract_version}/publications", response_model=None)
@reads_own_parameters
def get_publications(
    consumer_api: str, contract_version: str, request: Request, response: Response, session: DbSession
) -> dict[str, Any] | Response:
    """The workspace's publications, newest first, each with the ``eventSequence`` to follow changes
    from after reading it (C-D66)."""
    active = resolve_model_snapshot(session, request.query_params.get("workspace"))
    definition = consumer_definition(active.model, consumer_api, contract_version)
    parameters = _Parameters.check(request, definition, serves=_PUBLICATIONS, applies_definition=False)
    page_size, page = _page(parameters)
    workspace = _workspace(session, parameters.single("workspace"))

    def live() -> _Read:
        tag = entity_tag(
            ("live", workspace.key, str(workspace.feed_position), active.release_id), definition.contractVersion
        )
        return _Read(active.model, definition, ConsumerSource(workspace.key), parameters, tag)

    return _answer(
        request, response, workspace, live, lambda _read: read_publications(session, workspace.key, page, page_size)
    )


@router.get("/{consumer_api}/v{contract_version}/events", response_model=None)
@reads_own_parameters
def get_events(
    consumer_api: str, contract_version: str, request: Request, response: Response, session: DbSession
) -> dict[str, Any] | Response:
    """The pull feed: the definition's events in the workspace, in position order, from a position
    or a cursor, narrowed by ``event`` and the definition's parameters, with each object or its
    identity only (C10, C-D88–C-D92, C-D7 revised). The read is one snapshot, so ``stateAt`` is the
    position its objects show."""
    session.connection(execution_options={"isolation_level": "REPEATABLE READ"})
    active = resolve_model_snapshot(session, request.query_params.get("workspace"))
    definition = consumer_definition(active.model, consumer_api, contract_version)
    if not definition.events:
        raise api_error(
            404,
            "EVENTS_NOT_DECLARED",
            f"Consumer API '{definition.key}' declares no events at contract version {definition.contractVersion}",
        )
    parameters = _Parameters.check(request, definition, serves=_EVENTS, crosswalk=False)
    workspace = _workspace(session, parameters.single("workspace"))
    asked = _events_request(parameters, definition, workspace.key)
    derived, _start = derived_head(session, workspace.key)

    def live() -> _Read:
        # The derived head and the live one: full objects and parameters read live data, which a
        # write changes before its event is derived (0.9 R-F13, C-D65).
        tag = entity_tag(
            ("events", workspace.key, str(derived), str(workspace.feed_position), active.release_id),
            definition.contractVersion,
        )
        return _Read(active.model, definition, ConsumerSource(workspace.key), parameters, tag)

    return _answer(
        request,
        response,
        workspace,
        live,
        lambda read: read_consumer_events(
            session,
            read.model,
            read.definition,
            workspace,
            asked,
            retention_days=request.app.state.feed_retention_days,
        ),
    )


def _offered(definition: ConsumerApiDefinition, operation: str) -> None:
    """Refuse an operation the definition does not list (C-D132)."""
    if not definition.offers(operation):
        raise api_error(
            404,
            "OPERATION_NOT_OFFERED",
            f"Consumer API '{definition.key}' does not offer the '{operation}' operation at contract"
            f" version {definition.contractVersion}",
            {"operation": operation},
        )


def _events_request(parameters: _Parameters, definition: ConsumerApiDefinition, workspace_key: str) -> EventsRequest:
    """The pull feed's request, checked: its events, payload and page size, and where it starts,
    from ``after`` or a cursor issued for the same API, workspace, events and parameters."""
    declared = {event.key for event in definition.events}
    event_keys = tuple(dict.fromkeys(parameters.listed.get("event", []))) if "event" in parameters.raw else ()
    unknown = [key for key in event_keys if key not in declared]
    if unknown:
        raise api_error(
            400,
            "UNKNOWN_EVENT",
            f"Consumer API '{definition.key}' declares no event '{unknown[0]}'; it declares {', '.join(sorted(declared))}",
            {"events": unknown, "path": "/query/event"},
        )
    payload = parameters.single("payload") or "full"
    if payload not in PAGE_SIZES:
        raise api_error(
            400, "INVALID_PAYLOAD", "payload must be 'full' or 'identity'", {"path": "/query/payload"}
        )
    maximum, default = PAGE_SIZES[payload]
    raw_size = parameters.single("pageSize")
    try:
        page_size = default if raw_size is None else int(raw_size)
    except ValueError:
        page_size = 0
    if not 1 <= page_size <= maximum:
        raise api_error(
            400,
            "INVALID_PAGE_SIZE",
            f"pageSize must be a whole number from 1 to {maximum} with payload '{payload}'",
            {"path": "/query/pageSize"},
        )
    cursor, raw_after = parameters.single("cursor"), parameters.single("after")
    if cursor is not None and raw_after is not None:
        raise api_error(
            400,
            "CONFLICTING_PAGE_PARAMETERS",
            "Give either after or cursor: a cursor already holds where it continues",
            {"path": "/query/cursor"},
        )
    if cursor is not None:
        try:
            decoded = decode_cursor(
                cursor,
                scope=cursor_scope(definition, workspace_key),
                sort=SORT,
                filters=cursor_filters(event_keys, parameters.definition),
                position_size=2,
            )
            start = (int(decoded[0]), int(decoded[1]))
        except (ApiError, ValueError):
            raise api_error(
                400, "INVALID_CURSOR", "Cursor does not continue this read", {"path": "/query/cursor"}
            ) from None
    else:
        try:
            after = 0 if raw_after is None else int(raw_after)
        except ValueError:
            after = -1
        if after < 0:
            raise api_error(
                400, "INVALID_POSITION", "after must be a whole number, 0 or more", {"path": "/query/after"}
            )
        start = (after, AFTER_POSITION)
    return EventsRequest(
        start=start,
        page_size=page_size,
        payload=payload,
        event_keys=event_keys,
        parameters=parameters.definition,
    )


@router.get("", response_model=None)
@reads_own_parameters
def get_index(request: Request, response: Response, session: DbSession) -> dict[str, Any] | Response:
    """The API index: every consumer API of the release ``workspace`` runs (the default workspace
    without it), by ``consumerApi``, with its name, contract version and the URL of its OpenAPI
    document (C-D69), which carries the ``workspace`` asked for. A definition key may mean another
    contract in another workspace (0.11 D27): the headers name the workspace and release described.
    A ``consumer`` token sees the APIs it is granted there (0.12 Z3, D308)."""
    parameters = _plain(request, _PUBLICATIONS)
    listed: frozenset[str] | None = request.state.listed_apis
    workspace, active = _described(response, session, request.query_params.get("workspace"))
    page_size, page = _page(parameters)
    root_path = _root_path(request)
    suffix = _workspace_query(request)
    entries = [
        {
            "consumerApi": item.key,
            "name": item.name,
            **({"description": item.description} if item.description else {}),
            "contractVersion": item.contractVersion,
            "openapi": f"{root_path}{consumer_openapi_path(item)}{suffix}",
        }
        for item in consumer_apis(active.model)
        if listed is None or item.key in listed
    ]

    def read() -> dict[str, Any]:
        found = paginate_sequence(
            entries, lambda entry: (entry["consumerApi"],), scope="consumer-index", page=page, page_size=page_size
        )
        return {"items": found.items, "pageSize": page_size, **found.links()}

    tag = entity_tag(
        ("index", workspace.key, active.release_id, root_path, suffix, *(sorted(listed) if listed is not None else ["*"])), "index"
    )
    return _document(request, response, tag, read)


@router.get("/{consumer_api}/v{contract_version}/openapi.json", response_model=None)
@reads_own_parameters
def get_openapi(
    consumer_api: str, contract_version: str, request: Request, response: Response, session: DbSession
) -> dict[str, Any] | Response:
    """The definition's own OpenAPI document at its contract version (C6b), from the release
    ``workspace`` runs (the default workspace without it, 0.11 D10): its paths written out with the
    name and version, ``info.version`` the contract version; another version answers
    ``404 CONTRACT_VERSION_NOT_FOUND`` naming the one served."""
    _plain(request, frozenset({"workspace"}))
    workspace, active = _described(response, session, request.query_params.get("workspace"))
    definition = consumer_definition(active.model, consumer_api, contract_version)
    root_path = _root_path(request)
    return _document(
        request,
        response,
        entity_tag(("openapi", workspace.key, active.release_id, root_path), definition.contractVersion),
        lambda: consumer_openapi(
            active.model,
            definition,
            root_path=root_path,
            resolve_max_items=request.app.state.consumer_resolve_max_items,
            token_url=f"{request.app.state.identity_settings.issuer}/oauth/token",
        ),
    )


def _described(response: Response, session: Session, workspace_key: str | None) -> tuple[Workspace, ModelSnapshot]:
    """The workspace a document describes and its model, named in the answer's headers."""
    workspace = _workspace(session, workspace_key)
    active = resolve_model_snapshot(session, workspace.key)
    response.headers[WORKSPACE_HEADER] = workspace.key
    response.headers[RELEASE_HEADER] = active.release_id
    return workspace, active


def _workspace_query(request: Request) -> str:
    """``?workspace=…`` as the request named it, for the links a document gives."""
    key = request.query_params.get("workspace")
    return f"?{urlencode({'workspace': key})}" if key else ""


def _root_path(request: Request) -> str:
    """The deployment's root path behind a proxy, as the reference page follows it (V1)."""
    return str(request.scope.get("root_path", "")).rstrip("/")


def _plain(request: Request, serves: frozenset[str]) -> _Parameters:
    """The query parameters of a route that reads no definition parameters: a name it does not serve
    is ``UNKNOWN_PARAMETER``, or ``PARAMETER_NOT_SUPPORTED`` for one a consumer read serves."""
    raw = {name: request.query_params.getlist(name) for name in sorted(set(request.query_params))}
    unknown = [name for name in raw if name not in serves and name not in _ROUTE_NAMES]
    if unknown:
        raise api_error(
            400,
            "UNKNOWN_PARAMETER",
            f"Unknown query parameter '{unknown[0]}'",
            {"parameters": unknown, "path": f"/query/{unknown[0]}"},
        )
    unsupported = [name for name in raw if name not in serves]
    if unsupported:
        raise api_error(
            400,
            "PARAMETER_NOT_SUPPORTED",
            f"Parameter '{unsupported[0]}' is not supported on this read",
            {"parameters": unsupported, "path": f"/query/{unsupported[0]}"},
        )
    return _Parameters(raw=raw, listed={}, definition={}, parents=[])


def _document(
    request: Request, response: Response, tag: str, read: Callable[[], dict[str, Any]]
) -> dict[str, Any] | Response:
    """A read that depends on the active release only: its answer with ``tag``, or ``304``."""
    try:
        body = read()
    except ApiError as exc:
        if exc.status == 422 and exc.code in _PAGING_CODES:
            exc.status = 400
        raise
    if none_match(request.headers.get("if-none-match"), tag):
        return Response(status_code=304, headers={"ETag": tag})
    response.headers["ETag"] = tag
    return body


def _resolve_items(raw: bytes, definition: ConsumerApiDefinition, max_items: int) -> list[ResolveItem]:
    """The body's items, checked: its shape as a whole (``400 REQUEST_VALIDATION_ERROR``), the
    item count (``413 BATCH_TOO_LARGE``) and ``defaults``' names refuse the request (C-D49, C-D50);
    an item's own names, its ``query`` or ``id`` and its terms refuse that item only."""
    try:
        body = json.loads(raw)
    except ValueError:
        raise _shape("", "the body is not JSON") from None
    if not isinstance(body, dict):
        raise _shape("", "the body must be an object with 'items'")
    for name in body:
        if name not in ("items", "defaults"):
            raise _shape(f"/{name}", f"'{name}' is not part of a batch resolve request")
    items = body.get("items")
    if not isinstance(items, list):
        raise _shape("/items", "'items' must be a list of items")
    if len(items) > max_items:
        raise api_error(
            413,
            "BATCH_TOO_LARGE",
            f"The batch has {len(items)} items; at most {max_items} resolve in one request",
            {"setting": "CONSUMER_RESOLVE_MAX_ITEMS", "maximum": max_items, "items": len(items)},
        )
    if not items:
        raise _shape("/items", "'items' must hold at least one item")
    defaults = body.get("defaults", {})
    if not isinstance(defaults, dict):
        raise _shape("/defaults", "'defaults' must be an object of parameters")
    default_values = {name: _json_values(value, f"/defaults/{name}") for name, value in defaults.items()}
    shaped = [_shaped_item(item, f"/items/{index}") for index, item in enumerate(items)]

    targets = target_names(definition)
    known = _ROUTE_NAMES | _ITEM | set(definition.parameters) | set(targets) | {
        item.parentParameter.name for item in definition.lists if item.parentParameter is not None
    }
    applied = set(definition.parameters) | set(targets)
    refused = _names_refused(list(default_values), known, applied, "/defaults", targets)
    if refused is not None:
        raise refused
    resolved = []
    for index, (ref, values) in enumerate(shaped):
        refused = _names_refused(list(values), known, applied | _ITEM, f"/items/{index}", targets)
        if refused is not None:
            resolved.append(ResolveItem(index=index, ref=ref, refused=refused))
            continue
        if ("query" in values) == ("id" in values):
            resolved.append(
                ResolveItem(
                    index=index,
                    ref=ref,
                    refused=api_error(
                        400,
                        "QUERY_OR_ID_REQUIRED",
                        "An item holds exactly one of 'query' and 'id'",
                        {"pointer": f"/items/{index}"},
                    ),
                )
            )
            continue
        own = {name: given for name, given in values.items() if name not in _ITEM}
        # An item's target replaces the defaults' rather than adding a second (C-D56).
        inherited = {
            name: given
            for name, given in default_values.items()
            if name not in own and not (_is_target(name) and any(_is_target(key) for key in own))
        }
        pointers = {name: f"/defaults/{name}" for name in inherited}
        found = ResolveItem(
            index=index,
            ref=ref,
            parameters={**inherited, **own},
            pointers=pointers,
        )
        if "id" in values:
            resolved.append(replace(found, object_id=values["id"][0]))
            continue
        try:
            resolved.append(replace(found, terms=xref_terms(values["query"])))
        except ApiError as error:
            resolved.append(replace(found, refused=item_error(error, found.pointer("/query/query"))))
    return resolved


def _shaped_item(item: Any, pointer: str) -> tuple[str | None, dict[str, list[str]]]:
    """An item's ``ref`` and its other names' values, each a list of strings."""
    if not isinstance(item, dict):
        raise _shape(pointer, "an item must be an object")
    ref = item.get("ref")
    if ref is not None and not (isinstance(ref, str) and _REF_LENGTH[0] <= len(ref) <= _REF_LENGTH[1]):
        raise _shape(f"{pointer}/ref", "'ref' must be text of 1 to 200 characters")
    identifier = item.get("id")
    if identifier is not None and not isinstance(identifier, str):
        raise _shape(f"{pointer}/id", "'id' must be text")
    values = {
        name: _json_values(value, f"{pointer}/{name}") for name, value in item.items() if name != "ref"
    }
    return ref, values


def _json_values(value: Any, pointer: str) -> list[str]:
    """A value given as text or a list of texts. JSON lists values itself, so nothing is split on
    commas (C-D47)."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return list(value)
    raise _shape(pointer, "a value must be text or a list of texts")


def _names_refused(
    names: list[str], known: set[str], applied: set[str], at: str, targets: list[str]
) -> ApiError | None:
    """``UNKNOWN_PARAMETER`` for a name the API does not know, ``PARAMETER_NOT_SUPPORTED`` for one it
    knows that a lookup does not apply, pointing at the first; then ``MULTIPLE_TARGETS`` for a
    second ``to.`` name."""
    unknown = [name for name in names if name not in known]
    if unknown:
        return api_error(
            400,
            "UNKNOWN_PARAMETER",
            f"Unknown parameter '{unknown[0]}'{_targetable(unknown[0], targets)}",
            {"parameters": unknown, "pointer": f"{at}/{unknown[0]}"},
        )
    unsupported = [name for name in names if name not in applied]
    if unsupported:
        return api_error(
            400,
            "PARAMETER_NOT_SUPPORTED",
            f"Parameter '{unsupported[0]}' is not supported in batch resolve",
            {"parameters": unsupported, "pointer": f"{at}/{unsupported[0]}"},
        )
    return _multiple_targets(names, "pointer", at)


def _is_target(name: str) -> bool:
    return name.startswith(TARGET_PREFIX)


def _targetable(name: str, targets: list[str]) -> str:
    """The end of an unknown ``to.`` name's message: the names this API can target (C-D57)."""
    if not _is_target(name):
        return ""
    if not targets:
        return "; this API has no targetable parameter"
    return f"; this API targets {', '.join(targets)}"


def _multiple_targets(names: list[str], key: str, at: str) -> ApiError | None:
    """``MULTIPLE_TARGETS`` when ``names`` hold more than one ``to.`` name: a read has one target
    (C-D56)."""
    given = [name for name in names if _is_target(name)]
    if len(given) < 2:
        return None
    return api_error(
        400,
        "MULTIPLE_TARGETS",
        f"A read has one target, but {' and '.join(given)} are given",
        {"parameters": given, key: f"{at}/{given[1]}"},
    )


def _shape(pointer: str, message: str) -> ApiError:
    return api_error(
        400,
        "REQUEST_VALIDATION_ERROR",
        f"The request body is not a batch resolve request: {message}",
        {"pointer": pointer},
    )


def _expect_one(raw: str | None) -> bool:
    if raw is None or raw == "any":
        return False
    if raw == "one":
        return True
    raise api_error(400, "INVALID_EXPECT", "expect must be 'any' or 'one'", {"path": "/query/expect"})


def _answer(
    request: Request,
    response: Response,
    workspace: Workspace,
    reading: Callable[[], _Read],
    read: Callable[[_Read], dict[str, Any]],
    *,
    tagged: bool = True,
    dated: Callable[[_Read, dict[str, Any]], list[str]] | None = None,
) -> dict[str, Any] | Response:
    """The read's answer, naming the workspace and a pinned read's publication in the headers, on a
    refusal as well. A tagged read answers its ``ETag``, or ``304`` with no body when the request's
    ``If-None-Match`` names it (C-D65). A read dated by ``asOf`` names the dated types in
    ``RDM-As-Of-Applied``: ``dated`` reads them from the read and its body, by default the body's
    ``asOfApplied`` (C-D78)."""
    headers = {WORKSPACE_HEADER: workspace.key}
    try:
        current = reading()
        if current.source.publication_id is not None:
            headers[PUBLICATION_HEADER] = current.source.publication_id
        body = read(current)
    except ApiError as exc:
        if exc.status == 422 and exc.code in _PAGING_CODES:
            exc.status = 400
        exc.headers = {**(exc.headers or {}), **headers}
        raise
    if current.parameters.as_of is not None:
        names = dated(current, body) if dated is not None else body.get("asOfApplied", [])
        headers[AS_OF_HEADER] = ", ".join(names)
    if tagged:
        headers["ETag"] = current.tag
        if none_match(request.headers.get("if-none-match"), current.tag):
            return Response(status_code=304, headers=headers)
    response.headers.update(headers)
    return body


@dataclass(frozen=True)
class _Parameters:
    """A request's query parameters, checked against the names its route serves."""

    raw: dict[str, list[str]]
    # Each name's values, split as OpenAPI's form style lists them (C-D32, C3b).
    listed: dict[str, list[str]]
    # The definition parameters the route applies, by name, with a ``to.`` target among them.
    definition: dict[str, list[str]]
    parents: list[str]
    # The business date of ``asOf``, on a route that serves it (C16).
    as_of: date | None = None

    @classmethod
    def check(
        cls,
        request: Request,
        definition: ConsumerApiDefinition,
        *,
        serves: frozenset[str],
        parent: str | None = None,
        applies_definition: bool = True,
        crosswalk: bool = True,
    ) -> _Parameters:
        """Refuse a name the API does not know (``UNKNOWN_PARAMETER``), then one it knows that this
        route does not apply (``PARAMETER_NOT_SUPPORTED``): one outside ``serves``, a list's parent
        parameter off its list, or a definition parameter on a route that takes them in its body
        (batch resolve's ``defaults``). A ``to.`` name is a definition parameter's crosswalk target,
        one per read (C-D56, C-D57); a read without ``crosswalk`` (the pull feed) applies none."""
        targets = target_names(definition)
        applied = set(serves) | (
            set(definition.parameters) | (set(targets) if crosswalk else set())
            if applies_definition
            else set()
        )
        if parent is not None:
            applied.add(parent)
        known = applied | _ROUTE_NAMES | set(definition.parameters) | set(targets) | {
            item.parentParameter.name for item in definition.lists if item.parentParameter is not None
        }
        raw = {name: request.query_params.getlist(name) for name in sorted(set(request.query_params))}
        listed = _listed_values(request.scope.get("query_string", b""))
        unknown = [name for name in raw if name not in known]
        if unknown:
            raise api_error(
                400,
                "UNKNOWN_PARAMETER",
                f"Unknown query parameter '{unknown[0]}'{_targetable(unknown[0], targets)}",
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
        multiple = _multiple_targets(list(raw), "path", "/query")
        if multiple is not None:
            raise multiple
        # On its list, a parent parameter sharing a definition parameter's name addresses the parent.
        return cls(
            raw=raw,
            listed=listed,
            definition={
                name: listed[name]
                for name in raw
                if name in applied and (name in definition.parameters or _is_target(name)) and name != parent
            },
            parents=list(dict.fromkeys(listed[parent])) if parent in raw else [],
            as_of=_as_of(raw.get("asOf"), listed.get("asOf")) if "asOf" in raw else None,
        )

    def single(self, name: str) -> str | None:
        values = self.raw.get(name)
        return values[-1] if values else None


def _as_of(raw: list[str] | None, listed: list[str] | None) -> date:
    """``asOf`` as a date: one calendar day, ``YYYY-MM-DD`` (C-D79). A time, a zone, an impossible
    day or several values are ``400 INVALID_AS_OF``: a read answers for one date."""
    values = listed or raw or []
    if len(values) == 1 and _DATE.match(values[0]):
        try:
            return date.fromisoformat(values[0])
        except ValueError:
            pass
    raise api_error(
        400,
        "INVALID_AS_OF",
        "asOf must be one calendar date, written YYYY-MM-DD",
        {"path": "/query/asOf"},
    )


def _listed_values(query_string: bytes) -> dict[str, list[str]]:
    """Each name's values, repeated or comma-separated, as OpenAPI 3 serialises a list in a query
    (``style: form``, ``explode`` true or false; RFC 3986). The raw query is split on ``&``, each pair
    on its first ``=`` and each value on literal commas before anything is decoded, so a comma inside
    a value, sent as ``%2C``, stays in it (C-D32 amended, C3b)."""
    listed: dict[str, list[str]] = {}
    for pair in query_string.decode("latin-1").split("&"):
        if not pair:
            continue
        name, _, value = pair.partition("=")
        decoded = unquote_plus(name)
        listed.setdefault(decoded, []).extend(unquote_plus(piece) for piece in value.split(","))
    return listed


def _page(parameters: _Parameters) -> tuple[int, PageRequest]:
    """The page size and the page a list read asks for (C-D30)."""
    raw_size = parameters.single("pageSize")
    try:
        page_size = _DEFAULT_PAGE_SIZE if raw_size is None else int(raw_size)
    except ValueError:
        page_size = 0
    if not _MIN_PAGE_SIZE <= page_size <= _MAX_PAGE_SIZE:
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
