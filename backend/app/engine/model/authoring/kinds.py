"""The model-side operation kinds (0.10 A2, [API.md § Kinds](../../../../docs/API.md)).

Each kind checks its parameters against the document, applies its change through
:class:`~.document.Document`, and returns what it did: its parameters as stored (generated keys
filled in), its inverse, and the elements it created, re-keyed and named (D8). A draft-only kind
asks :meth:`Context.unreleased` before it changes an element, which marks the step as one that needs a
migration when the element is in the draft's base release and data holds it (D17, MG). Elements are
named by key, never by position.

A compound kind (a removal, a split, a merge, a move, a containment change) has the inverse
``restoreElements``: the logged changes that put back exactly what it changed (ADR-041).
"""

import copy
import json
import math
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any

from pydantic import ValidationError

from ....models.schema import ObjectTypeDefinition, TreeViewConfig
from ..compiler import SCHEMA_VERSIONS
from ..validation.application_rules import tree_action_refusal
from . import profile_side
from .cascade import Gone, drop_view_navigation, prune, rename
from .document import (
    MODEL,
    PROFILE,
    PROFILE_IDENTITIES,
    Document,
    Path,
    Refusal,
    apply_changes,
    identity,
)
from .keys import key_from_label
from .layout import (
    add_panel,
    application_path,
    children_panel,
    contained_types,
    detail_page,
    drop_unreachable_ancestor_sorts,
    held_relations,
    keep_order,
    place_attribute,
    place_child,
    place_relation,
    relations_panel,
    table_view,
    type_path,
)
from .references import Slot, known_keys, names_in_slot, slots

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
    "listing": ("applicationKey", "objectType"),
    "consumerApi": ("consumerApi",),
}


def atom(kind: str, *keys: str) -> str:
    return f"{kind}:" + "/".join(keys)


def element_of(value: str) -> dict[str, str]:
    """The element an atom names, as operations name it."""
    kind, _, rest = value.partition(":")
    return dict(zip(ELEMENT_FIELDS[kind], rest.split("/"), strict=True))


@dataclass
class Applied:
    parameters: dict[str, Any]
    inverse: dict[str, Any]
    created: set[str] = field(default_factory=set)
    rekeyed: set[str] = field(default_factory=set)
    named: set[str] = field(default_factory=set)
    # Views and panels the kind took away because they could stand nowhere after it, named for the
    # reader (a move between applications says what it could not carry).
    removed: list[dict[str, str]] = field(default_factory=list)
    # The elements of the base release the step changes that need a migration when the draft is
    # installed (MG): each ``{element, keyChange, impact}``, set by the history from the context's marks.
    migration: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class Sheet:
    """A sheet of the draft's profiled source file: its header row and its columns' headers, and
    ``row``: a row's filled cells as trimmed text by column number (0.10 A8b, D126), read from the
    staged cells when a kind needs it."""

    name: str
    header_row: int | None
    headers: tuple[str, ...]
    row: Callable[[int], dict[int, str]] | None = field(default=None, compare=False)
    # The letters of the columns the file's profile found on the sheet (a column named by its letter,
    # 0.13 AQ); empty when not known.
    letters: frozenset[str] = field(default=frozenset(), compare=False)


class Context:
    def __init__(
        self,
        document: Document,
        released: Callable[[str], bool],
        profile: Document | None = None,
        sheets: dict[str, Sheet] | None = None,
        file_name: str | None = None,
        in_use: Callable[[str], bool] | None = None,
        base: dict[str, Any] | None = None,
        profile_keys: Iterable[str] = (),
    ) -> None:
        self.document = document
        # The keys instance import profiles already hold: a draft's profile starts under a free one
        # (0.17 PL4), so installing it never meets another model's profile.
        self.profile_keys = frozenset(profile_keys)
        # The document of the draft's base release, which a consumer API version is frozen from (DF3).
        self.base = base
        # What the operation being applied changes that needs a migration: ``(atom, key change)``.
        self.marks: list[tuple[str, bool]] = []
        self.released = released
        # Released and held by records, values or relationships (AP-D28); without a count, released.
        self.in_use = in_use or released
        # The draft's import profile (0.10 A5, D75), writing into the model document's log.
        self.profile = profile or Document({}, name=PROFILE, identities=PROFILE_IDENTITIES, log=document.log)
        # The draft's profiled source file, or None (the mapping kinds refuse then).
        self.sheets = sheets
        self.file_name = file_name

    @property
    def documents(self) -> dict[str, Document]:
        return {MODEL: self.document, PROFILE: self.profile}

    @property
    def data(self) -> dict[str, Any]:
        return self.document.data

    def unreleased(self, *atoms: str) -> None:
        """Marks a change to an element data holds as needing a migration, which installing the
        draft states and activation checks again (AP-D28, MG-D1)."""
        for value in atoms:
            if self.in_use(value) and (value, False) not in self.marks:
                self.marks.append((value, False))

    def key_free(self, value: str) -> None:
        """Marks a new key for a released element, held or not, as needing a migration: integrations
        name it by its key (MG-D2)."""
        if self.released(value):
            self.marks.append((value, True))

    def take_marks(self) -> list[tuple[str, bool]]:
        """The marks of the operation applied, which the next one starts again from."""
        marks, self.marks = self.marks, []
        return marks

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


def check_names(raw: dict[str, Any], allowed: tuple[str, ...]) -> None:
    unknown = [name for name in raw if name not in allowed]
    if unknown:
        raise Refusal(unknown[0], "unknownParameter", f"Unknown parameter '{unknown[0]}'")


class Params:
    """An operation's parameters, checked by name and type; anything else is refused."""

    def __init__(self, raw: dict[str, Any], allowed: tuple[str, ...] | None = None) -> None:
        """``allowed``: the names a nested object may carry; an operation's own names are checked by
        :func:`apply_operation` against the ones its kind declares."""
        if allowed is not None:
            check_names(raw, allowed)
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
# The parameter names each kind allows: the one place they are declared, checked before a kind runs
# and described in the OpenAPI document (0.13 AQ).
PARAMETERS: dict[str, tuple[str, ...]] = {}
# Kinds a request may not send: they are written by the server (PATCH, undo).
INTERNAL_KINDS = {"replaceModel", "restoreElements"}


def kind(name: str, *, params: tuple[str, ...]) -> Callable[[KindFunction], KindFunction]:
    """Register an operation kind with the parameter names it allows; its docstring describes it."""

    def register(function: KindFunction) -> KindFunction:
        KINDS[name] = function
        PARAMETERS[name] = params
        return function

    return register


def apply_operation(context: Context, operation: dict[str, Any]) -> Applied:
    name = operation.get("kind")
    if not isinstance(name, str) or name not in KINDS:
        raise Refusal("kind", "unknownKind", f"Unknown operation kind '{name}'")
    parameters = {key: value for key, value in operation.items() if key != "kind"}
    check_names(parameters, PARAMETERS[name])
    return KINDS[name](context, parameters)


def restoring(context: Context, operation: dict[str, Any], applied: Applied) -> Applied:
    """``applied`` with the inverse that puts back what its kind changed. What the change took away
    from the model leaves the draft's profile too, as unmapped entries (D78)."""
    profile_side.prune(context.profile, context.data, operation["kind"])
    applied.inverse = {
        "kind": "restoreElements",
        "undoes": operation,
        # What putting things back takes away: refused once released, as a removal would be.
        "removes": sorted(a for a in applied.created if a.split(":", 1)[0] in _RELEASABLE),
        "changes": context.document.reversal(),
    }
    return applied


_RELEASABLE = {"application", "objectType", "attributeType", "relationType", "attributeBinding", "relationBinding", "listing"}


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


@kind("setLabel", params=("element", "name", "reverseName", "description", "icon", "color", "pluralName", "title", "label"))
def set_label(context: Context, raw: dict[str, Any]) -> Applied:
    """Change the labels of an element named by `element`: the fields that kind of element has (name, reverse name, description, icon, colour, plural name, title or label)."""
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


