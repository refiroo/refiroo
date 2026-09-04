from pathlib import Path

from alembic.config import Config
from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import Session, sessionmaker

from alembic import command

from .config import database_url
from .models.database import (
    ApplicationMeta,
    ApplicationObjectTypeMeta,
    AttributeTypeMeta,
    ModelRelease,
    ModelRuntimeState,
    ObjectTypeAttributeMeta,
    ObjectTypeMeta,
    ObjectTypeRelationMeta,
    RelationTypeMeta,
    ViewDefinitionMeta,
)
from .models.schema import EngineModel
from .services.model_compiler import canonical_model

engine = create_engine(database_url())
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def create_database() -> None:
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).resolve().parent / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url().replace("%", "%%"))
    command.upgrade(config, "head")


def bootstrap_model(model: EngineModel) -> ModelRelease:
    with SessionLocal() as session:
        release = ensure_bootstrap_release(session, model)
        session.commit()
        return release


def ensure_bootstrap_release(session: Session, model: EngineModel) -> ModelRelease:
    model_json, model_hash = canonical_model(model)
    identity_release = session.scalar(
        select(ModelRelease).where(
            ModelRelease.release_key == model.release.key,
            ModelRelease.release_version == model.release.version,
        )
    )
    if identity_release is not None and identity_release.model_hash != model_hash:
        raise RuntimeError(
            "Bootstrap model release identity conflict: "
            f"{model.release.key}@{model.release.version} has different installed content"
        )

    release = session.scalar(select(ModelRelease).where(ModelRelease.model_hash == model_hash))
    if release is None:
        release = _install_release_metadata(session, model, model_json, model_hash)

    state = session.get(ModelRuntimeState, 1)
    if state is None:
        legacy_active = list(
            session.scalars(select(ModelRelease).where(ModelRelease.is_active.is_(True)))
        )
        if len(legacy_active) > 1:
            raise RuntimeError(
                "Cannot initialize model runtime state: multiple legacy active releases exist"
            )
        selected_release = legacy_active[0] if legacy_active else release
        state = ModelRuntimeState(id=1, active_model_release_id=selected_release.id, version=1)
        session.add(state)
        session.flush()

    _sync_legacy_active_flag(session, state.active_model_release_id)
    return release


def _install_release_metadata(
    session: Session,
    model: EngineModel,
    model_json: dict,
    model_hash: str,
) -> ModelRelease:
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

    return release


def _sync_legacy_active_flag(session: Session, active_release_id: int) -> None:
    session.execute(update(ModelRelease).values(is_active=False))
    session.execute(
        update(ModelRelease)
        .where(ModelRelease.id == active_release_id)
        .values(is_active=True)
    )
