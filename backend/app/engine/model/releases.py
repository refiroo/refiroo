from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Lock

from sqlalchemy import select, update
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from ...models.database import (
    ApplicationMeta,
    ApplicationObjectTypeMeta,
    AttributeTypeMeta,
    AuditEvent,
    ModelRelease,
    ModelRuntimeState,
    ObjectTypeAttributeMeta,
    ObjectTypeMeta,
    ObjectTypeRelationMeta,
    RelationTypeMeta,
    ViewDefinitionMeta,
)
from ...models.schema import EngineModel
from ..indexes import matrix_states
from .compatibility import CompatibilityResult, analyze_compatibility
from .compiler import SUPPORTED_SCHEMA_VERSIONS, ModelDiagnostic, canonical_model, compile_model
from .consumer_contract import contract_diagnostics
from .validation import require_valid_references

model_installation_lock = Lock()
model_activation_lock = Lock()


@dataclass(frozen=True)
class ReleaseIdentityConflict(Exception):
    release_key: str
    release_version: str


@dataclass(frozen=True)
class ActivationConflict(Exception):
    active_release_id: str
    runtime_version: int


class ActivationBusy(Exception):
    """Live writes held the database writer lock for longer than the connection's busy timeout."""


@dataclass(frozen=True)
class ModelReleaseNotFound(Exception):
    release_id: str


@dataclass(frozen=True)
class UnsupportedModelSchema(Exception):
    release_id: str
    schema_version: str


@dataclass(frozen=True)
class InvalidInstalledModel(Exception):
    diagnostics: tuple[ModelDiagnostic, ...]


@dataclass(frozen=True)
class ModelMigrationRequired(Exception):
    compatibility: CompatibilityResult


@dataclass(frozen=True)
class ConsumerContractVersionRequired(Exception):
    """A consumer API definition changes what its consumers read without a new contract version."""

    diagnostics: tuple[ModelDiagnostic, ...]


@dataclass(frozen=True)
class ActivatedRuntimeState:
    active_release_id: str
    active_model_hash: str
    version: int
    updated_at: datetime


def activate_model_release(
    session: Session,
    release_id: str,
    *,
    expected_runtime_version: int,
    expected_active_release_id: str,
) -> ActivatedRuntimeState:
    """Validate and select an installed release in the current transaction.

    The transaction excludes live writes from the compatibility check until it commits (0.8 W5):
    on SQLite it starts with ``BEGIN IMMEDIATE``, the database-wide writer reservation; elsewhere
    the runtime-state row is locked for update. A live write rechecks the active release under the
    same lock before it commits (``registry._require_resolved_release``).
    """
    if session.bind is not None and session.bind.dialect.name == "sqlite":
        # Discard any read transaction so the check starts at the writer reservation.
        session.rollback()
        try:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
        except OperationalError as exc:
            session.rollback()
            raise ActivationBusy() from exc
    row = session.execute(
        select(ModelRuntimeState, ModelRelease)
        .join(
            ModelRelease,
            ModelRelease.id == ModelRuntimeState.active_model_release_id,
        )
        .with_for_update(of=ModelRuntimeState)
    ).one_or_none()
    if row is None:
        raise RuntimeError("Model runtime state has no active installed release")
    runtime_state, active_release = row

    candidate_release = session.scalar(
        select(ModelRelease).where(ModelRelease.public_id == release_id)
    )
    if candidate_release is None:
        raise ModelReleaseNotFound(release_id)

    if (
        runtime_state.version != expected_runtime_version
        or active_release.public_id != expected_active_release_id
    ):
        raise ActivationConflict(active_release.public_id, runtime_state.version)

    if candidate_release.schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        raise UnsupportedModelSchema(
            candidate_release.public_id, candidate_release.schema_version
        )

    active_compilation = compile_model(active_release.model_json)
    candidate_compilation = compile_model(candidate_release.model_json)
    if (
        not active_compilation.valid
        or active_compilation.model is None
        or not candidate_compilation.valid
        or candidate_compilation.model is None
    ):
        invalid_compilation, invalid_release = (
            (active_compilation, active_release)
            if not active_compilation.valid
            else (candidate_compilation, candidate_release)
        )
        if invalid_compilation.unsupported_schema_version is not None:
            raise UnsupportedModelSchema(
                invalid_release.public_id,
                invalid_compilation.unsupported_schema_version,
            )
        raise InvalidInstalledModel(tuple(invalid_compilation.diagnostics))

    compatibility = analyze_compatibility(
        session,
        active_compilation.model,
        candidate_compilation.model,
        active_release.public_id,
    )
    if compatibility.classification == "migration_required":
        raise ModelMigrationRequired(compatibility)
    # Consumers read the active release, so its definitions are the contract (C-D17).
    contract_errors = [
        item
        for item in contract_diagnostics(active_compilation.model, candidate_compilation.model)
        if item.severity == "error"
    ]
    if contract_errors:
        raise ConsumerContractVersionRequired(tuple(contract_errors))

    updated_at = datetime.now(UTC)
    result = session.execute(
        update(ModelRuntimeState)
        .where(
            ModelRuntimeState.id == runtime_state.id,
            ModelRuntimeState.version == expected_runtime_version,
            ModelRuntimeState.active_model_release_id == active_release.id,
        )
        .values(
            active_model_release_id=candidate_release.id,
            version=expected_runtime_version + 1,
            updated_at=updated_at,
        )
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        current_row = session.execute(
            select(ModelRuntimeState, ModelRelease).join(
                ModelRelease,
                ModelRelease.id == ModelRuntimeState.active_model_release_id,
            )
        ).one()
        current_state, current_release = current_row
        raise ActivationConflict(current_release.public_id, current_state.version)

    session.execute(update(ModelRelease).values(is_active=False))
    session.execute(
        update(ModelRelease)
        .where(ModelRelease.id == candidate_release.id)
        .values(is_active=True)
    )
    new_version = expected_runtime_version + 1
    # Stored matrix cell states follow the newly active model's matrix shapes (A3b).
    matrix_states.sync_all(session)
    session.add(
        AuditEvent(
            aggregate_type="model_runtime_state",
            aggregate_id=candidate_release.public_id,
            action="activated",
            version=new_version,
            changes={
                "oldReleaseId": active_release.public_id,
                "oldModelHash": active_release.model_hash,
                "newReleaseId": candidate_release.public_id,
                "newModelHash": candidate_release.model_hash,
            },
        )
    )
    return ActivatedRuntimeState(
        active_release_id=candidate_release.public_id,
        active_model_hash=candidate_release.model_hash,
        version=new_version,
        updated_at=updated_at,
    )


def install_model_release(session: Session, model: EngineModel) -> tuple[ModelRelease, bool]:
    """Install one immutable model and its metadata projection in the current transaction."""
    require_valid_references(model)
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
