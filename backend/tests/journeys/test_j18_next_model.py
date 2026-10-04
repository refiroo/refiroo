"""J18 — Prepare under the next model version while live keeps the current one (USER_JOURNEYS.md)."""

from uuid import uuid4

import pytest
from scenario import W1, W2, ok, refused
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool


def _pin(world, cs, release_id, version=None):
    version = version if version is not None else world.current(cs)["version"]
    return world.api.patch(
        f"/change-sets/{cs['id']}/model-release",
        {"modelReleaseId": release_id, "expectedChangeSetVersion": version},
    )


def _publish(world, cs):
    body = {
        "expectedChangeSetVersion": world.current(cs)["version"],
        "expectedActivePublicationId": None,
    }
    items = ok(world.api.get(f"/workspaces/{W1}/publications", pageSize=1))["items"]
    if items and items[0]["status"] == "active":
        body["expectedActivePublicationId"] = items[0]["id"]
    return world.api.post(f"/change-sets/{cs['id']}/publication", body)


def _create(world, structure, name, values, cs=None):
    body = {
        "applicationKey": world.app(structure),
        "objectTypeKey": world.key(structure),
        "name": name,
        "attributes": [
            {"attributeTypeKey": k, "value": v}
            for k, v in {**world.required_values(structure), **values}.items()
        ],
    }
    if cs is None:
        body["workspaceKey"] = W1
    else:
        body["changeSetId"] = cs["id"]
        body["expectedChangeSetVersion"] = world.current(cs)["version"]
    return world.api.post("/objects", body)


@pytest.mark.journey("J18")
@pytest.mark.structures("R")
def test_pin_a_change_set_to_the_candidate_activate_and_publish(world):
    """Given M1 active, candidate M2 installed with an added attribute, and change set C1 on M1. When
    C2 is created on M2, its model read, a record written in it with the new attribute and the same
    write made live; M2 activated and C2 published. Then C2 reads M2 and the write succeeds there,
    live refuses it, C1 and live keep M1 until activation, and C2 then publishes. When C1 is moved to
    M2. Then its version advances and it publishes."""
    m1 = ok(world.api.get("/model-runtime-state"))["activeReleaseId"]
    model, added = world.candidate("compatible")
    m2 = world.install(model)["id"]
    c1 = world.change_set(name="On M1")
    c2 = world.change_set(name="On M2", modelReleaseId=m2)
    assert c2["modelReleaseId"] == m2 and c1["modelReleaseId"] == m1

    pinned = world.api.get("/model", changeSetId=c2["id"])
    r_type = next(t for t in ok(pinned)["objectTypes"] if t["key"] == world.key("R"))
    assert added in {b["attributeTypeKey"] for b in r_type["attributes"]}
    assert pinned.headers["X-Model-Release-Id"] == m2
    ok(_create(world, "R", "Written on M2", {added: "new"}, cs=c2), 201)
    refused(_create(world, "R", "Written live", {added: "new"}), 422, "UNKNOWN_ATTRIBUTES")
    assert world.api.get("/model").headers["X-Model-Release-Id"] == m1

    ok(world.activate(m2))
    ok(_publish(world, c2))
    moved = ok(_pin(world, c1, m2))
    assert moved["modelReleaseId"] == m2 and moved["version"] == c1["version"] + 1
    ok(_publish(world, c1))


@pytest.mark.journey("J18.1")
@pytest.mark.structures("R")
def test_an_incompatible_candidate_is_refused_naming_the_records(world):
    """Given candidate M3 that live content does not fit. When a change set from current live is
    created on M3, and C1 moved to M3. Then both are refused naming the records, with their count;
    no change set is created and C1 is unchanged."""
    world.made("R", "Lacks the field")
    model, _key = world.candidate("incompatible")
    m3 = world.install(model)["id"]
    c1 = world.change_set()
    before = ok(world.api.get(f"/workspaces/{W1}/change-sets", pageSize=100))["items"]

    for response in (
        world.api.post(
            f"/workspaces/{W1}/change-sets", {"source": "currentLive", "modelReleaseId": m3}
        ),
        _pin(world, c1, m3),
    ):
        details = refused(response, 409, "CHANGE_SET_CONTENT_INCOMPATIBLE")["details"]
        assert 0 < len(details["diagnostics"]) <= 20
        assert details["diagnosticCount"] >= len(details["diagnostics"])
        assert "diagnosticsTruncated" in details
    assert ok(world.api.get(f"/workspaces/{W1}/change-sets", pageSize=100))["items"] == before
    assert world.current(c1) == ok(world.api.get(f"/change-sets/{c1['id']}"))
    assert world.current(c1)["version"] == c1["version"]


