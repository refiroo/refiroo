"""Stored relation matrix cell states (Base 0.8 A3b, ADR-033).

A relation matrix's row state filter decides over every row. Deriving each cell from records on
every request walks every cell record under the selected columns, so ``matrix_cell_states`` keeps
each non-empty cell's record and matching counts per owner and matrix shape, and the filter reads
them by index. Records stay the source of truth: every state here can be rebuilt from them.

Owners:

* ``live`` — a workspace's live records (owner ID: the workspace key);
* ``publication`` and ``base`` — a publication's rows and a change set's private current-live
  base, immutable once written;
* ``change_set`` — a change set's overlay: for each row record its changes touch, the row's states
  in the change set, replacing all of its base's states for that row (a sentinel row with an empty
  column marks the row as replaced);
* ``history`` — per workspace, the cells some publication held a record in, with the first
  publication that did, for ``historyOnly``.

A ``matrix_state_builds`` row says one owner's states of one shape are complete. Which owners need
which shapes follows from the models in use (:func:`required_shapes`); :func:`sync_workspace`
builds what is missing and drops the rest, at startup, on model activation and when change sets and
publications are created. A read uses stored states only when every owner it needs is built, and
otherwise derives its cells from records, so a missing build costs time, never correctness.

Maintenance: an ORM flush hook notes the records a write touches (relations of any type, parent
changes, attribute values and change set rows), and before the transaction commits the touched rows
are recomputed from records in each built shape. Nothing adjusts a count, so a missed update cannot
accumulate drift. Core statements that bypass the ORM note their changes with :func:`note_rows` and
:func:`note_cells`.
"""

import json
import logging
import time
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from itertools import islice
from typing import Any

from sqlalchemy import (
    Select,
    delete,
    event,
    except_,
    exists,
    func,
    insert,
    intersect,
    literal,
    select,
    union,
)
from sqlalchemy.orm import Session, attributes

from ..errors import ApiError
from ..models.database import (
    AttributeValue,
    ChangeSet,
    ChangeSetBaseObject,
    ChangeSetBaseRelation,
    ChangeSetObject,
    ChangeSetRelation,
    MatrixCellState,
    MatrixStateBuild,
    ModelRuntimeState,
    ObjectRelation,
    Publication,
    PublicationObject,
    PublicationRelation,
    RdmObject,
    Workspace,
)
from .matrix_cells import (
    CellScope,
    MatrixShape,
    cell_states,
    descendants,
    model_shapes,
    related_rows,
    unindexed,
)
from .snapshot_reads import SnapshotBase, SnapshotContext, change_set_context, find_objects

logger = logging.getLogger(__name__)

# The column of a change set's sentinel row: the row's base states are replaced.
REPLACED = ""
_CHUNK = 500
_PENDING = "matrix_state_changes"
_KINDS = ("live", "publication", "base", "change_set", "history")
_TABLE = MatrixCellState.__table__


@dataclass(frozen=True)
class Owner:
    kind: str
    id: str
    workspace_key: str


def _chunks(items: Iterable[str], size: int = _CHUNK) -> Iterable[list[str]]:
    iterator = iter(sorted(items))
    while chunk := list(islice(iterator, size)):
        yield chunk


def _change_set(session: Session, change_set_id: str) -> ChangeSet | None:
    return session.scalar(select(ChangeSet).where(ChangeSet.id == change_set_id))


def base_owner(change_set: Any) -> Owner | None:
    """The owner of a change set's base rows: its private base, a publication, or none."""
    if change_set.base_id is not None:
        return Owner("base", change_set.base_id, change_set.workspace_key)
    if change_set.derived_from_publication_id is not None:
        return Owner("publication", change_set.derived_from_publication_id, change_set.workspace_key)
    return None


def _context(session: Session, owner: Owner) -> SnapshotContext | None:
    if owner.kind == "live":
        return None
    if owner.kind == "change_set":
        return change_set_context(session, owner.id)
    base = (
        SnapshotBase(PublicationObject, PublicationRelation, "publication_id", owner.id)
        if owner.kind == "publication"
        else SnapshotBase(ChangeSetBaseObject, ChangeSetBaseRelation, "base_id", owner.id)
    )
    # A base's rows are read as a publication's are: immutable rows of one owner.
    return SnapshotContext("publication", owner.id, owner.workspace_key, None, base)


def _scope(session: Session, owner: Owner, shape: MatrixShape) -> CellScope:
    return CellScope(session, owner.workspace_key, shape, _context(session, owner))


# Which owners need which shapes.


def _release_shapes(
    session: Session, release_id: int, cache: dict[int, dict[str, MatrixShape]]
) -> dict[str, MatrixShape]:
    if release_id not in cache:
        from .model.registry import model_registry

        try:
            model = model_registry.resolve_release(session, release_id, require_ready=False).model
        except ApiError as exc:
            # An unusable release serves no reads either; its contexts derive nothing from here.
            logger.warning("Matrix states skip model release %s: %s", release_id, exc.message)
            cache[release_id] = {}
        else:
            cache[release_id] = model_shapes(model)
    return cache[release_id]