@kind("setKey", params=("element", "key", "reverseKey"))
def set_key(context: Context, raw: dict[str, Any]) -> Applied:
    """Give an element a new key; references to it are rewritten. Only an element the base release does not hold."""
    element_kind, path, element = element_reference(context, raw.get("element"))
    params = Params(raw)
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
        # Only an element the base release lacks is re-keyed, so a definition naming it is not yet read
        # by any consumer, and the rename rewrites it (D54).
        context.key_free(element)
    inverse: dict[str, Any] = {"kind": "setKey", "key": old}
    if element_kind == "relationType":
        old_reverse = context.document.at(path).get("reverseKey")
        if reverse_new is not None and reverse_new != old_reverse and reverse_new in taken | {new}:
            raise Refusal("reverseKey", "keyTaken", f"Key '{reverse_new}' is already used")
        rename(context.document, "relationKey", old, new)
        profile_side.rename(context.profile, "relationType", old, new)
        if reverse_new is not None and reverse_new != old_reverse:
            rename(context.document, "relationKey", old_reverse, reverse_new)
            context.document.set(["relationTypes", {"key": new}], "reverseKey", reverse_new)
            inverse["reverseKey"] = old_reverse
    elif element_kind in ("panel", "group"):
        context.document.set(path, "key", new)
    else:
        rename(context.document, element_kind, old, new, _rename_scope(element_kind, reference))
        if element_kind in ("application", "objectType", "attributeType"):
            profile_side.rename(context.profile, element_kind, old, new)
    new_reference = dict(reference)
    new_reference[{"application": "applicationKey"}.get(element_kind, element_kind)] = new
    inverse["element"] = new_reference
    new_atom = atom(element_kind, *[new_reference[f] for f in ELEMENT_FIELDS[element_kind]])
    return Applied(raw, inverse, rekeyed={new_atom}, named={element})


@kind("setRelease", params=("key", "name", "version", "schemaVersion"))
def set_release(context: Context, raw: dict[str, Any]) -> Applied:
    """Set the draft's release identity: key, name, version and schema version."""
    params = Params(raw)
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


@kind("addApplication", params=("key", "name", "description", "icon", "color", "position"))
def add_application(context: Context, raw: dict[str, Any]) -> Applied:
    """Add an application, with a key generated from its name when `key` is left out."""
    params = Params(raw)
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


