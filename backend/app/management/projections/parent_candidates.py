"""Move targets for a record (Base 0.8 B2).

A record's parent candidates are the records of every type the model allows to contain it, in the
record's application and workspace, in live data or a change set. They are the parents a
``PATCH`` with ``parentObjectId`` could name, listed in name order through the object query builder,
so search, cursors, positions and totals mean what they mean on an object list.

A candidate the write would refuse stays in the list, marked with its reason (D14): the record
itself, a record under it (a cycle), or its current parent. Whether a candidate is under the record
is read from the candidate's path, which the page returns anyway: one walk up per page, batched by
level, so it costs the page and the hierarchy's depth, never the size of the moved subtree.

In a change set, ``includeTypeChanges`` (Base 0.8 C3) also lists the records a move that changes
the record's type could go under: those of types that can contain another type of the record's
application, as the restructuring planner decides it. Each candidate then names the types the
record would be there.

``withinObjectTypeKey`` (Base 0.8 C4) keeps the list to a set of types, as a client that shows only
some types (a tree view) needs: candidates of those types only, and with ``includeTypeChanges`` only
those types as what the record would become, a candidate left with none dropped. The server filters,
so totals and positions stay truthful.
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...common.pagination import Keyed, Overlay, PageRequest, paginate_statement
from ...db import begin_snapshot_read
from ...engine.model.placements import application_type_keys, possible_types
from ...engine.model.traversal import parent_type_keys
from ...engine.reads.object_query import LIVE_OBJECT_COLUMNS, live_object_paths, refine_object_query
from ...engine.reads.snapshot_reads import (
    SnapshotContext,
    change_set_context,
    find_object,
    object_paths,
    object_projection,
    snapshot_object_columns,
)
from ...engine.records.context import load_active_projection
from ...engine.records.rules import get_object_type
from ...engine.workspaces.catalogue import resolve_workspace
from ...errors import api_error
from ...models.database import RdmObject
from ...models.schema import EngineModel
from ..schemas.records import ObjectPathPart, ParentCandidate, ParentCandidatePage


def parent_candidates(
    session: Session,
    model: EngineModel,
    *,
    object_type_key: str,
    object_id: str,
    workspace_key: str | None,
    change_set_id: str | None,
    parent_object_type_key: str | None,
    search: str | None,
    page: PageRequest,
    page_size: int,
    include_type_changes: bool = False,
    within_object_type_keys: list[str] | None = None,
) -> ParentCandidatePage:
    begin_snapshot_read(session)
    get_object_type(model, object_type_key)
    if include_type_changes and not change_set_id:
        raise api_error(
            422,
            "TYPE_CHANGES_NEED_CHANGE_SET",
            "A record's type changes only in a change set; includeTypeChanges needs changeSetId",
            {"parameter": "includeTypeChanges"},
        )
    context = change_set_context(session, change_set_id) if change_set_id else None
    if context is not None:
        record = find_object(session, context, object_id, object_type_key)
        if record is None:
            raise api_error(404, "OBJECT_NOT_FOUND", f"Object '{object_id}' not found")
        application_key, current_parent = record.application_key, record.parent_object_id
    else:
        workspace_key = resolve_workspace(session, workspace_key).key
        item = load_active_projection(session, object_id, object_type_key)
        if item.workspace_key != workspace_key:
            raise api_error(404, "OBJECT_NOT_FOUND", f"Object '{object_id}' not found")
        application_key, current_parent = item.application_key, item.parent_object_id

    within = set(within_object_type_keys) if within_object_type_keys else None
    unknown = sorted(key for key in within or () if model.object_type(key) is None)
    if unknown:
        raise api_error(
            422,
            "UNKNOWN_OBJECT_TYPE",
            f"withinObjectTypeKey names object types the model does not have: {unknown}",
            {"parameter": "withinObjectTypeKey", "objectTypeKeys": unknown},
        )
    own_parents = parent_type_keys(model, object_type_key)
    if within is not None:
        own_parents = own_parents & within
    becomes: dict[str, list[str]] = {}
    if include_type_changes:
        application_types = application_type_keys(model, application_key)
        for key in application_types:
            if within is not None and key not in within:
                continue
            if key in own_parents:
                becomes[key] = [object_type_key]
            elif options := [
                option
                for option in possible_types(model, application_types, key)
                if within is None or option in within
            ]:
                becomes[key] = options
    types = sorted(own_parents | set(becomes))
    if parent_object_type_key is not None:
        if parent_object_type_key not in types:
            raise api_error(
                422,
                "INVALID_PARENT_TYPE",
                f"Object type '{parent_object_type_key}' cannot contain '{object_type_key}' records",
                {"parentObjectTypeKey": parent_object_type_key, "permitted": types},
            )
        types = [parent_object_type_key]
    object_types = tuple(get_object_type(model, key) for key in types)
    filters = {
        "objectTypeKey": object_type_key,
        "objectId": object_id,
        "parentObjectTypeKey": parent_object_type_key,
        "search": search,
        **({"includeTypeChanges": True} if include_type_changes else {}),
        **({"withinObjectTypeKey": sorted(within)} if within is not None else {}),
    }

    if context is None:
        statement = select(RdmObject).where(
            RdmObject.workspace_key == workspace_key,
            RdmObject.application_key == application_key,
            RdmObject.object_type_key.in_(types),
        )
        statement, keys, *_ = refine_object_query(
            model,
            LIVE_OBJECT_COLUMNS,
            statement,
            object_types=object_types,
            search=search,
            sort=None,
            field_filters=[],
        )
        found = paginate_statement(
            session,
            statement,
            keys=keys,
            scope="parent-candidates",
            filters={**filters, "workspaceKey": workspace_key},
            page=page,
            page_size=page_size,
            message="Parent candidate cursor is invalid",
        )
        paths = live_object_paths(session, found.items)
        items = [(item.id, item.object_type_key, item.name) for item in found.items]
    else:
        statement, keys, overlay = _snapshot_statement(
            model, context, types, object_types, application_key, search
        )
        found = paginate_statement(
            session,
            statement,
            keys=keys,
            scope="parent-candidates-change-set",
            filters={**filters, "changeSetId": context.id},
            page=page,
            page_size=page_size,
            message="Parent candidate cursor is invalid",
            rows=True,
            overlay=overlay,
        )
        paths = object_paths(session, context, found.items)
        items = [(item.object_id, item.object_type_key, item.name) for item in found.items]

    candidates = []
    for candidate_id, candidate_type, name in items:
        path = paths[candidate_id]
        reason = _refusal(candidate_id, path, object_id, current_parent)
        candidates.append(
            ParentCandidate(
                id=candidate_id,
                objectTypeKey=candidate_type,
                name=name,
                path=[ObjectPathPart(**part) for part in path],
                eligible=reason is None,
                reason=reason,
                objectTypeKeys=becomes.get(candidate_type) if include_type_changes else None,
            )
        )
    return ParentCandidatePage(items=candidates, **found.links())


def _snapshot_statement(
    model: EngineModel,
    context: SnapshotContext,
    types: list[str],
    object_types: tuple[Any, ...],
    application_key: str,
    search: str | None,
) -> tuple[Any, Any, Overlay | None]:
    """The change set's candidates, with the parts position reads resolve through, as
    ``build_snapshot_object_query`` builds them for one type."""

    def refine(part: Any) -> tuple[Any, Any]:
        projection = object_projection(
            context, object_type_keys=types, application_key=application_key, part=part
        )
        statement, keys, *_ = refine_object_query(
            model,
            snapshot_object_columns(projection, context, search_index=part in {"effective", "base"}),
            select(projection),
            object_types=object_types,
            search=search,
            sort=None,
            field_filters=[],
        )
        return statement, keys

    statement, keys = refine("effective")
    overlay = None
    if context.base is not None:
        parts = {part: Keyed(*refine(part)) for part in ("base", "replaced", "added")}
        overlay = Overlay(parts["base"], parts["replaced"], parts["added"])
    return statement, keys, overlay


def _refusal(
    candidate_id: str, path: list[dict[str, str]], object_id: str, current_parent: str | None
) -> str | None:
    """Why moving the record under the candidate would be refused, or ``None``."""
    if candidate_id == object_id:
        return "self"
    if candidate_id == current_parent:
        return "currentParent"
    if any(part["id"] == object_id for part in path):
        return "descendant"
    return None
