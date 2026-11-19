"""A draft's consumer API definition and the documents an integration takes from it (0.10 A4c, D56).

The editor and an integrator read, from a draft before it is installed: the definition as written
and with every default written out, its contract against what the active release's consumers read,
and three documents, each a download of its own:

- the **schema**: the JSON Schema (2020-12) of the object message consumers receive, the ``Object``
  component of the definition's OpenAPI document (a union of the types' schemas) with the schemas it
  refers to, or one type's schema, which an integration validates messages against or generates its
  types from;
- a **message example**: one message of a type valid against that schema, written from it (a value of
  each property's type, a related block as one object or a list of one); no record is read, so the
  consumer tier never reads a model that is not running (D44, D45);
- the definition's **OpenAPI document**, as the consumer tier will serve it.
"""

from typing import Any

from ....errors import api_error
from ....models.database import ModelDraft
from ....models.schema import EngineModel
from ..compiler import compile_model
from ..consumer_contract import KEPT_VERSION_CHANGED, contract_diagnostics
from ..consumer_definitions import consumer_api
from ..consumer_examples import example_of
from ..consumer_openapi import consumer_openapi, type_schema_names
from ..consumer_rendering import expanded_definition
from .outline import diagnostic_with_element

JSON_SCHEMA = "https://json-schema.org/draft/2020-12/schema"
_REF = "#/components/schemas/"


def draft_consumer_api(draft: ModelDraft, key: str, active: EngineModel | None) -> dict[str, Any]:
    """The definition ``key`` of the draft, with its defaults and contract when the draft compiles;
    against ``active``, the model it is compared with, and compatible without one (a new model)."""
    data = draft.model_json if isinstance(draft.model_json, dict) else {}
    written = next(
        (item for item in data.get("consumerApis") or [] if isinstance(item, dict) and item.get("key") == key),
        None,
    )
    if written is None:
        raise _not_found(draft, key)
    compiled = compile_model(draft.model_json)
    answer: dict[str, Any] = {"version": draft.version, "valid": compiled.valid, "definition": written}
    if compiled.valid and compiled.model is not None:
        definition = consumer_api(compiled.model, key)
        if definition is not None:
            answer["expanded"] = expanded_definition(compiled.model, definition)
        prefix = f"/consumerApis/{key.replace('~', '~0').replace('/', '~1')}"
        mine = [
            item
            for item in (contract_diagnostics(active, compiled.model) if active is not None else ())
            if item.path == prefix or item.path.startswith(f"{prefix}/")
        ]
        answer["contract"] = {
            "classification": "version_required" if any(item.severity == "error" and item.code != KEPT_VERSION_CHANGED for item in mine) else "compatible",
            "diagnostics": [diagnostic_with_element(data, item) for item in mine],
        }
    return answer


def draft_openapi(
    draft: ModelDraft, key: str, *, root_path: str, resolve_max_items: int, token_url: str
) -> dict[str, Any]:
    """The definition's OpenAPI document as the consumer tier will serve it from this draft."""
    model, definition = _compiled(draft, key)
    return consumer_openapi(
        model, definition, root_path=root_path, resolve_max_items=resolve_max_items, token_url=token_url
    )


def draft_schema(
    draft: ModelDraft, key: str, *, resolve_max_items: int, object_type: str | None = None
) -> dict[str, Any]:
    """The JSON Schema of the object message: the OpenAPI document's ``Object`` (a union of the types'
    schemas) and what it refers to; with ``object_type`` (a public name) that one type's schema (OT-D5)."""
    # Only the schemas are taken, so the token URL is never read.
    model, definition = _compiled(draft, key)
    document = consumer_openapi(
        model, definition, root_path="", resolve_max_items=resolve_max_items, token_url=""
    )
    root = "Object"
    title = document["info"]["title"]
    if object_type is not None:
        by_name = {item.publicName: type_key for type_key, item in definition.objectTypes.items()}
        if object_type not in by_name:
            public = sorted(by_name)
            raise api_error(
                400,
                "UNKNOWN_OBJECT_TYPE",
                f"Unknown object type '{object_type}'; this API exposes {', '.join(public)}",
                {"objectTypes": [object_type], "publicNames": public, "path": "/query/objectType"},
            )
        root = type_schema_names(definition)[by_name[object_type]]
        title = object_type
    return object_schema(document, title=title, root=root)


def draft_example(
    draft: ModelDraft, key: str, *, resolve_max_items: int, object_type: str | None = None
) -> dict[str, Any]:
    """One object message valid against :func:`draft_schema`; of ``object_type`` when named, else of the
    first type the definition exposes (OT-D5)."""
    if object_type is None:
        _model, definition = _compiled(draft, key)
        object_type = next(iter(definition.objectTypes.values())).publicName
    schema = draft_schema(draft, key, resolve_max_items=resolve_max_items, object_type=object_type)
    return example_of(schema, schema.get("$defs", {}), "", object_type)


def object_schema(document: dict[str, Any], *, title: str, root: str = "Object") -> dict[str, Any]:
    schemas = document["components"]["schemas"]
    wanted: dict[str, Any] = {}

    def collect(node: Any) -> None:
        if isinstance(node, dict):
            reference = node.get("$ref")
            if isinstance(reference, str) and reference.startswith(_REF):
                name = reference.removeprefix(_REF)
                if name not in wanted:
                    wanted[name] = schemas[name]
                    collect(schemas[name])
            for value in node.values():
                collect(value)
        elif isinstance(node, list):
            for value in node:
                collect(value)

    start = schemas[root]
    collect(start)
    wanted.pop(root, None)
    schema = {"$schema": JSON_SCHEMA, **_relinked(start), "title": title}
    if wanted:
        schema["$defs"] = {name: _relinked(value) for name, value in wanted.items()}
    return schema


def _relinked(node: Any, parent: str = "") -> Any:
    """``$ref`` pointers and a discriminator's ``mapping`` targets rewritten from the OpenAPI document's
    components to this document's ``$defs``."""
    if isinstance(node, dict):
        return {
            name: (
                f"#/$defs/{value.removeprefix(_REF)}"
                if isinstance(value, str)
                and value.startswith(_REF)
                and (name == "$ref" or parent == "mapping")
                else _relinked(value, name)
            )
            for name, value in node.items()
        }
    if isinstance(node, list):
        return [_relinked(value) for value in node]
    return node


def _compiled(draft: ModelDraft, key: str) -> tuple[EngineModel, Any]:
    data = draft.model_json if isinstance(draft.model_json, dict) else {}
    if not any(isinstance(item, dict) and item.get("key") == key for item in data.get("consumerApis") or []):
        raise _not_found(draft, key)
    compiled = compile_model(draft.model_json)
    if not compiled.valid or compiled.model is None:
        raise api_error(
            422,
            "INVALID_MODEL",
            f"Model draft '{draft.public_id}' does not compile; its consumer API documents are written from a valid draft",
            {"diagnostics": [diagnostic_with_element(data, item) for item in compiled.diagnostics]},
        )
    definition = consumer_api(compiled.model, key)
    if definition is None:
        raise _not_found(draft, key)
    return compiled.model, definition


def _not_found(draft: ModelDraft, key: str) -> Exception:
    return api_error(
        404,
        "CONSUMER_API_NOT_FOUND",
        f"Model draft '{draft.public_id}' declares no consumer API '{key}'",
        {"consumerApi": key},
    )
