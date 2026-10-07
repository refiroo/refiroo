"""``engine/jobs/inline.py``: a batch's limits and its idempotency key's workspace.

J11 sends a batch over its item limit and replays one by key through the API. Here every limit is
checked for each run, at and over its bound, and a key is scoped to the workspace a change set
belongs to.
"""

from uuid import uuid4

import pytest
from scenario import W1, W2
from sqlalchemy import select

from app.db import SessionLocal
from app.engine.change_sets.lifecycle import create_change_set
from app.engine.jobs.inline import BatchLimits, check_batch_request, submit_inline_batch
from app.engine.model.registry import resolve_model_snapshot
from app.errors import ApiError
from app.models.commands import BatchRequest
from app.models.database import ChangeSet

LIMITS = BatchLimits(
    max_items=3,
    max_bytes=1000,
    atomic_max_items=2,
    retention_days=7,
    background_max_items=5,
    background_max_bytes=2000,
    chunk_items=2,
    import_max_bytes=4000,
)


def request(count: int, *, run: str = "inline", policy: str = "independent") -> BatchRequest:
    items = [{"op": "delete", "target": {"id": str(uuid4())}, "expectedVersion": 1}] * count
    return BatchRequest.model_validate(
        {"policy": policy, "run": run, "items": items, "workspaceKey": W1}
    )


@pytest.mark.parametrize(
    ("count", "run", "policy", "size", "refused"),
    [
        (3, "inline", "independent", 1000, None),
        (4, "inline", "independent", 10, ("BATCH_MAX_ITEMS", 3, "items", 4)),
        (1, "inline", "independent", 1001, ("BATCH_MAX_BYTES", 1000, "bytes", 1001)),
        (2, "inline", "atomic", 10, None),
        (3, "inline", "atomic", 10, ("ATOMIC_JOB_MAX_ITEMS", 2, "items", 3)),
        (5, "background", "independent", 2000, None),
        (6, "background", "independent", 10, ("BACKGROUND_JOB_MAX_ITEMS", 5, "items", 6)),
        (1, "background", "independent", 2001, ("BATCH_BACKGROUND_MAX_BYTES", 2000, "bytes", 2001)),
        (3, "background", "atomic", 10, ("ATOMIC_JOB_MAX_ITEMS", 2, "items", 3)),
    ],
)
def test_a_batch_over_one_of_its_runs_limits_is_refused_naming_the_setting(
    count, run, policy, size, refused
):
    batch = request(count, run=run, policy=policy)
    if refused is None:
        check_batch_request(batch, size, LIMITS)
        return
    with pytest.raises(ApiError) as error:
        check_batch_request(batch, size, LIMITS)
    setting, maximum, measure, value = refused
    assert (error.value.status, error.value.code) == (413, "BATCH_TOO_LARGE")
    assert error.value.details == {"setting": setting, "maximum": maximum, measure: value}


def test_a_key_belongs_to_the_workspace_its_batch_writes_in(seeded):
    """The same key and request in another workspace is a new request; in a change set the key
    belongs to the change set's workspace; an unknown change set is refused before anything runs."""
    world = seeded
    item = {
        "op": "create",
        "applicationKey": world.app("K"),
        "objectTypeKey": world.key("K"),
        "name": "Keyed",
        "attributes": [{"attributeTypeKey": world.key("K.code"), "value": "KEYED"}],
    }

    def submit(context: dict, key: str = "nightly") -> tuple[str, bool]:
        body = BatchRequest.model_validate(
            {"policy": "atomic", "run": "inline", "items": [item], **context}
        )
        with SessionLocal() as session:
            job, replayed = submit_inline_batch(
                session, body, idempotency_key=key, retention_days=7
            )
            return job.id, replayed

    first, _ = submit({"workspaceKey": W1})
    assert submit({"workspaceKey": W1}) == (first, True)
    elsewhere, replayed = submit({"workspaceKey": W2})
    assert elsewhere != first and not replayed

    with SessionLocal() as session:
        release = resolve_model_snapshot(session).release_db_id
        staged = create_change_set(session, W1, release, source="currentLive")
        change_set, version = staged.id, staged.version
    with pytest.raises(ApiError) as reused:
        submit({"changeSetId": change_set, "expectedChangeSetVersion": version})
    assert (reused.value.code, reused.value.details) == ("IDEMPOTENCY_KEY_REUSED", {"jobId": first})
    with pytest.raises(ApiError) as unknown:
        submit({"changeSetId": str(uuid4()), "expectedChangeSetVersion": 1})
    assert unknown.value.code == "CHANGE_SET_NOT_FOUND"
    with SessionLocal() as session:
        assert (
            session.scalar(select(ChangeSet.version).where(ChangeSet.id == change_set)) == version
        )
