"""Relation matrix reads (Base 0.8 A2).

A ``relationMatrix`` view lists records of its row type as rows and records of its column type as
columns. A cell holds the row's related records, through the view's one binding read from the row's
end (``direction``), that sit under the column's record: a cell record's column is its nearest
ancestor of the column type. Everything comes from the view and its binding; nothing here names a
type or relation.

Rows are every record of the row type in the workspace context, not only those the view's
application created, since an application may list a type another application owns.

A page costs a fixed number of statements whatever the dataset holds:

* the rows, through the object query builder, so search, sort, seek, positions and totals mean
  what they mean on an object list;
* the columns, named (at most ``MAX_COLUMNS``) or a name-ordered page with its own cursor (D10);
* every cell of the page in one statement: the page rows' relations of the binding, their related
  records, and one depth-bounded recursive walk up from each record to its column record, ranked so
  a cell returns at most ``CELL_RECORD_LIMIT`` records with its counts;
* the history evidence in one statement of the same shape over the workspace's publications;
* the rows' relation-set versions and the field values rows, columns and cells show.

A row state filter (``state`` with ``columnIds``) decides over every row, not a page: one recursive
walk down from the selected column records through the container types to cell records, then to
rows through the binding (D12), restricts the row statement before it is paged. Cell states (D11):

* ``one`` — exactly one related record under the column meets the binding's
  ``uniqueWhenToAttributeEquals`` condition (every record meets it when none is declared);
* ``several`` — more than one does; a ``conflict`` when the binding's ``uniqueToAncestorTypeKey`` is
  the column type, which live writes refuse but a change set can hold before validation;
* ``inactive`` — related records exist and none meets the condition;
* ``historyOnly`` — none in the context, but an earlier publication of the workspace held one;
* ``none`` — none of the above.

The binding's condition and uniqueness scope describe its ``to`` end, so they apply to cells only
when the row is the ``from`` end (``outgoing``); read ``incoming``, every cell record meets the
condition and ``several`` is never a conflict.

The walks join rows by keyed lookups on each context's tables. A change set's downward walk has one
recursive arm for its base and one for its own rows, which SQLite accepts; PostgreSQL needs the arms
in one recursive term (0.10 hardening, with D25).
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

from sqlalchemy import (
    Select,
    String,
    and_,
    false,
    func,
    literal,
    or_,
    select,
    union_all,
)
from sqlalchemy.orm import Session, aliased

from ..db import begin_snapshot_read
from ..errors import api_error
from ..models.api import (
    RelationMatrixCell,
    RelationMatrixCellRecord,
    RelationMatrixColumn,
    RelationMatrixContainer,
    RelationMatrixContainerPage,
    RelationMatrixLinkCandidate,
    RelationMatrixLinkCandidatePage,
    RelationMatrixPage,
    RelationMatrixPathPart,
    RelationMatrixPublicationReference,
    RelationMatrixRecord,
    RelationMatrixRow,
)
from ..models.database import (
    AttributeValue,
    Publication,
    PublicationObject,
    PublicationRelation,
    RdmObject,
    RelationSetVersion,
    SnapshotAttributeValue,
)
from ..models.schema import (
    EngineModel,
    ObjectTypeRelationDefinition,
    RelationMatrixViewConfig,
    RelationMatrixViewDefinition,
)
from .attributes import VALUE_COLUMNS, stored_json_value
from .matrix_cells import (
    MAX_DEPTH,
    CellScope,
    MatrixShape,
    cell_columns,
    cell_records,
    id_rows,
    view_binding,
)
from .matrix_cells import found as _found
from .matrix_cells import unindexed as _unindexed
from .matrix_states import listed, stored_row_filter
from .model.registry import ModelSnapshot, resolve_request_model
from .model.traversal import ancestor_type_keys, parent_type_keys
from .objects import _object_paths, build_object_query
from .pagination import Page, PageRequest, paginate_statement, text_key
from .snapshot_reads import (
    build_snapshot_object_query,
    change_set_context,
    find_objects,
    object_paths,
    publication_context,
)
from .workspaces import resolve_workspace

MAX_COLUMNS = 20
CELL_RECORD_LIMIT = 5

STATES = ("one", "several", "inactive", "historyOnly", "none")
# Ends each name in a container's sort path, so a record sorts before the records under it.
_PATH_SEPARATOR = "\x01"


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
            "changeSetId": self.context.id if self.context and self.context.kind == "change_set" else None,
            "publicationId": self.context.id if self.context and self.context.kind == "publication" else None,
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


def open_matrix_read(
    session: Session,
    workspace_key: str,
    application_key: str,
    view_key: str,
    change_set_id: str | None,
    publication_id: str | None,
) -> MatrixRead:
    begin_snapshot_read(session)
    workspace = resolve_workspace(session, workspace_key)
    snapshot = resolve_request_model(session, workspace.key, change_set_id, publication_id)
    application = next(
        (item for item in snapshot.model.applications if item.key == application_key), None
    )
    view = (
        next((item for item in application.views if item.key == view_key), None)
        if application
        else None
    )
    if not isinstance(view, RelationMatrixViewDefinition):
        raise api_error(
            404,
            "relation_matrix_view_not_found",
            "Relation matrix view not found in the selected model",
            {"applicationKey": application_key, "viewKey": view_key},
        )
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
        workspace.key,
        MatrixShape.of_view(snapshot.model, config, binding),
        context,
        application_key=application_key,
        view_key=view_key,
        snapshot=snapshot,
        config=config,
        binding=binding,
        publication_number=publication_number,
    )


def relation_matrix_page(
    read: MatrixRead,
    *,
    page: PageRequest,
    page_size: int | None,
    parent_object_id: str | None,
    search: str | None,
    sort: str | None,
    column_ids: Sequence[str] | None,
    column_cursor: str | None,
    column_page_size: int,
    state: str | None,
) -> RelationMatrixPage:
    if column_ids is not None and column_cursor is not None:
        raise api_error(
            422,
            "conflicting_column_parameters",
            "Name the columns with columnIds or page them with columnCursor, not both",
            {"parameters": ["columnIds", "columnCursor"]},
        )
    if state is not None and not column_ids:
        raise api_error(
            422,
            "relation_matrix_state_requires_columns",
            "A state filter applies to the columns named by columnIds",
            {"path": "/query/columnIds"},
        )
    _validate_parent_scope(read, parent_object_id)
    if column_ids:
        columns = _named_columns(read, column_ids)
        column_page: Page[Any] | None = None
    else:
        column_page = _column_page(read, column_cursor, column_page_size)
        columns = column_page.items
    selected = [_record_id(item) for item in columns]

    id_filter = _state_filter(read, selected, state) if state is not None else None
    options = {
        "object_type_key": read.config.rowObjectTypeKey,
        "application_key": None,
        "parent_object_id": parent_object_id,
        "search": search,
        "sort": sort,
        "field_filters": [],
        "search_fields": read.config.searchFields,
        "id_filter": id_filter,
    }
    if read.context is None:
        query = build_object_query(read.model, workspace_key=read.workspace_key, **options)
    else:
        query = build_snapshot_object_query(read.model, read.context, **options)
    row_page = paginate_statement(
        read.session,
        query.statement,
        keys=query.keys,
        scope="relation-matrix",
        filters={
            **query.filters,
            **read.filters(),
            "columnIds": list(column_ids) if column_ids else None,
            "state": state,
        },
        page=page,
        page_size=page_size or read.config.pageSize,
        message="Relation matrix cursor is invalid",
        rows=read.context is not None,
        seek=query.seek,
        overlay=query.overlay,
    )
    rows = row_page.items
    row_ids = [_record_id(item) for item in rows]
    items = _rows(read, rows, row_ids, selected)
    column_labels = _field_values(read, columns, (read.config.columnLabelField,))
    return RelationMatrixPage(
        items=items,
        **row_page.links(),
        columns=[
            RelationMatrixColumn(
                id=_record_id(item),
                name=item.name,
                label=column_labels[_record_id(item)][read.config.columnLabelField],
            )
            for item in columns
        ],
        columnsNextCursor=column_page.next_cursor if column_page else None,
        columnsPrevCursor=column_page.prev_cursor if column_page else None,
    )


def _record_id(item: Any) -> str:
    """The public ID of a live record or a change set or publication row."""
    return item.id if isinstance(item, RdmObject) else item.object_id


def _validate_parent_scope(read: MatrixRead, parent_object_id: str | None) -> None:
    if parent_object_id is None:
        return
    parent_type = _object_types(read, [parent_object_id]).get(parent_object_id)
    if parent_type is None:
        raise api_error(
            404,
            "relation_matrix_parent_not_found",
            "Parent record not found in the selected context",
            {"parentObjectId": parent_object_id},
        )
    row_type = read.model.object_type(read.config.rowObjectTypeKey)
    parent_relations = set(row_type.behavior.get("parentRelationTypeKeys", ()))
    if not any(
        allowed.relationTypeKey in parent_relations
        and allowed.fromObjectTypeKey == parent_type
        and allowed.toObjectTypeKey == row_type.key
        for allowed in read.model.objectTypeRelations
    ):
        raise api_error(
            422,
            "relation_matrix_parent_scope_mismatch",
            f"A '{parent_type}' record cannot contain the matrix's '{row_type.key}' rows",
            {"parentObjectId": parent_object_id, "parentObjectTypeKey": parent_type},
        )


def _object_types(read: MatrixRead, ids: Sequence[str]) -> dict[str, str]:
    if read.context is not None:
        return {key: row.object_type_key for key, row in find_objects(read.session, read.context, ids).items()}
    return dict(
        read.session.execute(
            select(RdmObject.id, RdmObject.object_type_key).where(
                _unindexed(RdmObject.workspace_key == read.workspace_key), RdmObject.id.in_(list(ids))
            )
        ).all()
    )


def _named_columns(read: MatrixRead, column_ids: Sequence[str]) -> list[Any]:
    if len(column_ids) > MAX_COLUMNS:
        raise api_error(
            422,
            "too_many_columns",
            f"Name at most {MAX_COLUMNS} columns",
            {"path": "/query/columnIds", "limit": MAX_COLUMNS},
        )
    if len(set(column_ids)) != len(column_ids):
        raise api_error(
            422,
            "duplicate_column_ids",
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
                    # Found by ID: the workspace index would read every record of the workspace.
                    _unindexed(RdmObject.workspace_key == read.workspace_key),
                    RdmObject.id.in_(list(column_ids)),
                )
            )
        }
    missing = [key for key in column_ids if key not in found or found[key].object_type_key != column_type]
    if missing:
        raise api_error(
            404,
            "relation_matrix_column_not_found",
            f"Columns must be '{column_type}' records in the selected context",
            {"columnIds": missing, "columnObjectTypeKey": column_type},
        )
    return [found[key] for key in column_ids]


def _column_page(read: MatrixRead, cursor: str | None, page_size: int) -> Page[Any]:
    options = {
        "object_type_key": read.config.columnObjectTypeKey,
        "application_key": None,
        "parent_object_id": None,
        "search": None,
        "sort": "name",
        "field_filters": [],
    }
    if read.context is None:
        query = build_object_query(read.model, workspace_key=read.workspace_key, **options)
    else:
        query = build_snapshot_object_query(read.model, read.context, **options)
    return paginate_statement(
        read.session,
        query.statement,
        keys=query.keys,
        scope="relation-matrix-columns",
        filters=read.filters(),
        page=PageRequest(cursor=cursor),
        page_size=page_size,
        message="Relation matrix column cursor is invalid",
        rows=read.context is not None,
        overlay=query.overlay,
    )


def _field_values(
    read: MatrixRead, records: Sequence[Any], fields: Sequence[str]
) -> dict[str, dict[str, Any]]:
    """The named fields of live records or change set and publication rows, typed as record reads
    return them: built-in fields, ``path``, ``ancestor:<type>`` and attribute values."""
    ids = [_record_id(item) for item in records]
    attributes = [
        field for field in fields if read.model.attribute_type(field) is not None
    ]
    values: dict[str, dict[str, Any]] = {key: {} for key in ids}
    if attributes and ids:
        if read.context is None:
            for row in read.session.execute(
                select(
                    AttributeValue.object_id,
                    AttributeValue.attribute_type_key,
                    AttributeValue.value_type,
                    *(getattr(AttributeValue, name) for name in set(VALUE_COLUMNS.values())),
                ).where(
                    AttributeValue.object_id.in_(ids),
                    AttributeValue.attribute_type_key.in_(attributes),
                )
            ):
                values[row.object_id][row.attribute_type_key] = stored_json_value(
                    getattr(row, VALUE_COLUMNS[row.value_type])
                )
        else:
            for item in records:
                values[item.object_id] = dict(item.attributes or {})
    needs_path = any(field == "path" or field.startswith("ancestor:") for field in fields)
    paths: dict[str, list[dict[str, Any]]] = {}
    if needs_path and records:
        paths = (
            _object_paths(read.session, list(records))
            if read.context is None
            else object_paths(read.session, read.context, records)
        )
    result = {}
    for item, key in zip(records, ids, strict=True):
        path = paths.get(key, [])
        live = read.context is None
        builtins = {
            "id": key,
            "name": item.name,
            "objectType": read.model.object_type(item.object_type_key).name,
            "createdAt": item.created_at if live else None,
            "updatedAt": item.updated_at if live else None,
            "path": " / ".join(part["name"] for part in path),
        }
        fields_of = {}
        for field in fields:
            if field in builtins:
                fields_of[field] = builtins[field]
            elif field.startswith("ancestor:"):
                ancestor_type = field.removeprefix("ancestor:")
                fields_of[field] = next(
                    (part["name"] for part in path[:-1] if part["objectTypeKey"] == ancestor_type),
                    None,
                )
            else:
                fields_of[field] = values[key].get(field)
        result[key] = fields_of
    return result


def _rows(
    read: MatrixRead, rows: Sequence[Any], row_ids: list[str], column_ids: list[str]
) -> list[RelationMatrixRow]:
    row_fields = _field_values(read, rows, read.config.rowColumns)
    current = _cells(read, row_ids, column_ids) if row_ids and column_ids else {}
    history = _history_cells(read, row_ids, column_ids) if row_ids and column_ids else {}
    set_versions = _set_versions(read, row_ids)
    cell_values = _cell_values(read, [*current.values(), *history.values()])
    result = []
    for row, key in zip(rows, row_ids, strict=True):
        cells = []
        for column_id in column_ids:
            held = current.get((key, column_id))
            evidence = history.get((key, column_id))
            publication = None
            if held is not None:
                records = held
                matching = records[0].matching_count
                if matching == 1:
                    state = "one"
                elif matching > 1:
                    state = "several"
                else:
                    state = "inactive"
            elif evidence is not None:
                records, state = evidence, "historyOnly"
                publication = RelationMatrixPublicationReference(
                    id=evidence[0].publication_id, number=evidence[0].publication_number
                )
            else:
                records, state = [], "none"
            cells.append(
                RelationMatrixCell(
                    columnId=column_id,
                    state=state,
                    conflict=state == "several" and read.conflict_scope,
                    recordCount=records[0].record_count if records else 0,
                    matchingCount=records[0].matching_count if records else 0,
                    records=[
                        RelationMatrixCellRecord(
                            id=record.cell_id,
                            name=record.name,
                            version=record.version,
                            relationId=record.relation_id,
                            relationVersion=record.relation_version,
                            meetsCondition=bool(record.meets),
                            fields={
                                field: cell_values.get((record.owner, record.cell_id), {}).get(field)
                                for field in read.config.cellFields
                            },
                        )
                        for record in records
                    ],
                    publication=publication,
                )
            )
        result.append(
            RelationMatrixRow(
                row=RelationMatrixRecord(
                    id=key,
                    objectTypeKey=row.object_type_key,
                    name=row.name,
                    fields=row_fields[key],
                ),
                relationSetVersion=set_versions.get(key, 0),
                cells=cells,
            )
        )
    return result


def _ranked(cells: Any, resolved: Any, column_ids: list[str]) -> Select[Any]:
    """Each cell's records, those meeting the condition first, at most ``CELL_RECORD_LIMIT`` per
    cell, with the cell's counts on every row."""
    partition = (cells.c.row_id, resolved.c.column_id)
    ranked = (
        select(
            *cells.c,
            resolved.c.column_id,
            func.count().over(partition_by=partition).label("record_count"),
            func.sum(cells.c.meets).over(partition_by=partition).label("matching_count"),
            func.row_number()
            .over(partition_by=partition, order_by=(cells.c.meets.desc(), cells.c.name, cells.c.cell_id))
            .label("rank"),
        )
        .select_from(cells)
        .join(resolved, resolved.c.cell_id == cells.c.cell_id)
        .where(resolved.c.column_id.in_(column_ids))
        .subquery("matrix_ranked")
    )
    return (
        select(ranked)
        .where(ranked.c.rank <= CELL_RECORD_LIMIT)
        .order_by(ranked.c.row_id, ranked.c.column_id, ranked.c.rank)
    )


