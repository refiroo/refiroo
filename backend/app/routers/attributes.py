from fastapi import APIRouter, Query, Response, status
from fastapi.encoders import jsonable_encoder

from ..db import SessionLocal
from ..models.api import AttributeValueResponse, AttributeValueWrite, ObjectResponse
from ..models.database import AuditEvent
from ..services.attributes import (
    build_attribute_value_response,
    check_attribute_uniqueness,
    current_attribute_values,
    ensure_attribute_value_absent,
    load_attribute_value,
    save_attribute_values,
    validate_attributes,
    validate_deletable_attribute,
    validate_object_attribute_rules,
)
from ..services.model_loader import current_model
from ..services.objects import (
    build_object_responses,
    claim_object_version,
    get_object_type,
    load_object,
)
from ..services.relations import validate_scoped_relations_for_subtree

router = APIRouter(prefix="/api/v1", tags=["attributes"])


def _record_attribute_change(session, item, attribute_type_key: str, value) -> None:
    session.add(
        AuditEvent(
            aggregate_type="object",
            aggregate_id=item.id,
            action="updated",
            version=item.version,
            changes=jsonable_encoder({"attributes": {attribute_type_key: value}}),
        )
    )


@router.get(
    "/objects/{object_type_key}/{object_id}/attributes/{attribute_type_key}",
    response_model=AttributeValueResponse,
)
def get_attribute_value(
    object_type_key: str, object_id: str, attribute_type_key: str
) -> AttributeValueResponse:
    get_object_type(object_type_key)
    with SessionLocal() as session:
        item = load_object(session, object_id, object_type_key)
        row = load_attribute_value(session, item.id, attribute_type_key)
        return build_attribute_value_response(current_model(), row, item.version)


@router.post(
    "/objects/{object_type_key}/{object_id}/attributes/{attribute_type_key}",
    response_model=ObjectResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_attribute_value(
    object_type_key: str,
    object_id: str,
    attribute_type_key: str,
    payload: AttributeValueWrite,
) -> ObjectResponse:
    object_type = get_object_type(object_type_key)
    with SessionLocal() as session:
        item = load_object(session, object_id, object_type_key)
        claim_object_version(session, item, payload.expectedVersion)
        ensure_attribute_value_absent(session, item.id, attribute_type_key)
        attributes = validate_attributes(
            current_model(), object_type, {attribute_type_key: payload.value}, partial=True
        )
        merged_attributes = current_attribute_values(session, item.id)
        merged_attributes.update(attributes)
        validate_object_attribute_rules(object_type, merged_attributes)
        check_attribute_uniqueness(
            session,
            current_model(),
            attributes,
            workspace_key=item.workspace_key,
            exclude_object_id=item.id,
        )
        save_attribute_values(session, current_model(), item.id, attributes)
        validate_scoped_relations_for_subtree(session, item)
        _record_attribute_change(session, item, attribute_type_key, attributes[attribute_type_key])
        session.commit()
        session.refresh(item)
        return build_object_responses(session, [item])[0]


@router.patch(
    "/objects/{object_type_key}/{object_id}/attributes/{attribute_type_key}",
    response_model=ObjectResponse,
)
def update_attribute_value(
    object_type_key: str,
    object_id: str,
    attribute_type_key: str,
    payload: AttributeValueWrite,
) -> ObjectResponse:
    object_type = get_object_type(object_type_key)
    with SessionLocal() as session:
        item = load_object(session, object_id, object_type_key)
        claim_object_version(session, item, payload.expectedVersion)
        load_attribute_value(session, item.id, attribute_type_key)
        attributes = validate_attributes(
            current_model(), object_type, {attribute_type_key: payload.value}, partial=True
        )
        merged_attributes = current_attribute_values(session, item.id)
        merged_attributes.update(attributes)
        validate_object_attribute_rules(object_type, merged_attributes)
        check_attribute_uniqueness(
            session,
            current_model(),
            attributes,
            workspace_key=item.workspace_key,
            exclude_object_id=item.id,
        )
        save_attribute_values(session, current_model(), item.id, attributes)
        validate_scoped_relations_for_subtree(session, item)
        _record_attribute_change(session, item, attribute_type_key, attributes[attribute_type_key])
        session.commit()
        session.refresh(item)
        return build_object_responses(session, [item])[0]


@router.delete(
    "/objects/{object_type_key}/{object_id}/attributes/{attribute_type_key}",
    status_code=204,
)
def delete_attribute_value(
    object_type_key: str,
    object_id: str,
    attribute_type_key: str,
    expected_version: int = Query(ge=1, alias="expectedVersion"),
):
    object_type = get_object_type(object_type_key)
    with SessionLocal() as session:
        item = load_object(session, object_id, object_type_key)
        claim_object_version(session, item, expected_version)
        row = load_attribute_value(session, item.id, attribute_type_key)
        validate_deletable_attribute(object_type, attribute_type_key)
        remaining_attributes = current_attribute_values(session, item.id)
        remaining_attributes.pop(attribute_type_key, None)
        validate_object_attribute_rules(object_type, remaining_attributes)
        session.delete(row)
        validate_scoped_relations_for_subtree(session, item)
        _record_attribute_change(session, item, attribute_type_key, None)
        session.commit()
        return Response(status_code=204)
