"""The model-side operation kinds (0.10 A2, [API.md § Kinds](../../../../docs/API.md)).

Each kind checks its parameters against the document, applies its change through
:class:`~.document.Document`, and returns what it did: its parameters as stored (generated keys
filled in), its inverse, and the elements it created, re-keyed and named (D8). A draft-only kind
asks :meth:`Context.unreleased` before it changes an element, which refuses when the element is in
the draft's base release (D17). Elements are named by key, never by position.

A compound kind (a removal, a split, a merge, a move, a containment change) has the inverse
``restoreElements``: the logged changes that put back exactly what it changed (ADR-041).
"""

import copy
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from ..compiler import SCHEMA_VERSIONS
from .cascade import Gone, prune, rename
from .document import Document, Path, Refusal, apply_changes, identity
from .keys import key_from_label
from .layout import (
    application_path,
    detail_page,
    keep_order,
    place_attribute,
    place_child,
    place_relation,
    table_view,
    type_path,
)
from .references import consumer_api_pointer, known_keys

VALUE_TYPES = {"text", "longText", "integer", "decimal", "boolean", "date", "dateTime", "json"}
CARDINALITIES = {"one-to-one", "one-to-many", "many-to-one", "many-to-many"}
# Element atoms, by kind, name the parts that identify an element.
ELEMENT_FIELDS: dict[str, tuple[str, ...]] = {
    "application": ("applicationKey",),
    "objectType": ("objectType",),
    "attributeType": ("attributeType",),
    "relationType": ("relationType",),
    "attributeBinding": ("objectType", "attributeType"),
    "relationBinding": ("relationType", "from", "to"),
    "view": ("applicationKey", "view"),
    "detail": ("applicationKey", "detail"),
    "panel": ("applicationKey", "detail", "panel"),
    "group": ("applicationKey", "group"),
}


def atom(kind: str, *keys: str) -> str:
    return f"{kind}:" + "/".join(keys)


def element_of(value: str) -> dict[str, str]:
    """The element an atom names, as operations name it."""
    kind, _, rest = value.partition(":")
    return dict(zip(ELEMENT_FIELDS[kind], rest.split("/"), strict=True))


class MigrationRequired(Exception):
    """A draft-only change to an element of the base release (D17): ``element`` is its atom."""

    def __init__(self, element: str) -> None:
        super().__init__(element)
        self.element = element


@dataclass
class Applied:
    parameters: dict[str, Any]
    inverse: dict[str, Any]
    created: set[str] = field(default_factory=set)
    rekeyed: set[str] = field(default_factory=set)
    named: set[str] = field(default_factory=set)


class Context:
    def __init__(self, document: Document, released: Callable[[str], bool]) -> None:
        self.document = document
        self.released = released

    @property
    def data(self) -> dict[str, Any]:
        return self.document.data

    def unreleased(self, *atoms: str) -> None:
        for value in atoms:
            if self.released(value):
                raise MigrationRequired(value)

    # --- finding elements ---

    def application(self, key: Any, name: str = "applicationKey") -> dict[str, Any]:
        return self._find("applications", key, name, "application")

    def object_type(self, key: Any, name: str = "objectType") -> dict[str, Any]:
        return self._find("objectTypes", key, name, "object type")

    def attribute_type(self, key: Any, name: str = "attributeType") -> dict[str, Any]:
        return self._find("attributeTypes", key, name, "attribute type")

    def relation_type(self, key: Any, name: str = "relationType") -> dict[str, Any]:
        return self._find("relationTypes", key, name, "relation type")

    def binding(self, type_key: str, attribute_key: str, name: str = "attributeType") -> dict[str, Any]:
        object_type = self.object_type(type_key)
        for item in object_type.get("attributes") or []:
            if item.get("attributeTypeKey") == attribute_key:
                return item
        raise Refusal(name, "unknownElement", f"Object type '{type_key}' does not bind '{attribute_key}'")

    def relation_binding(self, relation: str, source: str, target: str) -> dict[str, Any]:
        for item in self.document.items("objectTypeRelations"):
            if (item.get("relationTypeKey"), item.get("fromObjectTypeKey"), item.get("toObjectTypeKey")) == (
                relation,
                source,
                target,
            ):
                return item
        raise Refusal(
            "relationType", "unknownElement", f"Relation '{relation}' is not allowed from '{source}' to '{target}'"
        )

    def _find(self, collection: str, key: Any, name: str, label: str) -> dict[str, Any]:
        if not isinstance(key, str):
            raise Refusal(name, "invalidValue", f"'{name}' must be a key")
        found = self.document.find([collection, {"key": key}])
        if found is None:
            raise Refusal(name, "unknownElement", f"No {label} '{key}'")
        return found

    def keys(self, collection: str) -> set[str]:
        return {item.get("key") for item in self.document.items(collection)}

    def relation_keys(self) -> set[str]:
        return known_keys(self.data)[1]

    def new_key(self, params: Params, name: str, label: str, taken: set[str]) -> str:
        """The ``key`` parameter, or one generated from ``label`` (A-D6); refused when taken."""
        given = params.optional("key", str)
        if given is not None:
            if not given:
                raise Refusal("key", "invalidValue", "A key must not be empty")
            if given in taken:
                raise Refusal("key", "keyTaken", f"Key '{given}' is already used")
            return given
        return key_from_label(label, taken)

    def applications_of(self, type_key: str) -> list[str]:
        return [a["key"] for a in self.document.items("applications") if type_key in (a.get("objectTypeKeys") or [])]


class Params:
    """An operation's parameters, checked by name and type; anything else is refused."""

    def __init__(self, raw: dict[str, Any], allowed: tuple[str, ...]) -> None:
        unknown = [name for name in raw if name not in allowed]
        if unknown:
            raise Refusal(unknown[0], "unknownParameter", f"Unknown parameter '{unknown[0]}'")
        self.raw = raw

    def required(self, name: str, kind: type | tuple[type, ...] = str) -> Any:
        if name not in self.raw or self.raw[name] is None:
            raise Refusal(name, "missingParameter", f"'{name}' is required")
        return self.optional(name, kind)

    def optional(self, name: str, kind: type | tuple[type, ...] = str, default: Any = None) -> Any:
        value = self.raw.get(name, default)
        if value is None:
            return default
        if not isinstance(value, kind) or (kind is int and isinstance(value, bool)):
            raise Refusal(name, "invalidValue", f"'{name}' has the wrong type")
        return value

    def text(self, name: str) -> str:
        value = self.required(name, str)
        if not value.strip():
            raise Refusal(name, "invalidValue", f"'{name}' must not be empty")
        return value


KindFunction = Callable[[Context, dict[str, Any]], Applied]
KINDS: dict[str, KindFunction] = {}
# Kinds a request may not send: they are written by the server (PATCH, undo).
INTERNAL_KINDS = {"replaceModel", "restoreElements"}


def kind(name: str) -> Callable[[KindFunction], KindFunction]:
    def register(function: KindFunction) -> KindFunction:
        KINDS[name] = function
        return function

    return register


def apply_operation(context: Context, operation: dict[str, Any]) -> Applied:
    name = operation.get("kind")
    if not isinstance(name, str) or name not in KINDS:
        raise Refusal("kind", "unknownKind", f"Unknown operation kind '{name}'")
    parameters = {key: value for key, value in operation.items() if key != "kind"}
    return KINDS[name](context, parameters)


def restoring(context: Context, operation: dict[str, Any], applied: Applied) -> Applied:
    """``applied`` with the inverse that puts back what its kind changed."""
    applied.inverse = {
        "kind": "restoreElements",
        "undoes": operation,
        # What putting things back takes away: refused once released, as a removal would be.
        "removes": sorted(a for a in applied.created if a.split(":", 1)[0] in _RELEASABLE),
        "changes": context.document.reversal(),
    }
    return applied


_RELEASABLE = {"application", "objectType", "attributeType", "relationType", "attributeBinding", "relationBinding"}


# --- names ---

_LABEL_FIELDS: dict[str, tuple[str, ...]] = {
    "application": ("name", "description", "icon", "color"),
    "objectType": ("name", "pluralName", "description", "icon"),
    "attributeType": ("name", "description"),
    "relationType": ("name", "reverseName"),
    "view": ("name",),
    "panel": ("title",),
    "group": ("label",),
}


