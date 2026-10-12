"""The draft's import profile follows its model (0.10 A5, D13, D78).

A draft's profile (D75) names model elements by key: the type and application a source loads, the
attribute a column fills, the parent, relation or related record a column matches. When an
operation changes the model, the profile is changed in the same operation, through its own
:class:`~.document.Document`, so the step's undo takes back both:

- a key change rewrites the key everywhere in the profile (:func:`rename`);
- a moved attribute's column moves to a source of the target type on the same sheet and block;
  a split type's columns go to a source of the new type; a merged type's sources load the type it
  was merged into; an attribute turned into a list type becomes a lookup of the list by name; a
  changed containment re-points a parent column to the new parent when there is one;
- whatever a compound operation took away leaves the profile through :func:`prune`: a binding
  naming an element that is gone becomes an **unmapped** entry, kept in the profile with the
  operation that unmapped it, and reported as ``COLUMN_UNMAPPED`` until the column is mapped again.

The facts are read from the draft's JSON, not from a compiled model: a draft may be invalid between
steps (A2), and the profile still has to follow it.
"""

import copy
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

from .document import Document, Path
from .keys import key_from_label

# A slot of the profile naming a model element: where it is, its member, and what it names.
_BINDING_SLOTS = (
    ("relationTypeKey", "relationType"),
    ("objectTypeKey", "objectType"),
    ("applicationKey", "application"),
    ("attributeTypeKey", "attributeType"),
)


@dataclass
class Facts:
    """What the draft's model declares, as the profile needs it."""

    applications: dict[str, set[str]] = field(default_factory=dict)
    # Type key -> the attribute types it binds.
    types: dict[str, set[str]] = field(default_factory=dict)
    # (relation type, from type, to type) of every allowed relation.
    relations: set[tuple[str, str, str]] = field(default_factory=set)
    # Type key -> the types that may contain it.
    parents: dict[str, set[str]] = field(default_factory=dict)
    unique: set[str] = field(default_factory=set)

    def bound(self, type_key: str | None, attribute_key: str | None) -> bool:
        return attribute_key in self.types.get(type_key or "", set())

    def allowed(self, relation: str, direction: str, own: str, other: str) -> bool:
        ends = (own, other) if direction == "outgoing" else (other, own)
        return (relation, *ends) in self.relations


def facts(model: dict[str, Any]) -> Facts:
    found = Facts()
    for app in _items(model, "applications"):
        found.applications[app.get("key")] = set(app.get("objectTypeKeys") or [])
    containment: dict[str, set[str]] = {}
    for item in _items(model, "objectTypes"):
        found.types[item.get("key")] = {b.get("attributeTypeKey") for b in item.get("attributes") or []}
        containment[item.get("key")] = set((item.get("behavior") or {}).get("parentRelationTypeKeys") or [])
    for item in _items(model, "objectTypeRelations"):
        triple = (item.get("relationTypeKey"), item.get("fromObjectTypeKey"), item.get("toObjectTypeKey"))
        found.relations.add(triple)
        if triple[0] in containment.get(triple[2], set()):
            found.parents.setdefault(triple[2], set()).add(triple[1])
    for item in _items(model, "attributeTypes"):
        if (item.get("features") or {}).get("unique"):
            found.unique.add(item.get("key"))
    return found


def _items(data: dict[str, Any], name: str) -> list[dict[str, Any]]:
    return [item for item in data.get(name) or [] if isinstance(item, dict)]


def sources(profile: Document) -> list[dict[str, Any]]:
    return _items(profile.data, "sources")


def source_path(source: dict[str, Any]) -> Path:
    return ["sources", {"id": source["id"]}]


def column_path(source: dict[str, Any], binding: dict[str, Any], profile: Document) -> Path:
    return [*source_path(source), "columns", profile.identity(binding)]


def binding_kind(binding: dict[str, Any]) -> str:
    for name in ("field", "attributeTypeKey", "parent", "relation", "relationFlags", "relatedRecord", "ignore"):
        if binding.get(name) is not None:
            return name
    return ""


def new_source_id(profile: Document, sheet: str | None, type_key: str) -> str:
    return key_from_label(f"{sheet or 'sheet'} {type_key}", {s.get("id") for s in sources(profile)})


# --- slots and renames ---


