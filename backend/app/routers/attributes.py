from fastapi import APIRouter, Query, Response, status

from ..db import DbSession
from ..errors import api_error
from ..models.api import AttributeValueResponse, AttributeValueWrite, ObjectResponse
from ..services.attributes import build_attribute_value_response, load_attribute_value
from ..services.change_sets import (
    delete_change_set_attribute,
    ensure_change_set_writable,
    patch_change_set_attribute,
)
from ..services.model.registry import (
    RequestModelSnapshot,
    resolve_change_set_snapshot,
    resolve_model_snapshot,
)
from ..services.objects import (
    build_object_responses,
    delete_live_attribute_value,
    get_object_type,
    load_active_projection,
    set_live_attribute_value,
)
from ..services.snapshot_reads import change_set_context, find_object, publication_context
from .objects import _change_set_object_response

router = APIRouter(prefix="/api/v1", tags=["attributes"])
PATH = "/objects/{object_type_key}/{object_id}/attributes/{attribute_type_key}"


@router.get(PATH, response_model=AttributeValueResponse)
def get_attribute_value(object_type_key: str, object_id: str, attribute_type_key: str,
                        session: DbSession, snapshot: RequestModelSnapshot,
                        change_set_id: str | None = Query(default=None, alias="changeSetId"),
                        publication_id: str | None = Query(default=None, alias="publicationId")) -> AttributeValueResponse:
    if change_set_id and publication_id:
        raise api_error(422, "mutually_exclusive_context", "changeSetId and publicationId cannot be combined")
    get_object_type(snapshot.model, object_type_key)
    if change_set_id or publication_id:
        context = (
            change_set_context(session, change_set_id)
            if change_set_id
            else publication_context(session, publication_id)
        )
        item = find_object(session, context, object_id, object_type_key)
        if item is None and context.kind == "change_set":
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
    if payload.changeSetId:
        change_set_id = str(payload.changeSetId)
        if payload.expectedChangeSetVersion is None:
            raise api_error(409, "change_set_required",
                            "expectedChangeSetVersion is required when targeting a change set")
        ensure_change_set_writable(session, change_set_id)
        context = change_set_context(session, change_set_id)
        item = find_object(session, context, object_id, object_type_key)
        if item is None:
            raise api_error(404, "object_not_found", f"Object '{object_id}' not found")
        present = attribute_type_key in (item.attributes or {})
        if delete:
            if not present:
                raise api_error(404, "attribute_not_found", f"Attribute '{attribute_type_key}' has no value on object '{object_id}'")
            delete_change_set_attribute(session, change_set_id, object_id, attribute_type_key,
                                   payload.expectedChangeSetVersion, payload.expectedVersion)
            return Response(status_code=204)
        if require_absent and present:
            raise api_error(409, "attribute_already_exists", f"Attribute '{attribute_type_key}' already has a value on object '{object_id}'")
        if not require_absent and not present:
            raise api_error(404, "attribute_not_found", f"Attribute '{attribute_type_key}' has no value on object '{object_id}'")
        row = patch_change_set_attribute(session, change_set_id, object_id, attribute_type_key,
                                    payload.value, payload.expectedChangeSetVersion, payload.expectedVersion)
        change_set = change_set_context(session, change_set_id).change_set
        return _change_set_object_response(row, change_set_id, resolve_change_set_snapshot(session, change_set_id).model).model_copy(
            update={"workspaceKey": change_set.workspace_key, "changeSetVersion": change_set.version}
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
                           change_set_id: str | None = Query(default=None, alias="changeSetId"),
                           expected_change_set_version: int | None = Query(default=None, alias="expectedChangeSetVersion", ge=1),
                           expected_version: int = Query(ge=1, alias="expectedVersion")):
    payload = AttributeValueWrite(value=None, expectedVersion=expected_version,
                                  changeSetId=change_set_id,
                                  expectedChangeSetVersion=expected_change_set_version)
    return _write(object_type_key, object_id, attribute_type_key, payload, session, None, delete=True)
