"""A page of changes as people read it (Product 0.12 Z6, D343): each entry's workspace by its label,
its change set by its name, what it changed by its name now and its type's name from that
workspace's own model. A few statements per page, whatever its size; values never.
"""

from collections.abc import Iterable
from typing import Any

from sqlalchemy import select, tuple_
from sqlalchemy.orm import Session

from ...common.pagination import Page
from ...engine.identity.principals import actors
from ...engine.model.registry import (
    ModelRegistryUnavailable,
    WorkspaceModelUnavailable,
    model_registry,
)
from ...engine.reads.changes import KIND_OF
from ...engine.records.audit import change_set_of
from ...engine.records.feed import changed_names
from ...models.database import (
    AuditEvent,
    ChangeSet,
    ChangeSetObject,
    ChangeSetRelation,
    ModelDraft,
    ModelRelease,
    ObjectRelation,
    RdmObject,
    Workspace,
)
from ...models.schema import EngineModel
from ..presenters import actor_response
from ..schemas.changes import (
    ChangeAttribute,
    ChangeCause,
    ChangeEntry,
    ChangeObject,
    ChangePage,
    ChangeSetRef,
    ChangeSubject,
    ChangeWorkspace,
)

_ACTIONS = {"publication-withdrawn": "withdrawn"}


def _changes(event: AuditEvent) -> dict[str, Any]:
    return event.changes if isinstance(event.changes, dict) else {}


def _change_set(event: AuditEvent) -> str | None:
    """The change set an entry was made in, or the one a publication published."""
    if event.aggregate_type == "publication":
        return _changes(event).get("changeSetId")
    if KIND_OF[event.aggregate_type] in ("record", "relationship", "change-set"):
        return change_set_of(event.aggregate_type, event.aggregate_id, event.changes)
    return None


class _Names:
    """What a page's entries name, read once for the page."""

    def __init__(self, session: Session, events: list[AuditEvent]) -> None:
        self.session = session
        self.models: dict[str, EngineModel | None] = {}
        keys = {event.workspace_key for event in events if event.workspace_key}
        self.labels = dict(
            session.execute(select(Workspace.key, Workspace.label).where(Workspace.key.in_(keys)))
            .tuples()
            .all()
        )
        change_sets = {item for item in map(_change_set, events) if item}
        self.change_set_names = self._change_set_names(change_sets)
        record_ids: set[str] = set()
        relation_ids: set[str] = set()
        pairs: set[tuple[str, str]] = set()
        relation_pairs: set[tuple[str, str]] = set()
        for event in events:
            kind, change_set = KIND_OF[event.aggregate_type], _change_set(event)
            ids: list[str] = []
            if kind == "record":
                ids = [event.aggregate_id]
            elif kind == "relationship":
                relation_ids.add(event.aggregate_id)
                if change_set:
                    relation_pairs.add((change_set, event.aggregate_id))
                subject = {**_changes(event), **(event.subject or {})}
                ids = [
                    end for end in (subject.get("fromObjectId"), subject.get("toObjectId")) if end
                ]
            record_ids.update(ids)
            if change_set:
                pairs.update((change_set, item) for item in ids)
        self.live_records = {
            row.id: row
            for row in session.execute(
                select(
                    RdmObject.id,
                    RdmObject.name,
                    RdmObject.application_key,
                    RdmObject.object_type_key,
                ).where(RdmObject.id.in_(record_ids))
            )
        }
        self.staged_records = self._staged(ChangeSetObject, ChangeSetObject.object_id, pairs)
        self.live_relations = set(
            session.scalars(select(ObjectRelation.id).where(ObjectRelation.id.in_(relation_ids)))
        )
        self.staged_relations = self._staged(
            ChangeSetRelation, ChangeSetRelation.relation_id, relation_pairs
        )
        drafts = {e.aggregate_id for e in events if e.aggregate_type == "model_draft"}
        self.drafts = dict(
            session.execute(
                select(ModelDraft.public_id, ModelDraft.name).where(
                    ModelDraft.public_id.in_(drafts)
                )
            )
            .tuples()
            .all()
        )
        releases = {
            e.aggregate_id
            for e in events
            if KIND_OF[e.aggregate_type] == "model" and e.aggregate_type != "model_draft"
        }
        self.releases = {
            row.public_id: f"{row.release_name} {row.release_version}"
            for row in session.execute(
                select(
                    ModelRelease.public_id, ModelRelease.release_name, ModelRelease.release_version
                ).where(ModelRelease.public_id.in_(releases))
            )
        }

    def _change_set_names(self, ids: set[str]) -> dict[str, str | None]:
        """An open change set's name; a published or discarded one's as it was last named."""
        self.open_change_sets: set[str] = set()
        if not ids:
            return {}
        names: dict[str, str | None] = dict(
            self.session.execute(select(ChangeSet.id, ChangeSet.name).where(ChangeSet.id.in_(ids)))
            .tuples()
            .all()
        )
        self.open_change_sets = set(names)
        gone = ids - set(names)
        if gone:
            named = AuditEvent.changes["name"].as_string()
            rows = self.session.execute(
                select(AuditEvent.aggregate_id, named)
                .where(
                    AuditEvent.aggregate_type == "change-set",
                    AuditEvent.aggregate_id.in_(gone),
                    named.is_not(None),
                )
                .distinct(AuditEvent.aggregate_id)
                .order_by(AuditEvent.aggregate_id, AuditEvent.sequence_id.desc())
            )
            names.update(rows.tuples().all())
        return names

    def _staged(self, table: Any, column: Any, pairs: set[tuple[str, str]]) -> dict[Any, Any]:
        if not pairs:
            return {}
        rows = self.session.execute(
            select(table).where(tuple_(table.change_set_id, column).in_(sorted(pairs)))
        ).scalars()
        return {(row.change_set_id, getattr(row, column.key)): row for row in rows}

    def model(self, workspace_key: str | None) -> EngineModel | None:
        if workspace_key is None:
            return None
        if workspace_key not in self.models:
            try:
                model = model_registry.resolve_workspace(self.session, workspace_key).model
            except WorkspaceModelUnavailable, ModelRegistryUnavailable:
                model = None
            self.models[workspace_key] = model
        return self.models[workspace_key]

    def record(self, change_set: str | None, object_id: str) -> tuple[str | None, Any, bool]:
        """A record's name now, its row (application and type), and whether it is gone from
        where it was."""
        staged = self.staged_records.get((change_set, object_id)) if change_set else None
        if staged is not None:
            return (None if staged.is_deleted else staged.name), staged, bool(staged.is_deleted)
        live = self.live_records.get(object_id)
        if live is not None:
            return live.name, live, False
        return None, None, True

    def relation_removed(self, change_set: str | None, relation_id: str) -> bool:
        staged = self.staged_relations.get((change_set, relation_id)) if change_set else None
        if staged is not None:
            return bool(staged.is_deleted)
        return relation_id not in self.live_relations


