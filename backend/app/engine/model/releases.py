from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Lock
from typing import Any

from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from ...models.database import (
    ApplicationMeta,
    ApplicationObjectTypeMeta,
    AttributeTypeMeta,
    AuditEvent,
    ChangeSet,
    ConsumerSubscription,
    ModelRelease,
    ObjectTypeAttributeMeta,
    ObjectTypeMeta,
    ObjectTypeRelationMeta,
    RelationTypeMeta,
    ViewDefinitionMeta,
    Workspace,
    WorkspaceModel,
)
from ...models.schema import EngineModel
from ..events.subscription_rules import suspend_left_behind
from ..indexes import matrix_states
from .compatibility import CompatibilityResult, analyze_compatibility
from .compiler import SUPPORTED_SCHEMA_VERSIONS, ModelDiagnostic, canonical_model, compile_model
from .consumer_contract import contract_diagnostics
from .validation import require_valid_references
from .workspace_models import load_assignment

model_installation_lock = Lock()
model_activation_lock = Lock()


@dataclass(frozen=True)
class ReleaseIdentityConflict(Exception):
    release_key: str
    release_version: str


@dataclass(frozen=True)
class ActivationConflict(Exception):
    workspace_key: str
    current_release_id: str
    current_version: int


@dataclass(frozen=True)
class ModelReleaseNotFound(Exception):
    release_id: str


@dataclass(frozen=True)
class WorkspaceNotFound(Exception):
    workspace_key: str


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
class WorkspaceRetired(Exception):
    workspace_key: str


@dataclass(frozen=True)
class Activation:
    """A workspace's new assignment, and its change sets left on the release it no longer runs."""

    workspace_key: str
    release: ModelRelease
    version: int
    updated_at: datetime
    change_sets_left_behind: tuple[ChangeSet, ...]


def lock_what_activation_changes(
    session: Session, workspace_key: str, release_id: str, expected_release_id: str
) -> None:
    """Lock, before the workspace's assignment, the rows activation changes after its check (0.9
    R-F2, R-F3): the workspace's active subscriptions it may suspend, and the unique attribute
    values when the releases declare different ``unique`` attributes (the assignment's trigger then
    rewrites the workspace's rows). A write holding such a row takes the assignment's share lock
    only as it commits; had the activation held the assignment first, each would wait for the
    other. Locked first, the activation waits for that write, which commits, and the lock order is
    the assignment's (ARCHITECTURE): workspace, change set, assignment, records. The table lock is
    the one place an activation holds up writes of other workspaces, until it commits. The releases
    are read unlocked: an activation that changed the assignment meanwhile is refused below as a
    conflict."""
    session.execute(
        select(ConsumerSubscription.sequence_id)
        .where(
            ConsumerSubscription.status == "active",
            ConsumerSubscription.workspace_key == workspace_key,
        )
        .order_by(ConsumerSubscription.sequence_id)
        .with_for_update()
    ).all()
    sources = dict(
        session.execute(
            select(ModelRelease.public_id, ModelRelease.model_json).where(
                ModelRelease.public_id.in_([release_id, expected_release_id])
            )
        ).all()
    )
    if _unique_keys(sources.get(release_id)) != _unique_keys(sources.get(expected_release_id)):
        session.execute(text("LOCK TABLE unique_attribute_values IN SHARE ROW EXCLUSIVE MODE"))


def _unique_keys(source: Any) -> frozenset[str]:
    """The attribute types a model source declares ``unique``."""
    if not isinstance(source, dict):
        return frozenset()
    return frozenset(
        item.get("key")
        for item in source.get("attributeTypes", [])
        if isinstance(item, dict) and (item.get("features") or {}).get("unique")
    )


