from typing import Any

from fastapi import APIRouter, Query, Response, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError

from ..db import SessionLocal
from ..errors import api_error
from ..models.api import ObjectCreate, ObjectPage, ObjectResponse, ObjectUpdate, RelationCreate
from ..models.database import AttributeValue, AuditEvent, ObjectRelation, RdmObject
from ..services.attributes import (
    check_attribute_uniqueness,
    current_attribute_values,
    save_attribute_values,
    validate_attributes,
    validate_object_attribute_rules,
)
from ..services.deletion import build_delete_plan, delete_plan_details, execute_delete_plan
from ..services.model_registry import ActiveModelSnapshot
from ..services.objects import (
    build_object_responses,
    claim_object_version,
    get_object_type,
    load_object,
    replace_parent_relation,
    validate_application_object_type,
    validate_parent,
)
from ..services.relations import create_relation_instance, validate_scoped_relations_for_subtree

router = APIRouter(prefix="/api/v1", tags=["objects"])


def _attributes_to_dict(attributes: list) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for item in attributes:
        if item.attributeTypeKey in result:
            raise api_error(
                422,
                "duplicate_attribute",
                f"Attribute '{item.attributeTypeKey}' occurs more than once",
            )
        result[item.attributeTypeKey] = item.value
    return result


@router.get("/objects/{object_type_key}", response_model=ObjectPage)
def list_objects(
    object_type_key: str,
    snapshot: ActiveModelSnapshot,
    cursor: int | None = Query(default=None, ge=1),
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
    application_key: str | None = Query(default=None, alias="applicationKey"),
    workspace_key: str = Query(default="default", alias="workspaceKey"),
    parent_object_id: str | None = Query(default=None, alias="parentObjectId"),
    state_filter: str | None = Query(default=None, alias="state"),
    search: str | None = None,
) -> ObjectPage:
    model = snapshot.model
    object_type = get_object_type(model, object_type_key)
    if application_key:
        validate_application_object_type(model, application_key, object_type_key)

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
                if model.attribute_type(binding.attributeTypeKey).features.get("searchable")
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
        return ObjectPage(
            items=build_object_responses(session, model, visible), nextCursor=next_cursor
        )


