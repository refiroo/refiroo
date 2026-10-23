"""J40 — manage who can do what (USER_JOURNEYS.md § Security, 0.12 Z1).

A Security administrator (the harness, which holds every role at the instance) creates clients and
people, gives them roles in a workspace or at the instance, directly or through a group, and each
caller can do exactly what its roles allow: a refusal is ``403 FORBIDDEN`` naming the action, the
groups that would allow it and the workspace. A change applies on the next request, in every
process. Every case runs on two configurations through the public API.
"""

import json

import pytest
from harness_identity import TestClient, request_token
from processes import run
from scenario import W1, W2, Api, World, ok, refused
from test_j39_sign_in import _person, _sign_in


def _grant(world, kind: str, principal_id: str, role: str, **scope) -> dict:
    body = {
        "principal": {"kind": kind, "id": principal_id},
        "role": role,
        "scope": scope or {"workspaceKey": W1},
    }
    return ok(world.api.post("/grants", body), 201)


def _as(world, token: str) -> World:
    """The same engine, called with ``token`` instead of the harness's."""
    client = TestClient(
        world.api.client.app, authenticated=False, headers={"Authorization": f"Bearer {token}"}
    )
    return World(world.configuration, Api(client), world.database, world.ids)


def _client(world, name: str, *grants: tuple[str, dict]) -> tuple[dict, World]:
    """A client holding ``grants`` (role, scope), and the world as it sees it."""
    client = ok(world.api.post("/clients", {"name": name}), 201)
    for role, scope in grants:
        _grant(world, "client", client["id"], role, **scope)
    anonymous = TestClient(world.api.client.app, authenticated=False)
    token = ok(request_token(anonymous.post, client["id"], client["secret"]))["access_token"]
    return client, _as(world, token)


def _forbidden(response, action: str, groups: list[str], workspace: str | None) -> None:
    error = refused(response, 403, "FORBIDDEN")
    assert error["details"] == {"action": action, "groups": groups, "workspaceKey": workspace}
    assert error["message"].endswith(" needs " + " or ".join(_NAMES[group] for group in groups))


_NAMES = {
    "browse": "Browse",
    "edit-live": "Edit live",
    "change-sets": "Work in change sets",
    "publish": "Publish",
    "bulk": "Bulk and import",
    "security-admin": "Security administration",
}


def _publication_body(world, change_set: dict) -> dict:
    active = [
        item
        for item in ok(world.api.get(f"/workspaces/{W1}/publications", pageSize=1))["items"]
        if item.get("status") == "active"
    ]
    return {
        "expectedChangeSetVersion": world.current(change_set)["version"],
        "expectedActivePublicationId": active[0]["id"] if active else None,
    }


@pytest.mark.journey("J40.1")
def test_a_reader_reads_and_changes_nothing(world):
    """Given a client granted Reader in workspace A. When it reads the model, records, change sets
    and publications in A, or starts an export, then each answers; when it writes a record live,
    creates a change set, sends a batch or an import, or publishes, then each answers `403
    FORBIDDEN` with the action, the groups and A; in workspace B every read answers `403`."""
    record = world.made("R", "Read by a reader")
    change_set = world.change_set()
    _, reader = _client(world, "Reader", ("reader", {"workspaceKey": W1}))

    ok(reader.api.get("/model", workspaceKey=W1))
    assert ok(reader.read("R", record["id"]))["name"] == "Read by a reader"
    ok(reader.api.get(f"/objects/{world.key('R')}", workspaceKey=W1))
    ok(reader.api.get(f"/workspaces/{W1}/change-sets"))
    ok(reader.api.get(f"/change-sets/{change_set['id']}"))
    ok(reader.api.get(f"/workspaces/{W1}/publications"))
    export = {
        "workspaceKey": W1,
        "scope": {"types": [{"objectTypeKey": world.key("R")}]},
        "format": "jsonl",
    }
    ok(reader.api.post("/exports", export), 202)

    _forbidden(reader.create("R", "Not by a reader"), "records.write", ["edit-live"], W1)
    _forbidden(
        reader.api.post(f"/workspaces/{W1}/change-sets", {"source": "currentLive"}),
        "change-sets.write",
        ["change-sets"],
        W1,
    )
    _forbidden(
        reader.create("R", "Not in a change set", change_set=world.current(change_set)),
        "records.write",
        ["change-sets"],
        W1,
    )
    _forbidden(
        reader.api.post("/batches", {"workspaceKey": W1, "items": []}), "bulk.write", ["bulk"], W1
    )
    imported = reader.api.upload(
        "/imports",
        {"file": ("rows.csv", b"name\nx\n", "text/csv")},
        {"request": json.dumps({"workspaceKey": W1, "policy": "independent"})},
    )
    _forbidden(imported, "bulk.write", ["bulk"], W1)
    _forbidden(
        reader.api.post(
            f"/change-sets/{change_set['id']}/publication", _publication_body(world, change_set)
        ),
        "change-sets.publish",
        ["publish"],
        W1,
    )
    _forbidden(reader.api.get("/model", workspaceKey=W2), "model.read", ["browse"], W2)
    _forbidden(reader.api.get(f"/workspaces/{W2}"), "workspace.read", ["browse"], W2)


