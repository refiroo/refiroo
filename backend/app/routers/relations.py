from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Query, Response, status
from sqlalchemy import or_, select
from sqlalchemy.orm import aliased

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
from ..models.database import (
    ObjectRelation,
    RdmObject,
    WorkspaceRevision,
    WorkspaceRevisionObject,
    WorkspaceRevisionRelation,
)
from ..services.model.registry import ActiveModelSnapshot
from ..services.objects import build_object_responses, load_active_projection
from ..services.pagination import integer_key, paginate_sequence, paginate_statement
from ..services.relations import (
    build_relation_response,
    create_live_relation,
    delete_live_relation,
    load_relation,
    update_live_relation,
)
from ..services.workspace_revisions import (
    delete_draft_relation,
    effective_draft_membership,
    put_draft_relation,
    update_draft_relation,
)
from ..services.workspaces import resolve_workspace
from .objects import _draft_object_response

router = APIRouter(prefix="/api/v1", tags=["relations"])

def _draft_response(item) -> RelationResponse:
    now = datetime.now(UTC)
    return RelationResponse(id=item.relation_id, relationTypeKey=item.relation_type_key, fromObjectId=item.from_object_id, toObjectId=item.to_object_id, attributes=item.attributes or {}, version=item.version, createdAt=now, updatedAt=now)

def _ctx(draft: str, expected: int | None) -> int:
    if expected is None:
        raise api_error(
            409,
            "workspace_draft_required",
            "expectedWorkspaceDraftVersion is required when targeting a workspace draft",
        )
    return expected

@router.post("/relations", response_model=RelationResponse, status_code=status.HTTP_201_CREATED)
def create_relation(payload: RelationCreate, session: DbSession, snapshot: ActiveModelSnapshot) -> RelationResponse:
    if payload.workspaceDraftId:
        draft = str(payload.workspaceDraftId)
        expected = _ctx(draft, payload.expectedWorkspaceDraftVersion)
        row = put_draft_relation(session, draft, WorkspaceDraftRelationWrite(id=None, relationTypeKey=payload.relationTypeKey, fromObjectId=payload.fromObjectId, toObjectId=payload.toObjectId, attributes=payload.attributes, expectedDraftVersion=expected, expectedRecordVersion=None))
        return _draft_response(row).model_copy(update={"workspaceDraftVersion": effective_draft_membership(session, draft).draft.version})
    row = create_live_relation(session, snapshot.model, payload)
    return build_relation_response(row)

@router.get("/relations", response_model=RelationPage)
def list_relations(session: DbSession, snapshot: ActiveModelSnapshot, object_id: str = Query(alias="objectId"), direction: Literal["outgoing", "incoming", "both"] = "both", relation_type_key: str | None = Query(default=None, alias="relationTypeKey"), workspace_key: str | None = Query(default=None, alias="workspaceKey"), workspace_draft_id: str | None = Query(default=None, alias="workspaceDraftId"), workspace_revision_id: str | None = Query(default=None, alias="workspaceRevisionId"), cursor: str | None = None, page_size: int = Query(default=100, ge=1, le=500, alias="pageSize")) -> RelationPage:
    if sum(value is not None for value in (workspace_draft_id, workspace_revision_id)) > 1:
        raise api_error(422, "mutually_exclusive_context", "Workspace contexts cannot be combined")
    if workspace_draft_id:
        membership = effective_draft_membership(session, workspace_draft_id)
        rows = [row for row in membership.relations if (row.from_object_id == object_id and direction in {"outgoing", "both"}) or (row.to_object_id == object_id and direction in {"incoming", "both"})]
        if relation_type_key:
            rows = [row for row in rows if row.relation_type_key == relation_type_key]
        page, next_cursor = paginate_sequence(rows, lambda row: (row.relation_id,), scope="relations-draft", filters={"draftId": workspace_draft_id, "objectId": object_id, "direction": direction, "relationTypeKey": relation_type_key}, cursor=cursor, page_size=page_size, sort=("id",), message="Relation cursor is invalid")
        objects = {row.object_id: row for row in membership.objects}
        return RelationPage(items=[RelationExpansion(direction="outgoing" if row.from_object_id == object_id else "incoming", relation=_draft_response(row), object=_draft_object_response(objects[ row.to_object_id if row.from_object_id == object_id else row.from_object_id], workspace_draft_id, snapshot.model).model_copy(update={"workspaceKey": membership.draft.workspace_key})) for row in page if (row.to_object_id if row.from_object_id == object_id else row.from_object_id) in objects], nextCursor=next_cursor)
    if workspace_revision_id:
        revision = session.scalar(
            select(WorkspaceRevision).where(WorkspaceRevision.id == workspace_revision_id)
        )
        if revision is None:
            raise api_error(404, "workspace_revision_not_found", "Workspace revision not found")
        rows = list(session.scalars(select(WorkspaceRevisionRelation).where(WorkspaceRevisionRelation.revision_id == workspace_revision_id)))
        rows = [row for row in rows if (row.from_object_id == object_id and direction in {"outgoing", "both"}) or (row.to_object_id == object_id and direction in {"incoming", "both"})]
        if relation_type_key:
            rows = [row for row in rows if row.relation_type_key == relation_type_key]
        page, next_cursor = paginate_sequence(rows, lambda row: (row.relation_id,), scope="relations-revision", filters={"revisionId": workspace_revision_id, "objectId": object_id, "direction": direction, "relationTypeKey": relation_type_key}, cursor=cursor, page_size=page_size, sort=("id",), message="Relation cursor is invalid")
        objects = {row.object_id: row for row in session.scalars(select(WorkspaceRevisionObject).where(WorkspaceRevisionObject.revision_id == workspace_revision_id))}
        return RelationPage(items=[RelationExpansion(direction="outgoing" if row.from_object_id == object_id else "incoming", relation=_draft_response(row), object=_draft_object_response(objects[ row.to_object_id if row.from_object_id == object_id else row.from_object_id], workspace_revision_id, snapshot.model).model_copy(update={"workspaceKey": revision.workspace_key})) for row in page if (row.to_object_id if row.from_object_id == object_id else row.from_object_id) in objects], nextCursor=next_cursor)
    anchor = load_active_projection(session, object_id)
    workspace = resolve_workspace(session, workspace_key)
    if anchor.workspace_key != workspace.key:
        raise api_error(404, "object_not_found", "Object not found in the selected workspace")
    clauses = []
    if direction in {"outgoing", "both"}: clauses.append(ObjectRelation.from_object_id == object_id)
    if direction in {"incoming", "both"}: clauses.append(ObjectRelation.to_object_id == object_id)
    from_object, to_object = aliased(RdmObject), aliased(RdmObject)
    statement = select(ObjectRelation).join(from_object, from_object.id == ObjectRelation.from_object_id).join(to_object, to_object.id == ObjectRelation.to_object_id).where(or_(*clauses), from_object.workspace_key == anchor.workspace_key, to_object.workspace_key == anchor.workspace_key)
    if relation_type_key: statement = statement.where(ObjectRelation.relation_type_key == relation_type_key)
    rows, next_cursor = paginate_statement(session, statement, keys=(integer_key("sequenceId", ObjectRelation.sequence_id, "sequence_id"),), scope="relations", filters={"objectId": object_id, "direction": direction, "relationTypeKey": relation_type_key, "workspaceKey": anchor.workspace_key}, cursor=cursor, page_size=page_size, message="Relation cursor is invalid")
    related_ids = [row.to_object_id if row.from_object_id == object_id else row.from_object_id for row in rows]
    related = {item.id: item for item in session.scalars(select(RdmObject).where(RdmObject.id.in_(related_ids)))}
    return RelationPage(items=[RelationExpansion(direction="outgoing" if row.from_object_id == object_id else "incoming", relation=build_relation_response(row), object=build_object_responses(session, snapshot.model, [related[ row.to_object_id if row.from_object_id == object_id else row.from_object_id]])[0]) for row in rows], nextCursor=next_cursor)

