"""J40 — manage who can do what (USER_JOURNEYS.md § Security, 0.12 Z1).

A Security administrator (the harness, which holds every role at the instance) creates clients and
people, gives them roles in a workspace or at the instance, directly or through a group, and each
caller can do exactly what its roles allow: a refusal is ``403 FORBIDDEN`` naming the action, the
groups that would allow it and the workspace. A change applies on the next request, in every
process. Every case runs on two configurations through the public API.
"""

import itertools
import json
from datetime import UTC, datetime, timedelta

import pytest
from harness_identity import TestClient, request_token
from processes import run
from scenario import W1, W2, Api, World, ok, refused
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool
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

    # One principal's grants are adjacent: people, groups, clients, each by name; paging agrees.
    zed = ok(world.api.post("/users", {"username": "zed", "name": "Zed"}), 201)
    amy = ok(world.api.post("/users", {"username": "amy", "name": "amy"}), 201)
    for person, role in ((zed, "reader"), (amy, "reader"), (zed, "contributor"), (amy, "steward")):
        _grant(world, "user", person["id"], role)
    listing = f"/workspaces/{W1}/access"
    everything = ok(world.api.get(listing, pageSize=500))["items"]
    kinds = [item["principal"]["kind"] for item in everything]
    assert kinds == sorted(kinds, key=("user", "group", "client").index)
    runs = [item["principal"]["id"] for item in everything]
    assert len(set(runs)) == len({key for key, _ in itertools.groupby(runs)})
    order = [key for key, _ in itertools.groupby(runs)]
    assert order.index(amy["id"]) < order.index(zed["id"])
    assert runs.count(amy["id"]) == 2 and runs.count(zed["id"]) == 2
    walked, cursor = [], None
    while True:
        page = ok(world.api.get(listing, pageSize=2, **({"cursor": cursor} if cursor else {})))
        walked += [item["id"] for item in page["items"]]
        cursor = page["nextCursor"]
        if not cursor:
            break
    assert walked == [item["id"] for item in everything]

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


# --- Z2: record types at the write unit, jobs as their requester (D289–D297) ---------------------


def _narrowed(response, action: str, groups: list[str], workspace: str, types: list[str]) -> None:
    """A write refused for record types the caller's grants there do not name (D293)."""
    error = refused(response, 403, "FORBIDDEN")
    assert error["details"] == {
        "action": action,
        "groups": groups,
        "workspaceKey": workspace,
        "recordTypes": sorted(types),
    }


def _item(world, structure: str, name: str, **extra) -> dict:
    return {
        "op": "create",
        "applicationKey": world.app(structure),
        "objectTypeKey": world.key(structure),
        "name": name,
        "attributes": [
            {"attributeTypeKey": key, "value": value}
            for key, value in world.required_values(structure).items()
        ],
        **extra,
    }


def _batch(world, items, **body):
    request = {"workspaceKey": W1, "policy": "independent", "run": "inline", "items": items}
    return world.api.post("/batches", {**request, **body})


def _run_jobs(world) -> None:
    world.api.client.app.state.job_worker.run_until_idle()


@pytest.mark.journey("J40.3")
@pytest.mark.structures("H", "K")
def test_a_narrowed_live_write(world):
    """Given a client granted Data steward in A narrowed to one record type. When it creates and
    changes a record of that type, then both pass; a record of another type answers `403
    FORBIDDEN` with `recordTypes` naming it. A grant narrowed to the first type's application
    allows it."""
    h, k = world.key("H"), world.key("K")
    _, narrowed = _client(world, "One type", ("steward", {"workspaceKey": W1, "recordTypes": [h]}))
    record = ok(narrowed.create("H", "Allowed"), 201)
    ok(narrowed.update("H", record["id"], record["version"], name="Allowed again"))
    _narrowed(narrowed.create("K", "Not this type"), "records.write", ["edit-live"], W1, [k])

    other = world.made("K", "Made by the harness")
    _narrowed(
        narrowed.update("K", other["id"], other["version"], name="Not this one"),
        "records.write",
        ["edit-live"],
        W1,
        [k],
    )
    _, by_application = _client(
        world,
        "One application",
        ("steward", {"workspaceKey": W1, "applications": [world.app("H")]}),
    )
    ok(by_application.create("H", "By its application"), 201)
    _narrowed(
        by_application.create("K", "Other application"), "records.write", ["edit-live"], W1, [k]
    )