def element_reference(context: Context, raw: Any, name: str = "element") -> tuple[str, Path, str]:
    """An ``element`` parameter: its kind, path in the document and atom."""
    if not isinstance(raw, dict):
        raise Refusal(name, "invalidValue", "'element' must name an element by its keys")
    shape = set(raw)
    if shape == {"applicationKey"}:
        context.application(raw["applicationKey"], f"{name}/applicationKey")
        return "application", application_path(raw["applicationKey"]), atom("application", raw["applicationKey"])
    if shape == {"objectType"}:
        context.object_type(raw["objectType"], f"{name}/objectType")
        return "objectType", type_path(raw["objectType"]), atom("objectType", raw["objectType"])
    if shape == {"attributeType"}:
        context.attribute_type(raw["attributeType"], f"{name}/attributeType")
        return "attributeType", ["attributeTypes", {"key": raw["attributeType"]}], atom("attributeType", raw["attributeType"])
    if shape == {"relationType"}:
        context.relation_type(raw["relationType"], f"{name}/relationType")
        return "relationType", ["relationTypes", {"key": raw["relationType"]}], atom("relationType", raw["relationType"])
    if shape == {"applicationKey", "view"}:
        path = _view_path(context, raw["applicationKey"], raw["view"], name)
        return "view", path, atom("view", raw["applicationKey"], raw["view"])
    if shape == {"applicationKey", "detail", "panel"}:
        path = _panel_path(context, raw["applicationKey"], raw["detail"], raw["panel"], name)
        return "panel", path, atom("panel", raw["applicationKey"], raw["detail"], raw["panel"])
    if shape == {"applicationKey", "group"}:
        path = _group_path(context, raw["applicationKey"], raw["group"], name)
        return "group", path, atom("group", raw["applicationKey"], raw["group"])
    raise Refusal(name, "invalidValue", "'element' names no kind of element")


def _view_path(context: Context, app: Any, view: Any, name: str = "") -> Path:
    context.application(app, f"{name}/applicationKey".lstrip("/"))
    path = application_path(app) + ["views", {"key": view}]
    if not isinstance(view, str) or context.document.find(path) is None:
        raise Refusal(f"{name}/view".lstrip("/"), "unknownElement", f"No view '{view}' in '{app}'")
    return path


def _detail_path(context: Context, app: Any, detail: Any, name: str = "") -> Path:
    context.application(app, f"{name}/applicationKey".lstrip("/"))
    path = application_path(app) + ["details", {"objectTypeKey": detail}]
    if not isinstance(detail, str) or context.document.find(path) is None:
        raise Refusal(f"{name}/detail".lstrip("/"), "unknownElement", f"No detail page of '{detail}' in '{app}'")
    return path


def _panel_path(context: Context, app: Any, detail: Any, panel: Any, name: str = "") -> Path:
    path = _detail_path(context, app, detail, name) + ["panels", {"key": panel}]
    if not isinstance(panel, str) or context.document.find(path) is None:
        raise Refusal(f"{name}/panel".lstrip("/"), "unknownElement", f"No panel '{panel}' on '{detail}'")
    return path


def _group_path(context: Context, app: Any, group: Any, name: str = "") -> Path:
    context.application(app, f"{name}/applicationKey".lstrip("/"))
    path = application_path(app) + ["navigation", "groups", {"key": group}]
    if not isinstance(group, str) or context.document.find(path) is None:
        raise Refusal(f"{name}/group".lstrip("/"), "unknownElement", f"No navigation group '{group}' in '{app}'")
    return path


@kind("setLabel")
def set_label(context: Context, raw: dict[str, Any]) -> Applied:
    element_kind, path, element = element_reference(context, raw.get("element"))
    allowed = _LABEL_FIELDS[element_kind]
    params = Params(raw, ("element", *allowed))
    changes = {name: raw[name] for name in allowed if name in raw}
    if not changes:
        raise Refusal("element", "missingParameter", f"Name at least one of {list(allowed)}")
    node = context.document.at(path)
    old: dict[str, Any] = {}
    for name, value in changes.items():
        if value is not None and not isinstance(value, str):
            raise Refusal(name, "invalidValue", f"'{name}' must be text")
        old[name] = node.get(name)
        params.optional(name)
        context.document.set(path, name, value)
    return Applied(raw, {"kind": "setLabel", "element": raw["element"], **old}, named={element})


def _rename_scope(element_kind: str, raw: dict[str, Any]) -> Callable[[Any], bool] | None:
    if element_kind == "view":
        app = raw["applicationKey"]
        return lambda slot: slot.kind == "view" and slot.path[:2] == application_path(app)
    return None


@kind("setKey")
def set_key(context: Context, raw: dict[str, Any]) -> Applied:
    element_kind, path, element = element_reference(context, raw.get("element"))
    params = Params(raw, ("element", "key", "reverseKey"))
    new = params.text("key")
    reference = raw["element"]
    old = context.document.at(path).get("key")
    taken: set[str] = {
        "application": context.keys("applications"),
        "objectType": context.keys("objectTypes"),
        "attributeType": context.keys("attributeTypes"),
        "relationType": context.relation_keys(),
        "view": {v.get("key") for v in (context.document.at(path[:-2]).get("views") or [])},
        "panel": {p.get("key") for p in (context.document.at(path[:-2]).get("panels") or [])},
        "group": {g.get("key") for g in (context.document.at(path[:-2]).get("groups") or [])},
    }[element_kind]
    if new != old and new in taken:
        raise Refusal("key", "keyTaken", f"Key '{new}' is already used")
    reverse_new = params.optional("reverseKey")
    if reverse_new is not None and element_kind != "relationType":
        raise Refusal("reverseKey", "invalidValue", "Only a relation type has a reverse key")
    if element_kind in ("application", "objectType", "attributeType", "relationType"):
        context.unreleased(element)
        names = {old} | ({context.document.at(path).get("reverseKey")} if element_kind == "relationType" else set())
        pointer = consumer_api_pointer(context.data, {name for name in names if name})
        if pointer is not None:
            raise Refusal(
                "element",
                "namedByConsumerApi",
                f"'{old}' is named by a consumer API definition at {pointer}; change it there first",
            )
    inverse: dict[str, Any] = {"kind": "setKey", "key": old}
    if element_kind == "relationType":
        old_reverse = context.document.at(path).get("reverseKey")
        if reverse_new is not None and reverse_new != old_reverse and reverse_new in taken | {new}:
            raise Refusal("reverseKey", "keyTaken", f"Key '{reverse_new}' is already used")
        rename(context.document, "relationKey", old, new)
        if reverse_new is not None and reverse_new != old_reverse:
            rename(context.document, "relationKey", old_reverse, reverse_new)
            context.document.set(["relationTypes", {"key": new}], "reverseKey", reverse_new)
            inverse["reverseKey"] = old_reverse
    elif element_kind in ("panel", "group"):
        context.document.set(path, "key", new)
    else:
        rename(context.document, element_kind, old, new, _rename_scope(element_kind, reference))
    new_reference = dict(reference)
    new_reference[{"application": "applicationKey"}.get(element_kind, element_kind)] = new
    inverse["element"] = new_reference
    new_atom = atom(element_kind, *[new_reference[f] for f in ELEMENT_FIELDS[element_kind]])
    return Applied(raw, inverse, rekeyed={new_atom}, named={element})


@kind("setRelease")
def set_release(context: Context, raw: dict[str, Any]) -> Applied:
    params = Params(raw, ("key", "name", "version", "schemaVersion"))
    if not isinstance(context.data.get("release"), dict):
        context.document.set([], "release", {})
    old = {name: context.data["release"].get(name) for name in ("key", "name", "version") if name in raw}
    for name in ("key", "name", "version"):
        if name in raw:
            context.document.set(["release"], name, params.text(name))
    inverse: dict[str, Any] = {"kind": "setRelease", **old}
    schema = params.optional("schemaVersion")
    if schema is not None:
        current = context.data.get("schemaVersion")
        if schema not in SCHEMA_VERSIONS:
            raise Refusal("schemaVersion", "invalidValue", f"Schema version '{schema}' is not supported")
        inverse["schemaVersion"] = current
        context.document.set([], "schemaVersion", schema)
    if len(inverse) == 1:
        raise Refusal("version", "missingParameter", "Name at least one of key, name, version")
    return Applied(raw, inverse)


# --- applications ---


@kind("addApplication")
def add_application(context: Context, raw: dict[str, Any]) -> Applied:
    params = Params(raw, ("key", "name", "description", "icon", "color", "position"))
    name = params.text("name")
    key = context.new_key(params, "key", name, context.keys("applications"))
    application: dict[str, Any] = {"key": key, "name": name}
    for optional in ("description", "icon", "color"):
        if params.optional(optional) is not None:
            application[optional] = raw[optional]
    application.update({"objectTypeKeys": [], "defaultView": "", "views": [], "details": []})
    context.document.insert(["applications"], application, _position(params, context.document.items("applications")))
    stored = {**raw, "key": key}
    return Applied(
        stored,
        {"kind": "removeApplication", "applicationKey": key},
        created={atom("application", key)},
    )


