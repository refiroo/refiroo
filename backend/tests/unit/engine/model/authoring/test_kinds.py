"""``engine/model/authoring/kinds.py``: every kind's inverse takes back exactly what it did.

The operations are generated over every element of two models (the example model and generated-b),
not written one per kind: each is applied to the document, then its inverse, and the document must be
as it was. ``setKey`` over every key of the example model keeps the model valid and leaves no
reference to an old key, in its consumer API definitions too (0.10 A4c, D54). The consumer API kinds
are generated over every part of both models' definitions, and ``addConsumerApi`` over every type
writes a definition that compiles.
"""

import copy
import json
from collections.abc import Iterator
from itertools import pairwise
from typing import Any

import pytest
from configurations import example, generated

from app.engine.model.authoring.cascade import references
from app.engine.model.authoring.document import Document, Refusal
from app.engine.model.authoring.kinds import Context, apply_operation
from app.engine.model.authoring.layout import held_relations
from app.engine.model.compiler import compile_model

MODELS = {"example": example().model, "generated-b": generated("b").model}


def _operations(model: dict[str, Any]) -> Iterator[dict[str, Any]]:
    """Operations of every kind over the model's elements."""
    types = [t["key"] for t in model["objectTypes"]]
    for application in model["applications"]:
        app = application["key"]
        yield {"kind": "setLabel", "element": {"applicationKey": app}, "name": "Renamed"}
        yield {"kind": "setKey", "element": {"applicationKey": app}, "key": "zz-app"}
        yield {
            "kind": "addNavigationGroup",
            "applicationKey": app,
            "label": "Group",
            "collections": [],
        }
        yield {
            "kind": "addObjectType",
            "applicationKey": app,
            "name": "Zz",
            "pluralName": "Zzs",
            "parent": None,
        }
        for view in application["views"]:
            yield {"kind": "removeView", "applicationKey": app, "view": view["key"]}
            yield {
                "kind": "setKey",
                "element": {"applicationKey": app, "view": view["key"]},
                "key": "zz-view",
            }
            yield {
                "kind": "setViewProperty",
                "applicationKey": app,
                "view": view["key"],
                "property": "pageSize",
                "value": 7,
            }
            if view["type"] == "table":
                columns = view["config"]["columns"]
                yield {
                    "kind": "removeViewItem",
                    "applicationKey": app,
                    "view": view["key"],
                    "list": "columns",
                    "item": columns[-1],
                }
                if len(columns) > 1:
                    yield {
                        "kind": "moveViewItem",
                        "applicationKey": app,
                        "view": view["key"],
                        "list": "columns",
                        "item": columns[-1],
                        "position": 0,
                    }
            yield {"kind": "removeView", "applicationKey": app, "view": view["key"], "unlist": True}
            if view["type"] in ("table", "relationMatrix"):
                source = (
                    view["objectTypeKey"]
                    if view["type"] == "table"
                    else view["config"]["rowObjectTypeKey"]
                )
                yield {
                    "kind": "setCollectionOpening",
                    "applicationKey": app,
                    "collection": source,
                    "view": view["key"],
                }
            if view["type"] == "relationMatrix":
                yield {
                    "kind": "addNavigationGroup",
                    "applicationKey": app,
                    "label": "Matrices",
                    "collections": [{"view": view["key"]}],
                }
        for type_key in application["objectTypeKeys"]:
            yield {"kind": "unlistObjectType", "applicationKey": app, "objectType": type_key}
        for type_key in types:
            if type_key not in application["objectTypeKeys"]:
                yield {"kind": "listObjectType", "applicationKey": app, "objectType": type_key}
        paged = {detail["objectTypeKey"] for detail in application.get("details", [])}
        for type_key in application["objectTypeKeys"]:
            kind = "removeDetailPage" if type_key in paged else "addDetailPage"
            yield {"kind": kind, "applicationKey": app, "objectType": type_key}
        paged = {d["objectTypeKey"] for d in application.get("details", [])}
        for type_key in application["objectTypeKeys"]:
            if type_key in paged:
                yield {"kind": "removeDetailPage", "applicationKey": app, "objectType": type_key}
            else:
                yield {"kind": "addDetailPage", "applicationKey": app, "objectType": type_key}
        for detail in application.get("details", []):
            for relation_key, direction in held_relations(Document(model), detail["objectTypeKey"]):
                yield {
                    "kind": "addPanel",
                    "applicationKey": app,
                    "detail": detail["objectTypeKey"],
                    "show": {"relations": {"relation": relation_key, "direction": direction}},
                }
            for panel in detail["panels"]:
                yield {
                    "kind": "removeViewItem",
                    "applicationKey": app,
                    "detail": detail["objectTypeKey"],
                    "list": "panels",
                    "item": panel["key"],
                }
                yield {
                    "kind": "setViewProperty",
                    "applicationKey": app,
                    "detail": detail["objectTypeKey"],
                    "panel": panel["key"],
                    "property": "visible",
                    "value": False,
                }
    for type_key in types:
        yield {"kind": "setLabel", "element": {"objectType": type_key}, "pluralName": "Others"}
        yield {"kind": "setKey", "element": {"objectType": type_key}, "key": "zz-type"}
        yield {"kind": "removeObjectType", "objectType": type_key}
        yield {"kind": "setContainment", "objectType": type_key, "parent": None}
        for application in model["applications"]:
            if type_key not in application["objectTypeKeys"]:
                yield {
                    "kind": "setContainment",
                    "objectType": type_key,
                    "application": application["key"],
                }
        yield {
            "kind": "allowRelation",
            "relationType": model["relationTypes"][0]["key"],
            "from": type_key,
            "to": types[0],
        }
        bindings = [
            b["attributeTypeKey"]
            for b in next(t for t in model["objectTypes"] if t["key"] == type_key).get(
                "attributes", []
            )
        ]
        for attribute in bindings:
            yield {"kind": "detachAttribute", "objectType": type_key, "attributeType": attribute}
            yield {
                "kind": "setAttributeBinding",
                "objectType": type_key,
                "attributeType": attribute,
                "required": True,
                "position": 0,
            }
            yield {
                "kind": "convertAttributeToListType",
                "objectType": type_key,
                "attributeType": attribute,
                "name": "Zz list",
                "relationType": {"name": "Has zz", "reverseName": "Zz of"},
            }
            other = next((t for t in types if t != type_key), None)
            if other:
                yield {
                    "kind": "moveAttribute",
                    "attributeType": attribute,
                    "from": type_key,
                    "to": other,
                }
        if bindings:
            yield {
                "kind": "splitObjectType",
                "objectType": type_key,
                "name": "Zz part",
                "attributes": bindings[:1],
                "relationType": {"name": "Has part", "reverseName": "Part of"},
            }
        yield {
            "kind": "addObjectType",
            "applicationKey": model["applications"][0]["key"],
            "name": "Zz child",
            "pluralName": "Zz children",
            "parent": {
                "objectTypes": [type_key],
                "relationType": {"name": "Holds", "reverseName": "Held by"},
            },
        }
        # A parent a record may also do without (0.10 A6b, D99).
        yield {
            "kind": "setContainment",
            "objectType": type_key,
            "parent": {
                "objectTypes": [types[0]],
                "relationType": {"name": "Holds", "reverseName": "Held by"},
                "optional": True,
            },
        }
    for first, second in pairwise(types):
        yield {"kind": "mergeObjectTypes", "into": first, "from": second}
    yield from _property_operations(model)
    for attribute in model["attributeTypes"]:
        yield {"kind": "setLabel", "element": {"attributeType": attribute["key"]}, "name": "Other"}
        yield {
            "kind": "setKey",
            "element": {"attributeType": attribute["key"]},
            "key": "zz-attribute",
        }
        yield {
            "kind": "setAttributeTypeFeatures",
            "attributeType": attribute["key"],
            "features": {"searchable": True, "unique": None},
        }
        yield {"kind": "setValueType", "attributeType": attribute["key"], "valueType": "longText"}
        for type_key in types[:2]:
            yield {
                "kind": "attachAttribute",
                "objectType": type_key,
                "attributeType": attribute["key"],
            }
    for relation in model["relationTypes"]:
        if relation.get("reverseName"):
            yield {
                "kind": "setLabel",
                "element": {"relationType": relation["key"]},
                "reverseName": "Zz back",
            }
        yield {
            "kind": "setKey",
            "element": {"relationType": relation["key"]},
            "key": "zz-rel",
            "reverseKey": "zz-rel-back",
        }
    for binding in model["objectTypeRelations"]:
        triple = {
            "relationType": binding["relationTypeKey"],
            "from": binding["fromObjectTypeKey"],
            "to": binding["toObjectTypeKey"],
        }
        yield {"kind": "disallowRelation", **triple}
        yield {"kind": "setRelationRule", **triple, "required": not binding.get("required", False)}
    yield {"kind": "addAttributeType", "name": "Zz attribute", "valueType": "integer"}
    yield {"kind": "addRelationType", "name": "Zz rel", "reverseName": "Zz rel back"}
    yield {"kind": "setRelease", "version": "9.9.9", "schemaVersion": "0.10"}
    yield from _consumer_operations(model)


