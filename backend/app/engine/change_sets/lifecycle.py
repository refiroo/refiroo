"""A change set's life: created from live data or a publication, renamed, claimed and discarded, and its effective membership."""

from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from ...errors import api_error
from ...models.database import (
    ChangeSet,
    ChangeSetBase,
    ChangeSetBaseObject,
    ChangeSetBaseRelation,
    ModelRuntimeState,
    ObjectRelation,
    Publication,
    RdmObject,
    Workspace,
)
from ..indexes import matrix_states
from ..indexes.snapshot_values import delete_owner_values
from ..records.attributes import load_attribute_values
from ..records.relation_set_versions import delete_change_set_relation_set_versions
from ..records.writes import ChangeSetWrites
from ..workspaces.workspace_audit import (
    record_change_set_created,
    record_change_set_derived,
    record_change_set_discarded,
    record_change_set_renamed,
)
from .access import change_set_model, load_change_set
from .pinning import require_change_set_compatible


def create_change_set(
    session: Session,
    workspace_key: str,
    model_release_id: int,
    *,
    name: str | None = None,
    source_publication_id: str | None = None,
    source: str | None = None,
    expected_model_runtime_release_id: int | None = None,
    validate_selected_model: bool = False,
) -> ChangeSet:
    if source not in (None, "currentLive", "publication"):
        raise api_error(422, "change_set_source_invalid", "Change set source is invalid")
    if source == "publication" and source_publication_id is None:
        raise api_error(
            422,
            "change_set_source_invalid",
            "A publication source requires a publication id",
        )
    if source == "currentLive" and source_publication_id is not None:
        raise api_error(
            422,
            "change_set_source_invalid",
            "A current-live source cannot include a publication id",
        )
    if source == "currentLive":
        return _create_current_live_change_set(
            session,
            workspace_key,
            model_release_id,
            name=name,
            expected_model_runtime_release_id=expected_model_runtime_release_id,
            validate_selected_model=validate_selected_model,
        )
    workspace = session.get(Workspace, workspace_key)
    if workspace is None:
        raise api_error(404, "workspace_not_found", f"Workspace '{workspace_key}' not found")
    if workspace.status != "active":
        raise api_error(409, "workspace_retired", "Retired workspaces cannot be edited")
    if source_publication_id is not None:
        publication = session.scalar(
            select(Publication).where(Publication.id == source_publication_id)
        )
        if publication is None or publication.workspace_key != workspace_key:
            raise api_error(
                404, "publication_not_found", "Source publication was not found"
            )
        model_release_id = publication.model_release_id
    change_set = ChangeSet(
        workspace_key=workspace_key,
        model_release_id=model_release_id,
        derived_from_publication_id=source_publication_id,
        name=name,
    )
    session.add(change_set)
    session.flush()
    if validate_selected_model:
        require_change_set_compatible(session, change_set, change_set_model(session, change_set))
    if source_publication_id is not None:
        record_change_set_derived(session, change_set=change_set)
    else:
        record_change_set_created(session, change_set=change_set)
    matrix_states.record_change_set(session, change_set)
    session.commit()
    session.refresh(change_set)
    return change_set


