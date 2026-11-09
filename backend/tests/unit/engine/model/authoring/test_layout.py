"""``engine/model/authoring/layout.py``: D35's ``order`` kept in step with list position."""

import copy
import json
from pathlib import Path

import pytest

from app.engine.model.authoring.document import Document, Refusal
from app.engine.model.authoring.kinds import Context, apply_operation
from app.engine.model.authoring.layout import detail_page, keep_order
from app.engine.model.compiler import compile_model

ROOT = Path(__file__).resolve().parents[6]
# The guide's example model, and the page the rule gives its stop type: the frontend's undeclared
# page is checked against the same file (frontend/src/model/defaults.test.ts).
EXAMPLE = json.loads((ROOT / "guide/samples/model.json").read_text())
STOP_PAGE = ROOT / "frontend/src/model/stop-page.fixture.json"


def _orders(document: Document) -> list[tuple[str, int]]:
    return [(item["key"], item["order"]) for item in document.data["panels"]]


def _panel(key: str, order: int, region: str = "main") -> dict:
    return {"key": key, "type": "attributes", "region": region, "order": order}


def test_an_item_takes_an_order_between_its_neighbours_without_renumbering():
    document = Document({"panels": [_panel("a", 10), _panel("c", 30), _panel("b", 99)]})
    document.data["panels"].insert(1, document.data["panels"].pop(2))
    assert keep_order(document, ["panels"], {"key": "b"}) is True
    assert _orders(document) == [("a", 10), ("b", 20), ("c", 30)]


def test_first_and_last_places_count_past_their_neighbour_and_a_fitting_order_stays():
    document = Document({"panels": [_panel("x", 0), _panel("a", 10), _panel("y", 0)]})
    keep_order(document, ["panels"], {"key": "x"})
    keep_order(document, ["panels"], {"key": "y"})
    assert _orders(document) == [("x", 0), ("a", 10), ("y", 20)]
    assert keep_order(document, ["panels"], {"key": "a"}) is False


def test_the_list_is_renumbered_only_when_no_whole_number_fits():
    document = Document({"panels": [_panel("a", 10), _panel("b", 0), _panel("c", 11)]})
    keep_order(document, ["panels"], {"key": "b"})
    assert _orders(document) == [("a", 10), ("b", 20), ("c", 30)]


def test_a_panel_counts_within_its_region():
    document = Document({"panels": [_panel("m", 10), _panel("s", 10, "side"), _panel("n", 0)]})
    keep_order(document, ["panels"], {"key": "n"})
    assert _orders(document) == [("m", 10), ("s", 10), ("n", 20)]


def _example() -> dict:
    return copy.deepcopy(EXAMPLE)


def _apply(data: dict, operation: dict):
    return apply_operation(Context(Document(data), lambda _atom: False), operation)


def _page(data: dict, application: str, type_key: str) -> dict:
    app = next(a for a in data["applications"] if a["key"] == application)
    return next(d for d in app["details"] if d["objectTypeKey"] == type_key)


def test_the_page_a_type_gets_has_a_panel_for_each_relationship_in_each_direction():
    page = detail_page(Document(_example()), "stop")
    by_region = {
        r: [p["key"] for p in page["panels"] if p["region"] == r] for r in ("main", "side")
    }
    assert by_region["side"] == ["attributes", "hierarchy"]
    # Containment (a stop's municipality) has the hierarchy; the others are read from the stop.
    assert by_region["main"] == [
        "stop-served-by-mode",
        "stop-operated-by-operator",
        "represented-by-system-code",
        "object-has-translation",
    ]
    panels = {p["key"]: p for p in page["panels"]}
    mapped = panels["represented-by-system-code"]
    assert mapped["title"] == "Is represented by system code"
    assert mapped["config"] == {
        "relationTypeKeys": ["system-code-maps-to"],
        "direction": "incoming",
        "columns": ["name", "ancestor:system", "external-id", "description"],
        "showRelationshipColumn": False,
        "sortFields": ["ancestor:system", "name"],
        "defaultSort": "ancestor:system",
    }
    assert panels["object-has-translation"]["config"]["columns"] == [
        "name",
        "ancestor:language",
        "translated-name",
        "active",
    ]
    assert panels["stop-operated-by-operator"]["title"] == "Operated by"


