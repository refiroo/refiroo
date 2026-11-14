import copy
import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, exists, select, update
from sqlalchemy.orm import Session

from ...common.encoding import to_jsonable
from ...common.time import as_utc
from ...errors import api_error, require_version, version_conflict
from ...models.database import AiTask, AuditEvent, ModelDraft, ModelRelease, Workspace
from .workspace_models import load_assignment


def create_draft(
    session: Session,
    *,
    name: str,
    model: dict[str, Any],
    base_release_id: str | None,
) -> ModelDraft:
    base_release = _optional_base_release(session, base_release_id)
    draft = ModelDraft(
        name=name,
        model_json=model,
        base_model_release_id=base_release.id if base_release is not None else None,
    )
    session.add(draft)
    session.flush()
    session.add(
        AuditEvent(
            aggregate_type="model_draft",
            aggregate_id=draft.public_id,
            action="created",
            version=draft.version,
            changes=_audit_summary(draft, base_release_id, ["name", "model"]),
        )
    )
    return draft


def workspace_draft(session: Session, workspace_key: str) -> tuple[ModelDraft, bool]:
    """The draft of the model ``workspace_key`` runs, and whether it was created (0.16 WM1, WM-D2):
    the one it remembers while that is current, else the newest of the running release no workspace
    remembers and no assistant task names, else a new one. A task's draft goes with its task, so it
    is never taken. The assignment is held, so a concurrent first open finds the same draft."""
    assignment, release = load_assignment(session, workspace_key, for_update=True)
    workspace = session.get(Workspace, workspace_key)
    if workspace is None or workspace.status != "active":
        raise api_error(
            409,
            "WORKSPACE_RETIRED",
            f"Workspace '{workspace_key}' is retired; its model is not changed",
            {"workspaceKey": workspace_key},
        )
    remembered = session.scalar(select(ModelDraft).where(ModelDraft.workspace_key == workspace_key))
    if remembered is not None:
        if _still_current(session, remembered, release, assignment.updated_at):
            return remembered, False
        # The workspace's model changed elsewhere: this draft could undo that, so it lets go.
        remembered.workspace_key = None
        session.flush()
    unclaimed = session.scalar(
        select(ModelDraft)
        .where(
            ModelDraft.base_model_release_id == release.id,
            ModelDraft.workspace_key.is_(None),
            ~exists().where(AiTask.draft_id == ModelDraft.id),
        )
        .order_by(ModelDraft.updated_at.desc(), ModelDraft.id.desc())
        .limit(1)
        .with_for_update()
    )
    if unclaimed is not None:
        unclaimed.workspace_key = workspace_key
        return unclaimed, False
    draft = create_draft(
        session,
        name=f"The model of {workspace.label}"[:300],
        model=copy.deepcopy(release.model_json),
        base_release_id=release.public_id,
    )
    draft.workspace_key = workspace_key
    return draft, True


def _still_current(
    session: Session, draft: ModelDraft, running: ModelRelease, assigned_at: datetime
) -> bool:
    """Its base is the running release, or was installed since the workspace's model last changed:
    an apply stopped at the migration preview."""
    if draft.base_model_release_id == running.id:
        return True
    if draft.base_model_release_id is None:
        return False
    base = session.get(ModelRelease, draft.base_model_release_id)
    return base is not None and as_utc(base.installed_at) > as_utc(assigned_at)


def load_draft(session: Session, draft_id: str) -> ModelDraft:
    draft = session.scalar(select(ModelDraft).where(ModelDraft.public_id == draft_id))
    if draft is None:
        raise api_error(404, "MODEL_DRAFT_NOT_FOUND", f"Model draft '{draft_id}' not found")
    return draft


def load_draft_for_update(session: Session, draft_id: str) -> ModelDraft:
    draft = session.scalar(
        select(ModelDraft).where(ModelDraft.public_id == draft_id).with_for_update()
    )
    if draft is None:
        raise api_error(404, "MODEL_DRAFT_NOT_FOUND", f"Model draft '{draft_id}' not found")
    return draft