@kind("removeApplication", params=("applicationKey",))
def remove_application(context: Context, raw: dict[str, Any]) -> Applied:
    """Remove an application."""
    params = Params(raw)
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
    containment relation type (a key, or a new one's ``name``, ``reverseName`` and ``key``), and
    ``optional`` when a record may also stand at the top (0.10 A6b, D99)."""
    if raw is None:
        return None
    if not isinstance(raw, dict) or set(raw) - {"objectTypes", "relationType", "optional"}:
        raise Refusal(name, "invalidValue", "'parent' is null or names objectTypes and a relationType")
    if not isinstance(raw.get("optional", False), bool):
        raise Refusal(f"{name}/optional", "invalidValue", "'optional' is true or false")
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


def _contain(
    context: Context, child: str, parent: tuple[list[str], str | dict[str, Any]] | None, optional: bool = False
) -> tuple[Any, set[str]]:
    """Place ``child`` at the top or under its parents, there only unless ``optional``; returns the
    stored parent and created atoms."""
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
    context.document.set(path, "features", {**(object_type.get("features") or {}), "rootCreatable": optional})
    behavior = dict(object_type.get("behavior") or {})
    behavior["parentRelationTypeKeys"] = [relation_key]
    context.document.set(path, "behavior", behavior)
    return {"objectTypes": parents, "relationType": relation, **({"optional": True} if optional else {})}, created


def _optional(raw: Any) -> bool:
    return isinstance(raw, dict) and raw.get("optional") is True


@kind("addObjectType", params=("applicationKey", "key", "name", "pluralName", "parent", "displayAttribute", "description", "icon", "layout"))
def add_object_type(context: Context, raw: dict[str, Any]) -> Applied:
    """Add an object type to an application."""
    params = Params(
        raw,
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
    stored_parent, created = _contain(context, key, parent, _optional(raw.get("parent")))
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
    """Take out a relation type no binding uses any more, released or not, unless data holds it (D31)."""
    document = context.document
    if any(b.get("relationTypeKey") == relation_key for b in document.items("objectTypeRelations")):
        return
    if context.in_use(atom("relationType", relation_key)):
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
    if context.in_use(atom("attributeType", attribute_key)):
        return
    if document.find(["attributeTypes", {"key": attribute_key}]) is not None:
        document.remove(["attributeTypes"], {"key": attribute_key})
        gone.attribute_types.add(attribute_key)


@kind("removeObjectType", params=("objectType",))
def remove_object_type(context: Context, raw: dict[str, Any]) -> Applied:
    """Remove an object type."""
    params = Params(raw)
    key = params.text("objectType")
    context.object_type(key)
    context.unreleased(atom("objectType", key))
    gone = Gone()
    for app in context.applications_of(key):
        context.document.remove(application_path(app) + ["objectTypeKeys"], key)
    _remove_type(context, key, gone)
    prune(context.document, gone)
    return restoring(context, {"kind": "removeObjectType", **raw}, Applied(raw, {}, named={atom("objectType", key)}))


@kind("splitObjectType", params=("objectType", "key", "name", "pluralName", "attributes", "relationType", "cardinality"))
def split_object_type(context: Context, raw: dict[str, Any]) -> Applied:
    """Split an object type: some of its attributes move to a new type."""
    params = Params(raw)
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
    profile_side.split_columns(
        context.profile, profile_side.facts(context.data), source, new_key, apps[0], moved, relation_key
    )
    stored = {**raw, "key": new_key, "relationType": relation_key if isinstance(relation, str) else {**relation, "key": relation_key}}
    applied = Applied(
        stored,
        {},
        created=added.created | created | {atom("relationBinding", relation_key, source, new_key)},
        named={atom("objectType", source)} | {atom("attributeType", a) for a in moved},
    )
    return restoring(context, {"kind": "splitObjectType", **stored}, applied)


@kind("mergeObjectTypes", params=("into", "from"))
def merge_object_types(context: Context, raw: dict[str, Any]) -> Applied:
    """Merge one object type into another."""
    params = Params(raw)
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
    dropped: set[str] = set()
    for binding in list(document.items("objectTypeRelations")):
        ends = (binding.get("fromObjectTypeKey"), binding.get("toObjectTypeKey"))
        if source not in ends:
            continue
        if set(ends) == {into, source} and _is_containment(context, binding.get("relationTypeKey")):
            # The two types are one now: a containment between them would make it contain itself.
            document.remove(["objectTypeRelations"], identity(binding))
            dropped.add(binding["relationTypeKey"])
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
    parents = [r for r in parents if r not in dropped or _binds_to(document, r, into)]
    if parents:
        document.set(type_path(into), "behavior", {**(target.get("behavior") or {}), "parentRelationTypeKeys": parents})
    elif (target.get("behavior") or {}).get("parentRelationTypeKeys"):
        # Its only parent was the type merged into it: it stands at the top now.
        behavior = {k: v for k, v in (target.get("behavior") or {}).items() if k != "parentRelationTypeKeys"}
        document.set(type_path(into), "behavior", behavior or None)
        document.set(type_path(into), "features", {**(target.get("features") or {}), "rootCreatable": True})
    _merge_consumer_references(document, into, source)
    document.remove(["objectTypes"], {"key": source})
    gone = Gone(types={source})
    for relation_key in sorted(dropped):
        _drop_unbound_relation(context, relation_key, gone)
    prune(document, gone)
    profile_side.rename(context.profile, "objectType", source, into)
    return restoring(
        context,
        {"kind": "mergeObjectTypes", **raw},
        Applied(raw, {}, named={atom("objectType", into), atom("objectType", source)}),
    )


def _is_containment(context: Context, relation_key: Any) -> bool:
    relation = context.document.find(["relationTypes", {"key": relation_key}])
    return bool(relation and (relation.get("features") or {}).get("parentOf"))


def _binds_to(document: Document, relation_key: str, type_key: str) -> bool:
    return any(
        b.get("relationTypeKey") == relation_key and b.get("toObjectTypeKey") == type_key
        for b in document.items("objectTypeRelations")
    )


def _merge_consumer_references(document: Document, into: str, source: str) -> None:
    """A consumer API naming the merged-away type names the one it was merged into (as ``setKey``
    rewrites a key); one exposing both keeps the survivor's entry and public name."""
    for definition in list(document.items("consumerApis")):
        path = ["consumerApis", identity(definition)]
        exposes = definition.get("exposes") or []
        if into in exposes and source in exposes:
            document.remove(path + ["exposes"], source)
            if source in (definition.get("publicNames") or {}):
                document.set(path + ["publicNames"], source, None)
    rename(document, "objectType", source, into, within=lambda slot: slot.path[:1] == ["consumerApis"])


@kind("convertAttributeToListType", params=("objectType", "attributeType", "key", "name", "pluralName", "relationType"))
def convert_attribute_to_list_type(context: Context, raw: dict[str, Any]) -> Applied:
    """Turn an attribute of an object type into a list type, read as a lookup by name."""
    params = Params(raw)
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
    profile_side.list_lookup(context.profile, owner, attribute_key, new_key, relation_key)
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


@kind("addAttributeType", params=("key", "name", "valueType", "features", "validation", "description"))
def add_attribute_type(context: Context, raw: dict[str, Any]) -> Applied:
    """Add a global attribute type."""
    params = Params(raw)
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


@kind("removeAttributeType", params=("attributeType",))
def remove_attribute_type(context: Context, raw: dict[str, Any]) -> Applied:
    """Remove a global attribute type."""
    params = Params(raw)
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


@kind("setAttributeTypeFeatures", params=("attributeType", "features"))
def set_attribute_type_features(context: Context, raw: dict[str, Any]) -> Applied:
    """Replace the features of an attribute type."""
    params = Params(raw)
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


@kind("setValueType", params=("attributeType", "valueType", "validation"))
def set_value_type(context: Context, raw: dict[str, Any]) -> Applied:
    """Change an attribute type's value type and its validation."""
    params = Params(raw)
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


@kind("attachAttribute", params=("objectType", "attributeType", "required", "readOnly", "position", "layout"))
def attach_attribute(context: Context, raw: dict[str, Any]) -> Applied:
    """Bind an attribute type to an object type."""
    params = Params(raw)
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


@kind("detachAttribute", params=("objectType", "attributeType"))
def detach_attribute(context: Context, raw: dict[str, Any]) -> Applied:
    """Remove an attribute type's binding from an object type."""
    params = Params(raw)
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


@kind("moveAttribute", params=("attributeType", "from", "to", "layout"))
def move_attribute(context: Context, raw: dict[str, Any]) -> Applied:
    """Move an attribute binding from one object type to another."""
    params = Params(raw)
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
    profile_side.move_columns(context.profile, attribute_key, source, target)
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


@kind(
    "setAttributeBinding",
    params=("objectType", "attributeType", "required", "readOnly", "position", "ui"),
)
def set_attribute_binding(context: Context, raw: dict[str, Any]) -> Applied:
    """Change the settings of an attribute binding on an object type."""
    params = Params(raw)
    type_key, attribute_key = params.text("objectType"), params.text("attributeType")
    binding = context.binding(type_key, attribute_key)
    path = type_path(type_key) + ["attributes"]
    inverse: dict[str, Any] = {
        "kind": "setAttributeBinding",
        "objectType": type_key,
        "attributeType": attribute_key,
    }
    if "ui" in raw:
        _set_ui(context, path + [{"attributeTypeKey": attribute_key}], params.required("ui", dict))
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
            named = {
                atom("attributeBinding", type_key, attribute_key),
                atom("objectType", type_key),
            }
            return restoring(
                context, {"kind": "setAttributeBinding", **raw}, Applied(raw, {}, named=named)
            )
    if len(inverse) == 3 and "ui" not in raw:
        raise Refusal("required", "missingParameter", "Name required, readOnly, position or ui")
    if "ui" in raw:
        named = {atom("attributeBinding", type_key, attribute_key), atom("objectType", type_key)}
        return restoring(
            context, {"kind": "setAttributeBinding", **raw}, Applied(raw, {}, named=named)
        )
    return Applied(
        raw,
        inverse,
        named={atom("attributeBinding", type_key, attribute_key), atom("objectType", type_key)},
    )


# --- properties the editor sets (0.13 ED) ---

_UI_HINTS = ("hidden", "helpText")


def _set_ui(context: Context, path: Path, changes: dict[str, Any]) -> None:
    """Sets the display hints (``hidden``, ``helpText``) in the ``ui`` of the node at ``path``; a
    ``null`` hint, ``false`` for ``hidden`` or empty help text takes it away."""
    unknown = [name for name in changes if name not in _UI_HINTS]
    if unknown:
        raise Refusal(
            f"ui/{unknown[0]}",
            "unknownParameter",
            f"Unknown display hint '{unknown[0]}'; use hidden or helpText",
        )
    ui = dict(context.document.at(path).get("ui") or {})
    for name, value in changes.items():
        if name == "hidden" and value is not None and not isinstance(value, bool):
            raise Refusal("ui/hidden", "invalidValue", "'hidden' is true or false")
        if name == "helpText" and value is not None and not isinstance(value, str):
            raise Refusal("ui/helpText", "invalidValue", "'helpText' is text")
        if value in (None, False, ""):
            ui.pop(name, None)
        else:
            ui[name] = value
    context.document.set(path, "ui", ui or None)


def _set_member(context: Context, path: Path, container: str, member: str, value: Any) -> None:
    """Sets ``member`` of the object ``container`` of the node at ``path``; an emptied container goes."""
    current = dict(context.document.at(path).get(container) or {})
    if value is None:
        current.pop(member, None)
    else:
        current[member] = value
    context.document.set(path, container, current or None)


def _bound_attribute_keys(context: Context, type_key: str, raw: Any, name: str) -> list[str]:
    if raw is None:
        return []
    if not isinstance(raw, list) or not all(isinstance(key, str) for key in raw):
        raise Refusal(name, "invalidValue", f"'{name}' is a list of attribute type keys")
    if len(raw) != len(set(raw)):
        raise Refusal(name, "invalidValue", f"'{name}' names an attribute type twice")
    for key in raw:
        context.binding(type_key, key, name)
    return list(raw)


_OBJECT_TYPE_PROPERTIES = (
    "displayAttributeTypeKey",
    "effectivePeriod",
    "atLeastOneOf",
    "parentRelationTypeKeys",
)


@kind("setObjectTypeProperty", params=("objectType", "property", "value"))
def set_object_type_property(context: Context, raw: dict[str, Any]) -> Applied:
    """A type's display attribute, effective period, the attributes of which one must be filled
    (``validation.atLeastOneOf``) and its parent relationships (``behavior.parentRelationTypeKeys``).
    ``null`` takes the setting away. Stored data meeting a tighter ``atLeastOneOf`` is checked when
    the release is installed (compatibility)."""
    params = Params(raw)
    type_key, name = params.text("objectType"), params.text("property")
    object_type = context.object_type(type_key)
    if name not in _OBJECT_TYPE_PROPERTIES:
        raise Refusal(
            "property",
            "unknownElement",
            f"No type property '{name}'; use one of {list(_OBJECT_TYPE_PROPERTIES)}",
        )
    value = raw.get("value")
    path = type_path(type_key)
    if name == "displayAttributeTypeKey":
        if value is not None:
            if not isinstance(value, str):
                raise Refusal("value", "invalidValue", "'value' is an attribute type key")
            context.binding(type_key, value, "value")
        context.document.set(path, name, value)
    elif name == "effectivePeriod":
        if value is not None:
            if not isinstance(value, dict) or set(value) != {
                "startAttributeTypeKey",
                "endAttributeTypeKey",
            }:
                raise Refusal(
                    "value",
                    "invalidValue",
                    "An effective period names startAttributeTypeKey and endAttributeTypeKey",
                )
            for role in ("startAttributeTypeKey", "endAttributeTypeKey"):
                key = value[role]
                context.binding(type_key, key, f"value/{role}")
                if context.attribute_type(key, f"value/{role}").get("valueType") != "date":
                    raise Refusal(
                        f"value/{role}", "invalidValue", f"'{key}' is not a date attribute"
                    )
            if value["startAttributeTypeKey"] == value["endAttributeTypeKey"]:
                raise Refusal(
                    "value/endAttributeTypeKey",
                    "invalidValue",
                    "The start and the end are two different attributes",
                )
            value = dict(value)
        context.document.set(path, name, value)
    elif name == "atLeastOneOf":
        keys = _bound_attribute_keys(context, type_key, value, "value")
        value = keys or None
        _set_member(context, path, "validation", name, value)
    else:
        if value is None:
            keys = []
        elif (
            isinstance(value, list)
            and all(isinstance(key, str) for key in value)
            and len(value) == len(set(value))
        ):
            keys = list(value)
        else:
            raise Refusal("value", "invalidValue", "'value' is a list of relation type keys")
        for key in keys:
            if key not in context.relation_keys():
                raise Refusal("value", "unknownElement", f"No relation type '{key}'")
            if not any(
                (b.get("relationTypeKey"), b.get("toObjectTypeKey")) == (key, type_key)
                for b in context.document.items("objectTypeRelations")
            ):
                raise Refusal(
                    "value", "invalidValue", f"No relationship '{key}' is allowed to '{type_key}'"
                )
        if keys != list((object_type.get("behavior") or {}).get(name) or []):
            context.unreleased(atom("objectType", type_key))
        value = keys or None
        _set_member(context, path, "behavior", name, value)
    # The stored prior state is the inverse: a container (``validation``, ``behavior``) emptied or
    # created by the change comes back as it was.
    return restoring(
        context,
        {"kind": "setObjectTypeProperty", **raw},
        Applied({**raw, "value": value}, {}, named={atom("objectType", type_key)}),
    )


_ATTRIBUTE_TYPE_PROPERTIES = ("minimum", "maximum", "hidden", "helpText")


@kind("setAttributeTypeProperty", params=("attributeType", "property", "value"))
def set_attribute_type_property(context: Context, raw: dict[str, Any]) -> Applied:
    """An attribute type's ``validation`` bounds (``minimum``, ``maximum``: numbers, on an integer or
    decimal type) and display hints (``hidden``, ``helpText``). ``null`` takes the setting away.
    Stored values outside a new bound are found when the release is installed (compatibility)."""
    params = Params(raw)
    key, name = params.text("attributeType"), params.text("property")
    attribute = context.attribute_type(key)
    if name not in _ATTRIBUTE_TYPE_PROPERTIES:
        raise Refusal(
            "property",
            "unknownElement",
            f"No attribute property '{name}'; use one of {list(_ATTRIBUTE_TYPE_PROPERTIES)}",
        )
    value = raw.get("value")
    path = ["attributeTypes", {"key": key}]
    if name in ("minimum", "maximum"):
        if attribute.get("valueType") not in ("integer", "decimal"):
            raise Refusal(
                "property",
                "invalidValue",
                f"'{key}' is not a number type; a minimum and maximum apply to integer and decimal types",
            )
        if value is not None:
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
            ):
                raise Refusal("value", "invalidValue", f"'{name}' is a number")
            other = (attribute.get("validation") or {}).get(
                "maximum" if name == "minimum" else "minimum"
            )
            if other is not None and (value > other if name == "minimum" else value < other):
                raise Refusal("value", "invalidValue", "The minimum must not exceed the maximum")
        _set_member(context, path, "validation", name, value)
    else:
        _set_ui(context, path, {name: value})
    return restoring(
        context,
        {"kind": "setAttributeTypeProperty", **raw},
        Applied(raw, {}, named={atom("attributeType", key)}),
    )


