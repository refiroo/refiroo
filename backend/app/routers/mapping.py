"""Mapping-grid queries; configuration and orchestration live in the service."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from ..db import DbSession
from ..errors import api_error
from ..models.api import (
    MappingCandidatePage,
    MappingCoveragePage,
    MappingListPage,
    MappingReplacementRequest,
    MappingReplacementResponse,
    MappingTargetPage,
)
from ..models.schema import MappingGridViewConfig
from ..services.mapping import (
    MappingRead,
    candidates,
    coverage,
    list_mappings,
    open_mapping_read,
    replace_mapping,
    target_details,
    validate_binding,
)

router = APIRouter(prefix="/api/v1/workspaces/{workspace_key}", tags=["mapping"])


def mapping_read(
    workspace_key: str,
    session: DbSession,
    application_key: str = Query(alias="applicationKey"),
    view_key: str = Query(alias="viewKey"),
    workspace_draft_id: str | None = Query(default=None, alias="workspaceDraftId"),
    workspace_revision_id: str | None = Query(default=None, alias="workspaceRevisionId"),
) -> MappingRead:
    if workspace_draft_id and workspace_revision_id:
        raise api_error(
            422,
            "mutually_exclusive_context",
            "workspaceDraftId and workspaceRevisionId cannot be combined",
        )
    return open_mapping_read(
        session,
        workspace_key,
        application_key,
        view_key,
        workspace_draft_id,
        revision_id=workspace_revision_id,
    )


Read = Annotated[MappingRead, Depends(mapping_read)]


def binding_read(
    read: Read,
    relation_type_key: str = Query(alias="relationTypeKey"),
    from_object_type_key: str = Query(alias="fromObjectTypeKey"),
    to_object_type_key: str = Query(alias="toObjectTypeKey"),
    direction: Literal["outgoing", "incoming"] = Query(),
) -> MappingRead:
    validate_binding(read, relation_type_key, from_object_type_key, to_object_type_key, direction)
    return read


BindingRead = Annotated[MappingRead, Depends(binding_read)]


@router.get("/mapping-coverage", response_model=MappingCoveragePage)
def mapping_coverage(
    read: BindingRead,
    search: str | None = Query(default=None, max_length=500),
    parent_object_id: str | None = Query(default=None, alias="parentObjectId"),
    state: Literal["mapped", "unmapped", "ambiguous"] | None = Query(default=None),
    cursor: str | None = None,
    page_size: int | None = Query(default=None, ge=1, le=100, alias="pageSize"),
) -> MappingCoveragePage:
    return coverage(read, search, cursor, page_size, parent_object_id, state)


@router.get("/mappings", response_model=MappingListPage)
def get_mappings(
    workspace_key: str,
    session: DbSession,
    application_key: str | None = Query(default=None, alias="applicationKey"),
    view_key: str | None = Query(default=None, alias="viewKey"),
    relation_type_key: str | None = Query(default=None, alias="relationTypeKey"),
    from_object_type_key: str | None = Query(default=None, alias="fromObjectTypeKey"),
    to_object_type_key: str | None = Query(default=None, alias="toObjectTypeKey"),
    direction: Literal["outgoing", "incoming"] | None = Query(default=None),
    workspace_draft_id: str | None = Query(default=None, alias="workspaceDraftId"),
    search: str | None = Query(default=None, max_length=500),
    cursor: str | None = None,
    page_size: int | None = Query(default=None, ge=1, le=100, alias="pageSize"),
) -> MappingListPage:
    return list_mappings(
        session,
        workspace_key,
        draft_id=workspace_draft_id,
        application_key=application_key,
        view_key=view_key,
        relation_type_key=relation_type_key,
        from_object_type_key=from_object_type_key,
        to_object_type_key=to_object_type_key,
        direction=direction,
        search=search,
        cursor=cursor,
        page_size=page_size,
    )


@router.get("/mapping-candidates", response_model=MappingCandidatePage)
def mapping_candidates(
    read: Read,
    object_type_key: str = Query(alias="objectTypeKey"),
    search: str | None = Query(default=None, max_length=500),
    cursor: str | None = None,
    page_size: int | None = Query(default=None, ge=1, le=100, alias="pageSize"),
) -> MappingCandidatePage:
    return candidates(read, object_type_key, search, cursor, page_size)


def target_binding_read(
    workspace_key: str,
    session: DbSession,
    relation_type_key: str = Query(alias="relationTypeKey"),
    from_type: str = Query(alias="fromObjectTypeKey"),
    to_type: str = Query(alias="toObjectTypeKey"),
    direction: Literal["outgoing", "incoming"] = Query(),
    application_key: str | None = Query(default=None, alias="applicationKey"),
    view_key: str | None = Query(default=None, alias="viewKey"),
    draft_id: str | None = Query(default=None, alias="workspaceDraftId"),
    revision_id: str | None = Query(default=None, alias="workspaceRevisionId"),
) -> MappingRead:
    if draft_id and revision_id:
        raise api_error(422, "mutually_exclusive_context", "Workspace contexts cannot be combined")
    if (application_key is None) != (view_key is None):
        raise api_error(422, "mapping_view_required", "Supply applicationKey and viewKey together")
    config = (
        None
        if application_key is not None
        else MappingGridViewConfig(
            relationTypeKey=relation_type_key,
            fromObjectTypeKey=from_type,
            toObjectTypeKey=to_type,
            direction=direction,
            sourceColumns=("name",),
            targetDisplayColumns=("name",),
            candidateSearchFields=("name",),
            pageSize=20,
        )
    )
    read = open_mapping_read(
        session,
        workspace_key,
        application_key,
        view_key,
        draft_id,
        revision_id=revision_id,
        binding_config=config,
    )
    validate_binding(read, relation_type_key, from_type, to_type, direction)
    return read


TargetRead = Annotated[MappingRead, Depends(target_binding_read)]


@router.get("/mapping-targets", response_model=MappingTargetPage)
def mapping_targets(
    read: TargetRead,
    source_object_id: str = Query(alias="sourceObjectId"),
    mapping_version: int = Query(ge=0, alias="mappingVersion"),
    cursor: str | None = None,
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
) -> MappingTargetPage:
    return target_details(read, source_object_id, mapping_version, cursor, page_size)


@router.put("/mappings", response_model=MappingReplacementResponse)
def put_mapping(
    workspace_key: str,
    body: MappingReplacementRequest,
    session: DbSession,
) -> MappingReplacementResponse:
    return replace_mapping(session, workspace_key, body)
