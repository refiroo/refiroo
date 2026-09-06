from typing import Annotated

from fastapi import APIRouter, Query, Response, status
from pydantic import UUID4
from sqlalchemy import select

from ..db import DbSession
from ..models.api import (
    ObjectDraftActivationRequest,
    ObjectDraftCloneRequest,
    ObjectDraftCreate,
    ObjectDraftDeleteRequest,
    ObjectDraftPage,
    ObjectDraftResponse,
    ObjectDraftUpdate,
    ObjectRetirementImpactResponse,
    ObjectRetirementRequest,
    ObjectRetirementResponse,
    ObjectRevisionPage,
    ObjectRevisionResponse,
)
from ..models.database import ObjectDraft, ObjectRevision
from ..services.model.registry import ActiveModelSnapshot
from ..services.object_lifecycle import (
    activate_draft,
    clone_revision_to_draft,
    create_root_draft,
    discard_draft,
    draft_response,
    effective_model_release_id,
    load_draft,
    load_identity,
    load_revision,
    retire_active_revision,
    retirement_impact,
    revision_response,
    update_draft,
)
from ..services.pagination import datetime_key, integer_key, paginate_statement

router = APIRouter(prefix="/api/v1", tags=["object lifecycle"])

_DRAFT_KEYS = (
    datetime_key("updatedAt", ObjectDraft.updated_at, "updated_at", descending=True),
    integer_key("sequenceId", ObjectDraft.sequence_id, "sequence_id", descending=True),
)
_REVISION_KEYS = (
    integer_key(
        "revisionNumber",
        ObjectRevision.revision_number,
        "revision_number",
        descending=True,
    ),
    integer_key("sequenceId", ObjectRevision.sequence_id, "sequence_id", descending=True),
)


