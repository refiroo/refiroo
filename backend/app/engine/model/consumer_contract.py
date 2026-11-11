"""A consumer API definition's output contract, and the breaking-change check (Base 0.9 C1).

A definition's contract is what its consumers depend on: the exposed types and their public names,
the output fields and their value types, each projection's shape and fields, the scoring weights, the
lists, the parameters and the events (CONSUMER_API C-D2, C-D4, C-D18, C-D85). :func:`output_contract` derives it from a
definition and its release; model validation uses the same field resolution for its type rules, so
the checked contract and the validated one cannot drift apart.

:func:`contract_diagnostics` compares a candidate release with the active one, which is what
consumers read (C-D17). A definition whose contract loses or changes anything its consumers read
needs a higher ``contractVersion``; removing a whole definition is a warning (C-D18).
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any

from ...common.json_pointer import pointer_segment
from ...models.schema import (
    OBJECT_ROLES,
    PARENT_BLOCK_PREFIX,
    PARENT_BUILT_IN,
    ConsumerApiDefinition,
    ConsumerField,
    ConsumerProjection,
    EngineModel,
    ObjectTypeDefinition,
    ProjectionParameter,
)
from .consumer_definitions import authored_pointer, consumer_apis, served_versions
from .diagnostics import ModelDiagnostic
from .traversal import ancestor_type_keys, parent_type_keys, related_object_types

# Built-in fields a source, projection field or match rule may name, and their value types.
BUILT_IN_FIELDS = {"id": "text", "name": "text"}
# A projection field's source naming the related record's public type name (C-D73).
PROJECTION_TYPE_SOURCE = "objectType"
ANCESTOR_REFERENCE_PREFIX = "ancestor:"
# A projection field's source naming an attribute of the relationship itself (``relation:<attribute>``).
RELATION_REFERENCE_PREFIX = "relation:"
# Value types that compare as one output type (C-D19).
_TEXT_TYPES = {"text", "longText"}

BREAKING = "CONSUMER_CONTRACT_VERSION_REQUIRED"
# A kept earlier version would read differently from the one served now (0.13 DF3).
KEPT_VERSION_CHANGED = "CONSUMER_KEPT_VERSION_CHANGED"
KEPT_VERSION_STOPPED = "CONSUMER_VERSION_STOPPED"
# A filter's internal kind as the author's verb names it (C18).
FILTER_VERB = {"objectType": "byType", "ancestor": "under", "related": "linkedTo", "projection": "onRelated"}


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


def split_relation_reference(field: str) -> str | None:
    """``relation:<attribute>`` as the attribute type key, ``""`` when none follows the prefix, or
    ``None`` for another field."""
    if not field.startswith(RELATION_REFERENCE_PREFIX):
        return None
    return field.removeprefix(RELATION_REFERENCE_PREFIX)


def relation_attribute_keys(
    model: EngineModel,
    definition: ConsumerApiDefinition,
    relation: str,
    direction: str,
    owners: Sequence[ObjectTypeDefinition] | None = None,
) -> set[str]:
    """The relation attributes the bindings of the route carry, from an owner type's end (an exposed
    type's by default)."""
    exposed = set(definition.objectTypes) if owners is None else {item.key for item in owners}
    return {
        key
        for binding in model.objectTypeRelations
        if binding.relationTypeKey == relation
        and (binding.fromObjectTypeKey if direction == "outgoing" else binding.toObjectTypeKey) in exposed
        for key in binding.attributeTypeKeys
    }


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
    route: tuple[str, str] | None = None,
    owners: Sequence[ObjectTypeDefinition] | None = None,
) -> str | None:
    """The output type of a projection field's source, or ``None`` when it does not resolve.

    ``objectType`` is the related record's public type name, so it resolves only where the definition
    exposes every type the projection reaches; another type has no public name (C-D73).
    ``relation:<attribute>`` is an attribute of the relationship itself, which a binding of the
    projection's ``route`` (relation, direction) must carry.
    """
    attribute = split_relation_reference(source)
    if attribute is not None:
        definition_ = model.attribute_type(attribute)
        if route is None or definition_ is None or attribute not in relation_attribute_keys(
            model, definition, *route, owners=owners
        ):
            return None
        return output_type(definition_.valueType)
    if source == PROJECTION_TYPE_SOURCE:
        exposed = bool(targets) and all(item.key in definition.objectTypes for item in targets)
        return "text" if exposed else None
    return reference_value_type(model, targets, source)


