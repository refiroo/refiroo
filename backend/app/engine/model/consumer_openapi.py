"""A consumer API definition's own OpenAPI document (Base 0.9 C6b; SETTINGS_AND_UI_PLAN "Versions in
the documentation").

The document describes one definition at its contract version as the API answers it, so a client
generated from it, or the API reference page (V2), reads real answers. Its paths are written out with
the definition's name and version (``/api/consumer/rdm/v2/xref``), one per list, with no placeholder
for either; ``info.version`` is the contract version. Its schemas come from the contract
(``consumer_contract.output_contract``), the same derivation the breaking-change check compares, so
the document and the contract cannot drift apart. The limits a consumer meets are written where they
apply.
"""

import re
from typing import Any

from ...models.schema import (
    PARENT_BLOCK_PREFIX,
    AncestorParameter,
    ConsumerApiDefinition,
    EngineModel,
    ObjectTypeParameter,
    ProjectionParameter,
    RelatedParameter,
)
from ...models.search_index import MIN_INDEXED_LENGTH
from ..model.consumer_contract import OutputContract, output_contract, parent_blocks_held
from ..model.consumer_examples import example_of
from ..model.consumer_definitions import consumer_api, served_versions
from ..reads.consumer_events import FULL, IDENTITY
from ..reads.consumer_events import PAGE_SIZES as EVENT_PAGE_SIZES
from ..reads.consumer_lists import PAGE_SIZE
from ..reads.consumer_xref import MATCH_LIMIT, MAX_TERMS

OPENAPI_VERSION = "3.1.0"
# The read limits the document states (CONSUMER_API C-D30, C-D37, C-D38), the engine's own
# (0.9 R-F21): the document cannot state one the reads do not apply.
MIN_CONTAINS = MIN_INDEXED_LENGTH
_TYPES: dict[str, dict[str, Any]] = {
    "text": {"type": "string"},
    "integer": {"type": "integer"},
    "decimal": {"type": "string", "description": "A decimal, written as a string to keep its digits"},
    "boolean": {"type": "boolean"},
    "date": {"type": "string", "format": "date"},
    "dateTime": {"type": "string", "format": "date-time"},
}
_STRINGS = {"anyOf": [{"type": "string"}, {"type": "array", "items": {"type": "string"}}]}


def consumer_api_base(definition: ConsumerApiDefinition) -> str:
    """The path every route of the definition's API starts with, at its contract version."""
    return f"/api/consumer/{definition.key}/v{definition.contractVersion}"


def consumer_openapi_path(definition: ConsumerApiDefinition) -> str:
    """Where the definition's document is served, before the deployment's root path: the URL the API
    index (C-D69) and the reference page's source (V2) name."""
    return f"{consumer_api_base(definition)}/openapi.json"


def consumer_openapi(
    model: EngineModel,
    definition: ConsumerApiDefinition,
    *,
    root_path: str,
    resolve_max_items: int,
    token_url: str,
    workspace_key: str | None = None,
) -> dict[str, Any]:
    """The OpenAPI 3.1 document of ``definition`` as the active release ``model`` declares it; every
    operation needs a ``consumer`` token from ``token_url`` (0.12 Z3, D311). ``workspace_key`` names the
    workspace the document describes when that is not the deployment's default: every read then
    requires ``workspace`` with that key, so a client built from the document (the reference page's test
    request) reads that workspace; without it the parameter is optional and names the default."""
    document = _Document(model, definition, root_path, resolve_max_items, workspace_key).build()
    document["components"]["securitySchemes"] = {
        "oauth2": {
            "type": "oauth2",
            "description": "A client's credentials exchanged for a `consumer` access token; a read "
            "needs a grant of this consumer API in the workspace it reads.",
            "flows": {
                "clientCredentials": {
                    "tokenUrl": token_url,
                    "scopes": {"consumer": "Read the consumer APIs granted to the client"},
                }
            },
        }
    }
    document["security"] = [{"oauth2": ["consumer"]}]
    return document


# The schema names the document writes itself; a public type name that equals one cannot name its schema.
_OWN_SCHEMAS = frozenset(
    {
        "Object", "ScoredObject", "ListPage", "XrefPage", "Publication", "PublicationPage", "ResolveDefaults",
        "ResolveItem", "ResolveRequest", "ResolveOutcome", "ResolveAnswer", "ErrorBody", "Error", "Event",
        "EventPage", "Parent",
    }
)
_SCHEMA_NAME = re.compile(r"[A-Za-z0-9._-]+")


