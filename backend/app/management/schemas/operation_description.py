"""How an operation kind's parameters are described in the OpenAPI document.

The kinds (``engine/model/authoring/kinds.py``, ``engine/moves/mapping_kinds.py``) own what they
check; the tables built with these helpers only describe it: for each parameter a JSON schema type,
whether the kind refuses it as missing, and one plain sentence. Nothing here validates a request.
"""

from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, create_model
from pydantic.json_schema import JsonSchemaValue


@dataclass(frozen=True)
class Param:
    """One parameter of a kind: its JSON schema (without the description), the description, whether
    the kind refuses its absence (``required``) and, for a parameter needed only under a condition,
    ``when``: the sentence stating it, added to the description."""

    schema: dict[str, Any]
    description: str
    required: bool = False
    when: str | None = None

    @property
    def needed(self) -> bool:
        return self.required or self.when is not None


TEXT: dict[str, Any] = {"type": "string"}
INTEGER: dict[str, Any] = {"type": "integer"}
BOOLEAN: dict[str, Any] = {"type": "boolean"}
OBJECT: dict[str, Any] = {"type": "object"}
ANY: dict[str, Any] = {}


def array(items: dict[str, Any]) -> dict[str, Any]:
    return {"type": "array", "items": items}


def one_of(*values: str) -> dict[str, Any]:
    return {"type": "string", "enum": list(values)}


def nullable(schema: dict[str, Any]) -> dict[str, Any]:
    return {"anyOf": [schema, {"type": "null"}]}


def either(*schemas: dict[str, Any]) -> dict[str, Any]:
    return {"anyOf": list(schemas)}


def req(schema: dict[str, Any], description: str) -> Param:
    return Param(schema, description, required=True)


def opt(schema: dict[str, Any], description: str) -> Param:
    return Param(schema, description)


def cond(schema: dict[str, Any], description: str, when: str) -> Param:
    return Param(schema, description, when=when)


def shape(
    members: dict[str, Param], description: str | None = None, *, closed: bool = True
) -> dict[str, Any]:
    """An object schema whose members are described; ``closed`` when the code refuses any other."""
    result: dict[str, Any] = {
        "type": "object",
        "properties": {
            name: {**p.schema, "description": p.description} for name, p in members.items()
        },
    }
    required = [name for name, p in members.items() if p.required]
    if required:
        result["required"] = required
    if closed:
        result["additionalProperties"] = False
    if description:
        result["description"] = description
    return result


def property_schema(parameter: Param) -> dict[str, Any]:
    description = parameter.description
    if parameter.when:
        description = f"{description} {parameter.when}"
    return {**parameter.schema, "description": description}


def operation_model(
    name: str, kind: str, summary: str, parameters: dict[str, Param]
) -> type[BaseModel]:
    """The schema of one kind: ``kind`` fixed, each parameter typed and described, ``kind`` and the
    parameters the kind refuses as missing required. The schema only describes: a request keeps the
    engine's checks and their refusal codes (an unknown parameter is ``unknownParameter``, not a
    schema error)."""
    required = ["kind", *(member for member, parameter in parameters.items() if parameter.required)]

    def described(schema: JsonSchemaValue) -> None:
        properties = schema.setdefault("properties", {})
        for member, parameter in parameters.items():
            properties[member] = property_schema(parameter)
        schema["required"] = required

    class Operation(BaseModel):
        model_config = ConfigDict(extra="forbid", json_schema_extra=described)

    fields: dict[str, Any] = {member: (Any, Field(default=None)) for member in parameters}
    return create_model(
        name,
        __base__=Operation,
        __doc__=summary,
        kind=(Literal[kind], Field(description="The operation's kind")),  # type: ignore[valid-type]
        **fields,
    )