def _property_operations(model: dict[str, Any]) -> Iterator[dict[str, Any]]:
    """The property kinds (0.13 ED) over every type, attribute type, relation type and application."""
    dates = {a["key"] for a in model["attributeTypes"] if a.get("valueType") == "date"}
    for object_type in model["objectTypes"]:
        key = object_type["key"]
        bound = [b["attributeTypeKey"] for b in object_type.get("attributes", [])]
        for property_name, value in (
            ("displayAttributeTypeKey", bound[0] if bound else None),
            ("displayAttributeTypeKey", None),
            ("atLeastOneOf", bound[:2]),
            ("atLeastOneOf", None),
            ("parentRelationTypeKeys", None),
            ("effectivePeriod", None),
        ):
            yield {
                "kind": "setObjectTypeProperty",
                "objectType": key,
                "property": property_name,
                "value": value,
            }
        if len([k for k in bound if k in dates]) >= 2:
            start, end = [k for k in bound if k in dates][:2]
            yield {
                "kind": "setObjectTypeProperty",
                "objectType": key,
                "property": "effectivePeriod",
                "value": {"startAttributeTypeKey": start, "endAttributeTypeKey": end},
            }
        for binding in object_type.get("attributes", []):
            yield {
                "kind": "setAttributeBinding",
                "objectType": key,
                "attributeType": binding["attributeTypeKey"],
                "ui": {"hidden": True, "helpText": "Help"},
            }
            yield {
                "kind": "setAttributeBinding",
                "objectType": key,
                "attributeType": binding["attributeTypeKey"],
                "ui": {"hidden": None, "helpText": None},
            }
    for attribute in model["attributeTypes"]:
        for property_name, value in (
            ("minimum", 1),
            ("maximum", 99),
            ("minimum", None),
            ("hidden", True),
            ("helpText", "Help"),
            ("helpText", None),
        ):
            yield {
                "kind": "setAttributeTypeProperty",
                "attributeType": attribute["key"],
                "property": property_name,
                "value": value,
            }
    for relation in model["relationTypes"]:
        yield {
            "kind": "setRelationTypeProperty",
            "relationType": relation["key"],
            "property": "isOriented",
            "value": not relation.get("isOriented", True),
        }
    for binding in model["objectTypeRelations"]:
        triple = {
            "relationType": binding["relationTypeKey"],
            "from": binding["fromObjectTypeKey"],
            "to": binding["toObjectTypeKey"],
        }
        yield {
            "kind": "setRelationRule",
            **triple,
            "attributeTypeKeys": [model["attributeTypes"][0]["key"]],
        }
        yield {"kind": "setRelationRule", **triple, "attributeTypeKeys": []}
    for application in model["applications"]:
        for view in application["views"]:
            yield {
                "kind": "setApplicationProperty",
                "applicationKey": application["key"],
                "property": "defaultView",
                "value": view["key"],
            }


