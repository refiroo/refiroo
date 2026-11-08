"""J11 — Submit a bounded bulk change (USER_JOURNEYS.md).

Records are referred to by ID or by R's unique value ``R.u``; R2 stands under R and has its own.
J11.6 deletes records with what depends on them under a confirmation of that impact (0.9 K2b,
D120–D123). J11.9 previews a batch before it runs (0.9 K2, D112, D113); the journey application runs
no worker thread, so those tests run the engine's job worker themselves (``_run``).
"""

import copy

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
        ("rejected", "DUPLICATE_ATTRIBUTE_VALUE"),
    ]
    assert result["items"][4]["error"]["details"]["pointer"].startswith("/items/4")
    parent_id, child_id = result["items"][0]["id"], result["items"][1]["id"]
    assert world.record("R2", child_id)["parentObjectId"] == parent_id
    assert world.record("R", changed["id"])["name"] == "Renamed"
    refused(world.read("R", removed["id"]), 404, "OBJECT_NOT_FOUND")
    history = ok(world.api.get(f"/objects/{world.key('R2')}/{child_id}/history"))["items"]
    assert history[-1]["cause"] == {"kind": "job", "id": result["job"]["id"]}

    records, jobs = _count(world, "R"), _jobs(world)
    replay = _batch(world, items, key="k1")
    assert replay.headers["Idempotent-Replayed"] == "true" and replay.json() == result
    assert (_count(world, "R"), _jobs(world)) == (records, jobs)

    error = refused(_batch(world, items + items[:1]), 413, "BATCH_TOO_LARGE")
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
    assert _outcomes(result) == [("unprocessed", "BATCH_ROLLED_BACK")] * 4 + [
        ("rejected", "DUPLICATE_ATTRIBUTE_VALUE")
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
        ("rejected", "VERSION_REQUIRED"),
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
    assert _outcomes(result) == [("rejected", "REFERENCE_TYPE_MISMATCH"), ("applied", "created")]
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
        "CHANGE_SET_VERSION_CONFLICT",
    )
    refused(_batch(world, more, context=staged_in), 409, "CHANGE_SET_REQUIRED")
    both = _batch(
        world,
        more,
        context={**staged_in, "workspaceKey": W1},
        expectedChangeSetVersion=cs["version"] + 1,
    )
    refused(both, 422, "INVALID_BATCH_CONTEXT")
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
    with world.holding(W1, as_write=True) as held:
        batch = held.start(lambda: _batch(world, [_create(world, "R", "Too late", "LATE")]))
        held.waiting(1)
        activation = held.start(lambda: world.activate(release))
        ok(activation.result(timeout=20))
    refused(batch.result(timeout=20), 409, "MODEL_RELEASE_CHANGED")
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
        "IDEMPOTENCY_KEY_REUSED",
    )
    assert (_jobs(world), _count(world, "R")) == (jobs, records)
    # A key is 1–200 characters (API.md; merged from test_batches in H4d).
    for malformed in ("", "k" * 201):
        refused(
            _batch(world, [_create(world, "R", "Bad key", "KEY-X")], key=malformed),
            422,
            "REQUEST_VALIDATION_ERROR",
        )
    assert (_jobs(world), _count(world, "R")) == (jobs, records)

    background = [_create(world, "R", "Queued", "KEY-3")]
    queued = _batch(world, background, key="k2", run="background")
    assert queued.status_code == 202 and queued.json()["state"] == "queued"
    again = _batch(world, background, key="k2", run="background")
    refused(again, 409, "IDEMPOTENCY_IN_PROGRESS")
    assert again.headers["Retry-After"]


def _relation(world, op, source, target, values=None, **extra):
    """A relationship item of ``Bnn`` between records named by ID."""
    item = {
        "op": op,
        "relationTypeKey": world.key("Bnn"),
        "from": {"id": source},
        "to": {"id": target},
    }
    if values is not None:
        item["attributes"] = {world.key(k): v for k, v in values.items()}
    return {**item, **extra}


def _bnn(world, source, **params):
    page = ok(
        world.api.get(
            "/relations",
            objectId=source,
            direction="outgoing",
            relationTypeKey=world.key("Bnn"),
            pageSize=100,
            **params,
        )
    )
    return {item["object"]["id"]: item["relation"] for item in page["items"]}, {
        s["relationTypeKey"]: s["relationSetVersion"] for s in page["relationSets"]
    }


