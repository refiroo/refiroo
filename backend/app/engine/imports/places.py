"""Where an import puts a new cell record (Base 0.17 MC1 and EX1, PP-D24).

A link matrix column or a create matrix column holds records under one column record. A value that
finds no record creates one, and the relationship's candidate rules say where it may stand: the
containers under the column record that a record created there meets the ancestor criteria under
(``model/candidates.meets_criteria``, the evaluator the write rule uses), or, when none exists and
the criteria fix one (``model/candidate_places.derive_place``), a new place created with the record.
Nothing is written here: the answer is read from the context's records, and the binding turns it into
the items that create the place and the record in one load. The records and cell counts a place is
worked out from are read once for the import (:class:`PlaceReads`), not once per column record.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...models.schema import CandidateCriterion, EngineModel
from ..model.candidate_places import DerivedPlace, choose_container, derive_place, propose_place
from ..model.candidates import meets_criteria
from ..model.consumer_contract import split_ancestor_reference
from ..model.traversal import ancestor_type_keys, parent_type_keys
from ..reads.context_sets import record_source, relation_source
from ..reads.snapshot_reads import SnapshotContext

MAX_DEPTH = 64


class PlaceReads:
    """What the places of one import are worked out from, each read once by one statement and kept:
    the records of a set of types, the cells of a view held by every container, and the containers
    that hold cells of a view under any column record. Every column of the import that asks for the
    same set reuses the answer."""

    def __init__(self) -> None:
        self._rows: dict[tuple[str, ...], dict[str, Any]] = {}
        self._counts: dict[tuple[str, str, str, str], dict[str, int]] = {}
        self._used: dict[tuple[Any, ...], list[Any]] = {}

    def rows(
        self,
        session: Session,
        workspace_key: str,
        context: SnapshotContext | None,
        types: list[str],
    ) -> dict[str, Any]:
        key = tuple(types)
        if key not in self._rows:
            source = record_source(workspace_key, context, types)
            self._rows[key] = {
                row.object_id: row
                for row in session.execute(
                    select(
                        source.c.object_id,
                        source.c.object_type_key,
                        source.c.name,
                        source.c.parent_object_id,
                        source.c.attributes,
                    )
                )
            }
        return self._rows[key]

    def cells_in_use(
        self,
        session: Session,
        workspace_key: str,
        context: SnapshotContext | None,
        cell_type_key: str,
        relation_type_key: str,
        direction: str,
        row_type_key: str,
    ) -> dict[str, int]:
        key = (cell_type_key, relation_type_key, direction, row_type_key)
        if key not in self._counts:
            self._counts[key] = _cells_in_use(
                session,
                workspace_key,
                context,
                cell_type_key,
                relation_type_key,
                direction,
                row_type_key,
            )
        return self._counts[key]

    def used_containers(
        self,
        session: Session,
        workspace_key: str,
        context: SnapshotContext | None,
        container_types: list[str],
        cell_type_key: str,
        relation_type_key: str,
        direction: str,
        row_type_key: str,
    ) -> list[Any]:
        key = (
            tuple(container_types),
            cell_type_key,
            relation_type_key,
            direction,
            row_type_key,
        )
        if key not in self._used:
            self._used[key] = _used_containers(
                session,
                workspace_key,
                context,
                container_types,
                cell_type_key,
                relation_type_key,
                direction,
                row_type_key,
            )
        return self._used[key]


@dataclass(frozen=True)
class Place:
    """Where new records under one column record go: an existing ``container_id``, or a place to
    create (``new``, with ``container_id`` the ID it will have). ``container_id`` is ``None`` when the
    rules give no one place; ``several`` says why: more than one container meets them."""

    container_id: str | None
    new: DerivedPlace | None = None
    name: str | None = None
    type_key: str | None = None
    several: bool = False
    # Why there is none, in plain words, for the refusal and the preview.
    message: str | None = None


def resolve_place(
    session: Session,
    model: EngineModel,
    workspace_key: str,
    context: SnapshotContext | None,
    *,
    column_record_id: str,
    column_type_key: str,
    cell_type_key: str,
    criteria: tuple[CandidateCriterion, ...],
    relation_type_key: str,
    direction: str,
    row_type_key: str,
    reads: PlaceReads | None = None,
) -> Place:
    """The place for a new ``cell_type_key`` record under the ``column_record_id`` record."""
    container_types = {
        key
        for key in ancestor_type_keys(model, cell_type_key)
        if key != column_type_key and column_type_key in ancestor_type_keys(model, key)
    }
    direct = parent_type_keys(model, cell_type_key)
    types = sorted(container_types | {column_type_key} | ancestor_type_keys(model, column_type_key))
    reads = reads or PlaceReads()
    rows = reads.rows(session, workspace_key, context, types)
    ancestor_criteria = tuple(
        item for item in criteria if split_ancestor_reference(item.field) is not None
    )
    found: list[Any] = []
    for row in rows.values():
        if row.object_type_key not in direct:
            continue
        chain = _chain(rows, row.object_id, column_record_id)
        if chain is None:
            continue
        ancestors = [
            (item.object_type_key, item.name, lambda item=item: dict(item.attributes or {}))
            for item in chain
        ]
        if not ancestor_criteria or meets_criteria(model, ancestor_criteria, ("", dict), ancestors):
            found.append(row)
    # Where the criteria fix the one place and one container is it, that one; otherwise the container
    # that already holds cells of the view (PP-D24). A container holding none is never used.
    found_ids = {row.object_id for row in found}
    counts = (
        {
            container: count
            for container, count in reads.cells_in_use(
                session,
                workspace_key,
                context,
                cell_type_key,
                relation_type_key,
                direction,
                row_type_key,
            ).items()
            if container in found_ids
        }
        if found
        else {}
    )
    place = derive_place(model, column_type_key, cell_type_key, criteria)
    by_id = {row.object_id: row for row in found}
    chosen = choose_container(list(by_id), counts, fixed=place is not None)
    if chosen is not None:
        return Place(chosen, name=by_id[chosen].name, type_key=by_id[chosen].object_type_key)
    if not found and place is not None:
        return Place(str(uuid4()), place, place.name, place.object_type_key)
    if place is None:
        # Neither the rules nor the data give a place: propose a new container (PP-D28), which the
        # import creates with the first record that goes in it, the preview saying so first.
        proposed = _proposal(
            session,
            model,
            workspace_key,
            context,
            rows=rows,
            column_record_id=column_record_id,
            column_type_key=column_type_key,
            cell_type_key=cell_type_key,
            criteria=criteria,
            relation_type_key=relation_type_key,
            direction=direction,
            row_type_key=row_type_key,
            reads=reads,
            own={
                row.object_id
                for row in rows.values()
                if _chain(rows, row.object_id, column_record_id)
            },
        )
        if proposed is not None:
            return Place(str(uuid4()), proposed, proposed.name, proposed.object_type_key)
    return Place(
        None,
        several=len(found) > 1,
        message=_none(
            model,
            rows,
            column_record_id,
            direct,
            bool(found),
            sum(1 for item in counts.values() if item > 0) > 1,
        ),
    )


def _proposal(
    session: Session,
    model: EngineModel,
    workspace_key: str,
    context: SnapshotContext | None,
    *,
    rows: dict[str, Any],
    column_record_id: str,
    column_type_key: str,
    cell_type_key: str,
    criteria: tuple[CandidateCriterion, ...],
    relation_type_key: str,
    direction: str,
    row_type_key: str,
    own: set[str],
    reads: PlaceReads,
) -> DerivedPlace | None:
    """The container to propose under the column record (:func:`propose_place`), from the containers
    that hold cells of the view under other column records, read once for the import."""
    container_types = sorted(
        key
        for key in ancestor_type_keys(model, cell_type_key)
        if key != column_type_key and column_type_key in ancestor_type_keys(model, key)
    )
    used = [
        item
        for item in reads.used_containers(
            session,
            workspace_key,
            context,
            container_types,
            cell_type_key,
            relation_type_key,
            direction,
            row_type_key,
        )
        if item.object_id not in own
    ]
    chain: list[tuple[str, str, Callable[[], dict[str, Any]]]] = []
    at: str | None = column_record_id
    for _ in range(MAX_DEPTH):
        item = rows.get(at) if at is not None else None
        if item is None:
            break
        chain.append(
            (item.object_type_key, item.name, lambda item=item: dict(item.attributes or {}))
        )
        at = item.parent_object_id
    return propose_place(
        model,
        column_type_key,
        cell_type_key,
        criteria,
        [(item.object_type_key, item.name) for item in used],
        chain,
    )


def _used_containers(
    session: Session,
    workspace_key: str,
    context: SnapshotContext | None,
    container_types: list[str],
    cell_type_key: str,
    relation_type_key: str,
    direction: str,
    row_type_key: str,
) -> list[Any]:
    """The containers that hold cells of the view, one statement; the caller leaves out the ones it
    knows."""
    cells = record_source(workspace_key, context, [cell_type_key])
    holders = record_source(workspace_key, context, container_types)
    row_records = record_source(workspace_key, context, [row_type_key])
    relations = relation_source(context)
    cell_end, row_end = (
        (relations.c.to_object_id, relations.c.from_object_id)
        if direction == "outgoing"
        else (relations.c.from_object_id, relations.c.to_object_id)
    )
    return session.execute(
        select(holders.c.object_id, holders.c.object_type_key, holders.c.name)
        .where(
            holders.c.object_id.in_(
                select(cells.c.parent_object_id)
                .select_from(cells.join(relations, cell_end == cells.c.object_id))
                .where(
                    relations.c.relation_type_key == relation_type_key,
                    row_end.in_(select(row_records.c.object_id)),
                )
            )
        )
        .distinct(holders.c.object_id)
    ).all()


def _cells_in_use(
    session: Session,
    workspace_key: str,
    context: SnapshotContext | None,
    cell_type_key: str,
    relation_type_key: str,
    direction: str,
    row_type_key: str,
) -> dict[str, int]:
    """How many cell records stand directly under each container and are related, by the view's
    relationship, to a record of the view's row type: the cells of the view, which is the evidence of
    where its new cells go (PP-D24). One statement for every container."""
    cells = record_source(workspace_key, context, [cell_type_key])
    rows = record_source(workspace_key, context, [row_type_key])
    relations = relation_source(context)
    cell_end, row_end = (
        (relations.c.to_object_id, relations.c.from_object_id)
        if direction == "outgoing"
        else (relations.c.from_object_id, relations.c.to_object_id)
    )
    return dict(
        session.execute(
            select(cells.c.parent_object_id, func.count(func.distinct(cells.c.object_id)))
            .select_from(cells.join(relations, cell_end == cells.c.object_id))
            .where(
                relations.c.relation_type_key == relation_type_key,
                row_end.in_(select(rows.c.object_id)),
            )
            .group_by(cells.c.parent_object_id)
        ).all()
    )


def _none(
    model: EngineModel,
    rows: dict[str, Any],
    column_record_id: str,
    direct: set[str],
    any_found: bool,
    tied: bool,
) -> str:
    """No place for a new record, in plain words."""
    column = rows.get(column_record_id)
    column_name = column.name if column is not None else "this column"
    kinds = sorted(model.object_type(key).name.lower() for key in direct if model.object_type(key))
    kind = kinds[0] if kinds else "container"
    if tied:
        return (
            f"Several {kind}s under {column_name} hold the same number of cells of this view; "
            "choose one in the app"
        )
    if any_found:
        return f"No {kind} under {column_name} holds cells of this view yet; create the first one in the app"
    return f"No {kind} under {column_name} can hold a new record here; create one in the app"


def _chain(rows: dict[str, Any], object_id: str, column_record_id: str) -> list[Any] | None:
    """The record and the records above it up to the root, or ``None`` when it does not stand under
    the column record. The criteria read any ancestor, so the chain runs past the column record."""
    chain: list[Any] = []
    at: str | None = object_id
    for _ in range(MAX_DEPTH):
        row = rows.get(at) if at is not None else None
        if row is None:
            break
        chain.append(row)
        at = row.parent_object_id
    return chain if any(item.object_id == column_record_id for item in chain) else None