def _slots(profile: Document) -> Iterator[tuple[Path, str, str]]:
    """Every member of the profile naming a model element: (path of its object, member, kind)."""
    for source in sources(profile):
        path = source_path(source)
        yield path, "applicationKey", "application"
        yield path, "objectTypeKey", "objectType"
        if isinstance(source.get("key"), dict) and "attributeTypeKey" in source["key"]:
            yield [*path, "key"], "attributeTypeKey", "attributeType"
        for binding in source.get("columns") or []:
            at = column_path(source, binding, profile)
            if "attributeTypeKey" in binding:
                yield at, "attributeTypeKey", "attributeType"
            for part in ("parent", "relation", "relationFlags", "relatedRecord"):
                inner = binding.get(part)
                if not isinstance(inner, dict):
                    continue
                yield from _inner(inner, [*at, part])


def _inner(inner: dict[str, Any], path: Path) -> Iterator[tuple[Path, str, str]]:
    for member, kind in _BINDING_SLOTS:
        if member in inner:
            yield path, member, kind
    for nested in ("matchBy", "parent"):
        if isinstance(inner.get(nested), dict):
            yield from _inner(inner[nested], [*path, nested])
    for value in inner.get("attributes") or []:
        if isinstance(value, dict) and "attributeTypeKey" in value:
            yield [*path, "attributes", {"column": value.get("column")}], "attributeTypeKey", "attributeType"


def rename(profile: Document, kind: str, old: str, new: str) -> None:
    """Every slot of ``kind`` naming ``old`` names ``new``."""
    if old == new:
        return
    for path, member, slot_kind in list(_slots(profile)):
        if slot_kind == kind and profile.at(path).get(member) == old:
            profile.set(path, member, new)


# --- following a model change ---


def move_columns(profile: Document, attribute_key: str, source_type: str, target_type: str) -> None:
    """A moved attribute's columns go to a source of the target type on the same sheet and block."""
    for source in sources(profile):
        if source.get("objectTypeKey") != source_type:
            continue
        target = next(
            (
                other
                for other in sources(profile)
                if other.get("objectTypeKey") == target_type
                and other.get("sheet") == source.get("sheet")
                and other.get("block") == source.get("block")
            ),
            None,
        )
        if target is None:
            continue
        for binding in list(source.get("columns") or []):
            if binding.get("attributeTypeKey") != attribute_key:
                continue
            taken = {b.get("column") for b in target.get("columns") or []}
            if binding.get("column") in taken:
                continue
            moved = profile.remove([*source_path(source), "columns"], profile.identity(binding))
            profile.insert([*source_path(target), "columns"], moved)


def split_columns(
    profile: Document, facts_after: Facts, source_type: str, new_type: str, application: str,
    moved: list[str], relation_key: str,
) -> None:
    """A split type's moved columns go to a new source of the new type on the same sheet, keyed by
    the first moved unique attribute, joined to the original source by the split's relation."""
    for source in list(sources(profile)):
        if source.get("objectTypeKey") != source_type:
            continue
        columns = [b for b in source.get("columns") or [] if b.get("attributeTypeKey") in moved]
        if not columns:
            continue
        for binding in columns:
            profile.remove([*source_path(source), "columns"], profile.identity(binding))
        added: dict[str, Any] = {
            "id": new_source_id(profile, source.get("sheet"), new_type),
            **{name: copy.deepcopy(source[name]) for name in ("sheet", "headerRow", "block") if name in source},
            "applicationKey": application,
            "objectTypeKey": new_type,
            "columns": copy.deepcopy(columns),
        }
        key = next((b for b in columns if b["attributeTypeKey"] in facts_after.unique), None)
        if key is not None:
            added["key"] = {"attributeTypeKey": key["attributeTypeKey"]}
            profile.insert(
                [*source_path(source), "columns"],
                {
                    "column": key["column"],
                    "relation": {
                        "relationTypeKey": relation_key,
                        "objectTypeKey": new_type,
                        "matchBy": {"attributeTypeKey": key["attributeTypeKey"]},
                    },
                },
            )
        profile.insert(["sources"], added)


def list_lookup(profile: Document, owner: str, attribute_key: str, list_type: str, relation_key: str) -> None:
    """A column of an attribute turned into a list type reads the list by name, creating values
    the list lacks (D77)."""
    for source in sources(profile):
        if source.get("objectTypeKey") != owner:
            continue
        for binding in list(source.get("columns") or []):
            if binding.get("attributeTypeKey") != attribute_key:
                continue
            replaced = {
                "column": binding["column"],
                "relation": {
                    "relationTypeKey": relation_key,
                    "objectTypeKey": list_type,
                    "matchBy": {"field": "name"},
                    "missing": "create",
                },
            }
            if binding.get("valueMap"):
                replaced["valueMap"] = binding["valueMap"]
            path = [*source_path(source), "columns"]
            index = (source.get("columns") or []).index(binding)
            profile.remove(path, profile.identity(binding))
            profile.insert(path, replaced, index)


