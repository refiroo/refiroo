"""Mapping-grid queries; configuration and orchestration live in the service."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from ..db import DbSession
from ..models.api import MappingCandidatePage, MappingCoveragePage, MappingTargetPage
from ..services.mapping import (
    MappingRead,
    candidates,
    coverage,
    open_mapping_read,
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
) -> MappingRead:
    return open_mapping_read(session, workspace_key, application_key, view_key, workspace_draft_id)


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
    cursor: str | None = None,
    page_size: int | None = Query(default=None, ge=1, le=100, alias="pageSize"),
) -> MappingCoveragePage:
    return coverage(read, search, cursor, page_size)


@router.get("/mapping-candidates", response_model=MappingCandidatePage)
def mapping_candidates(
    read: Read,
    object_type_key: str = Query(alias="objectTypeKey"),
    search: str | None = Query(default=None, max_length=500),
    cursor: str | None = None,
    page_size: int | None = Query(default=None, ge=1, le=100, alias="pageSize"),
) -> MappingCandidatePage:
    return candidates(read, object_type_key, search, cursor, page_size)


@router.get("/mapping-targets", response_model=MappingTargetPage)
def mapping_targets(
    read: BindingRead,
    source_object_id: str = Query(alias="sourceObjectId"),
    mapping_version: int = Query(ge=0, alias="mappingVersion"),
    cursor: str | None = None,
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
) -> MappingTargetPage:
    return target_details(read, source_object_id, mapping_version, cursor, page_size)
