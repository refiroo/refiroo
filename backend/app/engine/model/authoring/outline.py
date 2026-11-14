"""A draft's outline: the structure an editor shows, read by the server (0.10 A4a, D36).

The editor shows a draft as its applications, their types in their containment tree, each type's
attributes, the relation types, the relations allowed between types and the navigation groups, each
element marked against the draft's base release. Containment and what counts as released are the
engine's rules (``layout.contained_types``, ``released.released_atoms``), so the browser reads them
here rather than deriving them from the JSON a second time.

The outline reads the draft's raw document: a draft may be invalid between steps, and it is outlined
with what can be read, beside the compiler's diagnostics, each tied to the element its pointer falls in.

A mark is ``new`` when the base release does not declare the element, ``changed`` when it does with a
different declaration, and ``released`` otherwise. Declarations are compared in the form a release
stores, every default written out (``_same``): a draft holds what was authored, and after an
installation its base release holds the same elements with their defaults (0.10 T1). A type is also ``changed`` when a relation allowed
from it was added, changed or removed: the relations a type starts are part of the type, as its
outgoing relations panel and the matrix's rows show.

An application lists a type either because it holds the type's records (the type is *own*: a table view
of it, or a tree that includes it) or because one of its relation views needs the type as rows,
columns, cells or ends (*borrowed*: the validation rule makes the view's types listed). A type that is
neither is *unused* there. The *home* of a type is the first application, in model order, where it is
own. The browser reads these sets from here (0.16.1 editor, borrowed types).
"""

import re
from typing import Any

from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from ....models.database import ModelDraft
from ....models.schema import (
    ApplicationDefinition,
    AttributeTypeDefinition,
    ConsumerApiDocument,
    EngineModel,
    NavigationGroupDefinition,
    ObjectTypeAttributeDefinition,
    ObjectTypeDefinition,
    ObjectTypeRelationDefinition,
    RelationTypeDefinition,
)
from ..compiler import compile_model
from ..consumer_contract import KEPT_VERSION_CHANGED, contract_diagnostics
from ..consumer_expansion import public_name
from ..diagnostics import ModelDiagnostic
from ..placements import model_placements
from ..releases import installed_versions, next_free_version
from .document import Document, is_containment
from .kinds import atom, unlistable_types
from .layout import contained_types
from .released import base_release, released_atoms


def suggested_release_version(session: Session, data: dict[str, Any], base: Any) -> str | None:
    """The version installing the draft proposes: its own when it is set, differs from its base's and
    no installed release of the key holds it; otherwise the next free one after the highest of its
    own and its base's. ``None`` when the draft has no release key."""
    release = data.get("release") or {}
    key, own = release.get("key"), str(release.get("version") or "")
    if not key:
        return None
    base_version = str(((base.model_json if base else None) or {}).get("release", {}).get("version") or "")
    if own and own != base_version and own not in installed_versions(session, key):
        return own
    highest = max([own, base_version], key=lambda text: [int(n) for n in re.findall(r"\d+", text)])
    return next_free_version(session, key, highest or "0.0.0")


def draft_outline(session: Session, draft: ModelDraft, active: EngineModel | None = None) -> dict[str, Any]:
    """The draft's outline at its current version, with its diagnostics, and each consumer API's
    contract against ``active``, the model the draft is compared with (0.10 A4c, D55; 0.11 D37);
    without one (a new model) every contract is compatible."""
    base = base_release(session, draft)
    data = draft.model_json if isinstance(draft.model_json, dict) else {}
    outline = build_outline(data, base.model_json if base else None)
    compiled = compile_model(draft.model_json)
    if compiled.valid and compiled.model is not None:
        found = contract_diagnostics(active, compiled.model) if active is not None else []
        for entry in outline["consumerApis"]:
            prefix = f"/consumerApis/{_escape(entry['key'])}"
            mine = [item for item in found if item.path == prefix or item.path.startswith(f"{prefix}/")]
            entry["contract"] = {
                "classification": "version_required"
                if any(i.severity == "error" and i.code != KEPT_VERSION_CHANGED for i in mine)
                else "compatible",
                "diagnostics": [diagnostic_with_element(data, item) for item in mine],
            }
    return {
        "version": draft.version,
        "suggestedReleaseVersion": suggested_release_version(session, data, base),
        "baseReleaseId": base.public_id if base else None,
        "workspaceKey": draft.workspace_key,
        **outline,
        "valid": compiled.valid,
        "diagnostics": [diagnostic_with_element(data, item) for item in compiled.diagnostics],
    }