@pytest.mark.journey("J40.3")
@pytest.mark.structures("H", "K")
def test_a_narrowed_batch_and_import(world):
    """Given the same grant. When it sends a batch with items of both types, one by one, then the
    permitted items pass and the others carry `403 FORBIDDEN` with `recordTypes`; sent atomic,
    nothing applies. An import of records of the other type reports each refused."""
    h, k = world.key("H"), world.key("K")
    _, narrowed = _client(world, "Batches", ("steward", {"workspaceKey": W1, "recordTypes": [h]}))
    items = [_item(world, "H", "Kept"), _item(world, "K", "Refused"), _item(world, "H", "Kept too")]
    result = ok(_batch(narrowed, items))
    assert [item["status"] for item in result["items"]] == ["applied", "rejected", "applied"]
    error = result["items"][1]["error"]
    assert error["code"] == "FORBIDDEN"
    assert error["details"]["recordTypes"] == [k]
    assert error["details"]["groups"] == ["bulk"]

    atomic = ok(_batch(narrowed, items, policy="atomic"))
    assert [item["status"] for item in atomic["items"]] == [
        "unprocessed",
        "rejected",
        "unprocessed",
    ]

    lines = "\n".join(json.dumps(_item(world, "K", f"Imported {n}")) for n in range(2)) + "\n"
    request = {"workspaceKey": W1, "policy": "independent", "stage": "execute"}
    job = ok(
        narrowed.api.upload(
            "/imports",
            {"file": ("rows.jsonl", lines.encode(), "application/x-ndjson")},
            {"request": json.dumps(request)},
        ),
        202,
    )
    _run_jobs(world)
    done = ok(narrowed.api.get(f"/jobs/{job['id']}"))
    assert done["state"] == "completed" and done["counts"]["rejected"] == 2, done
    outcomes = ok(narrowed.api.get(f"/jobs/{job['id']}/items"))["items"]
    assert {
        (item["error"]["code"], tuple(item["error"]["details"]["recordTypes"])) for item in outcomes
    } == {("FORBIDDEN", (k,))}


@pytest.mark.journey("J40.3")
@pytest.mark.structures("R", "H", "K", "Bnn")
def test_a_narrowed_relationship(world):
    """Given a grant narrowed to one type, a relationship from a permitted record to a record of
    another type passes; given one narrowed to a third type, a relationship between two records of
    other types answers `403` naming both."""
    h, k = world.key("H"), world.key("K")
    source, target = world.made("H", "From"), world.made("K", "To")
    _, narrowed = _client(world, "Relate", ("steward", {"workspaceKey": W1, "recordTypes": [h]}))
    ok(narrowed.relate("Bnn", source["id"], target["id"], {"Bnn.weight": 2}), 201)
    _, elsewhere = _client(
        world, "Neither end", ("steward", {"workspaceKey": W1, "recordTypes": [world.key("R")]})
    )
    other = world.made("H", "Another")
    _narrowed(
        elsewhere.relate("Bnn", other["id"], target["id"], {"Bnn.weight": 3}),
        "records.write",
        ["edit-live"],
        W1,
        [h, k],
    )


@pytest.mark.journey("J40.3")
@pytest.mark.structures("H", "K")
def test_a_narrowed_change_set_and_publication(world):
    """Given the narrowed grant. In a change set, writing a record of the other type answers `403`;
    a change set the harness wrote touching both types, published by the client, answers `403`
    naming the other type and publishes nothing."""
    h, k = world.key("H"), world.key("K")
    _, narrowed = _client(world, "Publisher", ("steward", {"workspaceKey": W1, "recordTypes": [h]}))
    own = narrowed.change_set()
    ok(narrowed.create("H", "Proposed", change_set=own), 201)
    _narrowed(
        narrowed.create("K", "Not proposed", change_set=narrowed.current(own)),
        "records.write",
        ["change-sets"],
        W1,
        [k],
    )
    both = world.change_set()
    world.made("H", "In both", change_set=both)
    world.made("K", "Out of reach", change_set=world.current(both))
    _narrowed(
        narrowed.api.post(f"/change-sets/{both['id']}/publication", _publication_body(world, both)),
        "change-sets.publish",
        ["publish"],
        W1,
        [k],
    )
    live = ok(world.api.get(f"/objects/{k}", workspaceKey=W1, search="Out of reach"))
    assert live["items"] == []


def _remove(world, structure: str, record: dict, **params):
    return world.api.delete(
        f"/objects/{world.key(structure)}/{record['id']}",
        expectedVersion=record["version"],
        **params,
    )


def _delete_item(record: dict, **extra) -> dict:
    return {
        "op": "delete",
        "target": {"id": record["id"]},
        "expectedVersion": record["version"],
        **extra,
    }


