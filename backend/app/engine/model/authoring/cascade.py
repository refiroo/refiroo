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
    related_types,
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
    if within is None and which is None and _prune_unbound(document):
        changed = True
    for path in _emptied_anchors(document):
        if within is not None and not within(path):
            continue
        _remove_owner(document, path)
        changed = True
    return changed


def _unbound(document: Document) -> set[tuple[str, str, str]]:
    """The relation bindings (relation type, from, to) this operation took out and that stand nowhere
    now, read from the document's change log."""
    present = {
        (b.get("relationTypeKey"), b.get("fromObjectTypeKey"), b.get("toObjectTypeKey"))
        for b in document.items("objectTypeRelations")
    }
    removed = set()
    for entry in document.log:
        value = entry.get("value")
        if (
            entry.get("change") == "insert"
            and entry.get("path") == ["objectTypeRelations"]
            and "document" not in entry
            and isinstance(value, dict)
        ):
            removed.add((value.get("relationTypeKey"), value.get("fromObjectTypeKey"), value.get("toObjectTypeKey")))
    return {triple for triple in removed if triple not in present}


def _prune_unbound(document: Document) -> bool:
    """Take out what depended on a relation binding that is gone while its relation type stays
    (another binding keeps it, or it was released): a relation a panel lists that its page's type no
    longer has in the panel's direction, with the columns only the dropped related types gave it; a
    mapping grid or matrix view over the binding; and the navigation entries a removed view leaves
    without a collection. A panel left listing no relation goes with the anchors that follow."""
    gone = _unbound(document)
    if not gone:
        return False
    changed = False
    relations = {triple[0] for triple in gone}
    bindings = [
        (b.get("relationTypeKey"), b.get("fromObjectTypeKey"), b.get("toObjectTypeKey"))
        for b in document.items("objectTypeRelations")
    ]
    for application in document.items("applications"):
        app = ["applications", {"key": application["key"]}]
        for detail in application.get("details") or []:
            page = detail.get("objectTypeKey")
            for panel in detail.get("panels") or []:
                config = panel.get("config") or {}
                if panel.get("type") != "relations":
                    continue
                direction = config.get("direction", "both")
                dropped = [
                    key
                    for key in config.get("relationTypeKeys") or []
                    if key in relations
                    and not any(
                        rel == key
                        and (direction in ("outgoing", "both") and source == page or direction in ("incoming", "both") and target == page)
                        for rel, source, target in bindings
                    )
                ]
                if not dropped:
                    continue
                panel_path = app + ["details", {"objectTypeKey": page}, "panels", {"key": panel["key"]}]
                for key in dropped:
                    document.remove(panel_path + ["config", "relationTypeKeys"], key)
                changed = True
                _drop_unreachable_columns(document, panel_path, page)
        for view in application.get("views") or []:
            if view.get("type") == "table" and _drop_related_fields(document, app, view, gone, bindings):
                changed = True
        removed_views = False
        for view in list(application.get("views") or []):
            if _view_over(view, gone):
                document.remove(app + ["views"], {"key": view["key"]})
                removed_views = changed = True
        if removed_views:
            _drop_orphan_collections(document, app)
    return changed


def _drop_related_fields(
    document: Document,
    app: Path,
    view: dict[str, Any],
    gone: set[tuple[str, str, str]],
    bindings: list[tuple[Any, Any, Any]],
) -> bool:
    """The ``related:`` columns, filters and sorts of a table view for a relationship its type no
    longer holds in that direction (``allowRelation`` placed them, 0.13 RL)."""
    type_key = view.get("objectTypeKey")
    stale: list[str] = []
    for relation_key, source, target in gone:
        relation = next(
            (r for r in document.items("relationTypes") if r.get("key") == relation_key), None
        )
        if relation is None:
            continue
        if type_key == source and not any(
            b[0] == relation_key and b[1] == type_key for b in bindings
        ):
            stale.append(relation_key)
        if (
            type_key == target
            and relation.get("reverseKey")
            and not any(b[0] == relation_key and b[2] == type_key for b in bindings)
        ):
            stale.append(relation["reverseKey"])
    changed = False
    config = view.get("config") or {}
    path = app + ["views", {"key": view["key"]}, "config"]
    for key in stale:
        for name in ("columns", "filterFields", "sortFields"):
            for column in [
                f
                for f in config.get(name) or []
                if f == f"related:{key}" or isinstance(f, str) and f.startswith(f"related:{key}.")
            ]:
                document.remove(path + [name], column)
                changed = True
        if str(config.get("defaultSort", "")).removeprefix("-") == f"related:{key}":
            document.set(path, "defaultSort", "name")
            changed = True
    return changed


def _view_over(view: dict[str, Any], gone: set[tuple[str, str, str]]) -> bool:
    """Whether a mapping grid or matrix view stands on a binding that is gone."""
    config = view.get("config") or {}
    if view.get("type") in ("mappingGrid", "relationTable"):
        return (config.get("relationTypeKey"), config.get("fromObjectTypeKey"), config.get("toObjectTypeKey")) in gone
    if view.get("type") == "relationMatrix":
        row, cell = config.get("rowObjectTypeKey"), config.get("cellObjectTypeKey")
        ends = (row, cell) if config.get("direction") == "outgoing" else (cell, row)
        return (config.get("relationTypeKey"), *ends) in gone
    return False


