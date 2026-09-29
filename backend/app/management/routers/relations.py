from typing import Annotated, Literal

from fastapi import APIRouter, Query, Response, status
from sqlalchemy import select

from ...common.pagination import paginate_statement
from ...engine.change_sets.records import (
    delete_change_set_relation,
    put_change_set_relation,
    update_change_set_relation,
)
from ...engine.model.registry import resolve_model_snapshot
from ...engine.reads.relation_queries import build_relation_query, build_snapshot_relation_query
from ...engine.reads.snapshot_reads import (
    change_set_context,
    find_object,
    find_objects,
    find_relation,
    object_paths,
    publication_context,
)
from ...engine.records.context import load_active_projection
from ...engine.records.relation_set_versions import set_claim
from ...engine.records.relations import (
    create_live_relation,
    delete_live_relation,
    load_relation,
    update_live_relation,
)
from ...engine.workspaces.catalogue import resolve_workspace
from ...errors import api_error
from ...models.commands import (
    ChangeSetRelationUpdate,
    ChangeSetRelationWrite,
    RelationCreate,
    RelationUpdate,
)
from ...models.database import RdmObject
from ..dependencies import DbSession, RequestModelSnapshot
from ..paging import SeekablePageQuery
from ..presenters import build_object_responses, build_relation_response, change_set_object_response
from ..schemas.records import RelationExpansion, RelationPage, RelationResponse

router = APIRouter(prefix="/api/v1", tags=["relations"])

def _change_set_response(item) -> RelationResponse:
    # Change set and history relations record no timestamps (WP-10K); never substitute the current time.
    return RelationResponse(id=item.relation_id, relationTypeKey=item.relation_type_key, fromObjectId=item.from_object_id, toObjectId=item.to_object_id, attributes=item.attributes or {}, version=item.version, createdAt=None, updatedAt=None)

def _ctx(change_set: str, expected: int | None) -> int:
    if expected is None:
        raise api_error(
            409,
            "change_set_required",
            "expectedChangeSetVersion is required when targeting a change set",
        )
    return expected

@router.post("/relations", response_model=RelationResponse, status_code=status.HTTP_201_CREATED)
def create_relation(payload: RelationCreate, session: DbSession) -> RelationResponse:
    claim = set_claim(payload.expectedRelationSetVersion, payload.relationSetDirection)
    if payload.changeSetId:
        change_set = str(payload.changeSetId)
        expected = _ctx(change_set, payload.expectedChangeSetVersion)
        row, set_version = put_change_set_relation(session, change_set, ChangeSetRelationWrite(id=None, relationTypeKey=payload.relationTypeKey, fromObjectId=payload.fromObjectId, toObjectId=payload.toObjectId, attributes=payload.attributes, expectedChangeSetVersion=expected, expectedRecordVersion=None), claim)
        return _change_set_response(row).model_copy(update={"changeSetVersion": change_set_context(session, change_set).change_set.version, "relationSetVersion": set_version})
    row, set_version = create_live_relation(session, resolve_model_snapshot(session).model, payload, claim)
    return build_relation_response(row).model_copy(update={"relationSetVersion": set_version})