def required_shapes(
    session: Session, workspace_key: str, cache: dict[int, dict[str, MatrixShape]] | None = None
) -> dict[Owner, dict[str, MatrixShape]]:
    """The shapes each owner of the workspace keeps states for.

    Live keeps the active model's; a change set, its release's; a change set's base, the change set's
    release's; a publication, its own release's and those of change sets based on it. The history
    keeps every shape any of them uses, since each context's ``historyOnly`` reads it.
    """
    cache = {} if cache is None else cache
    active_release = session.scalar(select(ModelRuntimeState.active_model_release_id))
    live = Owner("live", workspace_key, workspace_key)
    required: dict[Owner, dict[str, MatrixShape]] = {
        live: dict(_release_shapes(session, active_release, cache)) if active_release else {}
    }
    history = dict(required[live])
    for publication_id, release_id in session.execute(
        select(Publication.id, Publication.model_release_id).where(
            Publication.workspace_key == workspace_key
        )
    ):
        shapes = _release_shapes(session, release_id, cache)
        required[Owner("publication", publication_id, workspace_key)] = dict(shapes)
        history.update(shapes)
    for change_set in session.execute(
        select(
            ChangeSet.id,
            ChangeSet.workspace_key,
            ChangeSet.model_release_id,
            ChangeSet.base_id,
            ChangeSet.derived_from_publication_id,
        ).where(ChangeSet.workspace_key == workspace_key)
    ):
        shapes = _release_shapes(session, change_set.model_release_id, cache)
        required[Owner("change_set", change_set.id, workspace_key)] = dict(shapes)
        base = base_owner(change_set)
        if base is not None:
            required.setdefault(base, {}).update(shapes)
        history.update(shapes)
    required[Owner("history", workspace_key, workspace_key)] = history
    return required


def _built(session: Session, workspace_key: str) -> set[tuple[str, str, str]]:
    return {
        tuple(row)
        for row in session.execute(
            select(
                MatrixStateBuild.owner_kind, MatrixStateBuild.owner_id, MatrixStateBuild.shape_key
            ).where(MatrixStateBuild.workspace_key == workspace_key)
        )
    }


def sync_workspace(session: Session, workspace_key: str, *, commit: bool = False) -> int:
    """Build every missing (owner, shape) of the workspace and drop the ones no longer needed.

    With ``commit`` each build commits on its own, so a stopped run keeps what it finished.
    Returns the number of builds made.
    """
    required = required_shapes(session, workspace_key)
    built = _built(session, workspace_key)
    wanted = {(owner.kind, owner.id, key) for owner, shapes in required.items() for key in shapes}
    for kind, owner_id, key in sorted(built - wanted):
        _drop(session, Owner(kind, owner_id, workspace_key), key)
    if commit:
        session.commit()
    made = 0
    # Change sets compare with their base, and the history reads publications: build those first.
    for owner in sorted(required, key=lambda item: (_KINDS.index(item.kind), item.id)):
        for key, shape in sorted(required[owner].items()):
            if (owner.kind, owner.id, key) in built:
                continue
            _build(session, owner, shape)
            made += 1
            if commit:
                session.commit()
    return made


def sync_all(session: Session, *, commit: bool = False) -> int:
    """:func:`sync_workspace` for every workspace; builds of removed workspaces are dropped."""
    workspaces = list(session.scalars(select(Workspace.key).order_by(Workspace.key)))
    for workspace_key in session.scalars(
        select(MatrixStateBuild.workspace_key)
        .where(MatrixStateBuild.workspace_key.not_in(workspaces))
        .distinct()
    ):
        drop_workspace(session, workspace_key)
    made = sum(sync_workspace(session, key, commit=commit) for key in workspaces)
    if commit:
        session.commit()
    return made


def build_at_startup(session: Session) -> None:
    """Build every missing (owner, shape) before serving, committing each build.

    A failure does not stop the API: reads whose owners are not built derive their cells from
    records, which is correct but slower, and finished builds are kept for the next start.
    """
    started = time.perf_counter()
    try:
        made = sync_all(session, commit=True)
    except Exception as exc:
        session.rollback()
        logger.debug("Matrix cell state build diagnostic traceback", exc_info=exc)
        logger.error(
            "Relation matrix cell states could not be built: %s. The API still serves; matrix "
            "state filters derive their cells from records, correctly but more slowly, until a "
            "restart completes the build. Builds already finished are kept. If a restart fails "
            "the same way, report this message with the application version.",
            " ".join(str(exc).split())[:500] or type(exc).__name__,
        )
        return
    if made:
        logger.info(
            "Built %d relation matrix cell state sets in %.1f s", made, time.perf_counter() - started
        )


