"""A draft compared with its proposals (Product 0.10 A6, D89, D92).

**Whose an element is.** A step that applies a proposal stores, in its origin, a snapshot of every
element it created or changed as the step left it. An element is the engine's while it is as the
latest proposal step touching it left it; any other change makes it the administrator's, and an
undo that puts it back makes it the engine's again. The editor's Proposed marks read this, and a
proposal is proposed again (revised) only while everything it created is the engine's.

**Elements** are named as the history names them (``objectType:item``, ``relationBinding:has/a/b``)
and, for the draft's profile, ``source:<id>``, ``column:<source>/<header>`` (the binding holding
the column), ``valueMap:<name>`` and ``ignoredSheet:<name>``. Applications, views and detail pages
change whenever a type is added and are nobody's.

**Whether an operation holds.** An operation whose effect the draft already has (a type of its key,
a column bound as it binds it) is left out of a proposal, so proposing again applies only what
changed.
"""

import copy
from collections.abc import Iterable, Iterator
from typing import Any

from ...model.authoring.profile_side import binding_kind

MODEL_KINDS = ("objectType", "attributeType", "relationType", "attributeBinding", "relationBinding", "group")
# Operations naming a column of a source without binding it: they need the column bound first.
COLUMN_USERS = ("setValueMap", "splitColumn", "addValuesToList")
BINDING_KINDS = ("mapColumn", "setColumnReading", "ignoreColumn", "unmapColumn")


def _items(data: dict[str, Any], name: str) -> list[dict[str, Any]]:
    value = data.get(name) if isinstance(data, dict) else None
    return [item for item in value or [] if isinstance(item, dict)]


def element_state(model: dict[str, Any], profile: dict[str, Any] | None, element: str) -> Any:
    """The element as the draft holds it, or ``None`` when it is not there."""
    kind, _, rest = element.partition(":")
    parts = rest.split("/")
    profile = profile or {}
    if kind == "objectType":
        return next((t for t in _items(model, "objectTypes") if t.get("key") == rest), None)
    if kind == "attributeType":
        return next((a for a in _items(model, "attributeTypes") if a.get("key") == rest), None)
    if kind == "relationType":
        return next((r for r in _items(model, "relationTypes") if r.get("key") == rest), None)
    if kind == "attributeBinding" and len(parts) == 2:
        found = element_state(model, profile, f"objectType:{parts[0]}")
        return next((b for b in (found or {}).get("attributes") or [] if b.get("attributeTypeKey") == parts[1]), None)
    if kind == "relationBinding" and len(parts) == 3:
        return next(
            (
                b
                for b in _items(model, "objectTypeRelations")
                if (b.get("relationTypeKey"), b.get("fromObjectTypeKey"), b.get("toObjectTypeKey")) == tuple(parts)
            ),
            None,
        )
    if kind == "group" and len(parts) == 2:
        application = next((a for a in _items(model, "applications") if a.get("key") == parts[0]), None)
        groups = ((application or {}).get("navigation") or {}).get("groups") or []
        return next((g for g in groups if g.get("key") == parts[1]), None)
    if kind == "source":
        source = next((s for s in _items(profile, "sources") if s.get("id") == rest), None)
        return {k: v for k, v in source.items() if k != "columns"} if source else None
    if kind == "column":
        source_id, _, header = rest.partition("/")
        source = next((s for s in _items(profile, "sources") if s.get("id") == source_id), None)
        return bound(source, header)
    if kind == "valueMap":
        return (profile.get("valueMaps") or {}).get(rest)
    if kind == "ignoredSheet":
        return True if rest in (profile.get("ignoredSheets") or []) else None
    return None


def bound(source: dict[str, Any] | None, header: str) -> dict[str, Any] | None:
    """The binding of ``source`` that reads ``header``."""
    for binding in (source or {}).get("columns") or []:
        if binding.get("column") == header or header in (binding.get("columns") or []):
            return binding
    return None


