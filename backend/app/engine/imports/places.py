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

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from sqlalchemy import and_, func, literal, select
from sqlalchemy.dialects.postgresql import distinct_on
from sqlalchemy.orm import Session

from ...models.schema import CandidateCriterion, EngineModel
from ..model.candidate_places import DerivedPlace, choose_container, derive_place, propose_place
from ..model.traversal import ancestor_type_keys, parent_type_keys
from ..reads.context_sets import record_source, relation_source
from ..reads.model_query import candidate_place_filters
from ..reads.snapshot_reads import SnapshotContext

MAX_DEPTH = 64


class PlaceReads:
    """What the places of one import are worked out from, each read by whole-set statements and
    kept: the cells of a view held by every container, and the containers that hold cells of a view
    under any column record. Every column of the import that asks for the same set reuses the
    answer."""

    def __init__(self) -> None:
        self._counts: dict[tuple[str, str, str, str], dict[str, int]] = {}
        self._used: dict[tuple[Any, ...], list[Any]] = {}

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
class PlaceRequest:
    """One column record a new ``cell_type_key`` record may be created under, and the view it is
    created for."""

    column_record_id: str
    column_type_key: str
    cell_type_key: str
    criteria: tuple[CandidateCriterion, ...]
    relation_type_key: str
    direction: str
    row_type_key: str


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


def resolve_places(
    session: Session,
    model: EngineModel,
    workspace_key: str,
    context: SnapshotContext | None,
    requests: Sequence[PlaceRequest],
    reads: PlaceReads | None = None,
) -> list[Place]:
    """The place for a new record under each requested column record, in order. The records under
    the column records, the criteria and the ancestor chains are worked out by statements over the
    whole set of column records of a view (recursive CTEs), so the statements do not grow with the
    number of column records."""
    reads = reads or PlaceReads()
    groups: dict[tuple[Any, ...], list[int]] = {}
    for index, request in enumerate(requests):
        key = (
            request.column_type_key,
            request.cell_type_key,
            request.relation_type_key,
            request.direction,
            request.row_type_key,
            tuple(item.model_dump_json() for item in request.criteria),
        )
        groups.setdefault(key, []).append(index)
    places: list[Place | None] = [None] * len(requests)
    for indexes in groups.values():
        group = [requests[index] for index in indexes]
        view = _View(session, model, workspace_key, context, group, reads)
        for index, request in zip(indexes, group, strict=True):
            places[index] = view.place(request)
    return [place for place in places if place is not None]


