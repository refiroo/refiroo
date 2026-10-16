"""Every row a write adds or removes, live or in one change set.

A write operation opens the unit for its context and adds, claims and removes records, relations
and attribute values through it: ``LiveWrites`` for a workspace's live graph, ``ChangeSetWrites``
for one change set. Nothing else in the engine constructs or deletes those rows
(``tests/test_boundaries.py`` holds it), so what every write must do happens here once: a Core
statement notes what it changed for the stored matrix states, and a live write starts at
``LiveWrites._begin``, which takes the workspace lock.

Records created and updated through the object services are decided first and written together
(``write``, 0.9.0-alpha.1 PG3b): a chunk's rows of each kind go out in multi-row statements.

The operation keeps what only it knows: which rules to run (``rules.py``), what to record in the
audit log, and when to commit. In-place edits of a row the unit handed out (a name, a parent, new
values of a change set row) stay with the operation.
"""

from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from ...errors import api_error
from ...models.database import (
    AttributeValue,
    AuditEvent,
    ChangeSet,
    ChangeSetObject,
    ChangeSetRelation,
    ObjectRelation,
    RdmObject,
    Workspace,
)
from ...models.schema import EngineModel
from ..indexes import matrix_states, unique_values
from ..model import expected_release
from .audit import AuditEntry, record_audit_event, record_audit_events
from .batch_lookup import Changes
from .values import VALUE_COLUMNS, normalize_value

# Change sets whose version a job has claimed for all its items, in ``Session.info``.
_HELD_CLAIMS = "held_change_set_claims"
# IDs bound into one statement.
_CHUNK = 500


def _chunks(ids: Iterable[str]) -> Iterator[list[str]]:
    ordered = list(ids)
    for start in range(0, len(ordered), _CHUNK):
        yield ordered[start : start + _CHUNK]


