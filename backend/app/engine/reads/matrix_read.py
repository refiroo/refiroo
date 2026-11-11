"""A relation matrix view read in one context (Base 0.8 A2; 0.17 EX1).

What the matrix page (``management/projections/relation_matrix.py``) and the export of a matrix
(``engine/jobs/export_views.py``) both read: the view's shape in its context, the named column
records, the row state filter (D12) and the walk down from a column record to the records that can
hold its cells. Nothing here names a type or relation.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import Select, String, and_, func, literal, or_, select, union_all
from sqlalchemy.dialects.postgresql import distinct_on
from sqlalchemy.orm import Session, aliased

from ...errors import api_error
from ...models.database import Publication, PublicationObject, PublicationRelation, RdmObject
from ...models.schema import (
    EngineModel,
    ObjectTypeRelationDefinition,
    RelationMatrixViewConfig,
    RelationMatrixViewDefinition,
)
from ..indexes.matrix_states import listed, row_list, stored_row_filter
from ..model.candidate_places import DerivedPlace, derive_place, propose_place
from ..model.registry import ModelSnapshot
from ..model.traversal import ancestor_type_keys, parent_type_keys
from .context_sets import record_source
from .matrix_cells import (
    MAX_DEPTH,
    CellScope,
    MatrixShape,
    cell_records,
    id_rows,
    view_binding,
)
from .model_query import candidate_place_filters
from .object_query import build_object_query
from .snapshot_reads import (
    build_snapshot_object_query,
    change_set_context,
    find_objects,
    publication_context,
)

MAX_COLUMNS = 20
# Ends each name in a container's sort path, so a record sorts before the records under it.
PATH_SEPARATOR = "\x01"


@dataclass
class MatrixRead(CellScope):
    """One view's read: its shape in the read's context, and what the view adds to it."""

    application_key: str = ""
    view_key: str = ""
    snapshot: ModelSnapshot | None = None
    config: RelationMatrixViewConfig | None = None
    binding: ObjectTypeRelationDefinition | None = None
    # The publication read, whose history evidence comes from earlier publications only.
    publication_number: int | None = None

    @property
    def model(self) -> EngineModel:
        return self.snapshot.model

    @property
    def conflict_scope(self) -> bool:
        return (
            self.outgoing
            and self.binding.features.get("uniqueToAncestorTypeKey")
            == self.config.columnObjectTypeKey
        )

    def filters(self) -> dict[str, Any]:
        return {
            "workspaceKey": self.workspace_key,
            "changeSetId": self.context.id
            if self.context and self.context.kind == "change_set"
            else None,
            "publicationId": self.context.id
            if self.context and self.context.kind == "publication"
            else None,
            "modelHash": self.snapshot.model_hash,
            "applicationKey": self.application_key,
            "viewKey": self.view_key,
        }

    def container_types(self) -> set[str]:
        """Types that can hold the cell type, at some depth, and sit under the column type."""
        column_type, cell_type = self.config.columnObjectTypeKey, self.config.cellObjectTypeKey
        return {
            key
            for key in ancestor_type_keys(self.model, cell_type)
            if key != column_type and column_type in ancestor_type_keys(self.model, key)
        }

    def publications(self) -> Any:
        """The workspace's publications history evidence comes from, with their numbers."""
        statement = select(Publication.id, Publication.publication_number).where(
            Publication.workspace_key == self.workspace_key
        )
        if self.publication_number is not None:
            statement = statement.where(Publication.publication_number < self.publication_number)
        return statement.subquery("matrix_publications")


def build_matrix_read(
    session: Session,
    workspace_key: str,
    snapshot: ModelSnapshot,
    view: RelationMatrixViewDefinition,
    application_key: str,
    change_set_id: str | None,
    publication_id: str | None,
) -> MatrixRead:
    """The view's read in the context named, over the session's current snapshot."""
    config = view.config
    binding = view_binding(snapshot.model, config)
    context = None
    publication_number = None
    if change_set_id:
        context = change_set_context(session, change_set_id)
    elif publication_id:
        context = publication_context(session, publication_id)
        publication_number = session.scalar(
            select(Publication.publication_number).where(Publication.id == publication_id)
        )
    return MatrixRead(
        session,
        workspace_key,
        MatrixShape.of_view(snapshot.model, config, binding),
        context,
        application_key=application_key,
        view_key=view.key,
        snapshot=snapshot,
        config=config,
        binding=binding,
        publication_number=publication_number,
    )


def record_id(item: Any) -> str:
    """The public ID of a live record or a change set or publication row."""
    return item.id if isinstance(item, RdmObject) else item.object_id


