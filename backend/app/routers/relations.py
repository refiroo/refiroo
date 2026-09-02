from typing import Literal

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError

from ..db import SessionLocal
from ..models.api import RelationCreate, RelationExpansion, RelationResponse
from ..models.database import AuditEvent, ObjectRelation, RdmObject
from ..services.objects import build_object_responses, load_object
from ..services.relations import (
    build_relation_response,
    find_allowed_relation,
    validate_cardinality,
)

router = APIRouter(prefix="/api/v1", tags=["relations"])


@router.post(
    "/relations",
    response_model=RelationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_relation(payload: RelationCreate) -> RelationResponse:
    with SessionLocal() as session:
        from_object = load_object(session, payload.fromObjectId)
        to_object = load_object(session, payload.toObjectId)
        allowed = find_allowed_relation(
            payload.relationTypeKey,
            from_object.object_type_key,
            to_object.object_type_key,
        )
        validate_cardinality(session, allowed, payload)
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
        return build_relation_response(relation)


@router.get("/relations", response_model=list[RelationExpansion])
def get_relations(
    object_id: str = Query(alias="objectId"),
    direction: Literal["outgoing", "incoming", "both"] = "both",
    relation_type_key: str | None = Query(default=None, alias="relationTypeKey"),
) -> list[RelationExpansion]:
    with SessionLocal() as session:
        load_object(session, object_id)
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
                build_object_responses(session, list(related_objects.values())),
                strict=True,
            )
        }
        return [
            RelationExpansion(
                direction="outgoing" if relation.from_object_id == object_id else "incoming",
                relation=build_relation_response(relation),
                object=responses[
                    relation.to_object_id
                    if relation.from_object_id == object_id
                    else relation.from_object_id
                ],
            )
            for relation in relations
        ]
