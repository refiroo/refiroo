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
    assert applied.status_code in (403, 422), applied.text
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
