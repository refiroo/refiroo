"""A value valid against a schema, written from the schema alone (D56, OT-D4).

The editor's message example and the per-type examples of a consumer API's OpenAPI document are written
the same way: a value of each property's type, no record read, so no workspace data is published.
"""

from typing import Any

_STRINGS = {
    "date": "2026-01-01",
    "date-time": "2026-01-01T09:00:00Z",
    "uuid": "7f3c2a9e-1b4d-4c8a-9e21-5d0f6b8a3c11",
}


def example_of(
    schema: Any, defs: dict[str, Any], name: str = "", object_type: str | None = None
) -> Any:
    """A value valid against ``schema``: the first choice of a union that is not null, an enum's
    first value, and a value of each type otherwise. A union of object types (a discriminator on
    ``objectType``) takes the choice named ``object_type`` when one is; ``allOf`` merges its parts."""
    if not isinstance(schema, dict):
        return None
    reference = schema.get("$ref")
    if isinstance(reference, str):
        return example_of(defs.get(reference.rsplit("/", 1)[-1], {}), defs, name, object_type)
    if "const" in schema:
        return schema["const"]
    if schema.get("enum"):
        return schema["enum"][0]
    if isinstance(schema.get("allOf"), list):
        merged: dict[str, Any] = {}
        for part in schema["allOf"]:
            value = example_of(part, defs, name, object_type)
            if isinstance(value, dict):
                merged.update(value)
        return merged
    for union in ("anyOf", "oneOf"):
        if isinstance(schema.get(union), list):
            choices = [item for item in schema[union] if item.get("type") != "null"] or schema[
                union
            ]
            if object_type is not None:
                chosen = next(
                    (item for item in choices if _names_type(item, defs, object_type)), None
                )
                if chosen is not None:
                    return example_of(chosen, defs, name, object_type)
            return example_of(choices[0], defs, name, object_type)
    kind = schema.get("type")
    if isinstance(kind, list):
        kind = next((item for item in kind if item != "null"), "null")
    if kind == "object" or "properties" in schema:
        return {
            prop: example_of(value, defs, prop, object_type)
            for prop, value in (schema.get("properties") or {}).items()
        }
    if kind == "array":
        return [example_of(schema.get("items", {}), defs, name, object_type)]
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


def _names_type(schema: Any, defs: dict[str, Any], object_type: str) -> bool:
    """Whether ``schema`` is, or is a union or an ``allOf`` holding, the object schema of the public type
    ``object_type``."""
    if not isinstance(schema, dict):
        return False
    reference = schema.get("$ref")
    if isinstance(reference, str):
        return _names_type(defs.get(reference.rsplit("/", 1)[-1], {}), defs, object_type)
    kind = ((schema.get("properties") or {}).get("objectType") or {}).get("enum")
    if kind is not None:
        return kind == [object_type]
    return any(
        _names_type(part, defs, object_type)
        for key in ("allOf", "oneOf", "anyOf")
        for part in schema.get(key, ())
    )
