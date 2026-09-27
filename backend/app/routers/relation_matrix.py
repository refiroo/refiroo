"""Relation matrix reads; the view, its binding and the query live in the service."""

from typing import Literal

from fastapi import APIRouter, Query

from ..db import DbSession
from ..errors import api_error
from ..models.api import RelationMatrixPage
from ..services.relation_matrix import MAX_COLUMNS, open_matrix_read, relation_matrix_page
from .paging import SeekablePageQuery

_COLUMN_IDS = Query(
    default=None,
    alias="columnIds",
    description=(
        f"Column records to show, in order, at most {MAX_COLUMNS}; without them, a name-ordered"
        " page of the column type's records"
    ),
)

router = APIRouter(prefix="/api/v1/workspaces/{workspace_key}", tags=["relation-matrix"])


@router.get("/relation-matrix", response_model=RelationMatrixPage)
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
) -> RelationMatrixPage:
    if change_set_id and publication_id:
        raise api_error(
            422,
            "mutually_exclusive_context",
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
    )
