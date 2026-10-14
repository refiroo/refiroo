"""``engine/sources/profile_check.py``: the profile as the check reads the next file (0.10 A5c,
D83): renamed columns under their new header, members naming a missing column left out, a source
with nothing left to load not read."""

from app.engine.sources.profile_check import _follow

SOURCE = {
    "sheet": "Items",
    "applicationKey": "store",
    "objectTypeKey": "item",
    "key": {"attributeTypeKey": "code"},
    "missing": "delete",
    "columns": [
        {"column": "Code", "attributeTypeKey": "code"},
        {"column": "Name", "field": "name"},
        {"columns": ["Cold", "Dry"], "relationFlags": {"relationTypeKey": "kept", "objectTypeKey": "zone", "matchBy": {"field": "name"},
                                                         "targets": {"Cold": "Cold", "Dry": "Dry"}}},
        {"column": "Notes", "ignore": True},
    ],
}


def test_a_renamed_column_is_read_under_its_new_header_everywhere():
    followed = _follow(SOURCE, {"Cold": "Chilled", "Name": "Title"}, set())
    assert followed["columns"][1] == {"column": "Title", "field": "name"}
    flags = followed["columns"][2]
    assert flags["columns"] == ["Chilled", "Dry"]
    assert flags["relationFlags"]["targets"] == {"Chilled": "Cold", "Dry": "Dry"}


def test_a_missing_column_is_left_out_and_a_missing_key_column_drops_the_key_and_its_deletes():
    followed = _follow(SOURCE, {}, {"Dry", "Code"})
    assert [b.get("column") or b.get("columns") for b in followed["columns"]] == ["Name", ["Cold"], "Notes"]
    assert "key" not in followed and "missing" not in followed


def test_a_source_left_with_ignored_columns_only_is_not_read():
    assert _follow(SOURCE, {}, {"Code", "Name", "Cold", "Dry"}) is None
