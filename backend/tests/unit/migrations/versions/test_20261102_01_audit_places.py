"""``migrations/versions/20261102_01_audit_places.py``: placing existing entries (0.12 Z6, D341).

The rows here are entries as the release before Z6 wrote them, made by this test (no client can
write an entry without its workspace now): a change set's work named only its change set. The
migration's statements place each from the change set while it is open, from the publication entry
naming it once published, or from its lifecycle entries naming a workspace that existed then; an
entry naming none of them stays unplaced.
"""

import importlib
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from scenario import W1
from sqlalchemy import select, text, update

from app.db import SessionLocal
from app.models.database import AuditEvent, ChangeSet, WorkspaceModel

migration = importlib.import_module("app.migrations.versions.20261102_01_audit_places")


def _entry(session, aggregate_type: str, aggregate_id: str, **changes) -> AuditEvent:
    event = AuditEvent(
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        action="created",
        version=1,
        changes=changes,
    )
    session.add(event)
    session.flush()
    return event


def _as_before(session, *events: AuditEvent) -> None:
    """The entries as the release before wrote them: no workspace, no subject."""
    session.execute(
        update(AuditEvent)
        .where(AuditEvent.sequence_id.in_([e.sequence_id for e in events]))
        .values(workspace_key=None, subject=None)
    )


def _places(session, *events: AuditEvent) -> list[str | None]:
    session.expire_all()
    return [
        session.scalar(
            select(AuditEvent.workspace_key).where(AuditEvent.sequence_id == e.sequence_id)
        )
        for e in events
    ]


def test_each_change_set_entry_is_placed_where_it_can_be(seeded):
    with SessionLocal() as session:
        release = session.scalar(
            select(WorkspaceModel.model_release_id).where(WorkspaceModel.workspace_key == W1)
        )
        open_set = ChangeSet(id=str(uuid4()), workspace_key=W1, model_release_id=release)
        session.add(open_set)
        published, discarded, unknown = str(uuid4()), str(uuid4()), str(uuid4())
        in_open = _entry(session, "change-set-object", "r1", changeSetId=open_set.id)
        in_published = _entry(session, "relation", "l1", changeSetId=published)
        publication = _entry(session, "publication", "p1", changeSetId=published)
        session.execute(
            update(AuditEvent)
            .where(AuditEvent.sequence_id == publication.sequence_id)
            .values(workspace_key=W1)
        )
        lifecycle = _entry(session, "change-set", discarded, workspaceKey=W1)
        in_discarded = _entry(session, "change-set-object", "r2", changeSetId=discarded)
        stale = _entry(session, "change-set", unknown, workspaceKey=W1)
        session.execute(
            update(AuditEvent)
            .where(AuditEvent.sequence_id == stale.sequence_id)
            .values(occurred_at=datetime.now(UTC) - timedelta(days=36500))
        )
        in_unknown = _entry(session, "change-set-object", "r3", changeSetId=unknown)
        never = _entry(session, "change-set-object", "r4", changeSetId=str(uuid4()))
        _as_before(
            session, in_open, in_published, lifecycle, in_discarded, stale, in_unknown, never
        )

        session.execute(text(migration._PLACES))

        assert _places(session, in_open, in_published, in_discarded, lifecycle) == [W1] * 4
        # A lifecycle entry from before its workspace existed claims nothing (a key made again).
        assert _places(session, stale, in_unknown, never) == [None, None, None]
        session.rollback()


def test_a_change_set_record_is_named_from_the_rows_still_there(seeded):
    with SessionLocal() as session:
        record = session.execute(
            text("SELECT id, object_type_key FROM objects WHERE workspace_key = :w LIMIT 1"),
            {"w": W1},
        ).one()
        named = _entry(session, "change-set-object", record.id, changeSetId=str(uuid4()))
        deleted = _entry(
            session, "change-set-object", "gone", changeSetId=str(uuid4()), objectTypeKey="kept"
        )
        nothing = _entry(session, "change-set-object", "unknown", changeSetId=str(uuid4()))
        _as_before(session, named, deleted, nothing)

        session.execute(text(migration._RECORD_SUBJECTS))
        session.expire_all()

        subjects = [
            session.get(AuditEvent, e.sequence_id).subject for e in (named, deleted, nothing)
        ]
        assert subjects[0]["objectTypeKey"] == record.object_type_key
        assert subjects[1]["objectTypeKey"] == "kept"
        assert subjects[2] is None
        session.rollback()