def _create_current_live_change_set(
    session: Session,
    workspace_key: str,
    model_release_id: int,
    *,
    name: str | None,
    expected_model_runtime_release_id: int | None,
    validate_selected_model: bool,
) -> ChangeSet:
    """Capture one private base under SQLite's database-wide writer reservation.

    SQLite is the supported Base 0.6 runtime database.  ``BEGIN IMMEDIATE`` prevents a concurrent
    live writer (including model activation) from committing between graph rows, attributes, edges and
    the runtime-state comparison.  Other dialects are refused until their equivalent capture protocol
    is implemented, rather than silently returning a weaker mixed snapshot.
    """
    if session.bind is None or session.bind.dialect.name != "sqlite":
        raise api_error(
            409,
            "change_set_snapshot_unsupported",
            "Current-live change set capture is supported only on SQLite in this release",
        )
    # Active-model dependency resolution may have opened a read transaction before this service.
    # Discard it so the capture starts at the explicit writer reservation rather than a stale read view.
    session.rollback()
    try:
        session.connection().exec_driver_sql("BEGIN IMMEDIATE")
    except OperationalError as exc:
        session.rollback()
        raise api_error(
            409,
            "change_set_snapshot_retry",
            "Current live data is busy; retry starting the change set after the active write finishes",
        ) from exc
    try:
        workspace = session.get(Workspace, workspace_key)
        if workspace is None:
            raise api_error(404, "workspace_not_found", f"Workspace '{workspace_key}' not found")
        if workspace.status != "active":
            raise api_error(409, "workspace_retired", "Retired workspaces cannot be edited")
        state = session.get(ModelRuntimeState, 1)
        if (
            state is None
            or (
                expected_model_runtime_release_id is None
                and state.active_model_release_id != model_release_id
            )
            or (
                expected_model_runtime_release_id is not None
                and state.active_model_release_id != expected_model_runtime_release_id
            )
        ):
            raise api_error(
                409,
                "change_set_snapshot_retry",
                "The selected model changed before current-live capture; retry with the current model",
            )
        base = ChangeSetBase(
            workspace_key=workspace_key,
            model_release_id=state.active_model_release_id,
            model_runtime_version=state.version,
        )
        session.add(base)
        session.flush()
        live_objects, attributes, live_relations = _load_live_membership(session, workspace_key)
        for item in live_objects:
            session.add(
                ChangeSetBaseObject(
                    base_id=base.id,
                    object_id=item.id,
                    application_key=item.application_key,
                    object_type_key=item.object_type_key,
                    name=item.name,
                    parent_object_id=item.parent_object_id,
                    attributes={
                        key: value for key, (_row_id, value) in attributes[item.id].items()
                    },
                    version=item.version,
                )
            )
        for item in live_relations:
            session.add(
                ChangeSetBaseRelation(
                    base_id=base.id,
                    relation_id=item.id,
                    relation_type_key=item.relation_type_key,
                    from_object_id=item.from_object_id,
                    to_object_id=item.to_object_id,
                    attributes=dict(item.attributes or {}),
                    version=item.version,
                )
            )
        change_set = ChangeSet(
            workspace_key=workspace_key,
            model_release_id=model_release_id,
            base_id=base.id,
            name=name,
        )
        session.add(change_set)
        session.flush()
        if validate_selected_model:
            require_change_set_compatible(
                session,
                change_set,
                change_set_model(session, change_set),
                source_release_id=base.model_release_id,
            )
        record_change_set_created(session, change_set=change_set)
        matrix_states.record_change_set(session, change_set)
        session.commit()
        session.refresh(change_set)
        return change_set
    except Exception:
        session.rollback()
        raise


def _load_live_membership(
    session: Session, workspace_key: str
) -> tuple[list[RdmObject], dict[str, dict[str, tuple[str, Any]]], list[ObjectRelation]]:
    """Load the graph after current-live capture has acquired its SQLite writer reservation."""
    objects = list(
        session.scalars(select(RdmObject).where(RdmObject.workspace_key == workspace_key))
    )
    object_ids = [item.id for item in objects]
    attributes = load_attribute_values(session, object_ids)
    relations: list[ObjectRelation] = []
    if object_ids:
        relations = list(
            session.scalars(
                select(ObjectRelation).where(
                    ObjectRelation.from_object_id.in_(object_ids),
                    ObjectRelation.to_object_id.in_(object_ids),
                )
            )
        )
    return objects, attributes, relations


def update_change_set(
    session: Session, change_set_id: str, expected_version: int, name: str | None
) -> ChangeSet:
    change_set = load_change_set(session, change_set_id, for_update=True)
    writes = ChangeSetWrites(session, change_set)
    previous_name = change_set.name
    writes.claim(expected_version)
    if previous_name != name:
        record_change_set_renamed(session, change_set=change_set, from_name=previous_name, to_name=name)
    change_set.name = name
    session.commit()
    return change_set


def discard_change_set(session: Session, change_set_id: str, expected_version: int) -> None:
    change_set = load_change_set(session, change_set_id, for_update=True)
    writes = ChangeSetWrites(session, change_set)
    writes.claim(expected_version)
    record_change_set_discarded(session, change_set=change_set)
    delete_change_set_and_base(session, change_set)
    session.commit()


def delete_change_set_and_base(session: Session, change_set: ChangeSet) -> None:
    """Remove a private base explicitly because SQLite does not enable FK cascades by default."""
    base_id = change_set.base_id
    delete_change_set_relation_set_versions(session, change_set.id)
    delete_owner_values(session, change_set.id)
    matrix_states.drop_owner(
        session, matrix_states.Owner("change_set", change_set.id, change_set.workspace_key)
    )
    if base_id is not None:
        matrix_states.drop_owner(
            session, matrix_states.Owner("base", base_id, change_set.workspace_key)
        )
    session.delete(change_set)
    session.flush()
    if base_id is None:
        return
    delete_owner_values(session, base_id)
    session.execute(
        delete(ChangeSetBaseRelation).where(ChangeSetBaseRelation.base_id == base_id)
    )
    session.execute(
        delete(ChangeSetBaseObject).where(ChangeSetBaseObject.base_id == base_id)
    )
    session.execute(delete(ChangeSetBase).where(ChangeSetBase.id == base_id))
