"""J45 — start from home: the reads the home page needs (USER_JOURNEYS.md § Security, 0.12 HM1).

The page shows the workspaces the caller may browse with their applications and what waits there
(D332), and the caller's open change sets across workspaces (D333). Every case runs on two
configurations through the public API; J45.1 puts a second workspace on the other configuration's
model.
"""

import pytest
from harness_identity import TestClient
from scenario import W1, W2, W3, ok
from test_j17_review import _claim
from test_j36_workspace_models import BOTH, _beside
from test_j39_sign_in import _person, _sign_in
from test_j40_authorization import _as, _client, _grant, _publication_body


def _workspaces(world) -> dict[str, dict]:
    return {item["key"]: item for item in ok(world.api.get("/me/workspaces"))["items"]}


def _own(world) -> list[dict]:
    return ok(world.api.get("/me/change-sets"))["items"]


@pytest.mark.journey("J45.1")
@pytest.mark.structures(*BOTH)
def test_the_workspaces_i_can_open(world):
    """Given a caller who is Reader in A and Data steward in B, B on another model, a Security
    administrator with no data role and an instance Reader. When `GET /me/workspaces` is read, then
    the caller sees A and B, the default first, each naming its own model's applications; A's
    `openChangeSets` is null and B's counts every open change set; the administrator sees none; the
    instance Reader sees every active workspace and not the retired one."""
    _, _, other = _beside(world)
    _, caller = _client(
        world,
        "Reader here, steward there",
        ("reader", {"workspaceKey": W1}),
        ("steward", {"workspaceKey": other}),
    )
    _, security = _client(world, "Security only", ("security-admin", {"instance": True}))
    _, everywhere = _client(world, "Reads everything", ("reader", {"instance": True}))

    page = ok(caller.api.get("/me/workspaces"))
    assert [item["key"] for item in page["items"]] == [W1, other]
    seen = {item["key"]: item for item in page["items"]}
    assert seen[W1]["isDefault"] is True and seen[other]["isDefault"] is False
    assert seen[W1]["model"]["releaseId"] != seen[other]["model"]["releaseId"]
    for key in (W1, other):
        model = ok(world.api.get("/model", workspaceKey=key))
        assert [app["key"] for app in seen[key]["applications"]] == [
            app["key"] for app in model["applications"]
        ]
        assert all(app["name"] and app["defaultView"] for app in seen[key]["applications"])
    assert seen[W1]["openChangeSets"] is None and seen[W1]["ownChangeSets"] == 0
    assert seen[other]["openChangeSets"] == 0 and seen[other]["ownChangeSets"] == 0

    assert ok(security.api.get("/me/workspaces"))["items"] == []
    every = _workspaces(everywhere)
    assert {W1, W2, other} <= set(every) and W3 not in every


@pytest.mark.journey("J45.2")
@pytest.mark.structures("R", "K", "B1n")
def test_what_is_mine(world):
    """Given a person who is Data steward in A. When they create a change set, add two records and
    one relationship in it, and another caller creates one in A, then A's `ownChangeSets` is 1 and
    `openChangeSets` two more than before, and `GET /me/change-sets` lists the person's one with
    `changeCount` 3 and A's label."""
    person = _person(world, "hana-hm1")
    _grant(world, "user", person["id"], "steward", workspaceKey=W1)
    steward = _as(
        world, _sign_in(TestClient(world.api.client.app, authenticated=False), "hana-hm1")
    )
    _, other = _client(world, "Another contributor", ("contributor", {"workspaceKey": W1}))
    before = _workspaces(steward)[W1]["openChangeSets"]

    change_set = steward.change_set(name="Spring corrections")
    record = steward.made("R", "Added ledger", change_set=steward.current(change_set))
    token = steward.made("K", "Added token", change_set=steward.current(change_set))
    ok(steward.relate("B1n", record["id"], token["id"], **_claim(steward, change_set)), 201)
    other.change_set()

    here = _workspaces(steward)[W1]
    assert here["ownChangeSets"] == 1 and here["openChangeSets"] == before + 2
    [mine] = _own(steward)
    assert mine["id"] == change_set["id"] and mine["name"] == "Spring corrections"
    assert mine["changeCount"] == 3
    assert mine["workspaceLabel"] == ok(world.api.get(f"/workspaces/{W1}"))["label"]
    assert mine["createdBy"]["id"] == person["id"]


