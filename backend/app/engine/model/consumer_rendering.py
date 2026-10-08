"""A consumer API definition written out in the schema 0.9 vocabulary with every default (Base 0.9
C18, C-D137): what ``GET /api/v1/model/consumer-apis/{consumerApi}`` answers, for a 0.8 release as
for a 0.9 one. Expanding what this writes gives the same internal definition back.
"""

from typing import Any

from ...models.schema import (
    OBJECT_ROLES,
    AncestorParameter,
    ConsumerApiDefinition,
    ConsumerApiDocument,
    ConsumerEvent,
    EngineModel,
    ObjectTypeParameter,
    ProjectionParameter,
    RelatedParameter,
)
from .consumer_expansion import authored_through


def expanded_definition(model: EngineModel, definition: ConsumerApiDefinition) -> dict[str, Any]:
    described = definition.described
    document: dict[str, Any] = {"key": definition.key, "name": definition.name}
    if definition.description is not None:
        document["description"] = definition.description
    document["contractVersion"] = definition.contractVersion
    document["exposes"] = list(definition.objectTypes)
    document["publicNames"] = {key: item.publicName for key, item in definition.objectTypes.items()}
    document["object"] = _object(model, definition)
    operations: dict[str, Any] = {}
    for name in ("objects", "xref", "resolve"):
        if definition.offers(name):
            operations[name] = _with(described(f"operation:{name}"))
    if "xref" in operations and definition.match is not None:
        operations["xref"]["matchOn"] = [rule.model_dump(mode="json") for rule in definition.match.own]
        operations["xref"]["alsoMatchThrough"] = [
            {
                "related": item.projection,
                "firstOf": [rule.model_dump(mode="json") for rule in item.firstMatch],
                "preferTypes": list(item.preferTargetTypes),
            }
            for item in definition.match.promoted
        ]
    if definition.lists:
        operations["lists"] = {
            item.key: {
                "of": item.objectType,
                **(
                    {"within": {"filter": item.parentParameter.name, "types": list(item.parentParameter.objectTypes)}}
                    if item.parentParameter is not None
                    else {}
                ),
                **({"sortBy": item.sortBy} if item.sortBy is not None else {}),
                **_with(described(f"list:{item.key}")),
            }
            for item in definition.lists
        }
    if definition.events:
        operations["events"] = {
            "perType": False,
            "custom": [_event(event) for event in definition.events],
            **_with(described("operation:events")),
        }
    document["operations"] = operations
    document["filters"] = {
        name: {**_filter(parameter), **_with(described(f"filter:{name}"))}
        for name, parameter in definition.parameters.items()
    }
    ConsumerApiDocument.model_validate(document)
    return document


def _object(model: EngineModel, definition: ConsumerApiDefinition) -> dict[str, Any]:
    shape = definition.object
    fields: dict[str, Any] = {}
    for role in OBJECT_ROLES:
        field = getattr(shape, role)
        if field is not None:
            fields[field.output] = {"role": role, **_sources(definition, field.output, field.source, field.default)}
    for name, attribute in shape.attributes.items():
        fields[name] = _sources(definition, name, attribute.source, attribute.default)
    result: dict[str, Any] = {"fields": fields}
    if shape.parent is not None:
        result["parent"] = {"output": shape.parent.output, "fields": list(shape.parent.fields)}
    for part in ("path", "hierarchy"):
        if getattr(shape, part) is not None:
            result[part] = getattr(shape, part)
    result["related"] = {
        name: {
            "via": _via(model, projection.from_.relation, projection.from_.direction),
            "fields": dict(projection.fields),
            **_with(definition.described(f"related:{name}")),
        }
        for name, projection in definition.projections.items()
    }
    return result


def _sources(definition: ConsumerApiDefinition, output: str, sources: tuple[str, ...], default: Any) -> dict[str, Any]:
    return {
        "from": list(sources),
        **({"default": default} if default is not None else {}),
        **_with(definition.described(f"field:{output}")),
    }


def _via(model: EngineModel, relation: str, direction: str) -> str:
    if direction == "outgoing":
        return relation
    declared = model.relation_type(relation)
    return declared.reverseKey if declared is not None else relation


def _filter(parameter: Any) -> dict[str, Any]:
    if isinstance(parameter, ObjectTypeParameter):
        return {"byType": True}
    if isinstance(parameter, AncestorParameter):
        return {"under": list(parameter.objectTypes), "matchOn": list(parameter.matchFields)}
    if isinstance(parameter, RelatedParameter):
        return {
            "linkedTo": list(parameter.objectTypes),
            "through": [authored_through(item) for item in parameter.via],
            "matchOn": list(parameter.matchFields),
        }
    assert isinstance(parameter, ProjectionParameter)
    return {
        "onRelated": parameter.projection,
        "matchOn": list(parameter.matchFields),
        "keepOnlyMatching": parameter.requireMatch,
        "scoreOnlyMatching": parameter.scoresFrom,
        "crosswalk": parameter.targetable,
    }


def _event(event: ConsumerEvent) -> dict[str, Any]:
    item: dict[str, Any] = {"key": event.key, "objectTypes": list(event.objectTypes), "changes": list(event.changes)}
    if event.watch is not None:
        item["watch"] = {"fields": list(event.watch.fields), "related": list(event.watch.projections)}
    return item


def _with(description: str | None) -> dict[str, Any]:
    return {"description": description} if description else {}