def test_a_panel_listing_several_types_names_each_record_s_type_and_sits_under_no_one_parent():
    page = detail_page(Document(_example()), "system-code")
    maps_to = next(p for p in page["panels"] if p["key"] == "system-code-maps-to")
    assert maps_to["config"]["columns"] == [
        "name",
        "designation",
        "stop-number",
        "sloid",
        "abbreviation",
        "objectType",
    ]
    assert "defaultSort" not in maps_to["config"]


def test_the_page_of_the_stop_is_the_fixture_the_frontend_s_undeclared_page_is_checked_against():
    page = detail_page(Document(_example()), "stop")
    assert json.loads(STOP_PAGE.read_text()) == page, (
        "regenerate frontend/src/model/stop-page.fixture.json"
    )


def test_an_allowed_relation_gets_a_panel_and_a_column_at_both_its_types_and_the_undo_takes_them_away():
    data = _example()
    # A type with a page and a table in the network application.
    _apply(
        data,
        {
            "kind": "disallowRelation",
            "relationType": "stop-operated-by-operator",
            "from": "stop",
            "to": "operator",
        },
    )
    stop = _page(data, "network", "stop")
    assert "stop-operated-by-operator" not in [p["key"] for p in stop["panels"]]
    table = next(
        v
        for v in next(a for a in data["applications"] if a["key"] == "network")["views"]
        if v.get("objectTypeKey") == "stop"
    )
    assert "related:stop-operated-by-operator" not in table["config"]["columns"]
    before = copy.deepcopy(data)
    applied = _apply(
        data,
        {
            "kind": "allowRelation",
            "relationType": "stop-operated-by-operator",
            "from": "stop",
            "to": "operator",
            "cardinality": "many-to-one",
        },
    )
    for type_key, key, field in (
        ("stop", "stop-operated-by-operator", "related:stop-operated-by-operator"),
        ("operator", "operator-operates-stop", "related:operator-operates-stop"),
    ):
        panel = next(p for p in _page(data, "network", type_key)["panels"] if p["key"] == key)
        assert panel["type"] == "relations" and panel["config"]["showRelationshipColumn"] is False
        view = next(
            v
            for v in next(a for a in data["applications"] if a["key"] == "network")["views"]
            if v.get("objectTypeKey") == type_key
        )
        assert field in view["config"]["columns"] and field in view["config"]["filterFields"]
    # The reference model's Stops API reads values the binding carries: allowing the relation again
    # leaves them to be chosen (Carries), so the check restores them as the model had them.
    restored = copy.deepcopy(data)
    binding = next(
        b
        for b in restored["objectTypeRelations"]
        if (b["relationTypeKey"], b["fromObjectTypeKey"], b["toObjectTypeKey"])
        == ("stop-operated-by-operator", "stop", "operator")
    )
    binding["attributeTypeKeys"] = next(
        b["attributeTypeKeys"]
        for b in EXAMPLE["objectTypeRelations"]
        if b["relationTypeKey"] == "stop-operated-by-operator"
    )
    assert compile_model(restored).valid
    _apply(data, applied.inverse)
    assert data == before
    # Taking the binding away again leaves nothing of it on either type.
    _apply(
        data,
        {
            "kind": "allowRelation",
            "relationType": "stop-operated-by-operator",
            "from": "stop",
            "to": "operator",
        },
    )
    _apply(
        data,
        {
            "kind": "disallowRelation",
            "relationType": "stop-operated-by-operator",
            "from": "stop",
            "to": "operator",
        },
    )
    assert data == before


