"""The consumer API's routes (Base 0.9 C2 onward).

Each route resolves the definition from the active release (``{consumerApi}`` and ``v{contractVersion}``),
checks the request's parameters against the names it serves, resolves the workspace and reads its
live data, or with ``publication`` one of its publications (C6a), through
``engine/reads/consumer_objects``, ``consumer_lists``, ``consumer_xref`` and ``consumer_resolve``.
Every response names the workspace it read in the ``RDM-Workspace`` header (C-D23), and a pinned
read's the publication in ``RDM-Publication`` (C-D63). A ``GET`` answers an ``ETag`` and honours
``If-None-Match`` (C-D65). The routes stay out of the management OpenAPI document: each definition
serves its own at ``…/openapi.json``, and ``GET /api/consumer`` lists them (C6b, C-D69).
"""

import json
from collections.abc import Callable, Iterator
from dataclasses import dataclass, replace
from typing import Annotated, Any
from urllib.parse import unquote_plus

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..common.cursors import signed_scope
from ..common.pagination import PageRequest, paginate_sequence
from ..db import SessionLocal
from ..engine.model.consumer_openapi import consumer_openapi, consumer_openapi_path
from ..engine.model.registry import ModelSnapshot, resolve_model_snapshot, resolve_pinned_release
from ..engine.reads.consumer_lists import consumer_list, read_consumer_list
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
PUBLICATION_HEADER = "RDM-Publication"
# The value of ``publication`` that reads the workspace's active publication (C-D61).
LATEST = "latest"
# The names that select a list's page (ADR-030, C-D30).
_PAGING = frozenset({"pageSize", "cursor", "position", "from", "seek", "includeTotal"})
# The names each route serves besides the definition's parameters. XREF pages by score, which no
# caller seeks, and always counts its total (C-D39); with expect=one it reads no page (C-D40).
_OBJECT = frozenset({"workspace", "publication"})
_LIST = _OBJECT | _PAGING
_XREF_ONE = _OBJECT | {"query", "expect"}
_XREF = _XREF_ONE | (_PAGING - {"seek", "includeTotal"})
# The publications list reads live data in the order of publication, which no caller seeks (C-D66).
_PUBLICATIONS = frozenset({"workspace"}) | (_PAGING - {"seek"})
# Every name a route of the API serves.
_ROUTE_NAMES = _LIST | _XREF
# The names a batch resolve item holds besides the definition's parameters (C-D47).
_ITEM = frozenset({"ref", "query", "id"})
_REF_LENGTH = (1, 200)
_DEFAULT_PAGE_SIZE = 20
_MAX_PAGE_SIZE = 100
# The shared paging refusals answer 400 here, the consumer tier's status for a request error.
_PAGING_CODES = frozenset({"INVALID_CURSOR", "CONFLICTING_PAGE_PARAMETERS", "INVALID_POSITION", "INVALID_SEEK"})


def _session() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session


async def _body(request: Request) -> bytes:
    return await request.body()


DbSession = Annotated[Session, Depends(_session)]
Body = Annotated[bytes, Depends(_body)]

router = APIRouter(prefix=PREFIX, tags=["consumer"], include_in_schema=False)


def reads_own_parameters[F](endpoint: F) -> F:
    """Mark a route that checks its query parameters itself, against its definition: the app-wide
    unknown-parameter check (``management/query_parameters``) leaves it alone."""
    endpoint.reads_own_parameters = True  # type: ignore[attr-defined]
    return endpoint


@dataclass(frozen=True)
class _Read:
    """What a read reads: the model and definition that shape it, the source of its rows, its
    parameters as checked against that definition, and its entity tag."""

    model: EngineModel
    definition: ConsumerApiDefinition
    source: ConsumerSource
    parameters: _Parameters
    tag: str

    def narrowed(self, session: Session) -> Any:
        return consumer_filter(session, self.model, self.definition, self.source, self.parameters.definition)


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
        declared = next((item for item in pinned.model.consumerApis or () if item.key == definition.key), None)
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
    active = resolve_model_snapshot(session)
    definition = consumer_definition(active.model, consumer_api, contract_version)

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
    )