@kind("removeApplication")
def remove_application(context: Context, raw: dict[str, Any]) -> Applied:
    params = Params(raw, ("applicationKey",))
    key = params.text("applicationKey")
    application = context.application(key)
    context.unreleased(atom("application", key))
    only_here = [t for t in application.get("objectTypeKeys") or [] if context.applications_of(t) == [key]]
    for type_key in only_here:
        context.unreleased(atom("objectType", type_key))
    context.document.remove(["applications"], {"key": key})
    gone = Gone()
    for type_key in only_here:
        _remove_type(context, type_key, gone)
    prune(context.document, gone)
    return restoring(
        context,
        {"kind": "removeApplication", **raw},
        Applied(raw, {}, named={atom("application", key)}),
    )


# --- object types ---


def _parent(context: Context, raw: Any, child: str, name: str = "parent") -> tuple[list[str], str | dict[str, Any]] | None:
    """A ``parent`` parameter (D30): ``None`` for the top level, or the parent types and the
    containment relation type (a key, or a new one's ``name``, ``reverseName`` and ``key``)."""
    if raw is None:
        return None
    if not isinstance(raw, dict) or set(raw) - {"objectTypes", "relationType"}:
        raise Refusal(name, "invalidValue", "'parent' is null or names objectTypes and a relationType")
    parents = raw.get("objectTypes")
    if not isinstance(parents, list) or not parents:
        raise Refusal(f"{name}/objectTypes", "invalidValue", "Name at least one parent type")
    for position, parent in enumerate(parents):
        if parent != child:
            context.object_type(parent, f"{name}/objectTypes/{position}")
    relation = raw.get("relationType")
    if isinstance(relation, str):
        found = context.relation_type(relation, f"{name}/relationType")
        if not (found.get("features") or {}).get("parentOf"):
            raise Refusal(f"{name}/relationType", "invalidValue", f"'{relation}' is not a containment relation type")
        return list(parents), relation
    if not isinstance(relation, dict):
        raise Refusal(f"{name}/relationType", "missingParameter", "Name the containment relation type")
    unknown = set(relation) - {"key", "reverseKey", "name", "reverseName"}
    if unknown or not isinstance(relation.get("name"), str) or not isinstance(relation.get("reverseName"), str):
        raise Refusal(f"{name}/relationType", "invalidValue", "A new relation type needs name and reverseName")
    taken = context.relation_keys()
    key = relation.get("key") or key_from_label(f"{parents[0]}-{relation['name']}", taken)
    if key in taken:
        raise Refusal(f"{name}/relationType/key", "keyTaken", f"Key '{key}' is already used")
    reverse = relation.get("reverseKey") or key_from_label(f"{child}-{relation['reverseName']}", taken | {key})
    if reverse in taken | {key}:
        raise Refusal(f"{name}/relationType/reverseKey", "keyTaken", f"Key '{reverse}' is already used")
    return list(parents), {**relation, "key": key, "reverseKey": reverse}


def _contain(context: Context, child: str, parent: tuple[list[str], str | dict[str, Any]] | None) -> tuple[Any, set[str]]:
    """Place ``child`` at the top or under its parents; returns the stored parent and created atoms."""
    created: set[str] = set()
    path = type_path(child)
    if parent is None:
        context.document.set(path, "features", {**(context.document.at(path).get("features") or {}), "rootCreatable": True})
        return None, created
    parents, relation = parent
    if isinstance(relation, dict):
        context.document.insert(
            ["relationTypes"],
            {
                "key": relation["key"],
                "reverseKey": relation["reverseKey"],
                "name": relation["name"],
                "reverseName": relation["reverseName"],
                "features": {"parentOf": True, "creatableOnChildAdd": True},
            },
        )
        created.add(atom("relationType", relation["key"]))
        relation_key = relation["key"]
    else:
        relation_key = relation
    for parent_key in parents:
        context.document.insert(
            ["objectTypeRelations"],
            {
                "relationTypeKey": relation_key,
                "fromObjectTypeKey": parent_key,
                "toObjectTypeKey": child,
                "cardinality": "one-to-many",
            },
        )
        created.add(atom("relationBinding", relation_key, parent_key, child))
    object_type = context.document.at(path)
    context.document.set(path, "features", {**(object_type.get("features") or {}), "rootCreatable": False})
    behavior = dict(object_type.get("behavior") or {})
    behavior["parentRelationTypeKeys"] = [relation_key]
    context.document.set(path, "behavior", behavior)
    return {"objectTypes": parents, "relationType": relation}, created


@kind("addObjectType")
def add_object_type(context: Context, raw: dict[str, Any]) -> Applied:
    params = Params(
        raw,
        ("applicationKey", "key", "name", "pluralName", "parent", "displayAttribute", "description", "icon", "layout"),
    )
    app = params.text("applicationKey")
    context.application(app)
    name = params.text("name")
    plural = params.optional("pluralName") or f"{name}s"
    key = context.new_key(params, "key", name, context.keys("objectTypes"))
    if "parent" not in raw:
        raise Refusal("parent", "missingParameter", "'parent' is required (null for the top level)")
    parent = _parent(context, raw.get("parent"), key)
    object_type: dict[str, Any] = {"key": key, "name": name, "pluralName": plural}
    for optional in ("description", "icon"):
        if params.optional(optional) is not None:
            object_type[optional] = raw[optional]
    object_type["attributes"] = []
    context.document.insert(["objectTypes"], object_type)
    context.document.insert(application_path(app) + ["objectTypeKeys"], key)
    stored_parent, created = _contain(context, key, parent)
    created |= {atom("objectType", key)}
    display = params.optional("displayAttribute")
    if display is not None:
        context.attribute_type(display, "displayAttribute")
        context.document.set(type_path(key), "displayAttributeTypeKey", display)
    if params.optional("layout", bool, True):
        view = table_view(context.document, app, key)
        context.document.insert(application_path(app) + ["views"], view)
        if not context.document.at(application_path(app)).get("defaultView"):
            context.document.set(application_path(app), "defaultView", view["key"])
        created.add(atom("view", app, view["key"]))
        # A detail page where the application declares its detail pages; one without them shows
        # every type on the default page, and the server does not start a list for one type.
        if isinstance(context.document.at(application_path(app)).get("details"), list):
            context.document.insert(application_path(app) + ["details"], detail_page(context.document, key))
            created.add(atom("detail", app, key))
        if parent is not None:
            for parent_key in parent[0]:
                if parent_key != key:
                    place_child(context.document, parent_key, key)
    stored = {**raw, "key": key, "pluralName": plural, "parent": stored_parent}
    named = {atom("application", app)} | {atom("objectType", p) for p in (parent[0] if parent else [])}
    if isinstance(stored_parent, dict) and isinstance(stored_parent["relationType"], str):
        named.add(atom("relationType", stored_parent["relationType"]))
    if display:
        named.add(atom("attributeType", display))
    return Applied(stored, {"kind": "removeObjectType", "objectType": key}, created=created, named=named)


def _remove_type(context: Context, type_key: str, gone: Gone) -> None:
    """Take a type out with what only it used (D31); ``gone`` collects what went."""
    document = context.document
    object_type = document.at(type_path(type_key))
    bound = [b.get("attributeTypeKey") for b in object_type.get("attributes") or []]
    gone.types.add(type_key)
    gone.bindings |= {(type_key, key) for key in bound}
    document.remove(["objectTypes"], {"key": type_key})
    relations = set()
    for binding in list(document.items("objectTypeRelations")):
        if type_key in (binding.get("fromObjectTypeKey"), binding.get("toObjectTypeKey")):
            relations.add(binding["relationTypeKey"])
            document.remove(["objectTypeRelations"], identity(binding))
    for relation_key in sorted(relations):
        _drop_unbound_relation(context, relation_key, gone)
    for attribute_key in bound:
        _drop_unbound_attribute(context, attribute_key, gone)


def _drop_unbound_relation(context: Context, relation_key: str, gone: Gone) -> None:
    document = context.document
    if any(b.get("relationTypeKey") == relation_key for b in document.items("objectTypeRelations")):
        return
    if context.released(atom("relationType", relation_key)):
        return
    relation = document.find(["relationTypes", {"key": relation_key}])
    if relation is None:
        return
    document.remove(["relationTypes"], {"key": relation_key})
    gone.relation_keys |= {relation_key, relation.get("reverseKey")}


