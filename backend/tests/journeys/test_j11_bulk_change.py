"""J11 — Submit a bounded bulk change (USER_JOURNEYS.md).

Records are referred to by ID or by R's unique value ``R.u``; R2 stands under R and has its own.
J11.6 (delete with cascade) is planned (D-6, PG-D18).
"""

import pytest
from scenario import W1, ok, refused


def _attributes(world, structure, values):
    filled = world.required_values(structure)
    filled.update({world.key(k): v for k, v in values.items()})
    return [{"attributeTypeKey": k, "value": v} for k, v in filled.items()]


def _create(world, structure, name, u, **extra):
    unique = f"{structure}.u"
    return {
        "op": "create",
        "applicationKey": world.app(structure),
        "objectTypeKey": world.key(structure),
        "name": name,
        "attributes": _attributes(world, structure, {unique: u}),
        **extra,
    }


def _by_u(world, u):
    return {
        "objectTypeKey": world.key("R"),
        "key": {"attributeTypeKey": world.key("R.u"), "value": u},
    }


def _batch(world, items, *, key=None, context=None, **body):
    """``POST /batches``, inline and independent unless ``body`` says otherwise; live in W1 unless
    ``context`` names another."""
    request = {
        "policy": "independent",
        "run": "inline",
        "items": items,
        **(context or {"workspaceKey": W1}),
        **body,
    }
    headers = {"Idempotency-Key": key} if key is not None else None
    return world.api.client.post("/api/v1/batches", json=request, headers=headers)


def _outcomes(result):
    return [
        (i["status"], i.get("action") or i.get("reason") or i["error"]["code"])
        for i in result["items"]
    ]


def _jobs(world):
    return ok(world.api.get("/jobs", includeTotal=True, pageSize=1))["totalCount"]


def _count(world, structure):
    page = ok(world.api.get(f"/objects/{world.key(structure)}", includeTotal=True, pageSize=1))
    return page["totalCount"]


def _mixed(world):
    """A create, a child of it by key, an update and a delete by ID, and a create whose unique value
    is taken: the records it needs, and the items."""
    changed = world.made("R", "To rename", values={"R.u": "RENAME"})
    removed = world.made("R", "To remove", values={"R.u": "REMOVE"})
    world.made("R", "Holder", values={"R.u": "TAKEN"})
    items = [
        _create(world, "R", "New ledger", "A"),
        _create(world, "R2", "New entry", "A-1", parent=_by_u(world, "A")),
        {
            "op": "update",
            "target": {"id": changed["id"]},
            "expectedVersion": changed["version"],
            "name": "Renamed",
        },
        {"op": "delete", "target": {"id": removed["id"]}, "expectedVersion": removed["version"]},
        _create(world, "R", "Clash", "TAKEN"),
    ]
    return changed, removed, items


@pytest.mark.journey("J11")
@pytest.mark.structures("R", "R.u", "R2", "R2.u")
@pytest.mark.settings(BATCH_MAX_ITEMS="5")
def test_an_independent_batch_with_references_and_a_safe_retry(world):
    """When an independent inline batch creates a record, a child of it referred to by its unique
    value, updates and deletes records by ID, and creates one whose unique value is taken; then the
    same request is sent again with its key; then a batch over the item limit. Then each item's
    outcome comes in item order, the taken value rejected with its single write's code and a pointer
    into the request; the child stands under the new record and its history names the job; the retry
    answers the same response, replayed, creating nothing; the oversized batch is refused naming the
    setting and creates no job."""
    changed, removed, items = _mixed(world)
    response = _batch(world, items, key="k1")
    result = ok(response)
    assert "Idempotent-Replayed" not in response.headers
    assert result["job"]["result"] == "partial"
    assert _outcomes(result) == [
        ("applied", "created"),
        ("applied", "created"),
        ("applied", "updated"),
        ("applied", "deleted"),
        ("rejected", "duplicate_attribute_value"),
    ]
    assert result["items"][4]["error"]["details"]["pointer"].startswith("/items/4")
    parent_id, child_id = result["items"][0]["id"], result["items"][1]["id"]
    assert world.record("R2", child_id)["parentObjectId"] == parent_id
    assert world.record("R", changed["id"])["name"] == "Renamed"
    refused(world.read("R", removed["id"]), 404, "object_not_found")
    history = ok(world.api.get(f"/objects/{world.key('R2')}/{child_id}/history"))["items"]
    assert history[-1]["cause"] == {"kind": "job", "id": result["job"]["id"]}

    records, jobs = _count(world, "R"), _jobs(world)
    replay = _batch(world, items, key="k1")
    assert replay.headers["Idempotent-Replayed"] == "true" and replay.json() == result
    assert (_count(world, "R"), _jobs(world)) == (records, jobs)

    error = refused(_batch(world, items + items[:1]), 413, "batch_too_large")
    assert (error["details"]["setting"], error["details"]["maximum"]) == ("BATCH_MAX_ITEMS", 5)
    assert _jobs(world) == jobs


