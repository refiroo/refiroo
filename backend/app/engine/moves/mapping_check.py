"""A model mapping read against two releases (0.11 X1, D110): its problems and its coverage.

**Problems** are the entries naming what a release lacks or no longer allows, each with its JSON
pointer into the mapping and the side it concerns: ``ELEMENT_NOT_IN_RELEASE`` (a type, attribute or
relation the release does not declare), ``BINDING_NOT_ALLOWED`` (declared, but not bound to the
mapped type, not allowed at its end, not a containment of it, not unique for a match),
``VALUE_TYPES_NOT_CONVERTIBLE`` (a pair no value crosses) and ``ATTRIBUTE_FILLED_TWICE`` (two source
attributes onto one target attribute). Operations refuse each of them when they are applied; a
problem appears when a release changes under the mapping, or when it is read against the releases
two workspaces run.

**Coverage** is what the mapping leaves out: the source types, attributes and relationships not
mapped, the target's required attributes and relationships nothing fills, and the parents a source
record may stand under that its target type cannot. Record counts are the move's dry run (X2).
Both are read from model metadata only.
"""

from typing import Any

from ..records.values import conversion
from .sides import Side


def _escape(token: str) -> str:
    return token.replace("~", "~0").replace("/", "~1")


def problems(definition: dict[str, Any], source: Side, target: Side) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []

    def problem(code: str, pointer: str, side: str, message: str) -> None:
        found.append({"code": code, "pointer": pointer, "side": side, "message": message})

    def element(present: bool, pointer: str, side: str, label: str) -> bool:
        if not present:
            problem("ELEMENT_NOT_IN_RELEASE", pointer, side, f"The {side} release has no {label}")
        return present

    for i, entry in enumerate(definition.get("types") or []):
        at = f"/types/{i}"
        s, t = entry.get("source"), entry.get("target")
        s_ok = element(source.has_type(s), f"{at}/source", "source", f"type '{s}'")
        t_ok = element(target.has_type(t), f"{at}/target", "target", f"type '{t}'")
        filled: set[str] = set()
        for j, item in enumerate(entry.get("attributes") or []):
            here = f"{at}/attributes/{j}"
            a = item.get("source")
            if (
                s_ok
                and element(source.has_attribute(a), f"{here}/source", "source", f"attribute '{a}'")
                and not source.binding(s, a)
            ):
                problem(
                    "BINDING_NOT_ALLOWED",
                    f"{here}/source",
                    "source",
                    f"Type '{s}' does not bind '{a}'",
                )
            b = item.get("target")
            if item.get("ignore") or not t_ok:
                continue
            if not element(target.has_attribute(b), f"{here}/target", "target", f"attribute '{b}'"):
                continue
            if not target.binding(t, b):
                problem(
                    "BINDING_NOT_ALLOWED",
                    f"{here}/target",
                    "target",
                    f"Type '{t}' does not bind '{b}'",
                )
            elif (
                source.has_attribute(a)
                and conversion(source.value_type(a), target.value_type(b)) == "never"
            ):
                problem(
                    "VALUE_TYPES_NOT_CONVERTIBLE",
                    f"{here}/target",
                    "target",
                    f"No {source.value_type(a)} value converts to {target.value_type(b)}",
                )
            elif b in filled:
                problem(
                    "ATTRIBUTE_FILLED_TWICE",
                    f"{here}/target",
                    "target",
                    f"'{b}' is filled by two attributes",
                )
            filled.add(b)
        if not t_ok:
            continue
        for name in entry.get("defaults") or {}:
            pointer = f"{at}/defaults/{_escape(name)}"
            if element(
                target.has_attribute(name), pointer, "target", f"attribute '{name}'"
            ) and not target.binding(t, name):
                problem(
                    "BINDING_NOT_ALLOWED", pointer, "target", f"Type '{t}' does not bind '{name}'"
                )
        match = entry.get("match") or {}
        if match.get("attributeTypeKey") is not None:
            key = match["attributeTypeKey"]
            if not (target.binding(t, key) and target.unique(key)):
                problem(
                    "BINDING_NOT_ALLOWED",
                    f"{at}/match/attributeTypeKey",
                    "target",
                    f"Type '{t}' binds no unique '{key}'",
                )
        parent = entry.get("parent") or {}
        own = target.parents(t)
        if parent.get("relationTypeKey") is not None and parent["relationTypeKey"] not in {
            r for r, _ in own
        }:
            problem(
                "BINDING_NOT_ALLOWED",
                f"{at}/parent/relationTypeKey",
                "target",
                f"'{parent['relationTypeKey']}' does not contain '{t}'",
            )
        if parent.get("objectTypeKey") is not None and parent["objectTypeKey"] not in {
            p for _, p in own
        }:
            problem(
                "BINDING_NOT_ALLOWED",
                f"{at}/parent/objectTypeKey",
                "target",
                f"'{t}' cannot stand under '{parent['objectTypeKey']}'",
            )
        for k, item in enumerate(entry.get("relations") or []):
            here = f"{at}/relations/{k}"
            r = item.get("source")
            if (
                s_ok
                and element(source.has_relation(r), f"{here}/source", "source", f"relation '{r}'")
                and not source.relation_ends(r, s, "outgoing")
            ):
                problem(
                    "BINDING_NOT_ALLOWED",
                    f"{here}/source",
                    "source",
                    f"'{r}' is not allowed from '{s}'",
                )
            q, direction = item.get("target"), item.get("direction", "outgoing")
            if not element(target.has_relation(q), f"{here}/target", "target", f"relation '{q}'"):
                continue
            ends = target.relation_ends(q, t, direction)
            if not ends:
                problem(
                    "BINDING_NOT_ALLOWED",
                    f"{here}/target",
                    "target",
                    f"'{q}' is not allowed with '{t}' at its {direction} end",
                )
                continue
            allowed = {a for end in ends for a in end.attributeTypeKeys}
            for m, pair in enumerate(item.get("attributes") or []):
                if pair.get("target") not in allowed:
                    problem(
                        "BINDING_NOT_ALLOWED",
                        f"{here}/attributes/{m}/target",
                        "target",
                        f"'{q}' carries no '{pair.get('target')}'",
                    )
    return found