def type_schema_names(definition: ConsumerApiDefinition) -> dict[str, str]:
    """The schema of each exposed type, by type key (OT-D3): named by its public name, so a code
    generator and the reference page read ``Country``. A public name that equals one of the document's
    own schemas, or is no valid schema name, is prefixed ``Object_`` (and written in the discriminator's
    mapping)."""
    names: dict[str, str] = {}
    taken = set(_OWN_SCHEMAS)
    for key, item in definition.objectTypes.items():
        public = item.publicName
        name = public
        if not _SCHEMA_NAME.fullmatch(name) or name in taken or name.startswith("Projection_"):
            base = f"Object_{re.sub(r'[^A-Za-z0-9._-]+', '_', public)}"
            name, counter = base, 2
            while name in taken:
                name, counter = f"{base}_{counter}", counter + 1
        taken.add(name)
        names[key] = name
    return names


def _ref(name: str) -> dict[str, str]:
    return {"$ref": f"#/components/schemas/{name}"}


def _nullable(schema: dict[str, Any]) -> dict[str, Any]:
    if not schema:
        return schema
    if "type" in schema and "$ref" not in schema:
        return {**schema, "type": [schema["type"], "null"]}
    return {"anyOf": [schema, {"type": "null"}]}


def _value(value_type: Any) -> dict[str, Any]:
    """The schema of a contract type: a value type, ``text[]``, or any value (JSON, or unknown)."""
    if value_type == "text[]":
        return {"type": "array", "items": {"type": "string"}}
    return dict(_TYPES.get(value_type, {}))


def _object(properties: dict[str, Any], required: list[str] | None = None, *, closed: bool = False) -> dict[str, Any]:
    """An object schema. An answer's objects stay open, so a field added later is no breaking change
    for a client that validates against the document (COMPATIBILITY, D440); a request's are closed."""
    schema = {"type": "object", "properties": properties, "required": list(properties) if required is None else required}
    if closed:
        schema["additionalProperties"] = False
    return schema


