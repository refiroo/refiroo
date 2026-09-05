"""Projections that attach stable public IDs to active-model definitions.

Installed releases are immutable, so the key-to-public-ID maps for a release never change once the
release exists. They are therefore cached per release row id; the cache is cleared alongside the
parsed-model cache in :class:`~app.services.model.registry.ModelRegistry`.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from threading import Lock
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...models.api import (
    AllowedObjectTypePair,
    ApplicationResponse,
    AttributeBindingResponse,
    AttributeTypeResponse,
    ObjectTypeRelationResponse,
    ObjectTypeResponse,
    RelationTypeResponse,
)
from ...models.database import (
    ApplicationMeta,
    AttributeTypeMeta,
    ObjectTypeAttributeMeta,
    ObjectTypeMeta,
    ObjectTypeRelationMeta,
    RelationTypeMeta,
)
from ...models.schema import (
    ApplicationDefinition,
    AttributeTypeDefinition,
    ObjectTypeDefinition,
    ObjectTypeRelationDefinition,
    RelationTypeDefinition,
)
from .registry import ModelSnapshot


@dataclass(frozen=True)
class MetadataIdentifiers:
    """Public IDs of one installed release's metadata projection, keyed by model key."""

    applications: dict[str, str]
    attribute_types: dict[str, str]
    object_types: dict[str, str]
    relation_types: dict[str, str]
    object_type_attributes: dict[tuple[str, str], str]
    object_type_relations: dict[tuple[str, str, str], str]


_identifier_cache: dict[int, MetadataIdentifiers] = {}
_identifier_lock = Lock()


def clear_metadata_cache() -> None:
    with _identifier_lock:
        _identifier_cache.clear()


def metadata_identifiers(session: Session, release_db_id: int) -> MetadataIdentifiers:
    """Load, and then reuse, the public-ID maps of one immutable release."""
    with _identifier_lock:
        cached = _identifier_cache.get(release_db_id)
    if cached is not None:
        return cached

    identifiers = MetadataIdentifiers(
        applications=_keyed(session, ApplicationMeta, release_db_id),
        attribute_types=_keyed(session, AttributeTypeMeta, release_db_id),
        object_types=_keyed(session, ObjectTypeMeta, release_db_id),
        relation_types=_keyed(session, RelationTypeMeta, release_db_id),
        object_type_attributes={
            (row.object_type_key, row.attribute_type_key): row.public_id
            for row in session.scalars(
                select(ObjectTypeAttributeMeta).where(
                    ObjectTypeAttributeMeta.model_release_id == release_db_id
                )
            )
        },
        object_type_relations={
            (row.relation_type_key, row.from_object_type_key, row.to_object_type_key): row.public_id
            for row in session.scalars(
                select(ObjectTypeRelationMeta).where(
                    ObjectTypeRelationMeta.model_release_id == release_db_id
                )
            )
        },
    )
    with _identifier_lock:
        _identifier_cache[release_db_id] = identifiers
    return identifiers


def _keyed(session: Session, entity: Any, release_db_id: int) -> dict[str, str]:
    return {
        row.key: row.public_id
        for row in session.scalars(
            select(entity).where(entity.model_release_id == release_db_id)
        )
    }


def build_application_responses(
    session: Session,
    snapshot: ModelSnapshot,
    applications: Sequence[ApplicationDefinition],
) -> list[ApplicationResponse]:
    identifiers = metadata_identifiers(session, snapshot.release_db_id)
    results = []
    for application in applications:
        data = application.model_dump(mode="json")
        _inject_object_type_ids(data, identifiers.object_types)
        results.append(
            ApplicationResponse(
                id=identifiers.applications.get(application.key, ""),
                **data,
            )
        )
    return results


def _inject_object_type_ids(value: Any, object_type_ids: dict[str, str]) -> None:
    if isinstance(value, dict):
        if "objectTypeKey" in value:
            value["objectTypeId"] = object_type_ids.get(value["objectTypeKey"], "")
        for item in value.values():
            _inject_object_type_ids(item, object_type_ids)
    elif isinstance(value, list):
        for item in value:
            _inject_object_type_ids(item, object_type_ids)


