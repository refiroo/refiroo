"""A change set's life: created from live data or a publication, renamed, claimed and discarded, and its effective membership."""

from sqlalchemy import delete, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from ...db import begin_snapshot_read, is_serialization_failure
from ...errors import api_error
from ...models.database import (
    ChangeSet,
    ChangeSetBase,
    ChangeSetBaseObject,
    ChangeSetBaseRelation,
    ModelRuntimeState,
    Publication,
    Workspace,
)
from ..indexes import matrix_states
from ..indexes.snapshot_values import copy_live, delete_owner_values
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
    """Capture one private base from one snapshot of live data.

    The capture reads at REPEATABLE READ, so graph rows, attributes, edges and the runtime state are
    read from one database snapshot, and it holds share locks on the workspace and runtime-state
    rows, so neither retirement nor a model activation commits while it runs. Either one committing
    after the snapshot began ends the capture with ``change_set_snapshot_retry``, as does any other
    serialization failure; nothing is saved.
    """
    begin_snapshot_read(session)
    try:
        return _capture_current_live(
            session,
            workspace_key,
            model_release_id,
            name=name,
            expected_model_runtime_release_id=expected_model_runtime_release_id,
            validate_selected_model=validate_selected_model,
        )
    except OperationalError as exc:
        session.rollback()
        if not is_serialization_failure(exc):
            raise
        raise api_error(
            409,
            "change_set_snapshot_retry",
            "Live data or the active model changed while the change set was being started; "
            "nothing was saved. Retry starting the change set",
        ) from exc
    except Exception:
        session.rollback()
        raise


def _capture_current_live(
    session: Session,
    workspace_key: str,
    model_release_id: int,
    *,
    name: str | None,
    expected_model_runtime_release_id: int | None,
    validate_selected_model: bool,
) -> ChangeSet:
    workspace = session.scalar(
        select(Workspace).where(Workspace.key == workspace_key).with_for_update(read=True)
    )
    if workspace is None:
        raise api_error(404, "workspace_not_found", f"Workspace '{workspace_key}' not found")
    if workspace.status != "active":
        raise api_error(409, "workspace_retired", "Retired workspaces cannot be edited")
    state = session.scalar(
        select(ModelRuntimeState).where(ModelRuntimeState.id == 1).with_for_update(read=True)
    )
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
    copy_live(session, "base", base.id, workspace_key)
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
    """Remove a change set with its private base, values, set versions and matrix states."""
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
