"""The release the assistant installs (``engine/tasks/design_job.py``)."""

import json

from app.engine.tasks import agent, design_job


def test_the_release_the_assistant_installs_is_numbered_after_the_newest():
    from unittest.mock import MagicMock

    session = MagicMock()
    session.scalars.return_value = ["0.9.5", "0.10.0", "0.9.6"]
    # The draft came from 0.9.5, but 0.10.0 is the newest: the new release is 0.10.1.
    assert design_job._next_version(session, "model", "0.9.5") == "0.10.1"


def test_a_session_event_whose_message_is_text_does_not_stop_the_reading(tmp_path):
    """A permission refused comes as a system event with its message as text, as on a real run."""
    log = tmp_path / "session.log"
    turn = {
        "message": {
            "id": "m",
            "usage": {"input_tokens": 3},
            "content": [{"type": "text", "text": "Going on"}],
        }
    }
    refused = {"type": "system", "subtype": "permission_denied", "message": "outside the folder"}
    log.write_text("".join(json.dumps(line) + "\n" for line in (refused, [1], turn)))
    progress = agent._Progress(log)
    assert progress.read() is True
    progress.close()
    assert progress.now == "Going on" and progress.tokens()[0] == 3


from types import SimpleNamespace
from unittest.mock import MagicMock


def _session(job):
    session = MagicMock()
    session.scalar.return_value = job
    return session


def test_a_check_run_on_another_version_of_the_draft_is_stale():
    draft = SimpleNamespace(public_id="d", version=4)
    ran_on = lambda version: SimpleNamespace(
        state="completed", parameters={"draftVersion": version}
    )
    assert design_job.check_is_stale(_session(ran_on(3)), draft)
    assert not design_job.check_is_stale(_session(ran_on(4)), draft)
    # No completed check: nothing is stale, and the load is refused for its own reason.
    assert not design_job.check_is_stale(_session(None), draft)
    running = SimpleNamespace(state="running", parameters={"draftVersion": 1})
    assert not design_job.check_is_stale(_session(running), draft)


def test_the_check_of_a_dry_run_of_items_reads_records_and_relationships_apart_and_groups_refusals():
    from types import SimpleNamespace

    from app.engine.tasks.design_job import items_check

    summary = {
        "figures": {
            "recordsNew": 3,
            "recordsMatched": 2,
            "recordsChanged": 1,
            "refused": 2,
            "relationshipsNew": 4,
        },
        "refused": [
            {
                "index": 5,
                "ref": "S!A6",
                "code": "UNKNOWN_ATTRIBUTES",
                "message": "No such attribute",
            },
            {"index": 9, "ref": None, "code": "UNKNOWN_ATTRIBUTES", "message": "No such attribute"},
        ],
        "refusedByCode": [{"code": "UNKNOWN_ATTRIBUTES", "items": 2}],
        "ranAt": "2026-11-09T10:00:00Z",
    }
    job = SimpleNamespace(id="job-1", report={"itemsDryRun": summary})
    check = items_check(job)
    assert check["mode"] == "items" and check["sheets"] == [] and check["itemsSummary"] is summary
    assert check["summary"] == {
        "created": 3,
        "updated": 1,
        "unchanged": 1,
        "refused": 2,
        "relationships": 4,
        "skipped": 0,
    }
    (group,) = check["refused"]
    assert (group["code"], group["rows"]) == ("UNKNOWN_ATTRIBUTES", 2)
    assert [e["message"] for e in group["examples"]] == [
        "S!A6: No such attribute",
        "No such attribute",
    ]