@pytest.mark.journey("J40.3")
@pytest.mark.structures("H", "K")
def test_a_narrowed_live_delete(world):
    """Given the narrowed grant and records of both types. When the client deletes the record of
    its type, then it is gone; deleting a record of the other type answers `403 FORBIDDEN` with
    `recordTypes` naming it, and the record stays."""
    k = world.key("K")
    _, narrowed = _client(
        world, "Deleter", ("steward", {"workspaceKey": W1, "recordTypes": [world.key("H")]})
    )
    own, other = world.made("H", "Mine"), world.made("K", "Not mine")
    _narrowed(_remove(narrowed, "K", other), "records.write", ["edit-live"], W1, [k])
    assert world.record("K", other["id"])["id"] == other["id"]
    assert _remove(narrowed, "H", own).status_code == 204
    refused(world.read("H", own["id"]), 404, "OBJECT_NOT_FOUND")


@pytest.mark.journey("J40.3")
@pytest.mark.structures("R", "G", "D", "Bown")
def test_a_narrowed_cascade_delete_reaches_only_permitted_types(world):
    """Given a record of R owning a dependant of D, and a client narrowed to R only. When it
    deletes the owner with the cascade and the confirmed preview, then `403 FORBIDDEN` names D and
    nothing is deleted; a client narrowed to R and D deletes both."""
    d_key = world.key("D")
    owner = world.made("R", "Owner")
    group = world.made("G", "Scope")
    dependant = world.made(
        "D",
        "Dependant",
        parent=world.dependant_parent(group["id"]),
        relations=[world.owner("Bown", owner["id"])],
    )
    impact = refused(_remove(world, "R", owner), 409, "OBJECT_HAS_DEPENDANTS")["details"]
    cascade = {"cascade": True, "deletionPreviewToken": impact["deletionPreviewToken"]}
    _, narrowed = _client(
        world, "One", ("steward", {"workspaceKey": W1, "recordTypes": [world.key("R")]})
    )
    error = refused(_remove(narrowed, "R", owner, **cascade), 403, "FORBIDDEN")
    # The dependant's type, and its container's: the relationship that holds it there is removed too.
    assert (
        d_key in error["details"]["recordTypes"]
        and world.key("R") not in error["details"]["recordTypes"]
    )
    assert error["details"]["action"] == "records.write" and error["details"]["groups"] == [
        "edit-live"
    ]
    assert world.record("R", owner["id"])["id"] == owner["id"]
    assert world.record("D", dependant["id"])["id"] == dependant["id"]

    _, both = _client(
        world, "Both", ("steward", {"workspaceKey": W1, "recordTypes": [world.key("R"), d_key]})
    )
    assert _remove(both, "R", owner, **cascade).status_code == 204
    refused(world.read("D", dependant["id"]), 404, "OBJECT_NOT_FOUND")


@pytest.mark.journey("J40.3")
@pytest.mark.structures("H", "K")
def test_a_narrowed_batch_and_import_delete(world):
    """Given the narrowed grant. When it sends a batch deleting records of both types, one by one,
    then the permitted deletion applies and the other carries `403 FORBIDDEN` with `recordTypes`;
    sent atomic, nothing applies. An import file whose lines delete records of the other type
    reports each refused. The refused records stay."""
    k = world.key("K")
    _, narrowed = _client(
        world, "Batch deleter", ("steward", {"workspaceKey": W1, "recordTypes": [world.key("H")]})
    )
    own, other = world.made("H", "Mine"), world.made("K", "Not mine")
    items = [_delete_item(own), _delete_item(other)]
    result = ok(_batch(narrowed, items))
    assert [item["status"] for item in result["items"]] == ["applied", "rejected"]
    error = result["items"][1]["error"]
    assert error["code"] == "FORBIDDEN" and error["details"]["recordTypes"] == [k]
    assert error["details"]["groups"] == ["bulk"]
    refused(world.read("H", own["id"]), 404, "OBJECT_NOT_FOUND")
    assert world.record("K", other["id"])["id"] == other["id"]

    again, more = world.made("H", "Again"), world.made("K", "Not again")
    atomic = ok(_batch(narrowed, [_delete_item(more), _delete_item(again)], policy="atomic"))
    assert atomic["items"][0]["status"] == "rejected"
    assert world.record("H", again["id"])["id"] == again["id"]
    assert world.record("K", more["id"])["id"] == more["id"]

    lines = json.dumps(_delete_item(more)) + "\n"
    request = {"workspaceKey": W1, "policy": "independent", "stage": "execute"}
    job = ok(
        narrowed.api.upload(
            "/imports",
            {"file": ("rows.jsonl", lines.encode(), "application/x-ndjson")},
            {"request": json.dumps(request)},
        ),
        202,
    )
    _run_jobs(world)
    done = ok(narrowed.api.get(f"/jobs/{job['id']}"))
    assert done["state"] == "completed" and done["counts"]["rejected"] == 1, done
    outcomes = ok(narrowed.api.get(f"/jobs/{job['id']}/items"))["items"]
    assert {
        (item["error"]["code"], tuple(item["error"]["details"]["recordTypes"])) for item in outcomes
    } == {("FORBIDDEN", (k,))}
    assert world.record("K", more["id"])["id"] == more["id"]


