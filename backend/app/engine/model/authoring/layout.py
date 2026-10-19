"""The layout the server generates (0.10 A2, ADR-041: the server produces layout changes).

A new object type gets a table view and a detail page; an attached attribute, a child type and an
allowed relation take their place in the layouts of the types they belong to. Every client gets the
same layout from the same operations ([API.md § Draft operations](../../../../docs/API.md)).
"""

from typing import Any

from .document import Document, Path, identity
from .keys import key_from_label

PAGE_SIZE = 50


def application_path(application_key: str) -> Path:
    return ["applications", {"key": application_key}]


def type_path(type_key: str) -> Path:
    return ["objectTypes", {"key": type_key}]


def attribute_type(document: Document, key: str) -> dict[str, Any] | None:
    return document.find(["attributeTypes", {"key": key}])


def detail_paths(document: Document, type_key: str) -> list[Path]:
    """Every detail page of ``type_key``, in each application that declares one."""
    paths = []
    for application in document.items("applications"):
        for detail in application.get("details") or []:
            if isinstance(detail, dict) and detail.get("objectTypeKey") == type_key:
                paths.append(
                    application_path(application["key"]) + ["details", {"objectTypeKey": type_key}]
                )
    return paths


def table_view_paths(document: Document, type_key: str) -> list[Path]:
    paths = []
    for application in document.items("applications"):
        for view in application.get("views") or []:
            if view.get("type") == "table" and view.get("objectTypeKey") == type_key:
                paths.append(application_path(application["key"]) + ["views", {"key": view["key"]}])
    return paths


def table_view(document: Document, application_key: str, type_key: str) -> dict[str, Any]:
    """A table view of ``type_key``: its name, display attribute and attributes in order, filter and
    sort fields from the attributes' features, sorted by name."""
    object_type = document.at(type_path(type_key))
    application = document.at(application_path(application_key))
    taken = {view.get("key") for view in application.get("views") or []}
    columns, filters, sorts = ["name"], ["name"], ["name"]
    for binding in _bindings_in_order(object_type):
        definition = attribute_type(document, binding["attributeTypeKey"]) or {}
        features = definition.get("features") or {}
        columns.append(binding["attributeTypeKey"])
        if features.get("filterable"):
            filters.append(binding["attributeTypeKey"])
        if features.get("sortable"):
            sorts.append(binding["attributeTypeKey"])
    return {
        "key": key_from_label(object_type.get("pluralName") or type_key, taken),
        "name": object_type.get("pluralName") or object_type.get("name") or type_key,
        "type": "table",
        "objectTypeKey": type_key,
        "config": {
            "columns": columns,
            "filterFields": filters,
            "sortFields": sorts,
            "defaultSort": "name",
            "pageSize": PAGE_SIZE,
        },
    }


def detail_page(document: Document, type_key: str) -> dict[str, Any]:
    """A detail page of ``type_key``: an attributes panel in ``main``; a hierarchy panel in ``side``
    when it has a parent; a children panel when it contains types; a relations panel when a binding
    names it at its ``from`` end."""
    object_type = document.at(type_path(type_key))
    panels: list[dict[str, Any]] = [
        {
            "key": "attributes",
            "title": "Details",
            "type": "attributes",
            "region": "main",
            "order": 10,
            "config": {"fields": [b["attributeTypeKey"] for b in _bindings_in_order(object_type)]},
        }
    ]
    if (object_type.get("behavior") or {}).get("parentRelationTypeKeys"):
        panels.append(_hierarchy_panel())
    children = contained_types(document, type_key)
    if children:
        panels.append(_children_panel(document, children, panels))
    outgoing = [
        b["relationTypeKey"]
        for b in document.items("objectTypeRelations")
        if b.get("fromObjectTypeKey") == type_key and not _is_containment(document, b["relationTypeKey"])
    ]
    if outgoing:
        panels.append(_relations_panel(list(dict.fromkeys(outgoing)), panels))
    return {"objectTypeKey": type_key, "panels": panels}


def contained_types(document: Document, parent_key: str) -> list[str]:
    result = []
    for object_type in document.items("objectTypes"):
        for relation_key in (object_type.get("behavior") or {}).get("parentRelationTypeKeys") or []:
            if any(
                b.get("relationTypeKey") == relation_key
                and b.get("fromObjectTypeKey") == parent_key
                and b.get("toObjectTypeKey") == object_type.get("key")
                for b in document.items("objectTypeRelations")
            ):
                result.append(object_type["key"])
                break
    return result


def place_attribute(document: Document, type_key: str, attribute_key: str) -> None:
    """Show an attached attribute in the type's table views and attributes panels."""
    features = (attribute_type(document, attribute_key) or {}).get("features") or {}
    for path in table_view_paths(document, type_key):
        config = path + ["config"]
        _append_new(document, config + ["columns"], attribute_key)
        if features.get("filterable"):
            _append_new(document, config + ["filterFields"], attribute_key)
        if features.get("sortable"):
            _append_new(document, config + ["sortFields"], attribute_key)
    for path in detail_paths(document, type_key):
        panel = next(
            (p for p in document.at(path).get("panels") or [] if p.get("type") == "attributes"), None
        )
        if panel is not None:
            _append_new(document, path + ["panels", {"key": panel["key"]}, "config", "fields"], attribute_key)