def coverage(definition: dict[str, Any], source: Side, target: Side) -> dict[str, list[Any]]:
    entries = [
        e
        for e in definition.get("types") or []
        if source.has_type(e.get("source")) and target.has_type(e.get("target"))
    ]
    mapped = {e.get("source") for e in definition.get("types") or []}
    targets = {e["source"]: e["target"] for e in entries}
    attributes, relations, parents = [], [], []
    for entry in entries:
        s, t = entry["source"], entry["target"]
        named = {item.get("source") for item in entry.get("attributes") or []}
        attributes += [
            {"sourceType": s, "attributeTypeKey": b.attributeTypeKey}
            for b in source.bindings(s)
            if b.attributeTypeKey not in named
        ]
        carried = {item.get("source") for item in entry.get("relations") or []}
        for relation in dict.fromkeys(item.relationTypeKey for item in source.relations_from(s)):
            if relation not in carried:
                relations.append({"sourceType": s, "relationTypeKey": relation})
        parents += _parents(entry, source, target, targets)
    required: list[dict[str, str]] = []
    required_relations: list[dict[str, str]] = []
    for t in dict.fromkeys(e["target"] for e in entries):
        onto = [e for e in entries if e["target"] == t]
        for b in target.bindings(t):
            if not b.required:
                continue
            key = b.attributeTypeKey
            if (
                not all(_fills(e, key) for e in onto)
                and {"targetType": t, "attributeTypeKey": key} not in required
            ):
                required.append({"targetType": t, "attributeTypeKey": key})
        for b in target.relations_from(t):
            if b.required and not all(
                any(item.get("target") == b.relationTypeKey for item in e.get("relations") or [])
                for e in onto
            ):
                item = {"targetType": t, "relationTypeKey": b.relationTypeKey}
                if item not in required_relations:
                    required_relations.append(item)
    return {
        "types": [key for key in source.type_keys if key not in mapped],
        "attributes": attributes,
        "relations": relations,
        "required": required,
        "requiredRelations": required_relations,
        "parents": parents,
    }


def _fills(entry: dict[str, Any], attribute: str) -> bool:
    return attribute in (entry.get("defaults") or {}) or any(
        item.get("target") == attribute for item in entry.get("attributes") or []
    )


def _parents(
    entry: dict[str, Any], source: Side, target: Side, targets: dict[str, str]
) -> list[dict[str, Any]]:
    """Where a record of the source type may stand that its target type cannot."""
    s, t = entry["source"], entry["target"]
    parent = entry.get("parent")
    allowed = {p for _, p in target.parents(t)}
    if parent is None:
        return (
            []
            if target.rootable(t)
            else [{"sourceType": s, "parentType": None, "reason": "PARENT_REQUIRED"}]
        )
    if parent.get("from") != "source":
        return []
    found = []
    if source.rootable(s) and not target.rootable(t):
        found.append({"sourceType": s, "parentType": None, "reason": "PARENT_REQUIRED"})
    for parent_type in dict.fromkeys(p for _, p in source.parents(s)):
        if parent_type not in targets:
            found.append(
                {"sourceType": s, "parentType": parent_type, "reason": "PARENT_TYPE_NOT_MAPPED"}
            )
        elif targets[parent_type] not in allowed:
            found.append(
                {"sourceType": s, "parentType": parent_type, "reason": "PARENT_NOT_ALLOWED"}
            )
    return found
