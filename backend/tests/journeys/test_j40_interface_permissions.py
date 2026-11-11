"""J40.12 — the interface follows permissions: the reads it needs (USER_JOURNEYS.md § Security,
0.12 Z5).

The browser asks which workspaces the caller may use for a group (D327), which groups the caller
holds anywhere (D328) and which open change sets the caller created (D325), then offers only what
the engine would allow. A Contributor's proposal is walked as the interface walks it. Every case
runs on two configurations through the public API.
"""

import pytest
from harness_identity import TestClient
from scenario import W1, W2, ok, refused
from test_j39_sign_in import _person, _sign_in
from test_j40_authorization import _as, _client, _forbidden, _grant, _publication_body


def _keys(page: dict) -> set[str]:
    return {item["key"] for item in page["items"]}


def _held(world) -> dict[str, dict]:
    return {item["key"]: item for item in ok(world.api.get("/me/action-groups"))["items"]}


@pytest.mark.journey("J40.12")
def test_workspaces_holding_a_group(world):
    """Given a caller who is Reader in A and Integration administrator in B, and a Security
    administrator holding only that role. When the workspaces holding Browse are listed, then the
    first sees A only and the administrator none; holding Integration administration gives B; an
    instance Reader sees every workspace; an unknown group is `422 ACTION_GROUP_UNKNOWN`."""
    _, caller = _client(
        world,
        "Reader and integrator",
        ("reader", {"workspaceKey": W1}),
        ("integration-admin", {"workspaceKey": W2}),
    )
    _, security = _client(world, "Security only", ("security-admin", {"instance": True}))
    _, everywhere = _client(world, "Reads everything", ("reader", {"instance": True}))

    assert _keys(ok(caller.api.get("/workspaces", holding="browse"))) == {W1}
    assert _keys(ok(caller.api.get("/workspaces", holding="integration-admin"))) == {W2}
    assert _keys(ok(caller.api.get("/workspaces"))) == {W1, W2}
    assert _keys(ok(security.api.get("/workspaces", holding="browse"))) == set()
    assert {W1, W2} <= _keys(ok(everywhere.api.get("/workspaces", holding="browse")))
    error = refused(caller.api.get("/workspaces", holding="nonsense"), 422, "ACTION_GROUP_UNKNOWN")
    assert error["details"]["actionGroups"] == ["nonsense"]


@pytest.mark.journey("J40.12")
def test_the_groups_held_anywhere(world):
    """Given the same caller. When the groups it holds anywhere are read, then they are Browse in
    A and Integration administrator's groups (Integration administration, Feed and Use AI
    proposals: D230, API § predefined roles) in B and nothing else; the administrator's are
    Security administration at the instance; after the grant in B is removed, B is gone on the
    next request."""
    _, caller = _client(world, "Reader and integrator", ("reader", {"workspaceKey": W1}))
    client_id = ok(caller.api.get("/me"))["id"]
    in_b = _grant(world, "client", client_id, "integration-admin", workspaceKey=W2)
    _, security = _client(world, "Security only", ("security-admin", {"instance": True}))

    held = _held(caller)
    assert set(held) == {"browse", "integration-admin", "feed", "ai-proposals"}
    assert held["browse"]["name"] == "Browse" and held["browse"]["instance"] is False
    assert [where["key"] for where in held["browse"]["workspaces"]] == [W1]
    assert all(where["label"] for where in held["browse"]["workspaces"])
    assert [where["key"] for where in held["integration-admin"]["workspaces"]] == [W2]
    assert [where["key"] for where in held["feed"]["workspaces"]] == [W2]
    assert [where["key"] for where in held["ai-proposals"]["workspaces"]] == [W2]
    assert _held(security) == {
        "security-admin": {
            "key": "security-admin",
            "name": "Security administration",
            "instance": True,
            "workspaces": [],
        }
    }

    assert world.api.delete(f"/grants/{in_b['id']}").status_code == 204
    assert set(_held(caller)) == {"browse"}


@pytest.mark.journey("J40.12")
def test_their_change_sets(world):
    """Given two Contributors in A each creating a change set. When A's change sets are listed by
    each one's ID as creator, then each sees only their own; after one is published it is no longer
    listed; another workspace's change sets are never listed."""
    first, first_world = _client(world, "First contributor", ("contributor", {"workspaceKey": W1}))
    second, second_world = _client(
        world,
        "Second contributor",
        ("contributor", {"workspaceKey": W1}),
        ("contributor", {"workspaceKey": W2}),
    )
    mine = first_world.change_set()
    theirs = second_world.change_set()
    elsewhere = ok(
        second_world.api.post(f"/workspaces/{W2}/change-sets", {"source": "currentLive"}), 201
    )

    def created_by(principal: dict, workspace: str = W1) -> list[str]:
        page = ok(world.api.get(f"/workspaces/{workspace}/change-sets", createdBy=principal["id"]))
        return [item["id"] for item in page["items"]]

    assert created_by(first) == [mine["id"]]
    assert created_by(second) == [theirs["id"]]
    assert created_by(second, W2) == [elsewhere["id"]]
    assert {item["id"] for item in ok(world.api.get(f"/workspaces/{W1}/change-sets"))["items"]} >= {
        mine["id"],
        theirs["id"],
    }

    ok(world.api.post(f"/change-sets/{mine['id']}/publication", _publication_body(world, mine)))
    assert created_by(first) == []


@pytest.mark.journey("J40.12")
def test_a_contributor_proposes_a_change(world):
    """Given a person who is Contributor in A with no change set and a live record. When they find
    none of their own, create one, change the record in it and try to publish, then the change
    passes, the publish is `403 FORBIDDEN` naming Publish, their change set is listed as theirs and
    the live record is unchanged."""
    record = world.made("R", "As it was")
    person = _person(world, "jonah-z5")
    _grant(world, "user", person["id"], "contributor", workspaceKey=W1)
    contributor = _as(
        world, _sign_in(TestClient(world.api.client.app, authenticated=False), "jonah-z5")
    )

    def theirs() -> list[dict]:
        return ok(contributor.api.get(f"/workspaces/{W1}/change-sets", createdBy=person["id"]))[
            "items"
        ]

    assert theirs() == []
    change_set = ok(
        contributor.api.post(
            f"/workspaces/{W1}/change-sets",
            {"source": "currentLive", "name": "Changes by Jonah-Z5"},
        ),
        201,
    )
    assert [item["id"] for item in theirs()] == [change_set["id"]]
    assert theirs()[0]["createdBy"]["id"] == person["id"]
    ok(contributor.create("R", "Proposed", change_set=change_set), 201)
    _forbidden(contributor.create("R", "Not live"), "records.write", ["edit-live"], W1)
    _forbidden(
        contributor.api.post(
            f"/change-sets/{change_set['id']}/publication",
            _publication_body(world, change_set),
        ),
        "change-sets.publish",
        ["publish"],
        W1,
    )
    assert ok(world.read("R", record["id"]))["name"] == "As it was"
