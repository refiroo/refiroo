"""J07 — Withdraw a publication and start reviewed changes from history (USER_JOURNEYS.md)."""

import pytest
from scenario import W1, ok, refused


def _publish_from(world, publication, active=None, edit=None):
    cs = world.change_set(source="publication", derivedFromPublicationId=publication["id"])
    if edit:
        structure, record, name = edit
        staged = world.record(structure, record["id"], changeSetId=cs["id"])
        body = {
            "name": name,
            "expectedVersion": staged["version"],
            "changeSetId": cs["id"],
            "expectedChangeSetVersion": world.current(cs)["version"],
        }
        ok(world.api.patch(f"/objects/{world.key(structure)}/{record['id']}", body))
    body = {
        "expectedChangeSetVersion": world.current(cs)["version"],
        "expectedActivePublicationId": active,
    }
    return ok(world.api.post(f"/change-sets/{cs['id']}/publication", body))


@pytest.mark.journey("J07")
@pytest.mark.structures("R")
def test_withdraw_and_start_again_from_an_earlier_publication(world):
    """Given P1 and P2 (current), then live corrections. When the publications are listed, P1 read, P2
    withdrawn and a change set from P1 edited and published with no current publication. Then the
    list is newest first; P2 is withdrawn with its time and nothing is current, live unchanged; the
    new publication derives from P1 and newer live records are kept. Withdrawing one that is not
    current, an unknown one, or one in a retired workspace is refused."""
    first, reviewed = world.made("R", "In both"), world.made("R", "To review")
    p1 = world.publish(world.change_set())
    world.made("R", "In P2")
    p2 = world.publish(world.change_set())
    corrected = ok(world.update("R", first["id"], first["version"], name="Corrected live"))
    newer = world.made("R", "Newer live")

    listed = ok(world.api.get(f"/workspaces/{W1}/publications"))["items"]
    assert [p["id"] for p in listed][:2] == [p2["id"], p1["id"]]
    assert ok(world.api.get(f"/publications/{p1['id']}"))["publishedAt"]

    assert world.api.post(f"/publications/{p2['id']}/withdrawal").status_code == 204
    withdrawn = ok(world.api.get(f"/publications/{p2['id']}"))
    assert withdrawn["status"] == "withdrawn" and withdrawn["withdrawnAt"]
    statuses = {p["status"] for p in ok(world.api.get(f"/workspaces/{W1}/publications"))["items"]}
    assert "active" not in statuses
    assert world.record("R", first["id"])["version"] == corrected["version"]

    restarted = _publish_from(world, p1, edit=("R", reviewed, "Reviewed from P1"))
    assert world.record("R", reviewed["id"])["name"] == "Reviewed from P1"
    assert restarted["derivedFromPublicationId"] == p1["id"]
    assert world.record("R", newer["id"])["name"] == "Newer live"

    refused(
        world.api.post(f"/publications/{p1['id']}/withdrawal"),
        409,
        "WORKSPACE_ACTIVE_PUBLICATION_CONFLICT",
    )
    refused(
        world.api.post("/publications/00000000-0000-4000-8000-000000000000/withdrawal"),
        404,
        "PUBLICATION_NOT_FOUND",
    )
    ok(world.api.post("/workspaces", {"key": "short-lived", "label": "Short lived"}), 201)
    world.made("R", "Short lived record", workspace="short-lived")
    closing = world.publish(world.change_set(workspace="short-lived"), workspace="short-lived")
    workspace = ok(world.api.get("/workspaces/short-lived"))
    ok(
        world.api.patch(
            "/workspaces/short-lived",
            {"expectedVersion": workspace["version"], "status": "retired"},
        )
    )
    refused(world.api.post(f"/publications/{closing['id']}/withdrawal"), 409, "WORKSPACE_RETIRED")


