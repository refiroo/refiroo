"""An import's outcomes by row (``management/projections/job_rows.py``, 0.9 J3, D84).

J27.11 pages the rows of a two-sheet file through the API. Here are the read's own cases: a row's
status is its worst item's (rejected, then unprocessed, then applied), its applied items count by
action, and rows order by source and then by row as numbers, so row 10 follows row 9.
"""

import pytest
from scenario import W1

from app.common.pagination import PageRequest
from app.db import SessionLocal
from app.engine.jobs.store import ItemOutcome, record_outcomes, start_job
from app.engine.model.registry import resolve_model_snapshot
from app.errors import ApiError
from app.management.projections.job_rows import job_row_page
from app.models.database import JobInput

APPLIED = "applied"


def test_rows_take_their_worst_status_and_page_by_source_then_row(seeded):
    # (source, row, status, action) per item, in item order: records first, relationships last.
    items = [
        (0, 2, APPLIED, "created"),
        (0, 3, "rejected", None),
        (0, 10, APPLIED, "updated"),
        (0, 9, APPLIED, "unchanged"),
        (1, 2, APPLIED, "created"),
        (0, 2, "unprocessed", None),
        (0, 3, "unprocessed", None),
        (1, 2, APPLIED, "created"),
    ]
    with SessionLocal() as session:
        job = start_job(
            session,
            kind="import",
            workspace_key=W1,
            change_set_id=None,
            model_release_id=resolve_model_snapshot(session).release_db_id,
            parameters={"policy": "atomic", "stage": "execute"},
            total=len(items),
            retention_days=7,
            queued=True,
        )
        for index, (source, row, _status, _action) in enumerate(items):
            session.add(
                JobInput(
                    job_id=job.sequence_id,
                    item_index=index,
                    ref=f"S{source}!{row}",
                    source_index=source,
                    row_number=row,
                    item={},
                )
            )
        session.flush()
        record_outcomes(
            session,
            job,
            [
                ItemOutcome(
                    index,
                    f"S{source}!{row}",
                    status,
                    {"action": action}
                    if status == APPLIED
                    else {"reason": "BATCH_ROLLED_BACK"}
                    if status == "unprocessed"
                    else {"error": {"code": "X", "message": "x"}},
                )
                for index, (source, row, status, action) in enumerate(items)
            ],
        )

        seen, cursor = [], None
        while True:
            page = job_row_page(
                session, job, status=None, page=PageRequest(cursor=cursor), page_size=1
            )
            seen += page.items
            cursor = page.nextCursor
            if not cursor:
                break
        assert [(row.sheet, row.row, row.status) for row in seen] == [
            ("S0", 2, "unprocessed"),
            ("S0", 3, "rejected"),
            ("S0", 9, APPLIED),
            ("S0", 10, APPLIED),
            ("S1", 2, APPLIED),
        ]
        assert seen[-1].actions.created == 2 and seen[0].actions.created == 1
        assert [o.status for o in seen[1].outcomes] == ["rejected", "unprocessed"]
        rejected = job_row_page(
            session, job, status="rejected", page=PageRequest(), page_size=10
        ).items
        assert [row.ref for row in rejected] == ["S0!3"]

        job.kind = "batch"
        with pytest.raises(ApiError) as refused:
            job_row_page(session, job, status=None, page=PageRequest(), page_size=10)
        assert refused.value.code == "JOB_HAS_NO_ROWS"
        session.rollback()
