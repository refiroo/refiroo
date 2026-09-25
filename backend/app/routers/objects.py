from datetime import datetime

from fastapi import APIRouter, Query, Request, Response, status
from sqlalchemy import select

from ..common.time import as_utc
from ..db import DbSession
from ..errors import api_error
from ..models.api import (
    AuditEventPage,
    ObjectCreate,
    ObjectPage,
    ObjectResponse,
    ObjectUpdate,
    WorkspaceDraftObjectUpdate,
    WorkspaceDraftObjectWrite,
)
from ..models.database import WorkspaceRevision, WorkspaceRevisionObject
from ..services.attributes import normalize_value
from ..services.audit import list_object_history
from ..services.deletion import delete_object_record
from ..services.model.registry import (
    RequestModelSnapshot,
    resolve_draft_snapshot,
    resolve_model_snapshot,
)
from ..services.objects import (
    OBJECT_SORT_COLUMNS,
    _built_in_value_type,
    _parse_filter_value,
    _query_error,
    build_object_query,
    build_object_responses,
    create_object_record,
    get_object_type,
    load_active_projection,
    load_object,
    update_object_record,
)
from ..services.pagination import paginate_sequence, paginate_statement, sequence_sort_text
from ..services.workspace_revisions import (
    delete_draft_object,
    effective_draft_membership,
    put_draft_object,
    update_draft_object,
)
from ..services.workspaces import resolve_workspace

router = APIRouter(prefix="/api/v1", tags=["objects"])


# Draft and history rows record no timestamps; a query on them is refused, not matched as empty.
_UNRECORDED_TIMESTAMPS = {"createdAt": "Created", "updatedAt": "Updated"}


def _sequence_object_rows(
    rows, *, model, object_type_key, application_key, parent_object_id, search, sort, filters
):
    """Apply the public query contract to immutable draft/revision projections."""
    for field, operator, _raw in filters:
        if field in _UNRECORDED_TIMESTAMPS:
            _query_error(
                "invalid_filter",
                f"{_UNRECORDED_TIMESTAMPS[field]} is not recorded in drafts or history",
                f"filter.{field}.{operator}",
            )
    if (sort or "").removeprefix("-") in _UNRECORDED_TIMESTAMPS:
        _query_error(
            "invalid_sort",
            f"{_UNRECORDED_TIMESTAMPS[sort.removeprefix('-')]} is not recorded in drafts or history",
            "sort",
        )

    def value(item, field):
        if field == "id":
            return item.object_id
        if field == "name":
            return item.name
        stored = (item.attributes or {}).get(field)
        definition = model.attribute_type(field)
        if stored is None or definition is None:
            return stored
        # Draft rows hold the JSON form; compare as the declared type, like live SQL does.
        typed = normalize_value(definition, stored)
        return as_utc(typed) if isinstance(typed, datetime) else typed

    parsed_filters = []
    for field, operator, raw in filters:
        if field in OBJECT_SORT_COLUMNS:
            value_type = _built_in_value_type(field)
        else:
            definition = model.attribute_type(field)
            value_type = definition.valueType if definition else "text"
        parsed = _parse_filter_value(value_type, operator, raw, field)
        parsed_filters.append(
            (field, operator, as_utc(parsed) if isinstance(parsed, datetime) else parsed)
        )

    def matches(item):
        if application_key and item.application_key != application_key:
            return False
        if parent_object_id and item.parent_object_id != parent_object_id:
            return False
        if search:
            needle = search.casefold()
            if needle not in item.name.casefold() and not any(
                needle in str(v).casefold() for v in (item.attributes or {}).values()
            ):
                return False
        equalities: dict[str, list[object]] = {}
        for field, operator, expected in parsed_filters:
            if operator == "eq":
                equalities.setdefault(field, []).append(expected)
                continue
            candidate = value(item, field)
            if operator == "isUnset":
                if (field not in (item.attributes or {})) != expected:
                    return False
                continue
            if operator == "isNull":
                if (field in (item.attributes or {}) and candidate is None) != expected:
                    return False
                continue
            if candidate is None:
                return False
            if operator == "contains" and str(expected).casefold() not in str(candidate).casefold():
                return False
            if operator == "startsWith" and not str(candidate).casefold().startswith(
                str(expected).casefold()
            ):
                return False
            if operator == "lt" and not candidate < expected:
                return False
            if operator == "lte" and not candidate <= expected:
                return False
            if operator == "gt" and not candidate > expected:
                return False
            if operator == "gte" and not candidate >= expected:
                return False
        return not any(value(item, field) not in expected for field, expected in equalities.items())

    sort_name = sort or "id"
    descending = sort_name.startswith("-")
    field = sort_name.removeprefix("-")

    def identity(item):
        candidate = value(item, field)
        if candidate is None:
            rank = "a" if descending else "z"
            return (rank, item.object_id)
        rank = "z" if descending else "a"
        return (f"{rank}{sequence_sort_text(candidate)}", item.object_id)

    return [item for item in rows if matches(item)], identity, descending, field