def test_a_page_written_by_hand_is_not_rewritten_by_a_new_relationship():
    data = _example()
    page = _page(data, "network", "stop")
    written = copy.deepcopy(page)
    _apply(
        data,
        {
            "kind": "allowRelation",
            "relationType": "stop-served-by-mode",
            "from": "stop",
            "to": "municipality",
        },
    )
    assert [
        p for p in page["panels"] if p["key"] in {x["key"] for x in written["panels"]}
    ] == written["panels"]


def test_add_panel_builds_a_relations_panel_with_the_rule_and_the_undo_removes_it():
    data = _example()
    before = copy.deepcopy(data)
    page = _page(data, "network", "stop")
    page["panels"] = [p for p in page["panels"] if p["key"] != "system-codes"]
    declared = copy.deepcopy(data)
    applied = _apply(
        data,
        {
            "kind": "addPanel",
            "applicationKey": "network",
            "detail": "stop",
            "show": {"relations": {"relation": "system-code-maps-to", "direction": "incoming"}},
            "region": "main",
        },
    )
    assert applied.parameters["key"] == "represented-by-system-code"
    assert applied.parameters["title"] == "Is represented by system code"
    panel = next(p for p in page["panels"] if p["key"] == "represented-by-system-code")
    assert panel["config"]["columns"] == ["name", "ancestor:system", "external-id", "description"]
    assert compile_model(data).valid
    # A second panel of the same relationship takes a free key.
    again = _apply(
        data,
        {
            "kind": "addPanel",
            "applicationKey": "network",
            "detail": "stop",
            "show": {"relations": {"relation": "system-code-maps-to", "direction": "incoming"}},
            "title": "Codes",
        },
    )
    assert (
        again.parameters["key"] == "represented-by-system-code-2"
        and again.parameters["title"] == "Codes"
    )
    _apply(data, again.inverse)
    _apply(data, applied.inverse)
    assert data == declared
    assert before != declared


def test_add_panel_builds_a_children_panel_on_the_side_when_asked():
    data = _example()
    page = _page(data, "network", "municipality")
    page["panels"] = [p for p in page["panels"] if p["type"] != "children"]
    applied = _apply(
        data,
        {
            "kind": "addPanel",
            "applicationKey": "network",
            "detail": "municipality",
            "show": {"children": {"objectTypeKeys": ["stop"]}},
            "region": "side",
            "title": "Its stops",
        },
    )
    panel = next(p for p in page["panels"] if p["key"] == applied.parameters["key"])
    assert (panel["type"], panel["region"], panel["title"], panel["config"]["objectTypeKeys"]) == (
        "children",
        "side",
        "Its stops",
        ["stop"],
    )
    assert compile_model(data).valid


@pytest.mark.parametrize(
    ("operation", "reason"),
    [
        (
            {
                "detail": "stop",
                "show": {"relations": {"relation": "no-such", "direction": "outgoing"}},
            },
            "unknownElement",
        ),
        # The stop holds the system code mapping incoming only.
        (
            {
                "detail": "stop",
                "show": {"relations": {"relation": "system-code-maps-to", "direction": "outgoing"}},
            },
            "unknownElement",
        ),
        # The systems application declares no page for the stop.
        (
            {
                "detail": "stop",
                "applicationKey": "systems",
                "show": {"relations": {"relation": "stop-served-by-mode", "direction": "outgoing"}},
            },
            "unknownElement",
        ),
        # A type the application does not list.
        (
            {"detail": "municipality", "show": {"children": {"objectTypeKeys": ["system"]}}},
            "invalidValue",
        ),
        (
            {
                "detail": "stop",
                "key": "attributes",
                "show": {"relations": {"relation": "stop-served-by-mode", "direction": "outgoing"}},
            },
            "keyTaken",
        ),
        ({"detail": "stop", "show": {"nothing": {}}}, "invalidValue"),
    ],
)
def test_add_panel_refuses_what_the_page_cannot_show(operation: dict, reason: str):
    data = _example()
    before = copy.deepcopy(data)
    with pytest.raises(Refusal) as refused:
        _apply(data, {"kind": "addPanel", "applicationKey": "network", **operation})
    assert refused.value.reason == reason
    assert data == before
