from fastapi import APIRouter, Query, status
from sqlalchemy import select

from ..db import DbSession
from ..errors import ApiError, api_error
from ..models.api import (
    ChangeSetCreate,
    ChangeSetModelReleaseUpdate,
    ChangeSetPage,
    ChangeSetPublishRequest,
    ChangeSetResponse,
    ChangeSetUpdate,
    ChangeSetValidation,
    PublicationPage,
    PublicationResponse,
)
from ..models.database import ChangeSet, ModelRelease, Publication
from ..services.change_sets import (
    create_change_set,
    discard_change_set,
    effective_change_set_membership,
    pinned_model,
    publish_change_set,
    selected_change_set_release,
    set_change_set_model_release,
    update_change_set,
    validate_change_set,
    withdraw_publication,
)
from ..services.model.registry import ActiveModelSnapshot, resolve_model_snapshot
from ..services.model.runtime import load_runtime_state
from ..services.pagination import integer_key, paginate_sequence, paginate_statement, text_key
from ..services.workspace_audit import record_change_set_validated
from ..services.workspaces import load_workspace
from .paging import PageQuery

# The change-set workflow is an ordinary steward operation like a live edit (ADR-031): always
# registered, and refused in a retired workspace by the services it calls. Only workspace catalogue
# administration sits behind WORKSPACE_ADMIN_MUTATIONS_ENABLED.
router = APIRouter(prefix="/api/v1", tags=["change-sets"])


def _change_set_response(session, item: ChangeSet) -> ChangeSetResponse:
    release = session.get(ModelRelease, item.model_release_id)
    source = (
        "currentLive"
        if item.base_id is not None
        else "publication"
        if item.derived_from_publication_id
        else "empty"
    )
    return ChangeSetResponse(
        id=item.id,
        workspaceKey=item.workspace_key,
        name=item.name,
        modelReleaseId=release.public_id if release else str(item.model_release_id),
        modelReleaseKey=release.release_key if release else "unavailable",
        modelReleaseVersion=release.release_version if release else "unavailable",
        source=source,
        derivedFromPublicationId=item.derived_from_publication_id,
        version=item.version,
        createdAt=item.created_at,
        updatedAt=item.updated_at,
    )


def _publication_response(session, item: Publication) -> PublicationResponse:
    release = session.get(ModelRelease, item.model_release_id)
    return PublicationResponse(
        id=item.id,
        workspaceKey=item.workspace_key,
        modelReleaseId=release.public_id if release else str(item.model_release_id),
        modelReleaseKey=release.release_key if release else "unavailable",
        modelReleaseVersion=release.release_version if release else "unavailable",
        publicationNumber=item.publication_number,
        status=item.status,
        derivedFromPublicationId=item.derived_from_publication_id,
        supersedesPublicationId=item.supersedes_publication_id,
        createdAt=item.created_at,
        publishedAt=item.published_at,
        withdrawnAt=item.withdrawn_at,
    )


@router.get("/workspaces/{workspace_key}/change-sets", response_model=ChangeSetPage)
def list_change_sets(
    workspace_key: str,
    session: DbSession,
    paging: PageQuery,
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
) -> ChangeSetPage:
    load_workspace(session, workspace_key)
    items = list(
        session.scalars(select(ChangeSet).where(ChangeSet.workspace_key == workspace_key))
    )
    page = paginate_sequence(
        items,
        lambda x: (x.created_at.isoformat(), x.id),
        scope="change-sets",
        filters={"workspaceKey": workspace_key},
        page=paging,
        page_size=page_size,
        sort=("createdAt", "id"),
        message="Change set cursor is invalid",
    )
    return ChangeSetPage(
        items=[_change_set_response(session, x) for x in page.items], **page.links()
    )


