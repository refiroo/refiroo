import hashlib
import json
from pathlib import Path

from alembic.config import Config
from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import sessionmaker

from alembic import command

from .config import database_url
from .models.database import (
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
from .models.schema import EngineModel

engine = create_engine(database_url())
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def create_database() -> None:
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).resolve().parent / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url().replace("%", "%%"))
    command.upgrade(config, "head")


def install_model(model: EngineModel) -> ModelRelease:
    model_json = model.model_dump(mode="json")
    canonical = json.dumps(model_json, sort_keys=True, separators=(",", ":"))
    model_hash = hashlib.sha256(canonical.encode()).hexdigest()

    with SessionLocal() as session:
        existing = session.scalar(select(ModelRelease).where(ModelRelease.model_hash == model_hash))
        session.execute(update(ModelRelease).values(is_active=False))
        if existing:
            existing.is_active = True
            session.commit()
            return existing

        release = ModelRelease(
            release_key=model.release.key,
            release_name=model.release.name,
            release_version=model.release.version,
            schema_version=model.schemaVersion,
            model_hash=model_hash,
            model_json=model_json,
            is_active=True,
        )
        session.add(release)
        session.flush()

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

        session.commit()
        return release
