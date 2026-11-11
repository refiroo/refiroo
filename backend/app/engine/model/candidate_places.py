"""Where a new record may go, from the model's candidate rules (Base 0.17 MC1 and EX1, PP-D24).

A binding's ``candidates`` criteria limit the records at an end. A record created under a container
meets the ancestor criteria when the container is, or sits under, an ancestor that meets them; the
read side asks that of the candidate evaluator (``reads/model_query``), never of a second one. This
module adds what only the model can say:

* the place the criteria fix: equalities on one ancestor type's fields that the model lets sit
  directly under the column type and directly hold the cell type, with every required value of that
  type among them. The place is a record to create when none exists (:func:`derive_place`);
* the place to propose where neither the criteria nor the data give one (:func:`propose_place`, PP-D28);
* the fields that identify a type's records (:func:`identifying_fields`), the choices of what a cell
  lists (PP-D25).

Nothing names a type: the binding and the model say which.
"""

from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

from ...models.schema import CandidateCriterion, EngineModel
from .candidates import meets_criteria
from .consumer_contract import split_ancestor_reference
from .traversal import parent_type_keys


@dataclass(frozen=True)
class DerivedPlace:
    """The record the candidate criteria fix: its type, name and attribute values."""

    object_type_key: str
    name: str
    attributes: dict[str, Any] = field(default_factory=dict)
    # Proposed by :func:`propose_place` from the data, not fixed by the model's rules (PP-D28).
    proposed: bool = False


def derive_place(
    model: EngineModel,
    column_type_key: str,
    cell_type_key: str,
    criteria: Sequence[CandidateCriterion],
) -> DerivedPlace | None:
    """The one place the criteria fix under a ``column_type_key`` record for a new ``cell_type_key``
    record, or ``None``.

    Fixed means: every criterion is ``eq`` on a field of one ancestor type (``ancestor:<type>.<field>``),
    each field once, the type directly holds the cell type and sits directly under the column type,
    the name is among the fields, and every attribute the type requires is. A criterion on the
    record's own fields, another operator, a second value for a field or a second ancestor type fixes
    nothing: the containers that meet the criteria are then offered, none are created."""
    if not criteria:
        return None
    place_type = ""
    values: dict[str, Any] = {}
    for criterion in criteria:
        reference = split_ancestor_reference(criterion.field)
        if reference is None or criterion.op != "eq" or criterion.value is None:
            return None
        type_key, field_key = reference
        if place_type and type_key != place_type:
            return None
        place_type = type_key
        if field_key in values:
            return None
        values[field_key] = criterion.value
    definition = model.object_type(place_type)
    if (
        definition is None
        or place_type == column_type_key
        or place_type not in parent_type_keys(model, cell_type_key)
        or column_type_key not in parent_type_keys(model, place_type)
    ):
        return None
    name = values.pop("name", None)
    if not isinstance(name, str) or not name.strip():
        return None
    bound = {item.attributeTypeKey: item for item in definition.attributes}
    if any(key not in bound for key in values):
        return None
    if any(item.required and item.attributeTypeKey not in values for item in definition.attributes):
        return None
    return DerivedPlace(place_type, name, values)


def propose_place(
    model: EngineModel,
    column_type_key: str,
    cell_type_key: str,
    criteria: Sequence[CandidateCriterion],
    used: Sequence[tuple[str, str]],
    column_chain: Sequence[tuple[str, str, Callable[[], dict[str, Any]]]],
) -> DerivedPlace | None:
    """A new container to propose under a column record where neither the rules nor the data give a
    place (PP-D28): of the type the view's other columns use, named as most of those containers are.

    ``used`` is the (type, name) of each container the view uses in other columns; ``column_chain`` is
    the column record and the records above it (type, name, values). Only a type the model lets sit
    directly under the column type and directly hold the cell type, that requires no value, is
    proposed; among the types used the most common, among its names the most common, a tie going to
    the first in order. The proposal is dropped when a new container so named would not meet the
    binding's ancestor criteria (the write would refuse the record): no model rule is added for it."""
    direct = parent_type_keys(model, cell_type_key)
    fitting = [
        (type_key, name)
        for type_key, name in used
        if type_key in direct and column_type_key in parent_type_keys(model, type_key)
    ]
    if not fitting:
        return None
    types = Counter(type_key for type_key, _ in fitting)
    type_key = min(types, key=lambda key: (-types[key], key))
    definition = model.object_type(type_key)
    if definition is None or any(item.required for item in definition.attributes):
        return None
    names = Counter(name for key, name in fitting if key == type_key)
    name = min(names, key=lambda item: (-names[item], item))
    ancestor_criteria = tuple(
        item for item in criteria if split_ancestor_reference(item.field) is not None
    )
    if ancestor_criteria and not meets_criteria(
        model, ancestor_criteria, ("", dict), [(type_key, name, dict), *column_chain]
    ):
        return None
    return DerivedPlace(type_key, name, {}, proposed=True)


def identifying_fields(model: EngineModel, object_type_key: str) -> list[str]:
    """The fields of a type a matrix cell may list its records by, in the order offered: ``name``, the
    type's display attribute, then every other text attribute it binds (0.17 PP-D27; PP-D25 offered
    only the unique ones)."""
    definition = model.object_type(object_type_key)
    if definition is None:
        return []
    bound = [item.attributeTypeKey for item in definition.attributes]
    found = ["name"]
    display = definition.displayAttributeTypeKey
    if display and display != "name" and display in bound and model.attribute_type(display):
        found.append(display)
    for key in bound:
        attribute = model.attribute_type(key)
        if (
            key not in found
            and attribute is not None
            and attribute.valueType in {"text", "longText"}
        ):
            found.append(key)
    return found


def choose_container(
    container_ids: Sequence[str], cell_counts: dict[str, int], *, fixed: bool
) -> str | None:
    """The container a column's new cells go into, among those that meet the candidate criteria
    (PP-D24). Where the criteria fix the one place and one container is it, that one. Otherwise the
    evidence of the data: the container that already holds cells of the view, the one holding most when
    several do, none on a tie. A container holding no cells is never chosen, even as the only one."""
    if fixed and len(container_ids) == 1:
        return container_ids[0]
    used = sorted(
        (
            (cell_counts.get(item, 0), item)
            for item in container_ids
            if cell_counts.get(item, 0) > 0
        ),
        reverse=True,
    )
    if not used or (len(used) > 1 and used[0][0] == used[1][0]):
        return None
    return used[0][1]
