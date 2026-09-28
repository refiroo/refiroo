"""What a change set changes (Base 0.8 P2a): its own rows read against its source.

A change set holds one own row per record or relation it touched. Read against its source row, the
same public ID in the change set's base, an own row is ``added`` (no source row), ``changed``
(a source row) or ``removed`` (a tombstone with a source row). A tombstone with no source row was
created and deleted inside the change set, and publishing skips it, so the lists leave it out (D31).

*Before* is the source's row, not current live: the lists say what the change set does, and whether
live moved since is what validation and publishing report. Each list is one statement over the
change set's own rows, outer-joined to their source rows on the unique (owner, ID) keys, so a page
costs its own rows however large the base.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from typing import Any

from sqlalchemy import String, and_, case, literal, or_, select, union_all
from sqlalchemy.orm import Session, aliased

from ..errors import api_error
from ..models.database import ChangeSetObject, ChangeSetRelation
from ..models.schema import EngineModel
from .matrix_cells import unindexed
from .pagination import Page, PageRequest, paginate_statement, text_key
from .snapshot_reads import SnapshotContext

KINDS = ("added", "changed", "removed")


@dataclass(frozen=True)
class ObjectState:
    name: str
    parent_object_id: str | None
    attributes: dict[str, Any]
    version: int


@dataclass(frozen=True)
class ObjectChangeEntry:
    kind: str
    object_id: str
    object_type_key: str
    application_key: str
    before: ObjectState | None
    after: ObjectState | None
    changed_fields: list[str]
    path: list[dict[str, Any]]


@dataclass(frozen=True)
class RelationEnd:
    object_id: str
    object_type_key: str | None
    name: str | None


@dataclass(frozen=True)
class RelationState:
    attributes: dict[str, Any]
    version: int


@dataclass(frozen=True)
class RelationChangeEntry:
    kind: str
    relation_id: str
    relation_type_key: str
    containment: bool
    from_end: RelationEnd
    to_end: RelationEnd
    before: RelationState | None
    after: RelationState | None
    changed_fields: list[str]


def _kind(deleted: Any, source_id: Any | None) -> Any:
    """The entry kind of an own row, or null for a tombstone with no source row.

    The source row's presence is read inside a ``CASE``: a ``WHERE`` term requiring it would let
    SQLite turn the outer join into an inner one it may reorder, walking the base instead of the
    change set's rows (see ``snapshot_reads.EffectiveRecord``).
    """
    if source_id is None:
        return case((deleted.is_(False), literal("added", String)), else_=None)
    return case(
        (and_(deleted.is_(False), source_id.is_(None)), literal("added", String)),
        (deleted.is_(False), literal("changed", String)),
        (source_id.is_not(None), literal("removed", String)),
        else_=None,
    )


def _kinds(kinds: Sequence[str] | None) -> list[str]:
    return sorted(set(kinds)) if kinds else list(KINDS)


def _require_types(
    keys: Iterable[str], exists: Any, code: str, label: str, parameter: str
) -> list[str]:
    keys = sorted(set(keys))
    for key in keys:
        if exists(key) is None:
            raise api_error(
                422,
                code,
                f"{label} '{key}' is not in the change set's model",
                {"path": f"/query/{parameter}", "key": key},
            )
    return keys


def _attribute_order(model: EngineModel, object_type_key: str) -> dict[str, int]:
    object_type = model.object_type(object_type_key)
    bindings = object_type.attributes if object_type else ()
    return {binding.attributeTypeKey: index for index, binding in enumerate(bindings)}


def _changed_attributes(
    before: dict[str, Any], after: dict[str, Any], order: dict[str, int]
) -> list[str]:
    keys = {key for key in (*before, *after) if before.get(key) != after.get(key)}
    return sorted(keys, key=lambda key: (order.get(key, len(order)), key))


def list_object_changes(
    session: Session,
    context: SnapshotContext,
    model: EngineModel,
    *,
    kinds: Sequence[str] | None,
    object_type_keys: Sequence[str] | None,
    page: PageRequest,
    page_size: int,
) -> Page[ObjectChangeEntry]:
    """A page of the change set's record changes by (type, name, ID).

    The name is the own row's; a tombstone keeps the removed record's. The order is
    ``ix_change_set_objects_type_name``.
    """
    types = _require_types(
        object_type_keys or (), model.object_type, "unknown_object_type", "Object type", "objectTypeKey"
    )
    wanted = _kinds(kinds)
    own = ChangeSetObject
    base = context.base
    if base is None:
        kind = _kind(own.is_deleted, None)
        source_columns = [
            literal(None, String).label("source_name"),
            literal(None, String).label("source_parent_object_id"),
            literal(None).label("source_attributes"),
            literal(None).label("source_version"),
        ]
    else:
        source = aliased(base.objects)
        kind = _kind(own.is_deleted, source.object_id)
        source_columns = [
            source.name.label("source_name"),
            source.parent_object_id.label("source_parent_object_id"),
            source.attributes.label("source_attributes"),
            source.version.label("source_version"),
        ]
    statement = select(
        own.object_id,
        own.application_key,
        own.object_type_key,
        own.name,
        own.parent_object_id,
        own.attributes,
        own.version,
        kind.label("kind"),
        *source_columns,
    ).where(own.change_set_id == context.id, kind.in_(wanted))
    if base is not None:
        statement = statement.select_from(own).outerjoin(
            source,
            and_(
                getattr(source, base.owner_column) == base.owner_id,
                source.object_id == own.object_id,
            ),
        )
    if types:
        statement = statement.where(own.object_type_key.in_(types))
    result = paginate_statement(
        session,
        statement,
        keys=(
            text_key("objectTypeKey", own.object_type_key, "object_type_key"),
            text_key("name", own.name, "name"),
            text_key("id", own.object_id, "object_id"),
        ),
        scope="object-changes",
        filters={"changeSetId": context.id, "kind": wanted, "objectTypeKey": types},
        page=page,
        page_size=page_size,
        message="Object change cursor is invalid",
        rows=True,
    )

    def before(row: Any) -> ObjectState | None:
        if row.kind == "added":
            return None
        return ObjectState(
            row.source_name,
            row.source_parent_object_id,
            dict(row.source_attributes or {}),
            row.source_version,
        )

    def after(row: Any) -> ObjectState | None:
        if row.kind == "removed":
            return None
        return ObjectState(row.name, row.parent_object_id, dict(row.attributes or {}), row.version)

    states = [(row, before(row), after(row)) for row in result.items]
    # Added and changed records sit where the change set puts them; a removed one where its source
    # held it.
    paths = _paths(
        session,
        context,
        [
            ("source", _PathRow.of(row, before_state))
            if after_state is None
            else ("change_set", _PathRow.of(row, after_state))
            for row, before_state, after_state in states
        ],
    )
    orders: dict[str, dict[str, int]] = {}
    entries = []
    for row, before_state, after_state in states:
        order = orders.setdefault(row.object_type_key, _attribute_order(model, row.object_type_key))
        changed = []
        if (before_state and before_state.name) != (after_state and after_state.name):
            changed.append("name")
        if (before_state and before_state.parent_object_id) != (
            after_state and after_state.parent_object_id
        ):
            changed.append("parent")
        changed += _changed_attributes(
            before_state.attributes if before_state else {},
            after_state.attributes if after_state else {},
            order,
        )
        entries.append(
            ObjectChangeEntry(
                kind=row.kind,
                object_id=row.object_id,
                object_type_key=row.object_type_key,
                application_key=row.application_key,
                before=before_state,
                after=after_state,
                changed_fields=changed,
                path=paths.get(row.object_id, []),
            )
        )
    return replace(result, items=entries)


@dataclass(frozen=True)
class _PathRow:
    """The fields ``object_paths`` reads, from one side of an entry."""

    object_id: str
    name: str
    object_type_key: str
    parent_object_id: str | None

    @classmethod
    def of(cls, row: Any, state: ObjectState) -> _PathRow:
        return cls(row.object_id, state.name, row.object_type_key, state.parent_object_id)


def _read_records(
    session: Session, context: SnapshotContext, wanted: dict[str, set[str]]
) -> dict[tuple[str, str], Any]:
    """Records by (side, ID) in one statement, whichever sides a page needs.

    The ``change_set`` side is the change set's effective record: its own row unless that is a
    tombstone, else its source row. The ``source`` side is the source row alone. Both sides read
    the same two arms, the change set's rows and the source's rows by their unique (owner, ID) keys,
    so a page costs one statement whether or not it lists a removal.
    """
    ids = set().union(*wanted.values()) if wanted else set()
    if not ids:
        return {}

    def arm(entity: Any, owner: Any, origin: str, deleted: Any) -> Any:
        return select(
            entity.object_id,
            entity.object_type_key,
            entity.name,
            entity.parent_object_id,
            deleted.label("is_deleted"),
            literal(origin, String).label("origin"),
        ).where(owner, entity.object_id.in_(sorted(ids)))

    arms = [
        arm(
            ChangeSetObject,
            ChangeSetObject.change_set_id == context.id,
            "own",
            ChangeSetObject.is_deleted,
        )
    ]
    base = context.base
    if base is not None:
        arms.append(
            arm(
                base.objects,
                # Driven by the listed IDs: the owner's covering indexes would otherwise tempt the
                # planner to walk every record of the source.
                unindexed(getattr(base.objects, base.owner_column) == base.owner_id),
                "source",
                literal(False),
            )
        )
    own: dict[str, Any] = {}
    source: dict[str, Any] = {}
    for row in session.execute(union_all(*arms) if len(arms) > 1 else arms[0]):
        (own if row.origin == "own" else source)[row.object_id] = row
    found: dict[tuple[str, str], Any] = {}
    for object_id in wanted.get("change_set", ()):
        row = own[object_id] if object_id in own else source.get(object_id)
        if row is not None and not row.is_deleted:
            found[("change_set", object_id)] = row
    for object_id in wanted.get("source", ()):
        if object_id in source:
            found[("source", object_id)] = source[object_id]
    return found


def _paths(
    session: Session, context: SnapshotContext, items: list[tuple[str, _PathRow]]
) -> dict[str, list[dict[str, Any]]]:
    """Root-first paths, each followed on its item's side; one statement per hierarchy level, as
    ``snapshot_reads.object_paths`` resolves one context."""

    def part(record: Any) -> dict[str, Any]:
        return {"id": record.object_id, "name": record.name, "objectTypeKey": record.object_type_key}

    paths = {row.object_id: [part(row)] for _, row in items}
    visited = {row.object_id: {row.object_id} for _, row in items}
    frontier = {
        row.object_id: (side, row.parent_object_id) for side, row in items if row.parent_object_id
    }
    while frontier:
        wanted: dict[str, set[str]] = {}
        for side, parent_id in frontier.values():
            wanted.setdefault(side, set()).add(parent_id)
        found = _read_records(session, context, wanted)
        next_frontier: dict[str, tuple[str, str]] = {}
        for object_id, (side, parent_id) in frontier.items():
            parent = found.get((side, parent_id))
            if parent is None or parent.object_id in visited[object_id]:
                continue
            visited[object_id].add(parent.object_id)
            paths[object_id].append(part(parent))
            if parent.parent_object_id:
                next_frontier[object_id] = (side, parent.parent_object_id)
        frontier = next_frontier
    return {object_id: list(reversed(path)) for object_id, path in paths.items()}


def containment_pairs(model: EngineModel) -> set[tuple[str, str]]:
    """(relation type, child type) pairs whose edges the engine maintains as parent links."""
    return {
        (relation_type_key, object_type.key)
        for object_type in model.objectTypes
        for relation_type_key in (object_type.behavior or {}).get("parentRelationTypeKeys", [])
    }


def _containment_filter(
    model: EngineModel, context: SnapshotContext, own: Any, containment: bool
) -> Any:
    """Own relation rows that are (or with ``containment`` false, are not) parent edges.

    A relation type is decided by its key alone when every permitted pair ending at a type either
    declares it a parent relation or not; a key used both ways reads its ``to`` end's type, which a
    record never changes, from its change set row or else its source row.
    """
    pairs = containment_pairs(model)
    parents = {key for key, _ in pairs}
    ends: dict[str, set[str]] = {}
    for allowed in model.objectTypeRelations:
        if allowed.relationTypeKey in parents:
            ends.setdefault(allowed.relationTypeKey, set()).add(allowed.toObjectTypeKey)
    always = sorted(key for key, types in ends.items() if all((key, t) in pairs for t in types))
    mixed = sorted(parents - set(always))
    terms = [own.relation_type_key.in_(always)] if always else []
    if mixed:
        end = aliased(ChangeSetObject)
        to_type = (
            select(end.object_type_key)
            .where(end.change_set_id == context.id, end.object_id == own.to_object_id)
            .correlate_except(end)
            .scalar_subquery()
        )
        if context.base is not None:
            base = context.base
            source = aliased(base.objects)
            source_type = (
                select(source.object_type_key)
                .where(
                    getattr(source, base.owner_column) == base.owner_id,
                    source.object_id == own.to_object_id,
                )
                .correlate_except(source)
                .scalar_subquery()
            )
            to_type = case((to_type.is_not(None), to_type), else_=source_type)
        for key in mixed:
            children = sorted(child for relation, child in pairs if relation == key)
            terms.append(and_(own.relation_type_key == key, to_type.in_(children)))
    matches = or_(*terms) if terms else literal(False)
    return matches if containment else ~matches


def list_relation_changes(
    session: Session,
    context: SnapshotContext,
    model: EngineModel,
    *,
    kinds: Sequence[str] | None,
    relation_type_keys: Sequence[str] | None,
    containment: bool | None,
    page: PageRequest,
    page_size: int,
) -> Page[RelationChangeEntry]:
    """A page of the change set's relation changes by (type, ID).

    Engine-maintained parent edges are listed with ``containment`` set, so an integration sees
    every row that publishes (D32); ``containment`` narrows to them or leaves them out.
    """
    types = _require_types(
        relation_type_keys or (),
        model.relation_type,
        "unknown_relation_type",
        "Relation type",
        "relationTypeKey",
    )
    wanted = _kinds(kinds)
    own = ChangeSetRelation
    base = context.base
    if base is None:
        kind = _kind(own.is_deleted, None)
        source_columns = [
            literal(None).label("source_attributes"),
            literal(None).label("source_version"),
        ]
    else:
        source = aliased(base.relations)
        kind = _kind(own.is_deleted, source.relation_id)
        source_columns = [
            source.attributes.label("source_attributes"),
            source.version.label("source_version"),
        ]
    statement = select(
        own.relation_id,
        own.relation_type_key,
        own.from_object_id,
        own.to_object_id,
        own.attributes,
        own.version,
        kind.label("kind"),
        *source_columns,
    ).where(own.change_set_id == context.id, kind.in_(wanted))
    if base is not None:
        statement = statement.select_from(own).outerjoin(
            source,
            and_(
                getattr(source, base.owner_column) == base.owner_id,
                source.relation_id == own.relation_id,
            ),
        )
    if types:
        statement = statement.where(own.relation_type_key.in_(types))
    if containment is not None:
        statement = statement.where(_containment_filter(model, context, own, containment))
    result = paginate_statement(
        session,
        statement,
        keys=(
            text_key("relationTypeKey", own.relation_type_key, "relation_type_key"),
            text_key("id", own.relation_id, "relation_id"),
        ),
        scope="relation-changes",
        filters={
            "changeSetId": context.id,
            "kind": wanted,
            "relationTypeKey": types,
            "containment": containment,
        },
        page=page,
        page_size=page_size,
        message="Relation change cursor is invalid",
        rows=True,
    )

    # Both ends of the page in one statement: as the change set holds them, or for an end it
    # removed, as its source does.
    end_ids = {row.from_object_id for row in result.items} | {row.to_object_id for row in result.items}
    found = _read_records(session, context, {"change_set": end_ids, "source": end_ids})
    records = {
        object_id: found.get(("change_set", object_id)) or found.get(("source", object_id))
        for object_id in end_ids
    }

    def end(object_id: str) -> RelationEnd:
        record = records.get(object_id)
        if record is None:
            return RelationEnd(object_id, None, None)
        return RelationEnd(object_id, record.object_type_key, record.name)

    pairs = containment_pairs(model)
    entries = []
    for row in result.items:
        before = (
            None
            if row.kind == "added"
            else RelationState(dict(row.source_attributes or {}), row.source_version)
        )
        after = None if row.kind == "removed" else RelationState(dict(row.attributes or {}), row.version)
        from_end, to_end = end(row.from_object_id), end(row.to_object_id)
        entries.append(
            RelationChangeEntry(
                kind=row.kind,
                relation_id=row.relation_id,
                relation_type_key=row.relation_type_key,
                containment=(row.relation_type_key, to_end.object_type_key) in pairs,
                from_end=from_end,
                to_end=to_end,
                before=before,
                after=after,
                changed_fields=_changed_attributes(
                    before.attributes if before else {}, after.attributes if after else {}, {}
                ),
            )
        )
    return replace(result, items=entries)
