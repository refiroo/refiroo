"""``engine/reads/changes.py``: which entries a caller may see (0.12 Z6, D342).

J44.8 reads the rule through the API for a reader, a Security administrator and a model
administrator. Here the condition is checked for each kind of caller over one entry of each place:
in a workspace, in another, model administration outside workspaces, and a deleted workspace's.
"""

from scenario import W1
from sqlalchemy import select

from app.db import SessionLocal
from app.engine.authorization.permissions import Holding, Permissions
from app.engine.reads.changes import visible
from app.models.database import AuditEvent


def _holding(groups: tuple[str, ...], workspace: str | None) -> Holding:
    return Holding("g", "r", "R", groups, workspace, (), (), None, None)


CALLERS = {
    "instance reader": Permissions((_holding(("browse",), None),)),
    "reader here": Permissions((_holding(("browse",), W1),)),
    "model author": Permissions((_holding(("model-authoring",), None),)),
    "security only": Permissions((_holding(("security-admin",), None),)),
}
SEEN = {
    "instance reader": {"here", "elsewhere", "gone"},
    "reader here": {"here"},
    "model author": {"draft"},
    "security only": set(),
}


def test_each_caller_sees_its_own(seeded):
    with SessionLocal() as session:
        entries = {
            "here": AuditEvent(aggregate_type="object", workspace_key=W1),
            "elsewhere": AuditEvent(aggregate_type="object", workspace_key="elsewhere"),
            "draft": AuditEvent(aggregate_type="model_draft"),
            "gone": AuditEvent(aggregate_type="change-set-object"),
        }
        for name, entry in entries.items():
            entry.aggregate_id, entry.action, entry.version, entry.changes = name, "x", 1, {}
            session.add(entry)
        session.flush()
        ids = {entry.sequence_id: name for name, entry in entries.items()}
        for caller, permissions in CALLERS.items():
            rows = session.scalars(
                select(AuditEvent.sequence_id).where(
                    AuditEvent.sequence_id.in_(ids), visible(permissions)
                )
            )
            assert {ids[row] for row in rows} == SEEN[caller], caller
        session.rollback()