@pytest.mark.journey("J11.7")
@pytest.mark.structures("H", "K", "Bnn", "Bnn.weight", "Hparent")
def test_relationship_items_follow_their_single_writes(world):
    """Given H record h related to K records k2 and k3 (weight 1), and k1 unrelated. When an
    independent batch relates h to k1, ensures that relationship again with the same value, ensures
    h–k3 with another value and no version, changes h–k2 at its version, removes it at its new
    version, relates h with a value below its minimum, creates a containment relationship directly
    and removes a relationship claiming a stale set version. Then each outcome comes in item order:
    created, unchanged, refused for its missing version, updated, deleted, and refused with the
    single writes' codes pointing into the items; h's relationships are exactly the applied ones and
    its history names the job. Sent again with a declared overwrite, h–k3 is updated reporting the
    version it wrote over."""
    h = world.made("H", "Batch relating")
    k1, k2, k3 = (world.ids[f"k0{n}"] for n in (1, 2, 3))
    r2 = ok(world.relate("Bnn", h["id"], k2, {"Bnn.weight": 1}), 201)
    r3 = ok(world.relate("Bnn", h["id"], k3, {"Bnn.weight": 1}), 201)
    _relations, sets = _bnn(world, h["id"])
    seen = sets[world.key("Bnn")]

    ensure_k3 = _relation(world, "ensureRelation", h["id"], k3, {"Bnn.weight": 5})
    items = [
        _relation(world, "createRelation", h["id"], k1, {"Bnn.weight": 2}),
        _relation(world, "ensureRelation", h["id"], k1, {"Bnn.weight": 2}),
        ensure_k3,
        {
            "op": "updateRelation",
            "id": r2["id"],
            "expectedVersion": r2["version"],
            "attributes": {world.key("Bnn.weight"): 7},
        },
        {"op": "deleteRelation", "id": r2["id"], "expectedVersion": r2["version"] + 1},
        _relation(world, "createRelation", h["id"], k1, {"Bnn.weight": 0}),
        {
            "op": "createRelation",
            "relationTypeKey": world.key("Hparent"),
            "from": {"id": world.ids["h1"]},
            "to": {"id": h["id"]},
        },
        {
            "op": "deleteRelation",
            "id": r3["id"],
            "expectedVersion": r3["version"],
            "expectedRelationSetVersion": seen,
            "relationSetDirection": "outgoing",
        },
    ]
    result = ok(_batch(world, items))
    assert _outcomes(result) == [
        ("applied", "created"),
        ("applied", "unchanged"),
        ("rejected", "VERSION_REQUIRED"),
        ("applied", "updated"),
        ("applied", "deleted"),
        ("rejected", "ATTRIBUTE_BELOW_MINIMUM"),
        ("rejected", "IMMUTABLE_RELATION"),
        ("rejected", "RELATION_SET_VERSION_CONFLICT"),
    ]
    created = result["items"][0]
    assert created["version"] == 1 and result["items"][1]["relationId"] == created["relationId"]
    assert result["items"][3]["version"] == r2["version"] + 1
    assert result["items"][5]["error"]["details"]["pointer"] == "/items/5/attributes"
    assert (
        result["items"][7]["error"]["details"]["pointer"] == "/items/7/expectedRelationSetVersion"
    )
    relations, _sets = _bnn(world, h["id"])
    assert set(relations) == {k1, k3}
    assert relations[k1]["id"] == created["relationId"]
    assert relations[k3]["attributes"][world.key("Bnn.weight")] == 1
    history = ok(world.api.get(f"/objects/{world.key('H')}/{h['id']}/history"))["items"]
    assert {"kind": "job", "id": result["job"]["id"]} in [item.get("cause") for item in history]

    overwritten = ok(_batch(world, [ensure_k3], onExisting="overwrite"))
    [outcome] = overwritten["items"]
    assert (outcome["action"], outcome["previousVersion"]) == ("updated", r3["version"])
    assert _bnn(world, h["id"])[0][k3]["attributes"][world.key("Bnn.weight")] == 5


@pytest.mark.journey("J11.7", "J11.3")
@pytest.mark.structures("H", "K", "Bnn", "Bnn.weight")
def test_relationship_items_in_a_change_set(world):
    """Given H record h related to K record k2, and change set CS at version v. When a batch in CS
    relates h to k1 and k3 and changes h–k2's value, then a second batch removes the staged h–k3.
    Then CS is at v+2, holds h–k1 and the changed value without h–k3, and live is unchanged; after
    publishing live holds them."""
    h = world.made("H", "Staged batch relating")
    k1, k2, k3 = (world.ids[f"k0{n}"] for n in (1, 2, 3))
    r2 = ok(world.relate("Bnn", h["id"], k2, {"Bnn.weight": 1}), 201)
    cs = world.change_set()
    items = [
        _relation(world, "createRelation", h["id"], k1, {"Bnn.weight": 2}),
        _relation(world, "createRelation", h["id"], k3, {"Bnn.weight": 3}, ref="k3"),
        {
            "op": "updateRelation",
            "id": r2["id"],
            "expectedVersion": r2["version"],
            "attributes": {world.key("Bnn.weight"): 9},
        },
    ]
    result = ok(
        _batch(
            world, items, context={"changeSetId": cs["id"]}, expectedChangeSetVersion=cs["version"]
        )
    )
    assert result["job"]["result"] == "applied"
    k3_relation = result["items"][1]["relationId"]
    removal = {"op": "deleteRelation", "id": k3_relation, "expectedVersion": 1}
    ok(
        _batch(
            world,
            [removal],
            context={"changeSetId": cs["id"]},
            expectedChangeSetVersion=cs["version"] + 1,
        )
    )
    assert world.current(cs)["version"] == cs["version"] + 2

    staged, _sets = _bnn(world, h["id"], changeSetId=cs["id"])
    assert set(staged) == {k1, k2}
    assert staged[k2]["attributes"][world.key("Bnn.weight")] == 9
    live, _sets = _bnn(world, h["id"])
    assert set(live) == {k2} and live[k2]["attributes"][world.key("Bnn.weight")] == 1
    world.publish(cs)
    published, _sets = _bnn(world, h["id"])
    assert set(published) == {k1, k2}
    assert published[k2]["attributes"][world.key("Bnn.weight")] == 9