def _cells(read: MatrixRead, row_ids: list[str], column_ids: list[str]) -> dict[tuple[str, str], list[Any]]:
    """The page's cells in one statement: relations, related records and the walk to columns."""
    cells = cell_records(read, row_ids)
    result: dict[tuple[str, str], list[Any]] = {}
    for row in read.session.execute(_ranked(cells, cell_columns(read, cells), column_ids)):
        result.setdefault((row.row_id, row.column_id), []).append(row)
    return result


def _history_cells(
    read: MatrixRead, row_ids: list[str], column_ids: list[str]
) -> dict[tuple[str, str], list[Any]]:
    """Per cell, the records of the latest earlier publication that held any, in one statement."""
    config = read.config
    publications = read.publications()
    relation = aliased(PublicationRelation)
    record = aliased(PublicationObject)
    cells = (
        select(
            relation.publication_id.label("publication_id"),
            publications.c.publication_number.label("publication_number"),
            relation.relation_id.label("relation_id"),
            relation.version.label("relation_version"),
            getattr(relation, read.anchor_end).label("row_id"),
            getattr(relation, read.other_end).label("cell_id"),
            record.name.label("name"),
            record.version.label("version"),
            record.parent_object_id.label("parent_object_id"),
            relation.publication_id.label("owner"),
            read.meets(record.object_id, relation.publication_id, publication=True).label("meets"),
        )
        .select_from(relation)
        .join(publications, publications.c.id == relation.publication_id)
        .join(
            record,
            and_(
                record.publication_id == relation.publication_id,
                record.object_id == getattr(relation, read.other_end),
                record.object_type_key == config.cellObjectTypeKey,
            ),
        )
        .where(
            relation.relation_type_key == config.relationTypeKey,
            getattr(relation, read.anchor_end).in_(row_ids),
        )
        .cte("matrix_history_cells")
        .prefix_with("MATERIALIZED")
    )

    def lookup(publication_id: Any, object_id: Any, name: str) -> Any:
        found = aliased(PublicationObject)
        return (
            select(getattr(found, name))
            .where(found.publication_id == publication_id, found.object_id == object_id)
            .correlate_except(found)
            .scalar_subquery()
        )

    walk = (
        select(
            cells.c.publication_id,
            cells.c.cell_id,
            cells.c.parent_object_id.label("node"),
            literal(1).label("depth"),
        )
        .where(cells.c.parent_object_id.is_not(None))
        .distinct()
        .cte("matrix_history_walk", recursive=True)
    )
    walk = walk.union_all(
        select(
            walk.c.publication_id,
            walk.c.cell_id,
            lookup(walk.c.publication_id, walk.c.node, "parent_object_id"),
            walk.c.depth + 1,
        ).where(
            walk.c.node.is_not(None),
            lookup(walk.c.publication_id, walk.c.node, "object_type_key") != config.columnObjectTypeKey,
            walk.c.depth < MAX_DEPTH,
        )
    )
    resolved = (
        select(walk.c.publication_id, walk.c.cell_id, walk.c.node.label("column_id"))
        .where(
            lookup(walk.c.publication_id, walk.c.node, "object_type_key") == config.columnObjectTypeKey
        )
        .subquery("matrix_history_columns")
    )
    # The same record in several publications resolves once per publication.
    resolved_on = and_(
        resolved.c.cell_id == cells.c.cell_id, resolved.c.publication_id == cells.c.publication_id
    )
    partition = (cells.c.row_id, resolved.c.column_id, cells.c.publication_id)
    latest = (
        func.max(cells.c.publication_number)
        .over(partition_by=(cells.c.row_id, resolved.c.column_id))
        .label("latest")
    )
    ranked = (
        select(
            *cells.c,
            resolved.c.column_id,
            func.count().over(partition_by=partition).label("record_count"),
            func.sum(cells.c.meets).over(partition_by=partition).label("matching_count"),
            func.row_number()
            .over(partition_by=partition, order_by=(cells.c.meets.desc(), cells.c.name, cells.c.cell_id))
            .label("rank"),
            latest,
        )
        .select_from(cells)
        .join(resolved, resolved_on)
        .where(resolved.c.column_id.in_(column_ids))
        .subquery("matrix_history_ranked")
    )
    statement = (
        select(ranked)
        .where(ranked.c.rank <= CELL_RECORD_LIMIT, ranked.c.publication_number == ranked.c.latest)
        .order_by(ranked.c.row_id, ranked.c.column_id, ranked.c.rank)
    )
    result: dict[tuple[str, str], list[Any]] = {}
    for row in read.session.execute(statement):
        result.setdefault((row.row_id, row.column_id), []).append(row)
    return result


