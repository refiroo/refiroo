"""J33 — Design a model in the editor (USER_JOURNEYS.md).

J33.9 (0.10 N1): navigation groups declared on an application in schema 0.10. A group names the
application's collections, the source types of its views (ADR-029), which the tests read from the
configuration's view declarations, never from its keys.
"""

import copy
from typing import Any

import pytest
from scenario import ok, refused


def _collections(application: dict[str, Any]) -> list[str]:
    """The application's collections in sidebar order: each view's source type, first seen first."""
    result: list[str] = []
    for view in application["views"]:
        config = view.get("config", {})
        if view["type"] == "table":
            source = view["objectTypeKey"]
        elif view["type"] == "relationMatrix":
            source = config["rowObjectTypeKey"]
        elif view["type"] == "tree":
            source = config["rootObjectTypeKeys"][0]
        elif view["type"] == "relationTable" or config["direction"] == "outgoing":
            source = config["fromObjectTypeKey"]
        else:
            source = config["toObjectTypeKey"]
        if source not in result:
            result.append(source)
    return result


def _application(model: dict[str, Any], key: str) -> dict[str, Any]:
    return next(item for item in model["applications"] if item["key"] == key)


def _grouped(world, groups: list[dict[str, Any]] | None = None, version: str = "0.10"):
    """The configuration's model at ``version`` with ``groups`` on A1 (by default one group holding
    A1's first two collections, folded), and the pointer of A1's navigation."""
    model = copy.deepcopy(world.configuration.model)
    model["schemaVersion"] = version
    model["release"]["version"] += "-groups"
    a1 = _application(model, world.key("A1"))
    collections = _collections(a1)
    assert len(collections) >= 2, "A1 needs two collections to group"
    if groups is None:
        groups = [
            {"key": "lists", "label": "Lists", "collections": collections[:2], "collapsed": True}
        ]
    a1["navigation"] = {"groups": groups}
    return model, f"/applications/{world.key('A1')}/navigation"


def _diagnostics(world, model: dict[str, Any]) -> list[dict[str, Any]]:
    answer = ok(world.api.post("/model-validations", {"model": model}))
    assert answer["valid"] is False
    return answer["diagnostics"]


def _install(world, model: dict[str, Any]) -> dict[str, Any]:
    draft = ok(world.api.post("/model-drafts", {"name": "Groups", "model": model}), 201)
    return ok(
        world.api.post(
            f"/model-drafts/{draft['id']}/installation", {"expectedVersion": draft["version"]}
        ),
        201,
    )


@pytest.mark.journey("J33.9")
@pytest.mark.structures("A1", "A2")
def test_declared_groups_are_installed_and_served_as_written(world):
    """Given A1 at schema 0.10 with a folded group of two of its collections, its others ungrouped.
    When the model is validated, installed and activated. Then it is valid, the served model holds
    A1's navigation exactly as written, and A2 has no navigation member."""
    model, _ = _grouped(world)
    assert ok(world.api.post("/model-validations", {"model": model}))["valid"] is True
    release = _install(world, model)
    ok(world.activate(release["id"]))

    served = ok(world.api.get("/model"))
    assert served["schemaVersion"] == "0.10"
    written = _application(model, world.key("A1"))["navigation"]
    assert _application(served, world.key("A1"))["navigation"] == written
    assert "navigation" not in _application(served, world.key("A2"))


@pytest.mark.journey("J33.9")
@pytest.mark.structures("A1", "A2")
def test_a_group_entry_must_be_a_collection_of_its_application(world):
    """Given A1's group naming a collection of A2, or a key that is no type. When validated. Then
    each is refused INVALID_REFERENCE at the entry's pointer."""
    other = _collections(_application(world.configuration.model, world.key("A2")))[0]
    own = _collections(_application(world.configuration.model, world.key("A1")))
    assert other not in own
    for entry in (other, "no-such-collection"):
        model, pointer = _grouped(
            world, [{"key": "lists", "label": "Lists", "collections": [own[0], entry]}]
        )
        (diagnostic,) = [d for d in _diagnostics(world, model) if d["severity"] == "error"]
        assert diagnostic["code"] == "INVALID_REFERENCE", diagnostic
        assert diagnostic["path"] == f"{pointer}/groups/lists/collections/1"


@pytest.mark.journey("J33.9")
@pytest.mark.structures("A1")
def test_a_collection_stands_in_one_group_and_group_keys_are_unique(world):
    """Given A1 with one collection in two groups, or two groups with one key. When validated. Then
    the first is refused INVALID_MODEL at the second group's entry, the second DUPLICATE_KEY at the
    second group."""
    own = _collections(_application(world.configuration.model, world.key("A1")))
    model, pointer = _grouped(
        world,
        [
            {"key": "first", "label": "First", "collections": [own[0]]},
            {"key": "second", "label": "Second", "collections": [own[1], own[0]]},
        ],
    )
    (diagnostic,) = _diagnostics(world, model)
    assert diagnostic["code"] == "INVALID_MODEL", diagnostic
    assert diagnostic["path"] == f"{pointer}/groups/second/collections/1"

    model, pointer = _grouped(
        world,
        [
            {"key": "lists", "label": "First", "collections": [own[0]]},
            {"key": "lists", "label": "Second", "collections": [own[1]]},
        ],
    )
    (diagnostic,) = _diagnostics(world, model)
    assert diagnostic["code"] == "DUPLICATE_KEY", diagnostic
    assert diagnostic["path"] == f"{pointer}/groups/lists"


@pytest.mark.journey("J33.9")
@pytest.mark.structures("A1")
def test_navigation_has_its_own_shape(world):
    """Given a navigation group with a member groups do not have. When validated. Then it is refused
    at the unknown member; compiled as a draft, it answers with no changes (the list present); the
    model does not install."""
    model, _ = _grouped(world)
    _application(model, world.key("A1"))["navigation"]["groups"][0]["colour"] = "red"
    (diagnostic,) = _diagnostics(world, model)
    assert diagnostic["path"].startswith("/applications/") and diagnostic["path"].endswith(
        "/navigation/groups/0/colour"
    ), diagnostic
    draft = ok(world.api.post("/model-drafts", {"name": "Shape", "model": model}), 201)
    # Compiled, the invalid draft answers with every list present: `changes` empty, not left out
    # (the editor's Load dialog read its length and blanked the page, reported 2026-10-14).
    compiled = ok(
        world.api.post(
            f"/model-drafts/{draft['id']}/compile", {"expectedVersion": draft["version"]}
        )
    )
    assert compiled["valid"] is False and compiled["changes"] == []
    refused(
        world.api.post(
            f"/model-drafts/{draft['id']}/installation", {"expectedVersion": draft["version"]}
        ),
        422,
        "INVALID_MODEL",
    )
