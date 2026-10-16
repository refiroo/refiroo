"""J36.7 — A read spanning workspaces with different models (USER_JOURNEYS.md, Base 0.11 M4).

Each test runs on one configuration ``X`` in the default workspace and puts a workspace on the other
generated configuration's model ``Y`` beside it: generated A beside B, and B beside A (D41–D44).
"""

import csv
import io
from uuid import uuid4

import pytest
from scenario import W1, ok, refused
from test_j27_import import _export, _imported, _outcomes, _request
from test_j36_workspace_models import BOTH, _beside, _model


def _lookup(world, **params):
    """Every item of a cross-type lookup, paged two at a time."""
    items, cursor = [], None
    while True:
        page = ok(world.api.get("/objects", pageSize=2, cursor=cursor, **params))
        items += page["items"]
        cursor = page.get("nextCursor")
        if not cursor:
            return items


@pytest.mark.journey("J36.7")
@pytest.mark.structures(*BOTH)
def test_a_lookup_over_two_workspaces_on_two_models(world):
    """Given the default workspace on X and a workspace on Y, each with records. When the lookup
    names both workspaces. Then it pages every record of both once, ordered by name across them,
    each naming its workspace and that workspace's release, its attributes as its own model names
    them; an ID filter finds Y's record without its workspace; sorting by type answers."""
    other, y, key = _beside(world)
    x = _model(world)["releaseId"]
    token = uuid4().hex[:8]
    mine = [world.made("R", f"{token} {name}", workspace=W1, fill=True) for name in ("b", "d")]
    theirs = [other.made("R", f"{token} {name}", workspace=key, fill=True) for name in ("a", "c")]

    items = _lookup(world, workspaceKey=[W1, key], search=token)
    assert [item["name"] for item in items] == [f"{token} {n}" for n in ("a", "b", "c", "d")]
    release = {W1: x, key: y["id"]}
    for item in items:
        assert item["modelReleaseId"] == release[item["workspaceKey"]]
    by_id = {item["id"]: item for item in items}
    assert {by_id[r["id"]]["workspaceKey"] for r in mine} == {W1}
    assert {by_id[r["id"]]["workspaceKey"] for r in theirs} == {key}
    assert {by_id[r["id"]]["objectTypeKey"] for r in theirs} == {other.key("R")}
    attribute_keys = {a["attributeTypeKey"] for a in by_id[theirs[0]["id"]]["attributes"]}
    assert other.key("R.q") in attribute_keys and world.key("R.q") not in attribute_keys

    (found,) = _lookup(world, workspaceKey=[W1, key], filter__id__eq=theirs[1]["id"])
    assert (found["workspaceKey"], found["modelReleaseId"]) == (key, y["id"])
    by_type = _lookup(world, workspaceKey=[key, W1], search=token, sort="objectType")
    assert sorted(item["id"] for item in by_type) == sorted(by_id)


@pytest.mark.journey("J36.7")
@pytest.mark.structures(*BOTH)
def test_a_spanning_lookup_naming_an_element_one_model_lacks(world):
    """Given the default workspace on X and a workspace on Y. When the spanning lookup names a type
    only X has. Then it is refused naming Y's workspace; with X's workspace alone it answers; a type
    neither has is unknown; so is an application only X has; a change set with two workspaces
    is refused."""
    _other, _y, key = _beside(world)
    error = refused(
        world.api.get("/objects", workspaceKey=[W1, key], objectTypeKey=world.key("R")),
        422,
        "MODEL_ELEMENT_NOT_IN_EVERY_MODEL",
    )
    assert error["details"]["element"] == {"kind": "objectType", "key": world.key("R")}
    assert error["details"]["workspaces"] == [key]
    ok(world.api.get("/objects", workspaceKey=W1, objectTypeKey=world.key("R")))
    refused(
        world.api.get("/objects", workspaceKey=[W1, key], objectTypeKey=f"none-{uuid4().hex[:6]}"),
        404,
        "UNKNOWN_OBJECT_TYPE",
    )
    error = refused(
        world.api.get("/objects", workspaceKey=[W1, key], applicationKey=world.app("R")),
        422,
        "MODEL_ELEMENT_NOT_IN_EVERY_MODEL",
    )
    assert error["details"]["element"] == {"kind": "application", "key": world.app("R")}
    change_set = ok(
        world.api.post(f"/workspaces/{W1}/change-sets", {"name": f"cs-{uuid4().hex[:6]}"}), 201
    )
    refused(
        world.api.get("/objects", workspaceKey=[W1, key], changeSetId=change_set["id"]),
        422,
        "WORKSPACE_CONTEXT_MISMATCH",
    )


