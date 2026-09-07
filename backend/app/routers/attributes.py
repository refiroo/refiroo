from fastapi import APIRouter, Query, Response, status
from sqlalchemy import select

from ..db import DbSession
from ..errors import api_error
from ..models.api import AttributeValueResponse, AttributeValueWrite, ObjectResponse
from ..models.database import WorkspaceRevision, WorkspaceRevisionObject
from ..services.attributes import build_attribute_value_response, load_attribute_value
from ..services.model.registry import ActiveModelSnapshot
from ..services.objects import get_object_type, load_active_projection
from ..services.workspace_revisions import (
    delete_draft_attribute,
    effective_draft_membership,
    ensure_draft_writable,
    patch_draft_attribute,
)
from .objects import _draft_object_response

router = APIRouter(prefix="/api/v1", tags=["attributes"])
PATH = "/objects/{object_type_key}/{object_id}/attributes/{attribute_type_key}"


@router.get(PATH, response_model=AttributeValueResponse)
def get_attribute_value(object_type_key: str, object_id: str, attribute_type_key: str,
                        session: DbSession, snapshot: ActiveModelSnapshot,
                        workspace_draft_id: str | None = Query(default=None, alias="workspaceDraftId"),
                        workspace_revision_id: str | None = Query(default=None, alias="workspaceRevisionId")) -> AttributeValueResponse:
    if workspace_draft_id and workspace_revision_id:
        raise api_error(422, "mutually_exclusive_context", "workspaceDraftId and workspaceRevisionId cannot be combined")
    get_object_type(snapshot.model, object_type_key)
    if workspace_draft_id:
        membership = effective_draft_membership(session, workspace_draft_id)
        item = next((x for x in membership.objects if x.object_id == object_id and x.object_type_key == object_type_key), None)
        if item is None:
            raise api_error(404, "object_not_found", f"Object '{object_id}' not found")
        if attribute_type_key not in (item.attributes or {}):
            raise api_error(404, "attribute_not_found", f"Attribute '{attribute_type_key}' has no value on object '{object_id}'")
        definition = snapshot.model.attribute_type(attribute_type_key)
        return AttributeValueResponse(id=f"{object_id}:{attribute_type_key}", attributeTypeKey=attribute_type_key,
            name=definition.name if definition else attribute_type_key, valueType=definition.valueType if definition else "text",
            value=item.attributes[attribute_type_key], objectVersion=item.version)
    if workspace_revision_id:
        revision = session.scalar(
            select(WorkspaceRevision).where(WorkspaceRevision.id == workspace_revision_id)
        )
        if revision is None:
            raise api_error(404, "workspace_revision_not_found", "Workspace revision not found")
        item = session.scalar(
            select(WorkspaceRevisionObject).where(
                WorkspaceRevisionObject.revision_id == workspace_revision_id,
                WorkspaceRevisionObject.object_id == object_id,
                WorkspaceRevisionObject.object_type_key == object_type_key,
            )
        )
        if item is None or attribute_type_key not in (item.attributes or {}):
            raise api_error(
                404,
                "attribute_not_found",
                f"Attribute '{attribute_type_key}' has no value on object '{object_id}'",
            )
        definition = snapshot.model.attribute_type(attribute_type_key)
        return AttributeValueResponse(
            id=f"{object_id}:{attribute_type_key}",
            attributeTypeKey=attribute_type_key,
            name=definition.name if definition else attribute_type_key,
            valueType=definition.valueType if definition else "text",
            value=item.attributes[attribute_type_key],
            objectVersion=item.version,
        )
    item = load_active_projection(session, object_id, object_type_key)
    row = load_attribute_value(session, item.id, attribute_type_key)
    return build_attribute_value_response(snapshot.model, row, item.version)


def _write(object_type_key: str, object_id: str, attribute_type_key: str, payload: AttributeValueWrite,
           session, snapshot, *, delete: bool = False, require_absent: bool = False) -> Response | ObjectResponse:
    if not payload.workspaceDraftId or payload.workspaceDraftId is None or payload.expectedWorkspaceDraftVersion is None:
        raise api_error(409, "workspace_draft_required", "workspaceDraftId and expectedWorkspaceDraftVersion are required")
    ensure_draft_writable(session, str(payload.workspaceDraftId))
    membership = effective_draft_membership(session, str(payload.workspaceDraftId))
    item = next((entry for entry in membership.objects if entry.object_id == object_id and entry.object_type_key == object_type_key), None)
    if item is None:
        raise api_error(404, "object_not_found", f"Object '{object_id}' not found")
    present = attribute_type_key in (item.attributes or {})
    if delete:
        if not present:
            raise api_error(404, "attribute_not_found", f"Attribute '{attribute_type_key}' has no value on object '{object_id}'")
        row = delete_draft_attribute(session, str(payload.workspaceDraftId), object_id, attribute_type_key,
                                     payload.expectedWorkspaceDraftVersion, payload.expectedVersion)
    else:
        if require_absent and present:
            raise api_error(409, "attribute_already_exists", f"Attribute '{attribute_type_key}' already has a value on object '{object_id}'")
        if not require_absent and not present:
            raise api_error(404, "attribute_not_found", f"Attribute '{attribute_type_key}' has no value on object '{object_id}'")
        row = patch_draft_attribute(session, str(payload.workspaceDraftId), object_id, attribute_type_key,
                                    payload.value, payload.expectedWorkspaceDraftVersion, payload.expectedVersion)
    if delete:
        return Response(status_code=204)
    draft = effective_draft_membership(session, str(payload.workspaceDraftId)).draft
    return _draft_object_response(row, str(payload.workspaceDraftId), snapshot.model).model_copy(
        update={"workspaceKey": draft.workspace_key, "workspaceDraftVersion": draft.version}
    )


@router.post(PATH, response_model=ObjectResponse, status_code=status.HTTP_201_CREATED)
def create_attribute_value(object_type_key: str, object_id: str, attribute_type_key: str,
                           payload: AttributeValueWrite, session: DbSession, snapshot: ActiveModelSnapshot):
    return _write(object_type_key, object_id, attribute_type_key, payload, session, snapshot, require_absent=True)


@router.patch(PATH, response_model=ObjectResponse)
def update_attribute_value(object_type_key: str, object_id: str, attribute_type_key: str,
                           payload: AttributeValueWrite, session: DbSession, snapshot: ActiveModelSnapshot):
    return _write(object_type_key, object_id, attribute_type_key, payload, session, snapshot)


@router.delete(PATH, status_code=204)
def remove_attribute_value(object_type_key: str, object_id: str, attribute_type_key: str,
                           session: DbSession, snapshot: ActiveModelSnapshot,
                           workspace_draft_id: str | None = Query(default=None, alias="workspaceDraftId"),
                           expected_workspace_draft_version: int | None = Query(default=None, alias="expectedWorkspaceDraftVersion", ge=1),
                           expected_version: int = Query(ge=1, alias="expectedVersion")):
    payload = AttributeValueWrite(value=None, expectedVersion=expected_version,
                                  workspaceDraftId=workspace_draft_id,
                                  expectedWorkspaceDraftVersion=expected_workspace_draft_version)
    return _write(object_type_key, object_id, attribute_type_key, payload, session, snapshot, delete=True)
