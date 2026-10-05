"""A consumer API definition's output contract, and the breaking-change check (Base 0.9 C1).

A definition's contract is what its consumers depend on: the exposed types and their public names,
the output fields and their value types, each projection's shape and fields, the scoring weights, the
lists and the parameters (CONSUMER_API C-D2, C-D4, C-D18). :func:`output_contract` derives it from a
definition and its release; model validation uses the same field resolution for its type rules, so
the checked contract and the validated one cannot drift apart.

:func:`contract_diagnostics` compares a candidate release with the active one, which is what
consumers read (C-D17). A definition whose contract loses or changes anything its consumers read
needs a higher ``contractVersion``; removing a whole definition is a warning (C-D18).
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any

from ...common.json_pointer import pointer_segment
from ...models.schema import (
    ConsumerApiDefinition,
    ConsumerField,
    EngineModel,
    ObjectTypeDefinition,
    ProjectionParameter,
)
from .diagnostics import ModelDiagnostic
from .traversal import ancestor_type_keys, related_object_types

# Built-in fields a source, projection field or match rule may name, and their value types.
BUILT_IN_FIELDS = {"id": "text", "name": "text"}
# A projection field's source naming the related record's public type name (C-D73).
PROJECTION_TYPE_SOURCE = "objectType"
ANCESTOR_REFERENCE_PREFIX = "ancestor:"
# Roles of the shared object, in output order.
OBJECT_ROLES = ("id", "code", "name", "active", "validFrom", "validTo")
# Value types that compare as one output type (C-D19).
_TEXT_TYPES = {"text", "longText"}

BREAKING = "CONSUMER_CONTRACT_VERSION_REQUIRED"


def output_type(value_type: str) -> str:
    """The output type of a value type: ``text`` and ``longText`` are one type."""
    return "text" if value_type in _TEXT_TYPES else value_type


def binding_types(
    types: Iterable[ObjectTypeDefinition], attribute_type_key: str
) -> list[ObjectTypeDefinition]:
    """The types among ``types`` that bind the attribute."""
    return [
        item
        for item in types
        if any(binding.attributeTypeKey == attribute_type_key for binding in item.attributes)
    ]


def field_value_type(
    model: EngineModel, types: Sequence[ObjectTypeDefinition], field: str
) -> str | None:
    """The output type of a built-in field or an attribute one of ``types`` binds; else ``None``."""
    if field in BUILT_IN_FIELDS:
        return BUILT_IN_FIELDS[field]
    definition = model.attribute_type(field)
    if definition is None or not binding_types(types, field):
        return None
    return output_type(definition.valueType)


def split_ancestor_reference(field: str) -> tuple[str, str] | None:
    """``ancestor:<type>.<field>`` as ``(type, field)``, or ``None`` for another field."""
    if not field.startswith(ANCESTOR_REFERENCE_PREFIX):
        return None
    type_key, separator, name = field.removeprefix(ANCESTOR_REFERENCE_PREFIX).partition(".")
    return (type_key, name) if separator and type_key and name else ("", "")


def reference_value_type(
    model: EngineModel, types: Sequence[ObjectTypeDefinition], field: str
) -> str | None:
    """The output type of a field of ``types`` or of one of their ancestors; else ``None``.

    ``ancestor:<type>.<field>`` reads ``field`` of the ancestor of ``type``, which one of ``types``
    must be able to sit under.
    """
    reference = split_ancestor_reference(field)
    if reference is None:
        return field_value_type(model, types, field)
    type_key, name = reference
    ancestor = model.object_type(type_key)
    if ancestor is None or not any(type_key in ancestor_type_keys(model, item.key) for item in types):
        return None
    return field_value_type(model, (ancestor,), name)


def projection_field_type(
    model: EngineModel,
    definition: ConsumerApiDefinition,
    targets: Sequence[ObjectTypeDefinition],
    source: str,
) -> str | None:
    """The output type of a projection field's source, or ``None`` when it does not resolve.

    ``objectType`` is the related record's public type name, so it resolves only where the definition
    exposes every type the projection reaches; another type has no public name (C-D73).
    """
    if source == PROJECTION_TYPE_SOURCE:
        exposed = bool(targets) and all(item.key in definition.objectTypes for item in targets)
        return "text" if exposed else None
    return reference_value_type(model, targets, source)


def exposed_types(model: EngineModel, definition: ConsumerApiDefinition) -> list[ObjectTypeDefinition]:
    return [item for key in definition.objectTypes if (item := model.object_type(key)) is not None]


def projection_targets(
    model: EngineModel, definition: ConsumerApiDefinition, relation: str, direction: str
) -> list[ObjectTypeDefinition]:
    """The types at the other end of the route from any exposed type."""
    found: dict[str, ObjectTypeDefinition] = {}
    for item in exposed_types(model, definition):
        for target in related_object_types(model, item.key, direction, [relation]):
            found.setdefault(target.key, target)
    return list(found.values())


def projection_shape(
    model: EngineModel, definition: ConsumerApiDefinition, relation: str, direction: str
) -> str:
    """``one`` when every binding of the route allows at most one related object, else ``many``.

    Derived, never declared, so a cardinality change in the model is a contract change the check sees.
    """
    exposed = set(definition.objectTypes)
    single = True
    for binding in model.objectTypeRelations:
        if binding.relationTypeKey != relation:
            continue
        own = binding.fromObjectTypeKey if direction == "outgoing" else binding.toObjectTypeKey
        if own not in exposed:
            continue
        at_most_one = binding.cardinality == "one-to-one" or (
            binding.cardinality == "one-to-many" and direction == "incoming"
        )
        single = single and at_most_one
    return "one" if single else "many"


def parent_keys(definition: ConsumerApiDefinition) -> dict[str, str]:
    """Each field the ``parent`` lists, by the key it has in the answer: a role's output name, as
    the object's own field has it (C-D75), and ``objectType`` as itself. A role the object does not
    declare keeps its role name."""
    shape = definition.object
    assert shape.parent is not None
    keys = {}
    for name in shape.parent.fields:
        role: ConsumerField | None = None if name == "objectType" else getattr(shape, name)
        keys[name] = name if role is None else role.output
    return keys


def source_type(
    model: EngineModel, types: Sequence[ObjectTypeDefinition], sources: Sequence[str]
) -> str | None:
    """The shared output type of a field's sources (C-D19), or ``None`` when they differ."""
    found = {field_value_type(model, types, source) for source in sources}
    return found.pop() if len(found) == 1 and None not in found else None


