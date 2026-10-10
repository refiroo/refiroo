"""Which records a relationship may choose: the model's side (Base 0.9 K7, D168–D170).

A binding's ``candidates`` limits the records at its ``from`` end, its ``to`` end, or both, by
criteria over their own fields and their ancestors' fields: ``name``, any non-JSON attribute the
type binds (filterable or not), and ``ancestor:<type>.<field>`` (``name`` or an attribute of an
ancestor of that type at any depth). Each criterion takes the operators of its field's value type,
the list's own (:func:`filter_operators`), and a value of the JSON type that value type reads. This
module checks the criteria against the model; ``reads/model_query`` turns them into a set of IDs.
"""

from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from ...models.schema import CandidateCriterion, EngineModel, ObjectTypeDefinition
from .consumer_contract import split_ancestor_reference
from .traversal import ancestor_type_keys


def filter_operators(value_type: str, *, attribute: bool) -> set[str]:
    """The operators a filter on a field of ``value_type`` takes; ``isUnset`` only on an attribute."""
    suffix = {"isUnset"} if attribute else set()
    if value_type in {"text", "longText"}:
        return {"eq", "contains", "startsWith", "isNull"} | suffix
    if value_type in {"integer", "decimal", "date", "dateTime"}:
        return {"eq", "lt", "lte", "gt", "gte", "isNull"} | suffix
    if value_type == "boolean":
        return {"eq", "isNull"} | suffix
    return set()


class CandidateCriterionError(ValueError):
    """A criterion the end's records cannot be compared by; ``part`` is ``field``, ``op`` or ``value``."""

    def __init__(self, index: int, part: str, message: str) -> None:
        super().__init__(message)
        self.index = index
        self.part = part


def check_candidate_criteria(
    model: EngineModel, object_type: ObjectTypeDefinition, criteria: tuple[CandidateCriterion, ...]
) -> None:
    """Raise :class:`CandidateCriterionError` for the first criterion that does not resolve."""
    for index, criterion in enumerate(criteria):
        value_type, attribute = _field_type(model, object_type, criterion.field, index)
        if criterion.op not in filter_operators(value_type, attribute=attribute):
            raise CandidateCriterionError(
                index, "op", f"Operator '{criterion.op}' is not supported for field '{criterion.field}'"
            )
        _check_value(value_type, criterion, index)


def _field_type(
    model: EngineModel, object_type: ObjectTypeDefinition, field: str, index: int
) -> tuple[str, bool]:
    """The value type ``field`` compares on ``object_type``'s records and whether it is an attribute."""
    reference = split_ancestor_reference(field)
    if reference is not None:
        ancestor_type_key, name = reference
        ancestor = model.object_type(ancestor_type_key)
        if ancestor is None or ancestor_type_key not in ancestor_type_keys(model, object_type.key):
            raise CandidateCriterionError(
                index,
                "field",
                f"'{field}' names no ancestor type '{object_type.key}' records can sit under",
            )
        return _own_field_type(model, ancestor, name, index)
    return _own_field_type(model, object_type, field, index)


def _own_field_type(
    model: EngineModel, object_type: ObjectTypeDefinition, field: str, index: int
) -> tuple[str, bool]:
    if field == "name":
        return "text", False
    definition = model.attribute_type(field)
    if definition is None or field not in {item.attributeTypeKey for item in object_type.attributes}:
        raise CandidateCriterionError(
            index,
            "field",
            f"'{field}' is no field of '{object_type.key}' a criterion can compare: name, an"
            " attribute it binds, or ancestor:<type>.<field>",
        )
    if definition.valueType == "json":
        raise CandidateCriterionError(index, "field", f"'{field}' holds JSON, which cannot be compared")
    return definition.valueType, True


