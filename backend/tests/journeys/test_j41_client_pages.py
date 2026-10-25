"""J41 — manage clients and their access, the reads the Clients page needs (USER_JOURNEYS.md §
Security, 0.12 SP2).

A Security administrator (the harness) lists clients with the roles and consumer APIs they hold and
who created them, tells a client's secrets apart by their last four characters, and reads what a
grant in a workspace can be made from without reading that workspace's data (D348–D350, D355).
Every case runs on two configurations through the public API.
"""

import pytest
from scenario import W1, W2, ok, refused
from test_j39_sign_in import _browser, _person, _sign_in
from test_j40_authorization import _as, _grant


def _caller(world) -> dict:
    me = ok(world.api.get("/me"))
    return {"kind": me["kind"], "id": me["id"], "name": me["name"]}


def _consumer_grant(world, client: dict, workspace: str) -> dict:
    body = {
        "principal": {"kind": "client", "id": client["id"]},
        "consumerApi": world.key("Capi"),
        "scope": {"workspaceKey": workspace},
    }
    return ok(world.api.post("/grants", body), 201)


@pytest.mark.journey("J41")
def test_a_clients_access_is_in_its_reads(world):
    """Given a client granted Reader in A, Operator at the instance and a consumer API in A and B,
    and a second client with nothing. When the clients (and each client) are read, then the first
    lists Reader in A, Operator at the instance and the API in A and B, the second empty lists, and
    both name the caller as `createdBy`; `q` and `active` still narrow the list."""
    sync = ok(world.api.post("/clients", {"name": "Catalogue sync sp2"}), 201)
    idle = ok(world.api.post("/clients", {"name": "Idle portal sp2"}), 201)
    _grant(world, "client", sync["id"], "reader", workspaceKey=W1)
    _grant(world, "client", sync["id"], "operator", instance=True)
    _consumer_grant(world, sync, W1)
    _consumer_grant(world, sync, W2)

    listed = {item["id"]: item for item in ok(world.api.get("/clients", q="sp2"))["items"]}
    assert set(listed) == {sync["id"], idle["id"]}
    roles = {role["key"]: role for role in listed[sync["id"]]["roles"]}
    assert set(roles) == {"reader", "operator"}
    assert [where["key"] for where in roles["reader"]["workspaces"]] == [W1]
    assert not roles["reader"]["instance"]
    assert roles["operator"]["instance"] and roles["operator"]["workspaces"] == []
    [api] = listed[sync["id"]]["consumerApis"]
    assert api["key"] == world.key("Capi")
    assert sorted(where["key"] for where in api["workspaces"]) == sorted([W1, W2])
    assert all(where["label"] for where in api["workspaces"])
    assert listed[idle["id"]]["roles"] == [] and listed[idle["id"]]["consumerApis"] == []
    caller = _caller(world)
    assert listed[sync["id"]]["createdBy"] == caller == listed[idle["id"]]["createdBy"]

    one = ok(world.api.get(f"/clients/{sync['id']}"))
    assert one["roles"] == listed[sync["id"]]["roles"]
    assert one["consumerApis"] == listed[sync["id"]]["consumerApis"]
    assert one["createdBy"] == caller

    ok(
        world.api.patch(
            f"/clients/{idle['id']}", {"expectedVersion": idle["version"], "active": False}
        )
    )
    active = ok(world.api.get("/clients", q="sp2", active="true"))["items"]
    assert [item["id"] for item in active] == [sync["id"]]


@pytest.mark.journey("J41.3")
def test_a_clients_secrets_are_told_apart(world):
    """Given a new client, its secret answered once. When the client is read, then its secret's
    `hint` is the secret's last four characters; after a new secret with a one-hour overlap, both
    are listed with their own hints and the older with `expiresAt`; neither value is answered
    again."""
    client = ok(world.api.post("/clients", {"name": "Label printer sp2"}), 201)
    first = client["secret"]
    [only] = ok(world.api.get(f"/clients/{client['id']}"))["secrets"]
    assert only["hint"] == first[-4:] and only["id"] == client["secretId"]

    rotated = ok(
        world.api.post(
            f"/clients/{client['id']}/secrets",
            {"expectedVersion": client["version"], "overlapHours": 1},
        ),
        201,
    )
    second = rotated["secret"]
    read = ok(world.api.get(f"/clients/{client['id']}"))
    by_id = {secret["id"]: secret for secret in read["secrets"]}
    assert by_id[client["secretId"]]["hint"] == first[-4:]
    assert by_id[client["secretId"]]["expiresAt"] is not None
    assert by_id[rotated["secretId"]]["hint"] == second[-4:]
    assert by_id[rotated["secretId"]]["expiresAt"] is None
    text = str(read) + str(ok(world.api.get("/clients", q="Label printer sp2")))
    assert first not in text and second not in text


@pytest.mark.journey("J41")
def test_a_grant_is_made_from_the_workspaces_options(world):
    """Given two workspaces. When their grant options are read, then each answers the applications,
    record types and consumer APIs its model declares (as `GET /model` shows them there); a person
    holding only Security administrator reads them and grants a client one of those consumer APIs;
    an unknown workspace answers `404 WORKSPACE_NOT_FOUND`; a person without Security
    administration `403 FORBIDDEN`."""
    for workspace in (W1, W2):
        model = ok(world.api.get("/model", workspaceKey=workspace))
        options = ok(world.api.get(f"/workspaces/{workspace}/grant-options"))
        named = lambda items: [(item["key"], item["name"]) for item in items]
        assert named(options["applications"]) == named(model["applications"])
        assert named(options["recordTypes"]) == named(model["objectTypes"])
        assert named(options["consumerApis"]) == named(model.get("consumerApis") or [])

    admin = _person(world, "mei-sp2")
    _grant(world, "user", admin["id"], "security-admin", instance=True)
    as_admin = _as(world, _sign_in(_browser(world), "mei-sp2"))
    options = ok(as_admin.api.get(f"/workspaces/{W2}/grant-options"))
    assert world.key("Capi") in [item["key"] for item in options["consumerApis"]]
    client = ok(as_admin.api.post("/clients", {"name": "Nightly export sp2"}), 201)
    grant = ok(
        as_admin.api.post(
            "/grants",
            {
                "principal": {"kind": "client", "id": client["id"]},
                "consumerApi": world.key("Capi"),
                "scope": {"workspaceKey": W2},
            },
        ),
        201,
    )
    assert grant["consumerApi"]["key"] == world.key("Capi")

    refused(world.api.get("/workspaces/no-such-place/grant-options"), 404, "WORKSPACE_NOT_FOUND")
    reader = _person(world, "jonah-sp2")
    _grant(world, "user", reader["id"], "reader", workspaceKey=W1)
    as_reader = _as(world, _sign_in(_browser(world), "jonah-sp2"))
    refused(as_reader.api.get(f"/workspaces/{W1}/grant-options"), 403, "FORBIDDEN")