def drop_owner(session: Session, owner: Owner) -> None:
    _drop(session, owner, None)


def drop_workspace(session: Session, workspace_key: str) -> None:
    owners = session.execute(
        select(MatrixStateBuild.owner_kind, MatrixStateBuild.owner_id)
        .where(MatrixStateBuild.workspace_key == workspace_key)
        .distinct()
    ).all()
    for kind, owner_id in owners:
        _drop(session, Owner(kind, owner_id, workspace_key), None)


def _drop(session: Session, owner: Owner, shape_key: str | None) -> None:
    for table in (_TABLE, MatrixStateBuild.__table__):
        statement = delete(table).where(table.c.owner_kind == owner.kind, table.c.owner_id == owner.id)
        if shape_key is not None:
            statement = statement.where(table.c.shape_key == shape_key)
        session.execute(statement)


# Builds.


def _insert(session: Session, rows: Iterable[dict[str, Any]]) -> None:
    batch: list[dict[str, Any]] = []
    for row in rows:
        batch.append(row)
        if len(batch) == 5000:
            session.execute(insert(_TABLE), batch)
            batch = []
    if batch:
        session.execute(insert(_TABLE), batch)


def _state_rows(owner: Owner, shape_key: str, states: Iterable[Any]) -> Iterable[dict[str, Any]]:
    for state in states:
        yield {
            "owner_kind": owner.kind,
            "owner_id": owner.id,
            "shape_key": shape_key,
            "row_id": state.row_id,
            "column_id": state.column_id,
            "record_count": state.record_count,
            "matching_count": state.matching_count,
            "first_publication_number": getattr(state, "first_publication_number", None),
        }


def _stored(session: Session, owner: Owner, shape_key: str) -> Select[Any]:
    return select(
        _TABLE.c.row_id,
        _TABLE.c.column_id,
        _TABLE.c.record_count,
        _TABLE.c.matching_count,
        _TABLE.c.first_publication_number,
    ).where(
        _TABLE.c.owner_kind == owner.kind,
        _TABLE.c.owner_id == owner.id,
        _TABLE.c.shape_key == shape_key,
    )


def _mark_built(session: Session, owner: Owner, shape: MatrixShape) -> None:
    session.execute(
        insert(MatrixStateBuild).values(
            workspace_key=owner.workspace_key,
            owner_kind=owner.kind,
            owner_id=owner.id,
            shape_key=shape.key,
            shape=shape.definition(),
        )
    )


def _build(session: Session, owner: Owner, shape: MatrixShape) -> None:
    """Derive one owner's states of one shape from records, replacing any it holds."""
    _drop(session, owner, shape.key)
    if owner.kind == "history":
        _build_history(session, owner, shape)
    elif owner.kind == "change_set":
        _build_change_set(session, owner, shape)
    else:
        states = session.execute(cell_states(_scope(session, owner, shape), None))
        _insert(session, _state_rows(owner, shape.key, states))
    _mark_built(session, owner, shape)


def _by_row(rows: Iterable[Any]) -> dict[str, dict[str, tuple[int, int]]]:
    result: dict[str, dict[str, tuple[int, int]]] = {}
    for row in rows:
        if row.column_id != REPLACED:
            result.setdefault(row.row_id, {})[row.column_id] = (row.record_count, row.matching_count)
    return result


def _build_change_set(session: Session, owner: Owner, shape: MatrixShape) -> None:
    """Keep the rows whose states in the change set differ from its base's."""
    change_set = _change_set(session, owner.id)
    changed = session.scalar(
        select(
            exists().where(ChangeSetObject.change_set_id == owner.id)
            | exists().where(ChangeSetRelation.change_set_id == owner.id)
        )
    )
    if not changed:
        return
    effective = _by_row(session.execute(cell_states(_scope(session, owner, shape), None)))
    base = base_owner(change_set)
    base_states = _by_row(session.execute(_stored(session, base, shape.key))) if base else {}
    replaced = {
        row_id
        for row_id in effective.keys() | base_states.keys()
        if effective.get(row_id) != base_states.get(row_id)
    }
    _insert(session, _overlay_rows(owner, shape.key, replaced, effective))


def _overlay_rows(
    owner: Owner, shape_key: str, rows: Iterable[str], states: dict[str, dict[str, tuple[int, int]]]
) -> Iterable[dict[str, Any]]:
    for row_id in rows:
        cells = [(REPLACED, (0, 0)), *sorted(states.get(row_id, {}).items())]
        for column_id, (record_count, matching_count) in cells:
            yield {
                "owner_kind": owner.kind,
                "owner_id": owner.id,
                "shape_key": shape_key,
                "row_id": row_id,
                "column_id": column_id,
                "record_count": record_count,
                "matching_count": matching_count,
                "first_publication_number": None,
            }