class _Document:
    def __init__(
        self,
        model: EngineModel,
        definition: ConsumerApiDefinition,
        root_path: str,
        resolve_max_items: int,
        workspace_key: str | None = None,
    ) -> None:
        self.workspace = _workspace_parameter(workspace_key)
        self.workspace_key = workspace_key
        self.model = model
        self.definition = definition
        self.contract: OutputContract = output_contract(model, definition)
        self.root_path = root_path
        self.resolve_max_items = resolve_max_items
        self.base = consumer_api_base(definition)
        self.targets = sorted(self.contract.targetable)

    def build(self) -> dict[str, Any]:
        definition = self.definition
        release = self.model.release
        # The operations the definition offers (C-D132), each described as its author wrote (C-D139).
        offered = {
            f"{self.base}/objects/{{id}}": ("objects", "get", self._get_by_id),
            **{
                f"{self.base}/lists/{item.key}": ("lists", "get", lambda key=item.key: self._list(key))
                for item in definition.lists
            },
            f"{self.base}/xref": ("xref", "get", self._xref),
            f"{self.base}/resolve": ("resolve", "post", self._resolve),
            f"{self.base}/publications": (None, "get", self._publications),
            f"{self.base}/events": ("events", "get", self._events),
        }
        paths: dict[str, Any] = {
            path: {method: build()}
            for path, (operation, method, build) in offered.items()
            if operation is None or definition.offers(operation)
        }
        intro = f"{definition.description}\n\n" if definition.description else ""
        # An earlier version the model keeps is deprecated, and says until when if it was told (DF3).
        kept = next(
            (item for item in served_versions(self.model, definition.key) if item.definition is definition and not item.is_current),
            None,
        )
        if kept is not None:
            for methods in paths.values():
                for operation in methods.values():
                    operation["deprecated"] = True
            current = consumer_api(self.model, definition.key)
            later = f" Version {current.contractVersion} is the one served now." if current is not None else ""
            ends = (
                f" Its administrator announces {kept.sunset} as the day it stops; it is served until the administrator removes it."
                if kept.sunset
                else ""
            )
            intro += f"**Deprecated:** this earlier contract version is still served.{later}{ends}\n\n"
        return {
            "openapi": OPENAPI_VERSION,
            "info": {
                "title": definition.name,
                "version": str(definition.contractVersion),
                "description": (
                    f"{intro}Consumer API `{definition.key}`, contract version {definition.contractVersion},"
                    f" declared by the model release {release.name} {release.version}. A read takes the live"
                    + (
                        " data of a workspace (`workspace`, default: the deployment's default workspace) or one"
                        if self.workspace_key is None
                        else f" data of workspace `{self.workspace_key}`, which it names (`workspace={self.workspace_key}`), or one"
                    )
                    + " of its publications (`publication`: an ID or `latest`). Every `GET` answers an `ETag`"
                    " and `304 Not Modified` to a matching `If-None-Match`."
                ),
            },
            "servers": [{"url": self.root_path or "/"}],
            "paths": paths,
            "components": {"schemas": self._schemas(), "headers": _HEADERS, "responses": _RESPONSES},
        }

    # --- parameters ---

    def _definition_parameters(self, parent: str | None = None, *, crosswalk: bool = True) -> list[dict[str, Any]]:
        """The definition's parameters and, unless ``crosswalk`` is off, their ``to.`` names. On a list
        whose parent parameter shares a definition parameter's name, the name addresses the parent
        there, so it is listed once, as the parent (C1; the consumer router reads it so)."""
        found = []
        for name, parameter in self.definition.parameters.items():
            if name != parent:
                found.append(_query(name, self._filter_description(name, parameter), _LISTED))
        for name in self.targets if crosswalk else ():
            projection = self.definition.parameters[name]
            assert isinstance(projection, ProjectionParameter)
            found.append(
                _query(
                    f"to.{name}",
                    f"Crosswalk: show the `{projection.projection}` items `{name}` would match, as `target`, in"
                    " place of the plain parameter's; changes no object, score, order or total. One `to.` name"
                    " per read.",
                    _LISTED,
                )
            )
        return found

    def _reads(self, dated: bool | None = None) -> list[dict[str, Any]]:
        """The names every read takes, with ``asOf`` where the read can return a dated type: on a
        list, its type; elsewhere any exposed type (C16)."""
        if dated is None:
            dated = bool(self.contract.as_of)
        return [self.workspace, _PUBLICATION, *([_as_of(self._dated_names())] if dated else [])]

    def _include_description(self) -> str:
        names = ", ".join(f"`{name}`" for name in self.definition.on_request())
        return (
            f"Related blocks served on request: {names}. A block is in the answer only when the read names"
            " it here; a filter on it narrows the records either way. An unknown name is"
            " `400 UNKNOWN_INCLUDE`."
        )

    def _include(self) -> list[dict[str, Any]]:
        """The ``include`` parameter, listed where the definition has a block served on request (PP-D30)."""
        names = list(self.definition.on_request())
        if not names:
            return []
        return [
            {
                "name": "include",
                "in": "query",
                "description": f"{self._include_description()} Repeated or comma-separated.",
                "style": "form",
                "explode": True,
                "schema": {"type": "array", "items": {"type": "string", "enum": names}},
            }
        ]

    def _dated_names(self) -> str:
        return ", ".join(sorted(self.contract.types[key] for key in self.contract.as_of))

    def _dated_codes(self, dated: bool | None = None) -> str | None:
        if dated is None:
            dated = bool(self.contract.as_of)
        return "INVALID_AS_OF, AS_OF_NOT_SUPPORTED" if dated else None

    def _include_code(self) -> str | None:
        return "UNKNOWN_INCLUDE" if self.definition.on_request() else None

    def _bad(self, *codes: str | None) -> str | None:
        """The request errors a read adds: its own codes, then ``UNKNOWN_INCLUDE`` where ``include`` is listed."""
        return ", ".join(filter(None, [*codes, self._include_code()])) or None

    def _described(self, part: str, text: str) -> str:
        """``text`` after the author's description of ``part``, when there is one (C-D139)."""
        authored = self.definition.described(part)
        return f"{authored}\n\n{text}" if authored else text

    def _filter_description(self, name: str, parameter: Any) -> str:
        authored = self.definition.described(f"filter:{name}")
        text = _parameter_description(parameter)
        return f"{authored} {text}" if authored else text

    def _get_by_id(self) -> dict[str, Any]:
        return {
            "summary": "Get by ID",
            "description": self._described(
                "operation:objects",
                "The shared object of the record with this object ID. The definition's parameters filter"
                " it (`404 OBJECT_NOT_FOUND` when filtered out) and limit its projections.",
            ),
            "parameters": [
                {"name": "id", "in": "path", "required": True, "schema": {"type": "string"}},
                *self._reads(),
                *self._include(),
                *self._definition_parameters(),
            ],
            "responses": _responses(
                _ref("Object"),
                "OBJECT_NOT_FOUND, WORKSPACE_NOT_FOUND, PUBLICATION_NOT_FOUND, TARGET_NOT_FOUND",
                conflict="AMBIGUOUS_TARGET, PUBLICATION_CONTRACT_MISMATCH",
                bad=self._bad(self._dated_codes()),
            ),
        }

    def _list(self, key: str) -> dict[str, Any]:
        declared = next(item for item in self.definition.lists if item.key == key)
        public = self.definition.objectTypes[declared.objectType].publicName
        parent = []
        if declared.parentParameter is not None:
            names = ", ".join(
                self.definition.objectTypes[item].publicName if item in self.definition.objectTypes else item
                for item in declared.parentParameter.objectTypes
            )
            parent = [
                _query(
                    declared.parentParameter.name,
                    f"Object IDs of {names} records: keeps the records anywhere below any of them.",
                    _LISTED,
                )
            ]
        order = "its sort attribute (records without a value last), then name" if declared.sortBy else "name"
        dated = declared.objectType in self.contract.as_of
        return {
            "summary": f"List {key}",
            "description": self._described(
                f"list:{key}",
                f"Every {public} record, ordered by {order}, then creation order (in a publication, object ID)."
                f" Paged with cursors both ways, `position`, `from=end`, `seek` and `includeTotal`;"
                f" `pageSize` {PAGE_SIZE[0]}–{PAGE_SIZE[1]}, default {PAGE_SIZE[2]}.",
            ),
            "parameters": [
                *parent,
                *self._reads(dated),
                *self._include(),
                *self._definition_parameters(
                    declared.parentParameter.name if declared.parentParameter is not None else None
                ),
                *_PAGING,
                _SEEK,
                _INCLUDE_TOTAL,
            ],
            "responses": _responses(
                _ref("ListPage"),
                "LIST_NOT_FOUND, PARENT_NOT_FOUND, WORKSPACE_NOT_FOUND, PUBLICATION_NOT_FOUND",
                conflict="PUBLICATION_CONTRACT_MISMATCH",
                bad=self._bad(self._dated_codes(dated)),
            ),
        }

    def _xref(self) -> dict[str, Any]:
        return {
            "summary": "XREF lookup",
            "description": self._described(
                "operation:xref",
                "The exposed records the query's terms match, scored by the definition's match rules, best"
                " first (score, public type name, name, object ID); with `expect=one`, the single best one."
                f" Matching part of a value (contains) needs a term of at least {MIN_CONTAINS} characters; a"
                f" shorter term matches whole values only. A query whose terms match more than"
                f" {MATCH_LIMIT:,} records is refused as `400 QUERY_TOO_BROAD`, whatever parameters narrow"
                f" it. A query holds at most {MAX_TERMS} terms. The definition's parameters narrow the"
                " scored records without changing their scores.",
            ),
            "parameters": [
                {
                    "name": "query",
                    "in": "query",
                    "required": True,
                    "description": "The terms: repeated or comma-separated (a comma inside a term as `%2C`).",
                    **_LISTED,
                },
                {
                    "name": "expect",
                    "in": "query",
                    "description": "`one`: the single best record, `404 NO_MATCH` or `409 AMBIGUOUS_MATCH`.",
                    "schema": {"type": "string", "enum": ["any", "one"], "default": "any"},
                },
                *self._reads(),
                *self._include(),
                *self._definition_parameters(),
                *_PAGING,
            ],
            "responses": _responses(
                {"oneOf": [_ref("XrefPage"), _ref("ScoredObject")]},
                "NO_MATCH, TARGET_NOT_FOUND, WORKSPACE_NOT_FOUND, PUBLICATION_NOT_FOUND",
                conflict="AMBIGUOUS_MATCH, AMBIGUOUS_TARGET, PUBLICATION_CONTRACT_MISMATCH",
                bad=self._bad("QUERY_REQUIRED, TOO_MANY_TERMS, QUERY_TOO_BROAD, INVALID_EXPECT", self._dated_codes()),
            ),
        }

    def _resolve(self) -> dict[str, Any]:
        responses = _responses(
            _ref("ResolveAnswer"),
            "WORKSPACE_NOT_FOUND, PUBLICATION_NOT_FOUND",
            conflict="PUBLICATION_CONTRACT_MISMATCH",
            bad=self._bad("REQUEST_VALIDATION_ERROR", self._dated_codes()),
            tagged=False,
        )
        responses["413"] = {
            "description": f"More than {self.resolve_max_items} items, or a body over 16 KiB for each item allowed: `BATCH_TOO_LARGE`.",
            "content": {"application/json": {"schema": _ref("Error")}},
        }
        return {
            "summary": "Batch resolve",
            "description": self._described(
                "operation:resolve",
                f"Up to {self.resolve_max_items} lookups in one read, each answered as the single read it"
                " stands for: by `query` as XREF with `expect=one`, by `id` as get by ID. Outcomes come in"
                " item order. Answers no `ETag`.",
            ),
            "parameters": self._reads(),
            "requestBody": {"required": True, "content": {"application/json": {"schema": _ref("ResolveRequest")}}},
            "responses": responses,
        }

    def _publications(self) -> dict[str, Any]:
        return {
            "summary": "Publications",
            "description": (
                "The workspace's publications, newest first. `eventSequence` is the feed position of the"
                " publication's `published` entry: live data at that position equals the publication."
            ),
            "parameters": [self.workspace, *_PAGING, _INCLUDE_TOTAL],
            "responses": _responses(_ref("PublicationPage"), "WORKSPACE_NOT_FOUND"),
        }

    def _events(self) -> dict[str, Any]:
        declared = ", ".join(f"`{event.key}`" for event in self.definition.events)
        return {
            "summary": "Events",
            "description": self._described(
                "operation:events",
                f"The changes this API tells its consumers about ({declared}), in position order: `created`,"
                " `updated` naming the watched outputs that changed, `deleted`. Start after a position"
                " (`after`: `0`, or a publication's `eventSequence`) and continue by `cursor`, a lasting"
                " resume token; `caughtUp` says the events derived so far (`headPosition`) are read."
                " With `payload=full` (default) each event carries its object as get by ID answers it with"
                " the same parameters, at the feed position `stateAt`; `payload=identity` leaves it out. A"
                " parameter filters as on a list, against live data; an event whose object no longer exists"
                " passes every parameter but the type. Events are kept as long as the change feed's"
                " entries: an older position is `410 EVENTS_EXPIRED`, naming the publication to re-read.",
            ),
            "parameters": [
                self.workspace,
                _EVENT_NAMES,
                _AFTER,
                _EVENT_CURSOR,
                _EVENT_PAGE_SIZE,
                _PAYLOAD,
                *self._definition_parameters(crosswalk=False),
            ],
            "responses": _responses(
                _ref("EventPage"),
                "EVENTS_NOT_DECLARED, WORKSPACE_NOT_FOUND",
                conflict="EVENT_POSITION_AHEAD",
                bad="UNKNOWN_EVENT, INVALID_PAYLOAD, INVALID_POSITION",
                gone="EVENTS_EXPIRED",
            ),
        }

    # --- schemas ---

    def _schemas(self) -> dict[str, Any]:
        items = {name: self._projection_item(name) for name in self.contract.projections}
        schemas: dict[str, Any] = {f"Projection_{name}": item for name, item in items.items()}
        blocks = {
            name: _with_description(self._projection(name), self.definition.described(f"related:{name}"))
            for name in self.contract.projections
            if not name.startswith(PARENT_BLOCK_PREFIX)
        }
        target = self._target()
        names = type_schema_names(self.definition)
        required_of = self.contract.projections
        for key, public in self.contract.types.items():
            held = self.contract.type_outputs[key]
            properties = {
                "objectType": {"type": "string", "enum": [public]},
                **self._fields(key),
                **{name: block for name, block in blocks.items() if name in held},
                **({"target": target} if target else {}),
            }
            # A block served on request is an optional property: present when the read names it (PP-D30).
            required = [
                name for name in properties if name != "target" and required_of.get(name, {}).get("served") != "onRequest"
            ]
            schemas[names[key]] = {"title": public, **_object(properties, required)}
        mapping = {
            public: f"#/components/schemas/{names[key]}"
            for key, public in self.contract.types.items()
            if names[key] != public
        }
        schemas["Object"] = {
            "oneOf": [_ref(names[key]) for key in self.contract.types],
            "discriminator": {"propertyName": "objectType", **({"mapping": mapping} if mapping else {})},
        }
        schemas["ScoredObject"] = {
            "allOf": [
                _ref("Object"),
                _object({"matchScore": {"type": "integer"}}),
            ]
        }
        page = {
            "workspace": {"type": "string"},
            "publication": {"type": ["string", "null"]},
            "pageSize": {"type": "integer"},
            "nextCursor": {"type": ["string", "null"]},
            "prevCursor": {"type": ["string", "null"]},
            "anchor": {"type": ["string", "null"]},
            "totalCount": {"type": ["integer", "null"]},
            "startIndex": {"type": ["integer", "null"]},
        }
        applied = {
            "asOfApplied": {
                "type": "array",
                "items": {"type": "string"},
                "description": "With `asOf`: the public types dated by their effective period.",
            }
        }
        schemas["ListPage"] = _object(
            {"items": {"type": "array", "items": _ref("Object")}, **page, **applied}, ["items", *page]
        )
        xref = {
            "results": {"type": "array", "items": _ref("ScoredObject")},
            "query": {"type": "array", "items": {"type": "string"}},
            **page,
        }
        schemas["XrefPage"] = _object({**xref, **applied}, list(xref))
        schemas["Publication"] = _object(
            {
                "id": {"type": "string"},
                "publishedAt": {"type": "string", "format": "date-time"},
                "eventSequence": {"type": ["integer", "null"]},
                "status": {"type": "string", "enum": ["active", "withdrawn"]},
            }
        )
        schemas["PublicationPage"] = _object(
            {
                "items": {"type": "array", "items": _ref("Publication")},
                **{name: value for name, value in page.items() if name != "publication"},
            }
        )
        names = {
            name: {**_STRINGS, "description": self._filter_description(name, item)}
            for name, item in self.definition.parameters.items()
        }
        names.update({f"to.{name}": _STRINGS for name in self.targets})
        if self.definition.on_request():
            names["include"] = {**_STRINGS, "description": self._include_description()}
        schemas["ResolveDefaults"] = {"type": "object", "properties": names, "additionalProperties": False}
        schemas["ResolveItem"] = {
            "type": "object",
            "properties": {
                "ref": {"type": "string", "minLength": 1, "maxLength": 200},
                "query": _STRINGS,
                "id": {"type": "string"},
                **names,
            },
            "additionalProperties": False,
        }
        schemas["ResolveRequest"] = _object(
            {
                "defaults": _ref("ResolveDefaults"),
                "items": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": self.resolve_max_items,
                    "items": _ref("ResolveItem"),
                },
            },
            ["items"],
            closed=True,
        )
        schemas["ResolveOutcome"] = _object(
            {
                "index": {"type": "integer"},
                "ref": {"type": ["string", "null"]},
                "status": {"type": "string", "enum": ["found", "not_found", "ambiguous", "rejected"]},
                "object": {"anyOf": [_ref("ScoredObject"), _ref("Object")]},
                "error": _ref("ErrorBody"),
            },
            ["index", "ref", "status"],
        )
        counts = {name: {"type": "integer"} for name in ("found", "notFound", "ambiguous", "rejected")}
        answer = {
            "items": {"type": "array", "items": _ref("ResolveOutcome")},
            "workspace": {"type": "string"},
            "publication": {"type": ["string", "null"]},
            "counts": _object(counts),
        }
        schemas["ResolveAnswer"] = _object({**answer, **applied}, list(answer))
        schemas["ErrorBody"] = {
            "type": "object",
            "properties": {
                "code": {"type": "string"},
                "message": {"type": "string"},
                "details": {"type": "object"},
            },
            "required": ["code", "message"],
        }
        schemas["Error"] = _object({"error": _ref("ErrorBody")})
        if self.definition.events:
            schemas.update(self._event_schemas())
        return schemas

    def _event_schemas(self) -> dict[str, Any]:
        event = {
            "eventId": {"type": "string", "description": "The same event delivered again has the same ID."},
            "position": {"type": "integer", "description": "The feed position of the change that caused it."},
            "occurredAt": {"type": "string", "format": "date-time"},
            "event": {"type": "string", "enum": [item.key for item in self.definition.events]},
            "change": {"type": "string", "enum": ["created", "updated", "deleted"]},
            "contractVersion": {"type": "integer", "description": "The contract version that derived it."},
            "objectType": {"type": "string"},
            "id": {"type": "string"},
            "code": {"description": "The object's code now; null when it no longer exists."},
            "name": {"type": ["string", "null"], "description": "The object's name now; null when it no longer exists."},
            "changed": {"type": "array", "items": {"type": "string"}},
            "cause": _object(
                {"kind": {"type": "string", "enum": ["user", "job", "publication"]}, "id": {"type": "string"}},
                ["kind"],
            ),
        }
        full = {
            "stateAt": {"type": "integer", "description": "The feed position whose state `object` shows."},
            "object": _ref("Object"),
        }
        return {
            "Event": _object({**event, **full}, list(event)),
            "EventPage": _object(
                {
                    "items": {"type": "array", "items": _ref("Event")},
                    "workspace": {"type": "string"},
                    "pageSize": {"type": "integer"},
                    "cursor": {"type": "string"},
                    "caughtUp": {"type": "boolean"},
                    "headPosition": {"type": "integer"},
                    "earliestPosition": {"type": "integer"},
                }
            ),
        }

    def _fields(self, type_key: str) -> dict[str, Any]:
        """The fields of the type's objects (OT-D1): the contract's outputs the type holds."""
        held = self.contract.type_outputs[type_key]
        shape = self.definition.object
        fixed = {shape.id.output}
        if shape.name is not None:
            fixed.add(shape.name.output)
        defaults = {
            field.output for role in ("code", "name", "active", "validFrom", "validTo")
            if (field := getattr(shape, role)) is not None and field.default is not None
        } | {name for name, item in shape.attributes.items() if item.default is not None}
        found: dict[str, Any] = {}
        for name, value_type in self.contract.fields.items():
            if name not in held:
                continue
            if isinstance(value_type, dict):
                fields = self.definition.object.parent.fields
                properties = {}
                for field, kind in value_type["object"].items():
                    sources = fields[field].source
                    if set(sources) <= {"id", "name"} and fields[field].default is None:
                        properties[field] = _value(kind)  # built in and never null
                    elif set(sources) <= {"objectType", "code"}:
                        properties[field] = {"type": ["string", "null"]}
                    else:
                        # A source the parent has no value for, or no binding, is null (CA1).
                        properties[field] = _value(kind) if fields[field].default is not None else _nullable(_value(kind))
                # A parent block is on the parent when the parent's type is an end of its relation (OT-D2);
                # it is always there only when every type this one's parent can be holds it.
                held_blocks = parent_blocks_held(self.model, self.definition, type_key)
                parent_blocks = {
                    block: _with_description(
                        self._projection(f"{PARENT_BLOCK_PREFIX}{block}"),
                        self.definition.described(f"related:{PARENT_BLOCK_PREFIX}{block}"),
                    )
                    for block in self.definition.object.parent.projections
                    if f"{PARENT_BLOCK_PREFIX}{block}" in held_blocks
                }
                required = [
                    *properties,
                    *(
                        block
                        for block in parent_blocks
                        if held_blocks[f"{PARENT_BLOCK_PREFIX}{block}"]
                        and self.contract.projections[f"{PARENT_BLOCK_PREFIX}{block}"].get("served") != "onRequest"
                    ),
                ]
                found[name] = _nullable(_object({**properties, **parent_blocks}, required))
                continue
            schema = _value(value_type)
            if shape.path == name or shape.hierarchy == name or name in fixed or name in defaults:
                found[name] = schema
            else:
                found[name] = _nullable(schema)
        return {
            name: _with_description(schema, self.definition.described(f"field:{name}"))
            for name, schema in found.items()
        }

    def _projection_item(self, name: str) -> dict[str, Any]:
        fields = self.contract.projections[name]["fields"]
        return _object({output: _nullable(_value(kind)) for output, kind in fields.items()})

    def _projection(self, name: str) -> dict[str, Any]:
        item = _ref(f"Projection_{name}")
        if self.contract.projections[name]["shape"] == "many":
            return {"type": "array", "items": item}
        return _nullable(item)

    def _target(self) -> dict[str, Any] | None:
        projections = sorted(
            {
                parameter.projection
                for name in self.targets
                if isinstance(parameter := self.definition.parameters[name], ProjectionParameter)
            }
        )
        if not projections:
            return None
        shapes = []
        for projection in projections:
            item = _ref(f"Projection_{projection}")
            shapes += [item, {"type": "array", "items": item}]
        return {
            "description": (
                "With a `to.` name: the targeted projection's matching items; a single item where the read"
                " answers one object, else in the projection's shape."
            ),
            "anyOf": [*shapes, {"type": "null"}],
        }