@pytest.mark.journey("J40.2")
def test_a_contributor_changes_records_only_in_change_sets(world):
    """Given Contributor in A. When it creates a change set and writes a record in it, then both
    pass; the same write without `changeSetId` answers `403` naming Edit live; publishing the change
    set answers `403` naming Publish."""
    _, contributor = _client(world, "Contributor", ("contributor", {"workspaceKey": W1}))
    change_set = contributor.change_set()
    ok(contributor.create("R", "Proposed", change_set=change_set), 201)
    _forbidden(contributor.create("R", "Not live"), "records.write", ["edit-live"], W1)
    _forbidden(
        contributor.api.post(
            f"/change-sets/{change_set['id']}/publication", _publication_body(world, change_set)
        ),
        "change-sets.publish",
        ["publish"],
        W1,
    )


@pytest.mark.journey("J40.4")
def test_a_grant_to_a_group_applies_to_its_members(world):
    """Given a person signed in, in a group granted Data steward in A. When they write a record
    live, then it passes; when they are removed from the group, then their next request answers
    `403`."""
    person = _person(world, "grace")
    group = ok(world.api.post("/groups", {"name": "Curators"}), 201)
    ok(world.api.post(f"/groups/{group['id']}/members", {"userId": person["id"]}), 201)
    _grant(world, "group", group["id"], "steward", workspaceKey=W1)
    browser = TestClient(world.api.client.app, authenticated=False)
    steward = _as(world, _sign_in(browser, "grace"))
    ok(steward.create("R", "Through the group"), 201)
    assert world.api.delete(f"/groups/{group['id']}/members/{person['id']}").status_code == 204
    _forbidden(steward.create("R", "Not any more"), "records.write", ["edit-live"], W1)


@pytest.mark.journey("J40.5")
def test_a_custom_role_copied_from_a_predefined_one(world):
    """Given a role copied from Data steward without Publish, granted in A, then a live write passes
    and publishing answers `403`; changing a predefined role answers `409 ROLE_PREDEFINED`; deleting
    the granted role `409 ROLE_IN_USE`, and once the grant is removed it is deleted."""
    copied = ok(world.api.post("/roles", {"name": "Careful steward", "copiedFrom": "steward"}), 201)
    assert copied["actionGroups"] == ["browse", "edit-live", "change-sets", "publish", "bulk"]
    groups = [group for group in copied["actionGroups"] if group != "publish"]
    role = ok(
        world.api.patch(
            f"/roles/{copied['key']}",
            {"expectedVersion": copied["version"], "actionGroups": groups},
        )
    )
    assert role["actionGroups"] == groups and not role["predefined"]
    client, careful = _client(world, "Careful", (role["key"], {"workspaceKey": W1}))
    ok(careful.create("R", "Carefully"), 201)
    change_set = careful.change_set()
    _forbidden(
        careful.api.post(
            f"/change-sets/{change_set['id']}/publication", _publication_body(world, change_set)
        ),
        "change-sets.publish",
        ["publish"],
        W1,
    )
    steward = ok(world.api.get("/roles/steward"))
    refused(
        world.api.patch("/roles/steward", {"expectedVersion": steward["version"], "name": "X"}),
        409,
        "ROLE_PREDEFINED",
    )
    refused(world.api.delete(f"/roles/{role['key']}"), 409, "ROLE_IN_USE")
    [grant] = ok(world.api.get("/grants", principalId=client["id"]))["items"]
    assert world.api.delete(f"/grants/{grant['id']}").status_code == 204
    assert world.api.delete(f"/roles/{role['key']}").status_code == 204
    refused(world.api.get(f"/roles/{role['key']}"), 404, "ROLE_NOT_FOUND")