def _publication_pairs(
    session: Session, publication: Owner, shape: MatrixShape, built: set[tuple[str, str, str]]
) -> list[Any]:
    """The publication's non-empty cells, stored when built, else derived from its rows."""
    if (publication.kind, publication.id, shape.key) in built:
        return session.execute(_stored(session, publication, shape.key)).all()
    return session.execute(cell_states(_scope(session, publication, shape), None)).all()


def _build_history(session: Session, owner: Owner, shape: MatrixShape) -> None:
    built = _built(session, owner.workspace_key)
    first: dict[tuple[str, str], tuple[int, Any]] = {}
    for publication_id, number in session.execute(
        select(Publication.id, Publication.publication_number)
        .where(Publication.workspace_key == owner.workspace_key)
        .order_by(Publication.publication_number)
    ):
        publication = Owner("publication", publication_id, owner.workspace_key)
        for state in _publication_pairs(session, publication, shape, built):
            first.setdefault((state.row_id, state.column_id), (number, state))
    _insert(
        session,
        (
            {
                "owner_kind": owner.kind,
                "owner_id": owner.id,
                "shape_key": shape.key,
                "row_id": row_id,
                "column_id": column_id,
                "record_count": state.record_count,
                "matching_count": state.matching_count,
                "first_publication_number": number,
            }
            for (row_id, column_id), (number, state) in sorted(first.items())
        ),
    )


def _built_shapes(session: Session, owners: Sequence[Owner]) -> dict[Owner, list[MatrixShape]]:
    """The built shapes of each listed owner."""
    by_key = {(owner.kind, owner.id): owner for owner in owners}
    result: dict[Owner, list[MatrixShape]] = {}
    if not by_key:
        return result
    kinds = sorted({owner.kind for owner in owners})
    ids = sorted({owner.id for owner in owners})
    for kind, owner_id, shape in session.execute(
        select(MatrixStateBuild.owner_kind, MatrixStateBuild.owner_id, MatrixStateBuild.shape)
        .where(MatrixStateBuild.owner_kind.in_(kinds), MatrixStateBuild.owner_id.in_(ids))
        .order_by(MatrixStateBuild.shape_key)
    ):
        owner = by_key.get((kind, owner_id))
        if owner is not None:
            result.setdefault(owner, []).append(MatrixShape.from_definition(shape))
    return result


# Contexts created from others.


def record_change_set(session: Session, change_set: ChangeSet) -> None:
    """A new change set: its base takes live's states when it was captured from live now, and the
    rest is built. Call in the transaction that captured the base."""
    session.flush()
    apply_pending(session)
    base = base_owner(change_set)
    if base is not None and base.kind == "base":
        live = Owner("live", change_set.workspace_key, change_set.workspace_key)
        for shape in _built_shapes(session, [live]).get(live, []):
            _copy(session, live, base, shape)
    sync_workspace(session, change_set.workspace_key)


def record_publication(session: Session, publication: Publication) -> None:
    """A publication of live, after a change set was merged into it: it takes live's states and
    adds its cells to the workspace history. Call after the change set is removed."""
    session.flush()
    apply_pending(session)
    workspace_key = publication.workspace_key
    live = Owner("live", workspace_key, workspace_key)
    target = Owner("publication", publication.id, workspace_key)
    for shape in _built_shapes(session, [live]).get(live, []):
        _copy(session, live, target, shape)
    history = Owner("history", workspace_key, workspace_key)
    built = _built(session, workspace_key)
    for shape in _built_shapes(session, [history]).get(history, []):
        held = {
            (row.row_id, row.column_id)
            for row in session.execute(
                _stored(session, history, shape.key).with_only_columns(_TABLE.c.row_id, _TABLE.c.column_id)
            )
        }
        _insert(
            session,
            (
                {
                    **row,
                    "owner_kind": history.kind,
                    "owner_id": history.id,
                    "first_publication_number": publication.publication_number,
                }
                for row in _state_rows(
                    target, shape.key, _publication_pairs(session, target, shape, built)
                )
                if (row["row_id"], row["column_id"]) not in held
            ),
        )
    sync_workspace(session, workspace_key)


def _copy(session: Session, source: Owner, target: Owner, shape: MatrixShape) -> None:
    _drop(session, target, shape.key)
    _insert(session, _state_rows(target, shape.key, session.execute(_stored(session, source, shape.key))))
    _mark_built(session, target, shape)


# Maintenance.


@dataclass
class _Changes:
    """What a transaction touched in one context. Live changes are collected without their
    workspace, which is looked up when they are applied."""

    rows: set[str] = field(default_factory=set)
    cells: set[str] = field(default_factory=set)
    moved: set[str] = field(default_factory=set)
    attributes: set[tuple[str, str]] = field(default_factory=set)
    new_rows: set[str] = field(default_factory=set)


def _changes(session: Session, change_set_id: str | None = None) -> _Changes:
    pending = session.info.setdefault(_PENDING, {})
    return pending.setdefault(change_set_id, _Changes())