@pytest.mark.journey("J45.2")
@pytest.mark.structures("R")
def test_my_change_sets_count_their_changes_in_one_statement_for_the_page(world):
    """Given a person with one change set holding a record, and then with three. When
    `GET /me/change-sets` is read, then each reads its own `changeCount` and the page costs the same
    number of statements for three change sets as for one (the counts are not asked one by one)."""
    from sqlalchemy import event

    from app.db import get_engine

    person = _person(world, "hana-count")
    _grant(world, "user", person["id"], "steward", workspaceKey=W1)
    steward = _as(
        world, _sign_in(TestClient(world.api.client.app, authenticated=False), "hana-count")
    )

    def statements() -> tuple[list[dict], int]:
        seen: list[str] = []
        engine = get_engine()
        listener = lambda *args: seen.append(args[2])
        event.listen(engine, "before_cursor_execute", listener)
        try:
            items = _own(steward)
        finally:
            event.remove(engine, "before_cursor_execute", listener)
        return items, len(seen)

    first = steward.change_set(name="One")
    steward.made("R", "In one", change_set=steward.current(first))
    items, one = statements()
    assert [item["changeCount"] for item in items] == [1]
    for n in (2, 3):
        more = steward.change_set(name=f"Number {n}")
        for k in range(n):
            steward.made("R", f"In {n} {k}", change_set=steward.current(more))
    items, three = statements()
    assert sorted(item["changeCount"] for item in items) == [1, 2, 3]
    assert three == one


@pytest.mark.journey("J45.3")
def test_it_follows_the_work(world):
    """Given a caller who is Data steward in A and Contributor in B with a change set in each. When
    the one in A is published, then it leaves `GET /me/change-sets` and A's counts drop; when the
    grant in B is removed, B and the change set there are gone on the next request."""
    client, caller = _client(world, "Steward and contributor", ("steward", {"workspaceKey": W1}))
    in_b = _grant(world, "client", client["id"], "contributor", workspaceKey=W2)
    here = caller.change_set()
    there = caller.change_set(W2)
    assert {item["id"] for item in _own(caller)} == {here["id"], there["id"]}
    counts = _workspaces(caller)[W1]

    ok(caller.api.post(f"/change-sets/{here['id']}/publication", _publication_body(world, here)))
    assert [item["id"] for item in _own(caller)] == [there["id"]]
    after = _workspaces(caller)[W1]
    assert after["ownChangeSets"] == counts["ownChangeSets"] - 1
    assert after["openChangeSets"] == counts["openChangeSets"] - 1

    assert world.api.delete(f"/grants/{in_b['id']}").status_code == 204
    assert W2 not in _workspaces(caller)
    assert _own(caller) == []


@pytest.mark.journey("J45.4")
def test_a_client_sees_its_own(world):
    """Given a client holding Contributor in A that created a change set there, and another that
    created one too. When the first reads `GET /me/change-sets`, then it sees its own change set and
    no one else's."""
    _, first = _client(world, "First integration", ("contributor", {"workspaceKey": W1}))
    _, second = _client(world, "Second integration", ("contributor", {"workspaceKey": W1}))
    mine = first.change_set()
    second.change_set()
    assert [item["id"] for item in _own(first)] == [mine["id"]]


@pytest.mark.journey("J45.5")
def test_no_workspace_still_names_the_instance(world):
    """Given a caller holding no role. When it reads `GET /me/workspaces` and `GET /system`, then it
    has no workspace, and the system names the instance's product: the default workspace's model's,
    which the caller cannot read itself."""
    _, nobody = _client(world, "No roles")
    assert ok(nobody.api.get("/me/workspaces"))["items"] == []
    product = ok(world.api.get("/model"))["product"]
    named = ok(nobody.api.get("/system"))["product"]
    assert named == {"name": product["name"], "description": product.get("description")}
