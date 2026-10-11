"""The event deriver's round over the workspaces behind their feed (0.9 C10,
``engine/events/worker.py``)."""

import pytest

from app.engine.events.worker import EventDeriver


class _Deriver(EventDeriver):
    def __init__(self) -> None:
        super().__init__(lambda: None)
        self.derived: list[str] = []

    def pending(self) -> list[str]:
        return ["broken", "after"]

    def derive(self, workspace_key: str) -> bool:
        if workspace_key == "broken":
            raise RuntimeError("cannot derive")
        self.derived.append(workspace_key)
        return True


def test_a_workspace_that_fails_does_not_hold_up_the_others():
    """0.9 R-F11: the workspaces after a failing one are derived, then its error is raised."""
    deriver = _Deriver()
    with pytest.raises(RuntimeError, match="cannot derive"):
        deriver.run_once()
    assert deriver.derived == ["after"]