def _consumer_operations(model: dict[str, Any]) -> Iterator[dict[str, Any]]:
    """The consumer API kinds over every part of every definition: each member and item set to
    itself, moved first, removed, and a copy inserted under a new key or at the start."""
    types = [t["key"] for t in model["objectTypes"]]
    yield {"kind": "addConsumerApi", "name": "Zz feed", "exposes": types[:2]}
    for definition in model.get("consumerApis", []):
        api = definition["key"]
        yield {"kind": "removeConsumerApi", "consumerApi": api}
        yield {"kind": "setConsumerApiPart", "consumerApi": api, "pointer": "", "value": definition}
        yield {
            "kind": "setConsumerApiPart",
            "consumerApi": api,
            "pointer": "/contractVersion",
            "value": 9,
        }
        yield {
            "kind": "setConsumerApiPart",
            "consumerApi": api,
            "pointer": "/key",
            "value": "zz-api",
        }
        for pointer, node in _parts(definition, ""):
            yield {
                "kind": "setConsumerApiPart",
                "consumerApi": api,
                "pointer": pointer,
                "value": node,
            }
            yield {"kind": "removeConsumerApiPart", "consumerApi": api, "pointer": pointer}
            yield {
                "kind": "moveConsumerApiPart",
                "consumerApi": api,
                "pointer": pointer,
                "position": 0,
            }
            container, _, last = pointer.rpartition("/")
            if last.isdigit():
                yield {
                    "kind": "insertConsumerApiPart",
                    "consumerApi": api,
                    "pointer": container,
                    "value": node,
                    "position": 0,
                }
            else:
                yield {
                    "kind": "insertConsumerApiPart",
                    "consumerApi": api,
                    "pointer": container,
                    "key": f"zz{last}",
                    "value": node,
                    "position": 0,
                }


def _parts(node: Any, pointer: str) -> Iterator[tuple[str, Any]]:
    """Every member of a map or item of a list below the definition's top level, with its pointer."""
    if isinstance(node, dict):
        for name, value in node.items():
            child = f"{pointer}/{name}"
            if pointer:
                yield child, value
            yield from _parts(value, child)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield f"{pointer}/{index}", value
            yield from _parts(value, f"{pointer}/{index}")