def _draft_object_response(item, draft_id: str, model, *, objects=None) -> ObjectResponse:
    attrs = []
    for key, value in (item.attributes or {}).items():
        definition = model.attribute_type(key)
        attrs.append(
            {
                "id": f"{item.object_id}:{key}",
                "attributeTypeKey": key,
                "name": definition.name if definition else key,
                "valueType": definition.valueType if definition else "text",
                "value": value,
            }
        )
    path = []
    if objects is not None:
        by_id = {candidate.object_id: candidate for candidate in objects}
        current = item
        seen = set()
        while current is not None and current.object_id not in seen:
            seen.add(current.object_id)
            path.append(
                {
                    "id": current.object_id,
                    "name": current.name,
                    "objectTypeKey": current.object_type_key,
                }
            )
            current = by_id.get(current.parent_object_id) if current.parent_object_id else None
        path.reverse()
    return ObjectResponse(
        id=item.object_id,
        workspaceKey=(getattr(item, "workspace_key", None) or ""),
        applicationKey=item.application_key,
        objectTypeKey=item.object_type_key,
        parentObjectId=item.parent_object_id,
        name=item.name,
        path=path,
        attributes=attrs,
        version=item.version,
        # Not recorded for draft and history rows (WP-10K); never substitute the current time.
        createdAt=None,
        updatedAt=None,
    )


def _require_draft_context(draft_id: str, expected: int | None) -> int:
    """Guard a write that explicitly targets a draft but omits its optimistic-concurrency version."""
    if expected is None:
        raise api_error(
            409,
            "workspace_draft_required",
            "expectedWorkspaceDraftVersion is required when targeting a workspace draft",
        )
    return expected


@router.post("/objects", response_model=ObjectResponse, status_code=status.HTTP_201_CREATED)
def create_object(
    payload: ObjectCreate, session: DbSession
) -> ObjectResponse:
    attribute_keys = [item.attributeTypeKey for item in payload.attributes]
    if len(attribute_keys) != len(set(attribute_keys)):
        raise api_error(422, "duplicate_attribute", "Object attributes must not repeat a key")
    if payload.workspaceDraftId:
        draft_id = str(payload.workspaceDraftId)
        expected = _require_draft_context(draft_id, payload.expectedWorkspaceDraftVersion)
        membership = effective_draft_membership(session, draft_id)
        if payload.workspaceKey is not None and payload.workspaceKey != membership.draft.workspace_key:
            raise api_error(
                422,
                "workspace_context_mismatch",
                "workspaceKey does not match workspaceDraftId",
                {
                    "workspaceKey": payload.workspaceKey,
                    "contextWorkspaceKey": membership.draft.workspace_key,
                },
            )
        row = put_draft_object(
            session,
            draft_id,
            WorkspaceDraftObjectWrite(
                id=payload.id,
                applicationKey=payload.applicationKey,
                objectTypeKey=payload.objectTypeKey,
                name=payload.name,
                parentObjectId=payload.parentObjectId,
                attributes={item.attributeTypeKey: item.value for item in payload.attributes},
                initialRelations=payload.initialRelations,
                expectedDraftVersion=expected,
                expectedRecordVersion=None,
            ),
        )
        membership = effective_draft_membership(session, draft_id)
        draft = membership.draft
        return _draft_object_response(
            row, draft_id, resolve_draft_snapshot(session, draft_id).model, objects=membership.objects
        ).model_copy(
            update={"workspaceKey": draft.workspace_key, "workspaceDraftVersion": draft.version}
        )
    if payload.workspaceKey is None:
        raise api_error(
            422,
            "workspace_key_required",
            "workspaceKey is required for a live (active workspace) write; omit workspaceDraftId "
            "and provide workspaceKey, or target a workspace draft",
        )
    snapshot = resolve_model_snapshot(session)
    item = create_object_record(session, snapshot.model, payload)
    return build_object_responses(session, snapshot.model, [item])[0]


