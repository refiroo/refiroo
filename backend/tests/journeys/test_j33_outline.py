"""J33 — Design a model in the editor (USER_JOURNEYS.md): the draft's outline (0.10 A4a, D36).

The editor reads a draft's structure from the server: applications with their types in their
containment tree, attributes, relation types, the relations allowed between types and navigation
groups, each element marked ``new``, ``changed`` or ``released`` against the draft's base release,
and the compiler's diagnostics tied to the element they concern. The tests name structures of the
configuration (``R``, ``K``) and elements they create under ``j33-`` keys, never a configuration's keys.
"""

from typing import Any

import pytest
from scenario import ok, refused
from test_j33_operations import _apply, _draft_of_active, _empty_draft

DISABLED = {"MODEL_ADMIN_MUTATIONS_ENABLED": "false"}


def _outline(world, draft: dict[str, Any]) -> dict[str, Any]:
    return ok(world.api.get(f"/model-drafts/{draft['id']}/outline"))


def _by_key(items: list[dict[str, Any]], key: str, field: str = "key") -> dict[str, Any]:
    return next(item for item in items if item[field] == key)


def _nodes(tree: list[dict[str, Any]]):
    for node in tree:
        yield node
        yield from _nodes(node["children"])


@pytest.mark.journey("J33.2")
@pytest.mark.structures("R", "K")
def test_the_outline_of_a_draft_of_the_active_release_marks_what_is_new(world):
    """Given a draft of the active release. When a type is added under R with a new attribute and a
    relation from it to K is allowed. Then the outline shows the new type under R as new, R as
    changed, K and R's attributes as released, the new relation among the allowed relations, and the
    outline's version is the step's."""
    draft = _draft_of_active(world)
    r_key, k_key, r_app = world.key("R"), world.key("K"), world.app("R")
    answer = ok(
        _apply(
            world,
            draft,
            draft["version"],
            {
                "kind": "addObjectType",
                "applicationKey": r_app,
                "key": "j33-note",
                "name": "Note",
                "pluralName": "Notes",
                "parent": {
                    "objectTypes": [r_key],
                    "relationType": {"key": "j33-has-note", "name": "Has note", "reverseName": "Note of"},
                },
            },
            {"kind": "addAttributeType", "key": "j33-text", "name": "Note text", "valueType": "text"},
            {"kind": "attachAttribute", "objectType": "j33-note", "attributeType": "j33-text"},
            {"kind": "addRelationType", "key": "j33-cites", "name": "Cites", "reverseName": "Cited by"},
            {"kind": "allowRelation", "relationType": "j33-cites", "from": "j33-note", "to": k_key},
        )
    )
    outline = _outline(world, draft)
    assert outline["version"] == answer["version"]
    assert outline["baseReleaseId"] == draft["baseReleaseId"]

    note = _by_key(outline["objectTypes"], "j33-note")
    assert note["mark"] == "new"
    assert note["parents"] == [r_key]
    assert [(a["attributeType"], a["mark"]) for a in note["attributes"]] == [("j33-text", "new")]
    r_type = _by_key(outline["objectTypes"], r_key)
    assert r_type["mark"] == "changed"
    assert r_type["attributes"] and all(a["mark"] == "released" for a in r_type["attributes"])
    assert _by_key(outline["objectTypes"], k_key)["mark"] == "released"

    application = _by_key(outline["applications"], r_app)
    r_nodes = [node for node in _nodes(application["tree"]) if node["objectType"] == r_key]
    assert r_nodes and all("j33-note" in [c["objectType"] for c in node["children"]] for node in r_nodes)

    cites = [r for r in outline["relations"] if r["relationType"] == "j33-cites"]
    assert cites == [
        {
            "relationType": "j33-cites",
            "from": "j33-note",
            "to": k_key,
            "cardinality": cites[0]["cardinality"],
            "required": False,
            "containment": False,
            "mark": "new",
        }
    ]
    assert _by_key(outline["relationTypes"], "j33-has-note")["containment"] is True
    assert {r["mark"] for r in outline["relations"] if r["from"] != "j33-note" and r["to"] != "j33-note"} == {
        "released"
    }