@router.get("/{consumer_api}/v{contract_version}/lists/{list_key}", response_model=None)
@reads_own_parameters
def get_list(
    consumer_api: str, contract_version: str, list_key: str, request: Request, response: Response, session: DbSession
) -> dict[str, Any] | Response:
    """A page of the definition's list ``list_key``: the records of its type, below the parent
    values when given, narrowed by the definition's parameters (C-D27–C-D31)."""
    active = resolve_model_snapshot(session)
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
    active = resolve_model_snapshot(session)
    definition = consumer_definition(active.model, consumer_api, contract_version)
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
    active = resolve_model_snapshot(session)
    definition = consumer_definition(active.model, consumer_api, contract_version)

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
    active = resolve_model_snapshot(session)
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


@router.get("", response_model=None)
@reads_own_parameters
def get_index(request: Request, response: Response, session: DbSession) -> dict[str, Any] | Response:
    """The API index: every consumer API of the active release, by ``consumerApi``, with its name,
    contract version and the URL of its OpenAPI document (C-D69). Definitions are not per workspace."""
    active = resolve_model_snapshot(session)
    parameters = _plain(request, _PUBLICATIONS - {"workspace"})
    page_size, page = _page(parameters)
    root_path = _root_path(request)
    entries = [
        {
            "consumerApi": item.key,
            "name": item.name,
            **({"description": item.description} if item.description else {}),
            "contractVersion": item.contractVersion,
            "openapi": f"{root_path}{consumer_openapi_path(item)}",
        }
        for item in active.model.consumerApis or ()
    ]

    def read() -> dict[str, Any]:
        found = paginate_sequence(
            entries, lambda entry: (entry["consumerApi"],), scope="consumer-index", page=page, page_size=page_size
        )
        return {"items": found.items, "pageSize": page_size, **found.links()}

    return _document(request, response, entity_tag(("index", active.release_id, root_path), "index"), read)


@router.get("/{consumer_api}/v{contract_version}/openapi.json", response_model=None)
@reads_own_parameters
def get_openapi(
    consumer_api: str, contract_version: str, request: Request, response: Response, session: DbSession
) -> dict[str, Any] | Response:
    """The definition's own OpenAPI document at its contract version (C6b): its paths written out with
    the name and version, ``info.version`` the contract version; another version answers
    ``404 CONTRACT_VERSION_NOT_FOUND`` naming the one served."""
    active = resolve_model_snapshot(session)
    definition = consumer_definition(active.model, consumer_api, contract_version)
    _plain(request, frozenset())
    root_path = _root_path(request)
    return _document(
        request,
        response,
        entity_tag(("openapi", active.release_id, root_path), definition.contractVersion),
        lambda: consumer_openapi(
            active.model,
            definition,
            root_path=root_path,
            resolve_max_items=request.app.state.consumer_resolve_max_items,
        ),
    )


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
) -> dict[str, Any] | Response:
    """The read's answer, naming the workspace and a pinned read's publication in the headers, on a
    refusal as well. A tagged read answers its ``ETag``, or ``304`` with no body when the request's
    ``If-None-Match`` names it (C-D65)."""
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

    @classmethod
    def check(
        cls,
        request: Request,
        definition: ConsumerApiDefinition,
        *,
        serves: frozenset[str],
        parent: str | None = None,
        applies_definition: bool = True,
    ) -> _Parameters:
        """Refuse a name the API does not know (``UNKNOWN_PARAMETER``), then one it knows that this
        route does not apply (``PARAMETER_NOT_SUPPORTED``): one outside ``serves``, a list's parent
        parameter off its list, or a definition parameter on a route that takes them in its body
        (batch resolve's ``defaults``). A ``to.`` name is a definition parameter's crosswalk target,
        one per read (C-D56, C-D57)."""
        targets = target_names(definition)
        applied = set(serves) | (set(definition.parameters) | set(targets) if applies_definition else set())
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
        )

    def single(self, name: str) -> str | None:
        values = self.raw.get(name)
        return values[-1] if values else None


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