@router.patch("/objects/{object_type_key}/{object_id}", response_model=ObjectResponse)
def update_object(
    object_type_key: str,
    object_id: str,
    payload: ObjectUpdate,
    session: DbSession,
) -> ObjectResponse:
    fields = payload.model_dump(
        exclude={"expectedVersion", "workspaceDraftId", "expectedWorkspaceDraftVersion"},
        exclude_unset=True,
    )
    if "attributes" in fields:
        fields["attributes"] = {
            item["attributeTypeKey"]: item["value"] for item in fields["attributes"]
        }
    if payload.workspaceDraftId:
        draft_id = str(payload.workspaceDraftId)
        expected = _require_draft_context(draft_id, payload.expectedWorkspaceDraftVersion)
        draft_payload = WorkspaceDraftObjectUpdate(
            expectedDraftVersion=expected, expectedRecordVersion=payload.expectedVersion, **fields
        )
        row = update_draft_object(session, draft_id, object_id, draft_payload)
        membership = effective_draft_membership(session, draft_id)
        draft = membership.draft
        return _draft_object_response(
            row, draft_id, resolve_draft_snapshot(session, draft_id).model, objects=membership.objects
        ).model_copy(
            update={"workspaceKey": draft.workspace_key, "workspaceDraftVersion": draft.version}
        )
    snapshot = resolve_model_snapshot(session)
    item = update_object_record(session, snapshot.model, object_type_key, object_id, payload)
    return build_object_responses(session, snapshot.model, [item])[0]


@router.delete("/objects/{object_type_key}/{object_id}", status_code=204)
def delete_object(
    object_type_key: str,
    object_id: str,
    session: DbSession,
    workspace_draft_id: str | None = Query(default=None, alias="workspaceDraftId"),
    expected_workspace_draft_version: int | None = Query(
        default=None, alias="expectedWorkspaceDraftVersion", ge=1
    ),
    expected_version: int = Query(ge=1, alias="expectedVersion"),
    cascade: bool = False,
    deletion_preview_token: str | None = Query(default=None, alias="deletionPreviewToken"),
) -> Response:
    if workspace_draft_id:
        _require_draft_context(workspace_draft_id, expected_workspace_draft_version)
        delete_draft_object(
            session,
            workspace_draft_id,
            object_type_key,
            object_id,
            expected_workspace_draft_version,
            expected_version,
            cascade=cascade,
            deletion_preview=deletion_preview_token,
        )
    else:
        snapshot = resolve_model_snapshot(session)
        delete_object_record(
            session,
            snapshot.model,
            object_type_key,
            object_id,
            expected_version,
            cascade=cascade,
            deletion_preview=deletion_preview_token,
            model_identity=snapshot.model_hash,
        )
    return Response(status_code=204)


