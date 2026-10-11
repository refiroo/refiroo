"""``engine/model/authoring/layout.py``: D35's ``order`` kept in step with list position."""

from app.engine.model.authoring.document import Document
from app.engine.model.authoring.layout import keep_order


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
