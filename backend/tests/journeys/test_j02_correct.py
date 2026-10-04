"""J02 — Correct a record (USER_JOURNEYS.md)."""

import json

import pytest
from scenario import W1, W3, ok, refused


def _history(world, structure, object_id, **params):
    return ok(world.api.get(f"/objects/{world.key(structure)}/{object_id}/history", **params))[
        "items"
    ]


@pytest.mark.journey("J02")
@pytest.mark.structures("R", "R.n")
def test_correct_a_live_record_beside_an_open_change_set(world):
    """Given live R record r at version v and an unrelated open change set. When r's name and n are
    saved against v. Then r answers v+1 with the new values, keeps its identity, place and
    relationships, and its history's newest entry is the update; the publications and the change set
    are untouched; the same edit in a retired workspace is refused."""
    r = world.made("R", "Before", values={"R.n": 1})
    cs1 = world.change_set(name="Unrelated")
    publications = ok(world.api.get(f"/workspaces/{W1}/publications"))["items"]

    updated = ok(world.update("R", r["id"], r["version"], name="After", values={"R.n": 2}))
    assert updated["version"] == r["version"] + 1 and updated["name"] == "After"
    assert world.value(updated, "R.n") == 2
    live = world.record("R", r["id"])
    assert (live["id"], live["parentObjectId"], live["name"]) == (
        r["id"],
        r["parentObjectId"],
        "After",
    )
    newest = _history(world, "R", r["id"])[0]
    assert newest["action"] == "updated" and world.key("R.n") in newest["attributeTypeKeys"]

    assert ok(world.api.get(f"/workspaces/{W1}/publications"))["items"] == publications
    assert world.current(cs1)["version"] == cs1["version"]
    assert world.record("R", r["id"], changeSetId=cs1["id"])["name"] == "Before"

    closed = world.record("R", world.ids["w3r"], workspaceKey=W3)
    refused(
        world.update("R", closed["id"], closed["version"], name="Reopened"),
        409,
        "WORKSPACE_RETIRED",
    )


@pytest.mark.journey("J02.1")
@pytest.mark.structures("H", "K", "Bnn")
def test_rename_keeps_identity_place_and_relationships(world):
    """Given H record h3 with descendants to level 6 and a relationship to K. When it is renamed.
    Then it keeps its ID, parent and relationship; each descendant's path shows the new name at
    level 3, and the descendants' versions are unchanged."""
    h3 = world.ids["h3"]
    relation = ok(world.relate("Bnn", h3, world.ids["k02"], {"Bnn.weight": 1}), 201)
    descendants = {lvl: world.record("H", world.ids[f"h{lvl}"]) for lvl in range(4, 7)}
    before = world.record("H", h3)

    after = ok(world.update("H", h3, before["version"], name="Renamed level 3"))
    assert (after["id"], after["parentObjectId"]) == (h3, before["parentObjectId"])
    related = ok(world.api.get("/relations", objectId=h3, relationTypeKey=world.key("Bnn")))[
        "items"
    ]
    assert [item["relation"]["id"] for item in related] == [relation["id"]]
    for old in descendants.values():
        now = world.record("H", old["id"])
        assert now["path"][2] == {**old["path"][2], "name": "Renamed level 3"}
        assert now["version"] == old["version"]


@pytest.mark.journey("J02.2")
@pytest.mark.structures("R")
def test_the_second_of_two_writers_is_refused_with_the_current_version(world):
    """Given writers A and B both read R record r at version v. When A saves, then B saves against v.
    Then B is refused with the record's current version, r keeps A's content and its history holds
    one update."""
    r = world.made("R", "Shared")
    ok(world.update("R", r["id"], r["version"], name="Writer A"))

    error = refused(
        world.update("R", r["id"], r["version"], name="Writer B"), 409, "VERSION_CONFLICT"
    )
    assert error["details"]["currentVersion"] == r["version"] + 1
    current = world.record("R", r["id"])
    assert (current["name"], current["version"]) == ("Writer A", r["version"] + 1)
    assert [e["action"] for e in _history(world, "R", r["id"])] == ["updated", "created"]


@pytest.mark.journey("J02.3")
@pytest.mark.structures("R", "R.n", "R.b")
def test_zero_and_false_stay_values(world):
    """Given R record r with n 5 and b true. When it is changed to 0 and false and read live, in a
    change set and after publishing. Then every read answers 0 and false, and a not-null filter
    finds it."""
    r = world.made("R", "Falsy", values={"R.n": 5, "R.b": True})
    ok(world.update("R", r["id"], r["version"], values={"R.n": 0, "R.b": False}))
    change_set = world.change_set()
    publication = world.publish(world.change_set())

    contexts = ({}, {"changeSetId": change_set["id"]}, {"publicationId": publication["id"]})
    for context in contexts:
        record = world.record("R", r["id"], **context)
        assert world.value(record, "R.n") == 0 and world.value(record, "R.n") is not False
        assert world.value(record, "R.b") is False
    n = world.key("R.n")
    page = ok(
        world.api.get(
            f"/objects/{world.key('R')}", search="Falsy", **{f"filter.{n}.isNull": "false"}
        )
    )
    assert [item["id"] for item in page["items"]] == [r["id"]]