def exposed_types(model: EngineModel, definition: ConsumerApiDefinition) -> list[ObjectTypeDefinition]:
    return [item for key in definition.objectTypes if (item := model.object_type(key)) is not None]


def parent_types(model: EngineModel, definition: ConsumerApiDefinition) -> list[ObjectTypeDefinition]:
    """The types that can directly contain an exposed type: the ones a record's parent may be, whether
    or not the definition exposes them (CA1)."""
    keys = {key for item in exposed_types(model, definition) for key in parent_type_keys(model, item.key)}
    return [item for key in sorted(keys) if (item := model.object_type(key)) is not None]


def block_owners(
    model: EngineModel, definition: ConsumerApiDefinition, name: str
) -> list[ObjectTypeDefinition]:
    """The types whose records carry the related block ``name``: the exposed types for the object's
    blocks, the parent types for ``parent.<block>``."""
    if name.startswith(PARENT_BLOCK_PREFIX):
        return parent_types(model, definition)
    return exposed_types(model, definition)


def block_route(definition: ConsumerApiDefinition, name: str) -> ConsumerProjection:
    """The related block ``name`` as the object or ``parent.<block>`` names it."""
    return definition.blocks()[name]


def projection_targets(
    model: EngineModel,
    definition: ConsumerApiDefinition,
    relation: str,
    direction: str,
    owners: Sequence[ObjectTypeDefinition] | None = None,
) -> list[ObjectTypeDefinition]:
    """The types at the other end of the route from any owner type (the exposed types by default)."""
    found: dict[str, ObjectTypeDefinition] = {}
    for item in exposed_types(model, definition) if owners is None else owners:
        for target in related_object_types(model, item.key, direction, [relation]):
            found.setdefault(target.key, target)
    return list(found.values())


def block_targets(model: EngineModel, definition: ConsumerApiDefinition, name: str) -> list[ObjectTypeDefinition]:
    """The types at the other end of the related block ``name`` from its owners."""
    route = block_route(definition, name).from_
    return projection_targets(model, definition, route.relation, route.direction, block_owners(model, definition, name))


def projection_shape(
    model: EngineModel,
    definition: ConsumerApiDefinition,
    relation: str,
    direction: str,
    owners: Sequence[ObjectTypeDefinition] | None = None,
) -> str:
    """``one`` when every binding of the route allows at most one related object, else ``many``.

    Derived, never declared, so a cardinality change in the model is a contract change the check sees.
    """
    owning = {item.key for item in (exposed_types(model, definition) if owners is None else owners)}
    single = True
    for binding in model.objectTypeRelations:
        if binding.relationTypeKey != relation:
            continue
        own = binding.fromObjectTypeKey if direction == "outgoing" else binding.toObjectTypeKey
        if own not in owning:
            continue
        single = single and binding.holds_one("from" if direction == "outgoing" else "to")
    return "one" if single else "many"


def block_shape(model: EngineModel, definition: ConsumerApiDefinition, name: str) -> str:
    route = block_route(definition, name).from_
    return projection_shape(
        model, definition, route.relation, route.direction, block_owners(model, definition, name)
    )


def parent_source_type(
    model: EngineModel,
    parents: Sequence[ObjectTypeDefinition],
    role_types: dict[str, str | None],
    sources: Sequence[str],
) -> str | None:
    """The output type of a parent field's sources, or ``None`` when one does not resolve or they differ."""
    found = set()
    for source in sources:
        if source == "objectType":
            found.add("text")
        elif source in PARENT_BUILT_IN:
            found.add(role_types.get(source, "text"))
        else:
            found.add(reference_value_type(model, parents, source))
    return found.pop() if len(found) == 1 and None not in found else None


def source_type(
    model: EngineModel, types: Sequence[ObjectTypeDefinition], sources: Sequence[str]
) -> str | None:
    """The shared output type of a field's sources (C-D19), or ``None`` when they differ."""
    found = {field_value_type(model, types, source) for source in sources}
    return found.pop() if len(found) == 1 and None not in found else None


