"""``engine/records/audit.py``: audit entries, and the job that caused them.

J11 reads a batch item's history entry with the job as its cause. Here an entry written inside
``audit_cause`` names the job, and one written after it, as a single write's is, names none.
"""

from app.db import SessionLocal
from app.engine.records.audit import (
    AuditEntry,
    audit_cause,
    record_audit_event,
    record_audit_events,
)


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