@pytest.mark.journey("J40.6")
def test_a_change_applies_on_the_next_request_in_every_process(world):
    """Given a second engine process on the same database and a client granted Data steward, when
    its grant is removed through the first, then its next request to the second answers `403`;
    granted again, it passes."""
    client, steward = _client(world, "Nightly", ("steward", {"workspaceKey": W1}))
    token = steward.api.client.headers["Authorization"]
    [grant] = ok(world.api.get("/grants", principalId=client["id"]))["items"]
    with run(world.configuration, world.database, world.ids) as other:

        def write(name: str):
            return other.world.api.post(
                "/objects",
                {
                    "applicationKey": world.app("R"),
                    "objectTypeKey": world.key("R"),
                    "workspaceKey": W1,
                    "name": name,
                    "attributes": [
                        {"attributeTypeKey": key, "value": value}
                        for key, value in world.required_values("R").items()
                    ],
                },
                headers={"Authorization": token},
            )

        ok(write("Before"), 201)
        assert world.api.delete(f"/grants/{grant['id']}").status_code == 204
        _forbidden(write("After"), "records.write", ["edit-live"], W1)
        _grant(world, "client", client["id"], "steward", workspaceKey=W1)
        ok(write("Again"), 201)


@pytest.mark.journey("J40.7", "J40.8")
def test_who_can_do_what_here_and_the_last_security_administrator(world):
    """Given a direct grant in A, a group's grant in A and an instance grant, when A's access is
    read, then all three are listed; given one person holding Security administration, removing
    that grant, or deactivating the person, answers `409 LAST_SECURITY_ADMINISTRATOR`."""
    client, _ = _client(world, "Direct", ("reader", {"workspaceKey": W1}))
    group = ok(world.api.post("/groups", {"name": "Field team"}), 201)
    _grant(world, "group", group["id"], "contributor", workspaceKey=W1)
    other, _ = _client(world, "Everywhere", ("operator", {"instance": True}))
    elsewhere, _ = _client(world, "Elsewhere", ("reader", {"workspaceKey": W2}))
    access = ok(world.api.get(f"/workspaces/{W1}/access", pageSize=500))["items"]
    seen = {
        (item["principal"]["id"], item["role"]["key"], item["scope"]["instance"]) for item in access
    }
    assert (client["id"], "reader", False) in seen
    assert (group["id"], "contributor", False) in seen
    assert (other["id"], "operator", True) in seen
    assert all(item["principal"]["id"] != elsewhere["id"] for item in access)

    # The harness person is the only person holding Security administration.
    [harness] = ok(world.api.get("/users", q="harness"))["items"]
    admins = [
        item
        for item in ok(world.api.get("/grants", principalId=harness["id"]))["items"]
        if item["role"]["key"] == "security-admin"
    ]
    assert admins
    for item in admins:
        response = world.api.delete(f"/grants/{item['id']}")
        if response.status_code == 409:
            refused(response, 409, "LAST_SECURITY_ADMINISTRATOR")
            break
    else:
        pytest.fail("removing the last Security administrator's grant was not refused")
    refused(
        world.api.patch(
            f"/users/{harness['id']}", {"expectedVersion": harness["version"], "active": False}
        ),
        409,
        "LAST_SECURITY_ADMINISTRATOR",
    )
    assert ok(world.api.get(f"/users/{harness['id']}"))["active"] is True


