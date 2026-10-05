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

from typing import Any

from ...models.schema import (
    AncestorParameter,
    ConsumerApiDefinition,
    EngineModel,
    ObjectTypeParameter,
    ProjectionParameter,
    RelatedParameter,
)
from ..model.consumer_contract import OutputContract, output_contract, parent_keys

OPENAPI_VERSION = "3.1.0"
# The read limits the document states (CONSUMER_API C-D30, C-D37, C-D38).
PAGE_SIZE = (1, 100, 20)
MIN_CONTAINS = 3
MATCH_LIMIT = 10_000
MAX_TERMS = 100
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
    model: EngineModel, definition: ConsumerApiDefinition, *, root_path: str, resolve_max_items: int
) -> dict[str, Any]:
    """The OpenAPI 3.1 document of ``definition`` as the active release ``model`` declares it."""
    return _Document(model, definition, root_path, resolve_max_items).build()


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


def _object(properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties) if required is None else required,
        "additionalProperties": False,
    }


class _Document:
    def __init__(
        self, model: EngineModel, definition: ConsumerApiDefinition, root_path: str, resolve_max_items: int
    ) -> None:
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
        paths: dict[str, Any] = {
            f"{self.base}/objects/{{id}}": {"get": self._get_by_id()},
            **{f"{self.base}/lists/{item.key}": {"get": self._list(item.key)} for item in definition.lists},
            f"{self.base}/xref": {"get": self._xref()},
            f"{self.base}/resolve": {"post": self._resolve()},
            f"{self.base}/publications": {"get": self._publications()},
        }
        intro = f"{definition.description}\n\n" if definition.description else ""
        return {
            "openapi": OPENAPI_VERSION,
            "info": {
                "title": definition.name,
                "version": str(definition.contractVersion),
                "description": (
                    f"{intro}Consumer API `{definition.key}`, contract version {definition.contractVersion},"
                    f" declared by the model release {release.name} {release.version}. A read takes the live"
                    " data of a workspace (`workspace`, default: the deployment's default workspace) or one"
                    " of its publications (`publication`: an ID or `latest`). Every `GET` answers an `ETag`"
                    " and `304 Not Modified` to a matching `If-None-Match`."
                ),
            },
            "servers": [{"url": self.root_path or "/"}],
            "paths": paths,
            "components": {"schemas": self._schemas(), "headers": _HEADERS, "responses": _RESPONSES},
        }

    # --- parameters ---

    def _definition_parameters(self, parent: str | None = None) -> list[dict[str, Any]]:
        """The definition's parameters and their ``to.`` names. On a list whose parent parameter shares
        a definition parameter's name, the name addresses the parent there, so it is listed once, as
        the parent (C1; the consumer router reads it so)."""
        found = []
        for name, parameter in self.definition.parameters.items():
            if name != parent:
                found.append(_query(name, _parameter_description(parameter), _LISTED))
        for name in self.targets:
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

    def _reads(self) -> list[dict[str, Any]]:
        return [_WORKSPACE, _PUBLICATION]

    def _get_by_id(self) -> dict[str, Any]:
        return {
            "summary": "Get by ID",
            "description": (
                "The shared object of the record with this object ID. The definition's parameters filter"
                " it (`404 OBJECT_NOT_FOUND` when filtered out) and limit its projections."
            ),
            "parameters": [
                {"name": "id", "in": "path", "required": True, "schema": {"type": "string"}},
                *self._reads(),
                *self._definition_parameters(),
            ],
            "responses": _responses(_ref("Object"), "OBJECT_NOT_FOUND, WORKSPACE_NOT_FOUND, PUBLICATION_NOT_FOUND, TARGET_NOT_FOUND", conflict="AMBIGUOUS_TARGET, PUBLICATION_CONTRACT_MISMATCH"),
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
        return {
            "summary": f"List {key}",
            "description": (
                f"Every {public} record, ordered by {order}, then creation order (in a publication, object ID)."
                f" Paged with cursors both ways, `position`, `from=end`, `seek` and `includeTotal`;"
                f" `pageSize` {PAGE_SIZE[0]}–{PAGE_SIZE[1]}, default {PAGE_SIZE[2]}."
            ),
            "parameters": [
                *parent,
                *self._reads(),
                *self._definition_parameters(
                    declared.parentParameter.name if declared.parentParameter is not None else None
                ),
                *_PAGING,
                _SEEK,
                _INCLUDE_TOTAL,
            ],
            "responses": _responses(_ref("ListPage"), "LIST_NOT_FOUND, PARENT_NOT_FOUND, WORKSPACE_NOT_FOUND, PUBLICATION_NOT_FOUND", conflict="PUBLICATION_CONTRACT_MISMATCH"),
        }

    def _xref(self) -> dict[str, Any]:
        return {
            "summary": "XREF lookup",
            "description": (
                "The exposed records the query's terms match, scored by the definition's match rules, best"
                " first (score, public type name, name, object ID); with `expect=one`, the single best one."
                f" Matching part of a value (contains) needs a term of at least {MIN_CONTAINS} characters; a"
                f" shorter term matches whole values only. A query whose terms match more than"
                f" {MATCH_LIMIT:,} records is refused as `400 QUERY_TOO_BROAD`, whatever parameters narrow"
                f" it. A query holds at most {MAX_TERMS} terms. The definition's parameters narrow the"
                " scored records without changing their scores."
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
                *self._definition_parameters(),
                *_PAGING,
            ],
            "responses": _responses(
                {"oneOf": [_ref("XrefPage"), _ref("ScoredObject")]},
                "NO_MATCH, TARGET_NOT_FOUND, WORKSPACE_NOT_FOUND, PUBLICATION_NOT_FOUND",
                conflict="AMBIGUOUS_MATCH, AMBIGUOUS_TARGET, PUBLICATION_CONTRACT_MISMATCH",
                bad="QUERY_REQUIRED, TOO_MANY_TERMS, QUERY_TOO_BROAD, INVALID_EXPECT",
            ),
        }

    def _resolve(self) -> dict[str, Any]:
        responses = _responses(
            _ref("ResolveAnswer"),
            "WORKSPACE_NOT_FOUND, PUBLICATION_NOT_FOUND",
            conflict="PUBLICATION_CONTRACT_MISMATCH",
            bad="REQUEST_VALIDATION_ERROR",
            tagged=False,
        )
        responses["413"] = {
            "description": f"More than {self.resolve_max_items} items: `BATCH_TOO_LARGE`.",
            "content": {"application/json": {"schema": _ref("Error")}},
        }
        return {
            "summary": "Batch resolve",
            "description": (
                f"Up to {self.resolve_max_items} lookups in one read, each answered as the single read it"
                " stands for: by `query` as XREF with `expect=one`, by `id` as get by ID. Outcomes come in"
                " item order. Answers no `ETag`."
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
            "parameters": [_WORKSPACE, *_PAGING, _INCLUDE_TOTAL],
            "responses": _responses(_ref("PublicationPage"), "WORKSPACE_NOT_FOUND"),
        }

    # --- schemas ---

    def _schemas(self) -> dict[str, Any]:
        items = {name: self._projection_item(name) for name in self.contract.projections}
        schemas: dict[str, Any] = {f"Projection_{name}": item for name, item in items.items()}
        properties = {
            "objectType": {"type": "string", "enum": sorted(set(self.contract.types.values()))},
            **self._fields(),
            **{name: self._projection(name) for name in self.contract.projections},
        }
        target = self._target()
        shared = {**properties, **({"target": target} if target else {})}
        schemas["Object"] = _object(shared, list(properties))
        schemas["ScoredObject"] = _object(
            {**shared, "matchScore": {"type": "integer"}}, [*properties, "matchScore"]
        )
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
        schemas["ListPage"] = _object({"items": {"type": "array", "items": _ref("Object")}, **page})
        schemas["XrefPage"] = _object(
            {
                "results": {"type": "array", "items": _ref("ScoredObject")},
                "query": {"type": "array", "items": {"type": "string"}},
                **page,
            }
        )
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
        names = {name: {**_STRINGS, "description": _parameter_description(item)} for name, item in self.definition.parameters.items()}
        names.update({f"to.{name}": _STRINGS for name in self.targets})
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
        schemas["ResolveAnswer"] = _object(
            {
                "items": {"type": "array", "items": _ref("ResolveOutcome")},
                "workspace": {"type": "string"},
                "publication": {"type": ["string", "null"]},
                "counts": _object(counts),
            }
        )
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
        return schemas

    def _fields(self) -> dict[str, Any]:
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
            if isinstance(value_type, dict):
                # A parent's type is null when not exposed (C-D22), its code when it has none.
                keys = parent_keys(self.definition)
                nullable = {keys[name] for name in ("objectType", "code") if name in keys}
                properties = {
                    field: {"type": ["string", "null"]} if field in nullable else _value(kind)
                    for field, kind in value_type["object"].items()
                }
                found[name] = _nullable(_object(properties))
                continue
            schema = _value(value_type)
            if shape.path == name or shape.hierarchy == name or name in fixed or name in defaults:
                found[name] = schema
            else:
                found[name] = _nullable(schema)
        return found

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
}
_RESPONSES = {
    "NotModified": {
        "description": "Unchanged since the `If-None-Match` tag.",
        "headers": {"ETag": {"$ref": "#/components/headers/ETag"}},
    }
}


def _responses(
    ok: dict[str, Any], missing: str, *, conflict: str | None = None, bad: str | None = None, tagged: bool = True
) -> dict[str, Any]:
    headers = {
        "RDM-Workspace": {"$ref": "#/components/headers/RDM-Workspace"},
        "RDM-Publication": {"$ref": "#/components/headers/RDM-Publication"},
    }
    if tagged:
        headers["ETag"] = {"$ref": "#/components/headers/ETag"}
    error = {"content": {"application/json": {"schema": _ref("Error")}}}
    refused = "UNKNOWN_PARAMETER, PARAMETER_NOT_SUPPORTED, UNKNOWN_OBJECT_TYPE, MULTIPLE_TARGETS, the paging codes"
    responses: dict[str, Any] = {
        "200": {"description": "The answer.", "headers": headers, "content": {"application/json": {"schema": ok}}},
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
    return dict(sorted(responses.items()))