@router.post(
    "/workspaces/{workspace_key}/change-sets",
    response_model=ChangeSetResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_change_set(
    workspace_key: str,
    payload: ChangeSetCreate,
    session: DbSession,
) -> ChangeSetResponse:
    selected = (
        selected_change_set_release(session, str(payload.modelReleaseId))
        if payload.modelReleaseId
        else None
    )
    active_release_id = (
        load_runtime_state(session)[1].id
        if selected
        else resolve_model_snapshot(session).release_db_id
    )
    return _change_set_response(
        session,
        create_change_set(
            session,
            workspace_key,
            selected.id if selected else active_release_id,
            name=payload.name,
            source_publication_id=str(payload.derivedFromPublicationId)
            if payload.derivedFromPublicationId
            else None,
            source=payload.source,
            expected_model_runtime_release_id=active_release_id,
            validate_selected_model=selected is not None,
        ),
    )


@router.get("/change-sets/{change_set_id}", response_model=ChangeSetResponse)
def get_change_set(change_set_id: str, session: DbSession) -> ChangeSetResponse:
    # ChangeSet's ORM primary key is the autoincrement sequence_id, so session.get by the
    # stable public id would always miss; resolve through the unique id column instead.
    item = session.scalar(select(ChangeSet).where(ChangeSet.id == change_set_id))
    if item is None:
        raise api_error(404, "change_set_not_found", "Change set not found")
    return _change_set_response(session, item)


@router.patch("/change-sets/{change_set_id}", response_model=ChangeSetResponse)
def patch_change_set(
    change_set_id: str, payload: ChangeSetUpdate, session: DbSession
) -> ChangeSetResponse:
    return _change_set_response(
        session, update_change_set(session, change_set_id, payload.expectedVersion, payload.name)
    )


@router.patch(
    "/change-sets/{change_set_id}/model-release", response_model=ChangeSetResponse
)
def patch_change_set_model_release(
    change_set_id: str, payload: ChangeSetModelReleaseUpdate, session: DbSession
) -> ChangeSetResponse:
    return _change_set_response(
        session,
        set_change_set_model_release(
            session,
            change_set_id,
            str(payload.modelReleaseId),
            payload.expectedChangeSetVersion,
        ),
    )


@router.delete("/change-sets/{change_set_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_change_set(
    change_set_id: str, session: DbSession, expected_version: int = Query(alias="expectedVersion", ge=1)
) -> None:
    discard_change_set(session, change_set_id, expected_version)


@router.post(
    "/change-sets/{change_set_id}/validation", response_model=ChangeSetValidation
)
def post_change_set_validation(change_set_id: str, session: DbSession) -> ChangeSetValidation:
    change_set, change_set_model = pinned_model(session, change_set_id)
    diagnostics = validate_change_set(session, change_set_id, change_set_model)
    # A validation never mutates the change set graph or bumps its version; the audit record is its only
    # side effect and is bounded to identity metadata plus counts (see D3a).  The conflict
    # short-circuit can leave a corrupt base unresolved, so fall back to zero counts instead of
    # failing a validation that already reported its diagnostic.
    try:
        membership = effective_change_set_membership(session, change_set_id)
        object_count, relation_count = len(membership.objects), len(membership.relations)
    except ApiError:
        object_count, relation_count = 0, 0
    record_change_set_validated(
        session,
        change_set=change_set,
        valid=not diagnostics,
        error_codes=[item["code"] for item in diagnostics],
        object_count=object_count,
        relation_count=relation_count,
        error_count=len(diagnostics),
    )
    session.commit()
    return ChangeSetValidation(valid=not diagnostics, diagnostics=diagnostics)


@router.post(
    "/change-sets/{change_set_id}/publication", response_model=PublicationResponse
)
def post_change_set_publication(
    change_set_id: str,
    payload: ChangeSetPublishRequest,
    session: DbSession,
    snapshot: ActiveModelSnapshot,
) -> PublicationResponse:
    _change_set, change_set_model = pinned_model(session, change_set_id)
    publication = publish_change_set(
        session,
        change_set_id,
        change_set_model,
        snapshot.release_db_id,
        payload.expectedChangeSetVersion,
        str(payload.expectedActivePublicationId) if payload.expectedActivePublicationId else None,
    )
    return _publication_response(session, publication)


@router.get("/workspaces/{workspace_key}/publications", response_model=PublicationPage)
def list_publications(
    workspace_key: str,
    session: DbSession,
    paging: PageQuery,
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
) -> PublicationPage:
    load_workspace(session, workspace_key)
    page = paginate_statement(
        session,
        select(Publication).where(Publication.workspace_key == workspace_key),
        keys=(
            integer_key(
                "publicationNumber",
                Publication.publication_number,
                "publication_number",
                descending=True,
            ),
            text_key("id", Publication.id, "id", descending=True),
        ),
        scope="publications",
        filters={"workspaceKey": workspace_key},
        page=paging,
        page_size=page_size,
        message="Publication cursor is invalid",
    )
    return PublicationPage(
        items=[_publication_response(session, x) for x in page.items], **page.links()
    )


@router.get("/publications/{publication_id}", response_model=PublicationResponse)
def get_publication(publication_id: str, session: DbSession) -> PublicationResponse:
    item = session.scalar(select(Publication).where(Publication.id == publication_id))
    if item is None:
        raise api_error(404, "publication_not_found", "Publication not found")
    return _publication_response(session, item)


@router.post(
    "/publications/{publication_id}/withdrawal", status_code=status.HTTP_204_NO_CONTENT
)
def post_publication_withdrawal(publication_id: str, session: DbSession) -> None:
    withdraw_publication(session, publication_id)