def _cases() -> Iterator[Any]:
    for name, model in MODELS.items():
        for index, operation in enumerate(_operations(model)):
            yield pytest.param(name, operation, id=f"{name}-{index}-{operation['kind']}")


def _apply(data: dict[str, Any], operation: dict[str, Any]) -> Any:
    document = Document(data)
    return apply_operation(Context(document, lambda _atom: False), operation)


@pytest.mark.parametrize(("model_name", "operation"), list(_cases()))
def test_an_operation_and_then_its_inverse_return_the_document(
    model_name: str, operation: dict[str, Any]
):
    original = MODELS[model_name]
    data = copy.deepcopy(original)
    try:
        applied = _apply(data, operation)
    except Refusal as refusal:
        # A refusal must leave a reason a client can act on.
        assert refusal.reason, refusal.message
        return
    inverse = applied.inverse
    _apply(data, inverse)
    assert data == original, f"{operation} then {inverse['kind']}"


def test_a_draft_only_kind_on_a_released_element_that_data_holds_applies_and_marks_a_migration():
    data = copy.deepcopy(MODELS["example"])
    type_key = data["objectTypes"][0]["key"]
    context = Context(Document(data), lambda atom: atom == f"objectType:{type_key}")
    apply_operation(context, {"kind": "removeObjectType", "objectType": type_key})
    assert context.take_marks() == [(f"objectType:{type_key}", False)]
    assert type_key not in [item["key"] for item in data["objectTypes"]]
    assert context.take_marks() == []


def test_a_removal_drops_the_relation_types_left_unbound_and_keeps_the_bound_ones_released_or_not():
    """A relation type with no binding left goes, released or not, unless data holds it; one that
    still has a binding stays, with no data (D31)."""
    original = MODELS["example"]
    for type_key in [t["key"] for t in original["objectTypes"]][:6]:
        data = copy.deepcopy(original)
        released = lambda _atom: True
        apply_operation(
            Context(Document(data), released, in_use=lambda _atom: False),
            {"kind": "removeObjectType", "objectType": type_key},
        )
        bound = {b["relationTypeKey"] for b in data["objectTypeRelations"]}
        kept = {r["key"] for r in data["relationTypes"]}
        before = {b["relationTypeKey"] for b in original["objectTypeRelations"]}
        assert bound <= kept
        assert kept == {
            r["key"]
            for r in original["relationTypes"]
            if r["key"] in bound or r["key"] not in before
        }
        held = copy.deepcopy(original)
        apply_operation(
            Context(Document(held), released, in_use=lambda atom: atom.startswith("relationType:")),
            {"kind": "removeObjectType", "objectType": type_key},
        )
        assert {r["key"] for r in held["relationTypes"]} == {
            r["key"] for r in original["relationTypes"]
        }


def test_a_released_element_data_does_not_hold_changes_unmarked_but_its_key_change_is_always_marked():
    type_key = MODELS["example"]["objectTypes"][0]["key"]
    released = lambda atom: atom == f"objectType:{type_key}"
    unheld = lambda _atom: False
    renaming = Context(Document(copy.deepcopy(MODELS["example"])), released, in_use=unheld)
    apply_operation(
        renaming, {"kind": "setKey", "element": {"objectType": type_key}, "key": "renamed"}
    )
    assert renaming.take_marks() == [(f"objectType:{type_key}", True)]
    data = copy.deepcopy(MODELS["example"])
    removing = Context(Document(data), released, in_use=unheld)
    apply_operation(removing, {"kind": "removeObjectType", "objectType": type_key})
    assert type_key not in [item["key"] for item in data["objectTypes"]]
    assert removing.take_marks() == []


def test_which_records_a_released_relationship_may_choose_changes_without_a_migration():
    """``candidates`` is compatible in a release (0.9 K7): set on a released binding, it applies;
    its cardinality on the same binding still needs a migration (found in A4a)."""
    data = copy.deepcopy(MODELS["example"])
    binding = data["objectTypeRelations"][0]
    triple = {
        "relationType": binding["relationTypeKey"],
        "from": binding["fromObjectTypeKey"],
        "to": binding["toObjectTypeKey"],
    }
    released = lambda atom: atom.startswith("relationBinding:")
    criteria = {"to": [{"field": "name", "op": "startsWith", "value": "A"}]}
    before = copy.deepcopy(binding.get("candidates"))
    applied = apply_operation(
        Context(Document(data), released),
        {"kind": "setRelationRule", **triple, "candidates": criteria},
    )
    assert data["objectTypeRelations"][0]["candidates"] == criteria
    assert applied.inverse["candidates"] == before
    tightening = Context(Document(data), released)
    apply_operation(tightening, {"kind": "setRelationRule", **triple, "cardinality": "one-to-one"})
    assert [mark for mark, _key in tightening.take_marks()] == [
        f"relationBinding:{triple['relationType']}/{triple['from']}/{triple['to']}"
    ]