def activate_model_release(
    session: Session,
    workspace_key: str,
    release_id: str,
    *,
    expected_version: int,
    expected_release_id: str,
) -> Activation:
    """Validate and select an installed release for one workspace in the current transaction.

    The transaction excludes the workspace's live writes from the compatibility check until it
    commits (0.8 W5): the workspace's assignment row is locked for update, and a live write rechecks
    its workspace's release under a share lock on the same row before it commits
    (``registry.require_resolved_release``), so it waits for the activation and is then refused if
    its release is no longer the workspace's. Other workspaces keep their release, their data is not
    counted and their subscriptions are not touched (ADR-042).
    """
    workspace = session.get(Workspace, workspace_key)
    if workspace is None:
        raise WorkspaceNotFound(workspace_key)
    lock_what_activation_changes(session, workspace_key, release_id, expected_release_id)
    assignment, current_release = load_assignment(session, workspace_key, for_update=True)

    candidate_release = session.scalar(
        select(ModelRelease).where(ModelRelease.public_id == release_id)
    )
    if candidate_release is None:
        raise ModelReleaseNotFound(release_id)

    if assignment.version != expected_version or current_release.public_id != expected_release_id:
        raise ActivationConflict(workspace_key, current_release.public_id, assignment.version)
    if workspace.status != "active":
        raise WorkspaceRetired(workspace_key)

    if candidate_release.schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        raise UnsupportedModelSchema(candidate_release.public_id, candidate_release.schema_version)

    current_compilation = compile_model(current_release.model_json)
    candidate_compilation = compile_model(candidate_release.model_json)
    if (
        not current_compilation.valid
        or current_compilation.model is None
        or not candidate_compilation.valid
        or candidate_compilation.model is None
    ):
        invalid_compilation, invalid_release = (
            (current_compilation, current_release)
            if not current_compilation.valid
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
        current_compilation.model,
        candidate_compilation.model,
        current_release.public_id,
        [workspace_key],
    )
    if compatibility.classification == "migration_required":
        raise ModelMigrationRequired(compatibility)
    # The workspace's consumers read its release, so its definitions are the contract (C-D17).
    contract_errors = [
        item
        for item in contract_diagnostics(current_compilation.model, candidate_compilation.model)
        if item.severity == "error"
    ]
    if contract_errors:
        raise ConsumerContractVersionRequired(tuple(contract_errors))

    return switch_workspace_release(
        session,
        workspace_key,
        current_release,
        candidate_release,
        candidate_compilation.model,
        expected_version,
    )


def switch_workspace_release(
    session: Session,
    workspace_key: str,
    current_release: ModelRelease,
    candidate_release: ModelRelease,
    candidate_model: EngineModel,
    expected_version: int,
    *,
    changes: dict[str, Any] | None = None,
) -> Activation:
    """Point the workspace's assignment, held for update and checked by the caller, at the
    candidate release, and carry what follows the workspace's release with it: its matrix states,
    its subscriptions the release cannot serve, and the ``activated`` audit event (with
    ``changes`` added, a migration's). Activation and a confirmed migration (0.11 V1) end here."""
    updated_at = datetime.now(UTC)
    new_version = expected_version + 1
    result = session.execute(
        update(WorkspaceModel)
        .where(
            WorkspaceModel.workspace_key == workspace_key,
            WorkspaceModel.version == expected_version,
            WorkspaceModel.model_release_id == current_release.id,
        )
        .values(model_release_id=candidate_release.id, version=new_version, updated_at=updated_at)
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        current, release = load_assignment(session, workspace_key)
        raise ActivationConflict(workspace_key, release.public_id, current.version)

    # Stored matrix cell states follow the workspace's new matrix shapes (A3b).
    matrix_states.sync_workspace(session, workspace_key)
    # The workspace's subscriptions the new release cannot serve are suspended with it (C11, C-D99).
    suspend_left_behind(session, candidate_model, workspace_key)
    left_behind = tuple(
        session.scalars(
            select(ChangeSet)
            .where(
                ChangeSet.workspace_key == workspace_key,
                ChangeSet.model_release_id == current_release.id,
            )
            .order_by(ChangeSet.sequence_id)
        )
    )
    session.add(
        AuditEvent(
            aggregate_type="workspace_model",
            aggregate_id=candidate_release.public_id,
            action="activated",
            version=new_version,
            changes={
                "workspaceKey": workspace_key,
                "oldReleaseId": current_release.public_id,
                "oldModelHash": current_release.model_hash,
                "newReleaseId": candidate_release.public_id,
                "newModelHash": candidate_release.model_hash,
                "changeSetsLeftBehind": [item.id for item in left_behind],
                **(changes or {}),
            },
        )
    )
    return Activation(workspace_key, candidate_release, new_version, updated_at, left_behind)


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

    hash_release = session.scalar(select(ModelRelease).where(ModelRelease.model_hash == model_hash))
    if hash_release is not None:
        return hash_release, False

    release = ModelRelease(
        release_key=model.release.key,
        release_name=model.release.name,
        release_version=model.release.version,
        schema_version=model.schemaVersion,
        model_hash=model_hash,
        model_json=model_json,
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