@dataclass(frozen=True)
class OutputContract:
    """What a definition's consumers read, keyed for comparison."""

    types: dict[str, str]
    fields: dict[str, Any]
    projections: dict[str, dict[str, Any]]
    match: Any
    lists: dict[str, dict[str, Any]]
    parameters: dict[str, str]
    # The ``projection`` parameters declaring ``scoresFrom``, which changes ranking (C-D46).
    scores_from: frozenset[str] = frozenset()
    # The ``projection`` parameters declaring ``targetable``, which consumers read ``to.`` names of
    # (C-D58).
    targetable: frozenset[str] = frozenset()
    # Exposed types that declare an effective period, on which ``asOf`` filters (Base 0.9 Q4).
    as_of: frozenset[str] = frozenset()


def output_contract(model: EngineModel, definition: ConsumerApiDefinition) -> OutputContract:
    """The contract of a definition that validation has accepted against ``model``."""
    types = exposed_types(model, definition)
    shape = definition.object
    fields: dict[str, Any] = {}
    role_types: dict[str, str | None] = {}
    for role in OBJECT_ROLES:
        field: ConsumerField | None = getattr(shape, role)
        if field is not None:
            role_types[role] = source_type(model, types, field.source)
            fields[field.output] = role_types[role]
    for name, attribute in shape.attributes.items():
        fields[name] = source_type(model, types, attribute.source)
    if shape.parent is not None:
        parent_types = {
            "objectType": "text",
            "id": role_types.get("id"),
            "code": role_types.get("code"),
            "name": role_types.get("name", "text"),
        }
        fields[shape.parent.output] = {
            "object": {key: parent_types[name] for name, key in parent_keys(definition).items()}
        }
    if shape.path is not None:
        fields[shape.path] = "text"
    if shape.hierarchy is not None:
        fields[shape.hierarchy] = "text[]"

    projections = {}
    for name, projection in definition.projections.items():
        route = projection.from_
        targets = projection_targets(model, definition, route.relation, route.direction)
        projections[name] = {
            "shape": projection_shape(model, definition, route.relation, route.direction),
            "fields": {
                output: projection_field_type(model, definition, targets, source)
                for output, source in projection.fields.items()
            },
        }
    return OutputContract(
        types={key: item.publicName for key, item in definition.objectTypes.items()},
        fields=fields,
        projections=projections,
        match=None if definition.match is None else definition.match.model_dump(mode="json"),
        lists={
            item.key: {
                "objectType": item.objectType,
                "sortBy": item.sortBy,
                "parent": None
                if item.parentParameter is None
                else {
                    "name": item.parentParameter.name,
                    "objectTypes": sorted(item.parentParameter.objectTypes),
                },
            }
            for item in definition.lists
        },
        parameters={name: parameter.kind for name, parameter in definition.parameters.items()},
        scores_from=frozenset(
            name
            for name, parameter in definition.parameters.items()
            if isinstance(parameter, ProjectionParameter) and parameter.scoresFrom
        ),
        targetable=frozenset(
            name
            for name, parameter in definition.parameters.items()
            if isinstance(parameter, ProjectionParameter) and parameter.targetable
        ),
        as_of=frozenset(item.key for item in types if item.effectivePeriod is not None),
    )