def object_types(read: MatrixRead, ids: Sequence[str]) -> dict[str, str]:
    if read.context is not None:
        return {
            key: row.object_type_key
            for key, row in find_objects(read.session, read.context, ids).items()
        }
    return dict(
        read.session.execute(
            select(RdmObject.id, RdmObject.object_type_key).where(
                RdmObject.workspace_key == read.workspace_key, RdmObject.id.in_(list(ids))
            )
        ).all()
    )


def named_columns(read: MatrixRead, column_ids: Sequence[str]) -> list[Any]:
    if len(column_ids) > MAX_COLUMNS:
        raise api_error(
            422,
            "TOO_MANY_COLUMNS",
            f"Name at most {MAX_COLUMNS} columns",
            {"path": "/query/columnIds", "limit": MAX_COLUMNS},
        )
    if len(set(column_ids)) != len(column_ids):
        raise api_error(
            422,
            "DUPLICATE_COLUMN_IDS",
            "Each column may be named once",
            {"path": "/query/columnIds"},
        )
    column_type = read.config.columnObjectTypeKey
    if read.context is not None:
        found = find_objects(read.session, read.context, column_ids)
    else:
        found = {
            item.id: item
            for item in read.session.scalars(
                select(RdmObject).where(
                    RdmObject.workspace_key == read.workspace_key,
                    RdmObject.id.in_(list(column_ids)),
                )
            )
        }
    missing = [
        key for key in column_ids if key not in found or found[key].object_type_key != column_type
    ]
    if missing:
        raise api_error(
            404,
            "RELATION_MATRIX_COLUMN_NOT_FOUND",
            f"Columns must be '{column_type}' records in the selected context",
            {"columnIds": missing, "columnObjectTypeKey": column_type},
        )
    return [found[key] for key in column_ids]


def column_query(read: MatrixRead, id_filter: Callable[[Any], Any] | None = None) -> Any:
    options = {
        "object_type_key": read.config.columnObjectTypeKey,
        "application_key": None,
        "parent_object_id": None,
        "search": None,
        "sort": "name",
        "field_filters": [],
        "id_filter": id_filter,
    }
    if read.context is None:
        return build_object_query(read.model, workspace_key=read.workspace_key, **options)
    return build_snapshot_object_query(read.model, read.context, **options)


def state_filter(read: MatrixRead, column_ids: list[str], state: str) -> Callable[[Any], Any]:
    """A predicate on a row's ID: some selected column's cell has ``state``, over every row.

    Stored cell states decide it once for the request (A3b): the matching row IDs are read by
    index and every paging statement filters by that list, one shared parameter. Where an owner the read needs has no
    stored states, the cells are derived from records in each statement instead (D12).
    """
    stored = stored_row_filter(read, column_ids, state, read.publication_number)
    if stored is not None:
        ids, negated = stored
        rows = row_list(ids)
        return lambda row_id: ~listed(row_id, rows) if negated else listed(row_id, rows)
    pairs = current_pairs(read, column_ids)
    if state in {"one", "several", "inactive"}:
        matching = func.sum(pairs.c.meets)
        having = {"one": matching == 1, "several": matching > 1, "inactive": matching == 0}[state]
        rows = select(pairs.c.row_id).group_by(pairs.c.row_id, pairs.c.column_id).having(having)
        return lambda row_id: row_id.in_(rows)
    history = history_pairs(read, column_ids)

    def predicate(row_id: Any) -> Any:
        clauses = []
        for column_id in column_ids:
            present = row_id.in_(select(pairs.c.row_id).where(pairs.c.column_id == column_id))
            held = row_id.in_(select(history.c.row_id).where(history.c.column_id == column_id))
            clauses.append(and_(~present, held if state == "historyOnly" else ~held))
        return or_(*clauses)

    return predicate


def column_anchor(column_ids: list[str]) -> Any:
    """The selected column IDs as rows."""
    selected = id_rows(column_ids, "matrix_selected_columns")
    return select(selected.c.id.label("column_id")).subquery("matrix_selected")


def cells_under(read: MatrixRead, column_ids: list[str]) -> Any:
    """Every cell record under the selected columns, in the context: (``cell_id``, ``column_id``,
    ``owner``), one walk down from the column records through the container types."""
    config = read.config
    selected = column_anchor(column_ids)
    walk = select(
        selected.c.column_id.label("node"),
        selected.c.column_id,
        literal(config.columnObjectTypeKey, String).label("object_type_key"),
        literal(None, String).label("owner"),
        literal(0).label("depth"),
    ).cte("matrix_down", recursive=True)
    child = read.object_rows(["parent_object_id", "object_type_key"], "matrix_down_rows")
    walk = walk.union_all(
        select(
            child.c.id, walk.c.column_id, child.c.object_type_key, child.c.owner, walk.c.depth + 1
        )
        .select_from(walk)
        .join(
            child,
            and_(
                child.c.parent_object_id == walk.c.node,
                child.c.object_type_key.in_(read.walk_types()),
            ),
        )
        .where(walk.c.depth < MAX_DEPTH)
    )
    return (
        select(walk.c.node.label("cell_id"), walk.c.column_id, walk.c.owner)
        .where(walk.c.object_type_key == config.cellObjectTypeKey)
        .subquery("matrix_down_cells")
    )