def draft_model(draft: ModelDraft) -> dict[str, Any]:
    """The draft compiled as ``GET /model`` serves the active model, with its placements, for a
    client that renders it before installing (0.10 A4b, D43); without a model when it does not
    compile. A read: nothing is written."""
    data = draft.model_json if isinstance(draft.model_json, dict) else {}
    compiled = compile_model(draft.model_json)
    answer: dict[str, Any] = {
        "version": draft.version,
        "valid": compiled.valid,
        "diagnostics": [diagnostic_with_element(data, item) for item in compiled.diagnostics],
    }
    if compiled.valid and compiled.model is not None:
        answer["model"] = compiled.canonical_model
        answer["placements"] = model_placements(compiled.model)
    return answer


def build_outline(data: dict[str, Any], base: dict[str, Any] | None) -> dict[str, Any]:
    """The outline of a model document against its base release's document."""
    released = released_atoms(base)
    base = base or {}
    document = Document(data)
    mark = _Marks(released, base)
    relation_types = {item.get("key"): item for item in _items(data, "relationTypes")}
    containment = {key for key, item in relation_types.items() if is_containment(item)}
    bindings = _items(data, "objectTypeRelations")
    sharing: dict[str, list[str]] = {}
    for object_type in _items(data, "objectTypes"):
        for binding in _items(object_type, "attributes"):
            sharing.setdefault(binding.get("attributeTypeKey"), []).append(object_type.get("key"))
    attribute_types = {item.get("key"): item for item in _items(data, "attributeTypes")}
    roles = _roles(document, data, relation_types)
    homes = _homes(roles)

    object_types = []
    for object_type in _items(data, "objectTypes"):
        key = object_type.get("key")
        attributes = []
        for binding in _items(object_type, "attributes"):
            attribute_key = binding.get("attributeTypeKey")
            definition = attribute_types.get(attribute_key) or {}
            attributes.append(
                {
                    "attributeType": attribute_key,
                    "name": definition.get("name") or attribute_key,
                    "valueType": definition.get("valueType"),
                    "required": bool(binding.get("required", False)),
                    "readOnly": bool(binding.get("readOnly", False)),
                    "unique": bool((definition.get("features") or {}).get("unique", False)),
                    "sharedWith": [
                        other for other in sharing.get(attribute_key, []) if other != key
                    ],
                    "hidden": bool((binding.get("ui") or {}).get("hidden", False)),
                    "helpText": (binding.get("ui") or {}).get("helpText"),
                    "mark": mark.binding(key, attribute_key, binding),
                }
            )
        outgoing = [b for b in bindings if b.get("fromObjectTypeKey") == key]
        type_mark = mark.of(atom("objectType", key), object_type, ("objectTypes", key))
        if type_mark == "released" and mark.outgoing_differs(key, outgoing):
            type_mark = "changed"
        object_types.append(
            {
                "key": key,
                "name": object_type.get("name") or key,
                "pluralName": object_type.get("pluralName") or object_type.get("name") or key,
                "icon": object_type.get("icon"),
                "description": object_type.get("description"),
                "rootCreatable": bool((object_type.get("features") or {}).get("rootCreatable", False)),
                "parents": [
                    b.get("fromObjectTypeKey")
                    for b in bindings
                    if b.get("toObjectTypeKey") == key
                    and b.get("relationTypeKey") in ((object_type.get("behavior") or {}).get("parentRelationTypeKeys") or [])
                ],
                "displayAttribute": object_type.get("displayAttributeTypeKey"),
                "effectivePeriod": object_type.get("effectivePeriod"),
                "atLeastOneOf": list(
                    (object_type.get("validation") or {}).get("atLeastOneOf") or []
                ),
                "parentRelationTypeKeys": list(
                    (object_type.get("behavior") or {}).get("parentRelationTypeKeys") or []
                ),
                "attributes": attributes,
                "home": homes.get(key),
                "ownIn": [app for app, (own, _, _) in roles.items() if key in own],
                "borrowedIn": [
                    {"application": app, "uses": borrowed[key]}
                    for app, (_, borrowed, _) in roles.items()
                    if key in borrowed
                ],
                "mark": type_mark,
            }
        )

    applications = []
    for application in _items(data, "applications"):
        app_key = application.get("key")
        types = [key for key in application.get("objectTypeKeys") or [] if isinstance(key, str)]
        own, borrowed, unused = roles[app_key]
        applications.append(
            {
                "key": app_key,
                "name": application.get("name") or app_key,
                "icon": application.get("icon"),
                "color": application.get("color"),
                "defaultView": application.get("defaultView"),
                "objectTypeKeys": types,
                "tree": _tree(document, types),
                "ownTypes": own,
                "ownTree": _tree(document, own),
                "borrowed": [
                    {"objectType": key, "home": homes.get(key), "uses": uses} for key, uses in borrowed.items()
                ],
                "borrowedTree": _tree(document, list(borrowed)),
                "unused": unused,
                "navigation": _navigation(application, base, types),
                "views": _views(application, base),
                "unlistable": unlistable_types(document, app_key, released.__contains__),
                "mark": mark.of(atom("application", app_key), application, ("applications", app_key)),
            }
        )

    return {
        "release": {
            "key": (data.get("release") or {}).get("key"),
            "name": (data.get("release") or {}).get("name"),
            "version": (data.get("release") or {}).get("version"),
            "schemaVersion": data.get("schemaVersion"),
        },
        "baseRelease": (
            {
                "key": (base.get("release") or {}).get("key"),
                "name": (base.get("release") or {}).get("name"),
                "version": (base.get("release") or {}).get("version"),
            }
            if base
            else None
        ),
        "applications": applications,
        "objectTypes": object_types,
        "attributeTypes": [
            {
                "key": key,
                "name": item.get("name") or key,
                "valueType": item.get("valueType"),
                "features": item.get("features") or {},
                "minimum": (item.get("validation") or {}).get("minimum"),
                "maximum": (item.get("validation") or {}).get("maximum"),
                "hidden": bool((item.get("ui") or {}).get("hidden", False)),
                "helpText": (item.get("ui") or {}).get("helpText"),
                "boundBy": sharing.get(key, []),
                "mark": mark.of(atom("attributeType", key), item, ("attributeTypes", key)),
            }
            for key, item in attribute_types.items()
        ],
        "relationTypes": [
            {
                "key": key,
                "reverseKey": item.get("reverseKey"),
                "name": item.get("name") or key,
                "reverseName": item.get("reverseName"),
                "containment": key in containment,
                "isOriented": bool(item.get("isOriented", True)),
                "mark": mark.of(atom("relationType", key), item, ("relationTypes", key)),
            }
            for key, item in relation_types.items()
        ],
        # A definition without a key (one written by hand) is left to the diagnostics.
        "consumerApis": [
            _consumer_api(item, base) for item in _items(data, "consumerApis") if isinstance(item.get("key"), str)
        ],
        "relations": [
            {
                "relationType": b.get("relationTypeKey"),
                "from": b.get("fromObjectTypeKey"),
                "to": b.get("toObjectTypeKey"),
                "cardinality": b.get("cardinality"),
                "required": bool(b.get("required", False)),
                "containment": b.get("relationTypeKey") in containment,
                **(
                    {"attributeTypeKeys": list(b["attributeTypeKeys"])}
                    if b.get("attributeTypeKeys")
                    else {}
                ),
                **({"uniquePer": _unique_per(b)} if _unique_per(b) else {}),
                **({"candidates": b["candidates"]} if isinstance(b.get("candidates"), dict) else {}),
                "mark": mark.relation(b),
            }
            for b in bindings
        ],
    }