@kind("setRelationTypeProperty", params=("relationType", "property", "value"))
def set_relation_type_property(context: Context, raw: dict[str, Any]) -> Applied:
    """Whether a relation type is oriented: deleting a record then removes the relationships it points
    to. It changes what a later deletion does, not what is stored."""
    params = Params(raw)
    key, name = params.text("relationType"), params.text("property")
    relation = context.relation_type(key)
    if name != "isOriented":
        raise Refusal(
            "property", "unknownElement", f"No relation type property '{name}'; use isOriented"
        )
    # ``null`` is the default (oriented), left unwritten, as an inverse writes it back.
    if "value" not in raw:
        raise Refusal("value", "missingParameter", "'value' is required")
    value = params.optional("value", bool)
    old = relation.get("isOriented")
    context.document.set(["relationTypes", {"key": key}], "isOriented", value)
    return Applied(
        raw,
        {"kind": "setRelationTypeProperty", "relationType": key, "property": name, "value": old},
        named={atom("relationType", key)},
    )


@kind("setApplicationProperty", params=("applicationKey", "property", "value"))
def set_application_property(context: Context, raw: dict[str, Any]) -> Applied:
    """Set an application's default view (`property` is `defaultView`); its colour is set with `setLabel`."""
    params = Params(raw)
    app, name = params.text("applicationKey"), params.text("property")
    application = context.application(app)
    if name != "defaultView":
        raise Refusal(
            "property", "unknownElement", f"No application property '{name}'; use defaultView"
        )
    value = params.text("value")
    if value not in {v.get("key") for v in application.get("views") or []}:
        raise Refusal("value", "unknownElement", f"Application '{app}' has no view '{value}'")
    old = application.get("defaultView")
    context.document.set(application_path(app), "defaultView", value)
    return Applied(
        raw,
        {"kind": "setApplicationProperty", "applicationKey": app, "property": name, "value": old},
        named={atom("application", app)},
    )


# --- structure ---


@kind("setContainment", params=("objectType", "parent", "application", "fromApplication"))
def set_containment(context: Context, raw: dict[str, Any]) -> Applied:
    """Where a type stands: its parent (``parent``, null for the top level) and, with
    ``application``, the application it stands in. The type and every type under it in the
    application it leaves (``fromApplication``, needed only when it is in several) move together
    with their views and detail pages; relations are the model's and stay as they are."""
    params = Params(raw)
    key = params.text("objectType")
    context.object_type(key)
    target = params.optional("application")
    if "parent" not in raw and target is None:
        raise Refusal("parent", "missingParameter", "'parent' is required (null for the top level), or name the 'application'")
    if "parent" in raw:
        context.unreleased(atom("objectType", key))
    named = {atom("objectType", key)}
    before = _layout_items(context.document)
    if target is not None:
        moved = _move_to_application(context, key, target, params.optional("fromApplication"))
        named |= moved
        # Its records change application with it: a migration moves them (MG).
        context.unreleased(*(item for item in moved if item.startswith("objectType:")))
    stored, created = dict(raw), set()
    if "parent" in raw:
        stored_parent, created, parents = _set_parent(context, key, raw.get("parent"))
        stored["parent"] = stored_parent
        named |= {atom("objectType", p) for p in parents}
    drop_unreachable_ancestor_sorts(context.document)
    applied = Applied(stored, {}, created=created, named=named, removed=_removed(before, _layout_items(context.document)))
    return restoring(context, {"kind": "setContainment", **stored}, applied)


def _layout_items(document: Document) -> dict[tuple[str, ...], dict[str, Any]]:
    """Every view and panel by where it stands: ``(view, app, key)``, ``(panel, app, type, key)``."""
    items: dict[tuple[str, ...], dict[str, Any]] = {}
    for application in document.items("applications"):
        for view in application.get("views") or []:
            items[("view", application["key"], view["key"])] = view
        for detail in application.get("details") or []:
            for panel in detail.get("panels") or []:
                items[("panel", application["key"], detail["objectTypeKey"], panel["key"])] = panel
    return items


def _removed(before: dict[tuple[str, ...], dict[str, Any]], after: dict[tuple[str, ...], dict[str, Any]]) -> list[dict[str, str]]:
    """What ``before`` held that ``after`` holds nowhere: not where it stood, not moved (a view by
    its content under any key, a panel by its page's type and key in any application)."""
    views = {_without_key(item) for where, item in after.items() if where[0] == "view"}
    panels = {(where[2], where[3]) for where in after if where[0] == "panel"}
    removed = []
    for where, item in before.items():
        if where in after:
            continue
        if where[0] == "view" and _without_key(item) not in views:
            removed.append({"kind": "view", "applicationKey": where[1], "view": where[2], "name": str(item.get("name") or where[2])})
        elif where[0] == "panel" and (where[2], where[3]) not in panels:
            removed.append(
                {"kind": "panel", "applicationKey": where[1], "detail": where[2], "panel": where[3], "name": str(item.get("title") or where[3])}
            )
    return removed


def _without_key(view: dict[str, Any]) -> str:
    return json.dumps({**view, "key": ""}, sort_keys=True)


def _set_parent(context: Context, key: str, raw_parent: Any) -> tuple[Any, set[str], list[str]]:
    object_type = context.object_type(key)
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
    parent = _parent(context, raw_parent, key)
    stored_parent, created = _contain(context, key, parent, _optional(raw_parent))
    parents = list(parent[0]) if parent else []
    for parent_key in parents:
        place_child(context.document, parent_key, key)
    _follow_trees(context.document, key, parents)
    profile_side.follow_parent(context.profile, key, parents)
    return stored_parent, created, parents


