from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.database import (
    ApplicationMeta,
    ApplicationObjectTypeMeta,
    AttributeTypeMeta,
    ModelRelease,
    ObjectTypeAttributeMeta,
    ObjectTypeMeta,
    ObjectTypeRelationMeta,
    RelationTypeMeta,
    ViewDefinitionMeta,
)
from ..models.schema import EngineModel
from .model_compiler import canonical_model


@dataclass(frozen=True)
class ReleaseIdentityConflict(Exception):
    release_key: str
    release_version: str


def install_model_release(session: Session, model: EngineModel) -> tuple[ModelRelease, bool]:
    """Install one immutable model and its metadata projection in the current transaction."""
    model_json, model_hash = canonical_model(model)
    identity_release = session.scalar(
        select(ModelRelease).where(
            ModelRelease.release_key == model.release.key,
            ModelRelease.release_version == model.release.version,
        )
    )
    if identity_release is not None:
        if identity_release.model_hash != model_hash:
            raise ReleaseIdentityConflict(model.release.key, model.release.version)
        return identity_release, False

    hash_release = session.scalar(
        select(ModelRelease).where(ModelRelease.model_hash == model_hash)
    )
    if hash_release is not None:
        return hash_release, False

    release = ModelRelease(
        release_key=model.release.key,
        release_name=model.release.name,
        release_version=model.release.version,
        schema_version=model.schemaVersion,
        model_hash=model_hash,
        model_json=model_json,
        is_active=False,
    )
    session.add(release)
    session.flush()
    _install_metadata_projection(session, release, model)
    return release, True


def _install_metadata_projection(
    session: Session, release: ModelRelease, model: EngineModel
) -> None:
    for attribute in model.attributeTypes:
        session.add(
            AttributeTypeMeta(
                model_release_id=release.id,
                key=attribute.key,
                name=attribute.name,
                value_type=attribute.valueType,
                definition=attribute.model_dump(mode="json"),
            )
        )

    for object_type in model.objectTypes:
        session.add(
            ObjectTypeMeta(
                model_release_id=release.id,
                key=object_type.key,
                name=object_type.name,
                definition=object_type.model_dump(mode="json"),
            )
        )
        for binding in object_type.attributes:
            session.add(
                ObjectTypeAttributeMeta(
                    model_release_id=release.id,
                    object_type_key=object_type.key,
                    attribute_type_key=binding.attributeTypeKey,
                    required=binding.required,
                    read_only=binding.readOnly,
                    display_order=binding.order,
                    definition=binding.model_dump(mode="json"),
                )
            )

    for relation in model.relationTypes:
        session.add(
            RelationTypeMeta(
                model_release_id=release.id,
                key=relation.key,
                reverse_key=relation.reverseKey,
                name=relation.name,
                reverse_name=relation.reverseName,
                is_oriented=relation.isOriented,
                definition=relation.model_dump(mode="json"),
            )
        )

    for allowed in model.objectTypeRelations:
        session.add(
            ObjectTypeRelationMeta(
                model_release_id=release.id,
                relation_type_key=allowed.relationTypeKey,
                from_object_type_key=allowed.fromObjectTypeKey,
                to_object_type_key=allowed.toObjectTypeKey,
                cardinality=allowed.cardinality,
                definition=allowed.model_dump(mode="json"),
            )
        )

    for application in model.applications:
        session.add(
            ApplicationMeta(
                model_release_id=release.id,
                key=application.key,
                name=application.name,
                definition=application.model_dump(mode="json"),
            )
        )
        for object_type_key in application.objectTypeKeys:
            session.add(
                ApplicationObjectTypeMeta(
                    model_release_id=release.id,
                    application_key=application.key,
                    object_type_key=object_type_key,
                )
            )
        for view in application.views:
            session.add(
                ViewDefinitionMeta(
                    model_release_id=release.id,
                    application_key=application.key,
                    key=view.key,
                    name=view.name,
                    view_type=view.type,
                    definition=view.model_dump(mode="json"),
                )
            )
