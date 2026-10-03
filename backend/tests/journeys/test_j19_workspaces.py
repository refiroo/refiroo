"""J19 — Administer workspaces (USER_JOURNEYS.md).

J19.5 (a workspace's activity) is planned (D-5).
"""

import pytest
from scenario import W1, W2, ok, refused


def _workspace(world, key):
    return ok(world.api.get(f"/workspaces/{key}"))


def _create(world, key, label=None):
    return world.api.post("/workspaces", {"key": key, "label": label or key.title()})


def _default(world, key, version=None):
    state = ok(world.api.get("/workspace-runtime-state"))
    return world.api.patch(
        "/workspace-runtime-state",
        {
            "defaultWorkspaceKey": key,
            "expectedVersion": state["version"] if version is None else version,
        },
    )


def _retire(world, key):
    return world.api.patch(
        f"/workspaces/{key}",
        {"expectedVersion": _workspace(world, key)["version"], "status": "retired"},
    )


def _delete(world, key, version=None):
    version = _workspace(world, key)["version"] if version is None else version
    return world.api.delete(f"/workspaces/{key}", expectedVersion=version)


@pytest.mark.journey("J19")
@pytest.mark.structures("R")
def test_create_relabel_choose_the_default_retire_and_delete(world):
    """When a workspace is created (twice), relabelled, another made the default, W1 retired and
    written to, the default retired, and an empty workspace deleted and created again. Then the
    second create is refused; the key stays and the label changes; reads without a workspace use the
    new default while W1 can still be named; W1 retired is readable and refuses writes; the default
    cannot be retired; the deleted key can be created again. Deleting is refused, changing nothing,
    for the default, a workspace ever published, one holding a change set, a stale version and an
    unknown key, and single reads say whether and why a workspace can be deleted."""
    ok(_create(world, "fresh-site", "Fresh"), 201)
    refused(_create(world, "fresh-site"), 409, "workspace_already_exists")
    fresh = _workspace(world, "fresh-site")
    relabelled = ok(
        world.api.patch(
            "/workspaces/fresh-site",
            {"expectedVersion": fresh["version"], "label": "Fresh, relabelled"},
        )
    )
    assert (relabelled["key"], relabelled["label"]) == ("fresh-site", "Fresh, relabelled")

    w1_record = world.made("R", "Lives in W1")
    w2_record = world.made("R", "Lives in W2", workspace=W2)
    ok(_default(world, W2))
    r_type = world.key("R")
    assert w2_record["id"] in {i["id"] for i in ok(world.api.get(f"/objects/{r_type}"))["items"]}
    named = ok(world.api.get(f"/objects/{r_type}", workspaceKey=W1))["items"]
    assert w1_record["id"] in {i["id"] for i in named}

    ok(_retire(world, W1))
    assert world.record("R", w1_record["id"], workspaceKey=W1)["id"] == w1_record["id"]
    refused(
        world.update("R", w1_record["id"], w1_record["version"], name="Too late"),
        409,
        "workspace_retired",
    )
    refused(_retire(world, W2), 409, "default_workspace_cannot_be_retired")
    assert _delete(world, "fresh-site").status_code == 204
    ok(_create(world, "fresh-site"), 201)

    ok(_create(world, "published-site"), 201)
    world.made("R", "Published", workspace="published-site")
    publication = world.publish(
        world.change_set(workspace="published-site"), workspace="published-site"
    )
    assert world.api.post(f"/publications/{publication['id']}/withdrawal").status_code == 204
    ok(_create(world, "staged-site"), 201)
    world.change_set(workspace="staged-site")

    refused(_delete(world, W2), 409, "workspace_is_default")
    refused(_delete(world, "published-site"), 409, "workspace_has_publications")
    error = refused(_delete(world, "staged-site"), 409, "workspace_not_empty")
    assert (error["details"]["objectCount"], error["details"]["changeSetCount"]) == (0, 1)
    refused(
        _delete(world, "fresh-site", version=_workspace(world, "fresh-site")["version"] + 1),
        409,
        "version_conflict",
    )
    refused(_delete(world, "nowhere", version=1), 404, "workspace_not_found")
    blocked = {
        key: (_workspace(world, key)["deletable"], _workspace(world, key).get("deleteBlockedBy"))
        for key in (W2, "published-site", "staged-site", "fresh-site")
    }
    assert blocked == {
        W2: (False, "default"),
        "published-site": (False, "published"),
        "staged-site": (False, "notEmpty"),
        "fresh-site": (True, None),
    }


@pytest.mark.journey("J19.1")
@pytest.mark.structures("R")
def test_two_administrators_change_the_default_from_the_same_version(world):
    """Given administrators A and B who read the runtime state at version v. When A makes W2 the
    default with v, then B another workspace with v. Then B is refused and W2 is the default."""
    ok(_create(world, "third-site"), 201)
    version = ok(world.api.get("/workspace-runtime-state"))["version"]
    ok(_default(world, W2, version))
    refused(_default(world, "third-site", version), 409, "version_conflict")
    assert ok(world.api.get("/workspace-runtime-state"))["defaultWorkspaceKey"] == W2


