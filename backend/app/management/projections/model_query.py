"""The model-aware object query's page, items and expansions (Base 0.9 Q3).

The engine plans the query (``engine/reads/model_query.py``); this pages it and renders each record
as the object list does, then narrows it to a ``select``. Expansions read one statement per
``expand`` for the whole page and render every expanded record in one batch; the per-type list's
``expand`` (0.9 K5) reads its relation columns through the same step (:func:`expand_records`).
"""

from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...common.pagination import PageRequest, paginate_statement
from ...engine.model.consumer_contract import split_ancestor_reference
from ...engine.model.validation.fields import ANCESTOR_FIELD_PREFIX
from ...engine.reads.model_query import SELECT_FIELDS, Expansion, plan_model_query
from ...engine.reads.relation_queries import ExpansionRow, expansion_cursor, expansion_rows
from ...engine.reads.snapshot_reads import (
    SnapshotContext,
    change_set_context,
    find_objects,
    object_paths,
    publication_context,
)
from ...models.database import RdmObject
from ...models.queries import ModelQuery
from ...models.schema import EngineModel
from ..presenters import build_object_responses, change_set_object_response
from ..schemas.queries import (
    ExpandedRecord,
    ExpandedRelations,
    ObjectQueryPage,
    QueryObject,
    QuerySelectedObject,
    SelectedRecord,
)
from ..schemas.records import ObjectResponse


def query_objects(
    session: Session, model: EngineModel, request: ModelQuery, *, workspace_key: str
) -> ObjectQueryPage:
    """One page of the query in its context: live, or the change set or publication it names."""
    context = _context(session, request)
    plan = plan_model_query(model, request, workspace_key=workspace_key, context=context)
    page = paginate_statement(
        session,
        plan.query.statement,
        keys=plan.query.keys,
        scope=plan.scope,
        filters=plan.query.filters,
        page=PageRequest(
            cursor=request.cursor,
            position=request.position,
            from_end=request.from_ == "end",
            include_total=request.includeTotal,
        ),
        page_size=request.pageSize,
        message="Query cursor is invalid",
        rows=context is not None,
        overlay=plan.query.overlay,
    )
    records = _render(session, model, context, page.items)
    expansions = expand_records(
        session,
        model,
        context,
        workspace_key=workspace_key,
        anchor_ids=[record.id for record in records],
        expansions=plan.expansions,
    )
    items = []
    for record in records:
        expanded = expansions.get(record.id)
        if plan.select is None:
            items.append(QueryObject(**record.model_dump(), expanded=expanded))
        else:
            selected = _selected(record, plan.select)
            items.append(QuerySelectedObject(**selected.model_dump(), expanded=expanded))
    return ObjectQueryPage(items=items, **page.links())


def expand_records(
    session: Session,
    model: EngineModel,
    context: SnapshotContext | None,
    *,
    workspace_key: str,
    anchor_ids: Sequence[str],
    expansions: Sequence[Expansion],
) -> dict[str, list[ExpandedRelations]]:
    """Each anchor's expansions, in ``expansions``' order: one statement per expansion for every
    anchor, and the expanded records read and rendered in one batch. Empty without expansions."""
    if not expansions:
        return {}
    read = [
        (
            expansion,
            expansion_rows(
                session,
                context,
                workspace_key=workspace_key,
                anchor_ids=anchor_ids,
                direction=expansion.direction,
                relation_type_key=expansion.relation_type_key,
                limit=expansion.limit,
            ),
        )
        for expansion in expansions
    ]
    related = _related(session, model, context, read)
    values = {
        expansion.field: _field_values(session, model, context, related, expansion.field)
        for expansion in expansions
        if expansion.field is not None
    }
    return {
        anchor_id: [
            _expanded(context, workspace_key, expansion, rows, anchor_id, related, values)
            for expansion, rows in read
        ]
        for anchor_id in anchor_ids
    }


def _context(session: Session, request: ModelQuery) -> SnapshotContext | None:
    if request.context.changeSetId:
        return change_set_context(session, request.context.changeSetId)
    if request.context.publicationId:
        return publication_context(session, request.context.publicationId)
    return None


def _render(
    session: Session, model: EngineModel, context: SnapshotContext | None, rows: list[Any]
) -> list[ObjectResponse]:
    """Records as the object list returns them, in the order given."""
    if context is None:
        return build_object_responses(session, model, rows)
    paths = object_paths(session, context, rows)
    return [
        change_set_object_response(row, context.id, model, path=paths[row.object_id]).model_copy(
            update={"workspaceKey": context.workspace_key}
        )
        for row in rows
    ]