def _follow_trees(document: Document, key: str, parents: list[str]) -> None:
    """Every tree showing ``key`` stays whole once its place changed. As a top no longer allowed, it
    makes way for its new parents where the tree's application lists them; a node no longer reached
    from the top stands at the top when it may, and otherwise leaves the tree. A tree left with no
    top goes."""
    emptied: list[Path] = []
    for application in document.items("applications"):
        members = application.get("objectTypeKeys") or []
        for view in application.get("views") or []:
            config = view.get("config") or {}
            if view.get("type") != "tree" or key not in (config.get("objectTypeKeys") or []):
                continue
            path = application_path(application["key"]) + ["views", {"key": view["key"]}, "config"]
            roots = config.get("rootObjectTypeKeys") or []
            if key in roots and not _root_creatable(document, key):
                position = roots.index(key)
                document.remove(path + ["rootObjectTypeKeys"], key)
                tops = _tops_above(document, parents, members)
                if tops:
                    for offset, parent_key in enumerate(tops):
                        if parent_key not in document.at(path).get("objectTypeKeys"):
                            document.insert(path + ["objectTypeKeys"], parent_key, offset)
                        if parent_key not in document.at(path).get("rootObjectTypeKeys"):
                            document.insert(path + ["rootObjectTypeKeys"], parent_key, position + offset)
                    _fields_every_node_has(document, path, tops)
            if not _repair_tree(document, path):
                emptied.append(path[:-1])
    if emptied:
        prune(document, Gone(), within=lambda path: path in emptied)


def _repair_tree(document: Document, path: Path) -> bool:
    """The tree whose config is at ``path`` made whole again after a change to its types: a node no
    longer reached stands at the top when it may and otherwise leaves, and an action it can no longer
    offer goes, as the validator words it. False when no top is left."""
    for node in _unreached(document, path):
        if _root_creatable(document, node):
            document.insert(path + ["rootObjectTypeKeys"], node)
    for node in _unreached(document, path):
        document.remove(path + ["objectTypeKeys"], node)
    config = document.at(path)
    for node in list(config.get("childSort") or {}):
        if node not in (config.get("objectTypeKeys") or []):
            document.set(path + ["childSort"], node, None)
    if not config.get("rootObjectTypeKeys"):
        return False
    try:
        tree = TreeViewConfig.model_validate(config)
        nodes = [ObjectTypeDefinition.model_validate(document.at(type_path(k))) for k in tree.objectTypeKeys]
    except ValidationError:
        return True  # A tree the draft holds invalid anyway: its issue says why.
    containers = {
        key: {other for other in tree.objectTypeKeys if key in contained_types(document, other)}
        for key in tree.objectTypeKeys
    }
    for action in list(tree.actions):
        if tree_action_refusal(action, tree, nodes, containers):
            document.remove(path + ["actions"], action)
    return True


def _tops_above(document: Document, parents: list[str], members: list[str]) -> list[str]:
    """The types a tree grows up to above ``parents``: each parent that may stand at the top, else
    its own parents, as far as the application lists them; none when the way up leaves it."""
    tops: list[str] = []
    pending, seen = list(parents), set()
    while pending:
        current = pending.pop(0)
        if current in seen:
            continue
        seen.add(current)
        if current not in members:
            return []
        if _root_creatable(document, current):
            tops.append(current)
            continue
        above = [t["key"] for t in document.items("objectTypes") if current in contained_types(document, t["key"])]
        if not above:
            return []
        pending.extend(above)
    return tops


def _root_creatable(document: Document, key: str) -> bool:
    return bool((document.at(type_path(key)).get("features") or {}).get("rootCreatable"))


def _unreached(document: Document, path: Path) -> list[str]:
    """A tree's node types not reached from its top through the containers it shows, in its order."""
    config = document.at(path)
    nodes = list(config.get("objectTypeKeys") or [])
    reached = set(config.get("rootObjectTypeKeys") or [])
    grown = True
    while grown:
        grown = False
        for node in nodes:
            if node not in reached and any(node in contained_types(document, r) for r in reached):
                reached.add(node)
                grown = True
    return [node for node in nodes if node not in reached]


def _fields_every_node_has(document: Document, path: Path, added: list[str]) -> None:
    """A tree's label, secondary and availability fields name an attribute every node type binds:
    one the added types lack falls back, the label to ``name`` and the others to none."""
    attribute_keys = {a.get("key") for a in document.items("attributeTypes")}
    config = document.at(path)
    for name in ("labelField", "secondaryField", "availabilityField"):
        value = config.get(name)
        if value not in attribute_keys:
            continue
        if all(any(b.get("attributeTypeKey") == value for b in document.at(type_path(t)).get("attributes") or []) for t in added):
            continue
        document.set(path, name, "name" if name == "labelField" else None)
        if name == "availabilityField" and "setAvailability" in (config.get("actions") or []):
            document.remove(path + ["actions"], "setAvailability")


def _move_to_application(context: Context, key: str, target: Any, source: Any) -> set[str]:
    """``key`` and the types under it in ``source`` (the one application listing it, unless named)
    move to ``target``: listed there and no longer in ``source``, with the views and detail pages
    ``source`` keeps for them alone. A type ``target`` already lists keeps its own; one arriving with
    no view gets a table view and a detail page, as a new type does."""
    document = context.document
    context.application(target, "application")
    listed = context.applications_of(key)
    if source is None:
        others = [app for app in listed if app != target]
        if len(others) > 1:
            raise Refusal(
                "fromApplication", "missingParameter", f"'{key}' is in {', '.join(others)}: name the one it leaves"
            )
        if not others and key in listed:
            raise Refusal("application", "invalidValue", f"'{key}' is already in '{target}'")
        source = others[0] if others else None
    else:
        context.application(source, "fromApplication")
        if source == target:
            raise Refusal("fromApplication", "invalidValue", "'fromApplication' and 'application' are the same")
        if source not in listed:
            raise Refusal("fromApplication", "invalidValue", f"'{key}' is not in '{source}'")
    target_path = application_path(target)
    members = list(document.at(application_path(source)).get("objectTypeKeys") or []) if source else [key]
    branch = [key]
    for type_key in branch:
        branch.extend(c for c in contained_types(document, type_key) if c in members and c not in branch)
    before = set(document.at(target_path).get("objectTypeKeys") or [])
    arriving = [t for t in branch if t not in before]
    for type_key in branch:
        if source:
            document.remove(application_path(source) + ["objectTypeKeys"], type_key)
        if type_key in arriving:
            document.insert(target_path + ["objectTypeKeys"], type_key)
    if source:
        _carry(context, source, target, set(branch), set(arriving))
    for type_key in arriving:
        _lay_out(document, target, type_key)
    profile_side.follow_application(context.profile, branch, source, target)
    return {atom("application", target)} | ({atom("application", source)} if source else set()) | {
        atom("objectType", t) for t in branch
    }


def _carry(context: Context, source: str, target: str, branch: set[str], arriving: set[str]) -> None:
    """``source``'s views of the branch's types (a view is of the type it lists, as the sidebar
    groups it) and its detail pages of them go to ``target``, for a type ``target`` already lists
    they go. There a carried view keeps what may name another application (a relation or ancestor
    column) and loses the types its application must list but ``target`` does not: a tree its other
    nodes, a matrix whose columns or cells stay behind goes. What else in ``source`` names the branch
    leaves it, as a removal's references do."""
    document = context.document
    source_path, target_path = application_path(source), application_path(target)
    carried: list[Path] = []
    shown = _types_with_views(document, source)
    after = set(document.at(target_path).get("objectTypeKeys") or [])
    for view in list(document.at(source_path).get("views") or []):
        needs = _members_needed(document, source_path + ["views", {"key": view["key"]}])
        # A view of a moving type goes; so does one of another type that needs a moving one, when it
        # can stand in the target. Nothing that can stand there is left out (a key taken is renamed).
        if _listed_type(view) not in branch and not (needs & branch and needs <= after):
            continue
        moved = copy.deepcopy(document.remove(source_path + ["views"], {"key": view["key"]}))
        if needs <= after:
            taken = {v.get("key") for v in document.at(target_path).get("views") or []}
            if moved["key"] in taken:
                moved["key"] = key_from_label(moved["key"], taken)
            document.insert(target_path + ["views"], moved)
            carried.append(target_path + ["views", {"key": moved["key"]}])
    for detail in list(document.at(source_path).get("details") or []):
        type_key = detail.get("objectTypeKey")
        if type_key not in branch:
            continue
        moved = copy.deepcopy(document.remove(source_path + ["details"], {"objectTypeKey": type_key}))
        page = next((d for d in document.at(target_path).get("details") or [] if d.get("objectTypeKey") == type_key), None)
        if page is None:
            document.insert(target_path + ["details"], moved)
        else:
            # The target's page of a type it already lists takes the panels it lacks.
            page_path = target_path + ["details", {"objectTypeKey": type_key}]
            for panel in moved.get("panels") or []:
                if not any(p.get("key") == panel.get("key") for p in page.get("panels") or []):
                    document.insert(page_path + ["panels"], panel)
                    carried.append(page_path + ["panels", {"key": panel["key"]}])
            continue
        carried.append(target_path + ["details", {"objectTypeKey": type_key}])
    # What stays keeps its columns: a relation panel of a staying type may show the branch's fields.
    prune(document, Gone(types=set(branch)), within=lambda path: path[:2] == source_path, which=_membership_slot)
    staying = set(document.at(source_path).get("objectTypeKeys") or [])
    for type_key in (shown & staying) - _types_with_views(document, source):
        # A type staying behind keeps a list of its own when its last view went with the branch.
        _lay_out(document, source, type_key)
    emptied = [
        source_path + ["views", {"key": view["key"]}]
        for view in document.at(source_path).get("views") or []
        if view.get("type") == "tree" and not _repair_tree(document, source_path + ["views", {"key": view["key"]}, "config"])
    ]
    if emptied:
        prune(document, Gone(), within=lambda path: path in emptied)
    outside = context.keys("objectTypes") - set(document.at(target_path).get("objectTypeKeys") or [])
    if carried and outside:
        prune(
            document,
            Gone(types=outside),
            within=lambda path: any(path[: len(c)] == c for c in carried),
            which=_membership_slot,
        )
    gone_trees = [
        path
        for path in carried
        if document.find(path) is not None
        and document.at(path).get("type") == "tree"
        and not _repair_tree(document, path + ["config"])
    ]
    if gone_trees:
        prune(document, Gone(), within=lambda path: path in gone_trees)
    if not document.at(target_path).get("defaultView") and document.at(target_path).get("views"):
        document.set(target_path, "defaultView", document.at(target_path)["views"][0]["key"])


