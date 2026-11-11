"""The draft operations as the OpenAPI document describes them.

``POST /model-drafts/{id}/operations`` takes a list of operations, each ``{"kind": …, …}``. The kinds
and the parameters each allows live in one place, the registry in ``engine/model/authoring/kinds.py``
(``KINDS``, ``PARAMETERS``, a kind's docstring); the engine checks an operation against it and refuses
what it cannot apply, with its own codes. The schemas here describe the registry and validate
nothing: one object per public kind, discriminated by ``kind``, its docstring as the description and
each parameter typed and described by the table in ``model_operation_parameters.py``.
"""

from typing import Annotated, Union

from pydantic import BaseModel, Field

from ...engine.model.authoring.kinds import INTERNAL_KINDS, KINDS
from .model_operation_parameters import PARAMETERS as DESCRIBED
from .operation_description import operation_model


def operation_schema_name(kind: str) -> str:
    return f"{kind[0].upper()}{kind[1:]}Operation"


def kind_summary(function: object) -> str:
    return " ".join((getattr(function, "__doc__", None) or "").split())


OPERATION_SCHEMAS: dict[str, type[BaseModel]] = {
    kind: operation_model(
        operation_schema_name(kind), kind, kind_summary(KINDS[kind]), DESCRIBED[kind]
    )
    for kind in sorted(KINDS)
    if kind not in INTERNAL_KINDS
}

DraftOperation = Annotated[
    Union[tuple(OPERATION_SCHEMAS.values())],  # noqa: UP007  (built from the registry)
    Field(discriminator="kind"),
]