@router.get(
    "/objects/{object_type_key}",
    response_model=ObjectPage,
    openapi_extra={
        "parameters": [
            {
                "name": "filter.<field>.<operator>",
                "in": "query",
                "required": False,
                "description": (
                    "Repeatable schema 0.5 typed filter. Operators and lexical values depend on "
                    "the model-declared field type and filterable capability."
                ),
                "schema": {"type": "string"},
            }
        ]
    },
)
def list_objects(
    object_type_key: str,
    request: Request,
    session: DbSession,
    snapshot: RequestModelSnapshot,
    cursor: str | None = None,
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
    application_key: str | None = Query(default=None, alias="applicationKey"),
    workspace_key: str | None = Query(default=None, alias="workspaceKey"),
    workspace_draft_id: str | None = Query(default=None, alias="workspaceDraftId"),
    workspace_revision_id: str | None = Query(default=None, alias="workspaceRevisionId"),
    parent_object_id: str | None = Query(default=None, alias="parentObjectId"),
    search: str | None = None,
    sort: str | None = Query(
        default=None,
        description="One built-in or model-declared sortable field; prefix '-' for descending",
    ),
) -> ObjectPage:
    model = snapshot.model
    if workspace_draft_id and workspace_revision_id:
        raise api_error(
            422,
            "mutually_exclusive_context",
            "workspaceDraftId and workspaceRevisionId cannot be combined",
        )
    if workspace_draft_id:
        membership = effective_draft_membership(session, workspace_draft_id)
        get_object_type(model, object_type_key)
        filters = _field_filters(request)
        # Reuse the model-aware query builder for declared field/operator validation.
        build_object_query(
            model,
            object_type_key=object_type_key,
            application_key=application_key,
            workspace_key=membership.draft.workspace_key,
            parent_object_id=parent_object_id,
            search=search,
            sort=sort,
            field_filters=filters,
        )
        rows, identity, descending, sort_field = _sequence_object_rows(
            [x for x in membership.objects if x.object_type_key == object_type_key],
            model=model,
            object_type_key=object_type_key,
            application_key=application_key,
            parent_object_id=parent_object_id,
            search=search,
            sort=sort,
            filters=filters,
        )
        page, next_cursor = paginate_sequence(
            rows,
            identity,
            scope="objects-draft",
            filters={
                "draftId": workspace_draft_id,
                "objectTypeKey": object_type_key,
                "applicationKey": application_key,
                "parentObjectId": parent_object_id,
                "search": search,
                "sort": sort_field,
                "descending": descending,
                "typedFilters": filters,
            },
            cursor=cursor,
            page_size=page_size,
            sort=(("-" if descending else "") + sort_field, "id"),
            descending=descending,
            message="Object cursor is invalid",
        )
        return ObjectPage(
            items=[
                _draft_object_response(x, workspace_draft_id, model).model_copy(
                    update={"workspaceKey": membership.draft.workspace_key}
                )
                for x in page
            ],
            nextCursor=next_cursor,
        )
    if workspace_revision_id:
        revision = session.scalar(
            select(WorkspaceRevision).where(WorkspaceRevision.id == workspace_revision_id)
        )
        if revision is None:
            raise api_error(404, "workspace_revision_not_found", "Workspace revision not found")
        get_object_type(model, object_type_key)
        filters = _field_filters(request)
        build_object_query(
            model,
            object_type_key=object_type_key,
            application_key=application_key,
            workspace_key=revision.workspace_key,
            parent_object_id=parent_object_id,
            search=search,
            sort=sort,
            field_filters=filters,
        )
        rows, identity, descending, sort_field = _sequence_object_rows(
            list(
                session.scalars(
                    select(WorkspaceRevisionObject).where(
                        WorkspaceRevisionObject.revision_id == workspace_revision_id,
                        WorkspaceRevisionObject.object_type_key == object_type_key,
                    )
                )
            ),
            model=model,
            object_type_key=object_type_key,
            application_key=application_key,
            parent_object_id=parent_object_id,
            search=search,
            sort=sort,
            filters=filters,
        )
        page, next_cursor = paginate_sequence(
            rows,
            identity,
            scope="objects-revision",
            filters={
                "revisionId": workspace_revision_id,
                "objectTypeKey": object_type_key,
                "applicationKey": application_key,
                "parentObjectId": parent_object_id,
                "search": search,
                "sort": sort_field,
                "descending": descending,
                "typedFilters": filters,
            },
            cursor=cursor,
            page_size=page_size,
            sort=(("-" if descending else "") + sort_field, "id"),
            descending=descending,
            message="Object cursor is invalid",
        )
        return ObjectPage(
            items=[
                _draft_object_response(x, workspace_revision_id, model).model_copy(
                    update={"workspaceKey": revision.workspace_key}
                )
                for x in page
            ],
            nextCursor=next_cursor,
        )
    workspace = resolve_workspace(session, workspace_key)
    workspace_key = workspace.key
    query = build_object_query(
        model,
        object_type_key=object_type_key,
        application_key=application_key or None,
        workspace_key=workspace_key,
        parent_object_id=parent_object_id or None,
        search=search or None,
        sort=sort,
        field_filters=_field_filters(request),
    )
    objects, next_cursor = paginate_statement(
        session,
        query.statement,
        keys=query.keys,
        scope="objects",
        filters=query.filters,
        cursor=cursor,
        page_size=page_size,
        message="Object cursor is invalid",
    )
    return ObjectPage(items=build_object_responses(session, model, objects), nextCursor=next_cursor)