@pytest.mark.journey("J11.8")
@pytest.mark.structures("R", "R.u", "G", "D", "Bown", "K", "B1n")
def test_a_record_its_required_relationship_and_its_set_in_one_atomic_batch(world):
    """When an atomic batch creates R record r, creates D record d requiring r by r's unique value,
    and replaces r's set of one-to-many relationships with K records k1 and k2, claiming the empty
    set's version 0. Then everything applies. The same batch for another r with a stale claim on its
    last item leaves every item unprocessed and creates nothing."""
    g = world.made("G", "Atomic scope")
    k1, k2 = (world.made("K", f"Atomic token {n}")["id"] for n in (1, 2))

    def items(u, claimed):
        owner = _by_u(world, u)
        dependant = {
            "op": "create",
            "applicationKey": world.app("D"),
            "objectTypeKey": world.key("D"),
            "name": f"Needs {u}",
            "parent": {"id": world.dependant_parent(g["id"])},
            "attributes": [
                {"attributeTypeKey": k, "value": v} for k, v in world.required_values("D").items()
            ],
            "initialRelations": [
                {"relationTypeKey": world.key("Bown"), "direction": "incoming", "object": owner}
            ],
        }
        mapped = {
            "op": "replaceRelationSet",
            "relationTypeKey": world.key("B1n"),
            "fromObjectTypeKey": world.key("R"),
            "toObjectTypeKey": world.key("K"),
            "direction": "outgoing",
            "anchor": owner,
            "targets": [{"object": {"id": k}} for k in (k1, k2)],
            "expectedRelationSetVersion": claimed,
        }
        return [_create(world, "R", f"Owner {u}", u), dependant, mapped]

    result = ok(_batch(world, items("ATOM-A", 0), policy="atomic"))
    assert _outcomes(result) == [
        ("applied", "created"),
        ("applied", "created"),
        ("applied", "updated"),
    ]
    owner = result["items"][0]["id"]
    linked = ok(world.api.get("/relations", objectId=owner, relationTypeKey=world.key("B1n")))
    assert {item["object"]["id"] for item in linked["items"]} == {k1, k2}

    records = _count(world, "R")
    rolled_back = ok(_batch(world, items("ATOM-B", 5), policy="atomic"))
    assert _outcomes(rolled_back) == [("unprocessed", "BATCH_ROLLED_BACK")] * 2 + [
        ("rejected", "RELATION_SET_VERSION_CONFLICT")
    ]
    assert _count(world, "R") == records


@pytest.mark.journey("J11.1")
@pytest.mark.structures("R", "R.u")
def test_a_unique_value_handed_on_in_one_batch(world):
    """Given R1 holding the unique value X and R2 holding Y. When an atomic batch changes R1 to Z,
    then R2 to X. Then both are applied; a third record with X is refused naming R2; once R2 is
    deleted, X can be given again; the same value is accepted in another workspace."""
    r1 = world.made("R", "First holder", values={"R.u": "HAND-X"})
    r2 = world.made("R", "Second holder", values={"R.u": "HAND-Y"})
    u = world.key("R.u")
    items = [
        {
            "op": "update",
            "target": {"id": record["id"]},
            "expectedVersion": record["version"],
            "attributes": [{"attributeTypeKey": u, "value": value}],
        }
        for record, value in ((r1, "HAND-Z"), (r2, "HAND-X"))
    ]
    result = ok(_batch(world, items, policy="atomic"))
    assert _outcomes(result) == [("applied", "updated"), ("applied", "updated")]
    assert world.value(world.record("R", r1["id"]), "R.u") == "HAND-Z"
    assert world.value(world.record("R", r2["id"]), "R.u") == "HAND-X"

    refused(world.create("R", "Third", values={"R.u": "HAND-X"}), 409, "DUPLICATE_ATTRIBUTE_VALUE")
    r2 = world.record("R", r2["id"])
    ok(world.api.delete(f"/objects/{world.key('R')}/{r2['id']}", expectedVersion=r2["version"]), 204)
    world.made("R", "Third", values={"R.u": "HAND-X"})
    world.made("R", "Elsewhere", values={"R.u": "HAND-X"}, workspace="second-site")


# --- J11.9: a batch previewed, then applied (0.9 K2) ---------------------------------------------


def _run(world):
    return world.api.client.app.state.job_worker.run_until_idle()


def _job(world, job):
    return ok(world.api.get(f"/jobs/{job['id']}"))


def _items(world, job):
    page = ok(world.api.get(f"/jobs/{job['id']}/items", pageSize=100))
    return [
        (i["status"], i.get("action") or i.get("reason") or i["error"]["code"])
        for i in page["items"]
    ]


def _previewed(world, items, **body):
    """A background batch sent with ``stage: preview`` and run until it waits."""
    job = ok(_batch(world, items, run="background", stage="preview", **body), 202)
    assert job["state"] == "queued" and job["parameters"]["stage"] == "preview"
    _run(world)
    job = _job(world, job)
    assert job["state"] == "awaiting_confirmation", (job["state"], job["error"])
    return job


def _set_owner(record, owner, world):
    return {
        "op": "update",
        "target": {"id": record["id"]},
        "expectedVersion": record["version"],
        "attributes": [{"attributeTypeKey": world.key("R.q"), "value": owner}],
        "ref": record["name"],
    }


def _feed_head(world):
    return ok(world.api.get(f"/workspaces/{W1}/feed", pageSize=1))["headPosition"]