def _cell_values(read: MatrixRead, cells: Sequence[list[Any]]) -> dict[tuple[str | None, str], dict[str, Any]]:
    """The ``cellFields`` of every listed cell record, keyed by (values owner, record).

    Live records read ``attribute_values``; change set and publication rows, history evidence
    included, read their typed index. One statement serves both, whatever the page holds.
    """
    records = [record for cell in cells for record in cell]
    fields = list(read.config.cellFields)
    live = sorted({record.cell_id for record in records if record.owner is None})
    snapshot: dict[str, set[str]] = {}
    for record in records:
        if record.owner is not None:
            snapshot.setdefault(record.owner, set()).add(record.cell_id)
    typed = sorted(set(VALUE_COLUMNS.values()))
    value = SnapshotAttributeValue
    owned = [
        and_(value.owner_id == owner, value.object_id.in_(sorted(ids)))
        for owner, ids in sorted(snapshot.items())
    ]
    statement = union_all(
        select(
            literal(None, String).label("owner_id"),
            AttributeValue.object_id,
            AttributeValue.attribute_type_key,
            AttributeValue.value_type,
            *(getattr(AttributeValue, name) for name in typed),
        ).where(AttributeValue.object_id.in_(live), AttributeValue.attribute_type_key.in_(fields)),
        select(
            value.owner_id,
            value.object_id,
            value.attribute_type_key,
            value.value_type,
            *(getattr(value, name) for name in typed),
        ).where(or_(false(), *owned), value.attribute_type_key.in_(fields)),
    )
    result: dict[tuple[str | None, str], dict[str, Any]] = {}
    for row in read.session.execute(statement):
        result.setdefault((row.owner_id, row.object_id), {})[row.attribute_type_key] = (
            stored_json_value(getattr(row, VALUE_COLUMNS[row.value_type]))
        )
    return result


