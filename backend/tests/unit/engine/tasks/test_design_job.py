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
    assert progress.now == "Going on" and progress.tokens()[0] == 3