def _subject(event: AuditEvent, names: _Names, change_set: str | None) -> ChangeSubject:
    kind = KIND_OF[event.aggregate_type]
    changes = _changes(event)
    stored = event.subject or {}
    model = names.model(event.workspace_key)
    if kind == "record":
        name, row, removed = names.record(change_set, event.aggregate_id)
        type_key = (
            stored.get("objectTypeKey")
            or (row.object_type_key if row is not None else None)
            or changes.get("objectTypeKey")
        )
        application_key = stored.get("applicationKey") or (
            row.application_key if row is not None else None
        )
        object_type = model.object_type(type_key) if model and type_key else None
        return ChangeSubject(
            id=event.aggregate_id,
            name=name,
            applicationKey=application_key,
            objectTypeKey=type_key,
            objectTypeName=object_type.name if object_type else None,
            removed=removed,
        )
    if kind == "relationship":
        type_key = stored.get("relationTypeKey") or changes.get("relationTypeKey")
        relation_type = model.relation_type(type_key) if model and type_key else None
        ends = {}
        for position, key in (("fromObject", "fromObjectId"), ("toObject", "toObjectId")):
            end = stored.get(key) or changes.get(key)
            if end:
                ends[position] = ChangeObject(id=end, name=names.record(change_set, end)[0])
        return ChangeSubject(
            id=event.aggregate_id,
            relationTypeKey=type_key,
            relationTypeName=relation_type.name if relation_type else None,
            removed=names.relation_removed(change_set, event.aggregate_id),
            **ends,
        )
    if kind == "change-set":
        return ChangeSubject(
            id=event.aggregate_id, name=names.change_set_names.get(event.aggregate_id)
        )
    if kind == "publication":
        if event.aggregate_type == "workspace":
            return ChangeSubject(
                id=changes.get("withdrawnPublicationId", event.aggregate_id),
                number=changes.get("publicationNumber", event.version),
            )
        return ChangeSubject(id=event.aggregate_id, number=event.version)
    if event.aggregate_type == "model_draft":
        return ChangeSubject(
            id=event.aggregate_id,
            name=names.drafts.get(event.aggregate_id) or changes.get("name"),
        )
    return ChangeSubject(id=event.aggregate_id, name=names.releases.get(event.aggregate_id))


def _fields(event: AuditEvent) -> tuple[list[str], list[str]]:
    if KIND_OF[event.aggregate_type] in ("record", "relationship"):
        return changed_names(event)
    listed = _changes(event).get("changedFields")
    return ([str(item) for item in listed] if isinstance(listed, list) else []), []


def change_page(session: Session, events: Page[AuditEvent]) -> ChangePage:
    items = list(events.items)
    names = _Names(session, items)
    named_actors = actors(session, items)
    return ChangePage(
        items=[_entry(event, names, named_actors[event.sequence_id]) for event in items],
        **events.links(),
    )


def _entry(event: AuditEvent, names: _Names, actor: dict[str, str] | None) -> ChangeEntry:
    change_set = _change_set(event)
    fields, attribute_keys = _fields(event)
    model = names.model(event.workspace_key)
    label = names.labels.get(event.workspace_key) if event.workspace_key else None
    return ChangeEntry(
        id=event.event_id,
        occurredAt=event.occurred_at,
        kind=KIND_OF[event.aggregate_type],
        action=_ACTIONS.get(event.action, event.action),
        workspace=ChangeWorkspace(key=event.workspace_key, label=label)
        if event.workspace_key and label is not None
        else None,
        changeSet=ChangeSetRef(
            id=change_set,
            name=names.change_set_names.get(change_set),
            open=change_set in names.open_change_sets,
        )
        if change_set
        else None,
        subject=_subject(event, names, change_set),
        changedFields=fields,
        attributes=list(_attributes(attribute_keys, model)),
        cause=ChangeCause(kind=event.cause_kind or "user", id=event.cause_id),
        actor=actor_response(actor),
    )


def _attributes(keys: Iterable[str], model: EngineModel | None) -> Iterable[ChangeAttribute]:
    for key in keys:
        attribute = model.attribute_type(key) if model else None
        yield ChangeAttribute(key=key, name=attribute.name if attribute else key)
