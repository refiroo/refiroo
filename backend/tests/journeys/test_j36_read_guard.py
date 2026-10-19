"""J36.5 at the engine boundary — a request whose workspace switched while it ran (Base 0.11 N1).

A read resolves its workspace's release, reads, and is checked as it ends
(``require_unchanged_releases``, run by the request's session dependency, D166); a write is checked
as it commits (``require_resolved_release``). The interleavings are set with sessions: the request's
session resolves, the switch commits meanwhile, and the request's session ends or commits. Any
process on the database may hold either side.
"""

import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from scenario import W1, W2, ok
from service import execute
from sqlalchemy import text
from test_j36_workspace_models import BOTH

from app.db import SessionLocal
from app.engine.model.registry import (
    require_resolved_release,
    require_unchanged_releases,
    resolve_model_snapshot,
    resolve_request_model,
)
from app.errors import ApiError


def _refusal(session) -> ApiError:
    with pytest.raises(ApiError) as refusal:
        require_unchanged_releases(session)
    assert (refusal.value.status, refusal.value.code) == (409, "MODEL_RELEASE_CHANGED")
    return refusal.value


@pytest.mark.journey("J36.5")
@pytest.mark.structures(*BOTH)
def test_a_read_whose_workspace_switched_while_it_ran(world):
    """Given reads in the default and the second workspace resolved under X1, and a write in the
    default workspace committed. When X2 is activated into the default workspace before they end.
    Then the default workspace's read is refused naming the workspace, X1 and X2; the second
    workspace's read ends; the committed write's request is not refused."""
    model, _key = world.candidate("compatible")
    x2 = world.install(model)["id"]
    with SessionLocal() as here, SessionLocal() as there, SessionLocal() as wrote:
        x1 = resolve_model_snapshot(here, W1).release_id
        resolve_model_snapshot(there, W2)
        resolve_model_snapshot(wrote, W1)
        wrote.commit()
        ok(world.activate(x2))

        details = _refusal(here).details
        assert details == {"workspaceKey": W1, "resolvedReleaseId": x1, "currentReleaseId": x2}
        require_unchanged_releases(there)
        require_unchanged_releases(wrote)


@pytest.mark.journey("J36.5")
@pytest.mark.structures(*BOTH)
def test_a_read_in_a_change_set_moved_to_another_release(world):
    """Given a read in a change set of the default workspace resolved under its pin X1. When the
    change set is moved to X2 before the read ends (set in the database, as V3's move commits it).
    Then the read is refused naming the change set and both releases."""
    model, _key = world.candidate("compatible")
    x2 = world.install(model)["id"]
    change_set = world.change_set(W1)
    with SessionLocal() as reading:
        x1 = resolve_request_model(reading, None, change_set["id"], None).release_id
        execute(
            world.database,
            "UPDATE change_sets SET model_release_id = "
            "(SELECT id FROM model_releases WHERE public_id = :x2) WHERE id = :id",
            x2=x2,
            id=change_set["id"],
        )
        details = _refusal(reading).details
    assert details == {
        "workspaceKey": W1,
        "changeSetId": change_set["id"],
        "resolvedReleaseId": x1,
        "currentReleaseId": x2,
    }


@pytest.mark.journey("J36.5")
@pytest.mark.structures(*BOTH)
def test_a_write_whose_check_waits_for_the_switch(world):
    """Given a write in the default workspace resolved under X1, and a switch to X2 holding the
    workspace's assignment, not yet committed. When the write's commit check runs, it waits; the
    switch commits. Then the write is refused naming X1 and X2. (Before N1 the check joined the
    assignment to its release, and the row the wait returned dropped out of the join: the write
    passed under X1.)"""
    model, _key = world.candidate("compatible")
    x2 = world.install(model)["id"]
    started = threading.Event()

    def check(session):
        started.set()
        require_resolved_release(session)

    with SessionLocal() as switch, SessionLocal() as write, ThreadPoolExecutor(1) as pool:
        x1 = resolve_model_snapshot(write, W1).release_id
        switch.execute(
            text(
                "UPDATE workspace_models SET version = version + 1, model_release_id = "
                "(SELECT id FROM model_releases WHERE public_id = :x2) WHERE workspace_key = :w"
            ),
            {"x2": x2, "w": W1},
        )
        waiting = pool.submit(check, write)
        assert started.wait(10)
        with pytest.raises(TimeoutError):
            waiting.result(timeout=1)
        switch.commit()
        with pytest.raises(ApiError) as refusal:
            waiting.result(timeout=30)
        write.rollback()
    assert (refusal.value.status, refusal.value.code) == (409, "MODEL_RELEASE_CHANGED")
    assert refusal.value.details == {
        "workspaceKey": W1,
        "resolvedReleaseId": x1,
        "currentReleaseId": x2,
    }
