from typing import Annotated, Literal

from fastapi import APIRouter, Query, Response, status
from sqlalchemy import select

from ...common.pagination import paginate_statement
from ...engine.change_sets.records import (
    delete_change_set_relation,
    put_change_set_relation,
    update_change_set_relation,
)
from ...engine.model.registry import resolve_record_snapshot, resolve_relation_snapshot
from ...engine.reads.relation_queries import (
    build_relation_query,
    build_snapshot_relation_query,
    held_records_query,
    relation_scope,
)
from ...engine.reads.snapshot_reads import (
    change_set_context,
    find_object,
    find_objects,
    find_relation,
    object_paths,
    publication_context,
)
from ...engine.records.context import load_active_projection
from ...engine.records.relation_set_versions import anchored_set_versions, set_claim
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
from ..access import (
    CONTEXT,
    RELATION_CREATE,
    RELATION_READ,
    RELATION_WRITE,
    AuthorizedRoute,
    requires,
)
from ..dependencies import DbSession, RequestModelSnapshot
from ..paging import PageQuery, SeekablePageQuery
from ..presenters import build_object_responses, build_relation_response, change_set_object_response
from ..schemas.records import (
    HeldObject,
    HeldRecord,
    HeldRecordPage,
    RelationExpansion,
    RelationPage,
    RelationResponse,
    RelationSetVersionItem,
)

router = APIRouter(route_class=AuthorizedRoute, prefix="/api/v1", tags=["relations"])

def _change_set_response(item) -> RelationResponse:
    # Change set and history relations record no timestamps (WP-10K); never substitute the current time.
    return RelationResponse(id=item.relation_id, relationTypeKey=item.relation_type_key, fromObjectId=item.from_object_id, toObjectId=item.to_object_id, attributes=item.attributes or {}, version=item.version, createdAt=None, updatedAt=None)

def _relation_sets(session, model, *, workspace_key, change_set_id, anchor_type_key, anchor_id, direction, relation_type_keys) -> list[RelationSetVersionItem]:
    """The sets the listed record anchors and their versions (0.9 B3, D38)."""
    return [
        RelationSetVersionItem(relationTypeKey=item.relation_type_key, fromObjectTypeKey=item.from_object_type_key, toObjectTypeKey=item.to_object_type_key, direction=item.direction, relationSetVersion=item.version)
        for item in anchored_set_versions(session, model, workspace_key=workspace_key, change_set_id=change_set_id, anchor_type_key=anchor_type_key, anchor_id=anchor_id, direction=direction, relation_type_keys=relation_type_keys)
    ]

def _ctx(change_set: str, expected: int | None) -> int:
    if expected is None:
        raise api_error(
            409,
            "CHANGE_SET_REQUIRED",
            "expectedChangeSetVersion is required when targeting a change set",
        )
    return expected

@router.post("/relations", response_model=RelationResponse, status_code=status.HTTP_201_CREATED)
@requires("records.write", at=RELATION_CREATE)
def create_relation(payload: RelationCreate, session: DbSession) -> RelationResponse:
    claim = set_claim(payload.expectedRelationSetVersion, payload.relationSetDirection)
    if payload.changeSetId:
        change_set = str(payload.changeSetId)
        expected = _ctx(change_set, payload.expectedChangeSetVersion)
        row, set_version = put_change_set_relation(session, change_set, ChangeSetRelationWrite(id=None, relationTypeKey=payload.relationTypeKey, fromObjectId=payload.fromObjectId, toObjectId=payload.toObjectId, attributes=payload.attributes, expectedChangeSetVersion=expected, expectedRecordVersion=None), claim)
        return _change_set_response(row).model_copy(update={"changeSetVersion": change_set_context(session, change_set).change_set.version, "relationSetVersion": set_version})
    row, set_version = create_live_relation(session, resolve_record_snapshot(session, str(payload.fromObjectId)).model, payload, claim)
    return build_relation_response(row).model_copy(update={"relationSetVersion": set_version})

@router.get("/relations", response_model=RelationPage)
@requires("records.read", at=CONTEXT)
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
        raise api_error(422, "MUTUALLY_EXCLUSIVE_CONTEXT", "Workspace contexts cannot be combined")
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
            raise api_error(404, "OBJECT_NOT_FOUND", "Object not found")
        query = build_snapshot_relation_query(snapshot.model, context, anchor_type_key=anchor.object_type_key, **options)
        page = paginate_statement(session, query.statement, keys=query.keys, scope=relation_scope(context), filters=query.filters, page=paging, page_size=page_size, message="Relation cursor is invalid", rows=True, seek=query.seek)
        objects = find_objects(session, context, (row.related_id for row in page.items))
        paths = object_paths(session, context, objects.values())
        relation_sets = _relation_sets(session, snapshot.model, workspace_key=context.workspace_key, change_set_id=context.id, anchor_type_key=anchor.object_type_key, anchor_id=object_id, direction=direction, relation_type_keys=relation_type_keys) if change_set_id else None
        return RelationPage(items=[RelationExpansion(direction="outgoing" if row.from_object_id == object_id else "incoming", relation=_change_set_response(row), object=change_set_object_response(objects[row.related_id], context.id, snapshot.model, path=paths[row.related_id]).model_copy(update={"workspaceKey": context.workspace_key})) for row in page.items if row.related_id in objects], relationSets=relation_sets, **page.links())
    anchor = load_active_projection(session, object_id)
    workspace = resolve_workspace(session, workspace_key)
    if anchor.workspace_key != workspace.key:
        raise api_error(404, "OBJECT_NOT_FOUND", "Object not found in the selected workspace")
    query = build_relation_query(snapshot.model, anchor_type_key=anchor.object_type_key, workspace_key=anchor.workspace_key, **options)
    page = paginate_statement(session, query.statement, keys=query.keys, scope=relation_scope(None), filters=query.filters, page=paging, page_size=page_size, message="Relation cursor is invalid", rows=True, seek=query.seek)
    related_ids = list(dict.fromkeys(row.related_id for row in page.items))
    related_rows = list(session.scalars(select(RdmObject).where(RdmObject.id.in_(related_ids))))
    # One batched build for the page, not one per row (S1 finding).
    related = {item.id: item for item in build_object_responses(session, snapshot.model, related_rows)}
    relation_sets = _relation_sets(session, snapshot.model, workspace_key=anchor.workspace_key, change_set_id=None, anchor_type_key=anchor.object_type_key, anchor_id=object_id, direction=direction, relation_type_keys=relation_type_keys)
    return RelationPage(items=[RelationExpansion(direction="outgoing" if row.ObjectRelation.from_object_id == object_id else "incoming", relation=build_relation_response(row.ObjectRelation), object=related[row.related_id]) for row in page.items], relationSets=relation_sets, **page.links())

