import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from ..errors import api_error
from ..models.database import AuditEvent, ModelDraft, ModelRelease


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


def load_draft(session: Session, draft_id: str) -> ModelDraft:
    draft = session.scalar(select(ModelDraft).where(ModelDraft.public_id == draft_id))
    if draft is None:
        raise api_error(404, "model_draft_not_found", f"Model draft '{draft_id}' not found")
    return draft


def load_draft_for_update(session: Session, draft_id: str) -> ModelDraft:
    draft = session.scalar(
        select(ModelDraft)
        .where(ModelDraft.public_id == draft_id)
        .with_for_update()
    )
    if draft is None:
        raise api_error(404, "model_draft_not_found", f"Model draft '{draft_id}' not found")
    return draft


def update_draft(
    session: Session,
    draft_id: str,
    expected_version: int,
    *,
    name: str | None,
    model: dict[str, Any] | None,
) -> ModelDraft:
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

    result = session.execute(
        update(ModelDraft)
        .where(ModelDraft.id == draft.id, ModelDraft.version == expected_version)
        .values(**values)
    )
    if result.rowcount != 1:
        raise api_error(
            409,
            "version_conflict",
            f"Model draft '{draft_id}' has changed",
            {"expectedVersion": expected_version, "actualVersion": draft.version},
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
        raise api_error(
            409,
            "version_conflict",
            f"Model draft '{draft_id}' has changed",
            {"expectedVersion": expected_version, "actualVersion": draft.version},
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
    if draft.version != expected_version:
        raise api_error(
            409,
            "version_conflict",
            f"Model draft '{draft.public_id}' has changed",
            {"expectedVersion": expected_version, "actualVersion": draft.version},
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
        raise api_error(
            404, "model_release_not_found", f"Model release '{release_id}' not found"
        )
    return release


def _audit_summary(
    draft: ModelDraft, base_release_id: str | None, changed_fields: list[str]
) -> dict[str, Any]:
    canonical = json.dumps(draft.model_json, sort_keys=True, separators=(",", ":"))
    return jsonable_encoder(
        {
            "name": draft.name,
            "baseReleaseId": base_release_id,
            "modelHash": hashlib.sha256(canonical.encode()).hexdigest(),
            "changedFields": changed_fields,
        }
    )