@pytest.mark.journey("J18.2")
@pytest.mark.structures("R")
def test_publishing_on_a_release_no_longer_active(world):
    """Given C1 on M1, and M2 activated. When C1 is published. Then it is refused with an explanation;
    nothing is published; C1 can still be read, edited on M1 and discarded, leaving live unchanged."""
    record = world.made("R", "Staged on M1")
    c1 = world.change_set()
    model, _key = world.candidate("compatible")
    ok(world.activate(world.install(model)["id"]))
    publications = ok(world.api.get(f"/workspaces/{W1}/publications"))["items"]

    error = refused(_publish(world, c1), 409, "CHANGE_SET_MODEL_RELEASE_CONFLICT")
    assert error["message"]
    assert ok(world.api.get(f"/workspaces/{W1}/publications"))["items"] == publications
    staged = world.record("R", record["id"], changeSetId=c1["id"])
    ok(
        world.api.patch(
            f"/objects/{world.key('R')}/{record['id']}",
            {
                "name": "Edited on M1",
                "expectedVersion": staged["version"],
                "changeSetId": c1["id"],
                "expectedChangeSetVersion": world.current(c1)["version"],
            },
        )
    )
    gone = world.api.delete(
        f"/change-sets/{c1['id']}", expectedVersion=world.current(c1)["version"]
    )
    assert gone.status_code == 204, gone.text
    assert world.record("R", record["id"])["name"] == "Staged on M1"


@pytest.mark.journey("J18.3")
@pytest.mark.structures("R")
def test_an_unavailable_corrupt_or_unsupported_release_is_refused(world):
    """When a change set is created, and C1 moved, naming an unknown release. Then each is refused and
    live, the runtime selection, other change sets and the other workspace are unchanged. A corrupt
    and an unsupported stored release are refused the same way; such releases arrive only from
    outside the API (an older engine, a damaged store), so the test writes them into the store."""
    c1 = world.change_set()
    state = ok(world.api.get("/model-runtime-state"))
    others = ok(world.api.get(f"/workspaces/{W2}/change-sets"))["items"]
    unknown = str(uuid4())
    refused(
        world.api.post(
            f"/workspaces/{W1}/change-sets", {"source": "currentLive", "modelReleaseId": unknown}
        ),
        409,
        "PINNED_MODEL_UNAVAILABLE",
    )
    refused(_pin(world, c1, unknown), 409, "PINNED_MODEL_UNAVAILABLE")

    model, _key = world.candidate("compatible")
    corrupt = world.install(model, "Corrupt")["id"]
    model["release"]["version"] += "-two"
    unsupported = world.install(model, "Unsupported")["id"]
    engine = create_engine(world.database, poolclass=NullPool)
    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE model_releases SET model_json = (model_json::jsonb - 'objectTypes')::json "
                "WHERE public_id = :id"
            ),
            {"id": corrupt},
        )
        connection.execute(
            text(
                "UPDATE model_releases SET schema_version = '0.1', model_json = "
                "jsonb_set(model_json::jsonb, '{schemaVersion}', '\"0.1\"')::json "
                "WHERE public_id = :id"
            ),
            {"id": unsupported},
        )
    engine.dispose()
    refused(_pin(world, c1, corrupt), 409, "PINNED_MODEL_INVALID")
    refused(_pin(world, c1, unsupported), 409, "UNSUPPORTED_PINNED_MODEL_SCHEMA")

    assert ok(world.api.get("/model-runtime-state")) == state
    assert world.current(c1)["version"] == c1["version"]
    assert ok(world.api.get(f"/workspaces/{W2}/change-sets"))["items"] == others


@pytest.mark.journey("J18.4")
@pytest.mark.structures("R")
def test_a_pin_changed_by_someone_else_is_refused(world):
    """Given clients A and B who read C1 at version v. When A moves C1 to M2 with v, then B moves or
    writes to C1 with v. Then B is refused and C1 stays on M2 at v+1."""
    model, _key = world.candidate("compatible")
    m2 = world.install(model)["id"]
    c1 = world.change_set()
    v = c1["version"]
    ok(_pin(world, c1, m2, v))
    refused(_pin(world, c1, m2, v), 409, "CHANGE_SET_VERSION_CONFLICT")
    write = world.create("R", "Late write", change_set={"id": c1["id"], "version": v})
    refused(write, 409, "CHANGE_SET_VERSION_CONFLICT")
    now = world.current(c1)
    assert (now["modelReleaseId"], now["version"]) == (m2, v + 1)