def snapshot(model: dict[str, Any], profile: dict[str, Any] | None, elements: Iterable[str]) -> dict[str, Any]:
    return {element: copy.deepcopy(element_state(model, profile, element)) for element in sorted(set(elements))}


def profile_elements(operations: Iterable[dict[str, Any]]) -> set[str]:
    """The profile elements operations create or change."""
    found: set[str] = set()
    for operation in operations:
        name = operation.get("kind")
        if name == "addSource" and operation.get("id"):
            found.add(f"source:{operation['id']}")
        elif name == "setSource":
            found.add(f"source:{operation.get('source')}")
        if name in BINDING_KINDS + COLUMN_USERS and operation.get("source") and operation.get("column"):
            found.add(f"column:{operation['source']}/{operation['column']}")
        if name == "setValueMap":
            found.add(f"valueMap:{operation.get('name')}")
        if name == "ignoreSheet":
            found.add(f"ignoredSheet:{operation.get('sheet')}")
    return found


def model_elements(atoms: Iterable[str]) -> set[str]:
    return {a for a in atoms if a.partition(":")[0] in MODEL_KINDS}


def created_elements(operations: list[dict[str, Any]]) -> set[str]:
    """What a proposal's operations create, as later proposals and the history name it."""
    found: set[str] = set()
    for operation in operations:
        name = operation.get("kind")
        if name == "addApplication":
            found.add(f"application:{operation['key']}")
        elif name == "addObjectType":
            found.add(f"objectType:{operation['key']}")
            parent = operation.get("parent") or {}
            if isinstance(parent.get("relationType"), dict):
                found.add(f"relationType:{parent['relationType']['key']}")
        elif name == "setContainment":
            parent = operation.get("parent") or {}
            if isinstance(parent.get("relationType"), dict):
                found.add(f"relationType:{parent['relationType']['key']}")
        elif name == "addAttributeType":
            found.add(f"attributeType:{operation['key']}")
        elif name == "attachAttribute":
            found.add(f"attributeBinding:{operation['objectType']}/{operation['attributeType']}")
        elif name == "addRelationType":
            found.add(f"relationType:{operation['key']}")
        elif name == "allowRelation":
            found.add(f"relationBinding:{operation['relationType']}/{operation['from']}/{operation['to']}")
        elif name == "addNavigationGroup":
            found.add(f"group:{operation['applicationKey']}/{operation['key']}")
        elif name in ("mapColumn", "setColumnReading", "ignoreColumn"):
            found.add(f"column:{operation['source']}/{operation['column']}")
    return found | profile_elements(operations)


_REFERENCES = {
    "applicationKey": "application",
    "objectType": "objectType",
    "from": "objectType",
    "to": "objectType",
    "objectTypeKey": "objectType",
    "attributeType": "attributeType",
    "attributeTypeKey": "attributeType",
    "relationTypeKey": "relationType",
    "valueMap": "valueMap",
}


def _walk(value: Any) -> Iterator[str]:
    if isinstance(value, dict):
        for name, inner in value.items():
            if name in _REFERENCES and isinstance(inner, str):
                yield f"{_REFERENCES[name]}:{inner}"
            elif name == "relationType" and isinstance(inner, str):
                yield f"relationType:{inner}"
            elif name == "objectTypes" and isinstance(inner, list):
                yield from (f"objectType:{t}" for t in inner if isinstance(t, str))
            else:
                yield from _walk(inner)
    elif isinstance(value, list):
        for inner in value:
            yield from _walk(inner)


def referenced_elements(operations: list[dict[str, Any]]) -> set[str]:
    """What a proposal's operations name: model keys, sources, value maps, and the columns they
    use without binding them."""
    found: set[str] = set()
    for operation in operations:
        found |= set(_walk({k: v for k, v in operation.items() if k != "kind"}))
        if operation.get("source"):
            found.add(f"source:{operation['source']}")
        if operation.get("kind") in COLUMN_USERS + ("setColumnReading",) and operation.get("source") and operation.get("column"):
            found.add(f"column:{operation['source']}/{operation['column']}")
    return found