def _with_description(schema: dict[str, Any], description: str | None) -> dict[str, Any]:
    return {**schema, "description": description} if description else schema


def _parameter_description(parameter: Any) -> str:
    if isinstance(parameter, ObjectTypeParameter):
        return "Keeps records of these public type names."
    if isinstance(parameter, AncestorParameter):
        return "Keeps records below a record whose fields match a value, at any depth."
    if isinstance(parameter, RelatedParameter):
        return "Keeps records related to a record whose fields match a value."
    if isinstance(parameter, ProjectionParameter):
        text = f"Limits `{parameter.projection}` to the items matching a value"
        if parameter.requireMatch:
            text += ", and keeps only the records left with one"
        if parameter.scoresFrom:
            text += "; on XREF, only those items pass their scores"
        return text + "."
    return ""


_LISTED = {
    "style": "form",
    "explode": True,
    "schema": {"type": "array", "items": {"type": "string"}},
}


def _query(name: str, description: str, extra: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": name,
        "in": "query",
        "description": (
            f"{description} Several values, repeated or comma-separated (a comma inside a value as `%2C`),"
            " are alternatives; text matches ignoring case."
        ),
        **extra,
    }


_WORKSPACE = {
    "name": "workspace",
    "in": "query",
    "description": "The workspace read (default: the deployment's default workspace); named in `RDM-Workspace`.",
    "schema": {"type": "string"},
}
def _workspace_parameter(workspace_key: str | None) -> dict[str, Any]:
    """``workspace``: optional in the default workspace's document; required, with that key as its
    only value, in the document of any other workspace."""
    if workspace_key is None:
        return _WORKSPACE
    return {
        "name": "workspace",
        "in": "query",
        "required": True,
        "description": f"This document describes workspace `{workspace_key}`, which a read must name;"
        " named in `RDM-Workspace`.",
        "schema": {"type": "string", "enum": [workspace_key]},
        "example": workspace_key,
    }


