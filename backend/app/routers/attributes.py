from fastapi import APIRouter, Query, Response, status

from ..db import DbSession
from ..errors import api_error
from ..models.api import AttributeValueResponse, AttributeValueWrite, ObjectResponse
from ..services.attributes import build_attribute_value_response, load_attribute_value
from ..services.model.registry import (
    RequestModelSnapshot,
    resolve_draft_snapshot,
    resolve_model_snapshot,
)
from ..services.objects import (
    build_object_responses,
    delete_live_attribute_value,
    get_object_type,
    load_active_projection,
    set_live_attribute_value,
)
from ..services.snapshot_reads import draft_context, find_object, revision_context
from ..services.workspace_revisions import (
    delete_draft_attribute,
    ensure_draft_writable,
    patch_draft_attribute,
)
from .objects import _draft_object_response

router = APIRouter(prefix="/api/v1", tags=["attributes"])
PATH = "/objects/{object_type_key}/{object_id}/attributes/{attribute_type_key}"


@router.get(PATH, response_model=AttributeValueResponse)
def get_attribute_value(object_type_key: str, object_id: str, attribute_type_key: str,
                        session: DbSession, snapshot: RequestModelSnapshot,
                        workspace_draft_id: str | None = Query(default=None, alias="workspaceDraftId"),
                        workspace_revision_id: str | None = Query(default=None, alias="workspaceRevisionId")) -> AttributeValueResponse:
    if workspace_draft_id and workspace_revision_id:
        raise api_error(422, "mutually_exclusive_context", "workspaceDraftId and workspaceRevisionId cannot be combined")
    get_object_type(snapshot.model, object_type_key)
    if workspace_draft_id or workspace_revision_id:
        context = (
            draft_context(session, workspace_draft_id)
            if workspace_draft_id
            else revision_context(session, workspace_revision_id)
        )
        item = find_object(session, context, object_id, object_type_key)
        if item is None and context.kind == "draft":
            raise api_error(404, "object_not_found", f"Object '{object_id}' not found")
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
    if payload.workspaceDraftId:
        draft_id = str(payload.workspaceDraftId)
        if payload.expectedWorkspaceDraftVersion is None:
            raise api_error(409, "workspace_draft_required",
                            "expectedWorkspaceDraftVersion is required when targeting a workspace draft")
        ensure_draft_writable(session, draft_id)
        context = draft_context(session, draft_id)
        item = find_object(session, context, object_id, object_type_key)
        if item is None:
            raise api_error(404, "object_not_found", f"Object '{object_id}' not found")
        present = attribute_type_key in (item.attributes or {})
        if delete:
            if not present:
                raise api_error(404, "attribute_not_found", f"Attribute '{attribute_type_key}' has no value on object '{object_id}'")
            delete_draft_attribute(session, draft_id, object_id, attribute_type_key,
                                   payload.expectedWorkspaceDraftVersion, payload.expectedVersion)
            return Response(status_code=204)
        if require_absent and present:
            raise api_error(409, "attribute_already_exists", f"Attribute '{attribute_type_key}' already has a value on object '{object_id}'")
        if not require_absent and not present:
            raise api_error(404, "attribute_not_found", f"Attribute '{attribute_type_key}' has no value on object '{object_id}'")
        row = patch_draft_attribute(session, draft_id, object_id, attribute_type_key,
                                    payload.value, payload.expectedWorkspaceDraftVersion, payload.expectedVersion)
        draft = draft_context(session, draft_id).draft
        return _draft_object_response(row, draft_id, resolve_draft_snapshot(session, draft_id).model).model_copy(
            update={"workspaceKey": draft.workspace_key, "workspaceDraftVersion": draft.version}
        )
    if delete:
        snapshot = snapshot or resolve_model_snapshot(session)
        delete_live_attribute_value(session, snapshot.model, object_type_key, object_id,
                                    attribute_type_key, payload.expectedVersion)
        return Response(status_code=204)
    snapshot = snapshot or resolve_model_snapshot(session)
    set_live_attribute_value(session, snapshot.model, object_type_key, object_id, attribute_type_key,
                             payload.value, payload.expectedVersion, create_only=require_absent)
    item = load_active_projection(session, object_id, object_type_key)
    return build_object_responses(session, snapshot.model, [item])[0]


@router.post(PATH, response_model=ObjectResponse, status_code=status.HTTP_201_CREATED)
def create_attribute_value(object_type_key: str, object_id: str, attribute_type_key: str,
                           payload: AttributeValueWrite, session: DbSession):
    return _write(object_type_key, object_id, attribute_type_key, payload, session, None, require_absent=True)


@router.patch(PATH, response_model=ObjectResponse)
def update_attribute_value(object_type_key: str, object_id: str, attribute_type_key: str,
                           payload: AttributeValueWrite, session: DbSession):
    return _write(object_type_key, object_id, attribute_type_key, payload, session, None)


@router.delete(PATH, status_code=204)
def remove_attribute_value(object_type_key: str, object_id: str, attribute_type_key: str,
                           session: DbSession,
                           workspace_draft_id: str | None = Query(default=None, alias="workspaceDraftId"),
                           expected_workspace_draft_version: int | None = Query(default=None, alias="expectedWorkspaceDraftVersion", ge=1),
                           expected_version: int = Query(ge=1, alias="expectedVersion")):
    payload = AttributeValueWrite(value=None, expectedVersion=expected_version,
                                  workspaceDraftId=workspace_draft_id,
                                  expectedWorkspaceDraftVersion=expected_workspace_draft_version)
    return _write(object_type_key, object_id, attribute_type_key, payload, session, None, delete=True)