@pytest.mark.journey("J40.3")
@pytest.mark.structures("H", "K")
def test_a_narrowed_delete_in_a_change_set(world):
    """Given the narrowed grant and its change set. When it deletes a record of its type in the
    change set, then the change set holds it no more; deleting a record of the other type answers
    `403 FORBIDDEN` with `recordTypes` and the change set still holds it."""
    k = world.key("K")
    _, narrowed = _client(
        world, "Proposer", ("steward", {"workspaceKey": W1, "recordTypes": [world.key("H")]})
    )
    own, other = world.made("H", "Mine"), world.made("K", "Not mine")
    change_set = narrowed.change_set()

    def params() -> dict:
        return {
            "changeSetId": change_set["id"],
            "expectedChangeSetVersion": narrowed.current(change_set)["version"],
        }

    _narrowed(_remove(narrowed, "K", other, **params()), "records.write", ["change-sets"], W1, [k])
    assert narrowed.record("K", other["id"], changeSetId=change_set["id"])["id"] == other["id"]
    assert _remove(narrowed, "H", own, **params()).status_code == 204
    refused(world.read("H", own["id"], changeSetId=change_set["id"]), 404, "OBJECT_NOT_FOUND")


LADDER = ("L1", "L2", "L3", "L.only1", "L.extra")


@pytest.mark.journey("J40.3")
@pytest.mark.structures(*LADDER)
def test_a_narrowed_type_change(world):
    """Given a grant narrowed to L1 and two top-level L1 records. When the client moves one under the
    other, which makes it an L2, then the plan is refused with `FORBIDDEN` naming L2 for that record,
    and applying it changes nothing."""
    l1, l2 = world.key("L1"), world.key("L2")
    moving = world.made("L1", "Moving", values={"L.code": "M-1", "L.only1": "kept"})
    world.made("L2", "Moving 2", parent=moving["id"], values={"L.code": "M-2"})
    receiving = world.made("L1", "Receiving", values={"L.code": "R-1"})
    _, narrowed = _client(world, "Reshaper", ("steward", {"workspaceKey": W1, "recordTypes": [l1]}))
    change_set = narrowed.change_set()
    operation = {"kind": "move", "objectId": moving["id"], "parentObjectId": receiving["id"]}
    inputs = [
        {
            "objectId": moving["id"],
            "attributes": [{"attributeTypeKey": world.key("L.extra"), "value": "given"}],
        }
    ]
    mappings = [{"fromObjectTypeKey": l1, "toObjectTypeKey": l2, "attributes": []}]
    body = {"operation": operation, "inputs": inputs, "choices": {"mappings": mappings}}
    plan = ok(narrowed.api.post(f"/change-sets/{change_set['id']}/restructurings/preview", body))
    assert plan["status"] == "refused", plan
    [refusal] = [item for record in plan["records"] for item in record["refusals"]]
    assert refusal["code"] == "FORBIDDEN" and refusal["objectId"] == moving["id"]
    assert refusal["details"]["recordTypes"] == [l2]
    applied = narrowed.api.post(
        f"/change-sets/{change_set['id']}/restructurings",
        {
            **body,
            "planDigest": plan["planDigest"],
            "expectedChangeSetVersion": narrowed.current(change_set)["version"],
        },
    )
    refused(applied, 422, "RESTRUCTURING_NOT_READY")
    assert world.record("L1", moving["id"], changeSetId=change_set["id"])["objectTypeKey"] == l1


@pytest.mark.journey("J40.3")
@pytest.mark.structures("R", "R2")
def test_a_narrowed_move(world):
    """Given copy and move in the target narrowed to one of its types and Browse in the source. When
    the client moves the whole workspace, then only that type's records load and the others are
    refused with `FORBIDDEN` naming their type. A `mode: move` without Work in change sets in
    the source answers `403` before it starts (D297)."""
    from test_j38_1_model_mapping import _read
    from test_j38_2_move_dry_run import _rows
    from test_j38_3_move import _ledger, _mapped

    other, target, key = _mapped(world)
    ledger = _ledger(world, "Ledger")
    world.made("R2", "Entry", parent=ledger["id"])
    allowed = other.key("R")
    _, mover = _client(
        world,
        "Mover",
        ("owner", {"workspaceKey": target, "recordTypes": [allowed]}),
        ("reader", {"workspaceKey": W1}),
    )
    body = {
        "sourceWorkspaceKey": W1,
        "targetWorkspaceKey": target,
        "mapping": {"key": key, "expectedVersion": _read(world, key)["version"]},
        "selection": {},
        "stage": "execute",
    }
    _forbidden(
        mover.api.post("/moves", {**body, "mode": "move"}), "moves.create", ["change-sets"], W1
    )
    job = ok(mover.api.post("/moves", body), 202)
    _run_jobs(world)
    job = ok(mover.api.get(f"/jobs/{job['id']}"))
    assert job["state"] == "completed", job
    rows = [row for row in _rows(world, job["id"]) if row["kind"] == "record"]
    loaded = {row["targetType"] for row in rows if row["outcome"] in ("create", "update")}
    assert loaded == {allowed}, rows
    [entry] = [row for row in rows if row["targetType"] == other.key("R2")]
    [reason] = entry["reasons"]
    assert entry["outcome"] == "refused" and reason["code"] == "FORBIDDEN"
    assert reason["details"]["recordTypes"] == [other.key("R2")]
    assert reason["details"]["groups"] == ["copy-move"]


