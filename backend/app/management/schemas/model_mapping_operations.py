"""A model mapping's operations as the OpenAPI document describes them.

``POST /model-mappings/{key}/operations`` takes a list of operations, each ``{"kind": …, …}``, as a
draft's route does (``model_operations.py``). The registry in ``engine/moves/mapping_kinds.py``
(``KINDS``, ``PARAMETERS``, a kind's docstring) owns what each kind allows and the engine refuses
what it cannot apply, with its own codes; the schemas here describe it and validate nothing. A
schema is named ``Mapping<Kind>Operation``, since a draft has kinds of the same names.
"""

from typing import Annotated, Union

from pydantic import BaseModel, Field

from ...engine.moves.mapping_kinds import INTERNAL_KINDS, KINDS
from .mapping_operation_parameters import PARAMETERS as DESCRIBED
from .model_operations import kind_summary
from .operation_description import operation_model


def mapping_operation_schema_name(kind: str) -> str:
    return f"Mapping{kind[0].upper()}{kind[1:]}Operation"


MAPPING_OPERATION_SCHEMAS: dict[str, type[BaseModel]] = {
    kind: operation_model(
        mapping_operation_schema_name(kind), kind, kind_summary(KINDS[kind]), DESCRIBED[kind]
    )
    for kind in sorted(KINDS)
    if kind not in INTERNAL_KINDS
}

MappingOperation = Annotated[
    Union[tuple(MAPPING_OPERATION_SCHEMAS.values())],  # noqa: UP007  (built from the registry)
    Field(discriminator="kind"),
]