class LiveWrites:
    """The live graph of one workspace."""

    def __init__(self, session: Session, workspace_key: str) -> None:
        self.session = session
        self.workspace_key = workspace_key
        self.change_set_id: str | None = None
        self._begin()

    def _begin(self) -> None:
        """Where every live write starts, before it reads what it changes: the workspace lock
        (PG-D5).

        ``FOR NO KEY UPDATE`` on the workspace row serializes the live writes of one workspace, so
        what a write checks in code (unique values, parent cycles, cardinality, required relations,
        relation-set versions, matrix states) still holds when it commits, while other workspaces
        write in parallel. Publishing, a current-live capture, retirement and deletion conflict
        with it; rows that only name the workspace (a change set, a job) do not. Lock order:
        workspace, change set, runtime state, records, and a job's row at its checkpoint
        (ARCHITECTURE). Base 0.9 F1 adds the feed position to this row.

        A workspace deleted or retired after the write resolved it is refused here, since those
        transactions committed before the lock was granted.
        """
        status = self.session.scalar(
            select(Workspace.status)
            .where(Workspace.key == self.workspace_key)
            .with_for_update(key_share=True)
        )
        if status is None:
            raise api_error(
                404,
                "WORKSPACE_NOT_FOUND",
                f"Workspace '{self.workspace_key}' was deleted while this request was "
                "processed; nothing was saved",
            )
        if status != "active":
            raise api_error(
                409,
                "WORKSPACE_RETIRED",
                f"Workspace '{self.workspace_key}' was retired while this request was "
                "processed; nothing was saved",
            )
        # A client that built this write on another release than the workspace runs (M6a, D64).
        expected_release.check(self.session, self.workspace_key)

    # --- the audit log and the feed ---------------------------------------------------------------

    def record(self, **event: Any) -> AuditEvent:
        """Audit a change to live data; it takes the workspace's next feed position (Base 0.9 F1)
        under the lock ``_begin`` took. ``event`` as ``audit.record_audit_event`` takes it, with
        ``subject`` naming what the feed entry shows."""
        return record_audit_event(self.session, workspace_key=self.workspace_key, **event)

    def record_all(self, entries: list[AuditEntry]) -> list[AuditEvent]:
        """Audit decided changes to live data, in order, with consecutive feed positions."""
        return record_audit_events(self.session, entries, workspace_key=self.workspace_key)

    # --- records ---------------------------------------------------------------------------------

    def add_object(
        self,
        *,
        application_key: str,
        object_type_key: str,
        name: str,
        parent_object_id: str | None,
        object_id: str | None = None,
        version: int | None = None,
    ) -> RdmObject:
        item = RdmObject(
            workspace_key=self.workspace_key,
            application_key=application_key,
            object_type_key=object_type_key,
            parent_object_id=parent_object_id,
            name=name,
        )
        if object_id is not None:
            item.id = object_id
        if version is not None:
            item.version = version
        self.session.add(item)
        self.session.flush()
        return item

    def claim_object(self, item: RdmObject, expected_version: int) -> None:
        result = self.session.execute(
            update(RdmObject)
            .where(RdmObject.id == item.id, RdmObject.version == expected_version)
            .values(version=expected_version + 1, updated_at=datetime.now(UTC))
            .execution_options(synchronize_session=False)
        )
        if result.rowcount != 1:
            current = self.session.scalar(select(RdmObject.version).where(RdmObject.id == item.id))
            raise api_error(
                409, "VERSION_CONFLICT", "Object version has changed", {"currentVersion": current}
            )
        self.session.refresh(item)

    def write(self, model: EngineModel, changes: Changes) -> dict[str, RdmObject]:
        """Write what decided items change, each kind of row in multi-row statements: the
        relations they remove, their new records, then the records they change, their attribute
        values and the relations they add. Returns the written records by ID.

        Relations go first so a record moved away and back gets its new containment edge after
        the old one is gone; new records go before the rows that name them.
        """
        session = self.session
        if changes.removed:
            matrix_states.note_relations(session, changes.removed.values())
            for chunk in _chunks(sorted(changes.removed)):
                session.execute(delete(ObjectRelation).where(ObjectRelation.id.in_(chunk)))
        rows: dict[str, RdmObject] = {}
        for object_id, record in changes.records.items():
            if object_id in changes.created:
                rows[object_id] = RdmObject(
                    id=object_id,
                    workspace_key=self.workspace_key,
                    application_key=record.application_key,
                    object_type_key=record.object_type_key,
                    parent_object_id=record.parent_object_id,
                    name=record.name,
                    version=record.version,
                )
        session.add_all(rows.values())
        session.flush()
        updated = [object_id for object_id in changes.records if object_id not in changes.created]
        stored = {
            row.id: row
            for chunk in _chunks(updated)
            for row in session.scalars(select(RdmObject).where(RdmObject.id.in_(chunk)))
        }
        now = datetime.now(UTC)
        for object_id in updated:
            record, row = changes.records[object_id], stored[object_id]
            row.name = record.name
            row.parent_object_id = record.parent_object_id
            row.version = record.version
            row.updated_at = now
            rows[object_id] = row
        self._save_saved_values(model, changes)
        if changes.changed:
            # Through the ORM, so the matrix states follow the attribute change (ADR-033).
            for chunk in _chunks(sorted(changes.changed)):
                for row in session.scalars(
                    select(ObjectRelation).where(ObjectRelation.id.in_(chunk))
                ):
                    relation = changes.changed[row.id]
                    row.attributes = dict(relation.attributes)
                    row.version = relation.version
                    row.updated_at = now
        session.add_all(
            ObjectRelation(
                id=relation.relation_id,
                relation_type_key=relation.relation_type_key,
                from_object_id=relation.from_object_id,
                to_object_id=relation.to_object_id,
                attributes=relation.attributes,
                version=relation.version,
            )
            for relation in changes.added.values()
        )
        session.flush()
        unique_values.check(session, model, changes.saved)
        return rows

    def _save_saved_values(self, model: EngineModel, changes: Changes) -> None:
        """Each saved value in its typed column; a row saved again counts a version per save."""
        existing = [object_id for object_id in changes.saved if object_id not in changes.created]
        stored = {
            (row.object_id, row.attribute_type_key): row
            for chunk in _chunks(existing)
            for row in self.session.scalars(
                select(AttributeValue).where(AttributeValue.object_id.in_(chunk))
            )
        }
        for object_id, saved in changes.saved.items():
            attributes = changes.records[object_id].attributes
            for key, count in saved.items():
                definition = model.attribute_type(key)
                if definition is None:
                    raise api_error(500, "INTERNAL_ERROR", f"Unknown model attribute '{key}'")
                row = stored.get((object_id, key))
                if row is None:
                    row = AttributeValue(
                        object_id=object_id,
                        attribute_type_key=key,
                        value_type=definition.valueType,
                        version=count,
                    )
                    self.session.add(row)
                else:
                    row.version += count
                for column in set(VALUE_COLUMNS.values()):
                    setattr(row, column, None)
                setattr(
                    row,
                    VALUE_COLUMNS[definition.valueType],
                    normalize_value(definition, attributes.get(key)),
                )

    def save_values(self, model: EngineModel, object_id: str, attributes: dict[str, Any]) -> None:
        existing = {
            item.attribute_type_key: item
            for item in self.session.scalars(
                select(AttributeValue).where(
                    AttributeValue.object_id == object_id,
                    AttributeValue.attribute_type_key.in_(attributes),
                )
            )
        }
        for key, value in attributes.items():
            definition = model.attribute_type(key)
            if definition is None:
                raise api_error(500, "INTERNAL_ERROR", f"Unknown model attribute '{key}'")
            row = existing.get(key)
            if row is None:
                row = AttributeValue(
                    object_id=object_id,
                    attribute_type_key=key,
                    value_type=definition.valueType,
                )
                self.session.add(row)
            else:
                row.version += 1
            # Change set rows carry the JSON form; typed columns need the declared Python type.
            for column in set(VALUE_COLUMNS.values()):
                setattr(row, column, None)
            setattr(row, VALUE_COLUMNS[definition.valueType], normalize_value(definition, value))

    def remove_value(self, object_id: str, attribute_type_key: str) -> None:
        """Delete one attribute value row (404 when absent)."""
        row = self.session.scalar(
            select(AttributeValue).where(
                AttributeValue.object_id == object_id,
                AttributeValue.attribute_type_key == attribute_type_key,
            )
        )
        if not row:
            raise api_error(
                404,
                "ATTRIBUTE_NOT_FOUND",
                f"Attribute '{attribute_type_key}' has no value on object '{object_id}'",
            )
        self.session.delete(row)

    def remove_records(
        self, objects: list[RdmObject], relation_ids: set[str], endpoint_ids: set[str]
    ) -> None:
        """Delete relations, attribute values and records in one batch.

        Containment pointers are detached first, since the parent key is RESTRICT and a batch may
        hold a parent and its children in any order.
        """
        object_ids = {item.id for item in objects}
        if relation_ids:
            matrix_states.note_rows(self.session, endpoint_ids)
            self.session.execute(delete(ObjectRelation).where(ObjectRelation.id.in_(relation_ids)))
        self.session.execute(delete(AttributeValue).where(AttributeValue.object_id.in_(object_ids)))
        self.session.execute(
            update(RdmObject).where(RdmObject.id.in_(object_ids)).values(parent_object_id=None)
        )
        for item in objects:
            self.session.delete(item)

    # --- relations -------------------------------------------------------------------------------

    def add_relation(
        self,
        relation_type_key: str,
        from_object_id: str,
        to_object_id: str,
        attributes: dict[str, Any] | None = None,
        *,
        flush: bool = True,
    ) -> ObjectRelation:
        relation = ObjectRelation(
            relation_type_key=relation_type_key,
            from_object_id=from_object_id,
            to_object_id=to_object_id,
            attributes=attributes if attributes is not None else {},
        )
        self.session.add(relation)
        if flush:
            self.session.flush()
        return relation

    def claim_relation(self, relation: ObjectRelation, expected_version: int) -> None:
        result = self.session.execute(
            update(ObjectRelation)
            .where(ObjectRelation.id == relation.id, ObjectRelation.version == expected_version)
            .values(version=expected_version + 1, updated_at=datetime.now(UTC))
            .execution_options(synchronize_session=False)
        )
        if result.rowcount != 1:
            current = self.session.scalar(
                select(ObjectRelation.version).where(ObjectRelation.id == relation.id)
            )
            raise api_error(
                409, "VERSION_CONFLICT", "Relation version has changed", {"currentVersion": current}
            )
        self.session.refresh(relation)

    def remove_relation(self, relation: ObjectRelation) -> None:
        self.session.delete(relation)

    # --- publishing ------------------------------------------------------------------------------

    def apply_publication(self, model: EngineModel, merged: Any) -> None:
        """Apply a published change set's delta: remove its tombstoned rows, upsert the records and
        relations it authored, and leave every untouched live row as it is."""
        session = self.session
        if merged.removed_relation_ids:
            matrix_states.note_relations_removed(session, merged.removed_relation_ids)
            session.execute(
                delete(ObjectRelation).where(ObjectRelation.id.in_(merged.removed_relation_ids))
            )
        if merged.removed_object_ids:
            matrix_states.note_rows(session, merged.removed_object_ids)
            # The parent FK is RESTRICT; detach the removed rows from each other so bulk deletion
            # cannot trip the constraint regardless of parent/child ordering. Surviving authored
            # children may still point at a tombstoned parent. Detach them before deleting the
            # removed rows; their final parent is assigned after all upserts exist.
            session.execute(
                update(RdmObject)
                .where(
                    RdmObject.parent_object_id.in_(merged.removed_object_ids),
                    ~RdmObject.id.in_(merged.removed_object_ids),
                )
                .values(parent_object_id=None)
            )
            session.execute(
                update(RdmObject)
                .where(RdmObject.id.in_(merged.removed_object_ids))
                .values(parent_object_id=None)
            )
            session.execute(
                delete(AttributeValue).where(
                    AttributeValue.object_id.in_(merged.removed_object_ids)
                )
            )
            session.execute(delete(RdmObject).where(RdmObject.id.in_(merged.removed_object_ids)))
        authored_objects = {
            item.object_id: item
            for item in merged.membership.objects
            if item.object_id in merged.authored_object_ids
        }
        # No autoflush, and no query per row: every flush scans the session's whole identity map,
        # which the merge filled with the workspace, so a flush per record made the apply cost
        # records × workspace (24 s for 1,000 records in 26,000, 0.9 T1a). Flushes are explicit.
        with session.no_autoflush:
            live_objects = {
                item.id: item
                for item in session.scalars(
                    select(RdmObject).where(RdmObject.workspace_key == self.workspace_key)
                )
            }
            for object_id in sorted(authored_objects):
                authored = authored_objects[object_id]
                live = live_objects.get(object_id)
                if live is None:
                    # Added, not flushed one by one (``add_object`` flushes): the flush below.
                    live_objects[object_id] = RdmObject(
                        id=object_id,
                        workspace_key=self.workspace_key,
                        application_key=authored.application_key,
                        object_type_key=authored.object_type_key,
                        name=authored.name,
                        parent_object_id=None,
                        version=authored.version,
                    )
                    session.add(live_objects[object_id])
                else:
                    live.application_key = authored.application_key
                    live.object_type_key = authored.object_type_key
                    live.name = authored.name
                    live.version = authored.version
            session.flush()
            # Attribute rows are replaced in Core below; their records' condition values may change.
            matrix_states.note_cells(session, authored_objects)
            for object_id in sorted(authored_objects):
                authored = authored_objects[object_id]
                attribute_delete = delete(AttributeValue).where(
                    AttributeValue.object_id == object_id
                )
                if authored.attributes:
                    attribute_delete = attribute_delete.where(
                        ~AttributeValue.attribute_type_key.in_(set(authored.attributes))
                    )
                # Not synchronised with the session: evaluating the criteria against every loaded
                # object, per record, cost more than the statements.
                session.execute(attribute_delete.execution_options(synchronize_session=False))
                self.save_values(model, object_id, authored.attributes or {})
            session.flush()
            unique_values.check(session, model, authored_objects)
            for object_id in sorted(authored_objects):
                # Set containment pointers only after every merged object row exists (whole-graph
                # validation guarantees the parent is present in the merged graph) so a new parent
                # never precedes its row.
                live_objects[object_id].parent_object_id = authored_objects[object_id].parent_object_id
            authored_relations = sorted(
                (
                    item
                    for item in merged.membership.relations
                    if item.relation_id in merged.authored_relation_ids
                ),
                key=lambda item: item.relation_id,
            )
            relation_ids = [item.relation_id for item in authored_relations]
            live_relations: dict[str, ObjectRelation] = {}
            for start in range(0, len(relation_ids), 1000):
                live_relations.update(
                    (item.id, item)
                    for item in session.scalars(
                        select(ObjectRelation).where(
                            ObjectRelation.id.in_(relation_ids[start : start + 1000])
                        )
                    )
                )
            for authored in authored_relations:
                live = live_relations.get(authored.relation_id)
                if live is None:
                    session.add(
                        ObjectRelation(
                            id=authored.relation_id,
                            relation_type_key=authored.relation_type_key,
                            from_object_id=authored.from_object_id,
                            to_object_id=authored.to_object_id,
                            attributes=authored.attributes or {},
                            version=authored.version,
                        )
                    )
                else:
                    live.relation_type_key = authored.relation_type_key
                    live.from_object_id = authored.from_object_id
                    live.to_object_id = authored.to_object_id
                    live.attributes = authored.attributes or {}
                    live.version = authored.version


