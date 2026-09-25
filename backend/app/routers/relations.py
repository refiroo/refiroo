from typing import Annotated, Literal

from fastapi import APIRouter, Query, Response, status
from sqlalchemy import select

from ..db import DbSession
from ..errors import api_error
from ..models.api import (
    RelationCreate,
    RelationExpansion,
    RelationPage,
    RelationResponse,
    RelationUpdate,
    WorkspaceDraftRelationUpdate,
    WorkspaceDraftRelationWrite,
)
from ..models.database import RdmObject
from ..services.model.registry import RequestModelSnapshot, resolve_model_snapshot
from ..services.objects import build_object_responses, load_active_projection
from ..services.pagination import paginate_statement
from ..services.relation_queries import build_relation_query, build_snapshot_relation_query
from ..services.relations import (
    build_relation_response,
    create_live_relation,
    delete_live_relation,
    load_relation,
    update_live_relation,
)
from ..services.snapshot_reads import (
    draft_context,
    find_object,
    find_objects,
    find_relation,
    object_paths,
    revision_context,
)
from ..services.workspace_revisions import (
    delete_draft_relation,
    put_draft_relation,
    update_draft_relation,
)
from ..services.workspaces import resolve_workspace
from .objects import _draft_object_response
from .paging import SeekablePageQuery

router = APIRouter(prefix="/api/v1", tags=["relations"])

def _draft_response(item) -> RelationResponse:
    # Draft and history relations record no timestamps (WP-10K); never substitute the current time.
    return RelationResponse(id=item.relation_id, relationTypeKey=item.relation_type_key, fromObjectId=item.from_object_id, toObjectId=item.to_object_id, attributes=item.attributes or {}, version=item.version, createdAt=None, updatedAt=None)

def _ctx(draft: str, expected: int | None) -> int:
    if expected is None:
        raise api_error(
            409,
            "workspace_draft_required",
            "expectedWorkspaceDraftVersion is required when targeting a workspace draft",
        )
    return expected

@router.post("/relations", response_model=RelationResponse, status_code=status.HTTP_201_CREATED)
def create_relation(payload: RelationCreate, session: DbSession) -> RelationResponse:
    if payload.workspaceDraftId:
        draft = str(payload.workspaceDraftId)
        expected = _ctx(draft, payload.expectedWorkspaceDraftVersion)
        row = put_draft_relation(session, draft, WorkspaceDraftRelationWrite(id=None, relationTypeKey=payload.relationTypeKey, fromObjectId=payload.fromObjectId, toObjectId=payload.toObjectId, attributes=payload.attributes, expectedDraftVersion=expected, expectedRecordVersion=None))
        return _draft_response(row).model_copy(update={"workspaceDraftVersion": draft_context(session, draft).draft.version})
    row = create_live_relation(session, resolve_model_snapshot(session).model, payload)
    return build_relation_response(row)

@router.get("/relations", response_model=RelationPage)
def list_relations(
    session: DbSession,
    snapshot: RequestModelSnapshot,
    paging: SeekablePageQuery,
    object_id: str = Query(alias="objectId"),
    direction: Literal["outgoing", "incoming", "both"] = "both",
    relation_type_keys: Annotated[
        list[str] | None,
        Query(
            alias="relationTypeKey",
            description="List only these relation types; repeat the parameter for several",
        ),
    ] = None,
    workspace_key: str | None = Query(default=None, alias="workspaceKey"),
    workspace_draft_id: str | None = Query(default=None, alias="workspaceDraftId"),
    workspace_revision_id: str | None = Query(default=None, alias="workspaceRevisionId"),
    search: str | None = Query(
        default=None,
        description="Match the related record's name or searchable fields, case-insensitively",
    ),
    sort: str | None = Query(
        default=None,
        description=(
            "A field of the related record, as on an object list: name, a sortable attribute,"
            " ancestor:<type>, or (live only) createdAt or updatedAt; prefix '-' for descending."
            " Attribute and ancestor sorts need the listed relations to reach one object type."
            " Omitted: name"
        ),
    ),
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
) -> RelationPage:
    if sum(value is not None for value in (workspace_draft_id, workspace_revision_id)) > 1:
        raise api_error(422, "mutually_exclusive_context", "Workspace contexts cannot be combined")
    options = {
        "object_id": object_id,
        "direction": direction,
        "relation_type_keys": relation_type_keys or None,
        "search": search or None,
        "sort": sort,
    }
    if workspace_draft_id or workspace_revision_id:
        context = draft_context(session, workspace_draft_id) if workspace_draft_id else revision_context(session, workspace_revision_id)
        anchor = find_object(session, context, object_id)
        if anchor is None:
            raise api_error(404, "object_not_found", "Object not found")
        query = build_snapshot_relation_query(snapshot.model, context, anchor_type_key=anchor.object_type_key, **options)
        page = paginate_statement(session, query.statement, keys=query.keys, scope=f"relations-{context.kind}", filters=query.filters, page=paging, page_size=page_size, message="Relation cursor is invalid", rows=True, seek=query.seek)
        objects = find_objects(session, context, (row.related_id for row in page.items))
        paths = object_paths(session, context, objects.values())
        return RelationPage(items=[RelationExpansion(direction="outgoing" if row.from_object_id == object_id else "incoming", relation=_draft_response(row), object=_draft_object_response(objects[row.related_id], context.id, snapshot.model, path=paths[row.related_id]).model_copy(update={"workspaceKey": context.workspace_key})) for row in page.items if row.related_id in objects], **page.links())
    anchor = load_active_projection(session, object_id)
    workspace = resolve_workspace(session, workspace_key)
    if anchor.workspace_key != workspace.key:
        raise api_error(404, "object_not_found", "Object not found in the selected workspace")
    query = build_relation_query(snapshot.model, anchor_type_key=anchor.object_type_key, workspace_key=anchor.workspace_key, **options)
    page = paginate_statement(session, query.statement, keys=query.keys, scope="relations", filters=query.filters, page=paging, page_size=page_size, message="Relation cursor is invalid", rows=True, seek=query.seek)
    related_ids = list(dict.fromkeys(row.related_id for row in page.items))
    related_rows = list(session.scalars(select(RdmObject).where(RdmObject.id.in_(related_ids))))
    # One batched build for the page, not one per row (S1 finding).
    related = {item.id: item for item in build_object_responses(session, snapshot.model, related_rows)}
    return RelationPage(items=[RelationExpansion(direction="outgoing" if row.ObjectRelation.from_object_id == object_id else "incoming", relation=build_relation_response(row.ObjectRelation), object=related[row.related_id]) for row in page.items], **page.links())

