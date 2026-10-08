"""An import's preview (Base 0.9 J3, INTEGRATION_API §J1, D80–D83).

An import sent with ``stage: preview`` is bound as an execution would be (``binding.py``); the
worker's next step runs its first ``IMPORT_PREVIEW_MAX_ITEMS`` items through the batch path, every
item independently whatever the policy (D80), and then rolls the whole transaction back (D82):
records, relationships, feed positions, audit entries, matrix states, unique values and change-set
versions go together, and PostgreSQL drops a rolled-back transaction's notifications. A short
transaction then records the outcomes and the summary, and the job waits for confirmation.

The summary says what an execution would do: counts by action, the result under the request's
policy (``atomic`` writes nothing when any item is refused), and how much of the file it covers. A
row counts as previewed once every item of it ran (D83): items run records first and relationships
last, so a sample of a large file may preview a row's record and not its relationships.
"""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from pydantic import TypeAdapter
from sqlalchemy import text
from sqlalchemy.orm import Session

from ...models.commands import BatchItem
from ...models.database import Job
from ..jobs.batches import BatchContext, run_items
from ..jobs.store import ItemOutcome, await_confirmation, load_inputs, record_outcomes

_ITEM = TypeAdapter(BatchItem)

# Rows of the job's file, each with its last item; a row is previewed when that item ran.
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
    )


def record_preview(
    session: Session, job: Job, outcomes: list[ItemOutcome], *, retention_days: int
) -> None:
    """The preview's outcomes and summary, and the job waiting for confirmation; the caller
    commits."""
    record_outcomes(session, job, outcomes)
    await_confirmation(session, job, preview_summary(session, job), retention_days=retention_days)


def preview_summary(session: Session, job: Job) -> dict[str, Any]:
    rows, previewed, rejected = session.execute(
        text(_ROWS), {"job": job.sequence_id, "processed": job.processed}
    ).one()
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
    return {
        "coverage": "complete" if job.processed >= job.total else "sample",
        "items": {"total": job.total, "previewed": job.processed},
        "rows": {"total": rows, "previewed": previewed, "rejected": rejected},
        "counts": {key: counts[key] for key in ("created", "updated", "unchanged", "deleted")}
        | {"rejected": counts["rejected"]},
        "result": result,
        "previewedAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }
