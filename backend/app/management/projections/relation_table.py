"""A relationships table's page of the workspace edge list (0.13 RV).

The engine reads the rows (``engine/reads/relation_table.py``); this adds what a row shows: both
end records with the view's columns, the relationship's version and its relation set's, and for a
grouped table how many rows each group on the page holds. ``relation_grid_page`` reads the grid layout
(``engine/reads/relation_grid.py``): each ``from`` record once, with its relationships to the shown
``to`` records.
"""

from collections.abc import Callable
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.sql.selectable import Subquery

from ...common.pagination import PageRequest, paginate_statement
from ...engine.reads.relation_grid import COLUMN_CAP, build_relation_grid_query, record_ids_selector
from ...engine.reads.relation_table import build_relation_table_query, group_counts
from ...errors import api_error
from ...models.database import ChangeSetRelation, RelationSetVersion
from ...models.schema import EngineModel, RelationTableViewConfig
from ..schemas.mapping import (
    MappingListPage,
    MappingListRow,
    MappingObjectSummary,
    RelationGridColumn,
    RelationGridPage,
    RelationGridRelation,
    RelationGridRow,
)

Summaries = Callable[[list[Any], tuple[str, ...]], dict[str, MappingObjectSummary]]


def relation_table_page(
    session: Session,
    model: EngineModel,
    config: RelationTableViewConfig,
    objects: Subquery,
    relations: Subquery,
    summaries: Summaries,
    *,
    workspace_key: str,
    change_set_id: str | None,
    publication_id: str | None,
    from_object_id: str | None,
    to_object_id: str | None,
    field_filters: list[tuple[str, str, str]],
    search: str | None,
    sort: str | None,
    scope: str,
    page: PageRequest,
    page_size: int | None,
) -> MappingListPage:
    query = build_relation_table_query(
        model,
        config,
        objects,
        relations,
        live=change_set_id is None and publication_id is None,
        from_object_id=from_object_id,
        to_object_id=to_object_id,
        field_filters=field_filters,
        search=search,
        sort=sort,
    )
    found = paginate_statement(
        session,
        query.statement,
        keys=query.keys,
        scope=scope,
        filters={
            **query.filters,
            "workspaceKey": workspace_key,
            "changeSetId": change_set_id,
            "publicationId": publication_id,
            "sort": sort,
        },
        page=page,
        page_size=page_size or config.pageSize,
        rows=True,
        seek=query.seek,
    )
    rows = found.items
    ids = list(dict.fromkeys(oid for row in rows for oid in (row.from_id, row.to_id)))
    records = (
        {row.id: row for row in session.execute(select(*objects.c).where(objects.c.id.in_(ids)))}
        if ids
        else {}
    )
    from_ends = summaries([records[row.from_id] for row in rows], config.fromColumns)
    to_ends = summaries([records[row.to_id] for row in rows], config.toColumns)
    versions = _set_versions(
        session, config, workspace_key, change_set_id, publication_id, {row.from_id for row in rows}
    )
    result = MappingListPage(
        items=[
            MappingListRow(
                relationId=row.relation_id,
                relationTypeKey=row.relation_type_key,
                direction="outgoing",
                source=from_ends[row.from_id],
                target=to_ends[row.to_id],
                attributes=row.relation_attributes or {},
                relationVersion=row.relation_version,
                mappingVersion=versions.get(row.from_id, 0),
            )
            for row in rows
        ],
        **found.links(),
    )
    if config.groupBy:
        group_ids = list(
            dict.fromkeys(row.from_id if config.groupBy == "from" else row.to_id for row in rows)
        )
        result.groupCounts = group_counts(query, session, group_ids)
    return result


def _set_versions(
    session: Session,
    config: RelationTableViewConfig,
    workspace_key: str,
    change_set_id: str | None,
    publication_id: str | None,
    anchors: set[str],
) -> dict[str, int]:
    """The version of each ``from`` record's set of this binding, as a mapping row carries it; a
    publication is immutable and carries 0."""
    if publication_id is not None or not anchors:
        return {}
    return {
        row.anchor_object_id: row.version
        for row in session.scalars(
            select(RelationSetVersion).where(
                RelationSetVersion.workspace_key == workspace_key,
                RelationSetVersion.change_set_id == change_set_id,
                RelationSetVersion.relation_type_key == config.relationTypeKey,
                RelationSetVersion.from_object_type_key == config.fromObjectTypeKey,
                RelationSetVersion.to_object_type_key == config.toObjectTypeKey,
                RelationSetVersion.direction == "outgoing",
                RelationSetVersion.anchor_object_id.in_(anchors),
            )
        )
    }