def note_rows(session: Session, row_ids: Iterable[str], change_set_id: str | None = None) -> None:
    """Records whose cells must be recomputed: relation ends a Core statement changed."""
    _changes(session, change_set_id).rows.update(row_ids)


def note_cells(session: Session, object_ids: Iterable[str], *, moved: bool = False) -> None:
    """Live records a Core statement changed: their relations and condition values (``cells``),
    and with ``moved`` the records under them too."""
    changes = _changes(session)
    changes.cells.update(object_ids)
    if moved:
        changes.moved.update(object_ids)


def note_relations_removed(session: Session, relation_ids: Iterable[str]) -> None:
    """Live relations a Core statement is about to delete: their ends' cells change."""
    for chunk in _chunks(relation_ids):
        for from_id, to_id in session.execute(
            select(ObjectRelation.from_object_id, ObjectRelation.to_object_id).where(
                ObjectRelation.id.in_(chunk)
            )
        ):
            note_rows(session, (from_id, to_id))


def _changed(item: Any, *names: str) -> bool:
    state = attributes.instance_state(item)
    return any(state.attrs[name].history.has_changes() for name in names)


def _previous(item: Any, *names: str) -> set[str]:
    state = attributes.instance_state(item)
    return {value for name in names for value in state.attrs[name].history.deleted if value}


@event.listens_for(Session, "before_flush")
def _note_flushed_changes(session: Session, _context: Any, _instances: Any) -> None:
    for item in session.new:
        kind = type(item)
        if kind is ObjectRelation:
            note_rows(session, (item.from_object_id, item.to_object_id))
        elif kind is AttributeValue:
            _changes(session).attributes.add((item.object_id, item.attribute_type_key))
        elif kind is ChangeSetObject:
            changes = _changes(session, item.change_set_id)
            changes.cells.add(item.object_id)
            changes.new_rows.add(item.object_id)
        elif kind is ChangeSetRelation:
            note_rows(session, (item.from_object_id, item.to_object_id), item.change_set_id)
    for item in session.dirty:
        kind = type(item)
        if kind not in _TRACKED or not session.is_modified(item):
            continue
        if kind is RdmObject:
            if _changed(item, "parent_object_id"):
                _changes(session).moved.add(item.id)
        elif kind is ObjectRelation:
            ends = ("from_object_id", "to_object_id", "relation_type_key")
            if _changed(item, *ends):
                note_rows(
                    session,
                    {item.from_object_id, item.to_object_id} | _previous(item, "from_object_id", "to_object_id"),
                )
        elif kind is AttributeValue:
            _changes(session).attributes.add((item.object_id, item.attribute_type_key))
        elif kind is ChangeSetObject:
            changes = _changes(session, item.change_set_id)
            if _changed(item, "parent_object_id", "is_deleted"):
                changes.moved.add(item.object_id)
            if _changed(item, "attributes", "object_type_key", "is_deleted"):
                changes.cells.add(item.object_id)
        elif kind is ChangeSetRelation:
            ends = ("from_object_id", "to_object_id", "relation_type_key", "is_deleted")
            if _changed(item, *ends):
                note_rows(
                    session,
                    {item.from_object_id, item.to_object_id} | _previous(item, "from_object_id", "to_object_id"),
                    item.change_set_id,
                )
    for item in session.deleted:
        kind = type(item)
        if kind is RdmObject:
            note_rows(session, (item.id,))
        elif kind is ObjectRelation:
            note_rows(session, (item.from_object_id, item.to_object_id))
        elif kind is AttributeValue:
            _changes(session).attributes.add((item.object_id, item.attribute_type_key))
        elif kind is ChangeSetObject:
            changes = _changes(session, item.change_set_id)
            changes.cells.add(item.object_id)
            changes.moved.add(item.object_id)
        elif kind is ChangeSetRelation:
            note_rows(session, (item.from_object_id, item.to_object_id), item.change_set_id)


_TRACKED = {RdmObject, ObjectRelation, AttributeValue, ChangeSetObject, ChangeSetRelation}


@event.listens_for(Session, "before_commit")
def _apply_before_commit(session: Session) -> None:
    session.flush()
    apply_pending(session)


@event.listens_for(Session, "after_rollback")
def _discard_pending(session: Session) -> None:
    session.info.pop(_PENDING, None)


def apply_pending(session: Session) -> None:
    """Recompute the cells of every row the transaction's noted changes touch, in each built
    shape of the owners they belong to."""
    pending: dict[str | None, _Changes] | None = session.info.pop(_PENDING, None)
    if not pending:
        return
    live = pending.pop(None, None)
    if live is not None:
        _apply_live(session, live)
    for change_set_id, changes in sorted(pending.items()):
        _apply_change_set(session, change_set_id, changes)