def _drop_unbound_attribute(context: Context, attribute_key: str, gone: Gone) -> None:
    document = context.document
    for object_type in document.items("objectTypes"):
        if any(b.get("attributeTypeKey") == attribute_key for b in object_type.get("attributes") or []):
            return
    if any(attribute_key in (b.get("attributeTypeKeys") or []) for b in document.items("objectTypeRelations")):
        return
    if context.released(atom("attributeType", attribute_key)):
        return
    if document.find(["attributeTypes", {"key": attribute_key}]) is not None:
        document.remove(["attributeTypes"], {"key": attribute_key})
        gone.attribute_types.add(attribute_key)


@kind("removeObjectType")
def remove_object_type(context: Context, raw: dict[str, Any]) -> Applied:
    params = Params(raw, ("objectType",))
    key = params.text("objectType")
    context.object_type(key)
    context.unreleased(atom("objectType", key))
    gone = Gone()
    for app in context.applications_of(key):
        context.document.remove(application_path(app) + ["objectTypeKeys"], key)
    _remove_type(context, key, gone)
    prune(context.document, gone)
    return restoring(context, {"kind": "removeObjectType", **raw}, Applied(raw, {}, named={atom("objectType", key)}))


@kind("splitObjectType")
def split_object_type(context: Context, raw: dict[str, Any]) -> Applied:
    params = Params(raw, ("objectType", "key", "name", "pluralName", "attributes", "relationType", "cardinality"))
    source = params.text("objectType")
    context.object_type(source)
    moved = params.required("attributes", list)
    for position, attribute_key in enumerate(moved):
        context.binding(source, attribute_key, f"attributes/{position}")
    context.unreleased(atom("objectType", source), *(atom("attributeBinding", source, a) for a in moved))
    apps = context.applications_of(source)
    if not apps:
        raise Refusal("objectType", "invalidValue", f"'{source}' is in no application")
    name = params.text("name")
    cardinality = params.optional("cardinality", str, "many-to-many")
    if cardinality not in CARDINALITIES:
        raise Refusal("cardinality", "invalidValue", f"Unknown cardinality '{cardinality}'")
    relation = params.required("relationType", (str, dict))
    new_key = context.new_key(params, "key", name, context.keys("objectTypes"))
    relation_key, created = _relation_for(context, relation, "relationType", f"{source}-{new_key}")
    added = add_object_type(
        context,
        {"applicationKey": apps[0], "key": new_key, "name": name, "pluralName": raw.get("pluralName"), "parent": None},
    )
    gone = Gone()
    for attribute_key in moved:
        binding = copy.deepcopy(context.binding(source, attribute_key))
        context.document.remove(type_path(source) + ["attributes"], {"attributeTypeKey": attribute_key})
        gone.bindings.add((source, attribute_key))
        context.document.insert(type_path(new_key) + ["attributes"], binding)
        place_attribute(context.document, new_key, attribute_key)
    prune(context.document, gone)
    _allow(context, relation_key, source, new_key, cardinality, False)
    stored = {**raw, "key": new_key, "relationType": relation_key if isinstance(relation, str) else {**relation, "key": relation_key}}
    applied = Applied(
        stored,
        {},
        created=added.created | created | {atom("relationBinding", relation_key, source, new_key)},
        named={atom("objectType", source)} | {atom("attributeType", a) for a in moved},
    )
    return restoring(context, {"kind": "splitObjectType", **stored}, applied)


@kind("mergeObjectTypes")
def merge_object_types(context: Context, raw: dict[str, Any]) -> Applied:
    params = Params(raw, ("into", "from"))
    into, source = params.text("into"), params.text("from")
    context.object_type(into, "into")
    context.object_type(source, "from")
    if into == source:
        raise Refusal("from", "invalidValue", "A type cannot be merged into itself")
    context.unreleased(atom("objectType", into), atom("objectType", source))
    document = context.document
    target_bound = {b.get("attributeTypeKey") for b in document.at(type_path(into)).get("attributes") or []}
    for binding in list(document.at(type_path(source)).get("attributes") or []):
        if binding.get("attributeTypeKey") not in target_bound:
            document.insert(type_path(into) + ["attributes"], copy.deepcopy(binding))
            place_attribute(document, into, binding["attributeTypeKey"])
    for app in context.applications_of(source):
        if into not in (document.at(application_path(app)).get("objectTypeKeys") or []):
            document.insert(application_path(app) + ["objectTypeKeys"], into)
        document.remove(application_path(app) + ["objectTypeKeys"], source)
    for binding in list(document.items("objectTypeRelations")):
        ends = (binding.get("fromObjectTypeKey"), binding.get("toObjectTypeKey"))
        if source not in ends:
            continue
        moved = {
            **copy.deepcopy(binding),
            "fromObjectTypeKey": into if ends[0] == source else ends[0],
            "toObjectTypeKey": into if ends[1] == source else ends[1],
        }
        document.remove(["objectTypeRelations"], identity(binding))
        if document.find(["objectTypeRelations", identity(moved)]) is None:
            document.insert(["objectTypeRelations"], moved)
    source_behavior = document.at(type_path(source)).get("behavior") or {}
    target = document.at(type_path(into))
    parents = list((target.get("behavior") or {}).get("parentRelationTypeKeys") or [])
    for relation_key in source_behavior.get("parentRelationTypeKeys") or []:
        if relation_key not in parents:
            parents.append(relation_key)
    if parents:
        document.set(type_path(into), "behavior", {**(target.get("behavior") or {}), "parentRelationTypeKeys": parents})
    document.remove(["objectTypes"], {"key": source})
    gone = Gone(types={source})
    prune(document, gone)
    return restoring(
        context,
        {"kind": "mergeObjectTypes", **raw},
        Applied(raw, {}, named={atom("objectType", into), atom("objectType", source)}),
    )


@kind("convertAttributeToListType")
def convert_attribute_to_list_type(context: Context, raw: dict[str, Any]) -> Applied:
    params = Params(raw, ("objectType", "attributeType", "key", "name", "pluralName", "relationType"))
    owner, attribute_key = params.text("objectType"), params.text("attributeType")
    context.binding(owner, attribute_key)
    context.unreleased(atom("attributeBinding", owner, attribute_key))
    apps = context.applications_of(owner)
    if not apps:
        raise Refusal("objectType", "invalidValue", f"'{owner}' is in no application")
    name = params.text("name")
    new_key = context.new_key(params, "key", name, context.keys("objectTypes"))
    relation = params.required("relationType", (str, dict))
    relation_key, created = _relation_for(context, relation, "relationType", f"{owner}-{new_key}")
    added = add_object_type(
        context,
        {"applicationKey": apps[0], "key": new_key, "name": name, "pluralName": raw.get("pluralName"), "parent": None},
    )
    context.document.remove(type_path(owner) + ["attributes"], {"attributeTypeKey": attribute_key})
    gone = Gone(bindings={(owner, attribute_key)})
    _drop_unbound_attribute(context, attribute_key, gone)
    prune(context.document, gone)
    _allow(context, relation_key, owner, new_key, "many-to-many", False)
    stored = {**raw, "key": new_key, "relationType": relation_key if isinstance(relation, str) else {**relation, "key": relation_key}}
    applied = Applied(
        stored,
        {},
        created=added.created | created | {atom("relationBinding", relation_key, owner, new_key)},
        named={atom("attributeBinding", owner, attribute_key), atom("objectType", owner)},
    )
    return restoring(context, {"kind": "convertAttributeToListType", **stored}, applied)


def _relation_for(context: Context, relation: Any, name: str, label: str) -> tuple[str, set[str]]:
    """An existing relation type's key, or a new one added (``name``, ``reverseName``, ``key``)."""
    if isinstance(relation, str):
        context.relation_type(relation, name)
        return relation, set()
    if not isinstance(relation.get("name"), str) or not isinstance(relation.get("reverseName"), str):
        raise Refusal(name, "invalidValue", "A new relation type needs name and reverseName")
    added = add_relation_type(context, dict(relation))
    return added.parameters["key"], added.created


# --- attributes ---


def _features(raw: Any, name: str = "features") -> dict[str, Any]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise Refusal(name, "invalidValue", "'features' is an object")
    return dict(raw)


@kind("addAttributeType")
def add_attribute_type(context: Context, raw: dict[str, Any]) -> Applied:
    params = Params(raw, ("key", "name", "valueType", "features", "validation", "description"))
    name = params.text("name")
    value_type = params.optional("valueType", str, "text")
    if value_type not in VALUE_TYPES:
        raise Refusal("valueType", "invalidValue", f"Unknown value type '{value_type}'")
    key = context.new_key(params, "key", name, context.keys("attributeTypes"))
    attribute: dict[str, Any] = {"key": key, "name": name, "valueType": value_type}
    if params.optional("description") is not None:
        attribute["description"] = raw["description"]
    features = _features(raw.get("features"))
    if features:
        attribute["features"] = features
    validation = params.optional("validation", dict)
    if validation:
        attribute["validation"] = validation
    context.document.insert(["attributeTypes"], attribute)
    return Applied(
        {**raw, "key": key, "valueType": value_type},
        {"kind": "removeAttributeType", "attributeType": key},
        created={atom("attributeType", key)},
    )