_PUBLICATION = {
    "name": "publication",
    "in": "query",
    "description": (
        "Read a publication of the workspace instead of live data: its ID, or `latest` for the current"
        " one. Read with the definition of the model release it was published under, which must declare"
        " this contract version (`409 PUBLICATION_CONTRACT_MISMATCH`). Named in `RDM-Publication`; a"
        " cursor keeps its publication."
    ),
    "schema": {"type": "string"},
}
def _as_of(dated: str) -> dict[str, Any]:
    return {
        "name": "asOf",
        "in": "query",
        "description": (
            f"A business date, `YYYY-MM-DD`: keeps the records effective that day by their type's declared"
            f" effective period (no start after it, no end on or before it). Dated types: {dated}; records"
            " of other types are not filtered, and a read that can return none of the dated types is"
            " `400 AS_OF_NOT_SUPPORTED`. Projection items and ancestors are not dated. The dated types are"
            " named in `RDM-As-Of-Applied`."
        ),
        "schema": {"type": "string", "format": "date"},
    }


_PAGING = [
    {
        "name": "pageSize",
        "in": "query",
        "schema": {"type": "integer", "minimum": PAGE_SIZE[0], "maximum": PAGE_SIZE[1], "default": PAGE_SIZE[2]},
    },
    {"name": "cursor", "in": "query", "description": "`nextCursor`, `prevCursor` or `anchor` of a page.", "schema": {"type": "string"}},
    {"name": "position", "in": "query", "description": "Start at this position (from 0).", "schema": {"type": "integer", "minimum": 0}},
    {"name": "from", "in": "query", "description": "`end`: the last page.", "schema": {"type": "string", "enum": ["start", "end"]}},
]
_EVENT_NAMES = {
    "name": "event",
    "in": "query",
    "description": "Keep these events (their keys); several, repeated or comma-separated, are alternatives.",
    **_LISTED,
}
_AFTER = {
    "name": "after",
    "in": "query",
    "description": "Start after this position: `0`, or a publication's `eventSequence`. Not with `cursor`.",
    "schema": {"type": "integer", "minimum": 0, "default": 0},
}
_EVENT_CURSOR = {
    "name": "cursor",
    "in": "query",
    "description": "`cursor` of a page: continue after it, with the same events and parameters.",
    "schema": {"type": "string"},
}
_EVENT_PAGE_SIZE = {
    "name": "pageSize",
    "in": "query",
    "description": (
        f"1–{EVENT_PAGE_SIZES[FULL][0]:,} with `payload=full` (default {EVENT_PAGE_SIZES[FULL][1]:,}),"
        f" 1–{EVENT_PAGE_SIZES[IDENTITY][0]:,} with `payload=identity`"
        f" (default {EVENT_PAGE_SIZES[IDENTITY][1]:,})."
    ),
    "schema": {"type": "integer", "minimum": 1, "maximum": max(size for size, _ in EVENT_PAGE_SIZES.values())},
}
_PAYLOAD = {
    "name": "payload",
    "in": "query",
    "description": "`full`: each event with its object; `identity`: without it.",
    "schema": {"type": "string", "enum": ["full", "identity"], "default": "full"},
}
_SEEK = {"name": "seek", "in": "query", "description": "Start at this sort value.", "schema": {"type": "string"}}
_INCLUDE_TOTAL = {
    "name": "includeTotal",
    "in": "query",
    "description": "Count `totalCount` and `startIndex`.",
    "schema": {"type": "boolean", "default": False},
}
_HEADERS = {
    "ETag": {"description": "The answer's version; send it back as `If-None-Match`.", "schema": {"type": "string"}},
    "RDM-Workspace": {"description": "The workspace read.", "schema": {"type": "string"}},
    "RDM-Publication": {"description": "The publication read, on a pinned read.", "schema": {"type": "string"}},
    "RDM-As-Of-Applied": {
        "description": "On a read with `asOf`: the public types it dated, comma-separated.",
        "schema": {"type": "string"},
    },
}
_RESPONSES = {
    "NotModified": {
        "description": "Unchanged since the `If-None-Match` tag.",
        "headers": {"ETag": {"$ref": "#/components/headers/ETag"}},
    },
    "Unauthorized": {
        "description": "No access token (AUTHENTICATION_REQUIRED), or one refused (TOKEN_INVALID, with"
        " `details.reason`); with `WWW-Authenticate: Bearer`.",
        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}},
    },
    "Forbidden": {
        "description": "FORBIDDEN: the client holds no grant of this consumer API in the workspace read"
        " (`details`: `consumerApi`, `workspaceKey`).",
        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}},
    },
}