def _apply_live(session: Session, changes: _Changes) -> None:
    built: dict[str, list[MatrixShape]] = {}
    for workspace_key, shape in session.execute(
        select(MatrixStateBuild.workspace_key, MatrixStateBuild.shape).where(
            MatrixStateBuild.owner_kind == "live"
        )
    ):
        built.setdefault(workspace_key, []).append(MatrixShape.from_definition(shape))
    if not built:
        return
    conditions = {shape.condition[0] for shapes in built.values() for shape in shapes if shape.condition}
    cells = changes.cells | {object_id for object_id, key in changes.attributes if key in conditions}
    touched = changes.rows | cells | changes.moved
    workspace_of: dict[str, str] = {}
    for chunk in _chunks(touched):
        workspace_of.update(
            session.execute(
                select(RdmObject.id, RdmObject.workspace_key).where(RdmObject.id.in_(chunk))
            ).all()
        )
    # A deleted row keeps no cells in any workspace.
    for chunk in _chunks(changes.rows - workspace_of.keys()):
        session.execute(
            delete(_TABLE).where(_TABLE.c.owner_kind == "live", _TABLE.c.row_id.in_(chunk))
        )
    for workspace_key, shapes in sorted(built.items()):
        owner = Owner("live", workspace_key, workspace_key)

        def of_workspace(ids: set[str], workspace_key: str = workspace_key) -> set[str]:
            return {item for item in ids if workspace_of.get(item) == workspace_key}

        rows, cells_here, moved = of_workspace(changes.rows), of_workspace(cells), of_workspace(changes.moved)
        if not (rows or cells_here or moved):
            continue
        for shape in shapes:
            scope = _scope(session, owner, shape)
            _recompute(session, owner, scope, rows | _resolve(scope, cells_here, moved))


def _apply_change_set(session: Session, change_set_id: str, changes: _Changes) -> None:
    change_set = _change_set(session, change_set_id)
    if change_set is None:
        return
    owner = Owner("change_set", change_set_id, change_set.workspace_key)
    shapes = _built_shapes(session, [owner]).get(owner, [])
    if not shapes:
        return
    moved = changes.moved | _moved_from_base(session, change_set, changes.new_rows)
    for shape in shapes:
        scope = _scope(session, owner, shape)
        _recompute(session, owner, scope, changes.rows | _resolve(scope, changes.cells, moved))


def _moved_from_base(session: Session, change_set: ChangeSet, object_ids: set[str]) -> set[str]:
    """Change set rows new in this transaction whose record's parent differs from its base row's,
    or that delete it or add a record the base lacks."""
    if not object_ids:
        return set()
    base = base_owner(change_set)
    moved = set()
    for chunk in _chunks(object_ids):
        overlay = session.execute(
            select(ChangeSetObject.object_id, ChangeSetObject.parent_object_id, ChangeSetObject.is_deleted).where(
                ChangeSetObject.change_set_id == change_set.id, ChangeSetObject.object_id.in_(chunk)
            )
        ).all()
        parents: dict[str, str | None] = {}
        if base is not None:
            entity, column = (
                (PublicationObject, PublicationObject.publication_id)
                if base.kind == "publication"
                else (ChangeSetBaseObject, ChangeSetBaseObject.base_id)
            )
            parents = dict(
                session.execute(
                    select(entity.object_id, entity.parent_object_id).where(
                        column == base.id, entity.object_id.in_(chunk)
                    )
                ).all()
            )
        moved |= {
            row.object_id
            for row in overlay
            if row.is_deleted or row.object_id not in parents or parents[row.object_id] != row.parent_object_id
        }
    return moved


def _resolve(scope: CellScope, cells: set[str], moved: set[str]) -> set[str]:
    """The rows related to the listed records and, for moved ones, to the records under them."""
    session, shape = scope.session, scope.shape
    candidates = cells | moved
    # A column record takes its cells with it: moving it changes none of their columns.
    walk_from = moved - {key for key, kind in _object_types(scope, moved).items() if kind == shape.column_type}
    for chunk in _chunks(walk_from):
        candidates |= set(session.scalars(descendants(scope, chunk, shape.walk_types)))
    rows: set[str] = set()
    for chunk in _chunks(candidates):
        rows |= set(session.scalars(related_rows(scope, chunk)))
    return rows


def _object_types(scope: CellScope, ids: set[str]) -> dict[str, str]:
    if not ids:
        return {}
    if scope.context is not None:
        return {
            key: row.object_type_key for key, row in find_objects(scope.session, scope.context, ids).items()
        }
    types: dict[str, str] = {}
    for chunk in _chunks(ids):
        types.update(
            scope.session.execute(
                select(RdmObject.id, RdmObject.object_type_key).where(RdmObject.id.in_(chunk))
            ).all()
        )
    return types