@pytest.mark.journey("J36.7")
@pytest.mark.structures(*BOTH)
def test_a_lookup_without_a_workspace_reads_the_default_one(world):
    """Given a workspace on Y beside the default workspace on X, each with a record. When the lookup
    names no workspace. Then only the default workspace's record is listed, naming X's release."""
    other, _y, key = _beside(world)
    token = uuid4().hex[:8]
    mine = world.made("R", f"{token} mine", workspace=W1, fill=True)
    other.made("R", f"{token} theirs", workspace=key, fill=True)
    (item,) = _lookup(world, search=token)
    assert (item["id"], item["workspaceKey"]) == (mine["id"], W1)
    assert item["modelReleaseId"] == _model(world)["releaseId"]


def _replaced(content, old, new):
    return content.decode().replace(old, new).encode()


@pytest.mark.journey("J36.7", "J27.14")
@pytest.mark.structures(*BOTH)
def test_counterparts_across_models_are_refused_per_item(world):
    """Given a K record in a workspace on Y. When its ID is sent to X's default workspace with
    counterparts, as a batch upsert of X's K and as a row of X's K export. Then each such item or
    row is refused naming Y's workspace and both models, the import's notice says so, nothing is
    created in X's workspace under that ID's counterpart; the items without such an ID load."""
    other, y, key = _beside(world)
    x_model = _model(world)["releaseKey"]
    theirs = other.made("K", f"Theirs {uuid4().hex[:6]}", workspace=key, fill=True)
    expected = {"workspaceKey": key, "modelKey": y["key"], "workspaceModelKey": x_model}
    values = [{"attributeTypeKey": k, "value": v} for k, v in world.required_values("K").items()]

    batch = world.api.post(
        "/batches",
        {
            "workspaceKey": W1,
            "policy": "independent",
            "run": "inline",
            "otherWorkspaceIds": "counterparts",
            "items": [
                {
                    "op": "upsert",
                    "ref": "theirs",
                    "applicationKey": world.app("K"),
                    "objectTypeKey": world.key("K"),
                    "key": {"id": theirs["id"]},
                    "name": "Not loaded",
                    "attributes": values,
                },
                {
                    "op": "create",
                    "ref": "mine",
                    "applicationKey": world.app("K"),
                    "objectTypeKey": world.key("K"),
                    "name": f"Loaded {uuid4().hex[:6]}",
                    "attributes": values,
                },
            ],
        },
    )
    outcomes = {item["ref"]: item for item in ok(batch)["items"]}
    assert outcomes["theirs"]["status"] == "rejected", outcomes
    assert outcomes["theirs"]["error"]["code"] == "COUNTERPARTS_ACROSS_MODELS"
    details = outcomes["theirs"]["error"]["details"]
    assert {name: details[name] for name in expected} == expected
    assert outcomes["mine"]["status"] == "applied", outcomes

    mine = world.made("K", f"Mine {uuid4().hex[:6]}", workspace=W1, fill=True)
    content = _replaced(_export(world, W1, ("K",), "csv", relations="none"), mine["id"], theirs["id"])
    assert theirs["id"] in content.decode()
    job = _imported(world, "x.csv", content, _request(W1, otherWorkspaceIds="counterparts"))
    notices = {notice["code"]: notice for notice in job["notices"]}
    assert notices["COUNTERPARTS_ACROSS_MODELS"]["details"]["workspaceKey"] == key
    outcomes = _outcomes(world, job)
    rejected = [item for item in outcomes if item.get("error")]
    assert {item["error"]["code"] for item in rejected} == {"COUNTERPARTS_ACROSS_MODELS"}, rejected
    assert len(rejected) == 1
    assert len(outcomes) == len(list(csv.reader(io.StringIO(content.decode())))) - 1
    assert ok(world.api.get("/objects", workspaceKey=W1, filter__name__eq="Not loaded"))["items"] == []