# The members naming a type its application must list, as the validator checks them
# (application_rules, detail_view_rules: a table's type, a tree's, a matrix's, a page's and its
# children and table panels', navigation entries). A mapping grid's ends, a relation or ancestor
# column and a relation panel may name another application's types.
_MEMBERSHIP_FIELDS = frozenset(
    {"objectTypeKey", "rootObjectTypeKeys", "objectTypeKeys", "rowObjectTypeKey", "columnObjectTypeKey", "cellObjectTypeKey", "collections"}
)


def _members_needed(document: Document, prefix: Path) -> set[str]:
    """The types the element at ``prefix`` needs its application to list."""
    data = document.data
    known = known_keys(data)
    return {
        key
        for slot in slots(data)
        if slot.path[: len(prefix)] == prefix and _membership_slot(slot)
        for kind_name, key in names_in_slot(data, slot, known)
        if kind_name == "objectType"
    }


def _membership_slot(slot: Slot) -> bool:
    return slot.kind == "objectTypeMapKey" or (slot.kind == "objectType" and slot.field in _MEMBERSHIP_FIELDS)


def _listed_type(view: dict[str, Any]) -> str | None:
    """The type a view lists, as ``collection_keys`` reads it from a valid application."""
    config = view.get("config") or {}
    if view.get("type") == "table":
        return view.get("objectTypeKey")
    if view.get("type") == "relationMatrix":
        return config.get("rowObjectTypeKey")
    if view.get("type") == "tree":
        return next(iter(config.get("rootObjectTypeKeys") or []), None)
    if view.get("type") == "relationTable":
        return config.get("fromObjectTypeKey")
    return config.get("fromObjectTypeKey") if config.get("direction") == "outgoing" else config.get("toObjectTypeKey")


def _types_with_views(document: Document, app: str) -> set[str]:
    path = application_path(app)
    return set().union(*(_types_named(document, path + ["views", {"key": v["key"]}]) for v in document.at(path).get("views") or []))


def _types_named(document: Document, prefix: Path) -> set[str]:
    data = document.data
    known = known_keys(data)
    return {
        key
        for slot in slots(data)
        if slot.path[: len(prefix)] == prefix
        for kind_name, key in names_in_slot(data, slot, known)
        if kind_name == "objectType"
    }


def _lay_out(document: Document, app: str, type_key: str) -> None:
    """A table view and detail page for a type arriving in ``app`` with none there, as
    ``addObjectType`` lays one out."""
    application = document.at(application_path(app))
    views = application.get("views") or []
    if not any(type_key in _types_named(document, application_path(app) + ["views", {"key": v["key"]}]) for v in views):
        view = table_view(document, app, type_key)
        document.insert(application_path(app) + ["views"], view)
        if not document.at(application_path(app)).get("defaultView"):
            document.set(application_path(app), "defaultView", view["key"])
    details = document.at(application_path(app)).get("details")
    if isinstance(details, list) and not any(d.get("objectTypeKey") == type_key for d in details):
        document.insert(application_path(app) + ["details"], detail_page(document, type_key))


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


@kind("addRelationType", params=("key", "reverseKey", "name", "reverseName", "isOriented"))
def add_relation_type(context: Context, raw: dict[str, Any]) -> Applied:
    """Add a relation type."""
    params = Params(raw)
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


@kind("removeRelationType", params=("relationType",))
def remove_relation_type(context: Context, raw: dict[str, Any]) -> Applied:
    """Remove a relation type."""
    params = Params(raw)
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
    place_relation(context.document, relation_key, source, target)


@kind("allowRelation", params=("relationType", "from", "to", "cardinality", "required", "layout"))
def allow_relation(context: Context, raw: dict[str, Any]) -> Applied:
    """Allow a relation type between two object types."""
    params = Params(raw)
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
    if required:
        # The target's stored records would each need the relationship, as a required attribute
        # needs its value (0.10 R-F3).
        context.unreleased(atom("objectType", target))
    if params.optional("layout", bool, True):
        _allow(context, relation_key, source, target, cardinality, required)
    else:
        binding = {"relationTypeKey": relation_key, "fromObjectTypeKey": source, "toObjectTypeKey": target, "cardinality": cardinality}
        if required:
            binding["required"] = True
        context.document.insert(["objectTypeRelations"], binding)
    # Undone by restoring what it changed: the layout it placed (a panel, a relation added to one)
    # goes with the binding, and a panel of the page that listed the relation before stays.
    return restoring(
        context,
        {"kind": "allowRelation", **raw},
        Applied(
            raw,
            {},
            created={atom("relationBinding", relation_key, source, target)},
            named={atom("relationType", relation_key), atom("objectType", source), atom("objectType", target)},
        ),
    )


@kind("disallowRelation", params=("relationType", "from", "to"))
def disallow_relation(context: Context, raw: dict[str, Any]) -> Applied:
    """Remove an allowed relationship between two object types."""
    params = Params(raw)
    relation_key, source, target = params.text("relationType"), params.text("from"), params.text("to")
    binding = context.relation_binding(relation_key, source, target)
    context.unreleased(atom("relationBinding", relation_key, source, target))
    context.document.remove(["objectTypeRelations"], identity(binding))
    document = context.document
    behavior = (document.at(type_path(target)).get("behavior") or {}) if document.find(type_path(target)) else {}
    if relation_key in (behavior.get("parentRelationTypeKeys") or []) and not any(
        b.get("relationTypeKey") == relation_key and b.get("toObjectTypeKey") == target for b in document.items("objectTypeRelations")
    ):
        document.remove(type_path(target) + ["behavior", "parentRelationTypeKeys"], relation_key)
    prune(document, Gone())
    return restoring(
        context,
        {"kind": "disallowRelation", **raw},
        Applied(raw, {}, named={atom("relationBinding", relation_key, source, target), atom("relationType", relation_key)}),
    )


@kind(
    "setRelationRule",
    params=(
        "relationType",
        "from",
        "to",
        "cardinality",
        "required",
        "candidates",
        "uniqueToAncestorTypeKey",
        "attributeTypeKeys",
    ),
)
def set_relation_rule(context: Context, raw: dict[str, Any]) -> Applied:
    """Change the rule of an allowed relationship."""
    params = Params(raw)
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
    if "attributeTypeKeys" in raw:
        keys = params.optional("attributeTypeKeys", list) or []
        if not all(isinstance(key, str) for key in keys) or len(keys) != len(set(keys)):
            raise Refusal(
                "attributeTypeKeys",
                "invalidValue",
                "'attributeTypeKeys' is a list of attribute type keys",
            )
        for key in keys:
            context.attribute_type(key, "attributeTypeKeys")
        inverse["attributeTypeKeys"] = list(binding.get("attributeTypeKeys") or [])
        context.document.set(path, "attributeTypeKeys", keys or None)
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