def build_attribute_type_responses(
    session: Session,
    snapshot: ModelSnapshot,
    attribute_types: Sequence[AttributeTypeDefinition],
) -> list[AttributeTypeResponse]:
    identifiers = metadata_identifiers(session, snapshot.release_db_id)
    return [
        AttributeTypeResponse(
            id=identifiers.attribute_types.get(attribute_type.key, ""),
            key=attribute_type.key,
            name=attribute_type.name,
            description=attribute_type.description,
            valueType=attribute_type.valueType,
            default=attribute_type.default,
            features=attribute_type.features,
            validation=attribute_type.validation,
            ui=attribute_type.ui,
        )
        for attribute_type in attribute_types
    ]


def build_object_type_responses(
    session: Session,
    snapshot: ModelSnapshot,
    object_types: Sequence[ObjectTypeDefinition],
) -> list[ObjectTypeResponse]:
    model = snapshot.model
    identifiers = metadata_identifiers(session, snapshot.release_db_id)
    results = []
    for object_type in object_types:
        attribute_responses = []
        for binding in object_type.attributes:
            attribute_type = model.attribute_type(binding.attributeTypeKey)
            attribute_responses.append(
                AttributeBindingResponse(
                    id=identifiers.object_type_attributes.get(
                        (object_type.key, binding.attributeTypeKey), ""
                    ),
                    attributeTypeKey=binding.attributeTypeKey,
                    name=attribute_type.name if attribute_type else binding.attributeTypeKey,
                    valueType=attribute_type.valueType if attribute_type else "text",
                    required=binding.required,
                    readOnly=binding.readOnly,
                    order=binding.order,
                )
            )
        results.append(
            ObjectTypeResponse(
                id=identifiers.object_types.get(object_type.key, ""),
                key=object_type.key,
                name=object_type.name,
                pluralName=object_type.pluralName,
                description=object_type.description,
                icon=object_type.icon,
                displayAttributeTypeKey=object_type.displayAttributeTypeKey,
                attributes=attribute_responses,
                features=object_type.features,
                behavior=object_type.behavior,
                validation=object_type.validation,
            )
        )
    return results


def build_relation_type_responses(
    session: Session,
    snapshot: ModelSnapshot,
    relation_types: Sequence[RelationTypeDefinition],
) -> list[RelationTypeResponse]:
    model = snapshot.model
    identifiers = metadata_identifiers(session, snapshot.release_db_id)

    relation_keys = {relation_type.key for relation_type in relation_types}
    allowed_by_key: dict[str, list[ObjectTypeRelationDefinition]] = {
        key: [] for key in relation_keys
    }
    for allowed in model.objectTypeRelations:
        if allowed.relationTypeKey in relation_keys:
            allowed_by_key[allowed.relationTypeKey].append(allowed)

    results = []
    for relation_type in relation_types:
        pairs = [
            AllowedObjectTypePair(
                id=identifiers.object_type_relations.get(
                    (
                        allowed.relationTypeKey,
                        allowed.fromObjectTypeKey,
                        allowed.toObjectTypeKey,
                    ),
                    "",
                ),
                fromObjectTypeKey=allowed.fromObjectTypeKey,
                toObjectTypeKey=allowed.toObjectTypeKey,
                cardinality=allowed.cardinality,
                required=allowed.required,
                attributeTypeKeys=allowed.attributeTypeKeys,
                features=allowed.features,
            )
            for allowed in allowed_by_key.get(relation_type.key, [])
        ]
        results.append(
            RelationTypeResponse(
                id=identifiers.relation_types.get(relation_type.key, ""),
                key=relation_type.key,
                name=relation_type.name,
                reverseKey=relation_type.reverseKey,
                reverseName=relation_type.reverseName,
                isOriented=relation_type.isOriented,
                features=relation_type.features,
                allowedPairs=pairs,
            )
        )
    return results


def build_object_type_relation_responses(
    session: Session,
    snapshot: ModelSnapshot,
    relations: Sequence[ObjectTypeRelationDefinition],
) -> list[ObjectTypeRelationResponse]:
    identifiers = metadata_identifiers(session, snapshot.release_db_id)
    return [
        ObjectTypeRelationResponse(
            id=identifiers.object_type_relations[
                (
                    allowed.relationTypeKey,
                    allowed.fromObjectTypeKey,
                    allowed.toObjectTypeKey,
                )
            ],
            relationTypeKey=allowed.relationTypeKey,
            fromObjectTypeKey=allowed.fromObjectTypeKey,
            toObjectTypeKey=allowed.toObjectTypeKey,
            cardinality=allowed.cardinality,
            required=allowed.required,
            attributeTypeKeys=allowed.attributeTypeKeys,
            features=allowed.features,
        )
        for allowed in relations
    ]