def current_pairs(read: MatrixRead, column_ids: list[str]) -> Any:
    """(row, column, meets) for every cell record under the selected columns, in the context."""
    config = read.config
    cells = cells_under(read, column_ids)
    pairs = []
    for arm in read.relation_arms():
        relation = aliased(arm.entity)
        pairs.append(
            select(
                getattr(relation, read.anchor_end).label("row_id"),
                cells.c.column_id,
                read.meets(cells.c.cell_id, cells.c.owner).label("meets"),
            )
            .select_from(cells)
            .join(
                relation,
                and_(
                    getattr(relation, read.other_end) == cells.c.cell_id,
                    relation.relation_type_key == config.relationTypeKey,
                    *arm.where(relation),
                ),
            )
        )
    return (union_all(*pairs) if len(pairs) > 1 else pairs[0]).cte("matrix_pairs")


def history_pairs(read: MatrixRead, column_ids: list[str]) -> Any:
    """(row, column) for every cell record an earlier publication held under a selected column."""
    config = read.config
    publications = read.publications()
    top = aliased(PublicationObject)
    walk = (
        select(
            top.publication_id,
            top.object_id.label("node"),
            top.object_id.label("column_id"),
            top.object_type_key,
            literal(0).label("depth"),
        )
        .select_from(top)
        .join(publications, publications.c.id == top.publication_id)
        .where(top.object_id.in_(column_ids), top.object_type_key == config.columnObjectTypeKey)
        .cte("matrix_history_down", recursive=True)
    )
    child = aliased(PublicationObject)
    walk = walk.union_all(
        select(
            child.publication_id,
            child.object_id,
            walk.c.column_id,
            child.object_type_key,
            walk.c.depth + 1,
        )
        .select_from(walk)
        .join(
            child,
            and_(
                child.publication_id == walk.c.publication_id,
                child.parent_object_id == walk.c.node,
                child.object_type_key.in_(read.walk_types()),
            ),
        )
        .where(walk.c.depth < MAX_DEPTH)
    )
    relation = aliased(PublicationRelation)
    return (
        select(getattr(relation, read.anchor_end).label("row_id"), walk.c.column_id)
        .select_from(walk)
        .join(
            relation,
            and_(
                relation.publication_id == walk.c.publication_id,
                getattr(relation, read.other_end) == walk.c.node,
                relation.relation_type_key == config.relationTypeKey,
            ),
        )
        .where(walk.c.object_type_key == config.cellObjectTypeKey)
        .cte("matrixhistory_pairs")
    )


def walk_below(read: MatrixRead, column: Any, types: Sequence[str]) -> Any:
    """The column record and the records of ``types`` under it, in the read's context, each with
    a sort path of lower-cased names from below the column record."""
    walk = select(
        literal(record_id(column), String).label("object_id"),
        literal(read.config.columnObjectTypeKey, String).label("object_type_key"),
        literal(column.name, String).label("name"),
        literal(column.version).label("version"),
        literal(None, String).label("owner"),
        literal("", String).label("sort_path"),
        literal(0).label("depth"),
    ).cte("matrix_below", recursive=True)
    child = read.object_rows(
        ["parent_object_id", "object_type_key", "name", "version"], "matrix_below_rows"
    )
    return walk.union_all(
        select(
            child.c.id,
            child.c.object_type_key,
            child.c.name,
            child.c.version,
            child.c.owner,
            walk.c.sort_path + func.lower(child.c.name) + literal(PATH_SEPARATOR, String),
            walk.c.depth + 1,
        )
        .select_from(walk)
        .join(
            child,
            and_(
                child.c.parent_object_id == walk.c.object_id,
                child.c.object_type_key.in_(types),
            ),
        )
        .where(walk.c.depth < MAX_DEPTH)
    )


def cell_criteria(read: MatrixRead) -> tuple[Any, ...]:
    """The binding's candidate criteria at the cell's end: what a record in a cell must meet."""
    return read.binding.candidates_at("to" if read.outgoing else "from")