@pytest.mark.journey("J40.10")
@pytest.mark.structures("H")
def test_a_job_keeps_its_requesters_permissions(world):
    """Given a client that submits two background batches, when its grant is removed before they
    run, then the requester still reads and cancels its own job, and the other fails at its step
    with `403 FORBIDDEN` naming the requester; a client holding nothing there gets `403` for it."""
    client, steward = _client(world, "Requester", ("steward", {"workspaceKey": W1}))
    first = ok(_batch(steward, [_item(world, "H", "Queued")], run="background"), 202)
    second = ok(_batch(steward, [_item(world, "H", "Cancelled")], run="background"), 202)
    [grant] = ok(world.api.get("/grants", principalId=client["id"]))["items"]
    assert world.api.delete(f"/grants/{grant['id']}").status_code == 204

    assert ok(steward.api.get(f"/jobs/{first['id']}"))["state"] == "queued"
    ok(steward.api.post(f"/jobs/{second['id']}/cancel"), 202)
    listed = {job["id"] for job in ok(steward.api.get("/jobs"))["items"]}
    assert {first["id"], second["id"]} <= listed
    _run_jobs(world)
    failed = ok(steward.api.get(f"/jobs/{first['id']}"))
    assert failed["state"] == "failed", failed
    assert failed["error"]["code"] == "FORBIDDEN"
    assert failed["error"]["details"]["requestedBy"]["id"] == client["id"]
    assert failed["error"]["details"]["groups"] == ["bulk"]
    assert ok(steward.api.get(f"/jobs/{second['id']}"))["state"] == "cancelled"

    _, stranger = _client(world, "Stranger", ("reader", {"workspaceKey": W2}))
    _forbidden(stranger.api.get(f"/jobs/{first['id']}"), "jobs.use", ["bulk"], W1)


@pytest.mark.journey("J40")
@pytest.mark.structures("R", "R.u", "R.q", "R.x1")
def test_a_source_file_belongs_to_its_uploader_and_workspace(world):
    """Given clients holding Bulk and import in A, and one in B only. A file the first uploads for
    A's profile is listed for it and for A's other holder, not for B's client, whose read of it
    answers `403` (D295)."""
    from test_j36_workspace_resources import XLSX, _profile, _rows

    profile = ok(world.api.post("/import-profiles", _profile(world)), 201)
    _, uploader = _client(world, "Uploader", ("steward", {"workspaceKey": W1}))
    _, colleague = _client(world, "Colleague", ("steward", {"workspaceKey": W1}))
    _, elsewhere = _client(world, "Elsewhere", ("steward", {"workspaceKey": W2}))
    source = ok(
        uploader.api.upload(
            "/source-files",
            {"file": ("rows.xlsx", _rows("MINE"), XLSX)},
            {"request": json.dumps({"owner": {"profileKey": profile["key"]}, "workspaceKey": W1})},
        ),
        201,
    )

    def listed(caller) -> set[str]:
        page = ok(caller.api.get("/source-files", profileKey=profile["key"]))
        return {item["id"] for item in page["items"]}

    assert source["id"] in listed(uploader) and source["id"] in listed(colleague)
    assert source["id"] not in listed(elsewhere)
    ok(colleague.api.get(f"/source-files/{source['id']}"))
    _forbidden(
        elsewhere.api.get(f"/source-files/{source['id']}"), "source-files.manage", ["bulk"], W1
    )


def _upload(caller, profile_key: str, workspace: str, prefix: str):
    from test_j36_workspace_resources import XLSX, _rows

    return caller.api.upload(
        "/source-files",
        {"file": ("rows.xlsx", _rows(prefix), XLSX)},
        {"request": json.dumps({"owner": {"profileKey": profile_key}, "workspaceKey": workspace})},
    )


