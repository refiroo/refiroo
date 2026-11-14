"""Mapping-grid queries; configuration and orchestration live in the service."""

from dataclasses import dataclass
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Request

from ...engine.operations.mapping_replacement import MappingVersionConflict, replace_mapping
from ...engine.proposals import mapping_job
from ...errors import api_error
from ...models.commands import MappingProposalRequest, MappingReplacementRequest
from ...models.schema import MappingGridViewConfig
from ..access import (
    MAPPING_PROPOSAL,
    MAPPINGS_WRITE,
    WORKSPACE_PATH,
    AuthorizedRoute,
    requires,
)
from ..ai import ai_requested
from ..dependencies import DbSession
from ..paging import PageQuery, PageSize, SeekablePageQuery
from ..presenters import job_responses
from ..projections.mapping import (
    MappingRead,
    candidates,
    conflict_continuation,
    coverage,
    list_mappings,
    open_mapping_read,
    relation_grid,
    target_details,
    validate_binding,
)
from ..query_parameters import accepts_field_filters, field_filters
from ..schemas.jobs import JobResponse
from ..schemas.mapping import (
    MappingCandidatePage,
    MappingCoveragePage,
    MappingListPage,
    MappingReplacementResponse,
    MappingTargetPage,
    RelationGridPage,
)

router = APIRouter(
    route_class=AuthorizedRoute, prefix="/api/v1/workspaces/{workspace_key}", tags=["mapping"]
)


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
            "MUTUALLY_EXCLUSIVE_CONTEXT",
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
@requires("records.read", at=WORKSPACE_PATH)
def mapping_coverage(
    read: BindingRead,
    paging: SeekablePageQuery,
    search: str | None = Query(default=None, max_length=500),
    parent_object_id: str | None = Query(default=None, alias="parentObjectId"),
    state: Literal["mapped", "unmapped", "ambiguous"] | None = Query(
        default=None,
        description="Coverage state. ambiguous (two or more targets) exists only where the "
        "source end holds at most one target; elsewhere several targets are mapped",
    ),
    proposed: bool = Query(
        default=False,
        description="Only sources with a target the AI proposed and nobody has changed since "
        "(needs changeSetId, else 422 MAPPING_PROPOSED_NEEDS_CHANGE_SET)",
    ),
    page_size: int | None = PageSize(None, 100),
) -> MappingCoveragePage:
    return coverage(read, search, paging, page_size, parent_object_id, state, proposed)


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
    from_object_id: str | None = None
    to_object_id: str | None = None
    sort: str | None = None
    field_filters: tuple[tuple[str, str, str], ...] = ()


def edge_list_query(
    request: Request,
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
    page_size: int | None = PageSize(None, 100),
    from_object_id: str | None = Query(
        default=None, alias="fromObjectId", description="Only relationships from this record"
    ),
    to_object_id: str | None = Query(
        default=None, alias="toObjectId", description="Only relationships to this record"
    ),
    sort: str | None = Query(
        default=None,
        description=(
            "A relationships table's sort field, one of the view's sortFields (from:<field>,"
            " to:<field> or relation:<attribute>); prefix '-' for descending; the view's"
            " defaultSort when omitted. Needs applicationKey and viewKey naming a relationships"
            " table"
        ),
    ),
) -> EdgeListQuery:
    if change_set_id and publication_id:
        raise api_error(
            422,
            "MUTUALLY_EXCLUSIVE_CONTEXT",
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
        from_object_id,
        to_object_id,
        sort,
        tuple(field_filters(request)),
    )


EdgeList = Annotated[EdgeListQuery, Depends(edge_list_query)]


def edge_list(
    session: DbSession, query: EdgeListQuery, paging: SeekablePageQuery, scope: str
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
        from_object_id=query.from_object_id,
        to_object_id=query.to_object_id,
        sort=query.sort,
        field_filters=list(query.field_filters),
        page=paging,
        page_size=query.page_size,
    )


@router.get(
    "/relations",
    response_model=MappingListPage,
    tags=["relations"],
    openapi_extra={
        "parameters": [
            {
                "name": "filter.<field>.<operator>",
                "in": "query",
                "required": False,
                "description": (
                    "Repeatable, on a relationships table (applicationKey and viewKey naming one)"
                    " only: filter.<ref>.eq=<value>, <ref> one of the view's filterFields"
                    " (from:<field>, to:<field>, relation:<attribute>). Equalities on one field"
                    " are alternatives; different fields all must hold"
                ),
                "schema": {"type": "string"},
            }
        ]
    },
)
@accepts_field_filters
@requires("records.read", at=WORKSPACE_PATH)
def get_workspace_relations(
    session: DbSession, query: EdgeList, paging: SeekablePageQuery
) -> MappingListPage:
    """The workspace edge list: every relation of any type, in live data, a change set or a
    publication. ``GET /mappings``, the same list under another name, was removed (H4c, D-1).
    With the applicationKey and viewKey of a relationships table it lists that view's rows: the
    ends' ``fromColumns`` and ``toColumns``, each row's ``relationVersion``, ``sort`` and the
    field filters over the view's ``sortFields`` and ``filterFields``, and ``groupCounts`` with
    ``groupBy``."""
    return edge_list(session, query, paging, "workspace-relations")