def _related(
    session: Session,
    model: EngineModel,
    context: SnapshotContext | None,
    expansions: list[tuple[Expansion, list[ExpansionRow]]],
) -> dict[str, ObjectResponse]:
    """Every expanded record of the page, read and rendered in one batch."""
    ids = list(dict.fromkeys(row.related_id for _expansion, rows in expansions for row in rows))
    return _records(session, model, context, ids)


def _records(
    session: Session, model: EngineModel, context: SnapshotContext | None, ids: Sequence[str]
) -> dict[str, ObjectResponse]:
    """Records by ID in the context, rendered as the object list renders them, in one batch."""
    if not ids:
        return {}
    if context is None:
        rows = list(session.scalars(select(RdmObject).where(RdmObject.id.in_(ids))))
    else:
        rows = list(find_objects(session, context, ids).values())
    return {record.id: record for record in _render(session, model, context, rows)}


def _field_values(
    session: Session,
    model: EngineModel,
    context: SnapshotContext | None,
    records: dict[str, ObjectResponse],
    field: str,
) -> dict[str, Any]:
    """Each record's value of ``field`` (0.9 K5a, D148): its own name or attribute, or of its
    ancestor of a type (``ancestor:<type>.<field>``), the one nearest the root as ``path`` names it.
    An ancestor's attribute is read for the page's ancestors in one batch."""
    reference = split_ancestor_reference(field)
    if reference is None:
        return {record_id: _own_value(record, field) for record_id, record in records.items()}
    type_key, name = reference
    ancestors = {
        record_id: next(
            (part for part in record.path[:-1] if part["objectTypeKey"] == type_key), None
        )
        for record_id, record in records.items()
    }
    if name in {"id", "name"}:
        return {
            record_id: None if part is None else part[name] for record_id, part in ancestors.items()
        }
    read = _records(
        session,
        model,
        context,
        list(dict.fromkeys(part["id"] for part in ancestors.values() if part is not None)),
    )
    return {
        record_id: None if part is None or part["id"] not in read else _own_value(read[part["id"]], name)
        for record_id, part in ancestors.items()
    }


def _own_value(record: ObjectResponse, field: str) -> Any:
    if field in {"id", "name"}:
        return getattr(record, field)
    return next((item.value for item in record.attributes if item.attributeTypeKey == field), None)


def _expanded(
    context: SnapshotContext | None,
    workspace_key: str,
    expansion: Expansion,
    rows: list[ExpansionRow],
    anchor_id: str,
    related: dict[str, ObjectResponse],
    values: dict[str | None, dict[str, Any]] | None = None,
) -> ExpandedRelations:
    mine = [row for row in rows if row.anchor_id == anchor_id]
    count = mine[0].total if mine else 0
    more = count > len(mine)

    def shown(record: ObjectResponse) -> ObjectResponse | SelectedRecord:
        if expansion.select is None:
            return record
        selected = _selected(record, expansion.select)
        if expansion.field is not None and values is not None:
            selected.fields[expansion.field] = values[expansion.field].get(record.id)
        return selected

    return ExpandedRelations(
        relationTypeKey=expansion.relation_type_key,
        direction=expansion.direction,
        field=expansion.field,
        count=count,
        items=[
            ExpandedRecord(relationId=row.relation_id, object=shown(related[row.related_id]))
            for row in mine
        ],
        nextCursor=(
            expansion_cursor(
                context,
                workspace_key=workspace_key,
                direction=expansion.direction,
                relation_type_key=expansion.relation_type_key,
                after=mine[-1],
            )
            if more
            else None
        ),
    )


def _selected(record: ObjectResponse, fields: tuple[str, ...]) -> SelectedRecord:
    """The record narrowed to ``fields`` (D17)."""
    attributes = {item.attributeTypeKey: item.value for item in record.attributes}
    values: dict[str, Any] = {}
    for field in fields:
        if field in SELECT_FIELDS:
            values[field] = getattr(record, field)
        elif field.startswith(ANCESTOR_FIELD_PREFIX):
            ancestor_type_key = field.removeprefix(ANCESTOR_FIELD_PREFIX)
            # The path runs from the root to the record, so the first match is nearest the root.
            ancestor = next(
                (part for part in record.path[:-1] if part["objectTypeKey"] == ancestor_type_key),
                None,
            )
            values[field] = (
                None if ancestor is None else {"id": ancestor["id"], "name": ancestor["name"]}
            )
        else:
            values[field] = attributes.get(field)
    return SelectedRecord(
        id=record.id, objectTypeKey=record.objectTypeKey, version=record.version, fields=values
    )
