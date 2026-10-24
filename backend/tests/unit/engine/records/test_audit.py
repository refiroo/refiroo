"""``engine/records/audit.py``: audit entries, and the job that caused them.

J11 reads a batch item's history entry with the job as its cause. Here an entry written inside
``audit_cause`` names the job, and one written after it, as a single write's is, names none.
"""

from scenario import W1
from sqlalchemy import func, select

from app.db import SessionLocal
from app.engine.authorization.writes import SYSTEM, Writer, writing_as
from app.engine.records.audit import (
    AuditEntry,
    audit_actor_of,
    audit_cause,
    record_audit_event,
    record_audit_events,
    trial_run,
)
from app.models.database import AuditEvent, AuditEventSubject, OAuthClient, User, Workspace


def _both(session, aggregate_id: str):
    entry = AuditEntry("object", aggregate_id, "updated", 2, {"name": "x"}, (aggregate_id,))
    return [
        *record_audit_events(session, [entry]),
        record_audit_event(
            session,
            aggregate_type="object",
            aggregate_id=aggregate_id,
            action="updated",
            version=3,
            changes={},
            object_ids=[aggregate_id],
        ),
    ]


def test_entries_name_the_job_only_while_it_causes_them(seeded):
    with SessionLocal() as session:
        with audit_cause(session, "job", "job-1"):
            caused = _both(session, "a")
        single = _both(session, "b")
        assert {(e.cause_kind, e.cause_id) for e in caused} == {("job", "job-1")}
        assert {(e.cause_kind, e.cause_id) for e in single} == {(None, None)}
        session.rollback()


def test_a_trial_run_records_no_entry_and_takes_no_feed_position(seeded):
    """0.10 A3a (D72): a trial run (a preview or a dry run, rolled back) records no audit event and
    no subject and takes no position in the workspace's feed; outside it, entries are recorded."""
    with SessionLocal() as session:
        entry = AuditEntry("object", "t", "updated", 2, {"name": "x"}, ("t",))

        def written():
            return (
                session.scalar(select(func.count()).select_from(AuditEvent)),
                session.scalar(select(func.count()).select_from(AuditEventSubject)),
                session.scalar(select(Workspace.feed_position).where(Workspace.key == W1)),
            )

        before = written()
        with trial_run(session):
            assert record_audit_events(session, [entry], workspace_key=W1) == []
            session.flush()
        assert written() == before
        recorded = record_audit_events(session, [entry], workspace_key=W1)
        session.flush()
        events, subjects, _position = written()
        assert (len(recorded), events, subjects) == (1, before[0] + 1, before[1] + 1)
        assert recorded[0].feed_position is not None
        session.rollback()


def test_entries_name_whoever_the_session_writes_as(seeded):
    """0.12 Z4 (D313): an entry names the caller the session writes as, a request's or a job
    step's requester, whichever way it was built; with no caller, or a job without a requester,
    the engine; one built naming nobody (a failed sign-in) keeps that."""
    with SessionLocal() as session:
        person = User(username="audit-unit", name="Audit unit", active=True)
        client = OAuthClient(name="Audit unit client", active=True)
        session.add_all([person, client])
        session.flush()
        for principal in (("user", person.id), ("client", client.id)):
            with writing_as(session, Writer(None, (), "records.write", principal=principal)):
                assert audit_actor_of(session)["actor_kind"] == principal[0]
                for event in _both(session, f"{principal[0]}-entry"):
                    assert event.actor_kind == principal[0]
                    assert (event.actor_user_id or event.actor_client_id) == principal[1]
        with writing_as(session, SYSTEM):
            assert {e.actor_kind for e in _both(session, "requester-less")} == {"engine"}
        assert {e.actor_kind for e in _both(session, "no-writer")} == {"engine"}
        nobody = AuditEvent(
            aggregate_type="sign-in", aggregate_id="x", action="failed", version=1, changes={},
            actor_kind=None,
        )  # fmt: skip
        session.add(nobody)
        session.flush()
        assert nobody.actor_kind is None
        session.rollback()