def _check_value(value_type: str, criterion: CandidateCriterion, index: int) -> None:
    """The value's JSON type, as Q3 reads a criterion's value."""
    value, operator = criterion.value, criterion.op
    if operator in {"isNull", "isUnset"} or value_type == "boolean":
        valid, expected = isinstance(value, bool), "true or false"
    elif value_type == "integer":
        valid, expected = isinstance(value, int) and not isinstance(value, bool), "an integer"
    elif value_type == "decimal":
        valid = isinstance(value, (int, float, str)) and not isinstance(value, bool)
        expected = "a number"
    elif value_type == "date":
        valid, expected = isinstance(value, str) and _parses(date.fromisoformat, value), "a date"
    elif value_type == "dateTime":
        valid, expected = isinstance(value, str) and _parses(datetime.fromisoformat, value), "a date and time"
    else:
        valid, expected = isinstance(value, str), "a string"
    if not valid:
        raise CandidateCriterionError(
            index, "value", f"Criterion '{criterion.field} {operator}' needs {expected}"
        )


def _parses(parse, value: str) -> bool:
    try:
        parse(value)
    except ValueError:
        return False
    return True


def meets_criteria(
    model: EngineModel,
    criteria: tuple[CandidateCriterion, ...],
    record: tuple[str, Callable[[], dict[str, Any]]],
    ancestors: list[tuple[str, str, Callable[[], dict[str, Any]]]],
) -> bool:
    """Whether a record meets ``criteria``, read from its state rather than the database: what a
    batch has laid but not yet written (0.9 K7). ``record`` is its name and how to read its values
    (JSON form), ``ancestors`` each ancestor's type, name and values reader: values are read only
    when a criterion names an attribute. The meaning is the list's: ``eq`` exact,
    ``contains`` and ``startsWith`` ignoring case, comparisons by value type, ``isNull`` a value
    held empty, ``isUnset`` none held; criteria on one ancestor type are met by one ancestor, any
    of that type."""
    own = [item for item in criteria if split_ancestor_reference(item.field) is None]
    if not _all_met(model, own, *record):
        return False
    by_type: dict[str, list[CandidateCriterion]] = {}
    for item in criteria:
        reference = split_ancestor_reference(item.field)
        if reference is not None:
            by_type.setdefault(reference[0], []).append(
                item.model_copy(update={"field": reference[1]})
            )
    return all(
        any(
            _all_met(model, items, name, values)
            for type_key, name, values in ancestors
            if type_key == ancestor_type
        )
        for ancestor_type, items in by_type.items()
    )


def _all_met(
    model: EngineModel,
    criteria: list[CandidateCriterion],
    name: str,
    values: Callable[[], dict[str, Any]],
) -> bool:
    alternatives: dict[str, list[CandidateCriterion]] = {}
    for item in criteria:
        if item.op == "eq":
            alternatives.setdefault(item.field, []).append(item)
        elif not _met(model, item, name, values):
            return False
    return all(
        any(_met(model, item, name, values) for item in group) for group in alternatives.values()
    )


def _met(
    model: EngineModel, item: CandidateCriterion, name: str, values: Callable[[], dict[str, Any]]
) -> bool:
    if item.field == "name":
        held, value, value_type = True, name, "text"
    else:
        definition = model.attribute_type(item.field)
        value_type = definition.valueType if definition is not None else "text"
        read = values()
        held, value = item.field in read, read.get(item.field)
    if item.op == "isUnset":
        return held != bool(item.value)
    if item.op == "isNull":
        return (held and value is None) == bool(item.value)
    if value is None:
        return False
    if item.op in {"contains", "startsWith"}:
        text, wanted = str(value).casefold(), str(item.value).casefold()
        return wanted in text if item.op == "contains" else text.startswith(wanted)
    left, right = _comparable(value_type, value), _comparable(value_type, item.value)
    if item.op == "eq":
        return left == right
    return {"lt": left < right, "lte": left <= right, "gt": left > right, "gte": left >= right}[item.op]


def _comparable(value_type: str, value: Any) -> Any:
    if value_type == "decimal":
        return Decimal(str(value))
    if value_type == "date":
        return date.fromisoformat(str(value))
    if value_type == "dateTime":
        return datetime.fromisoformat(str(value))
    return value