@pytest.mark.journey("J33.1")
@pytest.mark.structures("A1")
def test_the_outline_of_a_draft_built_from_empty_holds_what_the_request_built(world):
    """Given an empty draft. When one request adds an application with a top-level type, a type
    under it, a relation between them and a group holding both. Then the outline's tree, groups and
    allowed relations are what the request built, every element new."""
    draft = _empty_draft(world)
    ok(
        _apply(
            world,
            draft,
            draft["version"],
            {"kind": "addApplication", "name": "J33 Storage Rooms"},
            {"kind": "addObjectType", "applicationKey": "j33-storage-rooms", "name": "J33 Shelf", "parent": None},
            {
                "kind": "addObjectType",
                "applicationKey": "j33-storage-rooms",
                "name": "J33 Item",
                "parent": {
                    "objectTypes": ["j33-shelf"],
                    "relationType": {"key": "j33-holds", "name": "Holds item", "reverseName": "On shelf"},
                },
            },
            {"kind": "addRelationType", "name": "J33 Replaces", "reverseName": "J33 Replaced by"},
            {"kind": "allowRelation", "relationType": "j33-replaces", "from": "j33-item", "to": "j33-item"},
            {"kind": "addNavigationGroup", "applicationKey": "j33-storage-rooms", "label": "J33 Storage"},
            {"kind": "placeCollection", "applicationKey": "j33-storage-rooms", "collection": "j33-shelf", "group": "j33-storage"},
        )
    )
    outline = _outline(world, draft)
    (application,) = outline["applications"]
    assert application["key"] == "j33-storage-rooms"
    assert application["tree"] == [
        {"objectType": "j33-shelf", "children": [{"objectType": "j33-item", "children": []}]}
    ]
    assert application["navigation"] == {
        "groups": [
            {"key": "j33-storage", "label": "J33 Storage", "collapsed": False, "collections": ["j33-shelf"], "mark": "new"}
        ],
        "ungrouped": ["j33-item"],
    }
    assert sorted((r["relationType"], r["from"], r["to"], r["containment"]) for r in outline["relations"]) == [
        ("j33-holds", "j33-shelf", "j33-item", True),
        ("j33-replaces", "j33-item", "j33-item", False),
    ]
    marks = {application["mark"]}
    for collection in ("objectTypes", "relationTypes", "relations"):
        marks |= {item["mark"] for item in outline[collection]}
    assert marks == {"new"}


@pytest.mark.journey("J33", "J08")
@pytest.mark.structures("A1")
def test_a_draft_left_invalid_between_steps_is_outlined_with_its_diagnostics(world):
    """Given an empty draft. When an application is added alone. Then the outline answers with the
    application and the step's diagnostics, each carrying the element its pointer falls in."""
    draft = _empty_draft(world)
    answer = ok(_apply(world, draft, draft["version"], {"kind": "addApplication", "name": "J33 Empty"}))
    outline = _outline(world, draft)
    assert [a["key"] for a in outline["applications"]] == ["j33-empty"]
    assert outline["valid"] is False
    assert [{k: v for k, v in d.items() if k != "element"} for d in outline["diagnostics"]] == answer["diagnostics"]
    assert all("element" in d for d in outline["diagnostics"])
    in_application = [d for d in outline["diagnostics"] if d["path"].startswith("/applications/j33-empty")]
    assert in_application
    assert all(d["element"]["applicationKey"] == "j33-empty" for d in in_application)


@pytest.mark.journey("J33")
@pytest.mark.structures("A1")
def test_the_outline_of_an_unknown_draft_is_not_found(world):
    refused(
        world.api.get("/model-drafts/00000000-0000-4000-8000-000000000000/outline"), 404, "MODEL_DRAFT_NOT_FOUND"
    )


@pytest.mark.journey("J33", "J08.7")
@pytest.mark.structures("A1")
@pytest.mark.settings(**DISABLED)
def test_with_model_administration_disabled_the_outline_is_absent(world):
    response = world.api.get("/model-drafts/00000000-0000-4000-8000-000000000000/outline")
    assert response.status_code == 404, response.text
    assert "MODEL_DRAFT_NOT_FOUND" not in response.text