@pytest.mark.journey("J07.1")
@pytest.mark.structures("R", "R.u", "H", "K", "Bnn", "Vnn", "G", "D", "Bown", "Mown")
def test_a_publication_reads_the_same_through_every_route(world):
    """Given P1, then live writes and a model activation. When P1 is read through the per-type list,
    the record, one value, the relationships, the edge list, the cross-type lookup, the query, the
    coverage, the matrix and the model. Then each answers what P1 held, and the model read names P1's
    release."""
    r = world.made("R", "Held ledger", values={"R.u": "HELD"})
    h, k = world.made("H", "Held branch"), world.made("K", "Held token")
    ok(world.relate("Bnn", h["id"], k["id"], {"Bnn.weight": 1}), 201)
    g = world.made("G", "Held column")
    world.made(
        "D",
        "Held cell",
        parent=world.dependant_parent(g["id"]),
        values={"D.active": True},
        relations=[world.owner("Bown", r["id"])],
    )
    release = ok(world.api.get("/model-runtime-state"))["activeReleaseId"]
    p1 = world.publish(world.change_set())

    ok(world.update("R", r["id"], r["version"], name="Renamed live", values={"R.u": "LIVE"}))
    ok(world.relate("Bnn", h["id"], world.ids["k01"], {"Bnn.weight": 1}), 201)
    model, _key = world.candidate("compatible")
    ok(world.activate(world.install(model)["id"]))

    at = {"publicationId": p1["id"]}
    r_type, u = world.key("R"), world.key("R.u")
    assert [
        i["name"] for i in ok(world.api.get(f"/objects/{r_type}", search="Held", **at))["items"]
    ] == ["Held ledger"]
    assert world.record("R", r["id"], **at)["name"] == "Held ledger"
    assert ok(world.api.get(f"/objects/{r_type}/{r['id']}/attributes/{u}", **at))["value"] == "HELD"
    related = ok(
        world.api.get("/relations", objectId=h["id"], relationTypeKey=world.key("Bnn"), **at)
    )
    assert [i["object"]["id"] for i in related["items"]] == [k["id"]]
    edges = ok(
        world.api.get(
            f"/workspaces/{W1}/relations",
            relationTypeKey=world.key("Bnn"),
            direction="outgoing",
            search="Held branch",
            **at,
        )
    )["items"]
    assert [e["target"]["id"] for e in edges] == [k["id"]]
    lookup = ok(world.api.get("/objects", search="Held ledger", **at))["items"]
    assert [i["id"] for i in lookup] == [r["id"]]
    query = {
        "objectTypeKey": r_type,
        "context": at,
        "where": [{"field": u, "op": "eq", "value": "HELD"}],
    }
    found = ok(world.api.post(f"/workspaces/{W1}/queries/objects", query))["items"]
    assert [i["id"] for i in found] == [r["id"]]
    application, config = next(
        (a["key"], v["config"])
        for a in world.configuration.model["applications"]
        for v in a["views"]
        if v["key"] == world.key("Vnn")
    )
    coverage = ok(
        world.api.get(
            f"/workspaces/{W1}/mapping-coverage",
            applicationKey=application,
            viewKey=world.key("Vnn"),
            search="Held branch",
            **{
                k: config[k]
                for k in ("relationTypeKey", "fromObjectTypeKey", "toObjectTypeKey", "direction")
            },
            **at,
        )
    )
    assert {t["object"]["id"] for t in coverage["items"][0]["targets"]} == {k["id"]}
    matrix = ok(
        world.api.get(
            f"/workspaces/{W1}/relation-matrix",
            applicationKey=world.key("A3"),
            viewKey=world.key("Mown"),
            columnIds=[g["id"]],
            search="Held",
            **at,
        )
    )
    assert matrix["items"][0]["cells"][0]["state"] == "one"
    model_read = world.api.get("/model", **at)
    assert model_read.status_code == 200 and model_read.headers["X-Model-Release-Id"] == release


@pytest.mark.journey("J07.2")
@pytest.mark.structures("R")
def test_publish_from_a_retained_publication_after_withdrawal(world):
    """Given the current publication withdrawn and P1 retained. When a change set from P1 is
    published with no current publication. Then the new publication is current, and P1 and the
    withdrawn one remain readable."""
    world.made("R", "Retained")
    p1 = world.publish(world.change_set())
    p2 = world.publish(world.change_set())
    assert world.api.post(f"/publications/{p2['id']}/withdrawal").status_code == 204

    current = _publish_from(world, p1)
    assert current["status"] == "active"
    assert ok(world.api.get(f"/publications/{p1['id']}"))["id"] == p1["id"]
    assert ok(world.api.get(f"/publications/{p2['id']}"))["status"] == "withdrawn"