@pytest.mark.journey("J11.9")
@pytest.mark.structures("R", "R.u", "R.q")
def test_a_preview_changes_nothing_and_says_what_applying_would(world):
    """Given three records: one to change, one already holding the value, and one changed since it
    was read. When a background batch setting the value on all three is previewed. Then the job
    waits with a complete preview: one updated, one unchanged, one refused for its version, the
    result partial; the records, the feed head and the history are as before. When confirmed, the
    job completes with the same outcomes in place of the preview's, and the value is written."""
    plain = world.made("R", "Plain", values={"R.u": "PV-1"})
    holding = world.made("R", "Holding", values={"R.u": "PV-2", "R.q": "Ops"})
    moved = world.made("R", "Moved on", values={"R.u": "PV-3"})
    ok(world.update("R", moved["id"], moved["version"], name="Moved on, renamed"))
    head = _feed_head(world)
    history = ok(world.api.get(f"/objects/{world.key('R')}/{plain['id']}/history"))["items"]

    items = [_set_owner(record, "Ops", world) for record in (plain, holding, moved)]
    job = _previewed(world, items)
    preview = job["preview"]
    assert preview["coverage"] == "complete" and preview["result"] == "partial"
    assert preview["items"] == {"total": 3, "previewed": 3} and "rows" not in preview
    assert preview["counts"] == {
        "created": 0,
        "updated": 1,
        "unchanged": 1,
        "deleted": 0,
        "rejected": 1,
    }
    expected = [("applied", "updated"), ("applied", "unchanged"), ("rejected", "VERSION_CONFLICT")]
    assert _items(world, job) == expected
    unchanged = world.record("R", plain["id"])
    assert unchanged["version"] == plain["version"]
    assert world.value(unchanged, "R.q") == world.value(plain, "R.q")
    assert _feed_head(world) == head
    assert ok(world.api.get(f"/objects/{world.key('R')}/{plain['id']}/history"))["items"] == history

    confirmed = ok(world.api.post(f"/jobs/{job['id']}/confirm", None), 202)
    assert confirmed["state"] == "queued" and confirmed["confirmedAt"]
    assert confirmed["preview"] == preview
    _run(world)
    done = _job(world, job)
    assert done["state"] == "completed" and done["result"] == "partial", done["error"]
    assert done["progress"] == {"total": 3, "processed": 3}
    assert _items(world, done) == expected
    assert world.value(world.record("R", plain["id"]), "R.q") == "Ops"


@pytest.mark.journey("J11.9", "J11.3")
@pytest.mark.structures("R", "R.u", "R.q")
def test_a_preview_in_a_change_set_and_a_write_before_confirming(world):
    """Given a change set holding a record. When a batch in it is previewed. Then the change set
    keeps its version. When the change set is written before confirming. Then confirming is
    refused as a stale change set and the job keeps waiting; cancelling it ends it cancelled."""
    cs = world.change_set()
    staged = world.made("R", "Staged", values={"R.u": "PV-CS"}, change_set=cs)
    cs = world.current(cs)
    job = _previewed(
        world,
        [_set_owner(staged, "Ops", world)],
        context={"changeSetId": cs["id"]},
        expectedChangeSetVersion=cs["version"],
    )
    assert job["preview"]["counts"]["updated"] == 1
    assert world.current(cs)["version"] == cs["version"]

    world.made("R", "Meanwhile", values={"R.u": "PV-CS2"}, change_set=cs)
    refused(world.api.post(f"/jobs/{job['id']}/confirm", None), 409, "CHANGE_SET_VERSION_CONFLICT")
    assert _job(world, job)["state"] == "awaiting_confirmation"
    cancelled = ok(world.api.post(f"/jobs/{job['id']}/cancel", None), 202)
    assert cancelled["state"] == "cancelled"
    staged_now = world.record("R", staged["id"], changeSetId=cs["id"])
    assert world.value(staged_now, "R.q") == world.value(staged, "R.q")


@pytest.mark.journey("J11.9", "J11.1")
@pytest.mark.structures("R", "R.u", "R.q")
def test_applying_a_preview_is_decided_on_the_data_as_it_is_then(world):
    """Given two records previewed under atomic, both applying. When one is changed live before
    confirming. Then execution refuses it for its version and, atomic, writes nothing."""
    first = world.made("R", "First", values={"R.u": "PV-A"})
    second = world.made("R", "Second", values={"R.u": "PV-B"})
    items = [_set_owner(record, "Ops", world) for record in (first, second)]
    job = _previewed(world, items, policy="atomic")
    assert job["preview"]["result"] == "applied"

    ok(world.update("R", second["id"], second["version"], name="Second, renamed"))
    ok(world.api.post(f"/jobs/{job['id']}/confirm", None), 202)
    _run(world)
    done = _job(world, job)
    assert done["state"] == "completed" and done["result"] == "rejected", done["error"]
    assert _items(world, done) == [
        ("unprocessed", "BATCH_ROLLED_BACK"),
        ("rejected", "VERSION_CONFLICT"),
    ]
    assert world.value(world.record("R", first["id"]), "R.q") == world.value(first, "R.q")


@pytest.mark.journey("J11.9")
@pytest.mark.structures("R", "R.u", "R.q")
@pytest.mark.settings(JOB_PREVIEW_MAX_ITEMS="2")
def test_a_preview_is_a_background_job_bounded_by_its_setting(world):
    """When a preview is sent to run inline. Then it is refused as a request shape. When three items
    are previewed with the preview limit at two. Then the first two run, the preview is a sample,
    and the capabilities report the limit as ``previewMaxItems``."""
    records = [world.made("R", f"Sampled {n}", values={"R.u": f"PV-S{n}"}) for n in range(3)]
    items = [_set_owner(record, "Ops", world) for record in records]
    jobs = _jobs(world)
    refused(_batch(world, items, stage="preview"), 422, "REQUEST_VALIDATION_ERROR")
    assert _jobs(world) == jobs

    job = _previewed(world, items)
    assert job["preview"]["coverage"] == "sample"
    assert job["preview"]["items"] == {"total": 3, "previewed": 2}
    limits = ok(world.api.get("/capabilities"))["integrationJobs"]["limits"]
    assert limits["previewMaxItems"] == 2 and "importPreviewMaxItems" not in limits