@kind("removeAttributeType")
def remove_attribute_type(context: Context, raw: dict[str, Any]) -> Applied:
    params = Params(raw, ("attributeType",))
    key = params.text("attributeType")
    context.attribute_type(key)
    bound = any(
        b.get("attributeTypeKey") == key for t in context.document.items("objectTypes") for b in t.get("attributes") or []
    ) or any(key in (b.get("attributeTypeKeys") or []) for b in context.document.items("objectTypeRelations"))
    if bound:
        raise Refusal("attributeType", "stillBound", f"Attribute type '{key}' is still attached to a type or relation")
    context.unreleased(atom("attributeType", key))
    context.document.remove(["attributeTypes"], {"key": key})
    prune(context.document, Gone(attribute_types={key}))
    return restoring(context, {"kind": "removeAttributeType", **raw}, Applied(raw, {}, named={atom("attributeType", key)}))


@kind("setAttributeTypeFeatures")
def set_attribute_type_features(context: Context, raw: dict[str, Any]) -> Applied:
    params = Params(raw, ("attributeType", "features"))
    key = params.text("attributeType")
    attribute = context.attribute_type(key)
    changes = _features(params.required("features", dict))
    current = dict(attribute.get("features") or {})
    if changes.get("unique") and not current.get("unique"):
        context.unreleased(atom("attributeType", key))
    old = {name: current.get(name) for name in changes}
    for name, value in changes.items():
        if value is None:
            current.pop(name, None)
        else:
            current[name] = value
    context.document.set(["attributeTypes", {"key": key}], "features", current or None)
    return Applied(raw, {"kind": "setAttributeTypeFeatures", "attributeType": key, "features": old}, named={atom("attributeType", key)})


@kind("setValueType")
def set_value_type(context: Context, raw: dict[str, Any]) -> Applied:
    params = Params(raw, ("attributeType", "valueType", "validation"))
    key = params.text("attributeType")
    attribute = context.attribute_type(key)
    # ``null`` is the default, text, left unwritten (as an inverse writes it back).
    value_type = params.optional("valueType")
    if "valueType" not in raw or (value_type is not None and value_type not in VALUE_TYPES):
        raise Refusal("valueType", "invalidValue", f"Unknown value type '{value_type}'")
    context.unreleased(atom("attributeType", key))
    inverse = {"kind": "setValueType", "attributeType": key, "valueType": attribute.get("valueType")}
    if "validation" in raw:
        inverse["validation"] = attribute.get("validation")
        context.document.set(["attributeTypes", {"key": key}], "validation", params.optional("validation", dict) or None)
    context.document.set(["attributeTypes", {"key": key}], "valueType", value_type)
    return Applied(raw, inverse, named={atom("attributeType", key)})


@kind("attachAttribute")
def attach_attribute(context: Context, raw: dict[str, Any]) -> Applied:
    params = Params(raw, ("objectType", "attributeType", "required", "readOnly", "position", "layout"))
    type_key, attribute_key = params.text("objectType"), params.text("attributeType")
    object_type = context.object_type(type_key)
    context.attribute_type(attribute_key)
    bindings = object_type.get("attributes") or []
    if any(b.get("attributeTypeKey") == attribute_key for b in bindings):
        raise Refusal("attributeType", "alreadyAttached", f"'{type_key}' already binds '{attribute_key}'")
    required = params.optional("required", bool, False)
    if required:
        context.unreleased(atom("objectType", type_key))
    binding: dict[str, Any] = {"attributeTypeKey": attribute_key}
    if required:
        binding["required"] = True
    if params.optional("readOnly", bool, False):
        binding["readOnly"] = True
    index = _position(params, bindings)
    context.document.insert(type_path(type_key) + ["attributes"], binding, index)
    keep_order(context.document, type_path(type_key) + ["attributes"], {"attributeTypeKey": attribute_key})
    if params.optional("layout", bool, True):
        place_attribute(context.document, type_key, attribute_key)
    return Applied(
        raw,
        {"kind": "detachAttribute", "objectType": type_key, "attributeType": attribute_key},
        created={atom("attributeBinding", type_key, attribute_key)},
        named={atom("objectType", type_key), atom("attributeType", attribute_key)},
    )


@kind("detachAttribute")
def detach_attribute(context: Context, raw: dict[str, Any]) -> Applied:
    params = Params(raw, ("objectType", "attributeType"))
    type_key, attribute_key = params.text("objectType"), params.text("attributeType")
    context.binding(type_key, attribute_key)
    context.unreleased(atom("attributeBinding", type_key, attribute_key))
    context.document.remove(type_path(type_key) + ["attributes"], {"attributeTypeKey": attribute_key})
    prune(context.document, Gone(bindings={(type_key, attribute_key)}))
    return restoring(
        context,
        {"kind": "detachAttribute", **raw},
        Applied(raw, {}, named={atom("attributeBinding", type_key, attribute_key), atom("objectType", type_key), atom("attributeType", attribute_key)}),
    )


@kind("moveAttribute")
def move_attribute(context: Context, raw: dict[str, Any]) -> Applied:
    params = Params(raw, ("attributeType", "from", "to", "layout"))
    attribute_key, source, target = params.text("attributeType"), params.text("from"), params.text("to")
    binding = copy.deepcopy(context.binding(source, attribute_key))
    target_type = context.object_type(target, "to")
    if any(b.get("attributeTypeKey") == attribute_key for b in target_type.get("attributes") or []):
        raise Refusal("to", "alreadyAttached", f"'{target}' already binds '{attribute_key}'")
    context.unreleased(atom("attributeBinding", source, attribute_key))
    context.document.remove(type_path(source) + ["attributes"], {"attributeTypeKey": attribute_key})
    prune(context.document, Gone(bindings={(source, attribute_key)}))
    context.document.insert(type_path(target) + ["attributes"], binding)
    keep_order(context.document, type_path(target) + ["attributes"], {"attributeTypeKey": attribute_key})
    if params.optional("layout", bool, True):
        place_attribute(context.document, target, attribute_key)
    return restoring(
        context,
        {"kind": "moveAttribute", **raw},
        Applied(
            raw,
            {},
            created={atom("attributeBinding", target, attribute_key)},
            named={atom("attributeBinding", source, attribute_key), atom("objectType", target), atom("attributeType", attribute_key)},
        ),
    )


@kind("setAttributeBinding")
def set_attribute_binding(context: Context, raw: dict[str, Any]) -> Applied:
    params = Params(raw, ("objectType", "attributeType", "required", "readOnly", "position"))
    type_key, attribute_key = params.text("objectType"), params.text("attributeType")
    binding = context.binding(type_key, attribute_key)
    path = type_path(type_key) + ["attributes"]
    inverse: dict[str, Any] = {"kind": "setAttributeBinding", "objectType": type_key, "attributeType": attribute_key}
    for name in ("required", "readOnly"):
        if name in raw:
            value = _flag(raw, name)
            if bool(binding.get(name, False)) != bool(value):
                context.unreleased(atom("attributeBinding", type_key, attribute_key))
            inverse[name] = binding.get(name)
            context.document.set(path + [{"attributeTypeKey": attribute_key}], name, value)
    if "position" in raw:
        index = params.required("position", int)
        if not 0 <= index < len(context.document.at(path)):
            raise Refusal("position", "outOfRange", f"Position {index} is outside the list")
        inverse["position"] = context.document.move(path, {"attributeTypeKey": attribute_key}, index)
        if keep_order(context.document, path, {"attributeTypeKey": attribute_key}):
            named = {atom("attributeBinding", type_key, attribute_key), atom("objectType", type_key)}
            return restoring(context, {"kind": "setAttributeBinding", **raw}, Applied(raw, {}, named=named))
    if len(inverse) == 3:
        raise Refusal("required", "missingParameter", "Name required, readOnly or position")
    return Applied(raw, inverse, named={atom("attributeBinding", type_key, attribute_key), atom("objectType", type_key)})


# --- structure ---


