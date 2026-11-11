"""The draft outline's element for a diagnostic pointer and its marks (0.10 A4a, D36)."""

import copy

import pytest

from app.engine.model.authoring.outline import build_outline, element_at

DOCUMENT = {
    "applications": [
        {
            "key": "app",
            "objectTypeKeys": ["a", "b"],
            "views": [{"key": "v", "type": "table", "objectTypeKey": "a"}],
            "details": [{"objectTypeKey": "a", "panels": []}],
            "navigation": {"groups": [{"key": "g", "label": "G", "collections": ["a"]}]},
        }
    ],
    "objectTypes": [
        {"key": "a", "name": "A", "attributes": [{"attributeTypeKey": "x"}]},
        {
            "key": "b",
            "name": "B",
            "behavior": {"parentRelationTypeKeys": ["holds"]},
            "attributes": [],
        },
    ],
    "attributeTypes": [{"key": "x", "name": "X", "valueType": "text"}],
    "relationTypes": [
        {"key": "holds", "name": "Holds", "features": {"parentOf": True}},
        {"key": "r", "name": "R"},
    ],
    "objectTypeRelations": [
        {"relationTypeKey": "holds", "fromObjectTypeKey": "a", "toObjectTypeKey": "b"}
    ],
}


@pytest.mark.parametrize(
    ("pointer", "element"),
    [
        ("/objectTypes/a", {"objectType": "a"}),
        ("/objectTypes/1/behavior", {"objectType": "b"}),
        ("/objectTypes/a/attributes/x/required", {"objectType": "a", "attributeType": "x"}),
        ("/objectTypes/a/attributes/0", {"objectType": "a", "attributeType": "x"}),
        ("/attributeTypes/x/validation", {"attributeType": "x"}),
        ("/relationTypes/holds", {"relationType": "holds"}),
        ("/objectTypeRelations/holds/a/b", {"relationType": "holds", "from": "a", "to": "b"}),
        ("/objectTypeRelations/0/cardinality", {"relationType": "holds", "from": "a", "to": "b"}),
        ("/applications/app/views/v/config", {"applicationKey": "app", "view": "v"}),
        ("/applications/app/details/a/panels/0", {"applicationKey": "app", "detail": "a"}),
        (
            "/applications/app/navigation/groups/g/collections/0",
            {"applicationKey": "app", "group": "g"},
        ),
        ("/applications/app/defaultView", {"applicationKey": "app"}),
        ("/release/version", None),
        ("/objectTypes/missing", None),
        ("", None),
    ],
)
def test_a_pointer_names_the_element_it_falls_in(pointer, element):
    assert element_at(DOCUMENT, pointer) == element


def test_marks_follow_the_base_release():
    draft = copy.deepcopy(DOCUMENT)
    draft["objectTypes"][0]["name"] = "A renamed"
    draft["objectTypeRelations"].append(
        {"relationTypeKey": "r", "fromObjectTypeKey": "b", "toObjectTypeKey": "a"}
    )
    draft["objectTypes"].append({"key": "c", "name": "C"})
    outline = build_outline(draft, DOCUMENT)
    marks = {item["key"]: item["mark"] for item in outline["objectTypes"]}
    # a's declaration changed; b starts a new relation; c is not in the base; nothing else moved.
    assert marks == {"a": "changed", "b": "changed", "c": "new"}
    assert [r["mark"] for r in outline["relations"]] == ["released", "new"]
    assert outline["objectTypes"][0]["attributes"][0]["mark"] == "released"
    assert outline["applications"][0]["navigation"]["groups"][0]["mark"] == "released"


def test_without_a_base_every_element_is_new_and_the_tree_follows_containment():
    outline = build_outline(DOCUMENT, None)
    assert {item["mark"] for item in outline["objectTypes"] + outline["relationTypes"]} == {"new"}
    assert outline["applications"][0]["tree"] == [
        {"objectType": "a", "children": [{"objectType": "b", "children": []}]}
    ]
    assert outline["applications"][0]["navigation"]["ungrouped"] == []


