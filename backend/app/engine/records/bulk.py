"""Writing decided items (0.9.0-alpha.1 PG3b, PG-D12): what a batch lookup collected, in bulk.

The object services decide a write through a batch lookup (``batch_lookup.py``) and write it here;
a single write is a batch of one. Each kind of row goes out in multi-row statements: records,
attribute values and relations through the write unit (``writes.py``), the relation sets the
items' relations advance, and one audit event per item with its subjects (PG-D16). The typed value
index and the stored matrix states follow the rows through their flush hooks, as for any write.
"""

from ...models.database import ChangeSetObject, RdmObject
from ...models.schema import EngineModel
from .audit import record_audit_events
from .batch_lookup import Changes
from .relation_set_versions import increment_set_versions_by
from .writes import ChangeSetWrites, LiveWrites


def write_live(writes: LiveWrites, model: EngineModel, changes: Changes) -> dict[str, RdmObject]:
    """Write decided live items; the written records by ID."""
    rows = writes.write(model, changes)
    increment_set_versions_by(
        writes.session, workspace_key=writes.workspace_key, change_set_id=None, counts=changes.sets
    )
    record_audit_events(writes.session, changes.audit)
    return rows


def write_change_set(writes: ChangeSetWrites, changes: Changes) -> dict[str, ChangeSetObject]:
    """Write decided items of one change set; the change set's written rows by record ID."""
    rows = writes.write(changes)
    increment_set_versions_by(
        writes.session,
        workspace_key=writes.workspace_key,
        change_set_id=writes.change_set_id,
        counts=changes.sets,
    )
    record_audit_events(writes.session, changes.audit)
    return rows