@kind("setContainment")
def set_containment(context: Context, raw: dict[str, Any]) -> Applied:
    params = Params(raw, ("objectType", "parent"))
    key = params.text("objectType")
    object_type = context.object_type(key)
    if "parent" not in raw:
        raise Refusal("parent", "missingParameter", "'parent' is required (null for the top level)")
    context.unreleased(atom("objectType", key))
    old_relations = list((object_type.get("behavior") or {}).get("parentRelationTypeKeys") or [])
    old_parents = []
    gone = Gone()
    for binding in list(context.document.items("objectTypeRelations")):
        if binding.get("relationTypeKey") in old_relations and binding.get("toObjectTypeKey") == key:
            old_parents.append(binding["fromObjectTypeKey"])
            context.document.remove(["objectTypeRelations"], identity(binding))
    behavior = dict(object_type.get("behavior") or {})
    behavior.pop("parentRelationTypeKeys", None)
    context.document.set(type_path(key), "behavior", behavior or None)
    for relation_key in old_relations:
        _drop_unbound_relation(context, relation_key, gone)
    for parent_key in old_parents:
        for path in _children_panel_paths(context.document, parent_key):
            items = context.document.at(path + ["config", "objectTypeKeys"])
            if key in items:
                context.document.remove(path + ["config", "objectTypeKeys"], key)
    prune(context.document, gone)
    parent = _parent(context, raw.get("parent"), key)
    stored_parent, created = _contain(context, key, parent)
    for parent_key in parent[0] if parent else []:
        place_child(context.document, parent_key, key)
    named = {atom("objectType", key)} | {atom("objectType", p) for p in (parent[0] if parent else [])}
    stored = {**raw, "parent": stored_parent}
    return restoring(context, {"kind": "setContainment", **stored}, Applied(stored, {}, created=created, named=named))


def _children_panel_paths(document: Document, parent_key: str) -> list[Path]:
    paths = []
    for application in document.items("applications"):
        for detail in application.get("details") or []:
            if detail.get("objectTypeKey") != parent_key:
                continue
            for panel in detail.get("panels") or []:
                if panel.get("type") == "children":
                    paths.append(
                        application_path(application["key"])
                        + ["details", {"objectTypeKey": parent_key}, "panels", {"key": panel["key"]}]
                    )
    return paths


@kind("addRelationType")
def add_relation_type(context: Context, raw: dict[str, Any]) -> Applied:
    params = Params(raw, ("key", "reverseKey", "name", "reverseName", "isOriented"))
    name, reverse_name = params.text("name"), params.text("reverseName")
    taken = context.relation_keys()
    key = context.new_key(params, "key", name, taken)
    reverse = params.optional("reverseKey")
    if reverse is None:
        reverse = key_from_label(reverse_name, taken | {key})
    elif reverse in taken | {key}:
        raise Refusal("reverseKey", "keyTaken", f"Key '{reverse}' is already used")
    relation: dict[str, Any] = {"key": key, "reverseKey": reverse, "name": name, "reverseName": reverse_name}
    if "isOriented" in raw:
        relation["isOriented"] = params.optional("isOriented", bool, True)
    context.document.insert(["relationTypes"], relation)
    return Applied(
        {**raw, "key": key, "reverseKey": reverse},
        {"kind": "removeRelationType", "relationType": key},
        created={atom("relationType", key)},
    )


@kind("removeRelationType")
def remove_relation_type(context: Context, raw: dict[str, Any]) -> Applied:
    params = Params(raw, ("relationType",))
    key = params.text("relationType")
    relation = context.relation_type(key)
    if any(b.get("relationTypeKey") == key for b in context.document.items("objectTypeRelations")):
        raise Refusal("relationType", "stillBound", f"Relation type '{key}' is still allowed between types")
    context.unreleased(atom("relationType", key))
    context.document.remove(["relationTypes"], {"key": key})
    prune(context.document, Gone(relation_keys={key, relation.get("reverseKey")}))
    return restoring(context, {"kind": "removeRelationType", **raw}, Applied(raw, {}, named={atom("relationType", key)}))


def _allow(context: Context, relation_key: str, source: str, target: str, cardinality: str, required: bool) -> None:
    binding: dict[str, Any] = {
        "relationTypeKey": relation_key,
        "fromObjectTypeKey": source,
        "toObjectTypeKey": target,
        "cardinality": cardinality,
    }
    if required:
        binding["required"] = True
    context.document.insert(["objectTypeRelations"], binding)
    place_relation(context.document, relation_key, source)


@kind("allowRelation")
def allow_relation(context: Context, raw: dict[str, Any]) -> Applied:
    params = Params(raw, ("relationType", "from", "to", "cardinality", "required", "layout"))
    relation_key, source, target = params.text("relationType"), params.text("from"), params.text("to")
    context.relation_type(relation_key)
    context.object_type(source, "from")
    context.object_type(target, "to")
    if context.document.find(["objectTypeRelations", {"relationTypeKey": relation_key, "fromObjectTypeKey": source, "toObjectTypeKey": target}]):
        raise Refusal("relationType", "alreadyAllowed", f"'{relation_key}' is already allowed from '{source}' to '{target}'")
    cardinality = params.optional("cardinality", str, "many-to-many")
    if cardinality not in CARDINALITIES:
        raise Refusal("cardinality", "invalidValue", f"Unknown cardinality '{cardinality}'")
    required = params.optional("required", bool, False)
    if params.optional("layout", bool, True):
        _allow(context, relation_key, source, target, cardinality, required)
    else:
        binding = {"relationTypeKey": relation_key, "fromObjectTypeKey": source, "toObjectTypeKey": target, "cardinality": cardinality}
        if required:
            binding["required"] = True
        context.document.insert(["objectTypeRelations"], binding)
    return Applied(
        raw,
        {"kind": "disallowRelation", "relationType": relation_key, "from": source, "to": target},
        created={atom("relationBinding", relation_key, source, target)},
        named={atom("relationType", relation_key), atom("objectType", source), atom("objectType", target)},
    )


@kind("disallowRelation")
def disallow_relation(context: Context, raw: dict[str, Any]) -> Applied:
    params = Params(raw, ("relationType", "from", "to"))
    relation_key, source, target = params.text("relationType"), params.text("from"), params.text("to")
    binding = context.relation_binding(relation_key, source, target)
    context.unreleased(atom("relationBinding", relation_key, source, target))
    context.document.remove(["objectTypeRelations"], identity(binding))
    document = context.document
    for type_key, direction in ((source, "outgoing"), (target, "incoming")):
        still = any(
            b.get("relationTypeKey") == relation_key
            and b.get("fromObjectTypeKey" if direction == "outgoing" else "toObjectTypeKey") == type_key
            for b in document.items("objectTypeRelations")
        )
        if still:
            continue
        for application in document.items("applications"):
            for detail in application.get("details") or []:
                if detail.get("objectTypeKey") != type_key:
                    continue
                for panel in detail.get("panels") or []:
                    config = panel.get("config") or {}
                    if panel.get("type") == "relations" and relation_key in (config.get("relationTypeKeys") or []):
                        document.remove(
                            application_path(application["key"])
                            + ["details", {"objectTypeKey": type_key}, "panels", {"key": panel["key"]}, "config", "relationTypeKeys"],
                            relation_key,
                        )
    behavior = (document.at(type_path(target)).get("behavior") or {}) if document.find(type_path(target)) else {}
    if relation_key in (behavior.get("parentRelationTypeKeys") or []) and not any(
        b.get("relationTypeKey") == relation_key and b.get("toObjectTypeKey") == target for b in document.items("objectTypeRelations")
    ):
        document.remove(type_path(target) + ["behavior", "parentRelationTypeKeys"], relation_key)
    unbound = not any(b.get("relationTypeKey") == relation_key for b in document.items("objectTypeRelations"))
    for application in document.items("applications"):
        for view in list(application.get("views") or []):
            config = view.get("config") or {}
            if config.get("relationTypeKey") != relation_key:
                continue
            over_binding = view.get("type") == "mappingGrid" and (
                config.get("fromObjectTypeKey"),
                config.get("toObjectTypeKey"),
            ) == (source, target)
            if over_binding or (view.get("type") == "relationMatrix" and unbound):
                document.remove(application_path(application["key"]) + ["views"], {"key": view["key"]})
    prune(document, Gone())
    return restoring(
        context,
        {"kind": "disallowRelation", **raw},
        Applied(raw, {}, named={atom("relationBinding", relation_key, source, target), atom("relationType", relation_key)}),
    )