def _field_filters(request: Request) -> list[tuple[str, str, str]]:
    result: list[tuple[str, str, str]] = []
    for key, value in request.query_params.multi_items():
        if not key.startswith("filter."):
            continue
        field_operator = key.removeprefix("filter.")
        if "." not in field_operator:
            raise api_error(
                422,
                "invalid_filter",
                f"Invalid filter parameter '{key}'",
                {"path": f"/query/{key}"},
            )
        field, operator = field_operator.rsplit(".", 1)
        if not field or not operator:
            raise api_error(
                422,
                "invalid_filter",
                f"Invalid filter parameter '{key}'",
                {"path": f"/query/{key}"},
            )
        result.append((field, operator, value))
    return result


@router.get("/objects/{object_type_key}/{object_id}", response_model=ObjectResponse)
def get_object(
    object_type_key: str,
    object_id: str,
    session: DbSession,
    snapshot: RequestModelSnapshot,
    workspace_key: str | None = Query(default=None, alias="workspaceKey"),
    workspace_draft_id: str | None = Query(default=None, alias="workspaceDraftId"),
    workspace_revision_id: str | None = Query(default=None, alias="workspaceRevisionId"),
) -> ObjectResponse:
    model = snapshot.model
    get_object_type(model, object_type_key)
    if workspace_draft_id and workspace_revision_id:
        raise api_error(
            422,
            "mutually_exclusive_context",
            "workspaceDraftId and workspaceRevisionId cannot be combined",
        )
    if workspace_draft_id:
        membership = effective_draft_membership(session, workspace_draft_id)
        item = next(
            (
                x
                for x in membership.objects
                if x.object_id == object_id and x.object_type_key == object_type_key
            ),
            None,
        )
        if item is None:
            raise api_error(404, "object_not_found", f"Object '{object_id}' not found")
        return _draft_object_response(item, workspace_draft_id, model).model_copy(
            update={"workspaceKey": membership.draft.workspace_key}
        )
    if workspace_revision_id:
        revision = session.scalar(
            select(WorkspaceRevision).where(WorkspaceRevision.id == workspace_revision_id)
        )
        if revision is None:
            raise api_error(404, "workspace_revision_not_found", "Workspace revision not found")
        item = session.scalar(
            select(WorkspaceRevisionObject).where(
                WorkspaceRevisionObject.revision_id == workspace_revision_id,
                WorkspaceRevisionObject.object_id == object_id,
                WorkspaceRevisionObject.object_type_key == object_type_key,
            )
        )
        if item is None:
            raise api_error(404, "object_not_found", f"Object '{object_id}' not found")
        return _draft_object_response(item, workspace_revision_id, model).model_copy(
            update={"workspaceKey": revision.workspace_key}
        )
    selected_workspace_key = resolve_workspace(session, workspace_key).key
    item = load_active_projection(session, object_id, object_type_key)
    if item.workspace_key != selected_workspace_key:
        raise api_error(404, "object_not_found", f"Object '{object_id}' not found")
    return build_object_responses(session, model, [item])[0]


@router.get("/objects/{object_type_key}/{object_id}/history", response_model=AuditEventPage)
def get_object_history(
    object_type_key: str,
    object_id: str,
    session: DbSession,
    cursor: str | None = None,
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
    workspace_draft_id: str | None = Query(default=None, alias="workspaceDraftId"),
) -> AuditEventPage:
    if workspace_draft_id:
        snapshot = resolve_draft_snapshot(session, workspace_draft_id)
        get_object_type(snapshot.model, object_type_key)
        membership = effective_draft_membership(session, workspace_draft_id)
        item = next(
            (
                candidate
                for candidate in membership.objects
                if candidate.object_id == object_id and candidate.object_type_key == object_type_key
            ),
            None,
        )
        if item is None:
            raise api_error(404, "object_not_found", f"Object '{object_id}' not found")
        return list_object_history(
            session,
            object_id=item.object_id,
            object_type_key=item.object_type_key,
            workspace_key=membership.draft.workspace_key,
            cursor=cursor,
            page_size=page_size,
        )
    snapshot = resolve_model_snapshot(session)
    get_object_type(snapshot.model, object_type_key)
    item = load_object(session, object_id, object_type_key)
    return list_object_history(
        session,
        object_id=item.id,
        object_type_key=item.object_type_key,
        workspace_key=item.workspace_key,
        cursor=cursor,
        page_size=page_size,
    )
