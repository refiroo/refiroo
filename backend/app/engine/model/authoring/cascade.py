"""What goes with a removed element, and every reference rewritten on a key change (0.10 A2, D31).

:func:`prune` takes out of the document every reference to elements that are gone: an item naming
them leaves its list, a field falls back to its default, and a view, detail page or panel that
exists only for a gone element goes with it (a children or relations panel whose list emptied, a
table view of a removed type). :func:`rename` rewrites every slot naming a key, in consumer API definitions too (0.10 A4c, D54).
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .document import Document, Path, identity
from .references import (
    Slot,
    consumer_slots,
    format_field,
    known_keys,
    names_in_slot,
    parse_field,
    rename_field,
    slot_value,
    slots,
)

# What a scalar slot does when what it names is gone: fall back to ``name``, lose the member, or
# take its owner (the object holding it, or the one above a ``config``) out of its list.
_SCALARS: dict[str, str] = {
    "defaultSort": "name",
    "labelField": "name",
    "columnLabelField": "name",
    "titleField": "name",
    "subtitleField": "drop",
    "secondaryField": "drop",
    "availabilityField": "drop",
    "displayAttributeTypeKey": "drop",
    "uniqueToAncestorTypeKey": "drop",
    "objectTypeKey": "owner",
    "relationTypeKey": "owner",
    "fromObjectTypeKey": "owner",
    "toObjectTypeKey": "owner",
    "rowObjectTypeKey": "owner",
    "columnObjectTypeKey": "owner",
    "cellObjectTypeKey": "owner",
    "startAttributeTypeKey": "owner",
    "endAttributeTypeKey": "owner",
    "attributeTypeKey": "owner",
    "field": "owner",
}
# Lists whose emptying takes their owner away: the list is what the panel or view is about.
_ANCHORS = {"objectTypeKeys", "relationTypeKeys", "rootObjectTypeKeys"}


@dataclass
class Gone:
    types: set[str] = field(default_factory=set)
    attribute_types: set[str] = field(default_factory=set)
    # (object type, attribute type) bindings no longer declared.
    bindings: set[tuple[str, str]] = field(default_factory=set)
    # Relation type keys and reverse keys no longer declared.
    relation_keys: set[str] = field(default_factory=set)

    def __bool__(self) -> bool:
        return bool(self.types or self.attribute_types or self.bindings or self.relation_keys)


def prune(
    document: Document,
    gone: Gone,
    within: Callable[[Path], bool] | None = None,
    which: Callable[[Slot], bool] | None = None,
) -> None:
    """Remove every reference to what is ``gone``; repeated until nothing more goes. ``within``
    limits it to the slots and anchors at the paths it accepts (a type leaving one application is
    gone from that application only), and ``which`` to the slots it accepts."""
    for _ in range(10):
        if not _prune_once(document, gone, within, which):
            break
    _fix_default_views(document)


def _prune_once(
    document: Document, gone: Gone, within: Callable[[Path], bool] | None, which: Callable[[Slot], bool] | None
) -> bool:
    data = document.data
    known = known_keys(data)
    known = (known[0] | gone.types, known[1] | gone.relation_keys)
    changed = False
    scoped = [
        slot
        for slot in slots(data)
        if (within is None or within(slot.path)) and (which is None or which(slot))
    ]
    for slot in sorted(scoped, key=_depth, reverse=True):
        if _declares(slot) or slot.path[:1] == ["objectTypeRelations"] and slot.field in (
            "relationTypeKey",
            "fromObjectTypeKey",
            "toObjectTypeKey",
        ):
            continue
        if document.find(slot.path) is None:
            continue
        if slot.kind == "view" or not any(
            _is_gone(gone, kind, key, slot) for kind, key in names_in_slot(data, slot, known)
        ):
            continue
        changed = True
        _drop(document, slot)
    for path in _emptied_anchors(document):
        if within is not None and not within(path):
            continue
        _remove_owner(document, path)
        changed = True
    return changed


def _is_gone(gone: Gone, kind: str, key: str, slot: Slot) -> bool:
    if kind == "objectType":
        return key in gone.types
    if kind == "relationType" or kind == "relationKey":
        return key in gone.relation_keys
    if kind == "attributeType":
        if key in gone.attribute_types:
            return True
        types = slot.types
        if slot.kind == "field" and types:
            return all(t in gone.types or (t, key) in gone.bindings for t in types)
        if slot.kind == "attributeType" and slot.path[:1] == ["objectTypes"]:
            owner = slot.path[1].get("key")
            return owner in gone.types or (owner, key) in gone.bindings
        return False
    return False


def _drop(document: Document, slot: Slot) -> None:
    value = slot_value(document.data, slot)
    if slot.kind == "objectTypeMapKey":
        document.set(slot.path, slot.member or "", None)
        return
    if slot.index is not None:
        document.remove(slot.path + [slot.field], value)
        return
    action = _SCALARS.get(slot.field, "drop")
    if slot.field == "attributeTypeKey" and slot.path[-1] == "uniqueWhenToAttributeEquals":
        document.set(slot.path[:-1], "uniqueWhenToAttributeEquals", None)
    elif slot.path[-1] == "effectivePeriod":
        document.set(slot.path[:-1], "effectivePeriod", None)
    elif action == "name":
        document.set(slot.path, slot.field, "name")
    elif action == "owner":
        owner = slot.path[:-1] if slot.path[-1] == "config" else slot.path
        if isinstance(owner[-1], int):
            # A candidate criterion, named by its position within its list.
            document.remove(owner[:-1], document.at(owner))
        else:
            _remove_owner(document, owner)
    else:
        document.set(slot.path, slot.field, None)


def _remove_owner(document: Document, path: Path) -> None:
    if document.find(path) is not None:
        document.remove(path[:-1], path[-1])


def _emptied_anchors(document: Document) -> list[Path]:
    """Panels and tree views whose anchor list is now empty."""
    found = []
    for application in document.items("applications"):
        app = ["applications", {"key": application["key"]}]
        for view in application.get("views") or []:
            config = view.get("config") or {}
            if view.get("type") == "tree" and not config.get("rootObjectTypeKeys"):
                found.append(app + ["views", {"key": view["key"]}])
        for detail in application.get("details") or []:
            for panel in detail.get("panels") or []:
                config = panel.get("config") or {}
                if any(name in config and not config[name] for name in _ANCHORS):
                    found.append(app + ["details", identity(detail), "panels", {"key": panel["key"]}])
    return found


def _fix_default_views(document: Document) -> None:
    for application in document.items("applications"):
        keys = [view.get("key") for view in application.get("views") or []]
        if application.get("defaultView") not in keys:
            document.set(["applications", {"key": application["key"]}], "defaultView", keys[0] if keys else "")


def _depth(slot: Slot) -> tuple[int, int]:
    return (len(slot.path), slot.index if slot.index is not None else -1)


def _is_definition(slot: Slot) -> bool:
    """A slot holding the key of the element at its own path: an identity, never pruned or renamed
    before the slots inside it."""
    last = slot.path[-1] if slot.path else None
    return slot.index is None and isinstance(last, dict) and slot.field in last


def _declares(slot: Slot) -> bool:
    """A definition's own key; a detail page's type is a reference to the type, not a definition."""
    return _is_definition(slot) and not (len(slot.path) >= 2 and slot.path[-2] == "details")


def rename(document: Document, kind: str, old: str, new: str, within: Callable[[Slot], bool] | None = None) -> None:
    """Rewrite every slot naming ``old`` of ``kind`` (``relationKey`` for a relation type's key or
    reverse key in fields) to ``new``; identities last, deepest first, so paths resolve throughout."""
    data = document.data
    known = known_keys(data)
    every = [*slots(data), *consumer_slots(data)]
    pending = [slot for slot in every if within is None or within(slot)]
    ordered = sorted(pending, key=lambda s: (_is_definition(s), -len(s.path)))
    # An identity slot's object is held, not its path: renaming one end of a binding changes the
    # identity the other end's path names (a type related to itself).
    owners = {id(slot): document.find(slot.path) for slot in ordered if _is_definition(slot)}
    for slot in ordered:
        owner = owners.get(id(slot))
        if owner is not None:
            slot = Slot(slot.path[:-1] + [identity(owner)], slot.field, slot.kind, slot.index, slot.types, slot.member)
        value = slot_value(data, slot)
        if not isinstance(value, str):
            continue
        replacement: str | None = None
        if slot.kind == "field":
            field_kind = "relationKey" if kind in ("relationType", "relationKey") else kind
            renamed = format_field(rename_field(parse_field(value, *known), field_kind, old, new))
            replacement = renamed if renamed != value else None
        elif slot.kind == "objectTypeMapKey" and kind == "objectType" and value == old:
            node = document.at(slot.path)
            document.set(slot.path, new, node[old])
            document.set(slot.path, old, None)
            continue
        elif (slot.kind == kind or (kind == "relationKey" and slot.kind == "relationType")) and value == old:
            replacement = new
        if replacement is None:
            continue
        if slot.index is not None:
            document.remove(slot.path + [slot.field], value)
            document.insert(slot.path + [slot.field], replacement, slot.index)
        else:
            document.set(slot.path, slot.field, replacement)


def references(data: dict[str, Any], kind: str, key: str) -> list[Slot]:
    """The slots naming ``key`` of ``kind``, consumer API definitions included, definitions left out."""
    known = known_keys(data)
    return [
        slot
        for slot in [*slots(data), *consumer_slots(data)]
        if not _is_definition(slot) and (kind, key) in set(names_in_slot(data, slot, known))
    ]
