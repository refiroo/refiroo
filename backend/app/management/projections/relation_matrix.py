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

The walks join rows by keyed lookups on each context's tables. A change set's downward walk joins
its base's rows and its own as one selectable in its one recursive term.
"""

from collections.abc import Sequence
from types import SimpleNamespace
from typing import Any

from sqlalchemy import (
    Select,
    String,
    and_,
    case,
    false,
    func,
    literal,
    or_,
    select,
    union_all,
)
from sqlalchemy.orm import Session, aliased

from ...common.pagination import Page, PageRequest, paginate_statement, text_key
from ...db import begin_snapshot_read
from ...engine.model.candidate_places import choose_container
from ...engine.model.registry import resolve_request_model
from ...engine.reads.matrix_cells import (
    MAX_DEPTH,
    cell_columns,
    cell_records,
)
from ...engine.reads.matrix_read import (
    MatrixRead,
    build_matrix_read,
    column_application,
    column_query,
    container_applications,
    container_cell_counts,
    container_rows,
    derived_place,
    named_columns,
    object_types,
    proposed_place,
    record_id,
    state_filter,
    walk_below,
)
from ...engine.reads.model_query import candidate_ids
from ...engine.reads.object_query import build_object_query, live_object_paths
from ...engine.reads.snapshot_reads import (
    build_snapshot_object_query,
    find_objects,
    object_paths,
)
from ...engine.records.rules import get_application
from ...engine.records.values import VALUE_COLUMNS, stored_json_value
from ...engine.workspaces.catalogue import resolve_workspace
from ...errors import api_error
from ...models.database import (
    AttributeValue,
    PublicationObject,
    PublicationRelation,
    RdmObject,
    RelationSetVersion,
    SnapshotAttributeValue,
)
from ...models.schema import (
    RelationMatrixViewDefinition,
)
from ..schemas.relation_matrix import (
    RelationMatrixCell,
    RelationMatrixCellRecord,
    RelationMatrixColumn,
    RelationMatrixContainer,
    RelationMatrixContainerPage,
    RelationMatrixDerivedPlace,
    RelationMatrixLinkCandidate,
    RelationMatrixLinkCandidatePage,
    RelationMatrixPage,
    RelationMatrixPathPart,
    RelationMatrixPublicationReference,
    RelationMatrixRecord,
    RelationMatrixRow,
)

CELL_RECORD_LIMIT = 5

STATES = ("one", "several", "inactive", "historyOnly", "none")


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
    # An unknown application is named as on every other route (H4c, deviation 2).
    application = get_application(snapshot.model, application_key)
    view = next((item for item in application.views if item.key == view_key), None)
    if not isinstance(view, RelationMatrixViewDefinition):
        raise api_error(
            404,
            "RELATION_MATRIX_VIEW_NOT_FOUND",
            "Relation matrix view not found in the selected model",
            {"applicationKey": application_key, "viewKey": view_key},
        )
    return build_matrix_read(
        session, workspace.key, snapshot, view, application_key, change_set_id, publication_id
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
    hide_empty_columns: bool = False,
) -> RelationMatrixPage:
    if column_ids is not None and column_cursor is not None:
        raise api_error(
            422,
            "CONFLICTING_COLUMN_PARAMETERS",
            "Name the columns with columnIds or page them with columnCursor, not both",
            {"parameters": ["columnIds", "columnCursor"]},
        )
    if state is not None and not column_ids:
        raise api_error(
            422,
            "RELATION_MATRIX_STATE_REQUIRES_COLUMNS",
            "A state filter applies to the columns named by columnIds",
            {"path": "/query/columnIds"},
        )
    _validate_parent_scope(read, parent_object_id)
    empty_hidden: int | None = None
    if column_ids:
        columns = named_columns(read, column_ids)
        column_page: Page[Any] | None = None
    else:
        # Columns with no cell under any row the search and parent scope leave are left out of the column
        # pages themselves, so every page is full and its cursors are exact (0.13 LB-D8); naming
        # columns wins over it.
        nonempty = (
            _non_empty_columns(read, parent_object_id, search) if hide_empty_columns else None
        )
        column_page = _column_page(
            read, column_cursor, column_page_size, nonempty, (parent_object_id, search)
        )
        columns = column_page.items
        if nonempty is not None:
            empty_hidden = _empty_column_count(read, nonempty)
    selected = [record_id(item) for item in columns]

    id_filter = state_filter(read, selected, state) if state is not None else None
    options = {
        "object_type_key": read.config.rowObjectTypeKey,
        "application_key": None,
        "parent_object_id": parent_object_id,
        "search": search,
        "sort": sort,
        "field_filters": [],
        "search_fields": read.config.searchFields,
        "id_filter": id_filter,
        "session": read.session,
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
        parts=query.parts,
    )
    rows = row_page.items
    row_ids = [record_id(item) for item in rows]
    items = _rows(read, rows, row_ids, selected)
    column_labels = _field_values(read, columns, (read.config.columnLabelField,))
    return RelationMatrixPage(
        items=items,
        **row_page.links(),
        columns=[
            RelationMatrixColumn(
                id=record_id(item),
                name=item.name,
                label=column_labels[record_id(item)][read.config.columnLabelField],
            )
            for item in columns
        ],
        columnsNextCursor=column_page.next_cursor if column_page else None,
        columnsPrevCursor=column_page.prev_cursor if column_page else None,
        emptyColumnsHidden=empty_hidden,
    )


def _validate_parent_scope(read: MatrixRead, parent_object_id: str | None) -> None:
    if parent_object_id is None:
        return
    parent_type = object_types(read, [parent_object_id]).get(parent_object_id)
    if parent_type is None:
        raise api_error(
            404,
            "RELATION_MATRIX_PARENT_NOT_FOUND",
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
            "RELATION_MATRIX_PARENT_SCOPE_MISMATCH",
            f"A '{parent_type}' record cannot contain the matrix's '{row_type.key}' rows",
            {"parentObjectId": parent_object_id, "parentObjectTypeKey": parent_type},
        )


def _column_page(
    read: MatrixRead,
    cursor: str | None,
    page_size: int,
    nonempty: Select[Any] | None = None,
    scope: tuple[str | None, str | None] = (None, None),
) -> Page[Any]:
    query = column_query(read, (lambda key: key.in_(nonempty)) if nonempty is not None else None)
    filters = read.filters()
    if nonempty is not None:
        # What is empty depends on the rows the scope leaves, so a cursor belongs to that scope.
        filters = {**filters, "hideEmptyColumns": list(scope)}
    return paginate_statement(
        read.session,
        query.statement,
        keys=query.keys,
        scope="relation-matrix-columns",
        filters=filters,
        page=PageRequest(cursor=cursor),
        page_size=page_size,
        message="Relation matrix column cursor is invalid",
        rows=read.context is not None,
        overlay=query.overlay,
    )


def _non_empty_columns(
    read: MatrixRead, parent_object_id: str | None, search: str | None
) -> Select[Any]:
    """The column records with a cell record under them in some row the search and parent scope
    leave, one aggregate statement over every such row: the binding's relations walked up to their
    column records, as a cell's own read does."""
    cells = cell_columns(read, cell_records(read, None, rows_of_type=True))
    statement = select(cells.c.column_id).distinct()
    if parent_object_id is not None or search:
        options = {
            "object_type_key": read.config.rowObjectTypeKey,
            "application_key": None,
            "parent_object_id": parent_object_id,
            "search": search,
            "sort": None,
            "field_filters": [],
            "search_fields": read.config.searchFields,
        }
        if read.context is None:
            rows = build_object_query(
                read.model, workspace_key=read.workspace_key, session=read.session, **options
            )
            ids = rows.statement.order_by(None).subquery().c.id
        else:
            rows = build_snapshot_object_query(
                read.model, read.context, session=read.session, **options
            )
            ids = rows.statement.order_by(None).subquery().c.object_id
        statement = statement.where(cells.c.row_id.in_(select(ids)))
    return statement


