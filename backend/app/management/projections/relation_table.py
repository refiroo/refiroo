"""A relationships table's page of the workspace edge list (0.13 RV).

The engine reads the rows (``engine/reads/relation_table.py``); this adds what a row shows: both
end records with the view's columns, the relationship's version and its relation set's, and for a
grouped table how many rows each group on the page holds.
"""

from collections.abc import Callable
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.sql.selectable import Subquery

from ...common.pagination import PageRequest, paginate_statement
from ...engine.reads.relation_table import build_relation_table_query, group_counts
from ...models.database import RelationSetVersion
from ...models.schema import EngineModel, RelationTableViewConfig
from ..schemas.mapping import MappingListPage, MappingListRow, MappingObjectSummary

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