def _current(world, profile_key: str) -> dict[str | None, str]:
    """The profile's current file (not superseded) of each workspace, read as the harness."""
    page = ok(world.api.get("/source-files", profileKey=profile_key, pageSize=200))
    return {
        item["workspaceKey"]: item["id"] for item in page["items"] if not item.get("supersededAt")
    }


@pytest.mark.journey("J40")
@pytest.mark.structures("R", "R.u", "R.q", "R.x1")
def test_a_profile_upload_needs_bulk_in_its_workspace(world):
    """Given a profile whose file the second workspace's owner uploaded, and a Data steward holding
    Bulk only in the first. When the steward uploads for the profile naming the second workspace,
    then it answers `403 FORBIDDEN` naming Bulk and the second workspace, and the owner's file stays
    current and unchanged."""
    from test_j36_workspace_resources import _profile

    profile = ok(world.api.post("/import-profiles", _profile(world)), 201)
    _, owner = _client(world, "Owner of two", ("steward", {"workspaceKey": W2}))
    _, steward = _client(world, "Steward of one", ("steward", {"workspaceKey": W1}))
    theirs = ok(_upload(owner, profile["key"], W2, "THEIRS"), 201)
    before = ok(world.api.get(f"/source-files/{theirs['id']}"))

    _forbidden(_upload(steward, profile["key"], W2, "OTHER"), "source-files.manage", ["bulk"], W2)

    assert _current(world, profile["key"]) == {W2: theirs["id"]}
    assert ok(world.api.get(f"/source-files/{theirs['id']}")) == before
    assert len(ok(world.api.get("/source-files", profileKey=profile["key"]))["items"]) == 1


@pytest.mark.journey("J40")
@pytest.mark.structures("R", "R.u", "R.q", "R.x1")
def test_an_upload_supersedes_only_its_own_workspaces_file(world):
    """Given files of one profile in both workspaces. When a steward holding Bulk in the first
    uploads again there, then only the first workspace's earlier file is superseded: each
    workspace has its own current file, also after the retention sweep."""
    from test_j36_workspace_resources import _profile

    from app.engine.sources.store import expire_superseded

    profile = ok(world.api.post("/import-profiles", _profile(world)), 201)
    _, owner = _client(world, "Owner of two", ("steward", {"workspaceKey": W2}))
    _, steward = _client(world, "Steward of one", ("steward", {"workspaceKey": W1}))
    first = ok(_upload(steward, profile["key"], W1, "ONE-A"), 201)
    theirs = ok(_upload(owner, profile["key"], W2, "TWO-A"), 201)
    assert _current(world, profile["key"]) == {W1: first["id"], W2: theirs["id"]}

    second = ok(_upload(steward, profile["key"], W1, "ONE-B"), 201)
    assert _current(world, profile["key"]) == {W1: second["id"], W2: theirs["id"]}
    engine = create_engine(world.database, poolclass=NullPool)
    with Session(engine) as session:
        expired = expire_superseded(session, datetime.now(UTC) + timedelta(minutes=1), 0)
        session.commit()
    engine.dispose()
    assert expired == [first["id"]]
    assert _current(world, profile["key"]) == {W1: second["id"], W2: theirs["id"]}
    ok(world.api.get(f"/source-files/{theirs['id']}"))


@pytest.mark.journey("J40")
@pytest.mark.structures("R", "R.u", "R.q", "R.x1")
def test_an_instance_wide_bulk_holder_uploads_in_any_workspace(world):
    """Given a client holding Data steward at the instance. When it uploads a profile's file naming
    either workspace, then both are accepted and each is current in its own workspace."""
    from test_j36_workspace_resources import _profile

    profile = ok(world.api.post("/import-profiles", _profile(world)), 201)
    _, everywhere = _client(world, "Everywhere", ("steward", {"instance": True}))
    one = ok(_upload(everywhere, profile["key"], W1, "ONE"), 201)
    two = ok(_upload(everywhere, profile["key"], W2, "TWO"), 201)
    assert _current(world, profile["key"]) == {W1: one["id"], W2: two["id"]}


@pytest.mark.journey("J40")
@pytest.mark.structures("R", "R.u", "R.q", "R.x1")
def test_a_profiles_files_coexist_one_current_per_workspace(world):
    """Given a steward in each workspace. When both upload for the same profile, then neither
    supersedes the other's file: each is current in its own workspace."""
    from test_j36_workspace_resources import _profile

    profile = ok(world.api.post("/import-profiles", _profile(world)), 201)
    _, one = _client(world, "Steward one", ("steward", {"workspaceKey": W1}))
    _, two = _client(world, "Steward two", ("steward", {"workspaceKey": W2}))
    first = ok(_upload(one, profile["key"], W1, "ONE"), 201)
    second = ok(_upload(two, profile["key"], W2, "TWO"), 201)
    assert _current(world, profile["key"]) == {W1: first["id"], W2: second["id"]}