@kind("insertViewItem", params=(*_TARGET, "list", "item", "position"))
def insert_view_item(context: Context, raw: dict[str, Any]) -> Applied:
    """Insert an item into a list of a view or panel at a position."""
    params = Params(raw)
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


@kind("addPanel", params=("applicationKey", "detail", "show", "region", "title", "key"))
def add_panel_kind(context: Context, raw: dict[str, Any]) -> Applied:
    """Add a panel to an object type's detail page, built by the server: the records of one of the type's relationships, in either direction, or its contained records. Change its columns afterwards with `insertViewItem` and `removeViewItem`."""
    params = Params(raw)
    app = params.text("applicationKey")
    path = _detail_path(context, app, raw.get("detail"))
    type_key = raw["detail"]
    region = params.optional("region", str, "main")
    if region not in ("main", "side"):
        raise Refusal("region", "invalidValue", "'region' is 'main' or 'side'")
    title = params.optional("title", str)
    if title is not None and not title.strip():
        raise Refusal("title", "invalidValue", "'title' must not be empty")
    show = params.required("show", dict)
    panels = context.document.at(path).get("panels") or []
    taken = {p.get("key") for p in panels}
    given = params.optional("key")
    if given is not None and given in taken:
        raise Refusal("key", "keyTaken", f"The page already has a panel '{given}'")
    if set(show) == {"relations"} and isinstance(show["relations"], dict):
        relation = Params(show["relations"], ("relation", "direction"))
        relation_key, direction = relation.text("relation"), relation.text("direction")
        if direction not in ("outgoing", "incoming"):
            raise Refusal(
                "show/relations/direction",
                "invalidValue",
                "'direction' is 'outgoing' or 'incoming'",
            )
        context.relation_type(relation_key, "show/relations/relation")
        if (relation_key, direction) not in held_relations(context.document, type_key):
            raise Refusal(
                "show/relations/relation",
                "unknownElement",
                f"'{type_key}' does not hold '{relation_key}' {direction}",
            )
        panel = relations_panel(
            context.document, type_key, relation_key, direction, panels, title, region
        )
        named = {atom("relationType", relation_key)}
    elif set(show) == {"children"} and isinstance(show["children"], dict):
        keys = Params(show["children"], ("objectTypeKeys",)).required("objectTypeKeys", list)
        listed = context.document.at(application_path(app)).get("objectTypeKeys") or []
        contained = contained_types(context.document, type_key)
        for key in keys:
            if not isinstance(key, str) or key not in listed:
                raise Refusal(
                    "show/children/objectTypeKeys",
                    "invalidValue",
                    f"'{key}' is not a type of '{app}'",
                )
            if key not in contained:
                raise Refusal(
                    "show/children/objectTypeKeys",
                    "invalidValue",
                    f"'{type_key}' does not contain '{key}'",
                )
        if not keys or len(keys) != len(set(keys)):
            raise Refusal(
                "show/children/objectTypeKeys", "invalidValue", "Name each contained type once"
            )
        panel = children_panel(context.document, keys, panels)
        panel["region"] = region
        if title is not None:
            panel["title"] = title
        named = {atom("objectType", key) for key in keys}
    else:
        raise Refusal(
            "show",
            "invalidValue",
            "'show' is {relations: {relation, direction}} or {children: {objectTypeKeys}}",
        )
    if given is not None:
        panel["key"] = given
    add_panel(context.document, path, panel)
    stored = {**raw, "key": panel["key"], "title": panel["title"], "region": region}
    return Applied(
        stored,
        {
            "kind": "removeViewItem",
            "applicationKey": app,
            "detail": type_key,
            "list": "panels",
            "item": panel["key"],
        },
        created={atom("panel", app, type_key, panel["key"])},
        named=named | {atom("detail", app, type_key)},
    )


@kind("moveViewItem", params=(*_TARGET, "list", "item", "position"))
def move_view_item(context: Context, raw: dict[str, Any]) -> Applied:
    """Move an item within a list of a view or panel."""
    params = Params(raw)
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


@kind("removeViewItem", params=(*_TARGET, "list", "item"))
def remove_view_item(context: Context, raw: dict[str, Any]) -> Applied:
    """Remove an item from a list of a view or panel."""
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


@kind("setViewProperty", params=(*_TARGET, "property", "value"))
def set_view_property(context: Context, raw: dict[str, Any]) -> Applied:
    """Set a property of a view or panel."""
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


@kind("addView", params=("applicationKey", "view", "position", "default"))
def add_view(context: Context, raw: dict[str, Any]) -> Applied:
    """Add a view to an application."""
    params = Params(raw)
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


@kind("removeView", params=("applicationKey", "view", "unlist"))
def remove_view(context: Context, raw: dict[str, Any]) -> Applied:
    """A view out of its application; with ``unlist``, the types it named that the application then
    lists for nothing, so a matrix leaves as it came."""
    app = raw.get("applicationKey")
    path = _view_path(context, app, raw.get("view"))
    application = context.application(app)
    views = application.get("views") or []
    position = next(i for i, v in enumerate(views) if v.get("key") == raw["view"])
    was_default = application.get("defaultView") == raw["view"]
    needed = _members_needed(context.document, path)
    removed = context.document.remove(path[:-1], path[-1])
    if was_default:
        remaining = [v.get("key") for v in context.document.at(application_path(app)).get("views") or []]
        context.document.set(application_path(app), "defaultView", remaining[0] if remaining else "")
    named = {atom("view", app, raw["view"])}
    leaving = (
        needed & set(unlistable_types(context.document, app, context.released))
        if raw.get("unlist") is True
        else set()
    )
    left_navigation = drop_view_navigation(context.document, application_path(app), raw["view"])
    if leaving or left_navigation:
        for type_key in sorted(leaving):
            context.document.remove(application_path(app) + ["objectTypeKeys"], type_key)
        return restoring(context, {"kind": "removeView", **raw}, Applied(raw, {}, named=named))
    return Applied(
        raw,
        {"kind": "addView", "applicationKey": app, "view": removed, "position": position, "default": was_default},
        named=named,
    )


def unlistable_types(document: Document, app: str, released: Callable[[str], bool]) -> list[str]:
    """The types ``app`` lists that it could stop listing: nothing in it needs them, another
    application keeps them, and no release has them here, where records may stand."""
    path = application_path(app)
    application = document.at(path)
    needed = set(_members_needed(document, path + ["navigation"]))
    for name, by in (("views", "key"), ("details", "objectTypeKey")):
        for item in application.get(name) or []:
            needed |= _members_needed(document, path + [name, {by: item.get(by)}])
    return [
        key
        for key in application.get("objectTypeKeys") or []
        if key not in needed
        and not released(atom("listing", app, key))
        and any(key in (other.get("objectTypeKeys") or []) for other in document.items("applications") if other.get("key") != app)
    ]


@kind("listObjectType", params=("applicationKey", "objectType"))
def list_object_type(context: Context, raw: dict[str, Any]) -> Applied:
    """An existing type in one more application: its records keep the application they stand in."""
    params = Params(raw)
    app = params.text("applicationKey")
    application = context.application(app)
    key = params.text("objectType")
    context.object_type(key)
    if key in (application.get("objectTypeKeys") or []):
        raise Refusal("objectType", "invalidValue", f"'{app}' already lists '{key}'")
    context.document.insert(application_path(app) + ["objectTypeKeys"], key)
    return Applied(
        raw,
        {"kind": "unlistObjectType", "applicationKey": app, "objectType": key},
        created={atom("listing", app, key)},
        named={atom("application", app), atom("objectType", key)},
    )


@kind("unlistObjectType", params=("applicationKey", "objectType"))
def unlist_object_type(context: Context, raw: dict[str, Any]) -> Applied:
    """Take an object type out of an application's listing."""
    params = Params(raw)
    app = params.text("applicationKey")
    application = context.application(app)
    key = params.text("objectType")
    context.object_type(key)
    keys = application.get("objectTypeKeys") or []
    if key not in keys:
        raise Refusal("objectType", "unknownElement", f"'{app}' does not list '{key}'")
    context.unreleased(atom("listing", app, key))
    if key not in unlistable_types(context.document, app, context.in_use):
        raise Refusal("objectType", "invalidValue", f"'{app}' still needs '{key}', or no other application lists it")
    context.document.remove(application_path(app) + ["objectTypeKeys"], key)
    return restoring(
        context,
        {"kind": "unlistObjectType", **raw},
        Applied(raw, {}, named={atom("application", app), atom("objectType", key)}),
    )