def test_every_key_of_the_example_renamed_keeps_it_valid_and_leaves_no_old_reference():
    data = copy.deepcopy(MODELS["example"])
    renamed: list[tuple[str, str]] = []
    for kind, collection in (
        ("objectType", "objectTypes"),
        ("attributeType", "attributeTypes"),
        ("relationType", "relationTypes"),
    ):
        for key, reverse in [(item["key"], item.get("reverseKey")) for item in data[collection]]:
            operation: dict[str, Any] = {
                "kind": "setKey",
                "element": {kind: key},
                "key": f"zq-{key}",
            }
            if kind == "relationType":
                operation["reverseKey"] = f"zq-{reverse}"
                renamed.append(("relationKey", reverse))
            _apply(data, operation)
            renamed.append((kind if kind != "relationType" else "relationKey", key))
    for application in list(data["applications"]):
        _apply(
            data,
            {
                "kind": "setKey",
                "element": {"applicationKey": application["key"]},
                "key": f"zq-{application['key']}",
            },
        )
    compiled = compile_model(data)
    assert compiled.valid, compiled.diagnostics
    for kind, old in renamed:
        assert references(data, kind, old) == [], (kind, old)
    assert json.dumps(data).count('"zq-') > 0


@pytest.mark.parametrize("model_name", list(MODELS))
def test_a_consumer_api_started_for_any_type_compiles(model_name: str):
    """D53: the definition ``addConsumerApi`` writes is valid for every type of both models."""
    for object_type in MODELS[model_name]["objectTypes"]:
        data = copy.deepcopy(MODELS[model_name])
        _apply(
            data,
            {
                "kind": "addConsumerApi",
                "name": f"Feed of {object_type['name']}",
                "exposes": [object_type["key"]],
            },
        )
        compiled = compile_model(data)
        assert compiled.valid, (object_type["key"], compiled.diagnostics)


def _moves(model: dict[str, Any]) -> Iterator[tuple[str, str, str]]:
    """Every type with the one application listing it and each application that does not."""
    for object_type in model["objectTypes"]:
        listed = [
            a["key"] for a in model["applications"] if object_type["key"] in a["objectTypeKeys"]
        ]
        if len(listed) == 1:
            for application in model["applications"]:
                if application["key"] not in listed:
                    yield object_type["key"], listed[0], application["key"]


def _contained(model: dict[str, Any], parent: str) -> list[str]:
    return [
        t["key"]
        for t in model["objectTypes"]
        for b in model["objectTypeRelations"]
        if b["fromObjectTypeKey"] == parent
        and b["toObjectTypeKey"] == t["key"]
        and b["relationTypeKey"] in ((t.get("behavior") or {}).get("parentRelationTypeKeys") or [])
    ]


