"""What a model draft changes, read from the draft's model against the model it was drafted on.

The assistant may reach its draft by any steps (a single ``replaceModel`` among them), so the page
reads the result, not the steps: the changes come out in the vocabulary of the draft operations
(``addObjectType``, ``attachAttribute``, ``allowRelation``…), the same whichever way the draft was
made. Views and layout are not model changes a steward reviews here and are left out."""

from typing import Any

_TYPE_FIELDS = ("name", "pluralName", "description", "icon", "displayAttributeTypeKey")


def _by_key(model: dict[str, Any], section: str) -> dict[str, dict[str, Any]]:
    return {item["key"]: item for item in model.get(section) or [] if item.get("key")}


def _relations(model: dict[str, Any]) -> dict[tuple[str, str, str], dict[str, Any]]:
    return {
        (r.get("relationTypeKey"), r.get("fromObjectTypeKey"), r.get("toObjectTypeKey")): r
        for r in model.get("objectTypeRelations") or []
    }


def model_changes(base: dict[str, Any], model: dict[str, Any]) -> list[dict[str, Any]]:
    """The draft operations that lead from ``base`` to ``model``, in the order the page reads them."""
    out: list[dict[str, Any]] = []
    applications, old_applications = _by_key(model, "applications"), _by_key(base, "applications")
    for key, item in applications.items():
        if key not in old_applications:
            out.append(
                {
                    "kind": "addApplication",
                    "key": key,
                    "name": item.get("name") or key,
                    "description": item.get("description") or "",
                }
            )
    attribute_types, old_attribute_types = (
        _by_key(model, "attributeTypes"),
        _by_key(base, "attributeTypes"),
    )
    for key, item in attribute_types.items():
        if key not in old_attribute_types:
            out.append({"kind": "addAttributeType", "key": key, "name": item.get("name") or key})
    relation_types, old_relation_types = (
        _by_key(model, "relationTypes"),
        _by_key(base, "relationTypes"),
    )
    for key, item in relation_types.items():
        if key not in old_relation_types:
            out.append(
                {
                    "kind": "addRelationType",
                    "key": key,
                    "name": item.get("name") or key,
                    "reverseName": item.get("reverseName") or "",
                }
            )
    allowed, old_allowed = _relations(model), _relations(base)
    parents = {
        to: source
        for (relation, source, to) in allowed
        if (relation_types.get(relation, {}).get("features") or {}).get("parentOf")
    }
    homes = {
        type_key: app_key
        for app_key, app in applications.items()
        for type_key in app.get("objectTypeKeys") or []
    }
    types, old_types = _by_key(model, "objectTypes"), _by_key(base, "objectTypes")
    for key, item in types.items():
        old = old_types.get(key)
        if old is None:
            out.append(
                {
                    "kind": "addObjectType",
                    "key": key,
                    "name": item.get("name") or key,
                    "pluralName": item.get("pluralName") or "",
                    "applicationKey": homes.get(key) or "",
                    "parent": parents.get(key),
                }
            )
        else:
            fields = [f for f in _TYPE_FIELDS if (item.get(f) or None) != (old.get(f) or None)]
            if fields:
                out.append({"kind": "changeObjectType", "objectType": key, "fields": fields})
        bound = {b.get("attributeTypeKey"): b for b in item.get("attributes") or []}
        was = {b.get("attributeTypeKey") for b in (old or {}).get("attributes") or []}
        for attribute, binding in bound.items():
            if attribute not in was:
                out.append(
                    {
                        "kind": "attachAttribute",
                        "objectType": key,
                        "attributeType": attribute,
                        "required": bool(binding.get("required")),
                    }
                )
        if old is not None:
            kept = {b.get("attributeTypeKey"): b for b in old.get("attributes") or []}
            for attribute, binding in bound.items():
                before = kept.get(attribute)
                if before is not None and bool(before.get("required")) != bool(
                    binding.get("required")
                ):
                    out.append(
                        {
                            "kind": "changeAttachment",
                            "objectType": key,
                            "attributeType": attribute,
                            "required": bool(binding.get("required")),
                        }
                    )
        for attribute in was - bound.keys():
            out.append({"kind": "detachAttribute", "objectType": key, "attributeType": attribute})
    for key in old_types.keys() - types.keys():
        out.append({"kind": "removeObjectType", "objectType": key})
    for key in old_attribute_types.keys() - attribute_types.keys():
        out.append({"kind": "removeAttributeType", "attributeType": key})
    for key in old_relation_types.keys() - relation_types.keys():
        out.append({"kind": "removeRelationType", "relationType": key})
    for key in old_applications.keys() - applications.keys():
        out.append({"kind": "removeApplication", "applicationKey": key})
    for (relation, source, target), item in allowed.items():
        old = old_allowed.get((relation, source, target))
        if old is None or old.get("cardinality") != item.get("cardinality"):
            out.append(
                {
                    "kind": "allowRelation",
                    "relationType": relation,
                    "from": source,
                    "to": target,
                    "cardinality": item.get("cardinality"),
                }
            )
    return out
