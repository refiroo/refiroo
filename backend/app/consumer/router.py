"""The consumer API's routes (Base 0.9 C2 onward).

Each route resolves the definition from the active release (``{apiKey}`` and ``v{contractVersion}``),
checks the request's parameters against the names it serves, resolves the workspace and reads live
data through ``engine/reads/consumer_objects``, ``consumer_lists``, ``consumer_xref`` and
``consumer_resolve``. Every response names the workspace it read in the ``RDM-Workspace`` header
(C-D23). The routes stay out of the management
OpenAPI document; C6 generates one document per definition.
"""

import json
from collections.abc import Callable, Iterator
from dataclasses import dataclass, replace
from typing import Annotated, Any
from urllib.parse import unquote_plus

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from ..common.pagination import PageRequest
from ..db import SessionLocal
from ..engine.model.registry import resolve_model_snapshot
from ..engine.reads.consumer_lists import consumer_list, read_consumer_list
from ..engine.reads.consumer_objects import consumer_definition, read_consumer_object
from ..engine.reads.consumer_parameters import consumer_filter
from ..engine.reads.consumer_resolve import ResolveItem, item_error, read_resolve
from ..engine.reads.consumer_xref import read_xref, xref_terms
from ..engine.workspaces.catalogue import resolve_workspace
from ..errors import ApiError, api_error
from ..models.database import Workspace
from ..models.schema import ConsumerApiDefinition

PREFIX = "/api/consumer"
WORKSPACE_HEADER = "RDM-Workspace"
# The names that select a list's page (ADR-030, C-D30).
_PAGING = frozenset({"pageSize", "cursor", "position", "from", "seek", "includeTotal"})
# The names each route serves besides the definition's parameters. XREF pages by score, which no
# caller seeks, and always counts its total (C-D39); with expect=one it reads no page (C-D40).
_OBJECT = frozenset({"workspace"})
_LIST = _OBJECT | _PAGING
_XREF_ONE = _OBJECT | {"query", "expect"}
_XREF = _XREF_ONE | (_PAGING - {"seek", "includeTotal"})
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


@router.get("/{api_key}/v{contract_version}/objects/{object_id}")
@reads_own_parameters
def get_object(
    api_key: str, contract_version: str, object_id: str, request: Request, response: Response, session: DbSession
) -> dict[str, Any]:
    """Get by ID: the definition's shared object for the record with this object ID, narrowed by the
    definition's parameters (C-D31)."""
    model = resolve_model_snapshot(session).model
    definition = consumer_definition(model, api_key, contract_version)
    parameters = _Parameters.check(request, definition, serves=_OBJECT)
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
            consumer_filter(session, model, definition, workspace.key, parameters.definition),
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
    parent = declared.parentParameter.name if declared.parentParameter else None
    parameters = _Parameters.check(request, definition, serves=_LIST, parent=parent)
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
            narrowed=consumer_filter(session, model, definition, workspace.key, parameters.definition),
            parameters=parameters.definition,
            page=page,
            page_size=page_size,
        ),
    )


@router.get("/{api_key}/v{contract_version}/xref")
@reads_own_parameters
def get_xref(
    api_key: str, contract_version: str, request: Request, response: Response, session: DbSession
) -> dict[str, Any]:
    """XREF: the exposed objects the query's terms match, scored by the definition's ``match`` and
    narrowed by its parameters, a page of them or with ``expect=one`` the single best (C-D34–C-D43)."""
    model = resolve_model_snapshot(session).model
    definition = consumer_definition(model, api_key, contract_version)
    expect = request.query_params.getlist("expect")
    expect_one = _expect_one(expect[-1] if expect else None)
    parameters = _Parameters.check(request, definition, serves=_XREF_ONE if expect_one else _XREF)
    terms = xref_terms(parameters.listed.get("query", []))
    page_size, page = (_DEFAULT_PAGE_SIZE, PageRequest()) if expect_one else _page(parameters)
    workspace = _workspace(session, parameters.single("workspace"))
    return _answer(
        response,
        workspace,
        lambda: read_xref(
            session,
            model,
            definition,
            workspace_key=workspace.key,
            terms=terms,
            narrowed=consumer_filter(session, model, definition, workspace.key, parameters.definition),
            parameters=parameters.definition,
            expect_one=expect_one,
            page=page,
            page_size=page_size,
        ),
    )


@router.post("/{api_key}/v{contract_version}/resolve")
@reads_own_parameters
def post_resolve(
    api_key: str, contract_version: str, request: Request, response: Response, session: DbSession, body: Body
) -> dict[str, Any]:
    """Batch resolve: each item as ``xref?expect=one`` (by ``query``) or get by ID (by ``id``), with
    the definition's parameters from ``defaults`` and the item, its outcome the single read's answer
    (C-D47–C-D50). A read: the body only carries the items."""
    model = resolve_model_snapshot(session).model
    definition = consumer_definition(model, api_key, contract_version)
    parameters = _Parameters.check(request, definition, serves=_OBJECT, applies_definition=False)
    workspace = _workspace(session, parameters.single("workspace"))
    return _answer(
        response,
        workspace,
        lambda: read_resolve(
            session,
            model,
            definition,
            workspace.key,
            _resolve_items(body, definition, request.app.state.consumer_resolve_max_items),
        ),
    )


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

    known = _ROUTE_NAMES | _ITEM | set(definition.parameters) | {
        item.parentParameter.name for item in definition.lists if item.parentParameter is not None
    }
    applied = set(definition.parameters)
    refused = _names_refused(list(default_values), known, applied, "/defaults")
    if refused is not None:
        raise refused
    resolved = []
    for index, (ref, values) in enumerate(shaped):
        refused = _names_refused(list(values), known, applied | _ITEM, f"/items/{index}")
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
        pointers = {name: f"/defaults/{name}" for name in default_values if name not in own}
        found = ResolveItem(
            index=index,
            ref=ref,
            parameters={**default_values, **own},
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


def _names_refused(names: list[str], known: set[str], applied: set[str], at: str) -> ApiError | None:
    """``UNKNOWN_PARAMETER`` for a name the API does not know, ``PARAMETER_NOT_SUPPORTED`` for one it
    knows that a lookup does not apply, pointing at the first."""
    unknown = [name for name in names if name not in known]
    if unknown:
        return api_error(
            400,
            "UNKNOWN_PARAMETER",
            f"Unknown parameter '{unknown[0]}'",
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
    return None


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
    # Each name's values, split as OpenAPI's form style lists them (C-D32, C3b).
    listed: dict[str, list[str]]
    # The definition parameters the route applies, by name.
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
        (batch resolve's ``defaults``)."""
        applied = set(serves) | (set(definition.parameters) if applies_definition else set())
        if parent is not None:
            applied.add(parent)
        known = applied | _ROUTE_NAMES | set(definition.parameters) | {
            item.parentParameter.name for item in definition.lists if item.parentParameter is not None
        }
        raw = {name: request.query_params.getlist(name) for name in sorted(set(request.query_params))}
        listed = _listed_values(request.scope.get("query_string", b""))
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
            listed=listed,
            definition={
                name: listed[name]
                for name in raw
                if name in applied and name in definition.parameters and name != parent
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