def _responses(
    ok: dict[str, Any],
    missing: str,
    *,
    conflict: str | None = None,
    bad: str | None = None,
    gone: str | None = None,
    tagged: bool = True,
) -> dict[str, Any]:
    headers = {
        "RDM-Workspace": {"$ref": "#/components/headers/RDM-Workspace"},
        "RDM-Publication": {"$ref": "#/components/headers/RDM-Publication"},
        "RDM-As-Of-Applied": {"$ref": "#/components/headers/RDM-As-Of-Applied"},
    }
    if tagged:
        headers["ETag"] = {"$ref": "#/components/headers/ETag"}
    error = {"content": {"application/json": {"schema": _ref("Error")}}}
    refused = "UNKNOWN_PARAMETER, PARAMETER_NOT_SUPPORTED, UNKNOWN_OBJECT_TYPE, MULTIPLE_TARGETS, the paging codes"
    responses: dict[str, Any] = {
        "200": {"description": "The answer.", "headers": headers, "content": {"application/json": {"schema": ok}}},
        "401": {"$ref": "#/components/responses/Unauthorized"},
        "403": {"$ref": "#/components/responses/Forbidden"},
        "400": {"description": f"A request error: {', '.join(filter(None, [bad, refused]))}.", **error},
        "404": {
            "description": f"Not found: {missing}, CONSUMER_API_NOT_FOUND, CONTRACT_VERSION_NOT_FOUND.",
            **error,
        },
    }
    if tagged:
        responses["304"] = {"$ref": "#/components/responses/NotModified"}
    if conflict:
        responses["409"] = {"description": f"Conflict: {conflict}.", **error}
    if gone:
        responses["410"] = {"description": f"Gone: {gone}.", **error}
    return dict(sorted(responses.items()))
