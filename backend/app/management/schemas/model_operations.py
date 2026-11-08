"""The draft operations as the OpenAPI document describes them (Product 0.13 AQ).

``POST /model-drafts/{id}/operations`` takes a list of operations, each ``{"kind": …, …}``. The kinds
and the parameters each allows live in one place, the registry in ``engine/model/authoring/kinds.py``
(``KINDS``, ``PARAMETERS``, a kind's docstring); the engine checks an operation against it and refuses
what it cannot apply. The schemas here are generated from that registry and only describe it: one
object per public kind, discriminated by ``kind``, with the kind's docstring as its description.
"""

from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, create_model
from pydantic.json_schema import JsonSchemaValue

from ...engine.model.authoring.kinds import INTERNAL_KINDS, KINDS, PARAMETERS


def _described(schema: JsonSchemaValue) -> None:
    """A parameter is optional in the description (the kind decides which it needs); none has a default."""
    for member in schema.get("properties", {}).values():
        member.pop("default", None)
    schema.pop("required", None)
    schema["required"] = ["kind"]


class _Operation(BaseModel):
    model_config = ConfigDict(extra="forbid", json_schema_extra=_described)


def operation_schema_name(kind: str) -> str:
    return f"{kind[0].upper()}{kind[1:]}Operation"


def _schema_of(kind: str) -> type[BaseModel]:
    fields: dict[str, Any] = {name: (Any, Field(default=None)) for name in PARAMETERS[kind]}
    return create_model(
        operation_schema_name(kind),
        __base__=_Operation,
        __doc__=" ".join((KINDS[kind].__doc__ or "").split()),
        kind=(Literal[kind], Field(description="The operation's kind")),
        **fields,
    )


OPERATION_SCHEMAS: dict[str, type[BaseModel]] = {
    kind: _schema_of(kind) for kind in sorted(KINDS) if kind not in INTERNAL_KINDS
}

DraftOperation = Annotated[
    Union[tuple(OPERATION_SCHEMAS.values())],  # noqa: UP007  (built from the registry)
    Field(discriminator="kind"),
]
