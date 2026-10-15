"""The difference between two dry runs (0.10 A3, D71; R-F2)."""

from app.engine.sources.dry_run import _difference


def _source(position: int, rows: int, created: int) -> dict:
    return {
        "source": position,
        "sheet": "Lists",
        "objectTypeKey": "entry",
        "rows": rows,
        "records": {"created": created, "updated": 0, "unchanged": 0, "deleted": 0},
        "values": 0,
        "relationships": 0,
        "relatedRecords": 0,
        "rejections": [],
    }


def test_sources_of_one_type_on_one_sheet_are_compared_one_by_one():
    """Lists of one shape read as one list are a source per block, each of the same type on the
    same sheet (D141): each compares with its own earlier figures, not with the last of them."""
    before = [_source(0, 3, 3), _source(1, 5, 5)]
    assert _difference(before, [_source(0, 3, 3), _source(1, 5, 5)]) == []
    (changed,) = _difference(before, [_source(0, 3, 3), _source(1, 6, 6)])
    assert changed["source"] == 1
    assert changed["figures"] == {
        "records.created": {"now": 6, "was": 5},
        "rows": {"now": 6, "was": 5},
    }