@kind("setRelationRule")
def set_relation_rule(context: Context, raw: dict[str, Any]) -> Applied:
    params = Params(raw, ("relationType", "from", "to", "cardinality", "required", "candidates", "uniqueToAncestorTypeKey"))
    relation_key, source, target = params.text("relationType"), params.text("from"), params.text("to")
    binding = context.relation_binding(relation_key, source, target)
    path = ["objectTypeRelations", identity(binding)]
    # Which records may be chosen (0.9 K7) is compatible in a release: installing checks no data, and
    # a relationship made before stays. Every other rule changes what stored data must hold.
    if set(raw) - {"kind", "relationType", "from", "to", "candidates"}:
        context.unreleased(atom("relationBinding", relation_key, source, target))
    inverse: dict[str, Any] = {"kind": "setRelationRule", "relationType": relation_key, "from": source, "to": target}
    if "cardinality" in raw:
        cardinality = params.text("cardinality")
        if cardinality not in CARDINALITIES:
            raise Refusal("cardinality", "invalidValue", f"Unknown cardinality '{cardinality}'")
        inverse["cardinality"] = binding.get("cardinality", "many-to-many")
        context.document.set(path, "cardinality", cardinality)
    if "required" in raw:
        inverse["required"] = binding.get("required")
        context.document.set(path, "required", _flag(raw, "required"))
    if "candidates" in raw:
        inverse["candidates"] = copy.deepcopy(binding.get("candidates"))
        context.document.set(path, "candidates", params.optional("candidates", dict))
    if "uniqueToAncestorTypeKey" in raw:
        features = dict(binding.get("features") or {})
        inverse["uniqueToAncestorTypeKey"] = features.get("uniqueToAncestorTypeKey")
        value = params.optional("uniqueToAncestorTypeKey")
        if value is None:
            features.pop("uniqueToAncestorTypeKey", None)
        else:
            context.object_type(value, "uniqueToAncestorTypeKey")
            features["uniqueToAncestorTypeKey"] = value
        context.document.set(path, "features", features or None)
    if len(inverse) == 4:
        raise Refusal("cardinality", "missingParameter", "Name a rule to set")
    return Applied(raw, inverse, named={atom("relationBinding", relation_key, source, target)})


# --- views and panels (D19) ---


def _target(context: Context, raw: dict[str, Any]) -> tuple[Path, str, str]:
    """A view (``applicationKey``, ``view``), a detail page (``applicationKey``, ``detail``) or a
    panel (with ``panel``): its path, kind and atom."""
    app = raw.get("applicationKey")
    if "view" in raw:
        return _view_path(context, app, raw["view"]), "view", atom("view", app, raw["view"])
    if "panel" in raw:
        return _panel_path(context, app, raw.get("detail"), raw["panel"]), "panel", atom("panel", app, raw.get("detail"), raw["panel"])
    if "detail" in raw:
        return _detail_path(context, app, raw["detail"]), "detail", atom("detail", app, raw["detail"])
    raise Refusal("view", "missingParameter", "Name a view, a detail page or a panel")


_TARGET = ("applicationKey", "view", "detail", "panel")


def _list_path(context: Context, path: Path, target: str, name: Any) -> Path:
    if not isinstance(name, str):
        raise Refusal("list", "invalidValue", "'list' names a list")
    node = context.document.at(path)
    if target == "detail":
        if name != "panels":
            raise Refusal("list", "invalidValue", "A detail page's list is 'panels'")
        return path + ["panels"]
    config = node.get("config") if isinstance(node.get("config"), dict) else None
    if config is not None and isinstance(config.get(name), list):
        return path + ["config", name]
    if config is not None and name in _LIST_DEFAULTS.get(str(node.get("type")), ()):
        return path + ["config", name]
    raise Refusal("list", "unknownElement", f"No list '{name}' here")


# Lists a panel may leave out (their defaults apply) and an insert creates.
_LIST_DEFAULTS = {
    "attributes": ("fields",),
    "children": ("columns",),
    "relations": ("columns", "sortFields"),
    "table": ("columns",),
}


def _item_key(item: Any) -> Any:
    return item.get("key") if isinstance(item, dict) else item


@kind("insertViewItem")
def insert_view_item(context: Context, raw: dict[str, Any]) -> Applied:
    params = Params(raw, (*_TARGET, "list", "item", "position"))
    path, target, element = _target(context, raw)
    list_path = _list_path(context, path, target, raw.get("list"))
    item = raw.get("item")
    if target == "detail":
        if not isinstance(item, dict) or not isinstance(item.get("key"), str):
            raise Refusal("item", "invalidValue", "A panel is an object with a key")
    elif not isinstance(item, str):
        raise Refusal("item", "invalidValue", "An item of this list is a field or key")
    current = context.document.find(list_path) or []
    if any(_item_key(existing) == _item_key(item) for existing in current):
        raise Refusal("item", "alreadyPresent", f"'{_item_key(item)}' is already in the list")
    context.document.insert(list_path, copy.deepcopy(item), _position(params, current))
    if target == "detail":
        keep_order(context.document, list_path, {"key": item["key"]})
    target_fields = {name: raw[name] for name in _TARGET if name in raw}
    return Applied(
        raw,
        {"kind": "removeViewItem", **target_fields, "list": raw["list"], "item": _item_key(item)},
        created={atom("panel", raw["applicationKey"], raw["detail"], item["key"])} if target == "detail" else set(),
        named={element},
    )


@kind("moveViewItem")
def move_view_item(context: Context, raw: dict[str, Any]) -> Applied:
    params = Params(raw, (*_TARGET, "list", "item", "position"))
    path, target, element = _target(context, raw)
    list_path = _list_path(context, path, target, raw.get("list"))
    current = context.document.find(list_path) or []
    item = raw.get("item")
    segment = {"key": item} if target == "detail" else item
    if not any(_item_key(existing) == item for existing in current):
        raise Refusal("item", "unknownElement", f"'{item}' is not in the list")
    index = params.required("position", int)
    if not 0 <= index < len(current):
        raise Refusal("position", "outOfRange", f"Position {index} is outside the list")
    old = context.document.move(list_path, segment, index)
    if target == "detail" and keep_order(context.document, list_path, {"key": item}):
        return restoring(context, {"kind": "moveViewItem", **raw}, Applied(raw, {}, named={element}))
    target_fields = {name: raw[name] for name in _TARGET if name in raw}
    return Applied(raw, {"kind": "moveViewItem", **target_fields, "list": raw["list"], "item": item, "position": old}, named={element})


@kind("removeViewItem")
def remove_view_item(context: Context, raw: dict[str, Any]) -> Applied:
    Params(raw, (*_TARGET, "list", "item"))
    path, target, element = _target(context, raw)
    list_path = _list_path(context, path, target, raw.get("list"))
    current = context.document.find(list_path) or []
    item = raw.get("item")
    position = next((i for i, existing in enumerate(current) if _item_key(existing) == item), None)
    if position is None:
        raise Refusal("item", "unknownElement", f"'{item}' is not in the list")
    removed = context.document.remove(list_path, {"key": item} if target == "detail" else item)
    target_fields = {name: raw[name] for name in _TARGET if name in raw}
    return Applied(
        raw,
        {"kind": "insertViewItem", **target_fields, "list": raw["list"], "item": removed, "position": position},
        named={element} | ({atom("panel", raw["applicationKey"], raw["detail"], item)} if target == "detail" else set()),
    )


_VIEW_TOP = {"name"}
_PANEL_TOP = {"title", "region", "visible", "order"}


@kind("setViewProperty")
def set_view_property(context: Context, raw: dict[str, Any]) -> Applied:
    Params(raw, (*_TARGET, "property", "value"))
    path, target, element = _target(context, raw)
    name = raw.get("property")
    if not isinstance(name, str) or not name:
        raise Refusal("property", "invalidValue", "'property' names a property")
    node = context.document.at(path)
    if target == "detail":
        group, _, member = name.partition(".")
        if group not in ("header", "breadcrumbs") or not member:
            raise Refusal("property", "unknownElement", "A detail page's properties are header.<name> and breadcrumbs.<name>")
        if not isinstance(node.get(group), dict):
            context.document.set(path, group, {})
        owner, field_name = path + [group], member
    elif (target == "view" and name in _VIEW_TOP) or (target == "panel" and name in _PANEL_TOP):
        owner, field_name = path, name
    elif isinstance(node.get("config"), dict) and name not in ("type", "key"):
        owner, field_name = path + ["config"], name
    else:
        raise Refusal("property", "unknownElement", f"No property '{name}' here")
    old = copy.deepcopy(context.document.at(owner).get(field_name))
    context.document.set(owner, field_name, copy.deepcopy(raw.get("value")))
    target_fields = {key: raw[key] for key in _TARGET if key in raw}
    return Applied(raw, {"kind": "setViewProperty", **target_fields, "property": name, "value": old}, named={element})