@pytest.mark.parametrize("model_name", list(MODELS))
def test_a_type_moved_to_another_application_takes_its_branch_and_keeps_the_draft_valid(
    model_name: str,
):
    """Moving a type between applications was missing (found 2026-10-19): the type and every type
    under it leave the application with their views and detail pages, and the draft stays valid. An
    application left with no type has no default view, as a new empty one."""
    original = MODELS[model_name]
    for type_key, source, target in _moves(original):
        data = copy.deepcopy(original)
        applied = _apply(
            data, {"kind": "setContainment", "objectType": type_key, "application": target}
        )
        apps = {a["key"]: a for a in data["applications"]}
        named = {
            (r["applicationKey"], r.get("view") or (r["detail"], r["panel"]))
            for r in applied.removed
        }
        branch, pending = [], [type_key]
        while pending:
            current = pending.pop()
            if (
                current not in branch
                and current
                in next(a for a in original["applications"] if a["key"] == source)["objectTypeKeys"]
            ):
                branch.append(current)
                pending.extend(_contained(original, current))
        assert set(branch) <= set(apps[target]["objectTypeKeys"]), (type_key, target)
        assert not set(branch) & set(apps[source]["objectTypeKeys"]), (type_key, source)
        # A type's lists go with it, relation columns naming another application's types and all
        # (a list was lost so, found 2026-10-19).
        before = next(a for a in original["applications"] if a["key"] == source)
        arriving = set(branch) - set(
            next(a for a in original["applications"] if a["key"] == target)["objectTypeKeys"]
        )
        for view in before["views"]:
            if view["type"] == "table" and view["objectTypeKey"] in arriving:
                assert any(v == {**view, "key": v["key"]} for v in apps[target]["views"]), (
                    type_key,
                    view["key"],
                )
        # Nothing is lost that can stand somewhere (lists were, found 2026-10-19): a view is kept,
        # perhaps re-keyed, unless it is a matrix whose three types no application lists together.
        members = [set(a["objectTypeKeys"]) for a in data["applications"]]
        kept_views = [
            json.dumps({**v, "key": ""}, sort_keys=True)
            for a in data["applications"]
            for v in a["views"]
        ]
        for view in before["views"]:
            if json.dumps({**view, "key": ""}, sort_keys=True) in kept_views:
                continue
            if view["type"] == "tree":
                # A tree staying behind loses the nodes that moved away, and keeps its top.
                trimmed = next((v for v in apps[source]["views"] if v["key"] == view["key"]), None)
                assert trimmed and set(trimmed["config"]["objectTypeKeys"]) == set(
                    view["config"]["objectTypeKeys"]
                ) - set(branch), (type_key, view["key"])
                continue
            assert view["type"] == "relationMatrix", (type_key, target, view["key"])
            config = view["config"]
            need = {
                config["rowObjectTypeKey"],
                config["columnObjectTypeKey"],
                config["cellObjectTypeKey"],
            }
            assert not any(need <= m for m in members), (type_key, target, view["key"])
            # What could not be kept is said, not dropped in silence.
            assert (source, view["key"]) in named, (type_key, target, view["key"], named)
        for detail in before.get("details", []):
            for panel in detail["panels"]:
                if not any(
                    p["key"] == panel["key"]
                    for a in data["applications"]
                    for d in a.get("details", [])
                    if d["objectTypeKey"] == detail["objectTypeKey"]
                    for p in d["panels"]
                ):
                    assert (source, (detail["objectTypeKey"], panel["key"])) in named, (
                        type_key,
                        target,
                        panel["key"],
                        named,
                    )
        # What stays behind keeps its columns and fields (a panel lost two, found 2026-10-19).
        for detail in before.get("details", []):
            if detail["objectTypeKey"] in branch:
                continue
            kept = {
                p["key"]: p
                for p in next(
                    d
                    for d in apps[source]["details"]
                    if d["objectTypeKey"] == detail["objectTypeKey"]
                )["panels"]
            }
            for panel in detail["panels"]:
                for part in ("columns", "fields", "sortFields"):
                    if panel["key"] in kept and part in (panel.get("config") or {}):
                        assert kept[panel["key"]]["config"].get(part) == panel["config"][part], (
                            type_key,
                            detail["objectTypeKey"],
                            panel["key"],
                            part,
                        )
        compiled = compile_model(data)
        problems = [d for d in compiled.diagnostics if d.severity == "error"]
        if apps[source]["objectTypeKeys"]:
            assert not problems, (type_key, source, target, problems[:2])
        else:
            assert [d.path for d in problems] == [f"/applications/{source}/defaultView"], (
                type_key,
                target,
                problems[:2],
            )


@pytest.mark.parametrize("model_name", list(MODELS))
def test_a_tree_s_top_given_a_parent_keeps_its_tree_valid(model_name: str):
    """A tree's top type put under a parent left the tree naming a top that needs a parent; the draft
    showed the error (found 2026-10-19). The tree grows up to the parent, keeping what it can show."""
    original = MODELS[model_name]
    for application in original["applications"]:
        for view in application["views"]:
            if view["type"] != "tree":
                continue
            root = view["config"]["rootObjectTypeKeys"][0]
            parent = next(
                (
                    t
                    for t in application["objectTypeKeys"]
                    if t not in view["config"]["objectTypeKeys"]
                ),
                None,
            )
            if parent is None:
                continue
            data = copy.deepcopy(original)
            relation = {"name": "Holds", "reverseName": "Held by"}
            _apply(
                data,
                {
                    "kind": "setContainment",
                    "objectType": root,
                    "parent": {"objectTypes": [parent], "relationType": relation},
                },
            )
            tree = f"/applications/{application['key']}/views/{view['key']}"
            compiled = compile_model(data)
            assert not [d for d in compiled.diagnostics if d.path.startswith(tree)], (
                tree,
                compiled.diagnostics[:2],
            )


@pytest.mark.parametrize("model_name", list(MODELS))
def test_a_type_merged_into_its_parent_does_not_contain_itself(model_name: str):
    """A merge turned the containment between the two types into the survivor containing itself, and
    left consumer APIs naming the merged-away type (found 2026-10-19)."""
    original = MODELS[model_name]
    own_hierarchies = {
        b["relationTypeKey"]
        for b in original["objectTypeRelations"]
        if b["fromObjectTypeKey"] == b["toObjectTypeKey"]
    }
    for parent in [t["key"] for t in original["objectTypes"]]:
        for child in [c for c in _contained(original, parent) if c != parent]:
            data = copy.deepcopy(original)
            _apply(data, {"kind": "mergeObjectTypes", "into": parent, "from": child})
            relations = {r["key"]: r for r in data["relationTypes"]}
            assert not [
                b
                for b in data["objectTypeRelations"]
                if b["fromObjectTypeKey"] == b["toObjectTypeKey"] == parent
                and (relations.get(b["relationTypeKey"], {}).get("features") or {}).get("parentOf")
                # A type's own self-hierarchy is inherited, not made by the merge.
                and b["relationTypeKey"] not in own_hierarchies
            ], (parent, child)
            assert references(data, "objectType", child) == [], (parent, child)