class _Unchanged:
    """A parameter left out, where ``None`` is a value."""


UNCHANGED = _Unchanged()


def update_draft(
    session: Session,
    draft_id: str,
    expected_version: int,
    *,
    name: str | None,
    model: dict[str, Any] | None,
    profile: dict[str, Any] | None | _Unchanged = UNCHANGED,
) -> ModelDraft:
    """The draft at ``expectedVersion`` + 1 with the given name, model and import profile
    (0.10 A5: ``profile`` left out keeps the draft's)."""
    draft = load_draft(session, draft_id)
    values: dict[str, Any] = {
        "version": expected_version + 1,
        "updated_at": datetime.now(UTC),
    }
    changed_fields: list[str] = []
    if name is not None:
        values["name"] = name
        changed_fields.append("name")
    if model is not None:
        values["model_json"] = model
        changed_fields.append("model")
    if not isinstance(profile, _Unchanged):
        values["profile_json"] = profile
        if profile != draft.profile_json:
            # A step may change the import profile alone (0.10 A5a; R-F11).
            changed_fields.append("profile")

    result = session.execute(
        update(ModelDraft)
        .where(ModelDraft.id == draft.id, ModelDraft.version == expected_version)
        .values(**values)
    )
    if result.rowcount != 1:
        raise version_conflict(
            draft.version,
            "Model draft",
            message=f"Model draft '{draft_id}' has changed",
            details={"expectedVersion": expected_version, "actualVersion": draft.version},
        )
    session.expire(draft)
    session.refresh(draft)
    base_release_id = base_release_public_id(session, draft)
    session.add(
        AuditEvent(
            aggregate_type="model_draft",
            aggregate_id=draft.public_id,
            action="updated",
            version=draft.version,
            changes=_audit_summary(draft, base_release_id, changed_fields),
        )
    )
    return draft


def delete_draft(session: Session, draft_id: str, expected_version: int) -> None:
    draft = load_draft(session, draft_id)
    base_release_id = base_release_public_id(session, draft)
    audit_summary = _audit_summary(draft, base_release_id, ["deleted"])
    result = session.execute(
        delete(ModelDraft).where(
            ModelDraft.id == draft.id,
            ModelDraft.version == expected_version,
        )
    )
    if result.rowcount != 1:
        raise version_conflict(
            draft.version,
            "Model draft",
            message=f"Model draft '{draft_id}' has changed",
            details={"expectedVersion": expected_version, "actualVersion": draft.version},
        )
    session.add(
        AuditEvent(
            aggregate_type="model_draft",
            aggregate_id=draft_id,
            action="deleted",
            version=expected_version,
            changes=audit_summary,
        )
    )


def require_draft_version(draft: ModelDraft, expected_version: int) -> None:
    require_version(
        draft,
        expected_version,
        "Model draft",
        message=f"Model draft '{draft.public_id}' has changed",
        details={"expectedVersion": expected_version, "actualVersion": draft.version},
    )


def base_release_public_id(session: Session, draft: ModelDraft) -> str | None:
    if draft.base_model_release_id is None:
        return None
    return session.scalar(
        select(ModelRelease.public_id).where(ModelRelease.id == draft.base_model_release_id)
    )


def _optional_base_release(session: Session, release_id: str | None) -> ModelRelease | None:
    if release_id is None:
        return None
    release = session.scalar(select(ModelRelease).where(ModelRelease.public_id == release_id))
    if release is None:
        raise api_error(404, "MODEL_RELEASE_NOT_FOUND", f"Model release '{release_id}' not found")
    return release


def _audit_summary(
    draft: ModelDraft, base_release_id: str | None, changed_fields: list[str]
) -> dict[str, Any]:
    canonical = json.dumps(draft.model_json, sort_keys=True, separators=(",", ":"))
    return to_jsonable(
        {
            "name": draft.name,
            "baseReleaseId": base_release_id,
            "modelHash": hashlib.sha256(canonical.encode()).hexdigest(),
            "changedFields": changed_fields,
        }
    )
