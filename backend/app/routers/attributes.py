from fastapi import APIRouter, Query, Response, status

from ..db import SessionLocal
from ..models.api import AttributeValueResponse, AttributeValueWrite, ObjectResponse
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
from ..services.audit import record_audit_event
from ..services.model_registry import ActiveModelSnapshot
from ..services.objects import (
    build_object_responses,
    claim_object_version,
    get_object_type,
    load_object,
)
from ..services.relations import validate_scoped_relations_for_subtree

router = APIRouter(prefix="/api/v1", tags=["attributes"])


def _record_attribute_change(session, item, attribute_type_key: str, value) -> None:
    record_audit_event(
        session,
        aggregate_type="object",
        aggregate_id=item.id,
        action="updated",
        version=item.version,
        changes={"attributes": {attribute_type_key: value}},
        object_ids=[item.id],
    )


@router.get(
    "/objects/{object_type_key}/{object_id}/attributes/{attribute_type_key}",
    response_model=AttributeValueResponse,
)
def get_attribute_value(
    object_type_key: str,
    object_id: str,
    attribute_type_key: str,
    snapshot: ActiveModelSnapshot,
) -> AttributeValueResponse:
    model = snapshot.model
    get_object_type(model, object_type_key)
    with SessionLocal() as session:
        item = load_object(session, object_id, object_type_key)
        row = load_attribute_value(session, item.id, attribute_type_key)
        return build_attribute_value_response(model, row, item.version)


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
    snapshot: ActiveModelSnapshot,
) -> ObjectResponse:
    model = snapshot.model
    object_type = get_object_type(model, object_type_key)
    with SessionLocal() as session:
        item = load_object(session, object_id, object_type_key)
        claim_object_version(session, item, payload.expectedVersion)
        ensure_attribute_value_absent(session, item.id, attribute_type_key)
        attributes = validate_attributes(
            model, object_type, {attribute_type_key: payload.value}, partial=True
        )
        merged_attributes = current_attribute_values(session, item.id)
        merged_attributes.update(attributes)
        validate_object_attribute_rules(object_type, merged_attributes)
        check_attribute_uniqueness(
            session,
            model,
            attributes,
            workspace_key=item.workspace_key,
            exclude_object_id=item.id,
        )
        save_attribute_values(session, model, item.id, attributes)
        validate_scoped_relations_for_subtree(session, model, item)
        _record_attribute_change(session, item, attribute_type_key, attributes[attribute_type_key])
        session.commit()
        session.refresh(item)
        return build_object_responses(session, model, [item])[0]


@router.patch(
    "/objects/{object_type_key}/{object_id}/attributes/{attribute_type_key}",
    response_model=ObjectResponse,
)
def update_attribute_value(
    object_type_key: str,
    object_id: str,
    attribute_type_key: str,
    payload: AttributeValueWrite,
    snapshot: ActiveModelSnapshot,
) -> ObjectResponse:
    model = snapshot.model
    object_type = get_object_type(model, object_type_key)
    with SessionLocal() as session:
        item = load_object(session, object_id, object_type_key)
        claim_object_version(session, item, payload.expectedVersion)
        load_attribute_value(session, item.id, attribute_type_key)
        attributes = validate_attributes(
            model, object_type, {attribute_type_key: payload.value}, partial=True
        )
        merged_attributes = current_attribute_values(session, item.id)
        merged_attributes.update(attributes)
        validate_object_attribute_rules(object_type, merged_attributes)
        check_attribute_uniqueness(
            session,
            model,
            attributes,
            workspace_key=item.workspace_key,
            exclude_object_id=item.id,
        )
        save_attribute_values(session, model, item.id, attributes)
        validate_scoped_relations_for_subtree(session, model, item)
        _record_attribute_change(session, item, attribute_type_key, attributes[attribute_type_key])
        session.commit()
        session.refresh(item)
        return build_object_responses(session, model, [item])[0]


@router.delete(
    "/objects/{object_type_key}/{object_id}/attributes/{attribute_type_key}",
    status_code=204,
)
def delete_attribute_value(
    object_type_key: str,
    object_id: str,
    attribute_type_key: str,
    snapshot: ActiveModelSnapshot,
    expected_version: int = Query(ge=1, alias="expectedVersion"),
):
    model = snapshot.model
    object_type = get_object_type(model, object_type_key)
    with SessionLocal() as session:
        item = load_object(session, object_id, object_type_key)
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
