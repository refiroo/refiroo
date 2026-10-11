"""``engine/model/authoring/layout.py``: D35's ``order`` kept in step with list position."""

from app.engine.model.authoring.document import Document
from app.engine.model.authoring.layout import keep_order, place_relation


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


def _page(*panels: dict) -> Document:
    return Document(
        {
            "objectTypes": [{"key": "brand"}],
            "applications": [
                {
                    "key": "app",
                    "objectTypeKeys": ["brand"],
                    "details": [{"objectTypeKey": "brand", "panels": list(panels)}],
                }
            ],
        }
    )


def _panels(document: Document) -> list[dict]:
    return document.data["applications"][0]["details"][0]["panels"]


def test_an_allowed_relation_leaves_a_panel_set_up_for_its_own_records_alone():
    """A relations panel with its own columns and an ancestor sort (a translations panel) keeps its one
    related type; the new relation gets a panel of its own (the user's draft, A4a)."""
    translations = {
        "key": "translations",
        "type": "relations",
        "region": "main",
        "order": 40,
        "config": {
            "relationTypeKeys": ["has-translation"],
            "direction": "outgoing",
            "columns": ["ancestor:language", "name"],
            "sortFields": ["ancestor:language"],
            "defaultSort": "ancestor:language",
        },
    }
    document = _page(translations)
    place_relation(document, "special-locations", "brand")
    panels = _panels(document)
    assert panels[0]["config"]["relationTypeKeys"] == ["has-translation"]
    assert panels[1]["config"] == {
        "relationTypeKeys": ["special-locations"],
        "direction": "outgoing",
    }


def test_an_allowed_relation_joins_a_plain_relations_panel():
    document = _page(
        {
            "key": "relations",
            "type": "relations",
            "region": "main",
            "order": 10,
            "config": {"relationTypeKeys": ["a"], "direction": "outgoing"},
        }
    )
    place_relation(document, "b", "brand")
    assert [p["config"]["relationTypeKeys"] for p in _panels(document)] == [["a", "b"]]