@kind("addDetailPage", params=("applicationKey", "objectType", "page", "position"))
def add_detail_page(context: Context, raw: dict[str, Any]) -> Applied:
    """Add a detail page for a type of the application that has none: the standard page, or the `page` given (what undoing removeDetailPage puts back, at its `position`)."""
    params = Params(raw)
    app = params.text("applicationKey")
    application = context.application(app)
    type_key = params.text("objectType")
    context.object_type(type_key)
    if type_key not in (application.get("objectTypeKeys") or []):
        raise Refusal("objectType", "invalidValue", f"'{type_key}' is not a type of '{app}'")
    details = application.get("details") if isinstance(application.get("details"), list) else []
    if any(d.get("objectTypeKey") == type_key for d in details):
        raise Refusal("objectType", "alreadyPresent", f"'{type_key}' already has a detail page in '{app}'")
    stored = params.optional("page", dict)
    page = copy.deepcopy(stored) if stored is not None else detail_page(context.document, type_key)
    page["objectTypeKey"] = type_key
    starts_list = not isinstance(application.get("details"), list)
    if starts_list:
        context.document.set(application_path(app), "details", [])
    context.document.insert(application_path(app) + ["details"], page, _position(params, details))
    applied = Applied(
        {**raw, "page": page} if stored is None else raw,
        {"kind": "removeDetailPage", "applicationKey": app, "objectType": type_key},
        created={atom("detail", app, type_key)},
        named={atom("application", app), atom("objectType", type_key)},
    )
    # The first page starts the application's list of pages, which the undo takes away again.
    return restoring(context, {"kind": "addDetailPage", **raw}, applied) if starts_list else applied


@kind("removeDetailPage", params=("applicationKey", "objectType"))
def remove_detail_page(context: Context, raw: dict[str, Any]) -> Applied:
    """Remove an object type's detail page in an application."""
    app = raw.get("applicationKey")
    context.application(app)
    path = application_path(app) + ["details", {"objectTypeKey": raw.get("objectType")}]
    if not isinstance(raw.get("objectType"), str) or context.document.find(path) is None:
        raise Refusal("objectType", "unknownElement", f"No detail page of '{raw.get('objectType')}' in '{app}'")
    position = next(
        i for i, d in enumerate(context.document.at(path[:-1])) if d.get("objectTypeKey") == raw["objectType"]
    )
    removed = context.document.remove(path[:-1], path[-1])
    return Applied(
        raw,
        {"kind": "addDetailPage", "applicationKey": app, "objectType": raw["objectType"], "page": removed, "position": position},
        named={atom("detail", app, raw["objectType"])},
    )


# --- navigation groups ---


@kind("addNavigationGroup", params=("applicationKey", "key", "label", "collapsed", "position", "collections"))
def add_navigation_group(context: Context, raw: dict[str, Any]) -> Applied:
    """Add a navigation group to an application."""
    params = Params(raw)
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
        named={atom("application", app)}
        | {atom("objectType", c) for c in collections if isinstance(c, str)},
    )


@kind("removeNavigationGroup", params=("applicationKey", "group"))
def remove_navigation_group(context: Context, raw: dict[str, Any]) -> Applied:
    """Remove a navigation group from an application."""
    app = raw.get("applicationKey")
    path = _group_path(context, app, raw.get("group"))
    groups = context.document.at(path[:-1])
    position = next(i for i, g in enumerate(groups) if g.get("key") == raw["group"])
    removed = context.document.remove(path[:-1], path[-1])
    if not context.document.at(path[:-1]) and not (
        context.document.at(application_path(app) + ["navigation"]).get("opens")
    ):
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


@kind("setNavigationGroup", params=("applicationKey", "group", "label", "collapsed", "position"))
def set_navigation_group(context: Context, raw: dict[str, Any]) -> Applied:
    """Change a navigation group."""
    params = Params(raw)
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


@kind("placeCollection", params=("applicationKey", "collection", "view", "group", "position"))
def place_collection(context: Context, raw: dict[str, Any]) -> Applied:
    """Place an entry in a navigation group, or take it out (``group`` null): a collection (its
    type, ``collection``) or a relation matrix view (``view``, which then has an entry of its own),
    at ``position`` of the group's one order, moving it from where it stood."""
    params = Params(raw)
    app = params.text("applicationKey")
    application = context.application(app)
    if ("collection" in raw) == ("view" in raw):
        raise Refusal(
            "collection", "missingParameter", "Name the entry: a collection or a view, not both"
        )
    entry: Any
    if "view" in raw:
        view_key = params.text("view")
        view = next((v for v in application.get("views") or [] if v.get("key") == view_key), None)
        if view is None:
            raise Refusal("view", "unknownElement", f"No view '{view_key}' in '{app}'")
        if view.get("type") != "relationMatrix":
            raise Refusal(
                "view",
                "invalidValue",
                f"View '{view_key}' is not a relation matrix; only a matrix has an entry of its own",
            )
        entry, named_entry = {"view": view_key}, atom("view", app, view_key)
        identifies = {"view": view_key}
    else:
        entry = params.text("collection")
        context.object_type(entry, "collection")
        identifies = {"collection": entry}
        named_entry = atom("objectType", entry)
    target = params.optional("group")
    groups = ((application.get("navigation") or {}).get("groups")) or []
    if target is not None and not any(g.get("key") == target for g in groups):
        raise Refusal("group", "unknownElement", f"No navigation group '{target}' in '{app}'")
    old_group, old_position = None, None
    for group in groups:
        members = group.get("collections") or []
        if entry in members:
            old_group, old_position = group["key"], members.index(entry)
            context.document.remove(
                application_path(app)
                + ["navigation", "groups", {"key": group["key"]}, "collections"],
                entry,
            )
    if target is not None:
        members_path = application_path(app) + ["navigation", "groups", {"key": target}, "collections"]
        members = context.document.find(members_path) or []
        context.document.insert(members_path, entry, _position(params, members))
    inverse: dict[str, Any] = {
        "kind": "placeCollection",
        "applicationKey": app,
        **identifies,
        "group": old_group,
    }
    if old_position is not None:
        inverse["position"] = old_position
    named = {atom("application", app), named_entry} | (
        {atom("group", app, target)} if target else set()
    )
    return Applied(raw, inverse, named=named)


@kind("setCollectionOpening", params=("applicationKey", "collection", "view"))
def set_collection_opening(context: Context, raw: dict[str, Any]) -> Applied:
    """The view a collection's sidebar entry opens on (``view`` null: the application's default
    view), by a view over the collection's type."""
    params = Params(raw)
    app = params.text("applicationKey")
    application = context.application(app)
    collection = params.text("collection")
    context.object_type(collection, "collection")
    views = application.get("views") or []
    if collection not in {_listed_type(v) for v in views}:
        raise Refusal("collection", "unknownElement", f"'{collection}' is no collection of '{app}'")
    view_key = params.optional("view")
    if view_key is not None and not any(
        v.get("key") == view_key and _listed_type(v) == collection for v in views
    ):
        raise Refusal(
            "view", "unknownElement", f"No view '{view_key}' of '{collection}' in '{app}'"
        )
    path = application_path(app)
    navigation = application.get("navigation")
    previous = (
        (navigation.get("opens") or {}).get(collection) if isinstance(navigation, dict) else None
    )
    if view_key is not None:
        if not isinstance(navigation, dict):
            context.document.set(path, "navigation", {"groups": []})
        context.document.set(
            path + ["navigation"],
            "opens",
            {
                **(context.document.at(path + ["navigation"]).get("opens") or {}),
                collection: view_key,
            },
        )
    elif previous is not None:
        remaining = {k: v for k, v in navigation["opens"].items() if k != collection}
        context.document.set(path + ["navigation"], "opens", remaining or None)
        if not remaining and not navigation.get("groups"):
            context.document.set(path, "navigation", None)
    inverse = {
        "kind": "setCollectionOpening",
        "applicationKey": app,
        "collection": collection,
        "view": previous,
    }
    return Applied(raw, inverse, named={atom("application", app), atom("objectType", collection)})


# --- written by the server ---


@kind("replaceModel", params=("model",))
def replace_model(context: Context, raw: dict[str, Any]) -> Applied:
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


@kind("restoreElements", params=("undoes", "removes", "changes"))
def restore_elements(context: Context, raw: dict[str, Any]) -> Applied:
    context.unreleased(*(raw.get("removes") or ()))
    changes = raw.get("changes")
    undoes = raw.get("undoes")
    if not isinstance(changes, list) or not isinstance(undoes, dict):
        raise Refusal("changes", "invalidValue", "'changes' are the logged changes of an operation")
    try:
        apply_changes(context.documents, changes)
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