def _recompute(session: Session, owner: Owner, scope: CellScope, rows: set[str]) -> None:
    """Replace the rows' states with ones derived from records. A change set replaces a row's
    base states only where it holds cells for the row or the base does."""
    shape = scope.shape
    for chunk in _chunks(rows):
        session.execute(
            delete(_TABLE).where(
                _TABLE.c.owner_kind == owner.kind,
                _TABLE.c.owner_id == owner.id,
                _TABLE.c.shape_key == shape.key,
                _TABLE.c.row_id.in_(chunk),
            )
        )
        states = _by_row(session.execute(cell_states(scope, chunk)))
        if owner.kind != "change_set":
            _insert(
                session,
                _state_rows(
                    owner,
                    shape.key,
                    (
                        _State(row_id, column_id, *counts)
                        for row_id, cells in sorted(states.items())
                        for column_id, counts in sorted(cells.items())
                    ),
                ),
            )
            continue
        base = base_owner(scope.context.change_set)
        in_base: set[str] = set()
        if base is not None:
            in_base = set(
                session.scalars(
                    _stored(session, base, shape.key)
                    .with_only_columns(_TABLE.c.row_id)
                    .where(_TABLE.c.row_id.in_(chunk))
                    .distinct()
                )
            )
        _insert(session, _overlay_rows(owner, shape.key, sorted(states.keys() | in_base), states))


@dataclass(frozen=True)
class _State:
    row_id: str
    column_id: str
    record_count: int
    matching_count: int


# Reads.


def _current_owners(read: CellScope) -> list[Owner]:
    """The owners whose states make up the read's context: one, or a change set over its base."""
    workspace_key, context = read.workspace_key, read.context
    if context is None:
        return [Owner("live", workspace_key, workspace_key)]
    if context.kind == "publication":
        return [Owner("publication", context.id, workspace_key)]
    base = base_owner(context.change_set)
    return [Owner("change_set", context.id, workspace_key), *([base] if base else [])]


def _all_built(session: Session, owners: Sequence[Owner], shape_key: str) -> bool:
    found = session.execute(
        select(MatrixStateBuild.owner_kind, MatrixStateBuild.owner_id).where(
            MatrixStateBuild.shape_key == shape_key,
            MatrixStateBuild.owner_id.in_(sorted({owner.id for owner in owners})),
        )
    ).all()
    return {(owner.kind, owner.id) for owner in owners} <= {tuple(row) for row in found}


# The filter reads each selected column's rows from this index, in row order.
_COLUMN_INDEX = "ix_matrix_cell_states_column"


def _column_rows(owner: Owner, shape_key: str, column_id: str, *terms: Any) -> Select[Any]:
    """The owner's rows with a stored cell in one column, meeting ``terms`` (callables on the
    table). Pinned to the column index: SQLite otherwise may scan the owner's whole shape through
    the unique index, whose order serves a merge but not the column."""
    table = _TABLE.alias()
    return (
        select(table.c.row_id)
        .where(
            table.c.owner_kind == owner.kind,
            table.c.owner_id == owner.id,
            table.c.shape_key == shape_key,
            table.c.column_id == column_id,
            *(term(table) for term in terms),
        )
        .with_hint(table, f"INDEXED BY {_COLUMN_INDEX}", "sqlite")
    )


def _replaced_rows(overlay: Owner, shape_key: str) -> Select[Any]:
    return _column_rows(overlay, shape_key, REPLACED)


def _rows_of(compound: Any, name: str) -> Select[Any]:
    """A compound select as a plain one, so compounds nest in SQLite, which takes no parentheses."""
    part = compound.subquery(name)
    return select(part.c.row_id)


def _present(owners: Sequence[Owner], shape_key: str, column_id: str, *terms: Any) -> list[Select[Any]]:
    """The context's rows whose cell in the column is stored and meets ``terms``: one owner's, or a
    change set's and its base's rows the change set does not replace. Kept as separate selects so
    a compound over them stays flat and SQLite merges it in index order."""
    if len(owners) == 1:
        return [_column_rows(owners[0], shape_key, column_id, *terms)]
    overlay, base = owners
    replaced = _replaced_rows(overlay, shape_key)
    return [
        _column_rows(overlay, shape_key, column_id, *terms),
        _column_rows(base, shape_key, column_id, *terms, lambda table: table.c.row_id.not_in(replaced)),
    ]


def _any(parts: Sequence[Select[Any]]) -> Any:
    return union(*parts) if len(parts) > 1 else parts[0]