def _empty_column_count(read: MatrixRead, nonempty: Select[Any]) -> int:
    """How many column records the context holds that ``nonempty`` leaves out."""
    column = column_query(read, lambda key: ~key.in_(nonempty))
    return (
        read.session.scalar(
            select(func.count()).select_from(column.statement.order_by(None).subquery())
        )
        or 0
    )


def _field_values(
    read: MatrixRead, records: Sequence[Any], fields: Sequence[str]
) -> dict[str, dict[str, Any]]:
    """The named fields of live records or change set and publication rows, typed as record reads
    return them: built-in fields, ``path``, ``ancestor:<type>`` and attribute values."""
    ids = [record_id(item) for item in records]
    attributes = [field for field in fields if read.model.attribute_type(field) is not None]
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
            live_object_paths(read.session, list(records))
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
                            relationAttributes=record.relation_attributes or {},
                            meetsCondition=bool(record.meets),
                            fields={
                                field: cell_values.get((record.owner, record.cell_id), {}).get(
                                    field
                                )
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


def _ranked(cells: Any, column_ids: list[str]) -> Select[Any]:
    """Each cell's records (``cells`` with their ``column_id``), those meeting the condition first,
    at most ``CELL_RECORD_LIMIT`` per cell, with the cell's counts on every row."""
    partition = (cells.c.row_id, cells.c.column_id)
    ranked = (
        select(
            *cells.c,
            func.count().over(partition_by=partition).label("record_count"),
            func.sum(cells.c.meets).over(partition_by=partition).label("matching_count"),
            func.row_number()
            .over(
                partition_by=partition,
                order_by=(cells.c.meets.desc(), cells.c.name, cells.c.cell_id),
            )
            .label("rank"),
        )
        .where(cells.c.column_id.in_(column_ids))
        .subquery("matrix_ranked")
    )
    return (
        select(ranked)
        .where(ranked.c.rank <= CELL_RECORD_LIMIT)
        .order_by(ranked.c.row_id, ranked.c.column_id, ranked.c.rank)
    )


def _cells(
    read: MatrixRead, row_ids: list[str], column_ids: list[str]
) -> dict[tuple[str, str], list[Any]]:
    """The page's cells in one statement: relations, related records and the walk to columns."""
    cells = cell_columns(read, cell_records(read, row_ids, relation_attributes=True))
    result: dict[tuple[str, str], list[Any]] = {}
    for row in read.session.execute(_ranked(cells, column_ids)):
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
            relation.attributes.label("relation_attributes"),
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
    )

    def lookup(publication_id: Any, object_id: Any, name: str) -> Any:
        found = aliased(PublicationObject)
        return (
            select(getattr(found, name))
            .where(found.publication_id == publication_id, found.object_id == object_id)
            .correlate_except(found)
            .scalar_subquery()
        )

    # The walk carries each record's columns, as ``cell_columns`` does, so nothing joins back.
    walk = (
        select(*cells.c, cells.c.parent_object_id.label("node"), literal(1).label("depth"))
        .where(cells.c.parent_object_id.is_not(None))
        .cte("matrix_history_walk", recursive=True)
    )
    walk = walk.union_all(
        select(
            *(walk.c[column.name] for column in cells.c),
            lookup(walk.c.publication_id, walk.c.node, "parent_object_id"),
            walk.c.depth + 1,
        ).where(
            walk.c.node.is_not(None),
            lookup(walk.c.publication_id, walk.c.node, "object_type_key")
            != config.columnObjectTypeKey,
            walk.c.depth < MAX_DEPTH,
        )
    )
    resolved = (
        select(*(walk.c[column.name] for column in cells.c), walk.c.node.label("column_id"))
        .where(
            lookup(walk.c.publication_id, walk.c.node, "object_type_key")
            == config.columnObjectTypeKey
        )
        .subquery("matrix_history_columns")
    )
    # The same record in several publications resolves once per publication.
    partition = (resolved.c.row_id, resolved.c.column_id, resolved.c.publication_id)
    latest = (
        func.max(resolved.c.publication_number)
        .over(partition_by=(resolved.c.row_id, resolved.c.column_id))
        .label("latest")
    )
    ranked = (
        select(
            *resolved.c,
            func.count().over(partition_by=partition).label("record_count"),
            func.sum(resolved.c.meets).over(partition_by=partition).label("matching_count"),
            func.row_number()
            .over(
                partition_by=partition,
                order_by=(resolved.c.meets.desc(), resolved.c.name, resolved.c.cell_id),
            )
            .label("rank"),
            latest,
        )
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


def _cell_values(
    read: MatrixRead, cells: Sequence[list[Any]]
) -> dict[tuple[str | None, str], dict[str, Any]]:
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
    path order; the default is the container that holds the view's cells, never an empty one (PP-D24)."""
    _require_action(read, "create")
    column = named_columns(read, [column_id])[0]
    base = container_rows(read, column).subquery("matrix_container_rows")
    everyone = list(read.session.scalars(select(base.c.object_id)))
    counts = container_cell_counts(read, everyone)
    place = derived_place(read)
    chosen = choose_container(everyone, counts, fixed=place is not None)
    # Neither the rules nor the data give a place: propose a new container (PP-D28).
    proposed = proposed_place(read, column) if place is None and chosen is None else None
    used = [key for key, number in counts.items() if number > 0]
    # Containers holding cells of the view first, then the others, each in path order.
    rank = case((base.c.object_id.in_(used), "0"), else_="1")
    statement = select(
        base.c.object_id,
        base.c.object_type_key,
        base.c.name,
        (rank + base.c.sort_path).label("sort_path"),
    )
    if search:
        statement = statement.where(
            func.lower(base.c.name).contains(search.lower(), autoescape=True)
        )
    found = paginate_statement(
        read.session,
        statement,
        keys=[
            text_key("path", statement.selected_columns["sort_path"], "sort_path"),
            text_key("id", statement.selected_columns["object_id"], "object_id"),
        ],
        scope="relation-matrix-containers",
        filters={**read.filters(), "columnId": column_id, "search": search},
        page=page,
        page_size=page_size,
        message="Relation matrix container cursor is invalid",
        rows=True,
    )
    paths = _paths_below(read, [item.object_id for item in found.items], column_id)
    applications = container_applications(read, [item.object_id for item in found.items])
    return RelationMatrixContainerPage(
        items=[
            RelationMatrixContainer(
                id=item.object_id,
                objectTypeKey=item.object_type_key,
                name=item.name,
                path=paths.get(item.object_id, []),
                cellCount=counts.get(item.object_id, 0),
                applicationKey=applications.get(item.object_id),
            )
            for item in found.items
        ],
        **found.links(),
        defaultContainerId=chosen,
        derivedPlace=(
            RelationMatrixDerivedPlace(
                objectTypeKey=place.object_type_key,
                name=place.name,
                attributes=place.attributes,
                willBeCreated=not everyone,
                applicationKey=column_application(read, column),
            )
            if place is not None
            else RelationMatrixDerivedPlace(
                objectTypeKey=proposed.object_type_key,
                name=proposed.name,
                attributes=proposed.attributes,
                willBeCreated=True,
                applicationKey=column_application(read, column),
                proposed=True,
            )
            if proposed is not None
            else None
        ),
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
    if object_types(read, [row_id]).get(row_id) != read.config.rowObjectTypeKey:
        raise api_error(
            404,
            "RELATION_MATRIX_ROW_NOT_FOUND",
            f"Rows must be '{read.config.rowObjectTypeKey}' records in the selected context",
            {"rowId": row_id, "rowObjectTypeKey": read.config.rowObjectTypeKey},
        )
    column = named_columns(read, [column_id])[0]
    walk = walk_below(read, column, read.walk_types())
    meets = read.meets(walk.c.object_id, walk.c.owner) if read.conflict_scope else literal(1)
    statement = select(
        walk.c.object_id,
        walk.c.object_type_key,
        walk.c.name,
        walk.c.version,
        walk.c.owner,
        meets.label("meets"),
    ).where(walk.c.object_type_key == read.config.cellObjectTypeKey)
    criteria = read.binding.candidates_at("to" if read.outgoing else "from")
    if criteria:
        # The binding's candidate criteria (0.9 K7, D171): only cells the model lets be chosen.
        cell_type = read.model.object_type(read.config.cellObjectTypeKey)
        assert cell_type is not None
        statement = statement.where(
            walk.c.object_id.in_(
                candidate_ids(
                    read.model,
                    cell_type,
                    criteria,
                    workspace_key=read.workspace_key,
                    context=read.context,
                )
            )
        )
    if search:
        statement = statement.where(
            func.lower(walk.c.name).contains(search.lower(), autoescape=True)
        )
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
            "RELATION_MATRIX_ACTION_NOT_ALLOWED",
            f"The view does not offer '{action}' in its cells",
            {"viewKey": read.view_key, "action": action},
        )


def _paths_below(
    read: MatrixRead, ids: Sequence[str], column_id: str
) -> dict[str, list[RelationMatrixPathPart]]:
    """Each record's path from below the column record down to the record itself."""
    if not ids:
        return {}
    if read.context is None:
        records = list(read.session.scalars(select(RdmObject).where(RdmObject.id.in_(list(ids)))))
        paths = live_object_paths(read.session, records)
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
    binding = read.binding
    scope_taken = False
    if read.conflict_scope:
        held = _cells(read, [row_id], [column_id]).get((row_id, column_id))
        scope_taken = bool(held and held[0].matching_count)
    result: dict[str, str | None] = {}
    for item in candidates:
        from_id, to_id = (row_id, item.object_id) if read.outgoing else (item.object_id, row_id)
        taken = set()
        if binding.holds_one("from") and from_id in sources:
            taken.add(from_id)
        if binding.holds_one("to") and to_id in targets:
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
