"""Workspace lifecycle audit seam (ADR-024 / WP8).

Workspace lifecycle events are purely workspace-scoped: change-set events use the
``change-set`` aggregate, publishing uses the ``publication`` aggregate and publication
withdrawal uses the ``workspace`` aggregate (aggregated on the workspace key), all with no
``AuditEventSubject`` rows.  The ``changes`` payloads are deliberately bounded identity metadata --
never graph payloads or attribute values.  What a publish changes in live data is audited per
record and relation by the publish itself (Base 0.9 D15, D32); the ``published`` and
``publication-withdrawn`` events then take the workspace's next feed position (F1).  Record-level change set CRUD keeps its own ``change-set-object`` / ``relation`` aggregates and
per-object subjects (see :mod:`app.engine.change_sets.lifecycle`).
"""

from typing import Any

from sqlalchemy.orm import Session

from ...models.database import AuditEvent, ChangeSet, ModelRelease, Publication
from ..records.audit import record_audit_event

_AGGREGATE_TYPE = "change-set"
_PUBLICATION_AGGREGATE_TYPE = "publication"
_WORKSPACE_AGGREGATE_TYPE = "workspace"


def _emit(
    session: Session, *, change_set: ChangeSet, action: str, changes: dict[str, Any]
) -> None:
    record_audit_event(
        session,
        aggregate_type=_AGGREGATE_TYPE,
        aggregate_id=change_set.id,
        action=action,
        version=change_set.version,
        changes=changes,
        object_ids=(),
    )


def _release_public_id(session: Session, model_release_id: int) -> str:
    release = session.get(ModelRelease, model_release_id)
    # ChangeSet/Publication model_release_id are FK RESTRICT, so the release is always
    # present; fall back to the stable integer id exactly like the change set response projection does for
    # a corrupt database.
    return release.public_id if release is not None else str(model_release_id)


def _model_release_public_id(session: Session, change_set: ChangeSet) -> str:
    return _release_public_id(session, change_set.model_release_id)


def _identity_changes(session: Session, change_set: ChangeSet) -> dict[str, Any]:
    changes: dict[str, Any] = {
        "workspaceKey": change_set.workspace_key,
        "modelReleaseId": _model_release_public_id(session, change_set),
    }
    if change_set.name is not None:
        changes["name"] = change_set.name
    return changes


def record_change_set_created(session: Session, *, change_set: ChangeSet) -> None:
    """Record the creation of an empty root change set."""
    _emit(session, change_set=change_set, action="created", changes=_identity_changes(session, change_set))


def record_change_set_derived(session: Session, *, change_set: ChangeSet) -> None:
    """Record deriving a change set from the current or an earlier publication."""
    changes = _identity_changes(session, change_set)
    if change_set.derived_from_publication_id is not None:
        changes["derivedFromPublicationId"] = change_set.derived_from_publication_id
    _emit(session, change_set=change_set, action="derived", changes=changes)


def record_change_set_renamed(
    session: Session,
    *,
    change_set: ChangeSet,
    from_name: str | None,
    to_name: str | None,
) -> None:
    """Record renaming a change set, preserving the previous and new names."""
    _emit(
        session,
        change_set=change_set,
        action="renamed",
        changes={"name": {"from": from_name, "to": to_name}},
    )


def record_change_set_discarded(session: Session, *, change_set: ChangeSet) -> None:
    """Record discarding a mutable change set before its row is deleted."""
    _emit(session, change_set=change_set, action="discarded", changes={"workspaceKey": change_set.workspace_key})


def record_change_set_validated(
    session: Session,
    *,
    change_set: ChangeSet,
    valid: bool,
    error_codes: list[str],
    object_count: int,
    relation_count: int,
    error_count: int,
) -> None:
    """Record a side-effect-free whole-graph validation outcome.

    The payload is deliberately bounded: only the validity flag, deduplicated error codes and graph
    counts are stored.  Per-object diagnostics, attribute values and unbounded graph payloads are
    never written so a validation cannot amplify audit storage with the change set's contents.
    """
    _emit(
        session,
        change_set=change_set,
        action="validated",
        changes={
            "valid": valid,
            "errorCodes": sorted(set(error_codes)),
            "objectCount": object_count,
            "relationCount": relation_count,
            "errorCount": error_count,
        },
    )


def record_change_set_published(
    session: Session,
    *,
    publication: Publication,
    change_set: ChangeSet,
    object_count: int,
    relation_count: int,
) -> AuditEvent:
    """Record publishing a mutable change set as an immutable publication.

    The event is aggregated on ``publication`` with the publication as its aggregate id and the
    publication number as the version, and is recorded in the same transaction as the publish so a
    rolled-back publish never leaves an orphan event.  The ``changes`` payload is deliberately
    bounded to identity metadata plus graph counts -- never graph payloads or attribute values -- and
    carries no ``AuditEventSubject`` rows.  It is recorded after the entries of what the publish
    changed and takes the next feed position, the publication's (Base 0.9 F1); the caller holds
    the workspace row lock.
    """
    changes: dict[str, Any] = {
        "changeSetId": change_set.id,
        "workspaceKey": publication.workspace_key,
        "modelReleaseId": _release_public_id(session, publication.model_release_id),
        "objectCount": object_count,
        "relationCount": relation_count,
    }
    if publication.derived_from_publication_id is not None:
        changes["derivedFromPublicationId"] = publication.derived_from_publication_id
    if publication.supersedes_publication_id is not None:
        changes["supersedesPublicationId"] = publication.supersedes_publication_id
    return record_audit_event(
        session,
        aggregate_type=_PUBLICATION_AGGREGATE_TYPE,
        aggregate_id=publication.id,
        action="published",
        version=publication.publication_number,
        changes=changes,
        object_ids=(),
        workspace_key=publication.workspace_key,
    )


def record_publication_withdrawn(
    session: Session, *, publication: Publication
) -> None:
    """Record withdrawing a workspace's current publication.

    The event is aggregated on the ``workspace`` aggregate with the workspace key as its aggregate id
    (the workspace's stable public/string identity) and the withdrawn publication's number as the
    version (see D3a).  It is recorded in the same transaction as the pointer clear and status change,
    so a rolled-back withdrawal never leaves an orphan event.  The ``changes`` payload is deliberately
    bounded to the withdrawn publication identity -- never graph payloads or attribute values -- and
    carries no ``AuditEventSubject`` rows (withdrawing a publication never amplifies events per
    object).  It takes the workspace's next feed position (Base 0.9 F1); the caller holds the
    workspace row lock.
    """
    record_audit_event(
        session,
        aggregate_type=_WORKSPACE_AGGREGATE_TYPE,
        aggregate_id=publication.workspace_key,
        action="publication-withdrawn",
        version=publication.publication_number,
        changes={
            "withdrawnPublicationId": publication.id,
            "publicationNumber": publication.publication_number,
        },
        object_ids=(),
        workspace_key=publication.workspace_key,
    )