@router.post(
    "/object-drafts",
    response_model=ObjectDraftResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_object_draft(
    payload: ObjectDraftCreate,
    session: DbSession,
    snapshot: ActiveModelSnapshot,
) -> ObjectDraftResponse:
    draft = create_root_draft(
        session,
        snapshot.model,
        model_release_db_id=effective_model_release_id(session, snapshot.release_db_id),
        payload=payload,
    )
    return draft_response(session, draft)


@router.post(
    "/objects/{object_type_key}/{object_id}/drafts",
    response_model=ObjectDraftResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_object_draft_from_revision(
    object_type_key: str,
    object_id: str,
    payload: ObjectDraftCloneRequest,
    session: DbSession,
    snapshot: ActiveModelSnapshot,
) -> ObjectDraftResponse:
    draft = clone_revision_to_draft(
        session,
        snapshot.model,
        model_release_db_id=effective_model_release_id(session, snapshot.release_db_id),
        object_type_key=object_type_key,
        object_id=object_id,
        derived_from_revision_id=str(payload.derivedFromRevisionId),
    )
    return draft_response(session, draft)


@router.get(
    "/objects/{object_type_key}/{object_id}/drafts",
    response_model=ObjectDraftPage,
)
def list_object_drafts(
    object_type_key: str,
    object_id: str,
    session: DbSession,
    _snapshot: ActiveModelSnapshot,
    cursor: str | None = None,
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
) -> ObjectDraftPage:
    item = load_identity(session, object_id, object_type_key)
    statement = select(ObjectDraft).where(ObjectDraft.object_id == item.id)
    drafts, next_cursor = paginate_statement(
        session,
        statement,
        keys=_DRAFT_KEYS,
        scope="object-drafts",
        filters={
            "objectId": item.id,
            "objectTypeKey": item.object_type_key,
            "workspaceKey": item.workspace_key,
        },
        cursor=cursor,
        page_size=page_size,
        message="Object draft cursor is invalid",
    )
    return ObjectDraftPage(
        items=[draft_response(session, draft) for draft in drafts],
        nextCursor=next_cursor,
    )


@router.get("/object-drafts/{draft_id}", response_model=ObjectDraftResponse)
def get_object_draft(
    draft_id: str,
    session: DbSession,
    _snapshot: ActiveModelSnapshot,
) -> ObjectDraftResponse:
    return draft_response(session, load_draft(session, draft_id))


@router.patch("/object-drafts/{draft_id}", response_model=ObjectDraftResponse)
def patch_object_draft(
    draft_id: str,
    payload: ObjectDraftUpdate,
    session: DbSession,
    snapshot: ActiveModelSnapshot,
) -> ObjectDraftResponse:
    return draft_response(
        session, update_draft(session, snapshot.model, draft_id, payload)
    )


@router.delete("/object-drafts/{draft_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_object_draft(
    draft_id: str,
    payload: ObjectDraftDeleteRequest,
    session: DbSession,
    _snapshot: ActiveModelSnapshot,
) -> Response:
    discard_draft(session, draft_id, payload.expectedVersion)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/object-drafts/{draft_id}/activation",
    response_model=ObjectRevisionResponse,
)
def activate_object_draft(
    draft_id: str,
    payload: ObjectDraftActivationRequest,
    session: DbSession,
    snapshot: ActiveModelSnapshot,
) -> ObjectRevisionResponse:
    revision = activate_draft(
        session,
        snapshot.model,
        current_model_release_db_id=effective_model_release_id(
            session, snapshot.release_db_id
        ),
        draft_id=draft_id,
        payload=payload,
    )
    return revision_response(session, revision)


@router.get(
    "/objects/{object_type_key}/{object_id}/revisions",
    response_model=ObjectRevisionPage,
)
def list_object_revisions(
    object_type_key: str,
    object_id: str,
    session: DbSession,
    _snapshot: ActiveModelSnapshot,
    cursor: str | None = None,
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
) -> ObjectRevisionPage:
    item = load_identity(session, object_id, object_type_key)
    statement = select(ObjectRevision).where(ObjectRevision.object_id == item.id)
    revisions, next_cursor = paginate_statement(
        session,
        statement,
        keys=_REVISION_KEYS,
        scope="object-revisions",
        filters={
            "objectId": item.id,
            "objectTypeKey": item.object_type_key,
            "workspaceKey": item.workspace_key,
        },
        cursor=cursor,
        page_size=page_size,
        message="Object revision cursor is invalid",
    )
    return ObjectRevisionPage(
        items=[revision_response(session, revision) for revision in revisions],
        nextCursor=next_cursor,
    )


@router.get("/object-revisions/{revision_id}", response_model=ObjectRevisionResponse)
def get_object_revision(
    revision_id: str,
    session: DbSession,
    _snapshot: ActiveModelSnapshot,
) -> ObjectRevisionResponse:
    return revision_response(session, load_revision(session, revision_id))


@router.post(
    "/objects/{object_type_key}/{object_id}/retirement",
    response_model=ObjectRetirementResponse,
)
def retire_object_revision(
    object_type_key: str,
    object_id: str,
    payload: ObjectRetirementRequest,
    session: DbSession,
    snapshot: ActiveModelSnapshot,
) -> ObjectRetirementResponse:
    return retire_active_revision(
        session,
        snapshot.model,
        object_type_key=object_type_key,
        object_id=object_id,
        expected_active_revision_id=str(payload.expectedActiveRevisionId),
        cascade=payload.cascade,
    )


@router.get(
    "/objects/{object_type_key}/{object_id}/retirement-impact",
    response_model=ObjectRetirementImpactResponse,
)
def get_retirement_impact(
    object_type_key: str,
    object_id: str,
    session: DbSession,
    snapshot: ActiveModelSnapshot,
    expected_active_revision_id: Annotated[
        UUID4, Query(alias="expectedActiveRevisionId")
    ],
) -> ObjectRetirementImpactResponse:
    return retirement_impact(
        session,
        snapshot.model,
        object_type_key=object_type_key,
        object_id=object_id,
        expected_active_revision_id=str(expected_active_revision_id),
    )