@router.get("/relations/{relation_id}", response_model=RelationResponse)
def get_relation(relation_id: str, session: DbSession, snapshot: RequestModelSnapshot, workspace_key: str | None = Query(default=None, alias="workspaceKey"), workspace_draft_id: str | None = Query(default=None, alias="workspaceDraftId"), workspace_revision_id: str | None = Query(default=None, alias="workspaceRevisionId")) -> RelationResponse:
    if workspace_draft_id and workspace_revision_id: raise api_error(422, "mutually_exclusive_context", "Workspace contexts cannot be combined")
    if workspace_draft_id or workspace_revision_id:
        context = draft_context(session, workspace_draft_id) if workspace_draft_id else revision_context(session, workspace_revision_id)
        row = find_relation(session, context, relation_id)
        if row is None: raise api_error(404, "relation_not_found", "Relation not found")
        return _draft_response(row)
    row = load_relation(session, relation_id)
    workspace = resolve_workspace(session, workspace_key)
    endpoints = set(session.scalars(
        select(RdmObject.id).where(
            RdmObject.id.in_([row.from_object_id, row.to_object_id]),
            RdmObject.workspace_key == workspace.key,
        )
    ))
    if endpoints != {row.from_object_id, row.to_object_id}:
        raise api_error(404, "relation_not_found", "Relation not found")
    return build_relation_response(row)

@router.patch("/relations/{relation_id}", response_model=RelationResponse)
def update_relation(relation_id: str, payload: RelationUpdate, session: DbSession) -> RelationResponse:
    if payload.workspaceDraftId:
        draft = str(payload.workspaceDraftId)
        expected = _ctx(draft, payload.expectedWorkspaceDraftVersion)
        row = update_draft_relation(session, draft, relation_id, WorkspaceDraftRelationUpdate(attributes=payload.attributes, expectedDraftVersion=expected, expectedRecordVersion=payload.expectedVersion))
        return _draft_response(row).model_copy(update={"workspaceDraftVersion": draft_context(session, draft).draft.version})
    row = update_live_relation(session, resolve_model_snapshot(session).model, relation_id, payload)
    return build_relation_response(row)

@router.delete("/relations/{relation_id}", status_code=204)
def remove_relation(relation_id: str, session: DbSession,
                    workspace_draft_id: str | None = Query(default=None, alias="workspaceDraftId"),
                    expected_workspace_draft_version: int | None = Query(default=None, alias="expectedWorkspaceDraftVersion", ge=1),
                    expected_version: int = Query(alias="expectedVersion", ge=1)) -> Response:
    if workspace_draft_id:
        _ctx(workspace_draft_id, expected_workspace_draft_version)
        delete_draft_relation(session, workspace_draft_id, relation_id, expected_workspace_draft_version, expected_version)
    else:
        delete_live_relation(session, resolve_model_snapshot(session).model, relation_id, expected_version)
    return Response(status_code=204)