@router.get("/relations/held", response_model=HeldRecordPage)
@requires("records.read", at=CONTEXT)
def list_held_records(
    session: DbSession,
    snapshot: RequestModelSnapshot,
    paging: PageQuery,
    object_type_key: str = Query(alias="objectTypeKey", description="The named records' type"),
    relation_type_key: str = Query(alias="relationTypeKey"),
    direction: Literal["outgoing", "incoming"] = Query(
        description="Read from the named records: outgoing when they are the relationship's from end"
    ),
    object_ids: Annotated[
        list[str],
        Query(alias="objectId", description="Repeatable, at most 500: the records whose holdings are read"),
    ] = [],  # noqa: B006
    workspace_key: str | None = Query(default=None, alias="workspaceKey"),
    change_set_id: str | None = Query(default=None, alias="changeSetId"),
    publication_id: str | None = Query(default=None, alias="publicationId"),
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
) -> HeldRecordPage:
    """The records the named records hold through one relationship, each with how many of them
    hold it, in name order (0.9 K6a, D165): what a selection's Remove offers."""
    if change_set_id and publication_id:
        raise api_error(422, "MUTUALLY_EXCLUSIVE_CONTEXT", "Workspace contexts cannot be combined")
    context = (
        change_set_context(session, change_set_id)
        if change_set_id
        else publication_context(session, publication_id)
        if publication_id
        else None
    )
    workspace = context.workspace_key if context else resolve_workspace(session, workspace_key).key
    query = held_records_query(
        snapshot.model,
        context,
        workspace_key=workspace,
        object_type_key=object_type_key,
        relation_type_key=relation_type_key,
        direction=direction,
        object_ids=object_ids,
    )
    page = paginate_statement(
        session,
        query.statement,
        keys=query.keys,
        scope="relations-held",
        filters=query.filters,
        page=paging,
        page_size=page_size,
        message="Cursor is invalid",
        rows=True,
    )
    return HeldRecordPage(
        items=[
            HeldRecord(
                object=HeldObject(id=row.id, name=row.name, objectTypeKey=row.object_type_key),
                count=row.held,
            )
            for row in page.items
        ],
        **page.links(),
    )


@router.get("/relations/{relation_id}", response_model=RelationResponse)
@requires("records.read", at=RELATION_READ)
def get_relation(relation_id: str, session: DbSession, snapshot: RequestModelSnapshot, workspace_key: str | None = Query(default=None, alias="workspaceKey"), change_set_id: str | None = Query(default=None, alias="changeSetId"), publication_id: str | None = Query(default=None, alias="publicationId")) -> RelationResponse:
    if change_set_id and publication_id: raise api_error(422, "MUTUALLY_EXCLUSIVE_CONTEXT", "Workspace contexts cannot be combined")
    if change_set_id or publication_id:
        context = change_set_context(session, change_set_id) if change_set_id else publication_context(session, publication_id)
        row = find_relation(session, context, relation_id)
        if row is None: raise api_error(404, "RELATION_NOT_FOUND", "Relation not found")
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
        raise api_error(404, "RELATION_NOT_FOUND", "Relation not found")
    return build_relation_response(row)

@router.patch("/relations/{relation_id}", response_model=RelationResponse)
@requires("records.write", at=RELATION_WRITE)
def update_relation(relation_id: str, payload: RelationUpdate, session: DbSession) -> RelationResponse:
    if payload.changeSetId:
        change_set = str(payload.changeSetId)
        expected = _ctx(change_set, payload.expectedChangeSetVersion)
        row = update_change_set_relation(session, change_set, relation_id, ChangeSetRelationUpdate(attributes=payload.attributes, expectedChangeSetVersion=expected, expectedRecordVersion=payload.expectedVersion))
        return _change_set_response(row).model_copy(update={"changeSetVersion": change_set_context(session, change_set).change_set.version})
    row = update_live_relation(session, resolve_relation_snapshot(session, relation_id).model, relation_id, payload)
    return build_relation_response(row)

@router.delete("/relations/{relation_id}", status_code=204)
@requires("records.write", at=RELATION_WRITE)
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
        delete_live_relation(session, resolve_relation_snapshot(session, relation_id).model, relation_id, expected_version, claim)
    return Response(status_code=204)
