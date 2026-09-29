"""Mapping-grid queries; configuration and orchestration live in the service."""

from dataclasses import dataclass
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from ...engine.operations.mapping_replacement import MappingVersionConflict, replace_mapping
from ...errors import api_error
from ...models.commands import MappingReplacementRequest
from ...models.schema import MappingGridViewConfig
from ..dependencies import DbSession
from ..paging import PageQuery, SeekablePageQuery
from ..projections.mapping import (
    MappingRead,
    candidates,
    conflict_continuation,
    coverage,
    list_mappings,
    open_mapping_read,
    target_details,
    validate_binding,
)
from ..schemas.mapping import (
    MappingCandidatePage,
    MappingCoveragePage,
    MappingListPage,
    MappingReplacementResponse,
    MappingTargetPage,
)

router = APIRouter(prefix="/api/v1/workspaces/{workspace_key}", tags=["mapping"])


def mapping_read(
    workspace_key: str,
    session: DbSession,
    application_key: str = Query(alias="applicationKey"),
    view_key: str = Query(alias="viewKey"),
    change_set_id: str | None = Query(default=None, alias="changeSetId"),
    publication_id: str | None = Query(default=None, alias="publicationId"),
) -> MappingRead:
    if change_set_id and publication_id:
        raise api_error(
            422,
            "mutually_exclusive_context",
            "changeSetId and publicationId cannot be combined",
        )
    return open_mapping_read(
        session,
        workspace_key,
        application_key,
        view_key,
        change_set_id,
        publication_id=publication_id,
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
    paging: SeekablePageQuery,
    search: str | None = Query(default=None, max_length=500),
    parent_object_id: str | None = Query(default=None, alias="parentObjectId"),
    state: Literal["mapped", "unmapped", "ambiguous"] | None = Query(default=None),
    page_size: int | None = Query(default=None, ge=1, le=100, alias="pageSize"),
) -> MappingCoveragePage:
    return coverage(read, search, paging, page_size, parent_object_id, state)


@dataclass(frozen=True)
class EdgeListQuery:
    workspace_key: str
    application_key: str | None
    view_key: str | None
    relation_type_key: str | None
    from_object_type_key: str | None
    to_object_type_key: str | None
    direction: Literal["outgoing", "incoming"] | None
    change_set_id: str | None
    publication_id: str | None
    search: str | None
    page_size: int | None


def edge_list_query(
    workspace_key: str,
    application_key: str | None = Query(default=None, alias="applicationKey"),
    view_key: str | None = Query(default=None, alias="viewKey"),
    relation_type_key: str | None = Query(default=None, alias="relationTypeKey"),
    from_object_type_key: str | None = Query(default=None, alias="fromObjectTypeKey"),
    to_object_type_key: str | None = Query(default=None, alias="toObjectTypeKey"),
    direction: Literal["outgoing", "incoming"] | None = Query(default=None),
    change_set_id: str | None = Query(default=None, alias="changeSetId"),
    publication_id: str | None = Query(default=None, alias="publicationId"),
    search: str | None = Query(default=None, max_length=500),
    page_size: int | None = Query(default=None, ge=1, le=100, alias="pageSize"),
) -> EdgeListQuery:
    if change_set_id and publication_id:
        raise api_error(
            422,
            "mutually_exclusive_context",
            "changeSetId and publicationId cannot be combined",
        )
    return EdgeListQuery(
        workspace_key,
        application_key,
        view_key,
        relation_type_key,
        from_object_type_key,
        to_object_type_key,
        direction,
        change_set_id,
        publication_id,
        search,
        page_size,
    )


EdgeList = Annotated[EdgeListQuery, Depends(edge_list_query)]


def edge_list(
    session: DbSession, query: EdgeListQuery, paging: PageQuery, scope: str
) -> MappingListPage:
    return list_mappings(
        session,
        query.workspace_key,
        scope=scope,
        change_set_id=query.change_set_id,
        publication_id=query.publication_id,
        application_key=query.application_key,
        view_key=query.view_key,
        relation_type_key=query.relation_type_key,
        from_object_type_key=query.from_object_type_key,
        to_object_type_key=query.to_object_type_key,
        direction=query.direction,
        search=query.search,
        page=paging,
        page_size=query.page_size,
    )


@router.get("/mappings", response_model=MappingListPage)
def get_mappings(session: DbSession, query: EdgeList, paging: PageQuery) -> MappingListPage:
    return edge_list(session, query, paging, "mapping-list")


@router.get("/relations", response_model=MappingListPage, tags=["relations"])
def get_workspace_relations(
    session: DbSession, query: EdgeList, paging: PageQuery
) -> MappingListPage:
    """The workspace edge list: every relation of any type, in live data, a change set or a
    publication. The same list as ``/mappings``; its cursors are its own."""
    return edge_list(session, query, paging, "workspace-relations")


@router.get("/mapping-candidates", response_model=MappingCandidatePage)
def mapping_candidates(
    read: Read,
    paging: PageQuery,
    object_type_key: str = Query(alias="objectTypeKey"),
    search: str | None = Query(default=None, max_length=500),
    page_size: int | None = Query(default=None, ge=1, le=100, alias="pageSize"),
) -> MappingCandidatePage:
    return candidates(read, object_type_key, search, paging, page_size)


def target_binding_read(
    workspace_key: str,
    session: DbSession,
    relation_type_key: str = Query(alias="relationTypeKey"),
    from_type: str = Query(alias="fromObjectTypeKey"),
    to_type: str = Query(alias="toObjectTypeKey"),
    direction: Literal["outgoing", "incoming"] = Query(),
    application_key: str | None = Query(default=None, alias="applicationKey"),
    view_key: str | None = Query(default=None, alias="viewKey"),
    change_set_id: str | None = Query(default=None, alias="changeSetId"),
    publication_id: str | None = Query(default=None, alias="publicationId"),
) -> MappingRead:
    if change_set_id and publication_id:
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
        change_set_id,
        publication_id=publication_id,
        binding_config=config,
    )
    validate_binding(read, relation_type_key, from_type, to_type, direction)
    return read


TargetRead = Annotated[MappingRead, Depends(target_binding_read)]


@router.get("/mapping-targets", response_model=MappingTargetPage)
def mapping_targets(
    read: TargetRead,
    paging: PageQuery,
    source_object_id: str = Query(alias="sourceObjectId"),
    mapping_version: int = Query(ge=0, alias="mappingVersion"),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
) -> MappingTargetPage:
    return target_details(read, source_object_id, mapping_version, paging, page_size)


@router.put("/mappings", response_model=MappingReplacementResponse)
def put_mapping(
    workspace_key: str,
    body: MappingReplacementRequest,
    session: DbSession,
) -> MappingReplacementResponse:
    try:
        result = replace_mapping(session, workspace_key, body)
    except MappingVersionConflict as conflict:
        if conflict.continuation is not None:
            conflict.details.update(conflict_continuation(session, conflict.continuation))
        raise
    return MappingReplacementResponse(
        sourceObjectId=result.source_object_id,
        mappingVersion=result.mapping_version,
        state=result.state,
        relationId=result.relation_id,
        changeSetVersion=result.change_set_version,
    )
