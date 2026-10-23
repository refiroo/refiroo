"""J40 — manage who can do what, the reads the Security pages need (USER_JOURNEYS.md § Security,
0.12 SP1).

A Security administrator (the harness) lists people with the roles they hold, reads a person's
grants including those of their groups, finds groups and clients by name, and is refused a
workspace grant of a role that can only be held at the instance (D298–D302). Every case runs on two
configurations through the public API.
"""

import pytest
from scenario import W1, W2, ok, refused
from test_j40_authorization import _grant


def _user(world, username: str) -> dict:
    return ok(world.api.post("/users", {"username": username, "name": username.title()}), 201)


def _roles(person: dict) -> dict[str, dict]:
    return {role["key"]: role for role in person["roles"]}


@pytest.mark.journey("J40")
def test_the_people_list_names_their_roles(world):
    """Given a person granted Data steward in A directly and Reader in B through a group, and
    another with an instance role. When the people list (and each person) is read, then the first
    lists Data steward in A and Reader in B, the second the role at the instance, and a person with
    none an empty list; `q` and `active` still narrow the list."""
    ana = _user(world, "ana-sp1")
    tomas = _user(world, "tomas-sp1")
    lena = _user(world, "lena-sp1")
    _grant(world, "user", ana["id"], "steward", workspaceKey=W1)
    group = ok(world.api.post("/groups", {"name": "Readers of B"}), 201)
    ok(world.api.post(f"/groups/{group['id']}/members", {"userId": ana["id"]}), 201)
    _grant(world, "group", group["id"], "reader", workspaceKey=W2)
    _grant(world, "user", tomas["id"], "model-admin", instance=True)

    listed = {item["id"]: item for item in ok(world.api.get("/users", q="-sp1"))["items"]}
    assert set(listed) == {ana["id"], tomas["id"], lena["id"]}
    roles = _roles(listed[ana["id"]])
    assert set(roles) == {"steward", "reader"}
    assert roles["steward"]["name"] == "Data steward" and not roles["steward"]["instance"]
    assert [where["key"] for where in roles["steward"]["workspaces"]] == [W1]
    assert [where["key"] for where in roles["reader"]["workspaces"]] == [W2]
    assert all(where["label"] for where in roles["reader"]["workspaces"])
    assert _roles(listed[tomas["id"]])["model-admin"] == {
        "key": "model-admin",
        "name": "Model administrator",
        "instance": True,
        "workspaces": [],
    }
    assert listed[lena["id"]]["roles"] == []
    assert _roles(ok(world.api.get(f"/users/{ana['id']}"))) == roles

    ok(
        world.api.patch(
            f"/users/{lena['id']}", {"expectedVersion": lena["version"], "active": False}
        )
    )
    active = ok(world.api.get("/users", q="-sp1", active="true"))["items"]
    assert {item["id"] for item in active} == {ana["id"], tomas["id"]}


@pytest.mark.journey("J40.4")
def test_a_persons_grants_include_their_groups(world):
    """Given a person with a direct grant and a group's grant. When their grants are read, then both
    are listed, the group's naming the group; when they leave the group, only the direct one; an
    unknown person answers `404 USER_NOT_FOUND`."""
    person = _user(world, "grace-sp1")
    direct = _grant(world, "user", person["id"], "contributor", workspaceKey=W1)
    group = ok(world.api.post("/groups", {"name": "Field team"}), 201)
    ok(world.api.post(f"/groups/{group['id']}/members", {"userId": person["id"]}), 201)
    through = _grant(world, "group", group["id"], "reader", workspaceKey=W2)

    grants = ok(world.api.get(f"/users/{person['id']}/grants"))["items"]
    assert {item["id"] for item in grants} == {direct["id"], through["id"]}
    [by_group] = [item for item in grants if item["id"] == through["id"]]
    assert by_group["principal"] == {"kind": "group", "id": group["id"], "name": "Field team"}

    assert world.api.delete(f"/groups/{group['id']}/members/{person['id']}").status_code == 204
    grants = ok(world.api.get(f"/users/{person['id']}/grants"))["items"]
    assert [item["id"] for item in grants] == [direct["id"]]
    refused(world.api.get("/users/no-such-person/grants"), 404, "USER_NOT_FOUND")


@pytest.mark.journey("J40")
def test_groups_and_clients_are_found_by_name(world):
    """Given two groups and two clients. When groups and clients are searched by name, then the
    matching one answers; groups filtered by a member answer that person's groups."""
    person = _user(world, "mei-sp1")
    herbarium = ok(world.api.post("/groups", {"name": "Herbarium curators"}), 201)
    ok(world.api.post("/groups", {"name": "Seed bank volunteers"}), 201)
    ok(world.api.post(f"/groups/{herbarium['id']}/members", {"userId": person["id"]}), 201)
    sync = ok(world.api.post("/clients", {"name": "Catalogue sync"}), 201)
    ok(world.api.post("/clients", {"name": "Nightly export"}), 201)

    found = ok(world.api.get("/groups", q="curator"))["items"]
    assert [item["id"] for item in found] == [herbarium["id"]]
    found = ok(world.api.get("/clients", q="catalogue"))["items"]
    assert [item["id"] for item in found] == [sync["id"]]
    found = ok(world.api.get("/groups", memberId=person["id"]))["items"]
    assert [item["id"] for item in found] == [herbarium["id"]]


@pytest.mark.journey("J40")
def test_a_role_held_only_at_the_instance(world):
    """Granting Security administrator in a workspace answers `422 GRANT_SCOPE_INVALID`; at the
    instance it passes; Model administrator in a workspace passes (Model release is held there)."""
    person = _user(world, "rosa-sp1")
    body = {"principal": {"kind": "user", "id": person["id"]}, "role": "security-admin"}
    error = refused(
        world.api.post("/grants", {**body, "scope": {"workspaceKey": W1}}),
        422,
        "GRANT_SCOPE_INVALID",
    )
    assert "Security administrator" in error["message"]
    ok(world.api.post("/grants", {**body, "scope": {"instance": True}}), 201)
    _grant(world, "user", person["id"], "model-admin", workspaceKey=W1)