@pytest.mark.journey("J11.1")
@pytest.mark.structures("R", "R.u", "R2", "R2.u")
def test_an_atomic_batch_applies_everything_or_nothing(world):
    """When the same items run atomic. Then the batch is rejected: the failing item is rejected and
    every other unprocessed as rolled back; no record is created, changed or deleted."""
    changed, removed, items = _mixed(world)
    records = _count(world, "R")
    result = ok(_batch(world, items, policy="atomic"))
    assert result["job"]["result"] == "rejected"
    assert _outcomes(result) == [("unprocessed", "batch_rolled_back")] * 4 + [
        ("rejected", "duplicate_attribute_value")
    ]
    assert _count(world, "R") == records and _count(world, "R2") == 0
    assert world.record("R", changed["id"])["version"] == changed["version"]
    assert world.record("R", removed["id"])["name"] == "To remove"


@pytest.mark.journey("J11.2")
@pytest.mark.structures("R", "R.u", "K")
def test_upserts_by_a_unique_value_or_an_id(world):
    """When upserts by the unique value create a new record, change one without a version, with its
    version and a new name, with a declared overwrite and no version, and equal to the record; one is
    keyed by the ID of another type's record and one by a new ID. Then created; refused for its
    missing version; updated; updated reporting the version it wrote over; unchanged with no new
    version or history entry; refused as another type; created under that ID."""
    values = {"R.u": "UP-1", "R.x1": "kept"}
    existing = world.made("R", "Upserted", values=values)

    def upsert(name, u, **extra):
        return {
            "op": "upsert",
            "applicationKey": world.app("R"),
            "objectTypeKey": world.key("R"),
            "key": {"attributeTypeKey": world.key("R.u")},
            "name": name,
            "attributes": [
                {"attributeTypeKey": a["attributeTypeKey"], "value": a["value"]}
                for a in existing["attributes"]
                if a["attributeTypeKey"] != world.key("R.ro")
            ]
            if u == "UP-1"
            else _attributes(world, "R", {"R.u": u}),
            **extra,
        }

    other = world.made("K", "Not a ledger")
    new_id = "1f0c9a5e-3b7d-4c2a-9e8f-6a5b4c3d2e10"
    by_id = {**_create(world, "R", "By ID", "UP-ID"), "op": "upsert", "key": {"id": new_id}}
    result = ok(
        _batch(
            world,
            [
                upsert("Brand new", "UP-NEW"),
                upsert("Changed without a version", "UP-1"),
                upsert("Renamed", "UP-1", expectedVersion=existing["version"]),
            ],
        )
    )
    assert _outcomes(result) == [
        ("applied", "created"),
        ("rejected", "version_required"),
        ("applied", "updated"),
    ]
    renamed = world.record("R", existing["id"])
    assert renamed["name"] == "Renamed"

    overwritten = ok(_batch(world, [upsert("Overwritten", "UP-1")], onExisting="overwrite"))
    [outcome] = overwritten["items"]
    assert (outcome["action"], outcome["previousVersion"]) == ("updated", renamed["version"])

    current = world.record("R", existing["id"])
    history = ok(
        world.api.get(f"/objects/{world.key('R')}/{existing['id']}/history", includeTotal=True)
    )["totalCount"]
    same = ok(_batch(world, [upsert("Overwritten", "UP-1", expectedVersion=1)]))
    assert _outcomes(same) == [("applied", "unchanged")]
    assert world.record("R", existing["id"])["version"] == current["version"]
    assert (
        ok(world.api.get(f"/objects/{world.key('R')}/{existing['id']}/history", includeTotal=True))[
            "totalCount"
        ]
        == history
    )

    wrong = {**by_id, "key": {"id": other["id"]}}
    result = ok(_batch(world, [wrong, by_id]))
    assert _outcomes(result) == [("rejected", "reference_type_mismatch"), ("applied", "created")]
    assert result["items"][1]["id"] == new_id
    assert world.record("R", new_id)["name"] == "By ID"