@router.get(
    "/relation-grid",
    response_model=RelationGridPage,
    tags=["relations"],
    openapi_extra={
        "parameters": [
            {
                "name": "filter.<field>.<operator>",
                "in": "query",
                "required": False,
                "description": (
                    "Repeatable: filter.<ref>.eq=<value>, <ref> one of the view's filterFields."
                    " from:<field> narrows the rows, to:<field> the column groups and"
                    " relation:<attribute> keeps the rows with a relationship to a shown column"
                    " record that holds the value"
                ),
                "schema": {"type": "string"},
            }
        ]
    },
)
@accepts_field_filters
@requires("records.read", at=WORKSPACE_PATH)
def get_relation_grid(
    request: Request,
    workspace_key: str,
    session: DbSession,
    paging: SeekablePageQuery,
    application_key: str = Query(alias="applicationKey"),
    view_key: str = Query(alias="viewKey"),
    change_set_id: str | None = Query(default=None, alias="changeSetId"),
    publication_id: str | None = Query(default=None, alias="publicationId"),
    to_object_ids: Annotated[
        list[str] | None,
        Query(
            alias="toObjectId",
            description="Repeatable: show only these column records (still narrowed by the to:"
            " filters); none shows every matching record, at most 50",
        ),
    ] = None,
    attributes: Annotated[
        list[str] | None,
        Query(
            alias="attribute",
            description="Repeatable: return only these relationship attributes, from the view's"
            " attributeColumns; none returns every stored value of the relationship",
        ),
    ] = None,
    search: str | None = Query(
        default=None, max_length=500, description="Search the row records, as the object list of their type searches"
    ),
    to_search: str | None = Query(
        default=None,
        alias="toSearch",
        max_length=500,
        description="Search the column records, as the object list of their type searches",
    ),
    sort: str | None = Query(
        default=None,
        description="One of the view's sortFields, '-' for descending; only from:<field> orders"
        " the rows, any other falls back to the record's name. The view's defaultSort when omitted",
    ),
    page_size: int | None = PageSize(None, 100),
) -> RelationGridPage:
    """A relationships table as a grid (layout ``grid``, 0.13 RG): each record of the view's
    ``from`` type once, linked or not, with its relationships to the shown ``to`` records, and
    those column groups (``columns``, at most 50 of ``columnTotal``) with how many of the rows
    each is related to. Rows page by cursor, position or seek, in live data, a change set (a
    relationship it stages is ``proposed``) or a publication."""
    if change_set_id and publication_id:
        raise api_error(
            422,
            "MUTUALLY_EXCLUSIVE_CONTEXT",
            "changeSetId and publicationId cannot be combined",
        )
    return relation_grid(
        session,
        workspace_key,
        application_key,
        view_key,
        scope="relation-grid",
        change_set_id=change_set_id,
        publication_id=publication_id,
        to_object_ids=list(dict.fromkeys(to_object_ids or [])),
        attributes=attributes,
        field_filters=field_filters(request),
        search=search,
        to_search=to_search,
        sort=sort,
        page=paging,
        page_size=page_size,
    )


@router.get("/mapping-candidates", response_model=MappingCandidatePage)
@requires("records.read", at=WORKSPACE_PATH)
def mapping_candidates(
    read: Read,
    paging: PageQuery,
    object_type_key: str = Query(alias="objectTypeKey"),
    search: str | None = Query(default=None, max_length=500),
    page_size: int | None = PageSize(None, 100),
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
        raise api_error(422, "MUTUALLY_EXCLUSIVE_CONTEXT", "Workspace contexts cannot be combined")
    if (application_key is None) != (view_key is None):
        raise api_error(422, "MAPPING_VIEW_REQUIRED", "Supply applicationKey and viewKey together")
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
@requires("records.read", at=WORKSPACE_PATH)
def mapping_targets(
    read: TargetRead,
    paging: PageQuery,
    source_object_id: str = Query(alias="sourceObjectId"),
    mapping_version: int = Query(ge=0, alias="mappingVersion"),
    page_size: int = PageSize(20, 100),
) -> MappingTargetPage:
    return target_details(read, source_object_id, mapping_version, paging, page_size)


@router.put("/mappings", response_model=MappingReplacementResponse)
@requires("records.write", at=MAPPINGS_WRITE)
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


@router.post("/mapping-proposals", response_model=JobResponse, status_code=202)
@requires("records.write", at=MAPPING_PROPOSAL)
def post_mapping_proposals(
    workspace_key: str, body: MappingProposalRequest, request: Request, session: DbSession
) -> JobResponse:
    """Ask the AI provider for targets for the unmapped sources of a mapping view, into a change
    set (0.16 AP2). Answers 202 with a queued ``aiProposal`` job; its ``aiProposal`` tally reads
    as it runs. Refused before a job exists: ``403 FORBIDDEN`` without Use AI proposals, ``409
    AI_NOT_CONFIGURED``, ``409 AI_SEND_LEVEL_TOO_LOW`` (a ``sendLevel`` above the ceiling, or below
    what the feature needs), ``404 CHANGE_SET_NOT_FOUND``, ``409 CHANGE_SET_VERSION_CONFLICT``,
    ``404 MAPPING_VIEW_NOT_FOUND``, ``404 MAPPING_PARENT_NOT_FOUND``."""
    ai_requested(
        request, "mappingTarget", True, workspace_key=workspace_key, send_level=body.sendLevel
    )
    job = mapping_job.queue(
        session,
        workspace_key,
        application_key=body.applicationKey,
        view_key=body.viewKey,
        search=body.search,
        parent_object_id=str(body.parentObjectId) if body.parentObjectId else None,
        change_set_id=str(body.changeSetId) if body.changeSetId else None,
        expected_change_set_version=body.expectedChangeSetVersion,
        change_set_name=body.changeSetName,
        send_level=body.sendLevel,
        retention_days=request.app.state.batch_limits.retention_days,
    )
    worker = getattr(request.app.state, "job_worker", None)
    if worker is not None:
        worker.wake()
    return job_responses(session, [job])[0]
