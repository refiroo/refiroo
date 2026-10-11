"""A consumer API's declared lists, page by page (Base 0.9 C3, C-D27–C-D30).

A list holds the records of its type in the workspace's live data, or in one of its publications
(C6a). A parent value, by object ID only, keeps
those anywhere below that record; several IDs keep those below any of them. The definition's
parameters narrow it as they narrow get by ID (``consumer_parameters``). The statement is the
per-type list's (``build_object_query``), ordered by the list's ``sortBy`` with records without a
value last, then by name, then by creation order, and paged as every engine list is (ADR-030). The
page's items are the shared object, composed for the page's IDs in a fixed number of statements.
"""

from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...common.pagination import Keyed, PageRequest, paginate_statement
from ...errors import api_error
from ...models.database import PublicationObject, PublicationRelation
from ...models.schema import ConsumerApiDefinition, ConsumerList, EngineModel
from .consumer_objects import ConsumerObjects
from .consumer_parameters import ConsumerFilter, as_of_not_supported, below, without_target
from .consumer_source import ConsumerSource, cursor_scope
from .object_query import as_of_filter, build_object_query
from .snapshot_reads import SnapshotBase, SnapshotContext, build_snapshot_object_query

# A list's and XREF's pages (C-D30): the smallest, the largest and the default size.
PAGE_SIZE = (1, 100, 20)


def consumer_list(definition: ConsumerApiDefinition, list_key: str) -> ConsumerList:
    """The definition's list ``list_key``, or ``404 LIST_NOT_FOUND``."""
    found = next((item for item in definition.lists if item.key == list_key), None)
    if found is None:
        raise api_error(404, "LIST_NOT_FOUND", f"List '{list_key}' not found")
    return found


def read_consumer_list(
    session: Session,
    model: EngineModel,
    definition: ConsumerApiDefinition,
    declared: ConsumerList,
    *,
    source: ConsumerSource,
    parent_ids: Sequence[str],
    narrowed: ConsumerFilter,
    parameters: Mapping[str, Sequence[str]],
    page: PageRequest,
    page_size: int,
) -> dict[str, Any]:
    """One page of the list. ``parameters`` are the request's parameter values, bound into the
    cursor with the workspace, the parent IDs and the contract version; a ``to.`` value is not
    bound, since it changes no row or order (C-D54). A pinned read lists the publication's records
    through the publication's list query, whose ties on equal names fall to the object ID: a
    publication records no creation order (as on the management API's publication lists). With
    ``asOf`` the list's type must declare a period (C-D77); the date is bound into the cursor and the
    envelope names the type in ``asOfApplied`` (C-D78)."""
    public = definition.objectTypes[declared.objectType].publicName
    if narrowed.as_of is not None and declared.objectType not in narrowed.dated:
        raise as_of_not_supported([public])
    if source.publication_id is None:
        query = build_object_query(
            model,
            object_type_key=declared.objectType,
            application_key=None,
            workspace_key=source.workspace_key,
            parent_object_id=None,
            search=None,
            sort=declared.sortBy,
        )
    else:
        query = build_snapshot_object_query(
            model,
            SnapshotContext(
                "publication",
                source.publication_id,
                source.workspace_key,
                None,
                SnapshotBase(PublicationObject, PublicationRelation, "publication_id", source.publication_id),
            ),
            object_type_key=declared.objectType,
            application_key=None,
            parent_object_id=None,
            search=None,
            sort=declared.sortBy,
            field_filters=[],
        )
    record = query.record
    conditions = narrowed.on(record)
    if parent_ids:
        _require_parents(session, declared, source, parent_ids)
        objects = source.objects
        starts = select(objects.id).where(objects.id.in_(list(parent_ids)))
        conditions.append(below(session, model, source, starts, [declared.objectType])(record))
    if declared.sortBy is not None:
        # The sort value, then name, then creation order (C-D29).
        query = query.then_by_name()
    found = paginate_statement(
        session,
        query.statement.where(*conditions),
        keys=query.keys,
        scope=cursor_scope(f"consumer-list:{definition.key}:{declared.key}", source),
        filters={
            "workspace": source.workspace_key,
            "contractVersion": definition.contractVersion,
            "parents": sorted(parent_ids),
            "parameters": {name: sorted(values) for name, values in sorted(without_target(parameters).items())},
            **as_of_filter(narrowed.as_of),
        },
        page=page,
        page_size=page_size,
        seek=query.seek,
        rows=source.pinned,
        parts=None
        if query.parts is None
        else [Keyed(part.statement.where(*conditions), part.keys) for part in query.parts],
    )
    ids = [row.object_id if source.pinned else row.id for row in found.items]
    composed = ConsumerObjects(model, definition).compose(session, source, ids, narrowed)
    return {
        "items": [composed[object_id] for object_id in ids if object_id in composed],
        "workspace": source.workspace_key,
        "publication": source.publication_id,
        **({"asOfApplied": [public]} if narrowed.as_of is not None else {}),
        "pageSize": page_size,
        **found.links(),
    }


def _require_parents(
    session: Session, declared: ConsumerList, source: ConsumerSource, parent_ids: Sequence[str]
) -> None:
    """Each parent ID names a record of the parent types in the source (C-D28)."""
    assert declared.parentParameter is not None
    objects = source.objects
    known = set(
        session.scalars(
            select(objects.id).where(
                objects.id.in_(list(parent_ids)),
                objects.workspace_key == source.workspace_key,
                objects.object_type_key.in_(list(declared.parentParameter.objectTypes)),
            )
        )
    )
    missing = [value for value in parent_ids if value not in known]
    if missing:
        raise api_error(
            404,
            "PARENT_NOT_FOUND",
            f"Parent '{missing[0]}' is no record the list '{declared.key}' sits under",
            {"parents": missing, "path": f"/query/{declared.parentParameter.name}"},
        )