def _consumer_api(definition: dict[str, Any], base: dict[str, Any]) -> dict[str, Any]:
    """A consumer API definition as the editor lists it, marked against the base release's; its
    ``contract`` is added by :func:`draft_outline` when the draft compiles (D55)."""
    key = definition.get("key")
    before = _item(base, "consumerApis", key)
    names = definition.get("publicNames") if isinstance(definition.get("publicNames"), dict) else {}
    shape = definition.get("object") if isinstance(definition.get("object"), dict) else {}
    operations = definition.get("operations") if isinstance(definition.get("operations"), dict) else {}
    events = operations.get("events") if isinstance(operations.get("events"), dict) else {}
    version = definition.get("contractVersion")
    name, description = definition.get("name"), definition.get("description")
    return {
        "key": key,
        "name": name if isinstance(name, str) and name else key,
        "description": description if isinstance(description, str) else None,
        "contractVersion": version if isinstance(version, int) and not isinstance(version, bool) else None,
        "exposes": [
            {
                "objectType": type_key,
                "publicName": names[type_key] if isinstance(names.get(type_key), str) else public_name(type_key),
            }
            for type_key in definition.get("exposes") or []
            if isinstance(type_key, str)
        ],
        "counts": {
            "fields": _size(shape.get("fields")),
            "related": _size(shape.get("related")),
            "lists": _size(operations.get("lists")),
            "filters": _size(definition.get("filters")),
            "events": _size(events.get("custom")),
        },
        "mark": "new" if before is None else ("released" if _same("consumerApis", before, definition) else "changed"),
        "contract": None,
    }