def place_child(document: Document, parent_key: str, child_key: str) -> None:
    """Show a contained type in its parent's detail pages, and the hierarchy in the child's; only in
    an application listing the child, as a panel names only its application's types."""
    for path in detail_paths(document, parent_key):
        if child_key not in (document.at(path[:2]).get("objectTypeKeys") or []):
            continue
        panels = document.at(path).get("panels") or []
        panel = next((p for p in panels if p.get("type") == "children"), None)
        if panel is None:
            add_panel(document, path, _children_panel(document, [child_key], panels))
        else:
            _append_new(
                document, path + ["panels", {"key": panel["key"]}, "config", "objectTypeKeys"], child_key
            )
    for path in detail_paths(document, child_key):
        panels = document.at(path).get("panels") or []
        if not any(p.get("type") == "hierarchy" for p in panels):
            panel = _hierarchy_panel()
            panel["key"] = key_from_label("hierarchy", {p.get("key") for p in panels})
            add_panel(document, path, panel)


def place_relation(document: Document, relation_key: str, from_key: str) -> None:
    """Show an allowed relation in its ``from`` type's detail pages: in a plain outgoing relations
    panel there, or a new one where the page has none (a panel set up for its own records keeps them
    alone; found in A4a, where a relation joined a translations panel sorted by its language)."""
    for path in detail_paths(document, from_key):
        panels = document.at(path).get("panels") or []
        panel = next((p for p in panels if _plain_outgoing_relations(p)), None)
        if panel is None:
            add_panel(document, path, _relations_panel([relation_key], panels))
        else:
            _append_new(
                document, path + ["panels", {"key": panel["key"]}, "config", "relationTypeKeys"], relation_key
            )


# What a relations panel may hold and still take any relation: its relation types, direction, title
# and place. A panel with columns, sorts or filters of its own is set up for the records it lists
# (a translations panel sorted by its language), and another type's relation would break it.
_PLAIN_RELATIONS_CONFIG = {"relationTypeKeys", "direction", "showRelationshipColumn"}


def _plain_outgoing_relations(panel: dict[str, Any]) -> bool:
    config = panel.get("config") or {}
    return (
        panel.get("type") == "relations"
        and config.get("direction") == "outgoing"
        and set(config) <= _PLAIN_RELATIONS_CONFIG
    )


def add_panel(document: Document, detail: Path, panel: dict[str, Any], index: int | None = None) -> None:
    document.insert(detail + ["panels"], panel, index)
    keep_order(document, detail + ["panels"], {"key": panel["key"]})


def keep_order(document: Document, path: Path, item: dict[str, Any]) -> bool:
    """Give ``item``'s ``order`` a value between its neighbours' (D35), renumbering as 10, 20, 30…
    only when no whole number fits between them; returns whether it changed an order. A panel's order
    counts within its region, so its neighbours are the panels of its region."""
    every = document.at(path)
    target = next(c for c in every if all(c.get(k) == v for k, v in item.items()))
    items = [c for c in every if _region(c) == _region(target)]
    index = next(i for i, candidate in enumerate(items) if candidate is target)
    before = items[index - 1].get("order", 0) if index > 0 else None
    after = items[index + 1].get("order", 0) if index + 1 < len(items) else None
    current = target.get("order")
    if isinstance(current, int) and (before is None or before < current) and (after is None or current < after):
        return False
    if before is None and after is None:
        wanted: int | None = 10
    elif after is None:
        wanted = before + 10
    elif before is None:
        wanted = after - 10
    else:
        wanted = (before + after) // 2 if after - before >= 2 else None
    if wanted is not None:
        document.set(path + [item], "order", wanted)
        return wanted != current
    for position, candidate in enumerate(items):
        document.set(path + [identity(candidate)], "order", (position + 1) * 10)
    return True


def _region(item: dict[str, Any]) -> str | None:
    return item.get("region", "main") if "type" in item else None


def _append_new(document: Document, path: Path, value: str) -> None:
    container = document.find(path)
    if isinstance(container, list) and value in container:
        return
    document.insert(path, value)


def _bindings_in_order(object_type: dict[str, Any]) -> list[dict[str, Any]]:
    bindings = [b for b in object_type.get("attributes") or [] if isinstance(b, dict)]
    return sorted(bindings, key=lambda b: b.get("order", 0))


def _is_containment(document: Document, relation_key: str) -> bool:
    relation = document.find(["relationTypes", {"key": relation_key}]) or {}
    return bool((relation.get("features") or {}).get("parentOf"))


def _hierarchy_panel() -> dict[str, Any]:
    return {"key": "hierarchy", "title": "Hierarchy", "type": "hierarchy", "region": "side", "order": 10}


def _children_panel(document: Document, children: list[str], panels: list[dict[str, Any]]) -> dict[str, Any]:
    first = document.find(type_path(children[0])) or {}
    return {
        "key": key_from_label("children", {p.get("key") for p in panels}),
        "title": first.get("pluralName") or "Children",
        "type": "children",
        "region": "main",
        "order": _next_order(panels),
        "config": {"objectTypeKeys": list(children), "columns": ["name"]},
    }


def _relations_panel(relation_keys: list[str], panels: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "key": key_from_label("relations", {p.get("key") for p in panels}),
        "title": "Related",
        "type": "relations",
        "region": "main",
        "order": _next_order(panels),
        "config": {"relationTypeKeys": list(relation_keys), "direction": "outgoing"},
    }


def _next_order(panels: list[dict[str, Any]]) -> int:
    return max((p.get("order", 0) for p in panels if p.get("region", "main") == "main"), default=0) + 10