CONFIGURATIONS = {"example": example(), "generated-b": generated("b")}


@pytest.mark.parametrize("model_name", list(MODELS))
def test_a_list_whose_column_reaches_another_application_moves_with_its_type(model_name: str):
    """A list of a moving type was left behind, and dropped, when a column reached a type outside the
    branch: a related record's ancestor in another application (found 2026-10-19 on a model's
    means-of-transport list, whose language column reached the translations' languages). It moves as
    authored; the draft stays valid."""
    configuration = CONFIGURATIONS[model_name]
    data = copy.deepcopy(MODELS[model_name])
    type_key, ancestor = configuration.key("R"), configuration.key("G")
    listed = [a for a in data["applications"] if type_key in a["objectTypeKeys"]]
    source = listed[0]
    target = next(a["key"] for a in data["applications"] if type_key not in a["objectTypeKeys"])
    view = next(
        v for v in source["views"] if v["type"] == "table" and v["objectTypeKey"] == type_key
    )
    column = f"related:{configuration.key('Bown')}.ancestor:{ancestor}.name"
    _apply(
        data,
        {
            "kind": "insertViewItem",
            "applicationKey": source["key"],
            "view": view["key"],
            "list": "columns",
            "item": column,
        },
    )
    _apply(
        data,
        {
            "kind": "setViewProperty",
            "applicationKey": source["key"],
            "view": view["key"],
            "property": "pageSize",
            "value": 7,
        },
    )
    assert compile_model(data).valid, compile_model(data).diagnostics[:2]
    authored = copy.deepcopy(
        next(
            v
            for v in next(a for a in data["applications"] if a["key"] == source["key"])["views"]
            if v["key"] == view["key"]
        )
    )
    move = {"kind": "setContainment", "objectType": type_key, "application": target}
    if len(listed) > 1:
        move["fromApplication"] = source["key"]
    _apply(data, move)
    arrived = [
        v
        for v in next(a for a in data["applications"] if a["key"] == target)["views"]
        if v.get("objectTypeKey") == type_key
    ]
    assert any(v == {**authored, "key": v["key"]} for v in arrived), arrived
    compiled = compile_model(data)
    assert not [
        d
        for d in compiled.diagnostics
        if d.severity == "error" and not d.path.endswith("/defaultView")
    ], compiled.diagnostics[:2]


def _example_with_numbers() -> dict[str, Any]:
    data = copy.deepcopy(MODELS["example"])
    type_key = data["objectTypes"][0]["key"]
    data["attributeTypes"].append({"key": "zz-count", "name": "Count", "valueType": "integer"})
    data["attributeTypes"].append({"key": "zz-name", "name": "Name", "valueType": "text"})
    data["objectTypes"][0].setdefault("attributes", []).extend(
        [{"attributeTypeKey": "zz-count"}, {"attributeTypeKey": "zz-name"}]
    )
    data["zz-type"] = type_key
    return data


