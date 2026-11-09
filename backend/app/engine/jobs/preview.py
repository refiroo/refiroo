"""A job's preview: an import's (Base 0.9 J3, INTEGRATION_API §J1, D80–D83) or a batch's (0.9 K2,
D112, D113).

A job sent with ``stage: preview`` runs its first ``JOB_PREVIEW_MAX_ITEMS`` items through the batch
path, every item independently whatever the policy (D80), and then rolls the whole transaction back
(D82): records, relationships, feed positions, audit entries, matrix states, unique values and
change-set versions go together, and PostgreSQL drops a rolled-back transaction's notifications. A
short transaction then records the outcomes and the summary, and the job waits for confirmation. An
import is bound first (``imports/binding.py``); a batch's items are stored when it is queued.

The summary says what an execution would do: counts by action, the result under the request's
policy (``atomic`` writes nothing when any item is refused), and how much of the job it covers. An
import's summary also counts its file's rows: a row counts as previewed once every item of it ran
(D83), since items run records first and relationships last, so a sample of a large file may
preview a row's record and not its relationships.
"""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from pydantic import TypeAdapter
from sqlalchemy import text
from sqlalchemy.orm import Session

from ...models.commands import BatchItem
from ...models.database import Job
from .batches import BatchContext, run_items
from .store import ROW_KINDS, ItemOutcome, await_confirmation, load_inputs, record_outcomes

_ITEM = TypeAdapter(BatchItem)

# An import's rows of its file, each with its last item; a row is previewed when that item ran.
_ROWS = """
    WITH rows AS (
        SELECT source_index, row_number, max(item_index) AS last FROM (
            SELECT source_index, row_number, item_index FROM job_inputs WHERE job_id = :job
            UNION ALL
            SELECT source_index, row_number, item_index FROM job_items WHERE job_id = :job
        ) found GROUP BY source_index, row_number)
    SELECT count(*), count(*) FILTER (WHERE last < :processed),
        (SELECT count(*) FROM (SELECT DISTINCT source_index, row_number FROM job_items
         WHERE job_id = :job AND status = 'rejected') refused)
    FROM rows
"""


def preview_items(
    session: Session,
    job: Job,
    context: BatchContext,
    *,
    limit: int,
    should_stop: Callable[[], bool],
) -> list[ItemOutcome]:
    """Run the job's first ``limit`` items independently (D80). The caller rolls back."""
    inputs = load_inputs(session, job, limit)
    return run_items(
        session,
        context,
        [(index, _ITEM.validate_python(item)) for index, item in inputs],
        policy="independent",
        on_existing=job.parameters.get("onExisting", "reject"),
        other_workspace_ids=job.parameters.get("otherWorkspaceIds", "refuse"),
        expected_change_set_version=job.change_set_version,
        job_id=job.id,
        should_stop=should_stop,
        previewing=True,
        # A dry run of items is a batch's preview: no file rows (0.13 AB).
        file_rows=job.kind in ROW_KINDS and job.parameters.get("mode") != "items",
    )


def record_preview(
    session: Session, job: Job, outcomes: list[ItemOutcome], *, retention_days: int
) -> None:
    """The preview's outcomes and summary, and the job waiting for confirmation; the caller
    commits."""
    record_outcomes(session, job, outcomes)
    summary = preview_summary(session, job)
    deletion = deletion_totals(outcomes)
    if deletion is not None:
        summary["deletion"] = deletion
    await_confirmation(session, job, summary, retention_days=retention_days)


def deletion_totals(outcomes: list[ItemOutcome]) -> dict[str, Any] | None:
    """What the preview's delete items would remove together (0.9 K2b, D121): records by type,
    relationships, and those reaching records that stay; ``None`` when it deletes nothing."""
    impacts = [
        outcome.fields["impact"]
        for outcome in outcomes
        if outcome.status == "applied" and "impact" in outcome.fields
    ]
    if not impacts:
        return None
    by_type: dict[str, int] = {}
    for impact in impacts:
        for key, count in impact["objectsByType"].items():
            by_type[key] = by_type.get(key, 0) + count
    return {
        "objectCount": sum(impact["objectCount"] for impact in impacts),
        "objectsByType": dict(sorted(by_type.items())),
        "relationshipCount": sum(impact["relationshipCount"] for impact in impacts),
        "retainedAssociationCount": sum(impact["retainedAssociationCount"] for impact in impacts),
    }


def preview_summary(session: Session, job: Job) -> dict[str, Any]:
    counts = job.counts
    if job.parameters.get("policy") == "atomic":
        result = "rejected" if counts["rejected"] else "applied"
    else:
        result = (
            "applied"
            if counts["applied"] == job.processed
            else "rejected"
            if counts["applied"] == 0
            else "partial"
        )
    summary: dict[str, Any] = {
        "coverage": "complete" if job.processed >= job.total else "sample",
        "items": {"total": job.total, "previewed": job.processed},
        "counts": {key: counts[key] for key in ("created", "updated", "unchanged", "deleted")}
        | {"rejected": counts["rejected"]},
        "result": result,
        "previewedAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }
    if job.kind in ROW_KINDS:
        rows, previewed, rejected = session.execute(
            text(_ROWS), {"job": job.sequence_id, "processed": job.processed}
        ).one()
        summary["rows"] = {"total": rows, "previewed": previewed, "rejected": rejected}
    return summary