def _checked_profile(world):
    """A profile, a steward holding Bulk in the first workspace only and the owner of the second;
    ``upload`` stores a file as one of them and runs the worker, which profiles it and checks it."""
    from test_j36_workspace_resources import _profile

    profile = ok(world.api.post("/import-profiles", _profile(world)), 201)
    _, owner = _client(world, "Owner of two", ("steward", {"workspaceKey": W2}))
    _, steward = _client(world, "Steward of one", ("steward", {"workspaceKey": W1}))

    def upload(caller, workspace: str, prefix: str) -> str:
        source = ok(_upload(caller, profile["key"], workspace, prefix), 201)
        world.api.client.app.state.job_worker.run_until_idle()
        return source["id"]

    return profile["key"], steward, owner, upload


@pytest.mark.journey("J40")
@pytest.mark.structures("R", "R.u", "R.q", "R.x1")
def test_a_profile_check_needs_bulk_in_its_workspace(world):
    """Given a profile whose file in the second workspace is checked, and a Data steward holding
    Bulk only in the first. When the steward reads the check or asks for it again naming the second
    workspace (and the findings and rows behind it), then each answers `403 FORBIDDEN` naming Bulk
    and the second workspace, and the check the owner reads is unchanged."""
    key, steward, owner, upload = _checked_profile(world)
    theirs = upload(owner, W2, "TWO")
    path = f"/import-profiles/{key}/check"
    before = ok(owner.api.get(path, workspaceKey=W2))
    assert before["sourceFileId"] == theirs

    for suffix in ("", "/new-values", "/drift", "/missing-records", "/rows"):
        _forbidden(
            steward.api.get(path + suffix, workspaceKey=W2), "import-profiles.manage", ["bulk"], W2
        )
    _forbidden(steward.api.post(path, {}, workspaceKey=W2), "import-profiles.manage", ["bulk"], W2)
    assert ok(owner.api.get(path, workspaceKey=W2)) == before


@pytest.mark.journey("J40")
@pytest.mark.structures("R", "R.u", "R.q", "R.x1")
def test_a_profile_check_reads_only_its_workspaces_file(world):
    """Given a profile with a file in both workspaces. When each steward checks it in its own
    workspace, then each check reads that workspace's file; when the first workspace's steward has
    no file of its own there, the check answers no file and the second workspace's file is not
    read, however recent."""
    key, steward, owner, upload = _checked_profile(world)
    path = f"/import-profiles/{key}/check"
    theirs = upload(owner, W2, "TWO")

    # (iv) a file in the second workspace only: the first has none, whichever route asks.
    refused(steward.api.get(path, workspaceKey=W1), 404, "PROFILE_CHECK_NOT_FOUND")
    refused(steward.api.post(path, {}, workspaceKey=W1), 404, "SOURCE_FILE_NOT_FOUND")

    # (ii), (iii) a file in each: each check reads its own.
    mine = upload(steward, W1, "ONE")
    assert ok(steward.api.get(path, workspaceKey=W1))["sourceFileId"] == mine
    assert ok(owner.api.get(path, workspaceKey=W2))["sourceFileId"] == theirs
    again = ok(steward.api.post(path, {}, workspaceKey=W1), 202)
    world.api.client.app.state.job_worker.run_until_idle()
    assert again["sourceFileId"] == mine
    assert ok(steward.api.get(path, workspaceKey=W1))["sourceFileId"] == mine
    assert ok(owner.api.get(path, workspaceKey=W2))["sourceFileId"] == theirs


@pytest.mark.journey("J40")
@pytest.mark.structures("R", "R.u", "R.q", "R.x1")
def test_a_profile_check_must_name_its_workspace(world):
    """When a check is read or asked for without `workspaceKey`, then it answers `422
    REQUEST_VALIDATION_ERROR` naming the query parameter."""
    key, steward, _, upload = _checked_profile(world)
    upload(steward, W1, "ONE")
    path = f"/import-profiles/{key}/check"
    for response in (steward.api.get(path), steward.api.post(path, {})):
        error = refused(response, 422, "REQUEST_VALIDATION_ERROR")
        assert [item["loc"] for item in error["details"]] == [["query", "workspaceKey"]], error