def derived_place(read: MatrixRead) -> DerivedPlace | None:
    """The record the candidate criteria fix as the place a new cell record goes (PP-D24), or ``None``
    where they fix none."""
    return derive_place(
        read.model,
        read.config.columnObjectTypeKey,
        read.config.cellObjectTypeKey,
        cell_criteria(read),
    )


def column_application(read: MatrixRead, column: Any) -> str | None:
    """The application the column record belongs to: a container created under it is created in the
    same one (a record stands in its parent's application)."""
    source = record_source(read.workspace_key, read.context, [read.config.columnObjectTypeKey])
    return read.session.scalar(
        select(source.c.application_key).where(source.c.object_id == record_id(column))
    )


def container_applications(read: MatrixRead, container_ids: Sequence[str]) -> dict[str, str]:
    """The application each container belongs to: a record created in one stands in the same
    application (a record stands in its parent's)."""
    if not container_ids:
        return {}
    types = sorted(read.container_types() | {read.config.columnObjectTypeKey})
    source = record_source(read.workspace_key, read.context, types)
    return dict(
        read.session.execute(
            select(source.c.object_id, source.c.application_key).where(
                source.c.object_id.in_(list(container_ids))
            )
        ).all()
    )


def proposed_place(read: MatrixRead, column: Any) -> DerivedPlace | None:
    """The new container to propose under ``column`` where neither the criteria nor the data give a
    place (PP-D28), from the containers the view uses in other columns."""
    types = sorted(read.container_types())
    below = walk_below(read, column, types)
    cells = cell_records(read, None, rows_of_type=True)
    containers = record_source(read.workspace_key, read.context, types)
    used = read.session.execute(
        select(containers.c.object_type_key, containers.c.name)
        .where(
            containers.c.object_id.in_(select(cells.c.parent_object_id)),
            containers.c.object_id.not_in(select(below.c.object_id)),
        )
        .ext(distinct_on(containers.c.object_id))
    ).all()
    chain_types = sorted(
        {read.config.columnObjectTypeKey}
        | ancestor_type_keys(read.model, read.config.columnObjectTypeKey)
    )
    source = record_source(read.workspace_key, read.context, chain_types)
    rows = {
        item.object_id: item
        for item in read.session.execute(
            select(
                source.c.object_id,
                source.c.object_type_key,
                source.c.name,
                source.c.parent_object_id,
                source.c.attributes,
            )
        )
    }
    chain: list[tuple[str, str, Callable[[], dict[str, Any]]]] = []
    at: str | None = record_id(column)
    for _ in range(MAX_DEPTH):
        item = rows.get(at) if at is not None else None
        if item is None:
            break
        chain.append(
            (item.object_type_key, item.name, lambda item=item: dict(item.attributes or {}))
        )
        at = item.parent_object_id
    return propose_place(
        read.model,
        read.config.columnObjectTypeKey,
        read.config.cellObjectTypeKey,
        cell_criteria(read),
        [(item.object_type_key, item.name) for item in used],
        chain,
    )


def container_cell_counts(read: MatrixRead, container_ids: Sequence[str]) -> dict[str, int]:
    """How many cell records stand directly under each container and are related to a row record by
    the view's relationship: the cells of the view, the evidence of where a column's new cells go
    (PP-D24)."""
    if not container_ids:
        return {}
    cells = cell_records(read, None, rows_of_type=True)
    parent = cells.c.parent_object_id
    return dict(
        read.session.execute(
            select(parent, func.count(func.distinct(cells.c.cell_id)))
            .where(parent.in_(list(container_ids)))
            .group_by(parent)
        ).all()
    )


def container_rows(read: MatrixRead, column: Any) -> Select[Any]:
    """The column record and the records under it that can directly hold a new cell record and meet
    the binding's candidate criteria there: (``object_id``, ``object_type_key``, ``name``,
    ``sort_path``). A record created under any of them meets the criteria that name an ancestor; the
    record's own fields are left to the write (PP-D24)."""
    walk = walk_below(read, column, sorted(read.container_types()))
    direct = sorted(parent_type_keys(read.model, read.config.cellObjectTypeKey))
    statement = select(
        walk.c.object_id, walk.c.object_type_key, walk.c.name, walk.c.sort_path
    ).where(walk.c.object_type_key.in_(direct))
    criteria = cell_criteria(read)
    if criteria:
        cell_type = read.model.object_type(read.config.cellObjectTypeKey)
        assert cell_type is not None
        for found in candidate_place_filters(
            read.model,
            cell_type,
            criteria,
            workspace_key=read.workspace_key,
            context=read.context,
        ):
            statement = statement.where(found.predicate(walk.c.object_id))
    return statement