def _size(value: Any) -> int:
    return len(value) if isinstance(value, (dict, list)) else 0


def _escape(segment: str) -> str:
    return segment.replace("~", "~0").replace("/", "~1")


def diagnostic_with_element(data: dict[str, Any], item: ModelDiagnostic) -> dict[str, Any]:
    result: dict[str, Any] = {"severity": item.severity, "code": item.code, "path": item.path, "message": item.message}
    if item.count is not None:
        result["count"] = item.count
    result["element"] = element_at(data, item.path)
    return result


def element_at(data: dict[str, Any], pointer: str) -> dict[str, str] | None:
    """The element a diagnostic's pointer falls in, named as operations name elements, or ``None``
    when it falls in no element (the release, the product). A segment
    names a list item by its key, as the validators write pointers, or by its index, as a shape
    error does."""
    parts = [_unescape(part) for part in pointer.split("/")[1:]] if pointer.startswith("/") else []
    if not parts:
        return None
    head, rest = parts[0], parts[1:]
    if head == "objectTypeRelations" and len(rest) >= 3 and not rest[0].isdigit():
        return {"relationType": rest[0], "from": rest[1], "to": rest[2]}
    if head == "objectTypeRelations" and rest:
        item = _item(data, head, rest[0])
        if item:
            return {
                "relationType": item.get("relationTypeKey"),
                "from": item.get("fromObjectTypeKey"),
                "to": item.get("toObjectTypeKey"),
            }
        return None
    if head == "consumerApis" and rest:
        definition = _item(data, head, rest[0])
        return {"consumerApi": definition.get("key")} if definition is not None else None
    names = {"objectTypes": "objectType", "attributeTypes": "attributeType", "relationTypes": "relationType"}
    if head in names and rest:
        item = _item(data, head, rest[0])
        if item is None:
            return None
        element = {names[head]: item.get("key")}
        if head == "objectTypes" and len(rest) >= 2 and rest[1] == "attributes":
            binding = _item(item, "attributes", rest[2], "attributeTypeKey") if len(rest) >= 3 else None
            if binding is not None:
                element["attributeType"] = binding.get("attributeTypeKey")
        return element
    if head == "applications" and rest:
        application = _item(data, head, rest[0])
        if application is None:
            return None
        element = {"applicationKey": application.get("key")}
        if len(rest) >= 4 and rest[1:3] == ["navigation", "groups"]:
            group = _item(application.get("navigation") or {}, "groups", rest[3])
            if group is not None:
                element["group"] = group.get("key")
        elif len(rest) >= 3 and rest[1] == "views":
            view = _item(application, "views", rest[2])
            if view is not None:
                element["view"] = view.get("key")
        elif len(rest) >= 3 and rest[1] == "details":
            detail = _item(application, "details", rest[2], "objectTypeKey")
            if detail is not None:
                element["detail"] = detail.get("objectTypeKey")
                if len(rest) >= 5 and rest[3] == "panels":
                    panel = _item(detail, "panels", rest[4])
                    if panel is not None:
                        element["panel"] = panel.get("key")
        return element
    return None