@router.get("/relations/{relation_id}", response_model=RelationResponse)
def get_relation(relation_id: str, session: DbSession, snapshot: ActiveModelSnapshot, workspace_draft_id: str | None = Query(default=None, alias="workspaceDraftId"), workspace_revision_id: str | None = Query(default=None, alias="workspaceRevisionId")) -> RelationResponse:
    if workspace_draft_id and workspace_revision_id: raise api_error(422, "mutually_exclusive_context", "Workspace contexts cannot be combined")
    if workspace_draft_id:
        row = next((row for row in effective_draft_membership(session, workspace_draft_id).relations if row.relation_id == relation_id), None)
        if row is None: raise api_error(404, "relation_not_found", "Relation not found")
        return _draft_response(row)
    if workspace_revision_id:
        row = session.scalar(select(WorkspaceRevisionRelation).where(WorkspaceRevisionRelation.revision_id == workspace_revision_id, WorkspaceRevisionRelation.relation_id == relation_id))
        if row is None: raise api_error(404, "relation_not_found", "Relation not found")
        return _draft_response(row)
    row = load_relation(session, relation_id)
    return build_relation_response(row)

@router.patch("/relations/{relation_id}", response_model=RelationResponse)
def update_relation(relation_id: str, payload: RelationUpdate, session: DbSession, snapshot: ActiveModelSnapshot) -> RelationResponse:
    if payload.workspaceDraftId:
        draft = str(payload.workspaceDraftId)
        expected = _ctx(draft, payload.expectedWorkspaceDraftVersion)
        row = update_draft_relation(session, draft, relation_id, WorkspaceDraftRelationUpdate(attributes=payload.attributes, expectedDraftVersion=expected, expectedRecordVersion=payload.expectedVersion))
        return _draft_response(row).model_copy(update={"workspaceDraftVersion": effective_draft_membership(session, draft).draft.version})
    row = update_live_relation(session, snapshot.model, relation_id, payload)
    return build_relation_response(row)

@router.delete("/relations/{relation_id}", status_code=204)
def remove_relation(relation_id: str, session: DbSession, snapshot: ActiveModelSnapshot,
                    workspace_draft_id: str | None = Query(default=None, alias="workspaceDraftId"),
                    expected_workspace_draft_version: int | None = Query(default=None, alias="expectedWorkspaceDraftVersion", ge=1),
                    expected_version: int = Query(alias="expectedVersion", ge=1)) -> Response:
    if workspace_draft_id:
        _ctx(workspace_draft_id, expected_workspace_draft_version)
        delete_draft_relation(session, workspace_draft_id, relation_id, expected_workspace_draft_version, expected_version)
    else:
        delete_live_relation(session, snapshot.model, relation_id, expected_version)
    return Response(status_code=204)