# --- J11.6: deleting records with what depends on them (0.9 K2b) --------------------------------


def _remove(record, **extra):
    return {
        "op": "delete",
        "target": {"id": record["id"]},
        "expectedVersion": record["version"],
        "ref": record["name"],
        **extra,
    }


def _owner_of_much(world, name):
    """An R record with two R2 children, a D record it owns (under a G record) and a link to a K
    record: what deleting it removes, and the records that stay."""
    owner = world.made("R", name)
    children = [world.made("R2", f"{name} child {n}", parent=owner["id"]) for n in range(2)]
    g = world.made("G", f"Scope of {name}")
    owned = world.made(
        "D",
        f"Owned by {name}",
        parent=world.dependant_parent(g["id"]),
        relations=[world.owner("Bown", owner["id"])],
    )
    kept = world.made("K", f"Kept by {name}")
    ok(world.relate("B1n", owner["id"], kept["id"]), 201)
    return world.record("R", owner["id"]), children, owned, kept


def _feed_after(world, after):
    entries = []
    while True:
        page = ok(world.api.get(f"/workspaces/{W1}/feed", after=after, pageSize=100))
        entries += page["items"]
        after = page["nextAfter"]
        if after == page["headPosition"]:
            return entries


@pytest.mark.journey("J11.6", "J11.9")
@pytest.mark.structures("R", "R2", "G", "D", "Bown", "K", "B1n")
def test_a_cascading_delete_previewed_then_applied(world):
    """Given a leaf record; a record with two children, a record it owns and a link to a record that
    stays; and one of those children, listed after it. When the three are deleted with cascade in a
    previewed batch. Then the preview deletes nothing and gives each item's impact: the owner's
    records by type, its relationships and the two that reach records that stay; the child goes with
    the owner's item; the summary totals them. When confirmed. Then the same outcomes, every record
    of the impact is gone, the linked record stays, and the feed has the job's entries, each
    record's relationships before its records."""
    leaf = world.made("R", "Leaf")
    owner, children, owned, kept = _owner_of_much(world, "Owner")
    head = _feed_head(world)
    items = [
        _remove(leaf, cascade=True),
        _remove(owner, cascade=True),
        _remove(children[0], cascade=True),
    ]

    job = _previewed(world, items)
    expected = [("applied", "deleted"), ("applied", "deleted"), ("applied", "unchanged")]
    assert _items(world, job) == expected
    outcomes = ok(world.api.get(f"/jobs/{job['id']}/items", pageSize=100))["items"]
    impact = outcomes[1]["impact"]
    assert impact["objectCount"] == 4
    assert impact["objectsByType"] == {world.key("R"): 1, world.key("R2"): 2, world.key("D"): 1}
    assert impact["retainedAssociationCount"] == 2 and impact["deletionPreviewToken"]
    assert outcomes[0]["impact"]["objectCount"] == 1
    assert outcomes[2]["deletedWithItem"] == 1 and "impact" not in outcomes[2]
    deletion = job["preview"]["deletion"]
    assert deletion["objectCount"] == 5
    assert deletion["relationshipCount"] == sum(o["impact"]["relationshipCount"] for o in outcomes[:2])
    assert job["preview"]["counts"]["deleted"] == 2
    for structure, record in (("R", owner), ("R2", children[1]), ("D", owned), ("R", leaf)):
        assert world.record(structure, record["id"])["version"] == record["version"]
    assert _feed_head(world) == head

    ok(world.api.post(f"/jobs/{job['id']}/confirm", None), 202)
    _run(world)
    done = _job(world, job)
    assert done["state"] == "completed" and done["result"] == "applied", done["error"]
    assert _items(world, done) == expected
    for structure, record in (
        ("R", leaf), ("R", owner), ("R2", children[0]), ("R2", children[1]), ("D", owned),
    ):
        refused(world.read(structure, record["id"]), 404, "OBJECT_NOT_FOUND")
    assert world.record("K", kept["id"])["id"] == kept["id"]

    entries = _feed_after(world, head)
    assert all(e["cause"] == {"kind": "job", "id": job["id"]} for e in entries)
    deleted = [e["id"] for e in entries if e["kind"] == "object"]
    assert set(deleted) == {leaf["id"], owner["id"], *(c["id"] for c in children), owned["id"]}
    after_leaf = entries[1:]
    kinds = [e["kind"] for e in after_leaf]
    assert kinds == sorted(kinds, key=lambda kind: kind != "relation"), kinds
    assert {(e["kind"], e["action"]) for e in after_leaf} == {
        ("relation", "deleted"),
        ("object", "deleted"),
    }


@pytest.mark.journey("J11.6", "J11.1")
@pytest.mark.structures("R", "R2", "G", "D", "Bown", "K", "B1n")
def test_an_impact_changed_after_the_preview_refuses_that_item(world):
    """Given two records with dependants, previewed for a cascading delete. When a child is added
    under one before confirming. Then that item is refused as a changed preview and the other is
    deleted. Under all or nothing the same change leaves both."""
    first, *_ = _owner_of_much(world, "First")
    second, *_ = _owner_of_much(world, "Second")
    job = _previewed(world, [_remove(first, cascade=True), _remove(second, cascade=True)])
    late = world.made("R2", "Late child", parent=second["id"])
    ok(world.api.post(f"/jobs/{job['id']}/confirm", None), 202)
    _run(world)
    done = _job(world, job)
    assert done["result"] == "partial", done["error"]
    assert _items(world, done) == [("applied", "deleted"), ("rejected", "DELETION_PREVIEW_CHANGED")]
    refused(world.read("R", first["id"]), 404, "OBJECT_NOT_FOUND")
    assert world.record("R2", late["id"])["parentObjectId"] == second["id"]

    third, *_ = _owner_of_much(world, "Third")
    fourth, *_ = _owner_of_much(world, "Fourth")
    items = [_remove(third, cascade=True), _remove(fourth, cascade=True)]
    job = _previewed(world, items, policy="atomic")
    assert job["preview"]["result"] == "applied"
    world.made("R2", "Another late child", parent=fourth["id"])
    ok(world.api.post(f"/jobs/{job['id']}/confirm", None), 202)
    _run(world)
    done = _job(world, job)
    assert done["result"] == "rejected", done["error"]
    assert _items(world, done) == [
        ("unprocessed", "BATCH_ROLLED_BACK"),
        ("rejected", "DELETION_PREVIEW_CHANGED"),
    ]
    assert world.record("R", third["id"])["id"] == third["id"]