def _set_versions(read: MatrixRead, row_ids: list[str]) -> dict[str, int]:
    if not row_ids or (read.context is not None and read.context.kind == "publication"):
        return {}
    config = read.config
    from_key, to_key = (
        (config.rowObjectTypeKey, config.cellObjectTypeKey)
        if read.outgoing
        else (config.cellObjectTypeKey, config.rowObjectTypeKey)
    )
    return dict(
        read.session.execute(
            select(RelationSetVersion.anchor_object_id, RelationSetVersion.version).where(
                RelationSetVersion.workspace_key == read.workspace_key,
                RelationSetVersion.change_set_id == (read.context.id if read.context else None),
                RelationSetVersion.relation_type_key == config.relationTypeKey,
                RelationSetVersion.from_object_type_key == from_key,
                RelationSetVersion.to_object_type_key == to_key,
                RelationSetVersion.direction == config.direction,
                RelationSetVersion.anchor_object_id.in_(row_ids),
            )
        ).all()
    )


def _state_filter(read: MatrixRead, column_ids: list[str], state: str) -> Callable[[Any], Any]:
    """A predicate on a row's ID: some selected column's cell has ``state``, over every row.

    Stored cell states decide it once for the request (A3b): the matching row IDs are read by
    index and every paging statement filters by that list. Where an owner the read needs has no
    stored states, the cells are derived from records in each statement instead (D12).
    """
    stored = stored_row_filter(read, column_ids, state, read.publication_number)
    if stored is not None:
        ids, negated = stored
        return lambda row_id: ~listed(read.session, row_id, ids) if negated else listed(read.session, row_id, ids)
    pairs = _current_pairs(read, column_ids)
    if state in {"one", "several", "inactive"}:
        matching = func.sum(pairs.c.meets)
        having = {"one": matching == 1, "several": matching > 1, "inactive": matching == 0}[state]
        rows = select(pairs.c.row_id).group_by(pairs.c.row_id, pairs.c.column_id).having(having)
        return lambda row_id: row_id.in_(rows)
    history = _history_pairs(read, column_ids)

    def predicate(row_id: Any) -> Any:
        clauses = []
        for column_id in column_ids:
            present = row_id.in_(select(pairs.c.row_id).where(pairs.c.column_id == column_id))
            held = row_id.in_(select(history.c.row_id).where(history.c.column_id == column_id))
            clauses.append(and_(~present, held if state == "historyOnly" else ~held))
        return or_(*clauses)

    return predicate


