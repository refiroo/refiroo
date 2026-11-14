"""An import's outcomes by row (Base 0.9 J3, D84): ``GET /jobs/{jobId}/rows``.

A row's items are spread over the job's item order (records, related records, relationships), so the
read groups the job's outcomes by the source and row stored on each, in source then row order, with
keyset paging on those two integers. A row's status is its worst item's: ``rejected``, then
``unprocessed``, then ``applied``. Rows without an outcome (a sample preview's rest) are not listed.
"""

from typing import Any

from sqlalchemy import String, case, cast, func, literal_column, select
from sqlalchemy.dialects.postgresql import JSONB, aggregate_order_by
from sqlalchemy.orm import Session

from ...common.pagination import Page, PageRequest, integer_key, paginate_statement
from ...engine.jobs.kinds import ROW_KINDS
from ...errors import api_error
from ...models.database import Job, JobItem, RdmObject
from ..schemas.jobs import (
    JobActions,
    JobItemResponse,
    JobRowPage,
    JobRowResponse,
    MigrationRow,
    MigrationRowPage,
    MoveRow,
    MoveRowPage,
)

_ROW_STATUSES = ("applied", "rejected", "unprocessed")
_OUTCOMES = ("conversion", "reclassified", "loss", "refused", "created")
# The expression ``ix_job_items_outcome`` indexes (migration 20261019_01).
_OUTCOME = literal_column("(job_items.outcome ->> 'outcome')", type_=String)


def job_row_page(
    session: Session,
    job: Job,
    *,
    status: str | None,
    page: PageRequest,
    page_size: int,
    source: int | None = None,
    code: str | None = None,
) -> JobRowPage:
    """``source`` keeps one source's rows; ``code`` the rows with an outcome refused with it (a
    dry run's rows behind a figure, 0.10 A3)."""
    if job.kind not in ROW_KINDS:
        raise api_error(
            404,
            "JOB_HAS_NO_ROWS",
            f"Job '{job.id}' is a {job.kind}; only an import's or a migration's outcomes read by "
            "row",
        )
    _require_status(status, _ROW_STATUSES)
    rows = _rows(job, status, source, code)
    found: Page[Any] = paginate_statement(
        session,
        select(rows),
        keys=(
            integer_key("source", rows.c.source_index, "source_index"),
            integer_key("row", rows.c.row_number, "row_number"),
        ),
        scope="job-rows",
        filters={"jobId": job.id, "status": status, "source": source, "code": code},
        page=page,
        page_size=page_size,
        message="Job row cursor is invalid",
        rows=True,
    )
    return JobRowPage(items=[_row(row) for row in found.items], **found.links())


def migration_row_page(
    session: Session, job: Job, *, outcome: str | None, page: PageRequest, page_size: int
) -> MigrationRowPage:
    """A migration's items in item order (0.11 V1), ``outcome`` keeping one kind."""
    _require_status(outcome, _OUTCOMES)
    statement = select(JobItem).where(JobItem.job_id == job.sequence_id)
    if outcome is not None:
        statement = statement.where(_OUTCOME == outcome)
    found: Page[JobItem] = paginate_statement(
        session,
        statement,
        keys=(integer_key("index", JobItem.item_index, "item_index"),),
        scope="migration-rows",
        filters={"jobId": job.id, "outcome": outcome},
        page=page,
        page_size=page_size,
        message="Job row cursor is invalid",
    )
    return MigrationRowPage(
        items=[MigrationRow(index=item.item_index, **item.outcome) for item in found.items],
        **found.links(),
    )


_MOVE_OUTCOMES = ("create", "update", "updateOriginal", "refused", "notMoved")
_MOVE_OUTCOME = literal_column("(job_items.outcome ->> 'outcome')", type_=String)


def move_row_page(
    session: Session,
    job: Job,
    *,
    outcome: str | None,
    reason: str | None,
    source_type: str | None,
    page: PageRequest,
    page_size: int,
) -> MoveRowPage:
    """A move's rows in their order (0.11 X2, D119), kept to one ``outcome``, rows with a
    ``reason`` of that code, or one ``sourceType``."""
    _require_status(outcome, _MOVE_OUTCOMES)
    statement = select(JobItem).where(JobItem.job_id == job.sequence_id)
    if outcome is not None:
        statement = statement.where(_MOVE_OUTCOME == outcome)
    if reason is not None:
        statement = statement.where(
            cast(JobItem.outcome, JSONB)["reasons"].op("@>")(
                func.jsonb_build_array(func.jsonb_build_object("code", reason))
            )
        )
    if source_type is not None:
        statement = statement.where(
            cast(JobItem.outcome, JSONB)["sourceType"].astext == source_type
        )
    found: Page[JobItem] = paginate_statement(
        session,
        statement,
        keys=(integer_key("index", JobItem.item_index, "item_index"),),
        scope="move-rows",
        filters={"jobId": job.id, "outcome": outcome, "reason": reason, "sourceType": source_type},
        page=page,
        page_size=page_size,
        message="Job row cursor is invalid",
    )
    # A relationship row names its two ends by ID; their names are read for the page in one
    # statement, as the records are named now (0.11 X4: eight rows of one record told nothing).
    ends = {
        key
        for item in found.items
        if item.outcome.get("kind") == "relationship"
        for key in (item.outcome.get("fromId"), item.outcome.get("toId"))
        if key
    }
    names = (
        dict(
            session.execute(
                select(RdmObject.id, RdmObject.name).where(RdmObject.id.in_(ends))
            ).all()
        )
        if ends
        else {}
    )

    def row(item: JobItem) -> MoveRow:
        outcome = dict(item.outcome)
        if outcome.get("kind") == "relationship":
            for end in ("from", "to"):
                name = names.get(outcome.get(f"{end}Id"))
                if name is not None:
                    outcome[f"{end}Name"] = name
        return MoveRow(index=item.item_index, **outcome)

    return MoveRowPage(items=[row(item) for item in found.items], **found.links())


def _require_status(status: str | None, allowed: tuple[str, ...]) -> None:
    if status is not None and status not in allowed:
        raise api_error(
            422,
            "INVALID_PAGE_PARAMETER",
            f"This job's rows take status {', '.join(allowed)}",
            {"parameter": "status", "allowed": list(allowed)},
        )


def _rows(job: Job, status: str | None, source: int | None, code: str | None) -> Any:
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
    if source is not None:
        statement = statement.where(JobItem.source_index == source)
    if code is not None:
        statement = statement.having(
            func.bool_or(cast(JobItem.outcome, JSONB)["error"]["code"].astext == code)
        )
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