@kind("addView")
def add_view(context: Context, raw: dict[str, Any]) -> Applied:
    params = Params(raw, ("applicationKey", "view", "position", "default"))
    app = params.text("applicationKey")
    application = context.application(app)
    view = params.required("view", dict)
    views = application.get("views") or []
    taken = {v.get("key") for v in views}
    if view.get("type", "table") == "table" and set(view) <= {"objectTypeKey", "type", "key", "name"}:
        type_key = view.get("objectTypeKey")
        context.object_type(type_key, "view/objectTypeKey")
        generated = table_view(context.document, app, type_key)
        generated["key"] = view.get("key") or generated["key"]
        generated["name"] = view.get("name") or generated["name"]
        view = generated
    else:
        view = copy.deepcopy(view)
    if not isinstance(view.get("key"), str) or view["key"] in taken:
        raise Refusal("view/key", "keyTaken" if view.get("key") in taken else "missingParameter", "A view needs a free key")
    context.document.insert(application_path(app) + ["views"], view, _position(params, views))
    if params.optional("default", bool, False) or not application.get("defaultView"):
        context.document.set(application_path(app), "defaultView", view["key"])
    return Applied(
        {**raw, "view": view},
        {"kind": "removeView", "applicationKey": app, "view": view["key"]},
        created={atom("view", app, view["key"])},
        named={atom("application", app)},
    )


@kind("removeView")
def remove_view(context: Context, raw: dict[str, Any]) -> Applied:
    Params(raw, ("applicationKey", "view"))
    app = raw.get("applicationKey")
    path = _view_path(context, app, raw.get("view"))
    application = context.application(app)
    views = application.get("views") or []
    position = next(i for i, v in enumerate(views) if v.get("key") == raw["view"])
    was_default = application.get("defaultView") == raw["view"]
    removed = context.document.remove(path[:-1], path[-1])
    if was_default:
        remaining = [v.get("key") for v in context.document.at(application_path(app)).get("views") or []]
        context.document.set(application_path(app), "defaultView", remaining[0] if remaining else "")
    return Applied(
        raw,
        {"kind": "addView", "applicationKey": app, "view": removed, "position": position, "default": was_default},
        named={atom("view", app, raw["view"])},
    )


# --- navigation groups ---


@kind("addNavigationGroup")
def add_navigation_group(context: Context, raw: dict[str, Any]) -> Applied:
    params = Params(raw, ("applicationKey", "key", "label", "collapsed", "position", "collections"))
    app = params.text("applicationKey")
    application = context.application(app)
    label = params.text("label")
    groups = ((application.get("navigation") or {}).get("groups")) or []
    key = context.new_key(params, "key", label, {g.get("key") for g in groups})
    collections = params.optional("collections", list, [])
    group = {"key": key, "label": label, "collections": list(collections), "collapsed": params.optional("collapsed", bool, False)}
    if not isinstance(application.get("navigation"), dict):
        context.document.set(application_path(app), "navigation", {"groups": []})
    context.document.insert(application_path(app) + ["navigation", "groups"], group, _position(params, groups))
    return Applied(
        {**raw, "key": key},
        {"kind": "removeNavigationGroup", "applicationKey": app, "group": key},
        created={atom("group", app, key)},
        named={atom("application", app)} | {atom("objectType", c) for c in collections},
    )


@kind("removeNavigationGroup")
def remove_navigation_group(context: Context, raw: dict[str, Any]) -> Applied:
    Params(raw, ("applicationKey", "group"))
    app = raw.get("applicationKey")
    path = _group_path(context, app, raw.get("group"))
    groups = context.document.at(path[:-1])
    position = next(i for i, g in enumerate(groups) if g.get("key") == raw["group"])
    removed = context.document.remove(path[:-1], path[-1])
    if not context.document.at(path[:-1]):
        context.document.set(application_path(app), "navigation", None)
    return Applied(
        raw,
        {
            "kind": "addNavigationGroup",
            "applicationKey": app,
            "key": removed["key"],
            "label": removed.get("label"),
            "collapsed": bool(removed.get("collapsed", False)),
            "collections": list(removed.get("collections") or []),
            "position": position,
        },
        named={atom("group", app, raw["group"])},
    )


@kind("setNavigationGroup")
def set_navigation_group(context: Context, raw: dict[str, Any]) -> Applied:
    params = Params(raw, ("applicationKey", "group", "label", "collapsed", "position"))
    app = raw.get("applicationKey")
    path = _group_path(context, app, raw.get("group"))
    group = context.document.at(path)
    inverse: dict[str, Any] = {"kind": "setNavigationGroup", "applicationKey": app, "group": raw["group"]}
    if "label" in raw:
        inverse["label"] = group.get("label")
        context.document.set(path, "label", params.text("label"))
    if "collapsed" in raw:
        inverse["collapsed"] = bool(group.get("collapsed", False))
        context.document.set(path, "collapsed", params.optional("collapsed", bool, False))
    if "position" in raw:
        groups = context.document.at(path[:-1])
        index = params.required("position", int)
        if not 0 <= index < len(groups):
            raise Refusal("position", "outOfRange", f"Position {index} is outside the list")
        inverse["position"] = context.document.move(path[:-1], path[-1], index)
    if len(inverse) == 3:
        raise Refusal("label", "missingParameter", "Name label, collapsed or position")
    return Applied(raw, inverse, named={atom("group", app, raw["group"])})


@kind("placeCollection")
def place_collection(context: Context, raw: dict[str, Any]) -> Applied:
    params = Params(raw, ("applicationKey", "collection", "group", "position"))
    app = params.text("applicationKey")
    application = context.application(app)
    collection = params.text("collection")
    context.object_type(collection, "collection")
    target = params.optional("group")
    groups = ((application.get("navigation") or {}).get("groups")) or []
    if target is not None and not any(g.get("key") == target for g in groups):
        raise Refusal("group", "unknownElement", f"No navigation group '{target}' in '{app}'")
    old_group, old_position = None, None
    for group in groups:
        members = group.get("collections") or []
        if collection in members:
            old_group, old_position = group["key"], members.index(collection)
            context.document.remove(application_path(app) + ["navigation", "groups", {"key": group["key"]}, "collections"], collection)
    if target is not None:
        members_path = application_path(app) + ["navigation", "groups", {"key": target}, "collections"]
        members = context.document.find(members_path) or []
        context.document.insert(members_path, collection, _position(params, members))
    inverse: dict[str, Any] = {"kind": "placeCollection", "applicationKey": app, "collection": collection, "group": old_group}
    if old_position is not None:
        inverse["position"] = old_position
    named = {atom("application", app), atom("objectType", collection)} | ({atom("group", app, target)} if target else set())
    return Applied(raw, inverse, named=named)


# --- written by the server ---


@kind("replaceModel")
def replace_model(context: Context, raw: dict[str, Any]) -> Applied:
    Params(raw, ("model",))
    model = raw.get("model")
    if not isinstance(model, dict):
        raise Refusal("model", "invalidValue", "'model' is a model document")
    previous = copy.deepcopy(context.data)
    created = _top_level_atoms(model) - _top_level_atoms(previous)
    context.data.clear()
    context.data.update(copy.deepcopy(model))
    return Applied(raw, {"kind": "replaceModel", "model": previous}, created=created, named=_top_level_atoms(previous) - created)


def _top_level_atoms(model: dict[str, Any]) -> set[str]:
    result = set()
    for collection, label in (
        ("applications", "application"),
        ("objectTypes", "objectType"),
        ("attributeTypes", "attributeType"),
        ("relationTypes", "relationType"),
    ):
        for item in model.get(collection) or []:
            if isinstance(item, dict) and isinstance(item.get("key"), str):
                result.add(atom(label, item["key"]))
    return result


@kind("restoreElements")
def restore_elements(context: Context, raw: dict[str, Any]) -> Applied:
    Params(raw, ("undoes", "removes", "changes"))
    context.unreleased(*(raw.get("removes") or ()))
    changes = raw.get("changes")
    undoes = raw.get("undoes")
    if not isinstance(changes, list) or not isinstance(undoes, dict):
        raise Refusal("changes", "invalidValue", "'changes' are the logged changes of an operation")
    try:
        apply_changes(context.document, changes)
    except LookupError as exc:
        raise Refusal("changes", "conflict", f"The document no longer holds what this restores: {exc}") from exc
    return Applied(raw, copy.deepcopy(undoes))


def _flag(raw: dict[str, Any], name: str) -> bool | None:
    """A rule's flag; ``null`` leaves it unwritten (its default, false), as an inverse writes it back."""
    value = raw.get(name)
    if value is not None and not isinstance(value, bool):
        raise Refusal(name, "invalidValue", f"'{name}' is true or false")
    return value


def _position(params: Params, items: list[Any]) -> int | None:
    """D35: the index in the declared list, the end when omitted; refused when out of range."""
    position = params.optional("position", int)
    if position is None:
        return None
    if not 0 <= position <= len(items):
        raise Refusal("position", "outOfRange", f"Position {position} is outside the list")
    return position