@pytest.mark.journey("J40")
@pytest.mark.structures("R")
def test_a_stale_grant_allows_nothing(world):
    """Given a grant narrowed to a record type that only a newer release has, when the workspace
    goes back to the release without it, then the grant reads `stale: true` naming the type, and
    the client's writes of any type answer `403` (D296)."""
    original = world.workspace_model()["releaseId"]
    model, _key = world.candidate("compatible")
    ok(world.activate(world.install(model)["id"]))
    added = f"{world.key('R')}-added-type"
    client, narrowed = _client(
        world, "Stale", ("steward", {"workspaceKey": W1, "recordTypes": [added]})
    )
    ok(world.activate(original))

    [grant] = ok(world.api.get("/grants", principalId=client["id"]))["items"]
    assert grant["stale"] is True
    assert grant["scope"]["missingRecordTypes"] == [added]
    held = {g["key"]: g for g in ok(narrowed.api.get("/me/permissions"))["actionGroups"]}
    assert held["edit-live"]["stale"] is True
    _narrowed(
        narrowed.create("R", "Nothing allowed"),
        "records.write",
        ["edit-live"],
        W1,
        [world.key("R")],
    )


@pytest.mark.journey("J40.2")
@pytest.mark.structures("R", "R.n", "B1n", "K")
def test_a_delete_naming_a_change_set_only_in_its_body_is_not_a_change_set_write(world):
    """Given Contributor in A and live records. When it deletes a record, a value or a
    relationship live with `changeSetId` in the request body instead of the query, then each
    answers `403 FORBIDDEN` naming Edit live and nothing is deleted; the same deletes naming the
    change set in the query pass into the change set and leave the live data alone (0.12 R-F1)."""
    record = world.made("R", "Kept live", values={"R.n": 5})
    other = world.made("K", "Related")
    relation = ok(world.relate("B1n", record["id"], other["id"]), 201)
    _, contributor = _client(world, "Contributor", ("contributor", {"workspaceKey": W1}))
    change_set = contributor.change_set()
    smuggled = {"changeSetId": change_set["id"], "expectedChangeSetVersion": change_set["version"]}
    client = contributor.api.client
    base = "/api/v1"
    path = f"/objects/{world.key('R')}/{record['id']}"

    for url, params in (
        (f"{path}/attributes/{world.key('R.n')}", {"expectedVersion": record["version"]}),
        (f"/relations/{relation['id']}", {"expectedVersion": relation["version"]}),
        (path, {"expectedVersion": record["version"]}),
    ):
        response = client.request("DELETE", base + url, params=params, json=smuggled)
        _forbidden(response, "records.write", ["edit-live"], W1)
    live = world.record("R", record["id"])
    assert world.value(live, "R.n") == 5
    ok(world.api.get(f"/relations/{relation['id']}"))

    ok(
        contributor.api.delete(
            f"{path}/attributes/{world.key('R.n')}",
            changeSetId=change_set["id"],
            expectedChangeSetVersion=change_set["version"],
            expectedVersion=record["version"],
        ),
        204,
    )
    assert world.value(world.record("R", record["id"]), "R.n") == 5


@pytest.mark.journey("J40.3")
@pytest.mark.structures("R", "H", "H.code")
def test_a_narrowed_editor_cannot_change_values_of_a_record_already_in_the_change_set(world):
    """Given Data steward narrowed to one record type, and a record of another type that someone
    else already changed in a change set. When the narrowed client changes or removes one of its
    values in that change set, then each answers `403 FORBIDDEN` naming the record type and the
    value stays (0.12 R-F2)."""
    record = world.made("H", "Held by another", values={"H.code": "H-1"})
    _, narrowed = _client(
        world, "Narrow", ("steward", {"workspaceKey": W1, "recordTypes": [world.key("R")]})
    )
    change_set = world.change_set()
    ok(
        world.api.patch(
            f"/objects/{world.key('H')}/{record['id']}",
            {
                "expectedVersion": record["version"],
                "name": "Renamed in the change set",
                "changeSetId": change_set["id"],
                "expectedChangeSetVersion": change_set["version"],
            },
        )
    )
    current = world.current(change_set)
    in_set = world.record("H", record["id"], changeSetId=change_set["id"])
    path = f"/objects/{world.key('H')}/{record['id']}/attributes/{world.key('H.code')}"
    body = {
        "value": "H-2",
        "expectedVersion": in_set["version"],
        "changeSetId": change_set["id"],
        "expectedChangeSetVersion": current["version"],
    }
    _narrowed(
        narrowed.api.patch(path, body), "records.write", ["change-sets"], W1, [world.key("H")]
    )
    _narrowed(
        narrowed.api.delete(
            path,
            changeSetId=change_set["id"],
            expectedChangeSetVersion=current["version"],
            expectedVersion=in_set["version"],
        ),
        "records.write",
        ["change-sets"],
        W1,
        [world.key("H")],
    )
    after = world.record("H", record["id"], changeSetId=change_set["id"])
    assert world.value(after, "H.code") == "H-1"