@pytest.mark.journey("J40.9")
def test_lists_follow_permissions(world):
    """Given a client granted Reader in A only, the workspace list, the workspace models and the
    jobs list show A and nothing of B; `GET /workspaces/B` answers `403`."""
    export = {
        "workspaceKey": W2,
        "scope": {"types": [{"objectTypeKey": world.key("R")}]},
        "format": "jsonl",
    }
    elsewhere = ok(world.api.post("/exports", export), 202)
    _, reader = _client(world, "Reader of A", ("reader", {"workspaceKey": W1}))
    workspaces = ok(reader.api.get("/workspaces", status="all"))["items"]
    assert [item["key"] for item in workspaces] == [W1]
    models = ok(reader.api.get("/workspace-models"))["items"]
    assert {item["workspaceKey"] for item in models} == {W1}
    own = ok(reader.api.post("/exports", {**export, "workspaceKey": W1}), 202)
    jobs = ok(reader.api.get("/jobs"))["items"]
    assert own["id"] in {job["id"] for job in jobs}
    assert {job["workspaceKey"] for job in jobs} == {W1}
    _forbidden(reader.api.get(f"/jobs/{elsewhere['id']}"), "jobs.use", ["browse"], W2)
    _forbidden(reader.api.get(f"/workspaces/{W2}"), "workspace.read", ["browse"], W2)
    refused(reader.api.get("/workspaces/no-such-workspace"), 404, "WORKSPACE_NOT_FOUND")


@pytest.mark.journey("J40")
def test_what_i_may_do(world):
    """Given grants in A (one narrowed to one record type) and at the instance, `GET
    /me/permissions?workspaceKey=A` lists each group with its narrowing, role and source; `GET
    /me/grants` lists the grants; a grant naming a record type A's model lacks answers `422
    GRANT_SCOPE_UNKNOWN`."""
    record_type = world.key("R")
    client, caller = _client(
        world,
        "Narrowed",
        ("steward", {"workspaceKey": W1, "recordTypes": [record_type]}),
        ("operator", {"instance": True}),
    )
    permissions = ok(caller.api.get("/me/permissions", workspaceKey=W1))
    assert permissions["workspaceKey"] == W1
    assert {role["key"] for role in permissions["roles"]} == {"steward", "operator"}
    held = {group["key"]: group for group in permissions["actionGroups"]}
    assert set(held) == {"browse", "edit-live", "change-sets", "publish", "bulk", "operations"}
    assert held["edit-live"]["recordTypes"] == [record_type]
    assert held["browse"]["recordTypes"] == []
    assert held["operations"]["sources"][0]["scope"] == "instance"
    assert held["edit-live"]["sources"][0]["scope"] == "workspace"
    elsewhere = ok(caller.api.get("/me/permissions", workspaceKey=W2))
    assert [group["key"] for group in elsewhere["actionGroups"]] == ["operations"]
    grants = ok(caller.api.get("/me/grants"))["items"]
    assert sorted(item["role"]["key"] for item in grants) == ["operator", "steward"]
    assert all(item["principal"]["id"] == client["id"] for item in grants)
    [narrowed] = [item for item in grants if item["role"]["key"] == "steward"]
    type_name = ok(world.api.get(f"/object-types/{record_type}"))["name"]
    assert narrowed["scope"]["recordTypeNames"] == [type_name]
    assert permissions["workspaceLabel"]
    refused(
        world.api.post(
            "/grants",
            {
                "principal": {"kind": "client", "id": client["id"]},
                "role": "steward",
                "scope": {"workspaceKey": W1, "recordTypes": ["no-such-type"]},
            },
        ),
        422,
        "GRANT_SCOPE_UNKNOWN",
    )
    _forbidden(caller.api.get("/users"), "security.manage", ["security-admin"], None)