@router.post(
    "/objects",
    response_model=ObjectResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_object(payload: ObjectCreate, snapshot: ActiveModelSnapshot) -> ObjectResponse:
    model = snapshot.model
    object_type_key = payload.objectTypeKey
    object_type = get_object_type(model, object_type_key)
    validate_application_object_type(model, payload.applicationKey, object_type_key)
    attributes = validate_attributes(model, object_type, _attributes_to_dict(payload.attributes))
    validate_object_attribute_rules(object_type, attributes)
    required_relation_keys = {
        allowed.relationTypeKey
        for allowed in model.objectTypeRelations
        if allowed.toObjectTypeKey == object_type_key
        and allowed.required
        and allowed.relationTypeKey
        not in set(object_type.behavior.get("parentRelationTypeKeys", []))
    }
    provided_required_keys = {
        relation.relationTypeKey
        for relation in payload.initialRelations
        if relation.direction == "incoming"
    }
    missing_relation_keys = required_relation_keys - provided_required_keys
    if missing_relation_keys:
        raise api_error(
            422,
            "missing_required_relations",
            f"Required relationships missing: {sorted(missing_relation_keys)}",
            {"relationTypeKeys": sorted(missing_relation_keys)},
        )

    with SessionLocal() as session:
        public_id = str(payload.id) if payload.id is not None else None
        if public_id is not None:
            existing = session.scalar(select(RdmObject.id).where(RdmObject.id == public_id))
            if existing:
                raise api_error(
                    409, "object_already_exists", f"An object with ID '{public_id}' already exists"
                )

        parent, parent_relation = validate_parent(
            session,
            model,
            object_type_key,
            payload.applicationKey,
            payload.workspaceKey,
            str(payload.parentObjectId) if payload.parentObjectId is not None else None,
        )
        check_attribute_uniqueness(session, model, attributes, workspace_key=payload.workspaceKey)
        item = RdmObject(
            workspace_key=payload.workspaceKey,
            application_key=payload.applicationKey,
            object_type_key=object_type_key,
            parent_object_id=parent.id if parent else None,
            state=payload.state,
            name=payload.name,
        )
        if public_id is not None:
            item.id = public_id
        session.add(item)
        session.flush()
        save_attribute_values(session, model, item.id, attributes)
        if parent and parent_relation:
            session.add(
                ObjectRelation(
                    relation_type_key=parent_relation,
                    from_object_id=parent.id,
                    to_object_id=item.id,
                )
            )
        for initial in payload.initialRelations:
            if initial.direction == "outgoing":
                from_id, to_id = item.id, str(initial.otherObjectId)
                from_object, to_object = item, None
            else:
                from_id, to_id = str(initial.otherObjectId), item.id
                from_object, to_object = None, item
            try:
                create_relation_instance(
                    session,
                    model,
                    RelationCreate(
                        relationTypeKey=initial.relationTypeKey,
                        fromObjectId=from_id,
                        toObjectId=to_id,
                        attributes=initial.attributes,
                    ),
                    from_object=from_object,
                    to_object=to_object,
                )
            except IntegrityError:
                session.rollback()
                raise api_error(409, "duplicate_relation", "Relation already exists") from None
        session.add(
            AuditEvent(
                aggregate_type="object",
                aggregate_id=item.id,
                action="created",
                version=1,
                changes=jsonable_encoder(
                    {
                        "objectTypeKey": object_type_key,
                        "attributes": attributes,
                        "initialRelations": [
                            relation.model_dump(mode="json")
                            for relation in payload.initialRelations
                        ],
                    }
                ),
            )
        )
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            raise api_error(409, "duplicate_relation", "Relation already exists") from None
        session.refresh(item)
        return build_object_responses(session, model, [item])[0]


@router.get("/objects/{object_type_key}/{object_id}", response_model=ObjectResponse)
def get_object(
    object_type_key: str, object_id: str, snapshot: ActiveModelSnapshot
) -> ObjectResponse:
    model = snapshot.model
    get_object_type(model, object_type_key)
    with SessionLocal() as session:
        item = load_object(session, object_id, object_type_key)
        return build_object_responses(session, model, [item])[0]


@router.patch("/objects/{object_type_key}/{object_id}", response_model=ObjectResponse)
def update_object(
    object_type_key: str,
    object_id: str,
    payload: ObjectUpdate,
    snapshot: ActiveModelSnapshot,
) -> ObjectResponse:
    model = snapshot.model
    object_type = get_object_type(model, object_type_key)
    attributes = (
        validate_attributes(
            model, object_type, _attributes_to_dict(payload.attributes), partial=True
        )
        if payload.attributes is not None
        else None
    )

    with SessionLocal() as session:
        item = load_object(session, object_id, object_type_key)
        claim_object_version(session, item, payload.expectedVersion)

        if attributes is not None:
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
                model,
                object_type_key,
                item.application_key,
                item.workspace_key,
                str(payload.parentObjectId) if payload.parentObjectId is not None else None,
                moving_object_id=item.id,
            )
            replace_parent_relation(session, model, item, parent, parent_relation)
            changes["parentObjectId"] = {
                "from": old_parent,
                "to": parent.id if parent else None,
            }
        if attributes is not None:
            save_attribute_values(session, model, item.id, attributes)
            changes["attributes"] = attributes

        validate_scoped_relations_for_subtree(session, model, item)

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
        return build_object_responses(session, model, [item])[0]


@router.delete("/objects/{object_type_key}/{object_id}", status_code=204)
def delete_object(
    object_type_key: str,
    object_id: str,
    snapshot: ActiveModelSnapshot,
    expected_version: int = Query(ge=1, alias="expectedVersion"),
    cascade: bool = False,
) -> Response:
    model = snapshot.model
    get_object_type(model, object_type_key)
    with SessionLocal() as session:
        item = load_object(session, object_id, object_type_key)
        claim_object_version(session, item, expected_version)
        plan = build_delete_plan(session, model, item, cascade=True)
        if plan.has_dependents and not cascade:
            raise api_error(
                409,
                "object_has_dependents",
                "Deleting this object requires cascade confirmation",
                delete_plan_details(session, model, plan),
            )
        execute_delete_plan(session, plan)
        session.commit()
        return Response(status_code=204)
