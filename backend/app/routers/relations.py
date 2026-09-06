from typing import Literal

from fastapi import APIRouter, Query, Response, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import aliased

from ..db import DbSession
from ..errors import api_error
from ..models.api import (
    RelationCreate,
    RelationExpansion,
    RelationPage,
    RelationResponse,
    RelationUpdate,
)
from ..models.database import ObjectRelation, RdmObject
from ..services.audit import record_audit_event
from ..services.model.registry import ActiveModelSnapshot
from ..services.object_lifecycle import load_active_object
from ..services.objects import build_object_responses, load_object
from ..services.pagination import integer_key, paginate_statement
from ..services.relations import (
    build_relation_response,
    claim_relation_version,
    create_relation_instance,
    ensure_relation_deletable,
    ensure_relation_mutable,
    find_allowed_relation,
    load_relation,
    validate_relation_attributes,
)
from ..services.workspaces import resolve_workspace

router = APIRouter(prefix="/api/v1", tags=["relations"])

_RELATION_KEYS = (integer_key("sequenceId", ObjectRelation.sequence_id, "sequence_id"),)


@router.post(
    "/relations",
    response_model=RelationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_relation(
    payload: RelationCreate, session: DbSession, snapshot: ActiveModelSnapshot
) -> RelationResponse:
    try:
        relation = create_relation_instance(session, snapshot.model, payload)
        session.commit()
    except IntegrityError:
        session.rollback()
        raise api_error(409, "duplicate_relation", "Relation already exists") from None
    session.refresh(relation)
    return build_relation_response(relation)


@router.get("/relations", response_model=RelationPage)
def get_relations(
    session: DbSession,
    snapshot: ActiveModelSnapshot,
    object_id: str = Query(alias="objectId"),
    direction: Literal["outgoing", "incoming", "both"] = "both",
    relation_type_key: str | None = Query(default=None, alias="relationTypeKey"),
    cursor: str | None = None,
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
) -> RelationPage:
    anchor = load_active_object(session, object_id)
    effective_relation_type_key = relation_type_key or None
    clauses = []
    if direction in {"outgoing", "both"}:
        clauses.append(ObjectRelation.from_object_id == object_id)
    if direction in {"incoming", "both"}:
        clauses.append(ObjectRelation.to_object_id == object_id)
    from_object = aliased(RdmObject)
    to_object = aliased(RdmObject)
    statement = (
        select(ObjectRelation)
        .join(from_object, from_object.id == ObjectRelation.from_object_id)
        .join(to_object, to_object.id == ObjectRelation.to_object_id)
        .where(
            or_(*clauses),
            from_object.workspace_key == anchor.workspace_key,
            to_object.workspace_key == anchor.workspace_key,
            from_object.active_revision_id.is_not(None),
            to_object.active_revision_id.is_not(None),
        )
    )
    if effective_relation_type_key:
        statement = statement.where(ObjectRelation.relation_type_key == effective_relation_type_key)

    visible, next_cursor = paginate_statement(
        session,
        statement,
        keys=_RELATION_KEYS,
        scope="relations",
        filters={
            "direction": direction,
            "objectId": object_id,
            "relationTypeKey": effective_relation_type_key,
            "workspaceKey": anchor.workspace_key,
        },
        cursor=cursor,
        page_size=page_size,
        message="Relation cursor is invalid",
    )

    related_ids = [_related_id(relation, object_id) for relation in visible]
    related_objects = {
        item.id: item
        for item in session.scalars(select(RdmObject).where(RdmObject.id.in_(related_ids)))
    }
    responses = {
        item.id: response
        for item, response in zip(
            related_objects.values(),
            build_object_responses(session, snapshot.model, list(related_objects.values())),
            strict=True,
        )
    }
    return RelationPage(
        items=[
            RelationExpansion(
                direction="outgoing" if relation.from_object_id == object_id else "incoming",
                relation=build_relation_response(relation),
                object=responses[_related_id(relation, object_id)],
            )
            for relation in visible
        ],
        nextCursor=next_cursor,
    )


def _related_id(relation: ObjectRelation, object_id: str) -> str:
    return (
        relation.to_object_id if relation.from_object_id == object_id else relation.from_object_id
    )


@router.get("/relations/{relation_id}", response_model=RelationResponse)
def get_relation(
    relation_id: str, session: DbSession, _snapshot: ActiveModelSnapshot
) -> RelationResponse:
    return build_relation_response(load_relation(session, relation_id))


@router.patch("/relations/{relation_id}", response_model=RelationResponse)
def update_relation(
    relation_id: str,
    payload: RelationUpdate,
    session: DbSession,
    snapshot: ActiveModelSnapshot,
) -> RelationResponse:
    model = snapshot.model
    relation = load_relation(session, relation_id)
    from_object = load_object(session, relation.from_object_id)
    to_object = load_object(session, relation.to_object_id)
    if from_object.active_revision_id is None or to_object.active_revision_id is None:
        raise api_error(409, "relation_endpoint_retired", "Related objects must be active")
    resolve_workspace(session, from_object.workspace_key, require_active=True)
    ensure_relation_mutable(model, relation.relation_type_key, to_object.object_type_key)
    allowed = find_allowed_relation(
        model,
        relation.relation_type_key,
        from_object.object_type_key,
        to_object.object_type_key,
    )
    if allowed.required:
        raise api_error(
            422,
            "immutable_relation",
            "Object-owned required relationships change through object drafts",
        )
    claim_relation_version(session, relation, payload.expectedVersion)
    attributes = validate_relation_attributes(model, allowed, payload.attributes)
    old_attributes = relation.attributes
    relation.attributes = attributes
    record_audit_event(
        session,
        aggregate_type="relation",
        aggregate_id=relation.id,
        action="updated",
        version=relation.version,
        changes={"attributes": {"from": old_attributes, "to": attributes}},
        object_ids=[relation.from_object_id, relation.to_object_id],
    )
    session.commit()
    session.refresh(relation)
    return build_relation_response(relation)


@router.delete("/relations/{relation_id}", status_code=204)
def delete_relation(
    relation_id: str,
    session: DbSession,
    snapshot: ActiveModelSnapshot,
    expected_version: int = Query(ge=1, alias="expectedVersion"),
) -> Response:
    model = snapshot.model
    relation = load_relation(session, relation_id)
    from_object = load_object(session, relation.from_object_id)
    to_object = load_object(session, relation.to_object_id)
    if from_object.active_revision_id is None or to_object.active_revision_id is None:
        raise api_error(409, "relation_endpoint_retired", "Related objects must be active")
    resolve_workspace(session, from_object.workspace_key, require_active=True)
    ensure_relation_mutable(model, relation.relation_type_key, to_object.object_type_key)
    allowed = find_allowed_relation(
        model,
        relation.relation_type_key,
        from_object.object_type_key,
        to_object.object_type_key,
    )
    ensure_relation_deletable(allowed)
    claim_relation_version(session, relation, expected_version)
    record_audit_event(
        session,
        aggregate_type="relation",
        aggregate_id=relation.id,
        action="deleted",
        version=relation.version,
        changes={
            "relationTypeKey": relation.relation_type_key,
            "fromObjectId": relation.from_object_id,
            "toObjectId": relation.to_object_id,
        },
        object_ids=[relation.from_object_id, relation.to_object_id],
    )
    session.delete(relation)
    session.commit()
    return Response(status_code=204)
