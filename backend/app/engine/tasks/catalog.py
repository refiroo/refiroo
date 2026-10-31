"""The workspace's model as the task's reading needs it (Product 0.16 AP6a).

For each object type: its application, the unique text attributes it binds, the attributes a load may
write, where it may stand (the types it may be contained in, whether it may stand at the top) and the
relationships it may hold to types contained in a parent: the one structure a column of translations
can be read as (``translations.py``).
"""

import re
from dataclasses import dataclass, field
from typing import Any

from ...models.schema import EngineModel
from ..model.traversal import parent_type_keys


@dataclass(frozen=True)
class Related:
    """A relationship the type may hold to a type contained in a parent."""

    relation: str
    relation_name: str
    type_key: str
    type_label: str
    application: str
    # The types that may contain the related type, with whether each may stand at the top.
    parents: tuple[tuple[str, str, bool], ...]


@dataclass(frozen=True)
class TypeInfo:
    key: str
    label: str
    plural: str
    application: str
    # (attribute key, label) of the unique text attributes the type binds.
    unique: tuple[tuple[str, str], ...]
    # (attribute key, label, value type) of the attributes a load may write.
    writable: tuple[tuple[str, str, str], ...]
    # The types a record of this type may be contained in.
    parents: tuple[str, ...] = ()
    # Whether a record of this type may stand at the top.
    top: bool = False
    related: tuple[Related, ...] = field(default_factory=tuple)


class Types(dict[str, TypeInfo]):
    """The types by key, with the model they were read from."""

    model: EngineModel


def type_infos(model: EngineModel) -> Types:
    applications: dict[str, str] = {}
    for application in model.applications:
        for key in application.objectTypeKeys:
            applications.setdefault(key, application.key)
    containment = {
        key
        for item in model.objectTypes
        for key in (item.behavior or {}).get("parentRelationTypeKeys", ())
    }
    parents = {
        item.key: tuple(sorted(parent_type_keys(model, item.key))) for item in model.objectTypes
    }
    top = {item.key: bool(item.features.get("rootCreatable", False)) for item in model.objectTypes}
    labels = {item.key: item.name for item in model.objectTypes}
    related: dict[str, dict[tuple[str, str], Related]] = {}
    for allowed in model.objectTypeRelations:
        if allowed.relationTypeKey in containment or not parents.get(allowed.toObjectTypeKey):
            continue
        relation = model.relation_type(allowed.relationTypeKey)
        related.setdefault(allowed.fromObjectTypeKey, {})[
            (allowed.relationTypeKey, allowed.toObjectTypeKey)
        ] = Related(
            allowed.relationTypeKey,
            relation.name if relation is not None else allowed.relationTypeKey,
            allowed.toObjectTypeKey,
            labels.get(allowed.toObjectTypeKey, allowed.toObjectTypeKey),
            applications.get(allowed.toObjectTypeKey, ""),
            tuple(
                (parent, labels.get(parent, parent), top.get(parent, False))
                for parent in parents[allowed.toObjectTypeKey]
            ),
        )
    found = Types()
    found.model = model
    for item in model.objectTypes:
        unique, writable = [], []
        for binding in item.attributes:
            definition = model.attribute_type(binding.attributeTypeKey)
            if definition is None:
                continue
            if definition.features.get("unique") and definition.valueType in ("text", "longText"):
                unique.append((definition.key, definition.name))
            if not binding.readOnly:
                writable.append((definition.key, definition.name, definition.valueType))
        found[item.key] = TypeInfo(
            item.key,
            item.name,
            item.pluralName,
            applications.get(item.key, ""),
            tuple(unique),
            tuple(writable),
            parents[item.key],
            top[item.key],
            tuple(related.get(item.key, {}).values()),
        )
    return found


def normal(text_: str) -> str:
    """A header or label compared ignoring case, spaces and punctuation."""
    return re.sub(r"[^0-9a-z]", "", text_.casefold())


BINDING_KINDS = (
    "field",
    "attributeTypeKey",
    "parent",
    "relation",
    "relationFlags",
    "relatedRecord",
    "ignore",
)


def kind_of(binding: dict[str, object] | None) -> str | None:
    """Which of a column binding's kinds it is (``ColumnBinding``)."""
    if not binding:
        return None
    return next((kind for kind in BINDING_KINDS if binding.get(kind) is not None), None)


def _by(types: Types, match: dict[str, str]) -> str:
    if "attributeTypeKey" in match:
        definition = types.model.attribute_type(match["attributeTypeKey"])
        return definition.name if definition else match["attributeTypeKey"]
    return "ID" if match.get("field") == "id" else "name"


def label_of(types: Types, binding: dict[str, object] | None) -> str:
    """A plain sentence of what a column's binding fills, for the person reading the table."""
    kind = kind_of(binding)
    assert binding is not None or kind is None
    if kind is None:
        return ""

    def type_label(key: str) -> str:
        item = types.get(key)
        return item.label if item else key

    def relation_name(key: str) -> str:
        item = types.model.relation_type(key)
        return item.name if item else key

    if kind == "field":
        return "The record's name"
    if kind == "attributeTypeKey":
        definition = types.model.attribute_type(str(binding["attributeTypeKey"]))
        return f"The attribute “{definition.name if definition else binding['attributeTypeKey']}”"
    if kind == "ignore":
        return "Not loaded"
    value: Any = binding[kind]
    if kind == "parent":
        return f"Its parent: a {type_label(value['objectTypeKey'])} found by {_by(types, value['matchBy'])}"
    if kind == "relation":
        many = ", several in one cell" if value.get("split") else ""
        return (
            f"Related {type_label(value['objectTypeKey'])} records, “{relation_name(value['relationTypeKey'])}”,"
            f" found by {_by(types, value['matchBy'])}{many}"
        )
    if kind == "relationFlags":
        count = len(value.get("targets", {}))
        return (
            f"A flag for each of {count} {type_label(value['objectTypeKey'])} records "
            f"(“{relation_name(value['relationTypeKey'])}”)"
        )
    parent = value["parent"]
    under = parent.get("value") or f"the column “{parent.get('column')}”"
    fills = (
        "name"
        if value.get("field")
        else _by(types, {"attributeTypeKey": value["attributeTypeKey"]})
    )
    return (
        f"The {fills} of a related {type_label(value['objectTypeKey'])} record "
        f"(“{relation_name(value['relationTypeKey'])}”) under the {type_label(parent['objectTypeKey'])} {under}"
    )