@pytest.mark.parametrize(
    ("operation", "field", "reason"),
    [
        (
            {
                "kind": "setAttributeTypeProperty",
                "attributeType": "zz-name",
                "property": "minimum",
                "value": 1,
            },
            "property",
            "invalidValue",
        ),
        (
            {
                "kind": "setAttributeTypeProperty",
                "attributeType": "zz-count",
                "property": "minimum",
                "value": "one",
            },
            "value",
            "invalidValue",
        ),
        (
            {
                "kind": "setAttributeTypeProperty",
                "attributeType": "zz-count",
                "property": "minimum",
                "value": True,
            },
            "value",
            "invalidValue",
        ),
        (
            {
                "kind": "setAttributeTypeProperty",
                "attributeType": "zz-count",
                "property": "colour",
                "value": 1,
            },
            "property",
            "unknownElement",
        ),
        (
            {
                "kind": "setAttributeTypeProperty",
                "attributeType": "nope",
                "property": "hidden",
                "value": True,
            },
            "attributeType",
            "unknownElement",
        ),
        (
            {
                "kind": "setAttributeTypeProperty",
                "attributeType": "zz-count",
                "property": "helpText",
                "value": 3,
            },
            "ui/helpText",
            "invalidValue",
        ),
        (
            {
                "kind": "setObjectTypeProperty",
                "property": "displayAttributeTypeKey",
                "value": "zz-unbound",
            },
            "value",
            "unknownElement",
        ),
        (
            {
                "kind": "setObjectTypeProperty",
                "property": "effectivePeriod",
                "value": {"startAttributeTypeKey": "zz-name", "endAttributeTypeKey": "zz-count"},
            },
            "value/startAttributeTypeKey",
            "invalidValue",
        ),
        (
            {
                "kind": "setObjectTypeProperty",
                "property": "atLeastOneOf",
                "value": ["zz-count", "zz-unbound"],
            },
            "value",
            "unknownElement",
        ),
        (
            {
                "kind": "setObjectTypeProperty",
                "property": "atLeastOneOf",
                "value": ["zz-count", "zz-count"],
            },
            "value",
            "invalidValue",
        ),
        (
            {
                "kind": "setObjectTypeProperty",
                "property": "parentRelationTypeKeys",
                "value": ["zz-unknown"],
            },
            "value",
            "unknownElement",
        ),
        (
            {
                "kind": "setRelationTypeProperty",
                "relationType": "{relation}",
                "property": "isOriented",
                "value": "yes",
            },
            "value",
            "invalidValue",
        ),
        (
            {
                "kind": "setApplicationProperty",
                "applicationKey": "{application}",
                "property": "defaultView",
                "value": "no-such-view",
            },
            "value",
            "unknownElement",
        ),
        (
            {
                "kind": "setApplicationProperty",
                "applicationKey": "{application}",
                "property": "state",
                "value": "retired",
            },
            "property",
            "unknownElement",
        ),
    ],
)
def test_a_property_that_does_not_fit_is_refused_with_the_field_at_fault(
    operation: dict[str, Any], field: str, reason: str
):
    data = _example_with_numbers()
    data.pop("zz-type")
    operation = json.loads(
        json.dumps(operation)
        .replace("{relation}", data["relationTypes"][0]["key"])
        .replace("{application}", data["applications"][0]["key"])
    )
    if operation["kind"] == "setObjectTypeProperty":
        operation["objectType"] = data["objectTypes"][0]["key"]
    before = copy.deepcopy(data)
    with pytest.raises(Refusal) as refused:
        _apply(data, operation)
    assert (refused.value.field, refused.value.reason) == (field, reason)
    assert data == before


def test_a_minimum_above_the_maximum_is_refused_and_a_bound_set_is_taken_back_by_its_inverse():
    data = _example_with_numbers()
    original = copy.deepcopy(data)
    _apply(
        data,
        {
            "kind": "setAttributeTypeProperty",
            "attributeType": "zz-count",
            "property": "maximum",
            "value": 5,
        },
    )
    with pytest.raises(Refusal) as refused:
        _apply(
            data,
            {
                "kind": "setAttributeTypeProperty",
                "attributeType": "zz-count",
                "property": "minimum",
                "value": 6,
            },
        )
    assert refused.value.reason == "invalidValue"
    applied = _apply(
        data,
        {
            "kind": "setAttributeTypeProperty",
            "attributeType": "zz-count",
            "property": "minimum",
            "value": 2,
        },
    )
    assert next(a for a in data["attributeTypes"] if a["key"] == "zz-count")["validation"] == {
        "maximum": 5,
        "minimum": 2,
    }
    compile_model(data)
    _apply(data, applied.inverse)
    assert next(a for a in data["attributeTypes"] if a["key"] == "zz-count").get("validation") == {
        "maximum": 5
    }
    _apply(
        data,
        {
            "kind": "setAttributeTypeProperty",
            "attributeType": "zz-count",
            "property": "maximum",
            "value": None,
        },
    )
    assert data["attributeTypes"] == original["attributeTypes"]


def test_the_type_properties_compile_and_a_parent_relationship_change_needs_a_migration_once_released():
    data = _example_with_numbers()
    type_key = data["objectTypes"][0]["key"]
    for property_name, value in (
        ("displayAttributeTypeKey", "zz-name"),
        ("atLeastOneOf", ["zz-count", "zz-name"]),
    ):
        _apply(
            data,
            {
                "kind": "setObjectTypeProperty",
                "objectType": type_key,
                "property": property_name,
                "value": value,
            },
        )
    compile_model(data)
    parents = next(
        t for t in data["objectTypes"] if (t.get("behavior") or {}).get("parentRelationTypeKeys")
    )
    document = Document(data)
    context = Context(document, lambda atom: atom == f"objectType:{parents['key']}")
    apply_operation(
        context,
        {
            "kind": "setObjectTypeProperty",
            "objectType": parents["key"],
            "property": "parentRelationTypeKeys",
            "value": None,
        },
    )
    assert context.take_marks() == [(f"objectType:{parents['key']}", False)]