def relation_grid_page(
    session: Session,
    model: EngineModel,
    config: RelationTableViewConfig,
    objects: Subquery,
    relations: Subquery,
    summaries: Summaries,
    *,
    workspace_key: str,
    application_key: str,
    change_set_id: str | None,
    publication_id: str | None,
    to_object_ids: list[str],
    attributes: list[str] | None,
    field_filters: list[tuple[str, str, str]],
    search: str | None,
    to_search: str | None,
    sort: str | None,
    scope: str,
    page: PageRequest,
    page_size: int | None,
) -> RelationGridPage:
    """A page of the grid: the rows by the sort and the cursor, the column groups (at most
    ``COLUMN_CAP``) and each row's relationships to them, all in a fixed number of statements."""
    chosen = None if attributes is None else list(attributes)
    for key in chosen or ():
        if key not in config.attributeColumns:
            raise api_error(
                422,
                "INVALID_ATTRIBUTE",
                f"'{key}' is not one of the view's attributeColumns",
                {"path": "/query/attribute"},
            )
    query = build_relation_grid_query(
        model,
        config,
        objects,
        relations,
        live=change_set_id is None and publication_id is None,
        application_key=application_key,
        record_ids=record_ids_selector(
            session,
            model,
            workspace_key=workspace_key,
            change_set_id=change_set_id,
            publication_id=publication_id,
        ),
        to_object_ids=to_object_ids,
        field_filters=field_filters,
        search=search,
        to_search=to_search,
        sort=sort,
    )
    column_rows = list(session.execute(query.columns.limit(COLUMN_CAP)))
    column_total = session.scalar(query.column_total) or 0
    shown = [row.id for row in column_rows]
    rows = query.rows_for(shown)
    found = paginate_statement(
        session,
        rows.statement,
        keys=rows.keys,
        scope=scope,
        filters={
            **rows.filters,
            "workspaceKey": workspace_key,
            "changeSetId": change_set_id,
            "publicationId": publication_id,
        },
        page=page,
        page_size=page_size or config.pageSize,
        rows=True,
        seek=rows.seek,
    )
    page_ids = [row.from_id for row in found.items]
    records = (
        {
            row.id: row
            for row in session.execute(select(*objects.c).where(objects.c.id.in_(page_ids + shown)))
        }
        if page_ids or shown
        else {}
    )
    from_ends = summaries([records[oid] for oid in page_ids], config.fromColumns)
    to_ends = summaries([records[oid] for oid in shown], config.toColumns)
    linked = {row.to_id: row.rows for row in session.execute(rows.linked)}
    label_field = config.toColumns[0]
    relation_rows = (
        list(
            session.execute(
                select(
                    relations.c.id,
                    relations.c.version,
                    relations.c.attributes,
                    relations.c.from_object_id,
                    relations.c.to_object_id,
                ).where(
                    relations.c.relation_type_key == config.relationTypeKey,
                    relations.c.from_object_id.in_(page_ids),
                    relations.c.to_object_id.in_(shown),
                )
            )
        )
        if page_ids and shown
        else []
    )
    staged = (
        set(
            session.scalars(
                select(ChangeSetRelation.relation_id).where(
                    ChangeSetRelation.change_set_id == change_set_id,
                    ChangeSetRelation.is_deleted.is_(False),
                    ChangeSetRelation.relation_id.in_([row.id for row in relation_rows]),
                )
            )
        )
        if change_set_id and relation_rows
        else set()
    )
    by_row: dict[str, dict[str, RelationGridRelation]] = {oid: {} for oid in page_ids}
    for relation in relation_rows:
        values = relation.attributes or {}
        by_row[relation.from_object_id][relation.to_object_id] = RelationGridRelation(
            relationId=relation.id,
            version=relation.version,
            attributes=dict(values)
            if chosen is None
            else {key: values[key] for key in chosen if key in values},
            proposed=relation.id in staged,
        )
    versions = _set_versions(
        session, config, workspace_key, change_set_id, publication_id, set(page_ids)
    )
    return RelationGridPage(
        items=[
            RelationGridRow(
                source=from_ends[oid], mappingVersion=versions.get(oid, 0), relations=by_row[oid]
            )
            for oid in page_ids
        ],
        columns=[
            RelationGridColumn(
                id=row.id,
                objectTypeKey=config.toObjectTypeKey,
                name=row.name,
                label=str(to_ends[row.id].fields.get(label_field) or row.name),
                fields=to_ends[row.id].fields,
                linkedCount=linked.get(row.id, 0),
            )
            for row in column_rows
        ],
        columnTotal=column_total,
        rowTotal=session.scalar(rows.row_total) or 0,
        **found.links(),
    )
