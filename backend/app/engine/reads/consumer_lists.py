"""A consumer API's declared lists, page by page (Base 0.9 C3, C-D27–C-D30).

A list holds the live records of its type in the workspace. A parent value, by object ID only, keeps
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

from ...common.pagination import PageRequest, paginate_statement, text_key
from ...errors import api_error
from ...models.database import RdmObject
from ...models.schema import ConsumerApiDefinition, ConsumerList, EngineModel
from .consumer_objects import ConsumerObjects
from .consumer_parameters import ConsumerFilter, below
from .object_query import build_object_query


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
    workspace_key: str,
    parent_ids: Sequence[str],
    narrowed: ConsumerFilter,
    parameters: Mapping[str, Sequence[str]],
    page: PageRequest,
    page_size: int,
) -> dict[str, Any]:
    """One page of the list. ``parameters`` are the request's parameter values, bound into the
    cursor with the workspace, the parent IDs and the contract version."""
    query = build_object_query(
        model,
        object_type_key=declared.objectType,
        application_key=None,
        workspace_key=workspace_key,
        parent_object_id=None,
        search=None,
        sort=declared.sortBy,
    )
    statement = query.statement.where(*narrowed.on(RdmObject))
    if parent_ids:
        _require_parents(session, declared, workspace_key, parent_ids)
        starts = select(RdmObject.id).where(RdmObject.id.in_(list(parent_ids)))
        statement = statement.where(below(model, workspace_key, starts, [declared.objectType])(RdmObject))
    keys = query.keys
    if declared.sortBy is not None:
        # The sort value, then name, then creation order (C-D29).
        keys = (*keys[:-1], text_key("name", RdmObject.name, "name"), keys[-1])
    found = paginate_statement(
        session,
        statement,
        keys=keys,
        scope=f"consumer-list:{definition.key}:{declared.key}",
        filters={
            "workspace": workspace_key,
            "contractVersion": definition.contractVersion,
            "parents": sorted(parent_ids),
            "parameters": {name: sorted(values) for name, values in sorted(parameters.items())},
        },
        page=page,
        page_size=page_size,
        seek=query.seek,
    )
    ids = [row.id for row in found.items]
    composed = ConsumerObjects(model, definition).compose(session, workspace_key, ids, narrowed)
    return {
        "items": [composed[object_id] for object_id in ids if object_id in composed],
        "workspace": workspace_key,
        "pageSize": page_size,
        **found.links(),
    }


def _require_parents(
    session: Session, declared: ConsumerList, workspace_key: str, parent_ids: Sequence[str]
) -> None:
    """Each parent ID names a record of the parent types in the workspace (C-D28)."""
    assert declared.parentParameter is not None
    known = set(
        session.scalars(
            select(RdmObject.id).where(
                RdmObject.id.in_(list(parent_ids)),
                RdmObject.workspace_key == workspace_key,
                RdmObject.object_type_key.in_(list(declared.parentParameter.objectTypes)),
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