@pytest.mark.journey("J02.4")
@pytest.mark.structures("R", "R.n", "R.dt")
def test_one_value_through_its_own_resource(world):
    """Given R record r with n stored and no date. When the date is added, n changed and the date
    removed, each against the record's version. Then adding and changing answer the whole record at
    its new version, removing answers nothing and the value is then not found; adding a stored value,
    changing an unstored one and a stale version are refused and change nothing."""
    r = world.made("R", "Single values", values={"R.n": 3})
    base = f"/objects/{world.key('R')}/{r['id']}/attributes"
    n, dt = f"{base}/{world.key('R.n')}", f"{base}/{world.key('R.dt')}"

    added = ok(world.api.post(dt, {"value": "2026-02-02", "expectedVersion": r["version"]}), 201)
    assert added["version"] == r["version"] + 1 and world.value(added, "R.dt") == "2026-02-02"
    changed = ok(world.api.patch(n, {"value": 4, "expectedVersion": added["version"]}))
    assert changed["version"] == added["version"] + 1 and world.value(changed, "R.n") == 4
    assert world.api.delete(dt, expectedVersion=changed["version"]).status_code == 204
    refused(world.api.get(dt), 404, "ATTRIBUTE_NOT_FOUND")
    version = world.record("R", r["id"])["version"]

    refused(
        world.api.post(n, {"value": 9, "expectedVersion": version}), 409, "ATTRIBUTE_ALREADY_EXISTS"
    )
    refused(
        world.api.patch(dt, {"value": "2026-03-03", "expectedVersion": version}),
        404,
        "ATTRIBUTE_NOT_FOUND",
    )
    refused(
        world.api.patch(n, {"value": 9, "expectedVersion": version - 1}), 409, "VERSION_CONFLICT"
    )
    final = world.record("R", r["id"])
    assert final["version"] == version and world.value(final, "R.n") == 4


@pytest.mark.journey("J02.5")
@pytest.mark.structures("R", "R.u", "R.n", "R.q", "R.ro", "R.x1", "R.x2")
def test_attribute_rules_refuse_and_name_the_rule(world):
    """Given R records r1 holding u "X" and r2 storing only x1 of its at-least-one-of pair. When r2
    takes n below its minimum, u "X", an undeclared attribute, loses its required q, loses x1, or
    changes its read-only value. Then each is refused with its rule's code naming the attribute, and
    r2 keeps its version and values."""
    world.made("R", "Holder", values={"R.u": "X"})
    r2 = world.made("R", "Checked", values={"R.n": 10})
    base = f"/objects/{world.key('R')}/{r2['id']}/attributes"

    attempts = [
        (
            world.update("R", r2["id"], r2["version"], values={"R.n": -1}),
            422,
            "ATTRIBUTE_BELOW_MINIMUM",
            "R.n",
        ),
        (
            world.update("R", r2["id"], r2["version"], values={"R.u": "X"}),
            409,
            "DUPLICATE_ATTRIBUTE_VALUE",
            "R.u",
        ),
        (
            world.update("R", r2["id"], r2["version"], values={"no-such-attribute": 1}),
            422,
            "UNKNOWN_ATTRIBUTES",
            None,
        ),
        (
            world.api.delete(f"{base}/{world.key('R.q')}", expectedVersion=r2["version"]),
            422,
            "CANNOT_DELETE_REQUIRED_ATTRIBUTE",
            "R.q",
        ),
        (
            world.api.delete(f"{base}/{world.key('R.x1')}", expectedVersion=r2["version"]),
            422,
            "OBJECT_ATTRIBUTE_RULE_VIOLATION",
            "R.x1",
        ),
        (
            world.update("R", r2["id"], r2["version"], values={"R.ro": "edited"}),
            422,
            "READ_ONLY_ATTRIBUTES",
            "R.ro",
        ),
    ]
    for response, status, code, structure in attempts:
        error = refused(response, status, code)
        names = (
            ["no-such-attribute"]
            if structure is None
            else [world.key(structure), world.attribute_name(structure)]
        )
        assert any(name in json.dumps(error) for name in names), error
    after = world.record("R", r2["id"])
    assert after["version"] == r2["version"] and after["attributes"] == r2["attributes"]
