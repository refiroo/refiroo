from typing import Any

from fastapi import APIRouter, Query, Response, status
from sqlalchemy.orm import Session

from ..db import DbSession
from ..models.api import AttributeValueResponse, AttributeValueWrite, ObjectResponse
from ..models.database import RdmObject
from ..models.schema import EngineModel
from ..services.attributes import (
    apply_attribute_values,
    build_attribute_value_response,
    current_attribute_values,
    ensure_attribute_value_absent,
    load_attribute_value,
    validate_attributes,
    validate_deletable_attribute,
    validate_object_attribute_rules,
)
from ..services.audit import record_audit_event
from ..services.model.registry import ActiveModelSnapshot
from ..services.objects import (
    build_object_responses,
    claim_object_version,
    get_object_type,
    load_object,
)
from ..services.relations import validate_scoped_relations_for_subtree
from ..services.workspaces import resolve_workspace

router = APIRouter(prefix="/api/v1", tags=["attributes"])

ATTRIBUTE_VALUE_PATH = "/objects/{object_type_key}/{object_id}/attributes/{attribute_type_key}"


def _record_attribute_change(
    session: Session, item: RdmObject, attribute_type_key: str, value: Any
) -> None:
    record_audit_event(
        session,
        aggregate_type="object",
        aggregate_id=item.id,
        action="updated",
        version=item.version,
        changes={"attributes": {attribute_type_key: value}},
        object_ids=[item.id],
    )


def _write_attribute_value(
    session: Session,
    model: EngineModel,
    object_type_key: str,
    object_id: str,
    attribute_type_key: str,
    payload: AttributeValueWrite,
    *,
    require_absent: bool,
) -> ObjectResponse:
    """Shared write path for creating and replacing a single attribute value."""
    object_type = get_object_type(model, object_type_key)
    item = load_object(session, object_id, object_type_key)
    resolve_workspace(session, item.workspace_key, require_active=True)
    claim_object_version(session, item, payload.expectedVersion)
    if require_absent:
        ensure_attribute_value_absent(session, item.id, attribute_type_key)
    else:
        load_attribute_value(session, item.id, attribute_type_key)
    attributes = validate_attributes(
        model, object_type, {attribute_type_key: payload.value}, partial=True
    )
    apply_attribute_values(session, model, object_type, item, attributes)
    _record_attribute_change(session, item, attribute_type_key, attributes[attribute_type_key])
    session.commit()
    session.refresh(item)
    return build_object_responses(session, model, [item])[0]


@router.get(ATTRIBUTE_VALUE_PATH, response_model=AttributeValueResponse)
def get_attribute_value(
    object_type_key: str,
    object_id: str,
    attribute_type_key: str,
    session: DbSession,
    snapshot: ActiveModelSnapshot,
) -> AttributeValueResponse:
    model = snapshot.model
    get_object_type(model, object_type_key)
    item = load_object(session, object_id, object_type_key)
    row = load_attribute_value(session, item.id, attribute_type_key)
    return build_attribute_value_response(model, row, item.version)


@router.post(
    ATTRIBUTE_VALUE_PATH,
    response_model=ObjectResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_attribute_value(
    object_type_key: str,
    object_id: str,
    attribute_type_key: str,
    payload: AttributeValueWrite,
    session: DbSession,
    snapshot: ActiveModelSnapshot,
) -> ObjectResponse:
    return _write_attribute_value(
        session,
        snapshot.model,
        object_type_key,
        object_id,
        attribute_type_key,
        payload,
        require_absent=True,
    )


@router.patch(ATTRIBUTE_VALUE_PATH, response_model=ObjectResponse)
def update_attribute_value(
    object_type_key: str,
    object_id: str,
    attribute_type_key: str,
    payload: AttributeValueWrite,
    session: DbSession,
    snapshot: ActiveModelSnapshot,
) -> ObjectResponse:
    return _write_attribute_value(
        session,
        snapshot.model,
        object_type_key,
        object_id,
        attribute_type_key,
        payload,
        require_absent=False,
    )


@router.delete(ATTRIBUTE_VALUE_PATH, status_code=204)
def delete_attribute_value(
    object_type_key: str,
    object_id: str,
    attribute_type_key: str,
    session: DbSession,
    snapshot: ActiveModelSnapshot,
    expected_version: int = Query(ge=1, alias="expectedVersion"),
) -> Response:
    model = snapshot.model
    object_type = get_object_type(model, object_type_key)
    item = load_object(session, object_id, object_type_key)
    resolve_workspace(session, item.workspace_key, require_active=True)
    claim_object_version(session, item, expected_version)
    row = load_attribute_value(session, item.id, attribute_type_key)
    validate_deletable_attribute(object_type, attribute_type_key)
    remaining_attributes = current_attribute_values(session, item.id)
    remaining_attributes.pop(attribute_type_key, None)
    validate_object_attribute_rules(object_type, remaining_attributes)
    session.delete(row)
    validate_scoped_relations_for_subtree(session, model, item)
    _record_attribute_change(session, item, attribute_type_key, None)
    session.commit()
    return Response(status_code=204)