@dataclass(frozen=True)
class EventContract:
    """An event's types, change kinds and watched names; ``watch`` ``None`` watches every output."""

    object_types: frozenset[str]
    changes: frozenset[str]
    watch: frozenset[str] | None


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
    # The declared events, which consumers rely on to be told (C9, C-D85).
    events: dict[str, EventContract] = field(default_factory=dict)
    # The operations among ``objects``, ``xref`` and ``resolve`` the definition offers (C-D132).
    operations: frozenset[str] = frozenset()



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
        parents = parent_types(model, definition)
        fields[shape.parent.output] = {
            "object": {
                output: parent_source_type(model, parents, role_types, field.source)
                for output, field in shape.parent.fields.items()
            }
        }
    if shape.path is not None:
        fields[shape.path] = "text"
    if shape.hierarchy is not None:
        fields[shape.hierarchy] = "text[]"

    projections = {}
    for name, projection in definition.blocks().items():
        route = projection.from_
        targets = block_targets(model, definition, name)
        projections[name] = {
            "shape": block_shape(model, definition, name),
            # Only a block served on request says so: the contract of a definition that serves every
            # block in every answer is unchanged.
            **({"served": projection.served} if projection.served != "always" else {}),
            "fields": {
                output: projection_field_type(
                    model, definition, targets, source, (route.relation, route.direction),
                    block_owners(model, definition, name),
                )
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
        events={
            event.key: EventContract(
                object_types=frozenset(event.objectTypes),
                changes=frozenset(event.changes),
                watch=None
                if event.watch is None
                else frozenset(event.watch.fields) | frozenset(event.watch.projections),
            )
            for event in definition.events
        },
        operations=frozenset(name for name in ("objects", "xref", "resolve") if definition.offers(name)),
    )


def contract_diagnostics(active: EngineModel, candidate: EngineModel) -> list[ModelDiagnostic]:
    """Breaking changes in ``candidate``'s definitions against ``active``'s (C-D17, C-D18).

    An error for each change a definition's consumers would notice without a higher
    ``contractVersion``, and a warning for each definition ``candidate`` no longer declares.
    """
    before = {item.key: item for item in consumer_apis(active)}
    after = {item.key: item for item in consumer_apis(candidate)}
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
    diagnostics += _kept_version_diagnostics(active, candidate)
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
                path=authored_pointer(candidate, key, f"{base}{path}"),
                message=(
                    f"Consumer API '{key}' {change}; raise contractVersion above"
                    f" {old.contractVersion} to release it"
                ),
            )
            for path, change in changes
        )
    return diagnostics


def _kept_version_diagnostics(active: EngineModel, candidate: EngineModel) -> list[ModelDiagnostic]:
    """The versions ``candidate`` serves beside the current one (DF3), against the same version in
    ``active``: a version is a contract, so it must read as it did (C-D2) while it is served. An
    error for each change its consumers would notice; a warning for a kept version that stops."""
    diagnostics: list[ModelDiagnostic] = []
    keys = {item.key for item in consumer_apis(active)} & {item.key for item in consumer_apis(candidate)}
    for key in sorted(keys):
        before = {item.definition.contractVersion: item for item in served_versions(active, key)}
        after = {item.definition.contractVersion: item for item in served_versions(candidate, key)}
        for version in sorted(set(before) - set(after)):
            if before[version].is_current:
                continue
            diagnostics.append(
                ModelDiagnostic(
                    severity="warning",
                    code=KEPT_VERSION_STOPPED,
                    path=f"/consumerApis/{pointer_segment(key)}",
                    message=(
                        f"Consumer API '{key}' stops serving version {version}; its consumers will receive"
                        f" 404 CONTRACT_VERSION_NOT_FOUND from /api/consumer/{key}/v{version}"
                    ),
                )
            )
        for version in sorted(set(before) & set(after)):
            old, new = before[version], after[version]
            if new.is_current:
                continue
            changes = _breaking_changes(
                output_contract(active, old.definition), output_contract(candidate, new.definition)
            )
            diagnostics.extend(
                ModelDiagnostic(
                    severity="error",
                    code=KEPT_VERSION_CHANGED,
                    path=authored_pointer(candidate, key, f"{new.base}{path}", new.index),
                    message=(
                        f"Consumer API '{key}' version {version} is kept and {change}; a kept version is"
                        " served as it was: restore it, or stop serving it"
                    ),
                )
                for path, change in changes
            )
    return diagnostics


def raised_contracts(active: EngineModel, candidate: EngineModel) -> list[dict[str, Any]]:
    """The consumer APIs ``candidate`` raises the contractVersion of, each with what its consumers
    stop reading or read differently: the engine's own account of the breaking changes."""
    before = {item.key: item for item in consumer_apis(active)}
    raised = []
    for item in consumer_apis(candidate):
        old = before.get(item.key)
        if old is None or item.contractVersion <= old.contractVersion:
            continue
        changes = _breaking_changes(output_contract(active, old), output_contract(candidate, item))
        raised.append(
            {
                "api": item.key,
                "name": item.name,
                "from": old.contractVersion,
                "to": item.contractVersion,
                "changes": [change for _, change in changes],
            }
        )
    return raised