def _column_anchor(column_ids: list[str]) -> Any:
    """The selected column IDs as rows."""
    selected = id_rows(column_ids, "matrix_selected_columns")
    return select(selected.c.id.label("column_id")).subquery("matrix_selected")


def _current_pairs(read: MatrixRead, column_ids: list[str]) -> Any:
    """(row, column, meets) for every cell record under the selected columns, in the context."""
    config = read.config
    selected = _column_anchor(column_ids)
    walk = select(
        selected.c.column_id.label("node"),
        selected.c.column_id,
        literal(config.columnObjectTypeKey, String).label("object_type_key"),
        literal(None, String).label("owner"),
        literal(0).label("depth"),
    ).cte("matrix_down", recursive=True)
    steps = []
    for arm in read.object_arms():
        child = aliased(arm.entity)
        steps.append(
            select(
                getattr(child, arm.id),
                walk.c.column_id,
                child.object_type_key,
                arm.owner if arm.owner is not None else literal(None, String),
                walk.c.depth + 1,
            )
            .select_from(walk)
            .outerjoin(
                child,
                and_(
                    child.parent_object_id == walk.c.node,
                    _unindexed(child.object_type_key.in_(read.walk_types())),
                    *arm.where(child),
                ),
            )
            .where(_found(getattr(child, arm.id)), walk.c.depth < MAX_DEPTH)
        )
    walk = walk.union_all(*steps)
    cells = (
        select(walk.c.node.label("cell_id"), walk.c.column_id, walk.c.owner)
        .where(walk.c.object_type_key == config.cellObjectTypeKey)
        .subquery("matrix_down_cells")
    )
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


