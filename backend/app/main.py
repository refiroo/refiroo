from contextlib import asynccontextmanager
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Query, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import delete, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .api_models import (
    ObjectCreate,
    ObjectPage,
    ObjectResponse,
    ObjectUpdate,
    RelationCreate,
    RelationExpansion,
    RelationResponse,
)
from .attribute_values import load_attribute_values, save_attribute_values, validate_attributes
from .database import (
    AttributeValue,
    AuditEvent,
    ObjectRelation,
    RdmObject,
    SessionLocal,
    create_database,
    install_model,
)
from .model_loader import current_model


@asynccontextmanager
async def lifespan(_: FastAPI):
    model = current_model()
    create_database()
    install_model(model)
    yield


app = FastAPI(
    title="RDM Engine API",
    version="0.3.0",
    description="API-first, model-driven reference data management engine.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/model")
def get_model() -> dict[str, Any]:
    return current_model().model_dump(mode="json")


@app.get("/api/v1/applications")
def get_applications() -> list[dict[str, Any]]:
    return [item.model_dump(mode="json") for item in current_model().applications]


@app.get("/api/v1/applications/{application_key}")
def get_application(application_key: str) -> dict[str, Any]:
    application = _application_definition(application_key)
    return application.model_dump(mode="json")


@app.get("/api/v1/attribute-types/{attribute_type_key}")
def get_attribute_type(attribute_type_key: str) -> dict[str, Any]:
    definition = current_model().attribute_type(attribute_type_key)
    if not definition:
        raise HTTPException(status_code=404, detail="Unknown attribute type")
    return definition.model_dump(mode="json")


@app.get("/api/v1/object-types/{object_type_key}")
def get_object_type(object_type_key: str) -> dict[str, Any]:
    return _object_type_definition(object_type_key).model_dump(mode="json")


@app.get("/api/v1/relation-types/{relation_type_key}")
def get_relation_type(relation_type_key: str) -> dict[str, Any]:
    definition = current_model().relation_type(relation_type_key)
    if not definition:
        raise HTTPException(status_code=404, detail="Unknown relation type")
    return definition.model_dump(mode="json")


@app.get("/api/v1/object-type-relations")
def get_object_type_relations(
    from_object_type: str | None = Query(default=None, alias="fromObjectType"),
    to_object_type: str | None = Query(default=None, alias="toObjectType"),
) -> list[dict[str, Any]]:
    relations = current_model().objectTypeRelations
    if from_object_type:
        relations = [item for item in relations if item.fromObjectTypeKey == from_object_type]
    if to_object_type:
        relations = [item for item in relations if item.toObjectTypeKey == to_object_type]
    return [item.model_dump(mode="json") for item in relations]


@app.get("/api/v1/objects/{object_type_key}", response_model=ObjectPage)
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
    object_type = _object_type_definition(object_type_key)
    if application_key:
        _validate_application_object_type(application_key, object_type_key)

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
            searchable_attributes = [
                binding.attributeTypeKey
                for binding in object_type.attributes
                if current_model()
                .attribute_type(binding.attributeTypeKey)
                .features.get("searchable")
            ]
            attribute_match = select(AttributeValue.object_id).where(
                AttributeValue.attribute_type_key.in_(searchable_attributes),
                AttributeValue.text_value.ilike(f"%{search}%"),
            )
            statement = statement.where(
                or_(RdmObject.name.ilike(f"%{search}%"), RdmObject.id.in_(attribute_match))
            )

        objects = list(
            session.scalars(statement.order_by(RdmObject.sequence_id).limit(page_size + 1))
        )
        has_more = len(objects) > page_size
        visible = objects[:page_size]
        next_cursor = str(visible[-1].sequence_id) if has_more else None
        return ObjectPage(items=_object_responses(session, visible), nextCursor=next_cursor)