class _View:
    """The column records of one view (one column type, cell type, relationship and criteria)."""

    def __init__(
        self,
        session: Session,
        model: EngineModel,
        workspace_key: str,
        context: SnapshotContext | None,
        requests: list[PlaceRequest],
        reads: PlaceReads,
    ) -> None:
        self.session, self.model, self.workspace_key = session, model, workspace_key
        self.context, self.reads = context, reads
        first = requests[0]
        self.first = first
        self.column_ids = sorted({item.column_record_id for item in requests})
        self.container_types = sorted(
            key
            for key in ancestor_type_keys(model, first.cell_type_key)
            if key != first.column_type_key
            and first.column_type_key in ancestor_type_keys(model, key)
        )
        self.direct = parent_type_keys(model, first.cell_type_key)
        self.types = sorted(
            set(self.container_types)
            | {first.column_type_key}
            | ancestor_type_keys(model, first.column_type_key)
        )
        self.found: dict[str, list[Any]] = {}
        self.own: dict[str, set[str]] = {}
        self._read_under()
        self._chains: dict[str, list[Any]] | None = None

    def _read_under(self) -> None:
        """Per column record, the containers under it (itself included) and which of them meet the
        ancestor criteria: one statement for every column record of the view."""
        source = record_source(self.workspace_key, self.context, self.types)
        starts = sorted(set(self.container_types) | self.direct)
        walk = (
            select(
                source.c.object_id.label("start_id"),
                source.c.object_id.label("at_id"),
                source.c.parent_object_id.label("parent_id"),
                literal(0).label("depth"),
            )
            .where(source.c.object_type_key.in_(starts))
            .cte("place_walk", recursive=True)
        )
        walk = walk.union_all(
            select(
                walk.c.start_id,
                source.c.object_id,
                source.c.parent_object_id,
                walk.c.depth + 1,
            )
            .select_from(walk.join(source, source.c.object_id == walk.c.parent_id))
            .where(walk.c.depth < MAX_DEPTH - 1)
        )
        cell_type = self.model.object_type(self.first.cell_type_key)
        filters = (
            candidate_place_filters(
                self.model,
                cell_type,
                self.first.criteria,
                workspace_key=self.workspace_key,
                context=self.context,
            )
            if cell_type is not None
            else []
        )
        meets = (
            and_(*(item.predicate(source.c.object_id) for item in filters))
            if filters
            else literal(True)
        )
        statement = (
            select(
                walk.c.at_id.label("column_id"),
                source.c.object_id,
                source.c.object_type_key,
                source.c.name,
                meets.label("meets"),
            )
            .select_from(walk.join(source, source.c.object_id == walk.c.start_id))
            .where(walk.c.at_id.in_(self.column_ids))
            .distinct()
        )
        for row in self.session.execute(statement):
            self.own.setdefault(row.column_id, set()).add(row.object_id)
            if row.object_type_key in self.direct and row.meets:
                self.found.setdefault(row.column_id, []).append(row)

    def chains(self) -> dict[str, list[Any]]:
        """Per column record, it and the records above it (root last): one statement, read when a
        place has to be proposed or explained."""
        if self._chains is None:
            source = record_source(self.workspace_key, self.context, self.types)
            walk = (
                select(
                    source.c.object_id.label("column_id"),
                    source.c.object_id.label("at_id"),
                    source.c.parent_object_id.label("parent_id"),
                    source.c.object_type_key,
                    source.c.name,
                    source.c.attributes,
                    literal(0).label("depth"),
                )
                .where(source.c.object_id.in_(self.column_ids))
                .cte("place_chain", recursive=True)
            )
            walk = walk.union_all(
                select(
                    walk.c.column_id,
                    source.c.object_id,
                    source.c.parent_object_id,
                    source.c.object_type_key,
                    source.c.name,
                    source.c.attributes,
                    walk.c.depth + 1,
                )
                .select_from(walk.join(source, source.c.object_id == walk.c.parent_id))
                .where(walk.c.depth < MAX_DEPTH - 1)
            )
            chains: dict[str, list[Any]] = {}
            for row in self.session.execute(select(walk).order_by(walk.c.column_id, walk.c.depth)):
                chains.setdefault(row.column_id, []).append(row)
            self._chains = chains
        return self._chains

    def place(self, request: PlaceRequest) -> Place:
        found = self.found.get(request.column_record_id, [])
        criteria = request.criteria
        found_ids = {row.object_id for row in found}
        view = (
            request.cell_type_key,
            request.relation_type_key,
            request.direction,
            request.row_type_key,
        )
        counts = (
            {
                container: count
                for container, count in self.reads.cells_in_use(
                    self.session, self.workspace_key, self.context, *view
                ).items()
                if container in found_ids
            }
            if found
            else {}
        )
        place = derive_place(self.model, request.column_type_key, request.cell_type_key, criteria)
        by_id = {row.object_id: row for row in found}
        chosen = choose_container(list(by_id), counts, fixed=place is not None)
        if chosen is not None:
            return Place(chosen, name=by_id[chosen].name, type_key=by_id[chosen].object_type_key)
        if not found and place is not None:
            return Place(str(uuid4()), place, place.name, place.object_type_key)
        if place is None:
            # Neither the rules nor the data give a place: propose a new container (PP-D28), which
            # the import creates with the first record that goes in it, the preview saying so first.
            proposed = self._proposal(request)
            if proposed is not None:
                return Place(str(uuid4()), proposed, proposed.name, proposed.object_type_key)
        return Place(
            None,
            several=len(found) > 1,
            message=self._none(
                request,
                bool(found),
                sum(1 for item in counts.values() if item > 0) > 1,
            ),
        )

    def _proposal(self, request: PlaceRequest) -> DerivedPlace | None:
        """The container to propose under the column record (:func:`propose_place`), from the
        containers that hold cells of the view under other column records."""
        own = self.own.get(request.column_record_id, set())
        used = [
            item
            for item in self.reads.used_containers(
                self.session,
                self.workspace_key,
                self.context,
                self.container_types,
                request.cell_type_key,
                request.relation_type_key,
                request.direction,
                request.row_type_key,
            )
            if item.object_id not in own
        ]
        chain: list[tuple[str, str, Callable[[], dict[str, Any]]]] = [
            (item.object_type_key, item.name, lambda item=item: dict(item.attributes or {}))
            for item in self.chains().get(request.column_record_id, [])
        ]
        return propose_place(
            self.model,
            request.column_type_key,
            request.cell_type_key,
            request.criteria,
            [(item.object_type_key, item.name) for item in used],
            chain,
        )

    def _none(self, request: PlaceRequest, any_found: bool, tied: bool) -> str:
        """No place for a new record, in plain words."""
        chain = self.chains().get(request.column_record_id, [])
        column_name = chain[0].name if chain else "this column"
        kinds = sorted(
            self.model.object_type(key).name.lower()
            for key in self.direct
            if self.model.object_type(key)
        )
        kind = kinds[0] if kinds else "container"
        if tied:
            return (
                f"Several {kind}s under {column_name} hold the same number of cells of this view; "
                "choose one in the app"
            )
        if any_found:
            return (
                f"No {kind} under {column_name} holds cells of this view yet; "
                "create the first one in the app"
            )
        return f"No {kind} under {column_name} can hold a new record here; create one in the app"


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
        .ext(distinct_on(holders.c.object_id))
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