def _history_pairs(read: MatrixRead, column_ids: list[str]) -> Any:
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
        .outerjoin(
            child,
            and_(
                child.publication_id == walk.c.publication_id,
                child.parent_object_id == walk.c.node,
                _unindexed(child.object_type_key.in_(read.walk_types())),
            ),
        )
        .where(_found(child.object_id), walk.c.depth < MAX_DEPTH)
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
        .cte("matrix_history_pairs")
    )


# Writes from a cell (A3). A cell writes through the generic object and relation APIs; these reads
# supply what it needs without asking the user again for what the row and column already say.


def matrix_containers(
    read: MatrixRead,
    *,
    column_id: str,
    search: str | None,
    page: PageRequest,
    page_size: int,
) -> RelationMatrixContainerPage:
    """The column record and the records under it that can directly hold a new cell record, in
    path order; the column's only container is its default (D13)."""
    _require_action(read, "create")
    column = _named_columns(read, [column_id])[0]
    walk = _walk_below(read, column, sorted(read.container_types()))
    direct = sorted(parent_type_keys(read.model, read.config.cellObjectTypeKey))
    statement = select(walk.c.object_id, walk.c.object_type_key, walk.c.name, walk.c.sort_path).where(
        walk.c.object_type_key.in_(direct)
    )
    first_two = list(read.session.scalars(statement.with_only_columns(walk.c.object_id).limit(2)))
    if search:
        statement = statement.where(func.lower(walk.c.name).contains(search.lower(), autoescape=True))
    found = paginate_statement(
        read.session,
        statement,
        keys=[
            text_key("path", walk.c.sort_path, "sort_path"),
            text_key("id", walk.c.object_id, "object_id"),
        ],
        scope="relation-matrix-containers",
        filters={**read.filters(), "columnId": column_id, "search": search},
        page=page,
        page_size=page_size,
        message="Relation matrix container cursor is invalid",
        rows=True,
    )
    paths = _paths_below(read, [item.object_id for item in found.items], column_id)
    return RelationMatrixContainerPage(
        items=[
            RelationMatrixContainer(
                id=item.object_id,
                objectTypeKey=item.object_type_key,
                name=item.name,
                path=paths.get(item.object_id, []),
            )
            for item in found.items
        ],
        **found.links(),
        defaultContainerId=first_two[0] if len(first_two) == 1 else None,
    )


