"""Relation matrix reads, and what a cell's writes need; the view, its binding and the queries
live in the service. The writes themselves go through the object and relation APIs."""

from typing import Literal

from fastapi import APIRouter, Query

from ...errors import api_error
from ..access import (
    WORKSPACE_PATH,
    AuthorizedRoute,
    requires,
)
from ..dependencies import DbSession
from ..paging import PageQuery, SeekablePageQuery
from ..projections.relation_matrix import (
    MAX_COLUMNS,
    matrix_containers,
    matrix_link_candidates,
    open_matrix_read,
    relation_matrix_page,
)
from ..schemas.relation_matrix import (
    RelationMatrixContainerPage,
    RelationMatrixLinkCandidatePage,
    RelationMatrixPage,
)

_COLUMN_IDS = Query(
    default=None,
    alias="columnIds",
    description=(
        f"Column records to show, in order, at most {MAX_COLUMNS}; without them, a name-ordered"
        " page of the column type's records"
    ),
)

router = APIRouter(
    route_class=AuthorizedRoute,
    prefix="/api/v1/workspaces/{workspace_key}",
    tags=["relation-matrix"],
)


@router.get("/relation-matrix", response_model=RelationMatrixPage)
@requires("records.read", at=WORKSPACE_PATH)
def get_relation_matrix(
    workspace_key: str,
    session: DbSession,
    paging: SeekablePageQuery,
    application_key: str = Query(alias="applicationKey"),
    view_key: str = Query(alias="viewKey", description="A relationMatrix view of the application"),
    change_set_id: str | None = Query(default=None, alias="changeSetId"),
    publication_id: str | None = Query(default=None, alias="publicationId"),
    parent_object_id: str | None = Query(
        default=None, alias="parentObjectId", description="Only rows directly under this record"
    ),
    search: str | None = Query(
        default=None, max_length=500, description="Matches the view's searchFields"
    ),
    sort: str | None = Query(
        default=None,
        description="A row field, as on an object list; prefix '-' for descending; name when omitted",
    ),
    column_ids: list[str] | None = _COLUMN_IDS,
    column_cursor: str | None = Query(
        default=None,
        alias="columnCursor",
        description="columnsNextCursor or columnsPrevCursor from a page without columnIds",
    ),
    column_page_size: int = Query(default=MAX_COLUMNS, ge=1, le=MAX_COLUMNS, alias="columnPageSize"),
    state: Literal["one", "several", "inactive", "historyOnly", "none"] | None = Query(
        default=None,
        description="Only rows with a cell in this state in any of columnIds, across every row",
    ),
    page_size: int | None = Query(default=None, ge=1, le=100, alias="pageSize"),
    hide_empty_columns: bool = Query(
        default=False,
        alias="hideEmptyColumns",
        description=(
            "Skip columns with no related record in any row the search and parentObjectId leave; "
            "column paging stays exact. Ignored when columnIds names the columns"
        ),
    ),
) -> RelationMatrixPage:
    if change_set_id and publication_id:
        raise api_error(
            422,
            "MUTUALLY_EXCLUSIVE_CONTEXT",
            "changeSetId and publicationId cannot be combined",
        )
    read = open_matrix_read(
        session, workspace_key, application_key, view_key, change_set_id, publication_id
    )
    return relation_matrix_page(
        read,
        page=paging,
        page_size=page_size,
        parent_object_id=parent_object_id or None,
        search=search or None,
        sort=sort,
        column_ids=column_ids or None,
        column_cursor=column_cursor,
        column_page_size=column_page_size,
        state=state,
        hide_empty_columns=hide_empty_columns,
    )


@router.get("/relation-matrix/containers", response_model=RelationMatrixContainerPage)
@requires("records.read", at=WORKSPACE_PATH)
def get_relation_matrix_containers(
    workspace_key: str,
    session: DbSession,
    paging: PageQuery,
    application_key: str = Query(alias="applicationKey"),
    view_key: str = Query(alias="viewKey", description="A relationMatrix view offering create"),
    column_id: str = Query(alias="columnId", description="The column record of the cell"),
    change_set_id: str | None = Query(default=None, alias="changeSetId"),
    search: str | None = Query(default=None, max_length=500, description="Matches the name"),
    page_size: int = Query(default=50, ge=1, le=100, alias="pageSize"),
) -> RelationMatrixContainerPage:
    read = open_matrix_read(session, workspace_key, application_key, view_key, change_set_id, None)
    return matrix_containers(
        read, column_id=column_id, search=search or None, page=paging, page_size=page_size
    )


@router.get("/relation-matrix/link-candidates", response_model=RelationMatrixLinkCandidatePage)
@requires("records.read", at=WORKSPACE_PATH)
def get_relation_matrix_link_candidates(
    workspace_key: str,
    session: DbSession,
    paging: PageQuery,
    application_key: str = Query(alias="applicationKey"),
    view_key: str = Query(alias="viewKey", description="A relationMatrix view offering link"),
    row_id: str = Query(alias="rowId", description="The row record of the cell"),
    column_id: str = Query(alias="columnId", description="The column record of the cell"),
    change_set_id: str | None = Query(default=None, alias="changeSetId"),
    search: str | None = Query(default=None, max_length=500, description="Matches the name"),
    page_size: int = Query(default=50, ge=1, le=100, alias="pageSize"),
) -> RelationMatrixLinkCandidatePage:
    read = open_matrix_read(session, workspace_key, application_key, view_key, change_set_id, None)
    return matrix_link_candidates(
        read,
        row_id=row_id,
        column_id=column_id,
        search=search or None,
        page=paging,
        page_size=page_size,
    )