def follow_parent(profile: Document, type_key: str, parents: list[str]) -> None:
    """A parent column of ``type_key`` names its new parent type when there is exactly one."""
    if len(parents) != 1:
        return
    for source in sources(profile):
        if source.get("objectTypeKey") != type_key:
            continue
        for binding in source.get("columns") or []:
            parent = binding.get("parent")
            if isinstance(parent, dict) and parent.get("objectTypeKey") not in parents:
                profile.set([*column_path(source, binding, profile), "parent"], "objectTypeKey", parents[0])


# --- what no longer resolves ---


def prune(profile: Document, model: dict[str, Any], because: str) -> None:
    """Every source and binding naming an element the model no longer declares becomes an
    unmapped entry, with the operation (``because``) that took it away."""
    if not sources(profile):
        return
    known = facts(model)
    for source in list(sources(profile)):
        if not _source_resolves(known, source):
            removed = profile.remove(["sources"], {"id": source["id"]})
            _unmapped(profile, {"sheet": removed.get("sheet"), "source": removed["id"], "loads": removed}, because)
            continue
        key = source.get("key")
        if isinstance(key, dict) and "attributeTypeKey" in key and not known.bound(
            source["objectTypeKey"], key["attributeTypeKey"]
        ):
            profile.set(source_path(source), "key", None)
            _unmapped(profile, {"sheet": source.get("sheet"), "source": source["id"], "key": key}, because)
        for binding in list(source.get("columns") or []):
            if binding_resolves(known, source, binding):
                continue
            profile.remove([*source_path(source), "columns"], profile.identity(binding))
            entry = {"sheet": source.get("sheet"), "source": source["id"], "binding": binding}
            entry["column" if "column" in binding else "columns"] = binding.get("column", binding.get("columns"))
            _unmapped(profile, entry, because)


def _unmapped(profile: Document, entry: dict[str, Any], because: str) -> None:
    """An unmapped entry, named ``<source>/<column>`` (``/key``, ``/source``), replacing an older one."""
    label = entry.get("column") or ",".join(entry.get("columns") or []) or ("key" if "key" in entry else "source")
    entry_id = f"{entry['source']}/{label}"
    if profile.find(["unmapped", {"id": entry_id}]) is not None:
        profile.remove(["unmapped"], {"id": entry_id})
    profile.insert(["unmapped"], {"id": entry_id, **copy.deepcopy(entry), "because": {"kind": because}})


def _source_resolves(known: Facts, source: dict[str, Any]) -> bool:
    type_key = source.get("objectTypeKey")
    return type_key in known.types and type_key in known.applications.get(source.get("applicationKey"), set())


def binding_resolves(known: Facts, source: dict[str, Any], binding: dict[str, Any]) -> bool:
    """Whether every element a column binding names is declared, and allowed where it stands."""
    own = source.get("objectTypeKey")
    if "attributeTypeKey" in binding:
        return known.bound(own, binding["attributeTypeKey"])
    parent = binding.get("parent")
    if isinstance(parent, dict):
        return parent.get("objectTypeKey") in known.parents.get(own, set()) and _match_resolves(
            known, parent.get("objectTypeKey"), parent.get("matchBy")
        )
    for part in ("relation", "relationFlags"):
        inner = binding.get(part)
        if isinstance(inner, dict):
            other = inner.get("objectTypeKey")
            return (
                other in known.types
                and known.allowed(inner.get("relationTypeKey"), inner.get("direction", "outgoing"), own, other)
                and _match_resolves(known, other, inner.get("matchBy"))
            )
    related = binding.get("relatedRecord")
    if isinstance(related, dict):
        other = related.get("objectTypeKey")
        parent = related.get("parent") if isinstance(related.get("parent"), dict) else {}
        return (
            other in known.types
            and other in known.applications.get(related.get("applicationKey"), set())
            and known.allowed(related.get("relationTypeKey"), related.get("direction", "outgoing"), own, other)
            and ("attributeTypeKey" not in related or known.bound(other, related["attributeTypeKey"]))
            and parent.get("objectTypeKey") in known.types
            and _match_resolves(known, parent.get("objectTypeKey"), parent.get("matchBy"))
        )
    return True


def _match_resolves(known: Facts, type_key: str | None, match: Any) -> bool:
    if isinstance(match, dict) and "attributeTypeKey" in match:
        return known.bound(type_key, match["attributeTypeKey"])
    return True