@pytest.mark.journey("J19.2")
@pytest.mark.structures("R")
def test_retirement_beside_a_live_and_a_change_set_write(world):
    """Given actor A's live write and actor C's change-set write in W2 in flight with actor B's
    retirement of W2, all at once. Then the retirement succeeds without a deadlock; each write either
    committed before it or is refused as retired and saves nothing; later live and change-set writes
    are refused. (Which order PostgreSQL grants is not the test's to choose; both orders are checked
    as the journey's guarantee.)"""
    live = world.made("R", "Live in W2", workspace=W2)
    staged = world.made("R", "Staged in W2", workspace=W2)
    cs = world.change_set(workspace=W2)
    in_cs = world.record("R", staged["id"], changeSetId=cs["id"])
    c_body = {
        "name": "Written by C",
        "expectedVersion": in_cs["version"],
        "changeSetId": cs["id"],
        "expectedChangeSetVersion": world.current(cs)["version"],
    }
    retire = {"expectedVersion": _workspace(world, W2)["version"], "status": "retired"}

    a, b, c = world.race(
        W2,
        lambda: world.update("R", live["id"], live["version"], name="Written by A"),
        lambda: world.api.patch(f"/workspaces/{W2}", retire),
        lambda: world.api.patch(f"/objects/{world.key('R')}/{staged['id']}", c_body),
    )
    ok(b)
    if a.status_code == 200:
        assert world.record("R", live["id"], workspaceKey=W2)["name"] == "Written by A"
    else:
        refused(a, 409, "workspace_retired")
        assert world.record("R", live["id"], workspaceKey=W2)["name"] == "Live in W2"
    if c.status_code == 200:
        assert world.record("R", staged["id"], changeSetId=cs["id"])["name"] == "Written by C"
    else:
        refused(c, 409, "workspace_retired")
    current = world.record("R", live["id"], workspaceKey=W2)
    refused(
        world.update("R", live["id"], current["version"], name="After"), 409, "workspace_retired"
    )
    refused(world.create("R", "After", change_set=world.current(cs)), 409, "workspace_retired")


@pytest.mark.journey("J19.3")
@pytest.mark.structures("R")
def test_search_and_page_the_workspace_catalogue(world):
    """When workspaces sharing a label are searched two at a time, by status, and a cursor reused with
    another search. Then the pages hold only matching active workspaces by default, only retired ones
    or both on request; a retired workspace's own read works; the reused cursor is refused."""
    for key in ("branch-a", "branch-b", "branch-c", "branch-d"):
        ok(_create(world, key, f"Branch {key[-1]}"), 201)
    ok(_retire(world, "branch-d"))

    def listed(**params):
        keys, cursor = [], None
        while True:
            page = ok(
                world.api.get("/workspaces", search="Branch", pageSize=2, cursor=cursor, **params)
            )
            keys += [item["key"] for item in page["items"]]
            cursor = page.get("nextCursor")
            if not cursor:
                return keys

    assert sorted(listed()) == ["branch-a", "branch-b", "branch-c"]
    assert listed(status="retired") == ["branch-d"]
    assert sorted(listed(status="all")) == ["branch-a", "branch-b", "branch-c", "branch-d"]
    assert _workspace(world, "branch-d")["status"] == "retired"
    first = ok(world.api.get("/workspaces", search="Branch", pageSize=2))
    refused(
        world.api.get("/workspaces", search="Other", pageSize=2, cursor=first["nextCursor"]),
        422,
        "invalid_cursor",
    )


@pytest.mark.journey("J19.4")
@pytest.mark.structures("R")
@pytest.mark.settings(WORKSPACE_ADMIN_MUTATIONS_ENABLED="false")
def test_workspace_administration_disabled(world):
    """Given workspace administration disabled. When the catalogue is read, workspaces created,
    relabelled, deleted and the default switched, and a change set used in W1. Then reads answer;
    the capabilities say administration is off with the setting's name; the changing routes are
    absent (405 where the path still has a read, 404 where it has none); the change set workflow
    works."""
    assert ok(world.api.get("/workspaces"))["items"]
    capabilities = ok(world.api.get("/capabilities"))["workspaceAdmin"]
    assert capabilities == {
        "manageWorkspaces": False,
        "setting": "WORKSPACE_ADMIN_MUTATIONS_ENABLED",
    }
    assert _create(world, "not-allowed").status_code == 405
    assert (
        world.api.patch(f"/workspaces/{W2}", {"expectedVersion": 1, "label": "x"}).status_code
        == 405
    )
    assert world.api.delete(f"/workspaces/{W2}", expectedVersion=1).status_code == 405
    assert (
        world.api.patch(
            "/workspace-runtime-state", {"defaultWorkspaceKey": W2, "expectedVersion": 1}
        ).status_code
        == 405
    )

    record = world.made("R", "Through a change set")
    cs = world.change_set()
    staged = world.record("R", record["id"], changeSetId=cs["id"])
    ok(
        world.api.patch(
            f"/objects/{world.key('R')}/{record['id']}",
            {
                "name": "Published anyway",
                "expectedVersion": staged["version"],
                "changeSetId": cs["id"],
                "expectedChangeSetVersion": world.current(cs)["version"],
            },
        )
    )
    world.publish(cs)
    assert world.record("R", record["id"])["name"] == "Published anyway"