def _breaking_changes(old: OutputContract, new: OutputContract) -> list[tuple[str, str]]:
    """``(path within the definition, what changed)`` for each breaking change."""
    changes: list[tuple[str, str]] = [
        ("/operations", f"no longer offers the '{name}' operation") for name in sorted(old.operations - new.operations)
    ]
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
        path = _block_path(name)
        if name not in new.projections:
            changes.append((path.rsplit("/", 1)[0], f"removes related block '{name}'"))
            continue
        if new.projections[name]["shape"] != projection["shape"]:
            before, after = _shape(projection["shape"]), _shape(new.projections[name]["shape"])
            changes.append((path, f"changes related block '{name}' from {before} to {after}"))
        # A block that was in every answer and is now served on request leaves the default answer;
        # the other way adds to it (CA1, PP-D30).
        if "served" not in projection and new.projections[name].get("served") == "onRequest":
            changes.append(
                (f"{path}/served", f"serves related block '{name}' only on request, so it leaves the default answer")
            )
        changes += _field_changes(
            f"{path}/fields", f"field of related block '{name}'", projection["fields"],
            new.projections[name]["fields"],
        )
    # Weights are read only through XREF and batch resolve: offering XREF again is an addition.
    if "xref" in old.operations & new.operations and old.match != new.match:
        changes.append(("/match", "changes its scoring weights"))
    for key, item in old.lists.items():
        if key not in new.lists:
            changes.append(("/lists", f"removes list '{key}'"))
        elif new.lists[key] != item:
            changes.append(("/lists", f"changes the type, sort or 'within' of list '{key}'"))
    for name, kind in old.parameters.items():
        if name not in new.parameters:
            changes.append(("/parameters", f"removes filter '{name}'"))
        elif new.parameters[name] != kind:
            changes.append(
                (
                    f"/parameters/{pointer_segment(name)}/kind",
                    f"changes filter '{name}' from '{FILTER_VERB[kind]}' to '{FILTER_VERB[new.parameters[name]]}'",
                )
            )
        elif (name in old.scores_from) != (name in new.scores_from):
            turned = "on" if name in new.scores_from else "off"
            changes.append(
                (
                    f"/parameters/{pointer_segment(name)}/scoresFrom",
                    f"turns scoreOnlyMatching {turned} for filter '{name}', which changes its ranking",
                )
            )
        # Turning targetable on adds a capability, as adding a field does (C-D2).
        if name in new.parameters and new.parameters[name] == kind and name in old.targetable - new.targetable:
            changes.append(
                (
                    f"/parameters/{pointer_segment(name)}/targetable",
                    f"turns crosswalk off for filter '{name}', so its to.{name} reads are refused",
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
    changes += _event_changes(old.events, new.events)
    return changes


def _block_path(name: str) -> str:
    """The internal pointer of a related block: the object's, or the parent's (``parent.<name>``)."""
    if name.startswith(PARENT_BLOCK_PREFIX):
        return f"/object/parent/projections/{pointer_segment(name.removeprefix(PARENT_BLOCK_PREFIX))}"
    return f"/projections/{pointer_segment(name)}"


def _event_changes(old: dict[str, EventContract], new: dict[str, EventContract]) -> list[tuple[str, str]]:
    """An event that tells its consumers less (C-D85): removed, a type or a change kind removed, a
    watched name removed or a watch added. Telling them more is compatible."""
    changes: list[tuple[str, str]] = []
    for key, event in old.items():
        path = f"/events/{pointer_segment(key)}"
        after = new.get(key)
        if after is None:
            changes.append(("/events", f"removes event '{key}'"))
            continue
        if lost := sorted(event.object_types - after.object_types):
            changes.append((f"{path}/objectTypes", f"no longer reports event '{key}' for {lost}"))
        if lost := sorted(event.changes - after.changes):
            changes.append((f"{path}/changes", f"no longer reports {lost} in event '{key}'"))
        if after.watch is not None and (event.watch is None or event.watch - after.watch):
            narrowed = "watches fewer outputs" if event.watch is not None else "adds a watch"
            changes.append((f"{path}/watch", f"{narrowed} in event '{key}', so it reports fewer updates"))
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