def test_a_containment_cycle_keeps_every_type_in_the_tree():
    cyclic = copy.deepcopy(DOCUMENT)
    cyclic["objectTypes"][0]["behavior"] = {"parentRelationTypeKeys": ["holds"]}
    cyclic["objectTypeRelations"].append(
        {"relationTypeKey": "holds", "fromObjectTypeKey": "b", "toObjectTypeKey": "a"}
    )
    tree = build_outline(cyclic, None)["applications"][0]["tree"]
    assert tree[0]["objectType"] == "a"
    assert tree[0]["children"][0]["objectType"] == "b"
    assert tree[0]["children"][0]["children"] == [{"objectType": "a", "children": []}]


def test_an_unreadable_document_is_outlined_empty():
    assert (
        build_outline({"objectTypes": "nonsense", "applications": [1]}, None)["objectTypes"] == []
    )


def test_a_relation_carries_its_uniqueness_scope():
    draft = copy.deepcopy(DOCUMENT)
    draft["objectTypeRelations"][0]["features"] = {"uniqueToAncestorTypeKey": "area"}
    assert build_outline(draft, None)["relations"][0]["uniquePer"] == "area"
    assert "uniquePer" not in build_outline(DOCUMENT, None)["relations"][0]


def test_a_relation_carries_which_records_it_may_choose():
    draft = copy.deepcopy(DOCUMENT)
    criteria = {"to": [{"field": "name", "op": "startsWith", "value": "A"}]}
    draft["objectTypeRelations"][0]["candidates"] = criteria
    (relation,) = build_outline(draft, None)["relations"]
    assert relation["candidates"] == criteria
    assert "candidates" not in build_outline(DOCUMENT, None)["relations"][0]


def test_a_relationships_table_view_carries_its_config():
    draft = copy.deepcopy(DOCUMENT)
    config = {"fromObjectTypeKey": "a", "toObjectTypeKey": "b", "layout": "grid"}
    draft["applications"][0]["views"].append(
        {"key": "rel", "type": "relationTable", "config": config}
    )
    views = {view["key"]: view for view in build_outline(draft, None)["applications"][0]["views"]}
    assert views["rel"]["config"] == config
    assert "config" not in views["v"]


def test_a_consumer_api_written_by_hand_without_its_parts_is_outlined_without_failing():
    """A definition saved through the JSON workbench may lack its key or name, or hold a version that
    is not a number; the outline lists what it can and leaves the rest to the diagnostics (0.10 A4c)."""
    data = {
        "consumerApis": [
            {"name": "No key"},
            {
                "key": "feed",
                "contractVersion": "two",
                "exposes": ["shelf", 3],
                "publicNames": {"shelf": 5},
            },
        ]
    }
    (entry,) = build_outline(data, None)["consumerApis"]
    assert entry["key"] == "feed"
    assert entry["name"] == "feed"
    assert entry["contractVersion"] is None
    assert entry["exposes"] == [{"objectType": "shelf", "publicName": "Shelf"}]
    assert entry["mark"] == "new"


def _matrix(key, relation, row, column, cell):
    return {
        "key": key,
        "name": f"{key} name",
        "type": "relationMatrix",
        "config": {
            "relationTypeKey": relation,
            "direction": "outgoing",
            "rowObjectTypeKey": row,
            "columnObjectTypeKey": column,
            "cellObjectTypeKey": cell,
        },
    }


def _table(key, type_key):
    return {"key": key, "name": key, "type": "table", "objectTypeKey": type_key}


def _contains(parent, child):
    return {"relationTypeKey": "holds", "fromObjectTypeKey": parent, "toObjectTypeKey": child}