@pytest.mark.journey("J11.3")
@pytest.mark.structures("R", "R.u")
def test_a_batch_in_a_change_set_claims_its_version_once(world):
    """When a batch of several items runs in a change set at version v, then one changing nothing,
    one with the stale version, one naming the change set without a version and one naming both
    contexts. Then the change set is at exactly v+1 and live is unchanged; the no-op leaves it there;
    the rest are refused and create no job."""
    cs = world.change_set()
    live = _count(world, "R")
    items = [_create(world, "R", f"Staged {n}", f"CS-{n}") for n in range(3)]
    result = ok(
        _batch(
            world, items, context={"changeSetId": cs["id"]}, expectedChangeSetVersion=cs["version"]
        )
    )
    assert result["job"]["result"] == "applied"
    assert world.current(cs)["version"] == cs["version"] + 1 and _count(world, "R") == live

    staged_id = result["items"][0]["id"]
    staged = world.record("R", staged_id, changeSetId=cs["id"])
    noop = {
        "op": "update",
        "target": {"id": staged_id},
        "expectedVersion": staged["version"],
        "name": staged["name"],
    }
    result = ok(
        _batch(
            world,
            [noop],
            context={"changeSetId": cs["id"]},
            expectedChangeSetVersion=cs["version"] + 1,
        )
    )
    assert _outcomes(result) == [("applied", "unchanged")]
    assert world.current(cs)["version"] == cs["version"] + 1

    jobs = _jobs(world)
    more = [_create(world, "R", "Late", "CS-LATE")]
    staged_in = {"changeSetId": cs["id"]}
    refused(
        _batch(world, more, context=staged_in, expectedChangeSetVersion=cs["version"]),
        409,
        "change_set_version_conflict",
    )
    refused(_batch(world, more, context=staged_in), 409, "change_set_required")
    both = _batch(
        world,
        more,
        context={**staged_in, "workspaceKey": W1},
        expectedChangeSetVersion=cs["version"] + 1,
    )
    refused(both, 422, "invalid_batch_context")
    assert _jobs(world) == jobs


@pytest.mark.journey("J11.4")
@pytest.mark.structures("R", "R.u")
def test_a_model_activated_meanwhile_refuses_the_inline_batch(world):
    """Given actor A's inline batch, which has resolved its model and waits for the workspace, and
    actor B activating another release meanwhile. Then A's batch is refused as a whole: no job, no
    record."""
    model, _key = world.candidate("compatible")
    release = world.install(model)["id"]
    jobs, records = _jobs(world), _count(world, "R")
    with world.holding(W1) as held:
        batch = held.start(lambda: _batch(world, [_create(world, "R", "Too late", "LATE")]))
        held.waiting(1)
        activation = held.start(lambda: world.activate(release))
        ok(activation.result(timeout=20))
    refused(batch.result(timeout=20), 409, "model_release_changed")
    assert (_jobs(world), _count(world, "R")) == (jobs, records)


@pytest.mark.journey("J11.5")
@pytest.mark.structures("R", "R.u")
def test_a_key_reused_with_another_request_or_while_its_job_runs(world):
    """When a key is sent with another request, and a key whose background job is still queued is
    sent again. Then the first is refused and runs nothing; the second asks to retry later."""
    ok(_batch(world, [_create(world, "R", "First", "KEY-1")], key="k1"))
    jobs, records = _jobs(world), _count(world, "R")
    refused(
        _batch(world, [_create(world, "R", "Second", "KEY-2")], key="k1"),
        422,
        "idempotency_key_reused",
    )
    assert (_jobs(world), _count(world, "R")) == (jobs, records)
    # A key is 1–200 characters (API.md; merged from test_batches in H4d).
    for malformed in ("", "k" * 201):
        refused(
            _batch(world, [_create(world, "R", "Bad key", "KEY-X")], key=malformed),
            422,
            "request_validation_error",
        )
    assert (_jobs(world), _count(world, "R")) == (jobs, records)

    background = [_create(world, "R", "Queued", "KEY-3")]
    queued = _batch(world, background, key="k2", run="background")
    assert queued.status_code == 202 and queued.json()["state"] == "queued"
    again = _batch(world, background, key="k2", run="background")
    refused(again, 409, "idempotency_in_progress")
    assert again.headers["Retry-After"]