class _Marks:
    def __init__(self, released: frozenset[str], base: dict[str, Any]) -> None:
        self.released = released
        self.base = base

    def of(self, value: str, declaration: Any, where: tuple[str, str]) -> str:
        if value not in self.released:
            return "new"
        return "released" if _same(where[0], _item(self.base, where[0], where[1]), declaration) else "changed"

    def binding(self, type_key: str, attribute_key: str, declaration: Any) -> str:
        if atom("attributeBinding", type_key, attribute_key) not in self.released:
            return "new"
        base_type = _item(self.base, "objectTypes", type_key) or {}
        before = _item(base_type, "attributes", attribute_key, "attributeTypeKey")
        return "released" if _same("attributes", before, declaration) else "changed"

    def relation(self, declaration: dict[str, Any]) -> str:
        identity = (declaration.get("relationTypeKey"), declaration.get("fromObjectTypeKey"), declaration.get("toObjectTypeKey"))
        if atom("relationBinding", *[str(key) for key in identity]) not in self.released:
            return "new"
        return "released" if _same("objectTypeRelations", self._base_relation(identity), declaration) else "changed"

    def outgoing_differs(self, type_key: str, outgoing: list[dict[str, Any]]) -> bool:
        before = _by_identity([b for b in _items(self.base, "objectTypeRelations") if b.get("fromObjectTypeKey") == type_key])
        after = _by_identity(outgoing)
        return before.keys() != after.keys() or any(
            not _same("objectTypeRelations", before[identity], binding) for identity, binding in after.items()
        )

    def _base_relation(self, identity: tuple[Any, ...]) -> dict[str, Any] | None:
        return next(
            (
                b
                for b in _items(self.base, "objectTypeRelations")
                if (b.get("relationTypeKey"), b.get("fromObjectTypeKey"), b.get("toObjectTypeKey")) == identity
            ),
            None,
        )


_Uses = dict[str, list[dict[str, Any]]]


def _roles(
    document: Document, data: dict[str, Any], relation_types: dict[Any, dict[str, Any]]
) -> dict[Any, tuple[list[str], _Uses, list[str]]]:
    """For each application, in model order: the listed types it holds the records of (*own*, in the
    application's order), those its relation views use (*borrowed*, each with its uses) and those
    neither (*unused*). A use is ``{view, viewName, viewType, role, relationType, relationName}``; the
    role is rows, columns, cells, from, to, or link for a type on the containment path from a matrix's
    column type down to its cell type."""
    result: dict[Any, tuple[list[str], _Uses, list[str]]] = {}
    for application in _items(data, "applications"):
        listed = [key for key in application.get("objectTypeKeys") or [] if isinstance(key, str)]
        owned: set[str] = set()
        uses: _Uses = {}
        for view in _items(application, "views"):
            config = view.get("config") or {}
            kind = view.get("type")
            if kind == "table":
                owned.add(view.get("objectTypeKey"))
                continue
            if kind == "tree":
                owned.update(key for key in config.get("objectTypeKeys") or [] if isinstance(key, str))
                continue
            if kind == "relationMatrix":
                ends = [
                    ("rows", config.get("rowObjectTypeKey")),
                    ("columns", config.get("columnObjectTypeKey")),
                    ("cells", config.get("cellObjectTypeKey")),
                ]
                ends += [
                    ("link", key)
                    for key in _path_between(document, config.get("columnObjectTypeKey"), config.get("cellObjectTypeKey"))
                ]
            elif kind in ("mappingGrid", "relationTable"):
                ends = [("from", config.get("fromObjectTypeKey")), ("to", config.get("toObjectTypeKey"))]
            else:
                continue
            relation = config.get("relationTypeKey")
            for role, key in ends:
                if isinstance(key, str):
                    uses.setdefault(key, []).append(
                        {
                            "view": view.get("key"),
                            "viewName": view.get("name") or view.get("key"),
                            "viewType": kind,
                            "role": role,
                            "relationType": relation,
                            "relationName": (relation_types.get(relation) or {}).get("name") or relation,
                        }
                    )
        own = [key for key in listed if key in owned]
        borrowed = {key: uses[key] for key in listed if key not in owned and key in uses}
        result[application.get("key")] = (
            own,
            borrowed,
            [key for key in listed if key not in owned and key not in uses],
        )
    return result