def matrix_link_candidates(
    read: MatrixRead,
    *,
    row_id: str,
    column_id: str,
    search: str | None,
    page: PageRequest,
    page_size: int,
) -> RelationMatrixLinkCandidatePage:
    """Cell-type records under the column record in name order, each marked eligible or with the
    reason a link from the row would be refused. Ineligible ones are listed so totals stay true."""
    _require_action(read, "link")
    if _object_types(read, [row_id]).get(row_id) != read.config.rowObjectTypeKey:
        raise api_error(
            404,
            "relation_matrix_row_not_found",
            f"Rows must be '{read.config.rowObjectTypeKey}' records in the selected context",
            {"rowId": row_id, "rowObjectTypeKey": read.config.rowObjectTypeKey},
        )
    column = _named_columns(read, [column_id])[0]
    walk = _walk_below(read, column, read.walk_types())
    meets = read.meets(walk.c.object_id, walk.c.owner) if read.conflict_scope else literal(1)
    statement = select(
        walk.c.object_id,
        walk.c.object_type_key,
        walk.c.name,
        walk.c.version,
        walk.c.owner,
        meets.label("meets"),
    ).where(walk.c.object_type_key == read.config.cellObjectTypeKey)
    if search:
        statement = statement.where(func.lower(walk.c.name).contains(search.lower(), autoescape=True))
    found = paginate_statement(
        read.session,
        statement,
        keys=[text_key("name", walk.c.name, "name"), text_key("id", walk.c.object_id, "object_id")],
        scope="relation-matrix-link-candidates",
        filters={**read.filters(), "rowId": row_id, "columnId": column_id, "search": search},
        page=page,
        page_size=page_size,
        message="Relation matrix candidate cursor is invalid",
        rows=True,
    )
    items = found.items
    ids = [item.object_id for item in items]
    paths = _paths_below(read, ids, column_id)
    values = _cell_values(
        read, [[SimpleNamespace(cell_id=item.object_id, owner=item.owner) for item in items]]
    )
    refusals = _link_refusals(read, row_id, column_id, items) if items else {}
    return RelationMatrixLinkCandidatePage(
        items=[
            RelationMatrixLinkCandidate(
                id=item.object_id,
                objectTypeKey=item.object_type_key,
                name=item.name,
                version=item.version,
                path=paths.get(item.object_id, []),
                fields={
                    field: values.get((item.owner, item.object_id), {}).get(field)
                    for field in read.config.cellFields
                },
                eligible=refusals.get(item.object_id) is None,
                reason=refusals.get(item.object_id),
            )
            for item in items
        ],
        **found.links(),
        relationSetVersion=_set_versions(read, [row_id]).get(row_id, 0),
    )


