"""``engine/model/authoring/profile_side.py``: a draft's import profile follows its model (0.10 A5, D78).

Over every element of two models (the example model and generated-b), a profile is generated
that maps a column to each attribute a type binds, a parent column to each parent it may have and
a relation column to each relation it may hold. Each model kind that renames, moves or removes
something is applied with that profile: afterwards nothing in the profile names an element the
model no longer declares (it was renamed, moved or kept as unmapped), and the kind's inverse puts
back the model and the profile whole.
"""

import copy
from collections.abc import Iterator
from typing import Any

import pytest
from configurations import example, generated

from app.engine.model.authoring.document import PROFILE, PROFILE_IDENTITIES, Document, Refusal
from app.engine.model.authoring.kinds import Context, apply_operation
from app.engine.model.authoring.profile_side import binding_resolves, facts

MODELS = {"example": example().model, "generated-b": generated("b").model}


def _profile(model: dict[str, Any]) -> dict[str, Any]:
    known = facts(model)
    sources = []
    for app in model["applications"]:
        for type_key in app["objectTypeKeys"]:
            columns: list[dict[str, Any]] = [{"column": "name", "field": "name"}]
            columns += [{"column": f"a-{a}", "attributeTypeKey": a} for a in sorted(known.types.get(type_key, ()))]
            columns += [
                {"column": f"p-{p}", "parent": {"objectTypeKey": p, "matchBy": {"field": "name"}}}
                for p in sorted(known.parents.get(type_key, ()))
            ]
            columns += [
                {"column": f"r-{r}-{to}", "relation": {"relationTypeKey": r, "objectTypeKey": to, "matchBy": {"field": "name"}}}
                for r, source, to in sorted(known.relations)
                if source == type_key
            ]
            sources.append({"id": f"{app['key']}-{type_key}", "sheet": "S", "applicationKey": app["key"], "objectTypeKey": type_key, "columns": columns})
    return {"key": "generated", "name": "Generated", "sources": sources, "valueMaps": {}}


def _operations(model: dict[str, Any]) -> Iterator[dict[str, Any]]:
    types = [t["key"] for t in model["objectTypes"]]
    for app in model["applications"]:
        yield {"kind": "setKey", "element": {"applicationKey": app["key"]}, "key": "zz-app"}
    for item in model["objectTypes"]:
        key = item["key"]
        yield {"kind": "setKey", "element": {"objectType": key}, "key": "zz-type"}
        yield {"kind": "removeObjectType", "objectType": key}
        yield {"kind": "setContainment", "objectType": key, "parent": None}
        others = [t for t in types if t != key]
        if others:
            yield {"kind": "mergeObjectTypes", "into": others[0], "from": key}
        bound = [b["attributeTypeKey"] for b in item.get("attributes") or []]
        for attribute in bound:
            yield {"kind": "detachAttribute", "objectType": key, "attributeType": attribute}
            yield {"kind": "convertAttributeToListType", "objectType": key, "attributeType": attribute, "name": "Zz list", "relationType": {"name": "Zz", "reverseName": "Zz of"}}
            for other in others[:2]:
                yield {"kind": "moveAttribute", "attributeType": attribute, "from": key, "to": other}
        if bound:
            yield {"kind": "splitObjectType", "objectType": key, "name": "Zz part", "attributes": bound[:1], "relationType": {"name": "Zz", "reverseName": "Zz of"}}
    for attribute in model["attributeTypes"]:
        yield {"kind": "setKey", "element": {"attributeType": attribute["key"]}, "key": "zz-attribute"}
    for relation in model["relationTypes"]:
        yield {"kind": "setKey", "element": {"relationType": relation["key"]}, "key": "zz-relation"}
    for binding in model["objectTypeRelations"]:
        yield {"kind": "disallowRelation", "relationType": binding["relationTypeKey"], "from": binding["fromObjectTypeKey"], "to": binding["toObjectTypeKey"]}


def _cases() -> Iterator[Any]:
    for name, model in MODELS.items():
        for index, operation in enumerate(_operations(model)):
            yield pytest.param(name, operation, id=f"{name}-{index}-{operation['kind']}")


def _context(model: dict[str, Any], profile: dict[str, Any]) -> Context:
    document = Document(model)
    return Context(document, lambda _atom: False, Document(profile, name=PROFILE, identities=PROFILE_IDENTITIES, log=document.log))


@pytest.mark.parametrize(("model_name", "operation"), list(_cases()))
def test_the_profile_names_only_what_the_model_declares_and_the_inverse_restores_both(model_name: str, operation: dict[str, Any]):
    model = copy.deepcopy(MODELS[model_name])
    profile = _profile(model)
    original = (copy.deepcopy(model), copy.deepcopy(profile))
    try:
        applied = apply_operation(_context(model, profile), operation)
    except Refusal as refusal:
        assert refusal.reason, refusal.message
        return
    known = facts(model)
    for source in profile["sources"]:
        assert source["objectTypeKey"] in known.applications.get(source["applicationKey"], set()), source
        for binding in source["columns"]:
            assert binding_resolves(known, source, binding), (operation["kind"], source["id"], binding)
    apply_operation(_context(model, profile), applied.inverse)
    assert (model, profile) == original, f"{operation} then {applied.inverse['kind']}"