def _homes(roles: dict[Any, tuple[list[str], _Uses, list[str]]]) -> dict[str, Any]:
    """The first application, in model order, where each type is own."""
    homes: dict[str, Any] = {}
    for app, (own, _, _) in roles.items():
        for key in own:
            homes.setdefault(key, app)
    return homes


def _path_between(document: Document, top: Any, bottom: Any) -> list[str]:
    """The types strictly between ``top`` and ``bottom`` on the shortest containment path down from
    one to the other; none when there is no path or they are the same type."""
    if not isinstance(top, str) or not isinstance(bottom, str) or top == bottom:
        return []
    came: dict[str, str] = {}
    pending = [top]
    while pending:
        current = pending.pop(0)
        for child in contained_types(document, current):
            if child in came or child == top:
                continue
            came[child] = current
            if child == bottom:
                path: list[str] = []
                node = came[child]
                while node != top:
                    path.append(node)
                    node = came[node]
                return path[::-1]
            pending.append(child)
    return []


def _tree(document: Document, types: list[str]) -> list[dict[str, Any]]:
    """The application's types by containment: each top-level type (one no type of the application
    contains) with the types it contains, in the application's order. A type contained by several
    parents appears under each; a cycle stops where a type would contain itself again."""
    members = set(types)
    children = {key: [c for c in contained_types(document, key) if c in members] for key in types}
    contained = {child for kids in children.values() for child in kids}

    def node(key: str, path: tuple[str, ...]) -> dict[str, Any]:
        below = [] if key in path else [node(child, (*path, key)) for child in children.get(key, [])]
        return {"objectType": key, "children": below}

    roots = [key for key in types if key not in contained]
    # A containment cycle with no top-level member would otherwise hide its types.
    for key in types:
        if key not in roots and not _reachable(key, roots, children):
            roots.append(key)
    return [node(key, ()) for key in roots]


def _reachable(key: str, roots: list[str], children: dict[str, list[str]]) -> bool:
    seen: set[str] = set()
    pending = list(roots)
    while pending:
        current = pending.pop()
        if current == key:
            return True
        if current in seen:
            continue
        seen.add(current)
        pending.extend(children.get(current, []))
    return False


def _navigation(application: dict[str, Any], base: dict[str, Any], types: list[str]) -> dict[str, Any]:
    base_application = _item(base, "applications", application.get("key")) or {}
    base_groups = {
        g.get("key"): g for g in _items(base_application.get("navigation") or {}, "groups")
    }
    navigation = application.get("navigation") or {}
    groups = []
    grouped: set[str] = set()
    for group in _items(navigation, "groups"):
        members = group.get("collections") or []
        collections = [c for c in members if isinstance(c, str)]
        grouped.update(collections)
        before = base_groups.get(group.get("key"))
        groups.append(
            {
                "key": group.get("key"),
                "label": group.get("label") or group.get("key"),
                "collapsed": bool(group.get("collapsed", False)),
                "collections": collections,
                # Types and matrices in the group's one order.
                "entries": [
                    {"collection": c} if isinstance(c, str) else {"view": c.get("view")}
                    for c in members
                    if isinstance(c, str)
                    or (isinstance(c, dict) and isinstance(c.get("view"), str))
                ],
                "mark": "new"
                if before is None
                else ("released" if _same("groups", before, group) else "changed"),
            }
        )
    opens = navigation.get("opens")
    return {
        "groups": groups,
        "ungrouped": [key for key in _collections(application) if key not in grouped],
        "opens": dict(opens) if isinstance(opens, dict) else {},
    }


