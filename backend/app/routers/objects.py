from typing import Any

from fastapi import APIRouter, HTTPException, Query, Response, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy import delete, or_, select

from ..db import SessionLocal
from ..models.api import ObjectCreate, ObjectPage, ObjectResponse, ObjectUpdate
from ..models.database import AttributeValue, AuditEvent, ObjectRelation, RdmObject
from ..services.attributes import save_attribute_values, validate_attributes
from ..services.model_loader import current_model
from ..services.objects import (
    build_object_responses,
    get_object_type,
    load_object,
    replace_parent_relation,
    validate_application_object_type,
    validate_parent,
)

router = APIRouter(prefix="/api/v1", tags=["objects"])


@router.get("/objects/{object_type_key}", response_model=ObjectPage)
def list_objects(
    object_type_key: str,
    cursor: int | None = Query(default=None, ge=1),
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
    application_key: str | None = Query(default=None, alias="applicationKey"),
    workspace_key: str = Query(default="default", alias="workspaceKey"),
    parent_object_id: str | None = Query(default=None, alias="parentObjectId"),
    state_filter: str | None = Query(default=None, alias="state"),
    search: str | None = None,
) -> ObjectPage:
    object_type = get_object_type(object_type_key)
    if application_key:
        validate_application_object_type(application_key, object_type_key)

    with SessionLocal() as session:
        statement = select(RdmObject).where(
            RdmObject.object_type_key == object_type_key,
            RdmObject.workspace_key == workspace_key,
        )
        if application_key:
            statement = statement.where(RdmObject.application_key == application_key)
        if parent_object_id:
            statement = statement.where(RdmObject.parent_object_id == parent_object_id)
        if state_filter:
            statement = statement.where(RdmObject.state == state_filter)
        if cursor is not None:
            statement = statement.where(RdmObject.sequence_id > cursor)
        if search:
            escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            searchable_attributes = [
                binding.attributeTypeKey
                for binding in object_type.attributes
                if current_model()
                .attribute_type(binding.attributeTypeKey)
                .features.get("searchable")
            ]
            attribute_match = select(AttributeValue.object_id).where(
                AttributeValue.attribute_type_key.in_(searchable_attributes),
                AttributeValue.text_value.ilike(f"%{escaped}%", escape="\\"),
            )
            statement = statement.where(
                or_(
                    RdmObject.name.ilike(f"%{escaped}%", escape="\\"),
                    RdmObject.id.in_(attribute_match),
                )
            )

        objects = list(
            session.scalars(statement.order_by(RdmObject.sequence_id).limit(page_size + 1))
        )
        has_more = len(objects) > page_size
        visible = objects[:page_size]
        next_cursor = str(visible[-1].sequence_id) if has_more else None
        return ObjectPage(items=build_object_responses(session, visible), nextCursor=next_cursor)


@router.post(
    "/objects/{object_type_key}",
    response_model=ObjectResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_object(object_type_key: str, payload: ObjectCreate) -> ObjectResponse:
    object_type = get_object_type(object_type_key)
    validate_application_object_type(payload.applicationKey, object_type_key)
    attributes = validate_attributes(current_model(), object_type, payload.attributes)

    with SessionLocal() as session:
        parent, parent_relation = validate_parent(
            session,
            object_type_key,
            payload.applicationKey,
            payload.workspaceKey,
            payload.parentObjectId,
        )
        item = RdmObject(
            workspace_key=payload.workspaceKey,
            application_key=payload.applicationKey,
            object_type_key=object_type_key,
            parent_object_id=parent.id if parent else None,
            state=payload.state,
            name=payload.name,
        )
        session.add(item)
        session.flush()
        save_attribute_values(session, current_model(), item.id, attributes)
        if parent and parent_relation:
            session.add(
                ObjectRelation(
                    relation_type_key=parent_relation,
                    from_object_id=parent.id,
                    to_object_id=item.id,
                )
            )
        session.add(
            AuditEvent(
                aggregate_type="object",
                aggregate_id=item.id,
                action="created",
                version=1,
                changes=jsonable_encoder(
                    {"objectTypeKey": object_type_key, "attributes": attributes}
                ),
            )
        )
        session.commit()
        session.refresh(item)
        return build_object_responses(session, [item])[0]


@router.get("/objects/{object_type_key}/{object_id}", response_model=ObjectResponse)
def get_object(object_type_key: str, object_id: str) -> ObjectResponse:
    get_object_type(object_type_key)
    with SessionLocal() as session:
        item = load_object(session, object_id, object_type_key)
        return build_object_responses(session, [item])[0]


@router.patch("/objects/{object_type_key}/{object_id}", response_model=ObjectResponse)
def update_object(object_type_key: str, object_id: str, payload: ObjectUpdate) -> ObjectResponse:
    object_type = get_object_type(object_type_key)
    attributes = (
        validate_attributes(current_model(), object_type, payload.attributes, partial=True)
        if payload.attributes is not None
        else None
    )

    with SessionLocal() as session:
        item = load_object(session, object_id, object_type_key)
        if item.version != payload.expectedVersion:
            raise HTTPException(status_code=409, detail="Object version has changed")

        changes: dict[str, Any] = {}
        if payload.name is not None:
            changes["name"] = {"from": item.name, "to": payload.name}
            item.name = payload.name
        if payload.state is not None:
            changes["state"] = {"from": item.state, "to": payload.state}
            item.state = payload.state
        if "parentObjectId" in payload.model_fields_set:
            old_parent = item.parent_object_id
            parent, parent_relation = validate_parent(
                session,
                object_type_key,
                item.application_key,
                item.workspace_key,
                payload.parentObjectId,
                moving_object_id=item.id,
            )
            replace_parent_relation(session, item, parent, parent_relation)
            changes["parentObjectId"] = {
                "from": old_parent,
                "to": parent.id if parent else None,
            }
        if attributes is not None:
            save_attribute_values(session, current_model(), item.id, attributes)
            changes["attributes"] = attributes

        item.version += 1
        session.add(
            AuditEvent(
                aggregate_type="object",
                aggregate_id=item.id,
                action="updated",
                version=item.version,
                changes=jsonable_encoder(changes),
            )
        )
        session.commit()
        session.refresh(item)
        return build_object_responses(session, [item])[0]


@router.delete("/objects/{object_type_key}/{object_id}", status_code=204)
def delete_object(
    object_type_key: str,
    object_id: str,
    expected_version: int = Query(alias="expectedVersion"),
):
    get_object_type(object_type_key)
    with SessionLocal() as session:
        item = load_object(session, object_id, object_type_key)
        if item.version != expected_version:
            raise HTTPException(status_code=409, detail="Object version has changed")
        has_child = session.scalar(
            select(RdmObject.id).where(RdmObject.parent_object_id == item.id).limit(1)
        )
        has_relation = session.scalar(
            select(ObjectRelation.id)
            .where(
                or_(
                    ObjectRelation.from_object_id == item.id,
                    ObjectRelation.to_object_id == item.id,
                )
            )
            .limit(1)
        )
        if has_child or has_relation:
            raise HTTPException(
                status_code=409,
                detail="Remove child objects and relations before deleting this object",
            )
        session.add(
            AuditEvent(
                aggregate_type="object",
                aggregate_id=item.id,
                action="deleted",
                version=item.version,
                changes=jsonable_encoder({"objectTypeKey": object_type_key}),
            )
        )
        session.execute(delete(AttributeValue).where(AttributeValue.object_id == item.id))
        session.delete(item)
        session.commit()
        return Response(status_code=204)