BORROWED = {
    "applications": [
        {
            "key": "reference",
            "objectTypeKeys": ["gender", "system", "system-value"],
            "views": [
                _table("genders", "gender"),
                _table("systems", "system"),
                _table("values", "system-value"),
            ],
        },
        {
            "key": "codes",
            "objectTypeKeys": ["gender", "system", "system-value"],
            "views": [
                _table("systems", "system"),
                _matrix("gender-by-system", "maps-to", "gender", "system", "system-value"),
            ],
        },
        {
            "key": "translations",
            "objectTypeKeys": ["gender", "language", "group", "translation"],
            "views": [
                _table("genders", "gender"),
                _matrix(
                    "in-every-language", "has-translation", "gender", "language", "translation"
                ),
            ],
        },
        {
            "key": "catalogue",
            "objectTypeKeys": [
                "category",
                "system",
                "system-value",
                "brand",
                "location",
                "language",
                "group",
                "translation",
            ],
            "views": [
                _table("categories", "category"),
                _matrix("offered", "offered-at", "category", "brand", "location"),
                _matrix("named", "has-translation", "category", "language", "translation"),
            ],
        },
    ],
    "objectTypes": [
        {
            "key": key,
            "name": key.title(),
            "behavior": {"parentRelationTypeKeys": ["holds"]}
            if key in ("group", "translation")
            else {},
        }
        for key in (
            "gender",
            "system",
            "system-value",
            "language",
            "group",
            "translation",
            "category",
            "brand",
            "location",
        )
    ],
    "relationTypes": [
        {"key": "holds", "name": "Holds", "features": {"parentOf": True}},
        {"key": "maps-to", "name": "Maps to"},
        {"key": "has-translation", "name": "Has translation"},
        {"key": "offered-at", "name": "Offered at"},
    ],
    "objectTypeRelations": [_contains("language", "group"), _contains("group", "translation")],
}


def _roles(outline, app):
    entry = next(item for item in outline["applications"] if item["key"] == app)
    return (
        entry["ownTypes"],
        {item["objectType"]: item for item in entry["borrowed"]},
        entry["unused"],
    )


def test_a_type_an_application_lists_for_a_relation_view_is_borrowed_from_its_home():
    outline = build_outline(BORROWED, None)
    own, borrowed, unused = _roles(outline, "codes")
    assert own == ["system"]
    gender = borrowed["gender"]
    assert gender["home"] == "reference"
    (use,) = gender["uses"]
    assert use == {
        "view": "gender-by-system",
        "viewName": "gender-by-system name",
        "viewType": "relationMatrix",
        "role": "rows",
        "relationType": "maps-to",
        "relationName": "Maps to",
    }
    assert borrowed["system-value"]["uses"][0]["role"] == "cells"
    assert unused == []


def test_columns_cells_and_the_containment_link_between_them_are_borrowed_and_unused_types_are_listed():
    outline = build_outline(BORROWED, None)
    own, borrowed, unused = _roles(outline, "catalogue")
    assert own == ["category"]
    roles = {key: [use["role"] for use in item["uses"]] for key, item in borrowed.items()}
    assert roles["brand"] == ["columns"] and roles["location"] == ["cells"]
    assert roles["group"] == ["link"]
    assert roles["language"] == ["columns"] and roles["translation"] == ["cells"]
    assert borrowed["translation"]["home"] is None
    assert unused == ["system", "system-value"]
    entry = next(item for item in outline["applications"] if item["key"] == "catalogue")
    assert entry["borrowedTree"] == [
        {"objectType": "brand", "children": []},
        {"objectType": "location", "children": []},
        {
            "objectType": "language",
            "children": [
                {"objectType": "group", "children": [{"objectType": "translation", "children": []}]}
            ],
        },
    ]


def test_a_type_own_in_two_applications_has_the_first_as_its_home_and_the_type_entry_lists_the_rest():
    outline = build_outline(BORROWED, None)
    gender = next(item for item in outline["objectTypes"] if item["key"] == "gender")
    assert gender["home"] == "reference"
    assert gender["ownIn"] == ["reference", "translations"]
    assert [(item["application"], item["uses"][0]["role"]) for item in gender["borrowedIn"]] == [
        ("codes", "rows")
    ]
    assert (
        next(item for item in outline["objectTypes"] if item["key"] == "language")["home"] is None
    )