def _require_action(read: MatrixRead, action: str) -> None:
    if action not in read.config.cellActions:
        raise api_error(
            422,
            "relation_matrix_action_not_allowed",
            f"The view does not offer '{action}' in its cells",
            {"viewKey": read.view_key, "action": action},
        )


def _walk_below(read: MatrixRead, column: Any, types: Sequence[str]) -> Any:
    """The column record and the records of ``types`` under it, in the read's context, each with
    a sort path of lower-cased names from below the column record."""
    walk = select(
        literal(_record_id(column), String).label("object_id"),
        literal(read.config.columnObjectTypeKey, String).label("object_type_key"),
        literal(column.name, String).label("name"),
        literal(column.version).label("version"),
        literal(None, String).label("owner"),
        literal("", String).label("sort_path"),
        literal(0).label("depth"),
    ).cte("matrix_below", recursive=True)
    steps = []
    for arm in read.object_arms():
        child = aliased(arm.entity)
        steps.append(
            select(
                getattr(child, arm.id),
                child.object_type_key,
                child.name,
                child.version,
                arm.owner if arm.owner is not None else literal(None, String),
                walk.c.sort_path + func.lower(child.name) + literal(_PATH_SEPARATOR, String),
                walk.c.depth + 1,
            )
            .select_from(walk)
            .outerjoin(
                child,
                and_(
                    child.parent_object_id == walk.c.object_id,
                    _unindexed(child.object_type_key.in_(types)),
                    *arm.where(child),
                ),
            )
            .where(_found(getattr(child, arm.id)), walk.c.depth < MAX_DEPTH)
        )
    return walk.union_all(*steps)


def _paths_below(
    read: MatrixRead, ids: Sequence[str], column_id: str
) -> dict[str, list[RelationMatrixPathPart]]:
    """Each record's path from below the column record down to the record itself."""
    if not ids:
        return {}
    if read.context is None:
        records = list(read.session.scalars(select(RdmObject).where(RdmObject.id.in_(list(ids)))))
        paths = _object_paths(read.session, records)
    else:
        paths = object_paths(
            read.session, read.context, find_objects(read.session, read.context, ids).values()
        )
    result = {}
    for key, path in paths.items():
        parts = [part["id"] for part in path]
        start = parts.index(column_id) + 1 if column_id in parts else 0
        result[key] = [RelationMatrixPathPart(**part) for part in path[start:]]
    return result


def _link_refusals(
    read: MatrixRead, row_id: str, column_id: str, candidates: Sequence[Any]
) -> dict[str, str | None]:
    """Why a link from the row to each candidate would be refused, or ``None``.

    Mirrors the relation writes: cardinality counts relations of the binding's relation type at an
    end, whatever the other end's type. The uniqueness scope is checked when it is the column; a
    scope of another type is left to the write.
    """
    config = read.config
    ends = [row_id, *(item.object_id for item in candidates)]
    parts = []
    for arm in read.relation_arms():
        relation = aliased(arm.entity)
        parts.append(
            select(relation.from_object_id, relation.to_object_id).where(
                relation.relation_type_key == config.relationTypeKey,
                or_(relation.from_object_id.in_(ends), relation.to_object_id.in_(ends)),
                *arm.where(relation),
            )
        )
    edges = read.session.execute(union_all(*parts) if len(parts) > 1 else parts[0]).all()
    pairs = {(edge.from_object_id, edge.to_object_id) for edge in edges}
    sources = {edge.from_object_id for edge in edges}
    targets = {edge.to_object_id for edge in edges}
    cardinality = read.binding.cardinality
    scope_taken = False
    if read.conflict_scope:
        held = _cells(read, [row_id], [column_id]).get((row_id, column_id))
        scope_taken = bool(held and held[0].matching_count)
    result: dict[str, str | None] = {}
    for item in candidates:
        from_id, to_id = (row_id, item.object_id) if read.outgoing else (item.object_id, row_id)
        taken = set()
        if cardinality == "one-to-one" and from_id in sources:
            taken.add(from_id)
        if cardinality in {"one-to-one", "one-to-many"} and to_id in targets:
            taken.add(to_id)
        if (from_id, to_id) in pairs:
            reason = "alreadyLinked"
        elif row_id in taken:
            reason = "rowCardinality"
        elif taken:
            reason = "candidateCardinality"
        elif scope_taken and item.meets:
            reason = "scopeTaken"
        else:
            reason = None
        result[item.object_id] = reason
    return result
