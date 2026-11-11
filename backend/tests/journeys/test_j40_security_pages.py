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


def _user(world, name: str) -> dict:
    return ok(world.api.post("/users", {"email": f"{name}@example.org", "name": name.title()}), 201)


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


@pytest.mark.journey("J40.4")
def test_several_people_join_and_leave_a_group_at_once(world):
    """Given a group with one member, three people (one deactivated).
    When a pasted list of e-mail addresses, in other cases, is checked, then each
    line says whom it names and whether they would be added, and nothing changes. When three are
    added by ID, the active two join (each with its security event) and the deactivated one is left
    out; when two are taken out with an unknown ID, both leave and the ID is not found (0.12 SP1b,
    D401, D402)."""
    group = ok(world.api.post("/groups", {"name": "Catalogue stewards"}), 201)
    kept = _user(world, "kept-sp1b")
    ok(world.api.post(f"/groups/{group['id']}/members", {"userId": kept["id"]}), 201)
    ivo = _user(world, "ivo-sp1b")
    body = {"name": "Jun", "email": "jun.sp1b@example.org"}
    jun = ok(world.api.post("/users", body), 201)
    old = _user(world, "old-sp1b")
    ok(world.api.patch(f"/users/{old['id']}", {"expectedVersion": old["version"], "active": False}))
    batch = f"/groups/{group['id']}/members/batch"

    lines = [
        "IVO-SP1B@example.org",
        "Jun.SP1b@example.org",
        "nobody@example.org",
        "kept-sp1b@example.org",
        " ",
    ]
    checked = ok(world.api.post(batch, {"identifiers": lines, "dryRun": True}))
    assert [(item["input"], item["outcome"]) for item in checked["items"]] == [
        ("IVO-SP1B@example.org", "toAdd"),
        ("Jun.SP1b@example.org", "toAdd"),
        ("nobody@example.org", "notFound"),
        ("kept-sp1b@example.org", "alreadyMember"),
    ]
    assert checked["items"][1]["member"]["id"] == jun["id"]
    assert checked["items"][2]["member"] is None
    assert checked["changed"] == 0
    members = f"/groups/{group['id']}/members"
    assert [item["id"] for item in ok(world.api.get(members))["items"]] == [kept["id"]]

    added = ok(world.api.post(batch, {"userIds": [ivo["id"], jun["id"], old["id"]]}))
    assert [item["outcome"] for item in added["items"]] == ["added", "added", "deactivated"]
    assert added["changed"] == 2
    assert {item["id"] for item in ok(world.api.get(members))["items"]} == {
        kept["id"],
        ivo["id"],
        jun["id"],
    }
    events = ok(world.api.get("/security-events", principalId=group["id"]))["items"]
    joined = {event["details"]["userId"] for event in events if event["action"] == "member-added"}
    assert {ivo["id"], jun["id"]} <= joined and old["id"] not in joined

    removal = f"/groups/{group['id']}/members/removal"
    gone = ok(world.api.post(removal, {"userIds": [ivo["id"], jun["id"], "no-such-person"]}))
    assert [item["outcome"] for item in gone["items"]] == ["removed", "removed", "notFound"]
    assert gone["changed"] == 2
    assert [item["id"] for item in ok(world.api.get(members))["items"]] == [kept["id"]]
    refused(world.api.post(removal, {"userIds": []}), 422, "REQUEST_VALIDATION_ERROR")


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