def holds(operation: dict[str, Any], model: dict[str, Any], profile: dict[str, Any] | None) -> bool:
    """Whether the draft already has what ``operation`` would do."""
    profile = profile or {}
    name = operation.get("kind")
    state = lambda element: element_state(model, profile, element)
    if name == "addApplication":
        return any(a.get("key") == operation["key"] for a in _items(model, "applications"))
    if name == "addObjectType":
        return state(f"objectType:{operation['key']}") is not None
    if name == "addAttributeType":
        return state(f"attributeType:{operation['key']}") is not None
    if name == "attachAttribute":
        return state(f"attributeBinding:{operation['objectType']}/{operation['attributeType']}") is not None
    if name == "addRelationType":
        return state(f"relationType:{operation['key']}") is not None
    if name == "allowRelation":
        return state(f"relationBinding:{operation['relationType']}/{operation['from']}/{operation['to']}") is not None
    if name == "setContainment":
        found = state(f"objectType:{operation['objectType']}")
        if found is None:
            return False
        relations = set((found.get("behavior") or {}).get("parentRelationTypeKeys") or [])
        parents = {
            b.get("fromObjectTypeKey")
            for b in _items(model, "objectTypeRelations")
            if b.get("toObjectTypeKey") == operation["objectType"] and b.get("relationTypeKey") in relations
        }
        wanted = set((operation.get("parent") or {}).get("objectTypes") or [])
        return parents == wanted
    if name == "addSource":
        return state(f"source:{operation['id']}") is not None
    if name == "setSource":
        found = state(f"source:{operation['source']}")
        return found is not None and all(found.get(k) == v for k, v in operation.items() if k not in ("kind", "source"))
    if name == "mapColumn":
        # The binding has what the operation sets; what other steps added to it (a value map of the
        # name drift's or the placeholders') does not undo it, and setting it again would drop that.
        current = state(f"column:{operation['source']}/{operation['column']}")
        return current is not None and all(current.get(k) == v for k, v in operation["binding"].items())
    if name == "setColumnReading" and operation.get("reading") == "relationFlag":
        current = state(f"column:{operation['source']}/{operation['column']}") or {}
        flags = current.get("relationFlags") or {}
        return (flags.get("targets") or {}).get(operation["column"]) == operation.get("target") and flags.get(
            "relationTypeKey"
        ) == operation.get("relationTypeKey")
    if name == "addValuesToList":
        current = state(f"column:{operation['source']}/{operation['column']}") or {}
        part = next((current[p] for p in ("relation", "parent", "relationFlags") if isinstance(current.get(p), dict)), {})
        return part.get("missing") == "create"
    if name == "splitColumn":
        current = state(f"column:{operation['source']}/{operation['column']}") or {}
        return (current.get("relation") or {}).get("split") == operation.get("delimiter")
    if name == "setValueMap":
        if (profile.get("valueMaps") or {}).get(operation["name"]) != operation.get("entries"):
            return False
        if operation.get("column"):
            current = state(f"column:{operation['source']}/{operation['column']}") or {}
            return current.get("valueMap") == operation["name"]
        return True
    if name == "ignoreColumn":
        current = state(f"column:{operation['source']}/{operation['column']}") or {}
        return bool(current.get("ignore"))
    if name == "unmapColumn":
        return state(f"column:{operation['source']}/{operation['column']}") is None
    if name == "ignoreSheet":
        return state(f"ignoredSheet:{operation['sheet']}") is not None
    if name == "setRelease" and set(operation) == {"kind", "schemaVersion"}:
        return _version(model.get("schemaVersion")) >= _version(operation["schemaVersion"])
    if name == "addNavigationGroup":
        return state(f"group:{operation['applicationKey']}/{operation['key']}") is not None
    return False


def _version(value: Any) -> tuple[int, ...]:
    try:
        return tuple(int(part) for part in str(value).split("."))
    except ValueError:
        return (0,)


def kind_of(binding: dict[str, Any] | None) -> str:
    return binding_kind(binding) if binding else ""
