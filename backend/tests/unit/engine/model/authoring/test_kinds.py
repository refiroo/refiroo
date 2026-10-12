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
from app.engine.model.authoring.kinds import Context, MigrationRequired, apply_operation
from app.engine.model.compiler import compile_model

MODELS = {"example": example().model, "generated-b": generated("b").model}


def _operations(model: dict[str, Any]) -> Iterator[dict[str, Any]]:
    """Operations of every kind over the model's elements."""
    types = [t["key"] for t in model["objectTypes"]]
    for application in model["applications"]:
        app = application["key"]
        yield {"kind": "setLabel", "element": {"applicationKey": app}, "name": "Renamed"}
        yield {"kind": "setKey", "element": {"applicationKey": app}, "key": "zz-app"}
        yield {"kind": "addNavigationGroup", "applicationKey": app, "label": "Group", "collections": []}
        yield {"kind": "addObjectType", "applicationKey": app, "name": "Zz", "pluralName": "Zzs", "parent": None}
        for view in application["views"]:
            yield {"kind": "removeView", "applicationKey": app, "view": view["key"]}
            yield {"kind": "setKey", "element": {"applicationKey": app, "view": view["key"]}, "key": "zz-view"}
            yield {"kind": "setViewProperty", "applicationKey": app, "view": view["key"], "property": "pageSize", "value": 7}
            if view["type"] == "table":
                columns = view["config"]["columns"]
                yield {"kind": "removeViewItem", "applicationKey": app, "view": view["key"], "list": "columns", "item": columns[-1]}
                if len(columns) > 1:
                    yield {"kind": "moveViewItem", "applicationKey": app, "view": view["key"], "list": "columns", "item": columns[-1], "position": 0}
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
            for panel in detail["panels"]:
                yield {"kind": "removeViewItem", "applicationKey": app, "detail": detail["objectTypeKey"], "list": "panels", "item": panel["key"]}
                yield {"kind": "setViewProperty", "applicationKey": app, "detail": detail["objectTypeKey"], "panel": panel["key"], "property": "visible", "value": False}
    for type_key in types:
        yield {"kind": "setLabel", "element": {"objectType": type_key}, "pluralName": "Others"}
        yield {"kind": "setKey", "element": {"objectType": type_key}, "key": "zz-type"}
        yield {"kind": "removeObjectType", "objectType": type_key}
        yield {"kind": "setContainment", "objectType": type_key, "parent": None}
        yield {"kind": "allowRelation", "relationType": model["relationTypes"][0]["key"], "from": type_key, "to": types[0]}
        bindings = [b["attributeTypeKey"] for b in next(t for t in model["objectTypes"] if t["key"] == type_key).get("attributes", [])]
        for attribute in bindings:
            yield {"kind": "detachAttribute", "objectType": type_key, "attributeType": attribute}
            yield {"kind": "setAttributeBinding", "objectType": type_key, "attributeType": attribute, "required": True, "position": 0}
            yield {
                "kind": "convertAttributeToListType",
                "objectType": type_key,
                "attributeType": attribute,
                "name": "Zz list",
                "relationType": {"name": "Has zz", "reverseName": "Zz of"},
            }
            other = next((t for t in types if t != type_key), None)
            if other:
                yield {"kind": "moveAttribute", "attributeType": attribute, "from": type_key, "to": other}
        if bindings:
            yield {
                "kind": "splitObjectType",
                "objectType": type_key,
                "name": "Zz part",
                "attributes": bindings[:1],
                "relationType": {"name": "Has part", "reverseName": "Part of"},
            }
        yield {"kind": "addObjectType", "applicationKey": model["applications"][0]["key"], "name": "Zz child", "pluralName": "Zz children", "parent": {"objectTypes": [type_key], "relationType": {"name": "Holds", "reverseName": "Held by"}}}
    for first, second in pairwise(types):
        yield {"kind": "mergeObjectTypes", "into": first, "from": second}
    for attribute in model["attributeTypes"]:
        yield {"kind": "setLabel", "element": {"attributeType": attribute["key"]}, "name": "Other"}
        yield {"kind": "setKey", "element": {"attributeType": attribute["key"]}, "key": "zz-attribute"}
        yield {"kind": "setAttributeTypeFeatures", "attributeType": attribute["key"], "features": {"searchable": True, "unique": None}}
        yield {"kind": "setValueType", "attributeType": attribute["key"], "valueType": "longText"}
        for type_key in types[:2]:
            yield {"kind": "attachAttribute", "objectType": type_key, "attributeType": attribute["key"]}
    for relation in model["relationTypes"]:
        yield {"kind": "setKey", "element": {"relationType": relation["key"]}, "key": "zz-rel", "reverseKey": "zz-rel-back"}
    for binding in model["objectTypeRelations"]:
        triple = {"relationType": binding["relationTypeKey"], "from": binding["fromObjectTypeKey"], "to": binding["toObjectTypeKey"]}
        yield {"kind": "disallowRelation", **triple}
        yield {"kind": "setRelationRule", **triple, "required": not binding.get("required", False)}
    yield {"kind": "addAttributeType", "name": "Zz attribute", "valueType": "integer"}
    yield {"kind": "addRelationType", "name": "Zz rel", "reverseName": "Zz rel back"}
    yield {"kind": "setRelease", "version": "9.9.9", "schemaVersion": "0.10"}
    yield from _consumer_operations(model)