@pytest.mark.journey("J11.6", "J11.1")
@pytest.mark.structures("R", "R2", "G", "D", "Bown", "K", "B1n")
def test_a_record_edited_after_the_preview_is_refused_with_its_current_version(world):
    """Given two records previewed for a cascading delete. When someone renames the second before
    confirming. Then the first is deleted and the second refused as a changed preview, naming the
    version it has now. When it is previewed again at that version, the delete is applied (0.13
    DOC11: Preview again claimed the old version and was refused again)."""
    first, *_ = _owner_of_much(world, "First")
    second, *_ = _owner_of_much(world, "Second")
    job = _previewed(world, [_remove(first, cascade=True), _remove(second, cascade=True)])
    edited = ok(world.update("R", second["id"], second["version"], name="Second renamed"))
    ok(world.api.post(f"/jobs/{job['id']}/confirm", None), 202)
    _run(world)
    done = _job(world, job)
    assert _items(world, done) == [("applied", "deleted"), ("rejected", "DELETION_PREVIEW_CHANGED")]
    refused_item = ok(world.api.get(f"/jobs/{done['id']}/items", status="rejected"))["items"][0]
    assert refused_item["error"]["details"]["currentVersion"] == edited["version"]

    again = _previewed(
        world,
        [
            _remove(
                {**second, "version": refused_item["error"]["details"]["currentVersion"]},
                cascade=True,
            )
        ],
    )
    ok(world.api.post(f"/jobs/{again['id']}/confirm", None), 202)
    _run(world)
    assert _items(world, _job(world, again)) == [("applied", "deleted")]
    refused(world.read("R", second["id"]), 404, "OBJECT_NOT_FOUND")


@pytest.mark.journey("J11.6", "J11.3")
@pytest.mark.structures("R", "R2", "G", "D", "Bown", "K", "B1n")
def test_a_cascading_delete_in_a_change_set_and_without_a_preview(world):
    """Given a change set holding a record with dependants. When it is deleted with cascade through
    a previewed batch in the change set. Then the change set no longer holds it or its dependants
    and live data still does. In batches sent to execute at once: cascade without a token is refused
    as needing a preview; without cascade a record with dependants is refused with its impact; the
    token the single delete's refusal gives confirms the batch item."""
    owner, children, owned, _kept = _owner_of_much(world, "Staged owner")
    cs = world.current(world.change_set())
    job = _previewed(
        world,
        [_remove(owner, cascade=True)],
        context={"changeSetId": cs["id"]},
        expectedChangeSetVersion=cs["version"],
    )
    assert job["preview"]["deletion"]["objectCount"] == 4
    ok(world.api.post(f"/jobs/{job['id']}/confirm", None), 202)
    _run(world)
    done = _job(world, job)
    assert done["state"] == "completed" and done["result"] == "applied", done["error"]
    for structure, record in (("R", owner), ("R2", children[0]), ("D", owned)):
        refused(world.read(structure, record["id"], changeSetId=cs["id"]), 404, "OBJECT_NOT_FOUND")
        assert world.record(structure, record["id"])["id"] == record["id"]

    no_token = ok(_batch(world, [_remove(owner, cascade=True)]))
    assert _outcomes(no_token) == [("rejected", "DELETION_PREVIEW_REQUIRED")]
    plain = ok(_batch(world, [_remove(owner)]))
    assert _outcomes(plain) == [("rejected", "OBJECT_HAS_DEPENDANTS")]
    assert plain["items"][0]["error"]["details"]["impact"]["objectCount"] == 4

    single = world.api.delete(
        f"/objects/{world.key('R')}/{owner['id']}", expectedVersion=owner["version"]
    )
    token = refused(single, 409, "OBJECT_HAS_DEPENDANTS")["details"]["deletionPreviewToken"]
    confirmed = ok(_batch(world, [_remove(owner, cascade=True, deletionPreviewToken=token)]))
    assert _outcomes(confirmed) == [("applied", "deleted")]
    assert confirmed["items"][0]["impact"]["objectCount"] == 4
    for structure, record in (("R", owner), ("R2", children[1]), ("D", owned)):
        refused(world.read(structure, record["id"]), 404, "OBJECT_NOT_FOUND")


# --- J11.10, J11.11: relationships of many records changed by their ends (0.9 K3) ---------------


def _apart(world, source, target, structure="Bnn", **extra):
    """An ``ensureNoRelation`` item between records named by ID (D129)."""
    return {
        "op": "ensureNoRelation",
        "relationTypeKey": world.key(structure),
        "from": {"id": source},
        "to": {"id": target},
        **extra,
    }


