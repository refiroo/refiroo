import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from ...db import lock_installation
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
from .consumer_contract import KeptContractVersion, contract_refusals
from .release_lifecycle import require_choosable
from .validation import require_valid_references
from .workspace_models import load_assignment


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
    kept_contract_versions: tuple[KeptContractVersion, ...] = ()


def lock_what_activation_changes(
    session: Session,
    workspace_key: str,
    release_id: str,
    expected_release_id: str,
    *,
    unique_values: bool = True,
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
    if unique_values:
        lock_unique_values(session, release_id, expected_release_id)


def lock_unique_values(session: Session, release_id: str, expected_release_id: str) -> None:
    """The unique attribute values, when the two releases declare different ``unique`` attributes:
    the assignment's trigger then rewrites the workspace's rows. Writes of every workspace wait for
    it until the commit. A migration, which holds its workspace's row from its start so that no
    write of the workspace holds such a row, takes it only just before the switch (0.11 R, R-F6)."""
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
    keep_contract_versions: bool = False,
) -> Activation:
    """Validate and select an installed release for one workspace in the current transaction.

    The transaction excludes the workspace's live writes from the compatibility check until it
    commits (0.8 W5): the workspace's assignment row is locked for update, and a live write rechecks
    its workspace's release under a share lock on the same row before it commits
    (``registry.require_resolved_release``), so it waits for the activation and is then refused if
    its release is no longer the workspace's. Other workspaces keep their release, their data is not
    counted and their subscriptions are not touched (ADR-042).
    """
    # Held for key share, first in the lock order: a retirement (which locks the row for update)
    # waits for the activation, or the activation reads it retired; live writes, which lock it for
    # no-key update, are not held up (0.11 R, R-F12).
    workspace = session.scalar(
        select(Workspace)
        .where(Workspace.key == workspace_key)
        .with_for_update(read=True, key_share=True)
        .execution_options(populate_existing=True)
    )
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
    if candidate_release.id != current_release.id:
        require_choosable(session, candidate_release, operation="activation")

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
    # With ``keep_contract_versions`` a person accepts the breaking changes of a current version
    # under its number; a lowered or changed earlier version is refused still.
    contract_errors, kept = contract_refusals(
        current_compilation.model,
        candidate_compilation.model,
        keep_contract_versions=keep_contract_versions,
    )
    if contract_errors:
        raise ConsumerContractVersionRequired(contract_errors)

    return switch_workspace_release(
        session,
        workspace_key,
        current_release,
        candidate_release,
        candidate_compilation.model,
        expected_version,
        changes=({"keptContractVersions": [item.as_record() for item in kept]} if kept else None),
        kept_contract_versions=kept,
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
    kept_contract_versions: tuple[KeptContractVersion, ...] = (),
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
    return Activation(
        workspace_key,
        candidate_release,
        new_version,
        updated_at,
        left_behind,
        kept_contract_versions,
    )


def installed_versions(session: Session, key: str) -> set[str]:
    """The versions the instance holds of one release key."""
    return set(
        session.scalars(select(ModelRelease.release_version).where(ModelRelease.release_key == key))
    )


def next_free_version(session: Session, key: str, version: str) -> str:
    """The version after the highest the model's releases (and ``version``) have, its last number
    bumped and never one an installed release holds: a release is the newest, whatever release its
    draft came from."""
    taken = installed_versions(session, key)

    def order(text: str) -> tuple[int, ...]:
        return tuple(int(part) for part in re.findall(r"\d+", text))

    highest = max([*taken, version], key=order)
    match = re.match(r"^(.*?)(\d+)$", highest)
    head, number = (match.group(1), int(match.group(2))) if match else (f"{highest}.", 0)
    number += 1
    while f"{head}{number}" in taken:
        number += 1
    return f"{head}{number}"


def install_model_release(session: Session, model: EngineModel) -> tuple[ModelRelease, bool]:
    """Install one immutable model and its metadata projection in the current transaction, under
    the installation lock until it ends (0.11 N1)."""
    require_valid_references(model)
    lock_installation(session)
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