def _collections(application: dict[str, Any]) -> list[str]:
    """The application's collections, first seen first: each view's source type (ADR-029), as
    ``validation.application_rules.collection_keys`` reads them from a parsed model."""
    result: list[str] = []
    for view in _items(application, "views"):
        source = _collection_of(view)
        if isinstance(source, str) and source not in result:
            result.append(source)
    return result


def _collection_of(view: dict[str, Any]) -> Any:
    """The collection a view belongs to: its source type."""
    config = view.get("config") or {}
    kind = view.get("type")
    if kind == "table":
        return view.get("objectTypeKey")
    if kind == "relationMatrix":
        return config.get("rowObjectTypeKey")
    if kind == "tree":
        return (config.get("rootObjectTypeKeys") or [None])[0]
    if kind == "relationTable":
        return config.get("fromObjectTypeKey")
    if config.get("direction") == "outgoing":
        return config.get("fromObjectTypeKey")
    return config.get("toObjectTypeKey")


def _views(application: dict[str, Any], base: dict[str, Any]) -> list[dict[str, Any]]:
    before = _item(base, "applications", application.get("key")) or {}
    result = []
    for view in _items(application, "views"):
        config = view.get("config") or {}
        kind = view.get("type")
        if kind == "table":
            shows = [view.get("objectTypeKey")]
        elif kind == "relationMatrix":
            shows = [config.get(name) for name in ("rowObjectTypeKey", "columnObjectTypeKey", "cellObjectTypeKey")]
        elif kind == "tree":
            shows = list(config.get("objectTypeKeys") or [])
        else:
            shows = [config.get("fromObjectTypeKey"), config.get("toObjectTypeKey")]
        old = _item(before, "views", view.get("key"))
        result.append(
            {
                "key": view.get("key"),
                "name": view.get("name") or view.get("key"),
                "type": kind,
                # The collection the view belongs to (its source type), for opening on it.
                "collection": _collection_of(view)
                if isinstance(_collection_of(view), str)
                else None,
                "shows": [key for key in shows if isinstance(key, str)],
                # What the editor changes a matrix from; the other kinds change in the preview.
                **({"matrix": config} if kind == "relationMatrix" else {}),
                **({"config": config} if kind in ("tree", "mappingGrid", "relationTable") else {}),
                "mark": "new" if old is None else "released" if old == view else "changed",
            }
        )
    return result


def _unique_per(binding: dict[str, Any]) -> str | None:
    features = binding.get("features")
    return features.get("uniqueToAncestorTypeKey") if isinstance(features, dict) else None


# The schema class of each kind of element, by the member that lists it.
_FORMS: dict[str, type[BaseModel]] = {
    "applications": ApplicationDefinition,
    "attributeTypes": AttributeTypeDefinition,
    "objectTypes": ObjectTypeDefinition,
    "relationTypes": RelationTypeDefinition,
    "objectTypeRelations": ObjectTypeRelationDefinition,
    "consumerApis": ConsumerApiDocument,
    "attributes": ObjectTypeAttributeDefinition,
    "groups": NavigationGroupDefinition,
}


def _same(collection: str, before: Any, after: Any) -> bool:
    """Whether two declarations of an element are the same, compared in the form a release stores
    them, every default written out; one that does not read as its schema class differs."""
    if before == after:
        return True
    if before is None or after is None:
        return False
    form = _FORMS[collection]
    try:
        return form.model_validate(before).model_dump(mode="json") == form.model_validate(after).model_dump(mode="json")
    except ValidationError:
        return False


def _by_identity(bindings: list[dict[str, Any]]) -> dict[tuple[Any, ...], dict[str, Any]]:
    return {(b.get("relationTypeKey"), b.get("fromObjectTypeKey"), b.get("toObjectTypeKey")): b for b in bindings}


def _items(node: Any, name: str) -> list[dict[str, Any]]:
    value = node.get(name) if isinstance(node, dict) else None
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _item(node: Any, collection: str, segment: Any, identity: str = "key") -> dict[str, Any] | None:
    items = _items(node, collection)
    for item in items:
        if item.get(identity) == segment:
            return item
    if isinstance(segment, str) and segment.isdigit() and int(segment) < len(items):
        return items[int(segment)]
    return None


def _unescape(segment: str) -> str:
    return segment.replace("~1", "/").replace("~0", "~")

