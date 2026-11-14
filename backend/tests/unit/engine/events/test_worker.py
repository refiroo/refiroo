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


def test_a_failing_workspace_waits_out_a_growing_backoff_while_the_others_go_on(monkeypatch):
    """A workspace that fails is tried again only after its wait (2 s, then 4 s, up to the cap),
    never every round; the others are derived every round."""
    from app.engine.events import worker

    now = [1000.0]
    monkeypatch.setattr(worker.time, "monotonic", lambda: now[0])
    deriver = _Deriver()
    attempts: list[str] = []
    original = deriver.derive

    def counting(key):
        attempts.append(key)
        return original(key)

    deriver.derive = counting  # type: ignore[method-assign]
    derived, failures = deriver.run_round()
    assert derived and len(failures) == 1 and attempts == ["broken", "after"]
    attempts.clear()
    now[0] += 1.0  # inside the 2 s wait
    _, failures = deriver.run_round()
    assert failures == [] and attempts == ["after"]
    attempts.clear()
    now[0] += 1.5  # past it: tried again, and the next wait doubles
    _, failures = deriver.run_round()
    assert len(failures) == 1 and attempts == ["broken", "after"]
    assert deriver._failing["broken"][0] == 2
    now[0] += 3.0  # inside the 4 s wait
    attempts.clear()
    deriver.run_round()
    assert attempts == ["after"]