def contract_diagnostics(active: EngineModel, candidate: EngineModel) -> list[ModelDiagnostic]:
    """Breaking changes in ``candidate``'s definitions against ``active``'s (C-D17, C-D18).

    An error for each change a definition's consumers would notice without a higher
    ``contractVersion``, and a warning for each definition ``candidate`` no longer declares.
    """
    before = {item.key: item for item in active.consumerApis or ()}
    after = {item.key: item for item in candidate.consumerApis or ()}
    diagnostics: list[ModelDiagnostic] = []
    for key in sorted(set(before) - set(after)):
        diagnostics.append(
            ModelDiagnostic(
                severity="warning",
                code="CONSUMER_API_REMOVED",
                path=f"/consumerApis/{pointer_segment(key)}",
                message=(
                    f"Consumer API '{key}' is removed; its consumers will receive 404 from"
                    f" /api/consumer/{key}"
                ),
            )
        )
    for key in sorted(set(before) & set(after)):
        old, new = before[key], after[key]
        base = f"/consumerApis/{pointer_segment(key)}"
        if new.contractVersion > old.contractVersion:
            continue
        if new.contractVersion < old.contractVersion:
            diagnostics.append(
                ModelDiagnostic(
                    severity="error",
                    code="CONSUMER_CONTRACT_VERSION_DECREASED",
                    path=f"{base}/contractVersion",
                    message=(
                        f"Consumer API '{key}' lowers contractVersion from {old.contractVersion}"
                        f" to {new.contractVersion}"
                    ),
                )
            )
            continue
        changes = _breaking_changes(output_contract(active, old), output_contract(candidate, new))
        diagnostics.extend(
            ModelDiagnostic(
                severity="error",
                code=BREAKING,
                path=f"{base}{path}",
                message=(
                    f"Consumer API '{key}' {change}; raise contractVersion above"
                    f" {old.contractVersion} to release it"
                ),
            )
            for path, change in changes
        )
    return diagnostics