@router.get("/relations", response_model=RelationPage)
def list_relations(
    session: DbSession,
    snapshot: RequestModelSnapshot,
    paging: SeekablePageQuery,
    object_id: str = Query(alias="objectId"),
    direction: Literal["outgoing", "incoming", "both"] = "both",
    relation_type_keys: Annotated[
        list[str] | None,
        Query(
            alias="relationTypeKey",
            description="List only these relation types; repeat the parameter for several",
        ),
    ] = None,
    workspace_key: str | None = Query(default=None, alias="workspaceKey"),
    change_set_id: str | None = Query(default=None, alias="changeSetId"),
    publication_id: str | None = Query(default=None, alias="publicationId"),
    search: str | None = Query(
        default=None,
        description="Match the related record's name or searchable fields, case-insensitively",
    ),
    sort: str | None = Query(
        default=None,
        description=(
            "A field of the related record, as on an object list: name, objectType, a scalar"
            " attribute, ancestor:<type>, or (live only) createdAt or updatedAt; or relationship,"
            " the label each row shows. Prefix '-' for descending. Records without the attribute"
            " sort last; an ancestor sort needs the listed relations to reach one object type."
            " Omitted: name"
        ),
    ),
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
) -> RelationPage:
    if sum(value is not None for value in (change_set_id, publication_id)) > 1:
        raise api_error(422, "mutually_exclusive_context", "Workspace contexts cannot be combined")
    options = {
        "object_id": object_id,
        "direction": direction,
        "relation_type_keys": relation_type_keys or None,
        "search": search or None,
        "sort": sort,
    }
    if change_set_id or publication_id:
        context = change_set_context(session, change_set_id) if change_set_id else publication_context(session, publication_id)
        anchor = find_object(session, context, object_id)
        if anchor is None:
            raise api_error(404, "object_not_found", "Object not found")
        query = build_snapshot_relation_query(snapshot.model, context, anchor_type_key=anchor.object_type_key, **options)
        page = paginate_statement(session, query.statement, keys=query.keys, scope=f"relations-{context.kind}", filters=query.filters, page=paging, page_size=page_size, message="Relation cursor is invalid", rows=True, seek=query.seek)
        objects = find_objects(session, context, (row.related_id for row in page.items))
        paths = object_paths(session, context, objects.values())
        return RelationPage(items=[RelationExpansion(direction="outgoing" if row.from_object_id == object_id else "incoming", relation=_change_set_response(row), object=change_set_object_response(objects[row.related_id], context.id, snapshot.model, path=paths[row.related_id]).model_copy(update={"workspaceKey": context.workspace_key})) for row in page.items if row.related_id in objects], **page.links())
    anchor = load_active_projection(session, object_id)
    workspace = resolve_workspace(session, workspace_key)
    if anchor.workspace_key != workspace.key:
        raise api_error(404, "object_not_found", "Object not found in the selected workspace")
    query = build_relation_query(snapshot.model, anchor_type_key=anchor.object_type_key, workspace_key=anchor.workspace_key, **options)
    page = paginate_statement(session, query.statement, keys=query.keys, scope="relations", filters=query.filters, page=paging, page_size=page_size, message="Relation cursor is invalid", rows=True, seek=query.seek)
    related_ids = list(dict.fromkeys(row.related_id for row in page.items))
    related_rows = list(session.scalars(select(RdmObject).where(RdmObject.id.in_(related_ids))))
    # One batched build for the page, not one per row (S1 finding).
    related = {item.id: item for item in build_object_responses(session, snapshot.model, related_rows)}
    return RelationPage(items=[RelationExpansion(direction="outgoing" if row.ObjectRelation.from_object_id == object_id else "incoming", relation=build_relation_response(row.ObjectRelation), object=related[row.related_id]) for row in page.items], **page.links())

@router.get("/relations/{relation_id}", response_model=RelationResponse)
def get_relation(relation_id: str, session: DbSession, snapshot: RequestModelSnapshot, workspace_key: str | None = Query(default=None, alias="workspaceKey"), change_set_id: str | None = Query(default=None, alias="changeSetId"), publication_id: str | None = Query(default=None, alias="publicationId")) -> RelationResponse:
    if change_set_id and publication_id: raise api_error(422, "mutually_exclusive_context", "Workspace contexts cannot be combined")
    if change_set_id or publication_id:
        context = change_set_context(session, change_set_id) if change_set_id else publication_context(session, publication_id)
        row = find_relation(session, context, relation_id)
        if row is None: raise api_error(404, "relation_not_found", "Relation not found")
        return _change_set_response(row)
    row = load_relation(session, relation_id)
    workspace = resolve_workspace(session, workspace_key)
    endpoints = set(session.scalars(
        select(RdmObject.id).where(
            RdmObject.id.in_([row.from_object_id, row.to_object_id]),
            RdmObject.workspace_key == workspace.key,
        )
    ))
    if endpoints != {row.from_object_id, row.to_object_id}:
        raise api_error(404, "relation_not_found", "Relation not found")
    return build_relation_response(row)

@router.patch("/relations/{relation_id}", response_model=RelationResponse)
def update_relation(relation_id: str, payload: RelationUpdate, session: DbSession) -> RelationResponse:
    if payload.changeSetId:
        change_set = str(payload.changeSetId)
        expected = _ctx(change_set, payload.expectedChangeSetVersion)
        row = update_change_set_relation(session, change_set, relation_id, ChangeSetRelationUpdate(attributes=payload.attributes, expectedChangeSetVersion=expected, expectedRecordVersion=payload.expectedVersion))
        return _change_set_response(row).model_copy(update={"changeSetVersion": change_set_context(session, change_set).change_set.version})
    row = update_live_relation(session, resolve_model_snapshot(session).model, relation_id, payload)
    return build_relation_response(row)

@router.delete("/relations/{relation_id}", status_code=204)
def remove_relation(relation_id: str, session: DbSession,
                    change_set_id: str | None = Query(default=None, alias="changeSetId"),
                    expected_change_set_version: int | None = Query(default=None, alias="expectedChangeSetVersion", ge=1),
                    expected_version: int = Query(alias="expectedVersion", ge=1),
                    expected_set_version: int | None = Query(default=None, alias="expectedRelationSetVersion", ge=0, description="With relationSetDirection: delete only while that end's relation set is at this version"),
                    set_direction: Literal["outgoing", "incoming"] | None = Query(default=None, alias="relationSetDirection", description="The claimed set: outgoing is the from end's")) -> Response:
    claim = set_claim(expected_set_version, set_direction)
    if change_set_id:
        _ctx(change_set_id, expected_change_set_version)
        delete_change_set_relation(session, change_set_id, relation_id, expected_change_set_version, expected_version, claim)
    else:
        delete_live_relation(session, resolve_model_snapshot(session).model, relation_id, expected_version, claim)
    return Response(status_code=204)
