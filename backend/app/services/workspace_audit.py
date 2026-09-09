"""Workspace lifecycle audit seam (ADR-024 / WP8).

Workspace lifecycle events are purely workspace-scoped: mutable-draft events use the
``workspace-draft`` aggregate, activation uses the ``workspace-revision`` aggregate and publication
retirement uses the ``workspace`` aggregate (aggregated on the workspace key), all with no
``AuditEventSubject`` rows, so a workspace lifecycle action never amplifies events per object.  The
``changes`` payloads are deliberately bounded identity metadata -- never graph payloads or attribute
values.  Record-level draft CRUD keeps its own ``object-draft`` / ``relation`` aggregates and
per-object subjects (see :mod:`app.services.workspace_revisions`).
"""

from typing import Any

from sqlalchemy.orm import Session

from ..models.database import ModelRelease, WorkspaceDraft, WorkspaceRevision
from .audit import record_audit_event

_AGGREGATE_TYPE = "workspace-draft"
_REVISION_AGGREGATE_TYPE = "workspace-revision"
_WORKSPACE_AGGREGATE_TYPE = "workspace"


def _emit(
    session: Session, *, draft: WorkspaceDraft, action: str, changes: dict[str, Any]
) -> None:
    record_audit_event(
        session,
        aggregate_type=_AGGREGATE_TYPE,
        aggregate_id=draft.id,
        action=action,
        version=draft.version,
        changes=changes,
        object_ids=(),
    )


def _release_public_id(session: Session, model_release_id: int) -> str:
    release = session.get(ModelRelease, model_release_id)
    # WorkspaceDraft/WorkspaceRevision model_release_id are FK RESTRICT, so the release is always
    # present; fall back to the stable integer id exactly like the draft response projection does for
    # a corrupt database.
    return release.public_id if release is not None else str(model_release_id)


def _model_release_public_id(session: Session, draft: WorkspaceDraft) -> str:
    return _release_public_id(session, draft.model_release_id)


def _identity_changes(session: Session, draft: WorkspaceDraft) -> dict[str, Any]:
    changes: dict[str, Any] = {
        "workspaceKey": draft.workspace_key,
        "modelReleaseId": _model_release_public_id(session, draft),
    }
    if draft.name is not None:
        changes["name"] = draft.name
    return changes


def record_draft_created(session: Session, *, draft: WorkspaceDraft) -> None:
    """Record the creation of an empty root workspace draft."""
    _emit(session, draft=draft, action="created", changes=_identity_changes(session, draft))


def record_draft_derived(session: Session, *, draft: WorkspaceDraft) -> None:
    """Record deriving a draft from an active or historical workspace revision."""
    changes = _identity_changes(session, draft)
    if draft.derived_from_revision_id is not None:
        changes["derivedFromRevisionId"] = draft.derived_from_revision_id
    _emit(session, draft=draft, action="derived", changes=changes)


def record_draft_renamed(
    session: Session,
    *,
    draft: WorkspaceDraft,
    from_name: str | None,
    to_name: str | None,
) -> None:
    """Record renaming a draft, preserving the previous and new names."""
    _emit(
        session,
        draft=draft,
        action="renamed",
        changes={"name": {"from": from_name, "to": to_name}},
    )


def record_draft_discarded(session: Session, *, draft: WorkspaceDraft) -> None:
    """Record discarding a mutable draft before its row is deleted."""
    _emit(session, draft=draft, action="discarded", changes={"workspaceKey": draft.workspace_key})


def record_draft_validated(
    session: Session,
    *,
    draft: WorkspaceDraft,
    valid: bool,
    error_codes: list[str],
    object_count: int,
    relation_count: int,
    error_count: int,
) -> None:
    """Record a side-effect-free whole-graph validation outcome.

    The payload is deliberately bounded: only the validity flag, deduplicated error codes and graph
    counts are stored.  Per-object diagnostics, attribute values and unbounded graph payloads are
    never written so a validation cannot amplify audit storage with the draft's contents.
    """
    _emit(
        session,
        draft=draft,
        action="validated",
        changes={
            "valid": valid,
            "errorCodes": sorted(set(error_codes)),
            "objectCount": object_count,
            "relationCount": relation_count,
            "errorCount": error_count,
        },
    )


def record_revision_activated(
    session: Session,
    *,
    revision: WorkspaceRevision,
    draft: WorkspaceDraft,
    object_count: int,
    relation_count: int,
) -> None:
    """Record activating an immutable workspace revision from a mutable draft.

    The event is aggregated on ``workspace-revision`` with the revision as its aggregate id and the
    revision number as the version, and is recorded in the same transaction as the activation so a
    rolled-back activation never leaves an orphan event.  The ``changes`` payload is deliberately
    bounded to identity metadata plus graph counts -- never graph payloads or attribute values -- and
    carries no ``AuditEventSubject`` rows (activating a workspace never amplifies events per object).
    """
    changes: dict[str, Any] = {
        "draftId": draft.id,
        "workspaceKey": revision.workspace_key,
        "modelReleaseId": _release_public_id(session, revision.model_release_id),
        "objectCount": object_count,
        "relationCount": relation_count,
    }
    if revision.derived_from_revision_id is not None:
        changes["derivedFromRevisionId"] = revision.derived_from_revision_id
    if revision.supersedes_revision_id is not None:
        changes["supersedesRevisionId"] = revision.supersedes_revision_id
    record_audit_event(
        session,
        aggregate_type=_REVISION_AGGREGATE_TYPE,
        aggregate_id=revision.id,
        action="activated",
        version=revision.revision_number,
        changes=changes,
        object_ids=(),
    )


def record_publication_retired(
    session: Session, *, revision: WorkspaceRevision
) -> None:
    """Record retiring a workspace's active publication.

    The event is aggregated on the ``workspace`` aggregate with the workspace key as its aggregate id
    (the workspace's stable public/string identity) and the retired revision's revision number as the
    version (see D3a).  It is recorded in the same transaction as the pointer clear and revision
    retire so a rolled-back retirement never leaves an orphan event.  The ``changes`` payload is
    deliberately bounded to the retired revision identity -- never graph payloads or attribute values
    -- and carries no ``AuditEventSubject`` rows (retiring a publication never amplifies events per
    object).  Workspace lifecycle audit stays separate from the record-level draft CRUD aggregates.
    """
    record_audit_event(
        session,
        aggregate_type=_WORKSPACE_AGGREGATE_TYPE,
        aggregate_id=revision.workspace_key,
        action="publication-retired",
        version=revision.revision_number,
        changes={
            "retiredRevisionId": revision.id,
            "revisionNumber": revision.revision_number,
        },
        object_ids=(),
    )
