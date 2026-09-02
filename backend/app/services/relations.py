from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..models.api import RelationCreate, RelationResponse
from ..models.database import ObjectRelation
from .model_loader import current_model


def find_allowed_relation(relation_type_key: str, from_type: str, to_type: str):
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


def validate_cardinality(session: Session, allowed, payload: RelationCreate) -> None:
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


def build_relation_response(relation: ObjectRelation) -> RelationResponse:
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
