"""Relation columns: a list's column of each row's related records (Base 0.9 K5, D140–D145).

A column ``related:<key>`` names a relation type's ``key`` (the listed type at the ``from`` end, read
outgoing) or its ``reverseKey`` (at the ``to`` end, read incoming); keys and reverse keys share one
namespace, so one key names the relation type and the direction. Every binding of that relation type
with the listed type at that end shows in the column. The per-type list's ``expand`` takes the same
keys. A column is single-valued, and sorts, when exactly one binding stands behind it and the listed
type's end of it holds at most one relationship.

A column may name a field of the related records instead of their name (0.9 K5a, D148):
``related:<key>.<field>``, the field as the consumer API writes it (``name``, an attribute one of the
types at the other end binds, ``ancestor:<type>.<field>``). A key may contain a dot, so the text
resolves against the model: the whole text when it is a key, otherwise the longest key it starts
with, followed by a dot. Such a column does not sort (D151).
"""

from dataclasses import dataclass
from typing import Literal

from ...models.schema import EngineModel, ObjectTypeRelationDefinition
from .consumer_contract import reference_value_type, split_ancestor_reference

RELATED_FIELD_PREFIX = "related:"

Direction = Literal["outgoing", "incoming"]


class RelatedKeyError(ValueError):
    """A key no relation column of the listed type can name; the message says why."""


@dataclass(frozen=True)
class RelatedColumn:
    key: str
    relation_type_key: str
    direction: Direction
    bindings: tuple[ObjectTypeRelationDefinition, ...]
    # The field each related record shows; ``None`` shows its name.
    field: str | None = None

    @property
    def target_type_keys(self) -> tuple[str, ...]:
        """The types at the other end, in binding order."""
        far = (
            (binding.toObjectTypeKey for binding in self.bindings)
            if self.direction == "outgoing"
            else (binding.fromObjectTypeKey for binding in self.bindings)
        )
        return tuple(dict.fromkeys(far))

    @property
    def single_valued(self) -> bool:
        """Whether each row holds at most one related record: one binding, whose listed end holds one."""
        end = "from" if self.direction == "outgoing" else "to"
        return self.field is None and len(self.bindings) == 1 and self.bindings[0].holds_one(end)


def is_related_field(field: str) -> bool:
    return field.startswith(RELATED_FIELD_PREFIX)


def related_column(model: EngineModel, object_type_key: str, key: str) -> RelatedColumn:
    """What ``key`` (a relation key or reverse key) shows for records of ``object_type_key``.

    Raises :class:`RelatedKeyError` for an unknown key or one the type has no binding of.
    """
    relation_type = next(
        (item for item in model.relationTypes if key in (item.key, item.reverseKey)), None
    )
    if relation_type is None:
        raise RelatedKeyError(f"No relation type has the key or reverse key '{key}'")
    direction: Direction = "outgoing" if key == relation_type.key else "incoming"
    bindings = tuple(
        binding
        for binding in model.objectTypeRelations
        if binding.relationTypeKey == relation_type.key
        and (binding.fromObjectTypeKey if direction == "outgoing" else binding.toObjectTypeKey)
        == object_type_key
    )
    if not bindings:
        end = "from" if direction == "outgoing" else "to"
        raise RelatedKeyError(
            f"Object type '{object_type_key}' is not at the {end} end of any binding of relation"
            f" type '{relation_type.key}', which '{key}' reads {direction}"
        )
    return RelatedColumn(key, relation_type.key, direction, bindings)


def narrow_to(column: RelatedColumn, far_type_key: str) -> RelatedColumn:
    """The column over its bindings whose far end is ``far_type_key`` alone (a view that names the
    target type, as a mapping grid does); the column unchanged when no binding reaches that type."""
    end = "toObjectTypeKey" if column.direction == "outgoing" else "fromObjectTypeKey"
    bindings = tuple(item for item in column.bindings if getattr(item, end) == far_type_key)
    if not bindings:
        return column
    return RelatedColumn(
        column.key, column.relation_type_key, column.direction, bindings, column.field
    )


def related_field_column(model: EngineModel, object_type_key: str, text: str) -> RelatedColumn:
    """What ``text`` (``<key>`` or ``<key>.<field>``, the part after ``related:``) shows for records
    of ``object_type_key``: the relation, and the field when it names one (D148).

    Raises :class:`RelatedKeyError` for a key that does not resolve or a field the types at the other
    end do not have.
    """
    keys = {key for item in model.relationTypes for key in (item.key, item.reverseKey)}
    if text in keys:
        return related_column(model, object_type_key, text)
    prefixes = [key for key in keys if text.startswith(f"{key}.")]
    if not prefixes:
        return related_column(model, object_type_key, text)
    key = max(prefixes, key=len)
    field = text.removeprefix(f"{key}.")
    column = related_column(model, object_type_key, key)
    targets = tuple(
        definition
        for definition in (model.object_type(item) for item in column.target_type_keys)
        if definition is not None
    )
    if reference_value_type(model, targets, field) is None:
        raise RelatedKeyError(
            f"'{field}' is no field of the records '{key}' reaches: name, an attribute they bind, or"
            " ancestor:<type>.<field> of a type they can sit under"
        )
    reference = split_ancestor_reference(field)
    attribute = model.attribute_type(field if reference is None else reference[1])
    if attribute is not None and attribute.valueType == "json":
        raise RelatedKeyError(f"'{field}' holds JSON, which a column cannot show")
    return RelatedColumn(
        column.key,
        column.relation_type_key,
        column.direction,
        column.bindings,
        None if field == "name" else field,
    )