def _breaking_changes(old: OutputContract, new: OutputContract) -> list[tuple[str, str]]:
    """``(path within the definition, what changed)`` for each breaking change."""
    changes: list[tuple[str, str]] = []
    for key, public_name in old.types.items():
        if key not in new.types:
            changes.append(("/objectTypes", f"no longer exposes object type '{key}'"))
        elif new.types[key] != public_name:
            changes.append(
                (
                    f"/objectTypes/{pointer_segment(key)}/publicName",
                    f"renames the public type '{public_name}' to '{new.types[key]}'",
                )
            )
    changes += _field_changes("/object", "output field", old.fields, new.fields)
    for name, projection in old.projections.items():
        path = f"/projections/{pointer_segment(name)}"
        if name not in new.projections:
            changes.append(("/projections", f"removes projection '{name}'"))
            continue
        if new.projections[name]["shape"] != projection["shape"]:
            before, after = _shape(projection["shape"]), _shape(new.projections[name]["shape"])
            changes.append((path, f"changes projection '{name}' from {before} to {after}"))
        changes += _field_changes(
            f"{path}/fields", f"field of projection '{name}'", projection["fields"],
            new.projections[name]["fields"],
        )
    if old.match != new.match:
        changes.append(("/match", "changes its scoring weights"))
    for key, item in old.lists.items():
        if key not in new.lists:
            changes.append(("/lists", f"removes list '{key}'"))
        elif new.lists[key] != item:
            changes.append(("/lists", f"changes the type, sort or parent parameter of list '{key}'"))
    for name, kind in old.parameters.items():
        if name not in new.parameters:
            changes.append(("/parameters", f"removes parameter '{name}'"))
        elif new.parameters[name] != kind:
            changes.append(
                (
                    f"/parameters/{pointer_segment(name)}/kind",
                    f"changes parameter '{name}' from kind '{kind}' to '{new.parameters[name]}'",
                )
            )
        elif (name in old.scores_from) != (name in new.scores_from):
            turned = "on" if name in new.scores_from else "off"
            changes.append(
                (
                    f"/parameters/{pointer_segment(name)}/scoresFrom",
                    f"turns scoresFrom {turned} for parameter '{name}', which changes its ranking",
                )
            )
        # Turning targetable on adds a capability, as adding a field does (C-D2).
        if name in new.parameters and new.parameters[name] == kind and name in old.targetable - new.targetable:
            changes.append(
                (
                    f"/parameters/{pointer_segment(name)}/targetable",
                    f"turns targetable off for parameter '{name}', so its to.{name} reads are refused",
                )
            )
    # A type still exposed without its period would refuse the asOf its consumers send.
    for key in sorted(old.as_of - new.as_of):
        if key in new.types:
            changes.append(
                (
                    f"/objectTypes/{pointer_segment(key)}",
                    (
                        f"exposes object type '{key}', which no longer declares an effective"
                        " period (asOf on it is refused)"
                    ),
                )
            )
    return changes


def _field_changes(
    path: str, label: str, old: dict[str, Any], new: dict[str, Any]
) -> list[tuple[str, str]]:
    """Removed or retyped fields; a nested object loses or retypes its own fields likewise."""
    changes: list[tuple[str, str]] = []
    for name, value_type in old.items():
        if name not in new:
            changes.append((path, f"removes {label} '{name}'"))
        elif isinstance(value_type, dict) and isinstance(new[name], dict):
            changes += _field_changes(path, f"{label} '{name}' field", value_type["object"], new[name]["object"])
        elif new[name] != value_type:
            changes.append((path, f"changes {label} '{name}' from {_type(value_type)} to {_type(new[name])}"))
    return changes


def _type(value_type: Any) -> str:
    return "an object" if isinstance(value_type, dict) else str(value_type)


def _shape(shape: str) -> str:
    return "an object or null" if shape == "one" else "an array"
