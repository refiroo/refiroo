"""The summary of a dry run of items counts what the load counts (0.13 DOC11 F2)."""

from uuid import uuid4

from scenario import W1

from app.db import SessionLocal
from app.engine.jobs.store import ItemOutcome, record_outcomes, start_job
from app.engine.model.registry import resolve_model_snapshot
from app.engine.sources.items_summary import summarize
from app.models.database import JobInput


def test_the_new_relationships_a_check_shows_include_the_links_to_parents_the_load_counts(seeded):
    """Given a workbook that makes five stops, four of them under a municipality, and links one
    of them to a line, when the items are checked, then the figure for new relationships is what
    the load will count (the line's link and the four parent links), and says how many of them
    are parent links."""
    root = str(uuid4())
    parent = {"id": root, "objectTypeKey": "municipality"}

    def stop(name, row, **more):
        return {
            "op": "create",
            "id": str(uuid4()),
            "applicationKey": "a",
            "objectTypeKey": "stop",
            "name": name,
            "ref": f"Stops!A{row}",
            **more,
        }

    items = [
        stop("Stop 1", 2, parent=parent),
        stop("Stop 2", 3, parent=parent),
        stop("Stop 3", 4, parent=parent),
        stop("Stop 4", 5, parent=parent, initialRelations=[]),
        stop(
            "Stop 5",
            6,
            initialRelations=[
                {
                    "relationTypeKey": "served-by",
                    "direction": "outgoing",
                    "object": {"objectTypeKey": "line", "name": "Line 1"},
                }
            ],
        ),
    ]
    with SessionLocal() as session:
        job = start_job(
            session,
            kind="dryRun",
            workspace_key=W1,
            change_set_id=None,
            model_release_id=resolve_model_snapshot(session).release_db_id,
            parameters={"mode": "items", "draftId": "d", "draftVersion": 1},
            total=len(items),
            retention_days=7,
            queued=False,
        )
        for index, item in enumerate(items):
            session.add(
                JobInput(job_id=job.sequence_id, item_index=index, ref=item["ref"], item=item)
            )
        session.flush()
        record_outcomes(
            session,
            job,
            [
                ItemOutcome(index, item["ref"], "applied", {"action": "created", "id": item["id"]})
                for index, item in enumerate(items)
            ],
        )
        figures = summarize(session, job, found_names=[])["figures"]
        assert figures["recordsNew"] == 5
        assert figures["parentLinksNew"] == 4
        assert figures["relationshipsNew"] == 1 + 4
        session.rollback()