def _replaced(world, anchor, targets, **extra):
    """A ``replaceRelationSet`` item of ``anchor``'s outgoing ``Bnn`` set, without a claim."""
    return {
        "op": "replaceRelationSet",
        "relationTypeKey": world.key("Bnn"),
        "fromObjectTypeKey": world.key("H"),
        "toObjectTypeKey": world.key("K"),
        "direction": "outgoing",
        "anchor": {"id": anchor},
        "targets": [{"object": {"id": target}} for target in targets],
        **extra,
    }


@pytest.mark.journey("J11.10")
@pytest.mark.structures("H", "K", "Bnn", "N", "Breq", "Hparent")
def test_two_records_kept_apart_by_their_ends(world):
    """Given H records a related to K record x, b not, c related to x, an N record needing a, and a
    child of h1. When a batch keeps a and x apart, b and x, a and its notice, h1 and its child, and
    c and x claiming a stale relationship version. Then a–x is deleted with its relationship's ID
    and audited with the job as cause, b–x is unchanged, the required relationship, the
    containment and the stale version are refused with the single delete's codes. Sent again, a–x
    and b–x are both unchanged. In a change set c–x is removed there and stays live."""
    a, b, c = (world.made("H", f"Apart {n}") for n in "ABC")
    x = world.ids["k01"]
    ax = ok(world.relate("Bnn", a["id"], x), 201)
    cx = ok(world.relate("Bnn", c["id"], x), 201)
    notice = world.made("N", "Needed by A", relations=[world.owner("Breq", a["id"])])
    child = world.made("H", "Held child", parent=world.ids["h1"])

    items = [
        _apart(world, a["id"], x),
        _apart(world, b["id"], x),
        _apart(world, a["id"], notice["id"], "Breq"),
        _apart(world, world.ids["h1"], child["id"], "Hparent"),
        _apart(world, c["id"], x, expectedVersion=cx["version"] + 1),
    ]
    result = ok(_batch(world, items))
    assert _outcomes(result) == [
        ("applied", "deleted"),
        ("applied", "unchanged"),
        ("rejected", "REQUIRED_RELATION"),
        ("rejected", "IMMUTABLE_RELATION"),
        ("rejected", "VERSION_CONFLICT"),
    ]
    assert result["items"][0]["relationId"] == ax["id"]
    assert "relationId" not in result["items"][1]
    assert set(_bnn(world, a["id"])[0]) == set()
    history = ok(world.api.get(f"/objects/{world.key('H')}/{a['id']}/history"))["items"]
    assert {"kind": "job", "id": result["job"]["id"]} in [item.get("cause") for item in history]

    again = ok(_batch(world, items[:2]))
    assert _outcomes(again) == [("applied", "unchanged"), ("applied", "unchanged")]

    cs = world.change_set()
    staged = ok(
        _batch(
            world,
            [_apart(world, c["id"], x)],
            context={"changeSetId": cs["id"]},
            expectedChangeSetVersion=cs["version"],
        )
    )
    assert _outcomes(staged) == [("applied", "deleted")]
    assert set(_bnn(world, c["id"], changeSetId=cs["id"])[0]) == set()
    assert set(_bnn(world, c["id"])[0]) == {x}


@pytest.mark.journey("J11.11", "J11.9")
@pytest.mark.structures("H", "K", "Bnn")
def test_a_previewed_set_replacement_claims_what_it_showed(world):
    """Given H records h1 related to k1, h2 to k2 and h3 to both. When a background preview makes
    each set k1 and k2 without a claim. Then h1 and h2 would be updated and h3 is unchanged, each
    with the set's version it found, and nothing is written. When h2's set changes before
    confirming. Then h2 is refused for its set's version and the others apply. Under atomic, such a
    change writes nothing. Executed without a preview or a claim, a replacement still needs one."""
    k1, k2, k3 = (world.ids[f"k0{n}"] for n in (1, 2, 3))

    def anchors(label):
        h1, h2, h3 = (world.made("H", f"{label} {n}")["id"] for n in (1, 2, 3))
        for source, target in ((h1, k1), (h2, k2), (h3, k1), (h3, k2)):
            ok(world.relate("Bnn", source, target), 201)
        return h1, h2, h3

    h1, h2, h3 = anchors("Claimed")
    found = {h: _bnn(world, h)[1][world.key("Bnn")] for h in (h1, h2, h3)}
    items = [_replaced(world, h, (k1, k2), ref=f"set {n}") for n, h in enumerate((h1, h2, h3))]
    job = _previewed(world, items)
    assert _items(world, job) == [
        ("applied", "updated"),
        ("applied", "updated"),
        ("applied", "unchanged"),
    ]
    outcomes = ok(world.api.get(f"/jobs/{job['id']}/items"))["items"]
    assert [o["previousRelationSetVersion"] for o in outcomes] == [found[h] for h in (h1, h2, h3)]
    assert set(_bnn(world, h1)[0]) == {k1}

    ok(world.relate("Bnn", h2, k3), 201)
    ok(world.api.post(f"/jobs/{job['id']}/confirm", None), 202)
    _run(world)
    done = _job(world, job)
    assert done["result"] == "partial", done["error"]
    assert _items(world, done) == [
        ("applied", "updated"),
        ("rejected", "RELATION_SET_VERSION_CONFLICT"),
        ("applied", "unchanged"),
    ]
    assert set(_bnn(world, h1)[0]) == {k1, k2}
    assert set(_bnn(world, h2)[0]) == {k2, k3}

    a1, a2, a3 = anchors("Atomic")
    job = _previewed(world, [_replaced(world, h, (k1, k2)) for h in (a1, a2, a3)], policy="atomic")
    ok(world.relate("Bnn", a2, k3), 201)
    ok(world.api.post(f"/jobs/{job['id']}/confirm", None), 202)
    _run(world)
    assert _job(world, job)["result"] == "rejected"
    assert set(_bnn(world, a1)[0]) == {k1}

    executed = ok(_batch(world, [_replaced(world, a1, (k1, k2))]))
    assert _outcomes(executed) == [("rejected", "VERSION_REQUIRED")]


