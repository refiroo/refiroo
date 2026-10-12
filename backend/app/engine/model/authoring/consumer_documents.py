"""A draft's consumer API definition and the documents an integration takes from it (0.10 A4c, D56).

The editor and an integrator read, from a draft before it is installed: the definition as written
and with every default written out, its contract against what the active release's consumers read,
and three documents, each a download of its own:

- the **schema**: the JSON Schema (2020-12) of the object message consumers receive, the ``Object``
  component of the definition's OpenAPI document with the schemas it refers to, which an integration
  validates messages against or generates its types from;
- a **message example**: one message valid against that schema, written from it (a value of each
  property's type, a related block as one object or a list of one); no record is read, so the
  consumer tier never reads a model that is not running (D44, D45);
- the definition's **OpenAPI document**, as the consumer tier will serve it.
"""

from typing import Any

from ....errors import api_error
from ....models.database import ModelDraft
from ....models.schema import EngineModel
from ..compiler import compile_authored_model
from ..consumer_contract import contract_diagnostics
from ..consumer_definitions import consumer_api
from ..consumer_openapi import consumer_openapi
from ..consumer_rendering import expanded_definition
from .outline import diagnostic_with_element

JSON_SCHEMA = "https://json-schema.org/draft/2020-12/schema"
_REF = "#/components/schemas/"


def draft_consumer_api(draft: ModelDraft, key: str, active: EngineModel) -> dict[str, Any]:
    """The definition ``key`` of the draft, with its defaults and contract when the draft compiles."""
    data = draft.model_json if isinstance(draft.model_json, dict) else {}
    written = next(
        (item for item in data.get("consumerApis") or [] if isinstance(item, dict) and item.get("key") == key),
        None,
    )
    if written is None:
        raise _not_found(draft, key)
    compiled = compile_authored_model(draft.model_json)
    answer: dict[str, Any] = {"version": draft.version, "valid": compiled.valid, "definition": written}
    if compiled.valid and compiled.model is not None:
        definition = consumer_api(compiled.model, key)
        if definition is not None:
            answer["expanded"] = expanded_definition(compiled.model, definition)
        prefix = f"/consumerApis/{key.replace('~', '~0').replace('/', '~1')}"
        mine = [
            item
            for item in contract_diagnostics(active, compiled.model)
            if item.path == prefix or item.path.startswith(f"{prefix}/")
        ]
        answer["contract"] = {
            "classification": "version_required" if any(item.severity == "error" for item in mine) else "compatible",
            "diagnostics": [diagnostic_with_element(data, item) for item in mine],
        }
    return answer


def draft_openapi(draft: ModelDraft, key: str, *, root_path: str, resolve_max_items: int) -> dict[str, Any]:
    """The definition's OpenAPI document as the consumer tier will serve it from this draft."""
    model, definition = _compiled(draft, key)
    return consumer_openapi(model, definition, root_path=root_path, resolve_max_items=resolve_max_items)


def draft_schema(draft: ModelDraft, key: str, *, resolve_max_items: int) -> dict[str, Any]:
    """The JSON Schema of the object message: the OpenAPI document's ``Object`` and what it refers to."""
    document = draft_openapi(draft, key, root_path="", resolve_max_items=resolve_max_items)
    return object_schema(document, title=document["info"]["title"])


def draft_example(draft: ModelDraft, key: str, *, resolve_max_items: int) -> dict[str, Any]:
    """One object message valid against :func:`draft_schema`."""
    schema = draft_schema(draft, key, resolve_max_items=resolve_max_items)
    return example_of(schema, schema.get("$defs", {}))


def object_schema(document: dict[str, Any], *, title: str) -> dict[str, Any]:
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

    root = schemas["Object"]
    collect(root)
    wanted.pop("Object", None)
    schema = {"$schema": JSON_SCHEMA, "title": title, **_relinked(root)}
    if wanted:
        schema["$defs"] = {name: _relinked(value) for name, value in wanted.items()}
    return schema


def _relinked(node: Any) -> Any:
    if isinstance(node, dict):
        return {
            name: (f"#/$defs/{value.removeprefix(_REF)}" if name == "$ref" and isinstance(value, str) else _relinked(value))
            for name, value in node.items()
        }
    if isinstance(node, list):
        return [_relinked(value) for value in node]
    return node


_STRINGS = {"date": "2026-01-01", "date-time": "2026-01-01T09:00:00Z", "uuid": "7f3c2a9e-1b4d-4c8a-9e21-5d0f6b8a3c11"}


def example_of(schema: Any, defs: dict[str, Any], name: str = "") -> Any:
    """A value valid against ``schema``: the first choice of a union that is not null, an enum's
    first value, and a value of each type otherwise."""
    if not isinstance(schema, dict):
        return None
    reference = schema.get("$ref")
    if isinstance(reference, str):
        return example_of(defs.get(reference.removeprefix("#/$defs/"), {}), defs, name)
    if "const" in schema:
        return schema["const"]
    if schema.get("enum"):
        return schema["enum"][0]
    for union in ("anyOf", "oneOf"):
        if isinstance(schema.get(union), list):
            choices = [item for item in schema[union] if item.get("type") != "null"] or schema[union]
            return example_of(choices[0], defs, name)
    kind = schema.get("type")
    if isinstance(kind, list):
        kind = next((item for item in kind if item != "null"), "null")
    if kind == "object" or "properties" in schema:
        return {prop: example_of(value, defs, prop) for prop, value in (schema.get("properties") or {}).items()}
    if kind == "array":
        return [example_of(schema.get("items", {}), defs, name)]
    if kind == "string":
        return _STRINGS.get(schema.get("format", ""), f"Example {name}".strip())
    if kind == "integer":
        return 1
    if kind == "number":
        return 1.5
    if kind == "boolean":
        return True
    if kind == "null":
        return None
    return f"Example {name}".strip()


def _compiled(draft: ModelDraft, key: str) -> tuple[EngineModel, Any]:
    data = draft.model_json if isinstance(draft.model_json, dict) else {}
    if not any(isinstance(item, dict) and item.get("key") == key for item in data.get("consumerApis") or []):
        raise _not_found(draft, key)
    compiled = compile_authored_model(draft.model_json)
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