class ChangeSetWrites:
    """The rows of one change set: each record or relation it changes has its own row, copied from
    the base on first change; a deletion is a tombstone row."""

    def __init__(self, session: Session, change_set: ChangeSet) -> None:
        self.session = session
        self.change_set = change_set
        self.change_set_id = change_set.id
        self.workspace_key = change_set.workspace_key
        expected_release.check(
            session, self.workspace_key, change_set.model_release_id, change_set_id=change_set.id
        )

    def record(self, **event: Any) -> AuditEvent:
        """Audit a change set edit; it changes no live data, so it takes no feed position."""
        event.pop("subject", None)
        return record_audit_event(self.session, **event)

    def record_all(self, entries: list[AuditEntry]) -> list[AuditEvent]:
        return record_audit_events(self.session, entries)

    def claim(
        self,
        expected: int,
        *,
        conflict_code: str = "CHANGE_SET_VERSION_CONFLICT",
        conflict_message: str = "Change set version has changed",
    ) -> None:
        """Claim the change set's version for this write.

        While a job holds the claim (``hold_claim``), the job's items are parts of one write and
        claim nothing more.
        """
        if self.change_set_id in self.session.info.get(_HELD_CLAIMS, ()):
            return
        change_set = self.change_set
        if change_set.version != expected:
            raise api_error(409, conflict_code, conflict_message)
        # The conditional update is the claim and the version bump in one statement, before any
        # candidate write is flushed.
        with self.session.no_autoflush:
            result = self.session.execute(
                update(ChangeSet)
                .where(ChangeSet.id == change_set.id, ChangeSet.version == expected)
                .values(version=expected + 1, updated_at=datetime.now(UTC))
                .execution_options(synchronize_session=False)
            )
            if result.rowcount != 1:
                raise api_error(409, conflict_code, conflict_message)
            self.session.refresh(change_set, attribute_names=["version", "updated_at"])

    @contextmanager
    def hold_claim(self, expected: int) -> Iterator[None]:
        """Claim the change set's version once for every write made meanwhile (INTEGRATION_API
        P3): a batch in a change set advances its version once, like one single write."""
        self.claim(expected)
        held = self.session.info.setdefault(_HELD_CLAIMS, set())
        held.add(self.change_set_id)
        try:
            yield
        finally:
            held.discard(self.change_set_id)

    def write(self, changes: Changes) -> dict[str, ChangeSetObject]:
        """Write what decided items change, each kind of row in multi-row statements: the
        change set's own row for every record they create or change (copied from the base on
        first change), a tombstone for every relation they remove, and the relations they add.
        Returns the written rows by record ID."""
        session = self.session
        stored = {
            row.object_id: row
            for chunk in _chunks(
                object_id for object_id in changes.records if object_id not in changes.created
            )
            for row in session.scalars(
                select(ChangeSetObject).where(
                    ChangeSetObject.change_set_id == self.change_set_id,
                    ChangeSetObject.object_id.in_(chunk),
                )
            )
        }
        rows: dict[str, ChangeSetObject] = {}
        for object_id, record in changes.records.items():
            row = stored.get(object_id)
            if row is None:
                row = ChangeSetObject(
                    change_set_id=self.change_set_id,
                    object_id=object_id,
                    application_key=record.application_key,
                    object_type_key=record.object_type_key,
                )
                session.add(row)
            row.name = record.name
            row.parent_object_id = record.parent_object_id
            row.attributes = dict(record.attributes)
            row.version = record.version
            row.is_deleted = False
            rows[object_id] = row
        removed = {
            row.relation_id: row
            for chunk in _chunks(sorted(changes.removed))
            for row in session.scalars(
                select(ChangeSetRelation).where(
                    ChangeSetRelation.change_set_id == self.change_set_id,
                    ChangeSetRelation.relation_id.in_(chunk),
                )
            )
        }
        for relation_id, relation in changes.removed.items():
            row = removed.get(relation_id)
            if row is None:
                session.add(
                    ChangeSetRelation(
                        change_set_id=self.change_set_id,
                        relation_id=relation_id,
                        relation_type_key=relation.relation_type_key,
                        from_object_id=relation.from_object_id,
                        to_object_id=relation.to_object_id,
                        attributes=dict(relation.attributes or {}),
                        version=relation.version + 1,
                        is_deleted=True,
                    )
                )
            else:
                row.version += 1
                row.is_deleted = True
        owned = {
            row.relation_id: row
            for chunk in _chunks(sorted(changes.changed))
            for row in session.scalars(
                select(ChangeSetRelation).where(
                    ChangeSetRelation.change_set_id == self.change_set_id,
                    ChangeSetRelation.relation_id.in_(chunk),
                )
            )
        }
        for relation_id, relation in changes.changed.items():
            row = owned.get(relation_id)
            if row is None:
                row = ChangeSetRelation(
                    change_set_id=self.change_set_id,
                    relation_id=relation_id,
                    relation_type_key=relation.relation_type_key,
                    from_object_id=relation.from_object_id,
                    to_object_id=relation.to_object_id,
                )
                session.add(row)
            row.attributes = dict(relation.attributes)
            row.version = relation.version
            row.is_deleted = False
        session.add_all(
            ChangeSetRelation(
                change_set_id=self.change_set_id,
                relation_id=relation.relation_id,
                relation_type_key=relation.relation_type_key,
                from_object_id=relation.from_object_id,
                to_object_id=relation.to_object_id,
                attributes=relation.attributes,
                version=relation.version,
            )
            for relation in changes.added.values()
        )
        session.flush()
        return rows

    # --- records ---------------------------------------------------------------------------------

    def stored_object(self, object_id: str) -> ChangeSetObject | None:
        return self.session.scalar(
            select(ChangeSetObject).where(
                ChangeSetObject.change_set_id == self.change_set_id,
                ChangeSetObject.object_id == object_id,
            )
        )

    def own_object(self, record: Any, *, flush: bool = False) -> ChangeSetObject:
        """The change set's own row for an effective record, copied from its base when it has none."""
        row = self.stored_object(record.object_id)
        if row is None:
            row = ChangeSetObject(
                change_set_id=self.change_set_id,
                object_id=record.object_id,
                application_key=record.application_key,
                object_type_key=record.object_type_key,
                name=record.name,
                parent_object_id=record.parent_object_id,
                attributes=dict(record.attributes or {}),
                version=record.version,
            )
            self.session.add(row)
            if flush:
                self.session.flush()
        return row

    def add_object(
        self,
        *,
        object_id: str,
        application_key: str,
        object_type_key: str,
        name: str,
        parent_object_id: str | None,
        attributes: dict[str, Any],
    ) -> ChangeSetObject:
        row = ChangeSetObject(
            change_set_id=self.change_set_id,
            object_id=object_id,
            application_key=application_key,
            object_type_key=object_type_key,
            name=name,
            parent_object_id=parent_object_id,
            attributes=attributes,
            version=1,
        )
        self.session.add(row)
        return row

    def remove_object(self, record: Any) -> None:
        """Tombstone a record the change set holds."""
        row = self.stored_object(record.object_id)
        if row is None:
            self.session.add(
                ChangeSetObject(
                    change_set_id=self.change_set_id,
                    object_id=record.object_id,
                    application_key=record.application_key,
                    object_type_key=record.object_type_key,
                    name=record.name,
                    parent_object_id=record.parent_object_id,
                    attributes=dict(record.attributes or {}),
                    version=record.version + 1,
                    is_deleted=True,
                )
            )
        else:
            row.version += 1
            row.is_deleted = True

    # --- relations -------------------------------------------------------------------------------

    def stored_relation(self, relation_id: str) -> ChangeSetRelation | None:
        return self.session.scalar(
            select(ChangeSetRelation).where(
                ChangeSetRelation.change_set_id == self.change_set_id,
                ChangeSetRelation.relation_id == relation_id,
            )
        )

    def own_relation(self, relation: Any, *, flush: bool = False) -> ChangeSetRelation:
        """The change set's own row for an effective relation, copied from its base when it has none."""
        row = self.stored_relation(relation.relation_id)
        if row is None:
            row = ChangeSetRelation(
                change_set_id=self.change_set_id,
                relation_id=relation.relation_id,
                relation_type_key=relation.relation_type_key,
                from_object_id=relation.from_object_id,
                to_object_id=relation.to_object_id,
                attributes=dict(relation.attributes or {}),
                version=relation.version,
            )
            self.session.add(row)
            if flush:
                self.session.flush()
        return row

    def add_relation(
        self,
        relation_type_key: str,
        from_object_id: str,
        to_object_id: str,
        attributes: dict[str, Any],
        *,
        relation_id: str | None = None,
    ) -> ChangeSetRelation:
        row = ChangeSetRelation(
            change_set_id=self.change_set_id,
            relation_id=relation_id or str(uuid4()),
            relation_type_key=relation_type_key,
            from_object_id=from_object_id,
            to_object_id=to_object_id,
            attributes=attributes,
            version=1,
        )
        self.session.add(row)
        return row

    def remove_relation(self, relation: Any) -> None:
        """Tombstone a relation the change set holds."""
        row = self.stored_relation(relation.relation_id)
        if row is None:
            self.session.add(
                ChangeSetRelation(
                    change_set_id=self.change_set_id,
                    relation_id=relation.relation_id,
                    relation_type_key=relation.relation_type_key,
                    from_object_id=relation.from_object_id,
                    to_object_id=relation.to_object_id,
                    attributes=dict(relation.attributes or {}),
                    version=relation.version + 1,
                    is_deleted=True,
                )
            )
        else:
            row.version += 1
            row.is_deleted = True