@pytest.mark.journey("J11.10", "J11.9")
@pytest.mark.structures("H", "K", "Bnn")
def test_relationships_added_and_removed_together_and_sent_again(world):
    """Given H records h1 and h2 each related to k2. When a preview relates both to k1 and keeps
    both apart from k2, and is confirmed. Then two relationships are created and two deleted. Sent
    again, every item is unchanged."""
    k1, k2 = world.ids["k01"], world.ids["k02"]
    hs = [world.made("H", f"Swapped {n}")["id"] for n in (1, 2)]
    for h in hs:
        ok(world.relate("Bnn", h, k2), 201)
    items = [
        item
        for h in hs
        for item in (_relation(world, "ensureRelation", h, k1), _apart(world, h, k2))
    ]
    job = _previewed(world, items)
    counts = job["preview"]["counts"]
    assert (counts["created"], counts["deleted"], counts["rejected"]) == (2, 2, 0)
    ok(world.api.post(f"/jobs/{job['id']}/confirm", None), 202)
    _run(world)
    assert _job(world, job)["result"] == "applied"
    assert all(set(_bnn(world, h)[0]) == {k1} for h in hs)

    again = ok(_batch(world, items))
    assert _outcomes(again) == [("applied", "unchanged")] * 4


# --- J11.12: a record holds one of a kind (0.9 K3a) ------------------------------------------------


def _held(world, source, **params):
    """The K records ``source`` holds through ``Bn1``, by ID."""
    page = ok(
        world.api.get(
            "/relations",
            objectId=source,
            direction="outgoing",
            relationTypeKey=world.key("Bn1"),
            pageSize=100,
            **params,
        )
    )
    return {item["object"]["id"] for item in page["items"]}


def _bn1_set(world, anchor, targets, **extra):
    """A ``replaceRelationSet`` item of ``anchor``'s outgoing ``Bn1`` set; the batch overwrites."""
    return {
        "op": "replaceRelationSet",
        "relationTypeKey": world.key("Bn1"),
        "fromObjectTypeKey": world.key("H"),
        "toObjectTypeKey": world.key("K"),
        "direction": "outgoing",
        "anchor": {"id": anchor},
        "targets": [{"object": {"id": target}} for target in targets],
        **extra,
    }


@pytest.mark.journey("J11.12")
@pytest.mark.structures("H", "K", "Bn1")
def test_a_record_holds_one_of_a_kind(world):
    """Given a many-to-one binding from H to K, H record h1 holding k1. When h1 is given a second K
    by the single write, by a batch item, by a set of two and in a change set. Then each is refused
    for cardinality, and h1 still holds k1. When h2 also takes k1, and h1's set becomes k2. Then
    both are written: a K serves many H, and a set of one replaces the one held."""
    k1, k2, k3 = (world.ids[f"k0{n}"] for n in (1, 2, 3))
    h1, h2 = (world.made("H", f"Holder {n}")["id"] for n in (1, 2))
    ok(world.relate("Bn1", h1, k1), 201)

    refused(world.relate("Bn1", h1, k2), 409, "CARDINALITY_VIOLATION")
    second = {
        "op": "ensureRelation",
        "relationTypeKey": world.key("Bn1"),
        "from": {"id": h1},
        "to": {"id": k2},
    }
    assert _outcomes(ok(_batch(world, [second]))) == [("rejected", "CARDINALITY_VIOLATION")]
    assert _outcomes(ok(_batch(world, [_bn1_set(world, h1, (k1, k2))], onExisting="overwrite"))) == [
        ("rejected", "CARDINALITY_VIOLATION")
    ]
    cs = world.change_set()
    staged = ok(
        _batch(
            world,
            [{**second, "to": {"id": k3}}],
            context={"changeSetId": cs["id"]},
            expectedChangeSetVersion=cs["version"],
        )
    )
    assert _outcomes(staged) == [("rejected", "CARDINALITY_VIOLATION")]
    assert _held(world, h1) == {k1}
    assert _held(world, h1, changeSetId=cs["id"]) == {k1}

    ok(world.relate("Bn1", h2, k1), 201)
    replaced = ok(_batch(world, [_bn1_set(world, h1, (k2,))], onExisting="overwrite"))
    assert _outcomes(replaced) == [("applied", "updated")]
    assert (_held(world, h1), _held(world, h2)) == ({k2}, {k1})


@pytest.mark.journey("J11.12", "J08.1")
@pytest.mark.structures("H", "K", "Bn1")
def test_many_to_one_is_never_required(world):
    """Given the configuration's model. When it is validated with its many-to-one binding required.
    Then it is invalid at that binding: a required many-to-one is not offered."""
    identity = (world.key("Bn1"), world.key("H"), world.key("K"))
    path = "/objectTypeRelations/" + "/".join(identity)

    def diagnostic(model):
        answer = ok(world.api.post("/model-validations", {"model": model}))
        assert answer["valid"] is False
        return answer["diagnostics"][0]

    def binding(model):
        return next(
            b
            for b in model["objectTypeRelations"]
            if (b["relationTypeKey"], b["fromObjectTypeKey"], b["toObjectTypeKey"]) == identity
        )

    required = copy.deepcopy(world.configuration.model)
    binding(required)["required"] = True
    assert diagnostic(required)["path"] == f"{path}/required"