def _drop_unreachable_columns(document: Document, panel_path: Path, page: str) -> None:
    """Columns and sort fields of a relations panel naming an attribute none of the types it still
    reaches has; its default sort falls back to ``name``."""
    data = document.data
    config = document.at(panel_path + ["config"])
    far = set(related_types(data, page, config.get("relationTypeKeys") or (), config.get("direction", "both")))
    bound = {
        b.get("attributeTypeKey")
        for t in document.items("objectTypes")
        if t.get("key") in far
        for b in t.get("attributes") or []
    }
    attributes = {a.get("key") for a in document.items("attributeTypes")}

    def lost(field: str) -> bool:
        name = field.removeprefix("-")
        return name in attributes and name not in bound

    for name in ("columns", "sortFields"):
        for column in [f for f in config.get(name) or [] if isinstance(f, str) and lost(f)]:
            document.remove(panel_path + ["config", name], column)
    sort = config.get("defaultSort")
    if isinstance(sort, str) and lost(sort):
        document.set(panel_path + ["config"], "defaultSort", "name")


def _drop_orphan_collections(document: Document, app: Path) -> None:
    """Navigation entries naming a collection or matrix no view of the application provides any
    more, and the views collections open on that are gone or no longer theirs."""
    application = document.at(app)
    collections = set()
    sources: dict[str, str | None] = {}
    matrices = set()
    for view in application.get("views") or []:
        config = view.get("config") or {}
        source = None
        if view.get("type") == "table":
            source = view.get("objectTypeKey")
        elif view.get("type") == "relationMatrix":
            source = config.get("rowObjectTypeKey")
            matrices.add(view.get("key"))
        elif view.get("type") == "tree":
            source = (config.get("rootObjectTypeKeys") or [None])[0]
        elif view.get("type") == "relationTable":
            source = config.get("fromObjectTypeKey")
        elif view.get("type") == "mappingGrid":
            source = config.get(
                "fromObjectTypeKey" if config.get("direction") == "outgoing" else "toObjectTypeKey"
            )
        collections.add(source)
        sources[view.get("key")] = source
    navigation = application.get("navigation") or {}
    for group in navigation.get("groups") or []:
        for entry in list(group.get("collections") or []):
            gone = (
                entry not in collections
                if isinstance(entry, str)
                else entry.get("view") not in matrices
            )
            if gone:
                document.remove(
                    app + ["navigation", "groups", {"key": group["key"]}, "collections"], entry
                )
    for collection, view_key in list((navigation.get("opens") or {}).items()):
        if collection not in collections or sources.get(view_key) != collection:
            _clear_opening(document, app, collection)


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
    if kind == "view":
        _rename_view_entries(document, old, new, within)
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


def _clear_opening(document: Document, app: Path, collection: str) -> None:
    """A collection's chosen opening view out of ``opens``, which goes with its last member."""
    document.set(app + ["navigation", "opens"], collection, None)
    if not document.at(app + ["navigation", "opens"]):
        document.set(app + ["navigation"], "opens", None)


def drop_view_navigation(document: Document, app: Path, view_key: str) -> bool:
    """The navigation entries of a view taken out of its application: its place in a group (a
    relation matrix) and the collection opening on it. True when something went."""
    navigation = document.at(app).get("navigation")
    if not isinstance(navigation, dict):
        return False
    changed = False
    for group in navigation.get("groups") or []:
        for entry in list(group.get("collections") or []):
            if isinstance(entry, dict) and entry.get("view") == view_key:
                document.remove(
                    app + ["navigation", "groups", {"key": group["key"]}, "collections"], entry
                )
                changed = True
    for collection, opened in list((navigation.get("opens") or {}).items()):
        if opened == view_key:
            _clear_opening(document, app, collection)
            changed = True
    return changed


def _rename_view_entries(
    document: Document, old: str, new: str, within: Callable[[Slot], bool] | None
) -> None:
    """A renamed view as a navigation entry (a relation matrix in a group) and as the view a
    collection opens on."""
    for application in document.items("applications"):
        navigation = application.get("navigation")
        if not isinstance(navigation, dict):
            continue
        app = ["applications", {"key": application["key"]}]
        if within is not None and not within(Slot(app + ["navigation"], "opens", "view")):
            continue
        for group in navigation.get("groups") or []:
            members = app + ["navigation", "groups", {"key": group["key"]}, "collections"]
            for position, entry in enumerate(list(group.get("collections") or [])):
                if isinstance(entry, dict) and entry.get("view") == old:
                    document.remove(members, entry)
                    document.insert(members, {"view": new}, position)
        for collection, view_key in (navigation.get("opens") or {}).items():
            if view_key == old:
                document.set(app + ["navigation", "opens"], collection, new)


def references(data: dict[str, Any], kind: str, key: str) -> list[Slot]:
    """The slots naming ``key`` of ``kind``, consumer API definitions included, definitions left out."""
    known = known_keys(data)
    return [
        slot
        for slot in [*slots(data), *consumer_slots(data)]
        if not _is_definition(slot) and (kind, key) in set(names_in_slot(data, slot, known))
    ]
