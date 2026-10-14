"""An import profile's check (Product 0.10 A5c, D83): the report and its lists, paged.

The check's lists (new values, drift, records missing from the file) are kept on its job's report;
each is read as a page of the JSON array's elements by their position (ADR-030), narrowed to one
source when asked.
"""

from typing import Any

from sqlalchemy import Integer, cast, column, func, select, true
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

from ...common.pagination import PageRequest, integer_key, paginate_statement
from ...models.database import Job
from ..schemas.imports import CheckSource, ProfileCheckResponse

_LISTS = ("newValues", "drift", "missingRecords")


def check_response(job: Job) -> ProfileCheckResponse:
    report = (job.report or {}).get("check") or {}
    findings = report.get("findings") or {}
    counts = {name: _per_source(findings.get(name) or []) for name in _LISTS}
    sources = [
        CheckSource(
            **entry,
            **{
                name: counts[name].get(entry["source"], 0) if entry["source"] is not None else 0
                for name in _LISTS
            },
        )
        for entry in report.get("sources") or []
    ]
    dry_run = report.get("dryRun")
    return ProfileCheckResponse(
        jobId=job.id,
        state="checking" if job.state in {"queued", "running"} else job.state,
        profileKey=job.parameters["profileKey"],
        profileVersion=report.get("profileVersion"),
        sourceFileId=job.parameters["sourceFileId"],
        previousSourceFileId=report.get("previousSourceFileId"),
        workspaceKey=job.workspace_key,
        releaseId=report.get("releaseId"),
        valid=report.get("valid"),
        problems=report.get("problems") or [],
        sources=sources,
        dryRun=(
            {"difference": None, "previousJobId": None, **dry_run} if dry_run is not None else None
        ),
        bindingReport=(job.report or {}).get("bindingReport"),
        error=job.error,
    )


def finding_page(
    session: Session,
    job: Job,
    name: str,
    *,
    source: int | None,
    page: PageRequest,
    page_size: int,
) -> Any:
    """One of the check's lists, a page of its elements in their stored order."""
    elements = (
        func.jsonb_array_elements(
            func.coalesce(cast(Job.report, JSONB)["check"]["findings"][name], cast("[]", JSONB))
        )
        .table_valued(column("value", JSONB), with_ordinality="position")
        .render_derived()
    )
    statement = (
        select(elements.c.value.label("value"), elements.c.position.label("position"))
        .select_from(Job)
        .join(elements, true())
        .where(Job.sequence_id == job.sequence_id)
    )
    if source is not None:
        statement = statement.where(
            cast(func.jsonb_extract_path_text(elements.c.value, "source"), Integer) == source
        )
    rows = statement.subquery()
    return paginate_statement(
        session,
        select(rows),
        keys=(integer_key("position", rows.c.position, "position"),),
        scope=f"profile-check-{name}",
        filters={"jobId": job.id, "source": source},
        page=page,
        page_size=page_size,
        message="Profile check cursor is invalid",
        rows=True,
    )


def _per_source(items: list[dict[str, Any]]) -> dict[int, int]:
    counts: dict[int, int] = {}
    for item in items:
        counts[item["source"]] = counts.get(item["source"], 0) + 1
    return counts