def _consumer_operations(model: dict[str, Any]) -> Iterator[dict[str, Any]]:
    """The consumer API kinds over every part of every definition: each member and item set to
    itself, moved first, removed, and a copy inserted under a new key or at the start."""
    types = [t["key"] for t in model["objectTypes"]]
    yield {"kind": "addConsumerApi", "name": "Zz feed", "exposes": types[:2]}
    for definition in model.get("consumerApis", []):
        api = definition["key"]
        yield {"kind": "removeConsumerApi", "consumerApi": api}
        yield {"kind": "setConsumerApiPart", "consumerApi": api, "pointer": "", "value": definition}
        yield {"kind": "setConsumerApiPart", "consumerApi": api, "pointer": "/contractVersion", "value": 9}
        yield {"kind": "setConsumerApiPart", "consumerApi": api, "pointer": "/key", "value": "zz-api"}
        for pointer, node in _parts(definition, ""):
            yield {"kind": "setConsumerApiPart", "consumerApi": api, "pointer": pointer, "value": node}
            yield {"kind": "removeConsumerApiPart", "consumerApi": api, "pointer": pointer}
            yield {"kind": "moveConsumerApiPart", "consumerApi": api, "pointer": pointer, "position": 0}
            container, _, last = pointer.rpartition("/")
            if last.isdigit():
                yield {"kind": "insertConsumerApiPart", "consumerApi": api, "pointer": container, "value": node, "position": 0}
            else:
                yield {"kind": "insertConsumerApiPart", "consumerApi": api, "pointer": container, "key": f"zz{last}", "value": node, "position": 0}


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
def test_an_operation_and_then_its_inverse_return_the_document(model_name: str, operation: dict[str, Any]):
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


def test_a_draft_only_kind_on_a_released_element_is_refused_before_anything_changes():
    data = copy.deepcopy(MODELS["example"])
    type_key = data["objectTypes"][0]["key"]
    document = Document(data)
    with pytest.raises(MigrationRequired) as refused:
        apply_operation(Context(document, lambda atom: atom == f"objectType:{type_key}"), {"kind": "removeObjectType", "objectType": type_key})
    assert refused.value.element == f"objectType:{type_key}"
    assert document.log == []
    assert data == MODELS["example"]


def test_which_records_a_released_relationship_may_choose_changes_without_a_migration():
    """``candidates`` is compatible in a release (0.9 K7): set on a released binding, it applies;
    its cardinality on the same binding still needs a migration (found in A4a)."""
    data = copy.deepcopy(MODELS["example"])
    binding = data["objectTypeRelations"][0]
    triple = {"relationType": binding["relationTypeKey"], "from": binding["fromObjectTypeKey"], "to": binding["toObjectTypeKey"]}
    released = lambda atom: atom.startswith("relationBinding:")
    criteria = {"to": [{"field": "name", "op": "startsWith", "value": "A"}]}
    before = copy.deepcopy(binding.get("candidates"))
    applied = apply_operation(Context(Document(data), released), {"kind": "setRelationRule", **triple, "candidates": criteria})
    assert data["objectTypeRelations"][0]["candidates"] == criteria
    assert applied.inverse["candidates"] == before
    with pytest.raises(MigrationRequired):
        apply_operation(Context(Document(data), released), {"kind": "setRelationRule", **triple, "cardinality": "one-to-one"})


def test_every_key_of_the_example_renamed_keeps_it_valid_and_leaves_no_old_reference():
    data = copy.deepcopy(MODELS["example"])
    renamed: list[tuple[str, str]] = []
    for kind, collection in (("objectType", "objectTypes"), ("attributeType", "attributeTypes"), ("relationType", "relationTypes")):
        for key, reverse in [(item["key"], item.get("reverseKey")) for item in data[collection]]:
            operation: dict[str, Any] = {"kind": "setKey", "element": {kind: key}, "key": f"zq-{key}"}
            if kind == "relationType":
                operation["reverseKey"] = f"zq-{reverse}"
                renamed.append(("relationKey", reverse))
            _apply(data, operation)
            renamed.append((kind if kind != "relationType" else "relationKey", key))
    for application in list(data["applications"]):
        _apply(data, {"kind": "setKey", "element": {"applicationKey": application["key"]}, "key": f"zq-{application['key']}"})
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
        _apply(data, {"kind": "addConsumerApi", "name": f"Feed of {object_type['name']}", "exposes": [object_type["key"]]})
        compiled = compile_model(data)
        assert compiled.valid, (object_type["key"], compiled.diagnostics)