def stored_row_filter(
    read: CellScope, column_ids: Sequence[str], state: str, publication_number: int | None
) -> tuple[list[str], bool] | None:
    """The rows whose cell in some selected column has ``state``, from stored states, as (IDs,
    negated): with ``negated`` the rows are those *not* listed. ``None`` when an owner the read
    needs is not built; the caller then derives the cells from records.

    Each selected column contributes its rows in row order, and the columns combine by ``UNION``,
    ``EXCEPT`` and ``INTERSECT``, which SQLite merges without sorting.
    """
    session, shape_key = read.session, read.shape.key
    current = _current_owners(read)
    history = Owner("history", read.workspace_key, read.workspace_key)
    needs_history = state in {"historyOnly", "none"}
    if not _all_built(session, [*current, *([history] if needs_history else [])], shape_key):
        return None
    columns = sorted(set(column_ids))

    def held(column_id: str) -> Select[Any]:
        earlier = (
            [lambda table: table.c.first_publication_number < publication_number]
            if publication_number is not None
            else []
        )
        return _column_rows(history, shape_key, column_id, *earlier)

    def holding(column_id: str) -> list[Select[Any]]:
        return _present(current, shape_key, column_id, lambda table: table.c.record_count > 0)

    if state in {"one", "several", "inactive"}:
        matching = {
            "one": lambda table: table.c.matching_count == 1,
            "several": lambda table: table.c.matching_count > 1,
            "inactive": lambda table: table.c.matching_count == 0,
        }[state]
        parts = [
            part
            for column_id in columns
            for part in _present(current, shape_key, column_id, lambda table: table.c.record_count > 0, matching)
        ]
        return list(session.scalars(_any(parts))), False
    if state == "historyOnly":
        parts = [
            _rows_of(except_(held(column_id), *holding(column_id)), f"matrix_history_only_{index}")
            for index, column_id in enumerate(columns)
        ]
        return list(session.scalars(_any(parts))), False
    # none: a row matches unless every selected column holds a record now or held one before.
    covered = [
        _rows_of(union(held(column_id), *holding(column_id)), f"matrix_covered_{index}")
        for index, column_id in enumerate(columns)
    ]
    statement = intersect(*covered) if len(covered) > 1 else covered[0]
    return list(session.scalars(statement)), True


def listed(session: Session, column: Any, ids: Sequence[str]) -> Any:
    """``column IN ids`` for a list of any length: SQLite reads a long list as one JSON value.

    The term is kept off the column's index: a paging statement then walks its sort index in
    order and probes the list, rather than looking up every listed row and sorting them all.
    """
    if len(ids) <= _CHUNK or session.get_bind().dialect.name != "sqlite":
        return column.in_(list(ids))
    values = func.json_each(literal(json.dumps(list(ids)))).table_valued("value")
    return unindexed(column.in_(select(values.c.value)))


# Verification.


def verify(session: Session) -> list[str]:
    """Compare every built (owner, shape) with states derived from records now; each mismatch is
    one message. A rebuild-and-compare check for tests and operators."""
    problems = []
    for workspace_key, kind, owner_id, definition in session.execute(
        select(
            MatrixStateBuild.workspace_key,
            MatrixStateBuild.owner_kind,
            MatrixStateBuild.owner_id,
            MatrixStateBuild.shape,
        ).order_by(MatrixStateBuild.sequence_id)
    ):
        owner, shape = Owner(kind, owner_id, workspace_key), MatrixShape.from_definition(definition)
        stored, derived = _stored_effective(session, owner, shape), _derived(session, owner, shape)
        if stored != derived:
            differing = sorted(key for key in stored.keys() | derived.keys() if stored.get(key) != derived.get(key))
            problems.append(
                f"{kind} {owner_id} shape {shape.key}: {len(differing)} cells differ, e.g. "
                + ", ".join(f"{key}: stored {stored.get(key)} derived {derived.get(key)}" for key in differing[:3])
            )
    return problems


def _stored_effective(session: Session, owner: Owner, shape: MatrixShape) -> dict[tuple[str, str], Any]:
    def cells(rows: Iterable[Any]) -> dict[tuple[str, str], Any]:
        return {
            (row.row_id, row.column_id): (
                (row.record_count, row.matching_count)
                if owner.kind != "history"
                else row.first_publication_number
            )
            for row in rows
            if row.column_id != REPLACED
        }

    own = session.execute(_stored(session, owner, shape.key)).all()
    if owner.kind != "change_set":
        return cells(own)
    base = base_owner(_change_set(session, owner.id))
    replaced = {row.row_id for row in own if row.column_id == REPLACED}
    base_rows = session.execute(_stored(session, base, shape.key)).all() if base else []
    return {**cells(row for row in base_rows if row.row_id not in replaced), **cells(own)}


def _derived(session: Session, owner: Owner, shape: MatrixShape) -> dict[tuple[str, str], Any]:
    if owner.kind != "history":
        return {
            (row.row_id, row.column_id): (row.record_count, row.matching_count)
            for row in session.execute(cell_states(_scope(session, owner, shape), None))
        }
    first: dict[tuple[str, str], Any] = {}
    for publication_id, number in session.execute(
        select(Publication.id, Publication.publication_number)
        .where(Publication.workspace_key == owner.workspace_key)
        .order_by(Publication.publication_number)
    ):
        publication = Owner("publication", publication_id, owner.workspace_key)
        for row in session.execute(cell_states(_scope(session, publication, shape), None)):
            first.setdefault((row.row_id, row.column_id), number)
    return first