@app.post(
    "/api/v1/objects/{object_type_key}",
    response_model=ObjectResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_object(object_type_key: str, payload: ObjectCreate) -> ObjectResponse:
    object_type = _object_type_definition(object_type_key)
    _validate_application_object_type(payload.applicationKey, object_type_key)
    attributes = validate_attributes(current_model(), object_type, payload.attributes)

    with SessionLocal() as session:
        parent, parent_relation = _validate_parent(
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
        return _object_responses(session, [item])[0]


@app.get("/api/v1/objects/{object_type_key}/{object_id}", response_model=ObjectResponse)
def get_object(object_type_key: str, object_id: str) -> ObjectResponse:
    _object_type_definition(object_type_key)
    with SessionLocal() as session:
        item = _load_object(session, object_id, object_type_key)
        return _object_responses(session, [item])[0]


@app.patch("/api/v1/objects/{object_type_key}/{object_id}", response_model=ObjectResponse)
def update_object(object_type_key: str, object_id: str, payload: ObjectUpdate) -> ObjectResponse:
    object_type = _object_type_definition(object_type_key)
    attributes = (
        validate_attributes(current_model(), object_type, payload.attributes, partial=True)
        if payload.attributes is not None
        else None
    )

    with SessionLocal() as session:
        item = _load_object(session, object_id, object_type_key)
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
            parent, parent_relation = _validate_parent(
                session,
                object_type_key,
                item.application_key,
                item.workspace_key,
                payload.parentObjectId,
                moving_object_id=item.id,
            )
            _replace_parent_relation(session, item, parent, parent_relation)
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
        return _object_responses(session, [item])[0]


@app.delete("/api/v1/objects/{object_type_key}/{object_id}", status_code=204)
def delete_object(
    object_type_key: str,
    object_id: str,
    expected_version: int = Query(alias="expectedVersion"),
):
    _object_type_definition(object_type_key)
    with SessionLocal() as session:
        item = _load_object(session, object_id, object_type_key)
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
        session.execute(delete(AttributeValue).where(AttributeValue.object_id == item.id))
        session.delete(item)
        session.commit()
        return Response(status_code=204)


@app.post(
    "/api/v1/relations",
    response_model=RelationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_relation(payload: RelationCreate) -> RelationResponse:
    with SessionLocal() as session:
        from_object = _load_object(session, payload.fromObjectId)
        to_object = _load_object(session, payload.toObjectId)
        allowed = _allowed_relation(
            payload.relationTypeKey,
            from_object.object_type_key,
            to_object.object_type_key,
        )
        _validate_cardinality(session, allowed, payload)
        relation = ObjectRelation(
            relation_type_key=payload.relationTypeKey,
            from_object_id=payload.fromObjectId,
            to_object_id=payload.toObjectId,
            attributes=payload.attributes,
        )
        session.add(relation)
        session.flush()
        session.add(
            AuditEvent(
                aggregate_type="relation",
                aggregate_id=relation.id,
                action="created",
                version=1,
                changes=jsonable_encoder(payload.model_dump()),
            )
        )
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            raise HTTPException(status_code=409, detail="Relation already exists") from None
        session.refresh(relation)
        return _relation_response(relation)


@app.get("/api/v1/relations", response_model=list[RelationExpansion])
def get_relations(
    object_id: str = Query(alias="objectId"),
    direction: Literal["outgoing", "incoming", "both"] = "both",
    relation_type_key: str | None = Query(default=None, alias="relationTypeKey"),
) -> list[RelationExpansion]:
    with SessionLocal() as session:
        _load_object(session, object_id)
        clauses = []
        if direction in {"outgoing", "both"}:
            clauses.append(ObjectRelation.from_object_id == object_id)
        if direction in {"incoming", "both"}:
            clauses.append(ObjectRelation.to_object_id == object_id)
        statement = select(ObjectRelation).where(or_(*clauses))
        if relation_type_key:
            statement = statement.where(ObjectRelation.relation_type_key == relation_type_key)
        relations = list(session.scalars(statement.order_by(ObjectRelation.sequence_id)))
        related_ids = [
            relation.to_object_id
            if relation.from_object_id == object_id
            else relation.from_object_id
            for relation in relations
        ]
        related_objects = {
            item.id: item
            for item in session.scalars(select(RdmObject).where(RdmObject.id.in_(related_ids)))
        }
        responses = {
            item.id: response
            for item, response in zip(
                related_objects.values(),
                _object_responses(session, list(related_objects.values())),
                strict=True,
            )
        }
        return [
            RelationExpansion(
                direction="outgoing" if relation.from_object_id == object_id else "incoming",
                relation=_relation_response(relation),
                object=responses[
                    relation.to_object_id
                    if relation.from_object_id == object_id
                    else relation.from_object_id
                ],
            )
            for relation in relations
        ]


def _application_definition(application_key: str):
    application = next(
        (item for item in current_model().applications if item.key == application_key), None
    )
    if not application:
        raise HTTPException(status_code=404, detail="Unknown application")
    return application


def _object_type_definition(object_type_key: str):
    definition = current_model().object_type(object_type_key)
    if not definition:
        raise HTTPException(status_code=404, detail="Unknown object type")
    return definition


def _validate_application_object_type(application_key: str, object_type_key: str) -> None:
    application = _application_definition(application_key)
    if object_type_key not in application.objectTypeKeys:
        raise HTTPException(
            status_code=422,
            detail=f"Object type '{object_type_key}' is not available in '{application_key}'",
        )


def _load_object(session: Session, object_id: str, object_type_key: str | None = None) -> RdmObject:
    statement = select(RdmObject).where(RdmObject.id == object_id)
    if object_type_key:
        statement = statement.where(RdmObject.object_type_key == object_type_key)
    item = session.scalar(statement)
    if not item:
        raise HTTPException(status_code=404, detail="Object not found")
    return item


def _validate_parent(
    session: Session,
    object_type_key: str,
    application_key: str,
    workspace_key: str,
    parent_object_id: str | None,
    moving_object_id: str | None = None,
) -> tuple[RdmObject | None, str | None]:
    object_type = _object_type_definition(object_type_key)
    root_creatable = object_type.features.get("rootCreatable", False)
    if parent_object_id is None:
        if not root_creatable:
            raise HTTPException(status_code=422, detail="This object type requires a parent")
        return None, None

    parent = _load_object(session, parent_object_id)
    if parent.application_key != application_key or parent.workspace_key != workspace_key:
        raise HTTPException(
            status_code=422, detail="Parent must be in the same application and workspace"
        )
    if moving_object_id and _would_create_parent_cycle(session, moving_object_id, parent.id):
        raise HTTPException(status_code=422, detail="Parent selection would create a cycle")

    permitted = set(object_type.behavior.get("parentRelationTypeKeys", []))
    matches = [
        relation
        for relation in current_model().objectTypeRelations
        if relation.relationTypeKey in permitted
        and relation.fromObjectTypeKey == parent.object_type_key
        and relation.toObjectTypeKey == object_type_key
    ]
    if len(matches) != 1:
        raise HTTPException(
            status_code=422, detail="Parent type is not permitted for this object type"
        )
    return parent, matches[0].relationTypeKey


def _replace_parent_relation(
    session: Session,
    item: RdmObject,
    parent: RdmObject | None,
    parent_relation: str | None,
) -> None:
    parent_relation_types = set(
        _object_type_definition(item.object_type_key).behavior.get("parentRelationTypeKeys", [])
    )
    session.execute(
        delete(ObjectRelation).where(
            ObjectRelation.to_object_id == item.id,
            ObjectRelation.relation_type_key.in_(parent_relation_types),
        )
    )
    item.parent_object_id = parent.id if parent else None
    if parent and parent_relation:
        session.add(
            ObjectRelation(
                relation_type_key=parent_relation,
                from_object_id=parent.id,
                to_object_id=item.id,
            )
        )


def _would_create_parent_cycle(session: Session, object_id: str, parent_id: str) -> bool:
    current_id: str | None = parent_id
    visited: set[str] = set()
    while current_id:
        if current_id == object_id or current_id in visited:
            return True
        visited.add(current_id)
        current_id = session.scalar(
            select(RdmObject.parent_object_id).where(RdmObject.id == current_id)
        )
    return False


def _allowed_relation(relation_type_key: str, from_type: str, to_type: str):
    relation_type = current_model().relation_type(relation_type_key)
    if not relation_type:
        raise HTTPException(status_code=404, detail="Unknown relation type")
    allowed = next(
        (
            item
            for item in current_model().objectTypeRelations
            if item.relationTypeKey == relation_type_key
            and item.fromObjectTypeKey == from_type
            and item.toObjectTypeKey == to_type
        ),
        None,
    )
    if not allowed:
        raise HTTPException(
            status_code=422, detail="Relation is not permitted between these object types"
        )
    return allowed


def _validate_cardinality(session: Session, allowed, payload: RelationCreate) -> None:
    clauses = []
    if allowed.cardinality == "one-to-one":
        clauses = [
            ObjectRelation.from_object_id == payload.fromObjectId,
            ObjectRelation.to_object_id == payload.toObjectId,
        ]
    elif allowed.cardinality == "one-to-many":
        clauses = [ObjectRelation.to_object_id == payload.toObjectId]
    if clauses:
        existing = session.scalar(
            select(ObjectRelation.id)
            .where(ObjectRelation.relation_type_key == payload.relationTypeKey, or_(*clauses))
            .limit(1)
        )
        if existing:
            raise HTTPException(status_code=409, detail="Relation cardinality would be violated")


def _object_responses(session: Session, objects: list[RdmObject]) -> list[ObjectResponse]:
    values = load_attribute_values(session, [item.id for item in objects])
    return [
        ObjectResponse(
            id=item.id,
            workspaceKey=item.workspace_key,
            applicationKey=item.application_key,
            objectTypeKey=item.object_type_key,
            parentObjectId=item.parent_object_id,
            state=item.state,
            name=item.name,
            path=_object_path(session, item),
            attributes=values[item.id],
            version=item.version,
            createdAt=item.created_at,
            updatedAt=item.updated_at,
        )
        for item in objects
    ]


def _object_path(session: Session, item: RdmObject) -> list[dict[str, str]]:
    path = [{"id": item.id, "name": item.name, "objectTypeKey": item.object_type_key}]
    parent_id = item.parent_object_id
    visited = {item.id}
    while parent_id:
        if parent_id in visited:
            break
        visited.add(parent_id)
        parent = session.scalar(select(RdmObject).where(RdmObject.id == parent_id))
        if not parent:
            break
        path.append({"id": parent.id, "name": parent.name, "objectTypeKey": parent.object_type_key})
        parent_id = parent.parent_object_id
    return list(reversed(path))


def _relation_response(relation: ObjectRelation) -> RelationResponse:
    return RelationResponse(
        id=relation.id,
        relationTypeKey=relation.relation_type_key,
        fromObjectId=relation.from_object_id,
        toObjectId=relation.to_object_id,
        attributes=relation.attributes,
        version=relation.version,
        createdAt=relation.created_at,
        updatedAt=relation.updated_at,
    )
