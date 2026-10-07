"""An import's outcomes by row (Base 0.9 J3, D84): ``GET /jobs/{jobId}/rows``.

A row's items are spread over the job's item order (records, related records, relationships), so the
read groups the job's outcomes by the source and row stored on each, in source then row order, with
keyset paging on those two integers. A row's status is its worst item's: ``rejected``, then
``unprocessed``, then ``applied``. Rows without an outcome (a sample preview's rest) are not listed.
"""

from typing import Any

from sqlalchemy import case, cast, func, select
from sqlalchemy.dialects.postgresql import JSONB, aggregate_order_by
from sqlalchemy.orm import Session

from ...common.pagination import Page, PageRequest, integer_key, paginate_statement
from ...errors import api_error
from ...models.database import Job, JobItem
from ..schemas.jobs import JobActions, JobItemResponse, JobRowPage, JobRowResponse


def job_row_page(
    session: Session, job: Job, *, status: str | None, page: PageRequest, page_size: int
) -> JobRowPage:
    if job.kind != "import":
        raise api_error(
            404,
            "JOB_HAS_NO_ROWS",
            f"Job '{job.id}' is a {job.kind}; only an import's outcomes read by row",
        )
    rows = _rows(job, status)
    found: Page[Any] = paginate_statement(
        session,
        select(rows),
        keys=(
            integer_key("source", rows.c.source_index, "source_index"),
            integer_key("row", rows.c.row_number, "row_number"),
        ),
        scope="job-rows",
        filters={"jobId": job.id, "status": status},
        page=page,
        page_size=page_size,
        message="Job row cursor is invalid",
        rows=True,
    )
    return JobRowPage(items=[_row(row) for row in found.items], **found.links())


def _rows(job: Job, status: str | None) -> Any:
    def applied(action: str) -> Any:
        return func.count().filter(
            (JobItem.status == "applied")
            & (cast(JobItem.outcome, JSONB)["action"].astext == action)
        )

    worst = case(
        (func.bool_or(JobItem.status == "rejected"), "rejected"),
        (func.bool_or(JobItem.status == "unprocessed"), "unprocessed"),
        else_="applied",
    )
    outcome = cast(JobItem.outcome, JSONB).op("||")(
        func.jsonb_build_object(
            "index", JobItem.item_index, "ref", JobItem.ref, "status", JobItem.status
        )
    )
    statement = (
        select(
            JobItem.source_index.label("source_index"),
            JobItem.row_number.label("row_number"),
            func.min(JobItem.ref).label("ref"),
            worst.label("status"),
            applied("created").label("created"),
            applied("updated").label("updated"),
            applied("unchanged").label("unchanged"),
            applied("deleted").label("deleted"),
            func.jsonb_agg(aggregate_order_by(outcome, JobItem.item_index), type_=JSONB)
            .filter(JobItem.status != "applied")
            .label("outcomes"),
        )
        .where(JobItem.job_id == job.sequence_id, JobItem.source_index.is_not(None))
        .group_by(JobItem.source_index, JobItem.row_number)
    )
    if status is not None:
        statement = statement.having(worst == status)
    return statement.subquery()


def _row(row: Any) -> JobRowResponse:
    ref = row.ref or ""
    sheet = ref.rsplit("!", 1)[0] if "!" in ref else None
    return JobRowResponse(
        ref=ref,
        sheet=sheet,
        row=row.row_number,
        status=row.status,
        actions=JobActions(
            created=row.created,
            updated=row.updated,
            unchanged=row.unchanged,
            deleted=row.deleted,
        ),
        outcomes=[JobItemResponse(**outcome) for outcome in row.outcomes or []],
    )
