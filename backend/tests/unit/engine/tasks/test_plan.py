"""The plan of a task (``engine/tasks/plan.py``): the reading and the person's choices as an import
profile, which the profile's own model accepts."""

from app.engine.tasks import plan
from app.models.imports import ImportProfileDefinition


def _table(**changes):
    table = {
        "table": "t1",
        "sheet": "Records",
        "place": {"sheetIndex": 0, "headerRow": 1, "lastRow": None, "block": None},
        "as": "update",
        "objectTypeKey": "ledger",
        "applicationKey": "atlas",
        "reason": "An update of ledgers",
        "owner": "rules",
        "origin": None,
        "keyColumn": "A",
        "key": {"attributeTypeKey": "number"},
        "meaning": [],
        "columns": [
            {"column": "A", "header": "Number", "binding": {"attributeTypeKey": "number"}},
            {"column": "B", "header": "Name", "binding": {"field": "name"}},
            {"column": "C", "header": "Score", "binding": {"attributeTypeKey": "score"}},
            {"column": "D", "header": "Price", "binding": None},
        ],
        "choices": {
            "newRecords": {"value": "create", "owner": "rules"},
            "names": {"value": "file", "owner": "rules"},
            "missing": {"value": "leave", "owner": "rules"},
            "load": {"value": True, "owner": "rules"},
        },
    }
    table.update(changes)
    return table


def _built(table, computed=None, fixes=(), **kwargs):
    built = plan.build([table], computed or {}, list(fixes), csv_delimiter=None, **kwargs)
    assert built is not None
    ImportProfileDefinition.model_validate(built.profile)
    return built


def test_a_plain_update_is_one_upsert_source_keyed_by_the_reading_with_the_left_out_column_missing():
    built = _built(_table())
    (source,) = built.profile["sources"]
    assert source["record"] == "upsert" and source["key"] == {"attributeTypeKey": "number"}
    assert [c["column"] for c in source["columns"]] == ["Number", "Name", "Score"]
    assert source["missing"] == "report" and "rowsWithoutKey" not in source
    assert built.profile["valueMaps"] == {}
    assert [s["kind"] for s in built.steps] == ["profileSource", "destination"]


def test_leaving_the_new_keys_out_maps_them_to_nothing_and_skips_rows_without_a_key():
    table = _table()
    table["choices"]["newRecords"] = {"value": "leaveOut", "owner": "person"}
    table["meaning"] = [
        {"value": "X-9", "to": "A-9", "origin": {"kind": "ai"}, "record": {"id": "r", "name": "N"}}
    ]
    built = _built(table, {"t1": plan.Computed(new_keys=["X-9", "N-1", "N-2"])})
    (source,) = built.profile["sources"]
    assert source["rowsWithoutKey"] == "skip"
    key_map = built.profile["valueMaps"][source["columns"][0]["valueMap"]]
    # A key meant as a stored record is mapped to it, not left out.
    assert key_map == {"X-9": "A-9", "N-1": None, "N-2": None}
    owners = {s["owner"] for s in built.steps if s["kind"] == "valueMap"}
    assert owners == {"assistant", "person"}


def test_keeping_the_stored_names_maps_each_differing_name_and_names_what_cannot_be_mapped():
    table = _table()
    table["choices"]["names"] = {"value": "stored", "owner": "person"}
    computed = plan.Computed(names={"Spelled badly": "Stored"}, unmapped_names=["Twice"])
    built = _built(table, {"t1": computed})
    name = next(c for c in built.profile["sources"][0]["columns"] if c["column"] == "Name")
    assert built.profile["valueMaps"][name["valueMap"]] == {"Spelled badly": "Stored"}
    assert len(built.notes) == 1 and "1 names" in built.notes[0]
    taking = _built(_table(), {"t1": computed})
    assert taking.profile["valueMaps"] == {} and taking.notes == []


def test_removing_the_missing_records_is_a_delete_source():
    table = _table()
    table["choices"]["missing"] = {"value": "remove", "owner": "person"}
    assert _built(table).profile["sources"][0]["missing"] == "delete"


def test_a_fix_joins_the_map_of_its_column_and_never_replaces_an_earlier_entry():
    fixes = [
        {
            "table": "t1",
            "column": "C",
            "value": "45 mins",
            "to": "45",
            "reason": "Minutes",
            "origin": {"kind": "ai"},
        },
        {"table": "t1", "column": "A", "value": "N-1", "to": "A-1", "reason": "", "origin": None},
    ]
    table = _table()
    table["meaning"] = [
        {"value": "N-1", "to": "A-5", "origin": {"kind": "ai"}, "record": {"id": "r", "name": "N"}}
    ]
    built = _built(table, fixes=fixes)
    columns = {c["column"]: c for c in built.profile["sources"][0]["columns"]}
    assert built.profile["valueMaps"][columns["Score"]["valueMap"]] == {"45 mins": "45"}
    assert built.profile["valueMaps"][columns["Number"]["valueMap"]] == {"N-1": "A-5"}


def test_tables_not_loaded_are_not_in_the_plan_and_a_plan_of_none_is_none():
    new_data = _table(**{"as": "newData"})
    off = _table()
    off["choices"]["load"] = {"value": False, "owner": "person"}
    assert plan.build([new_data, off], {}, [], csv_delimiter=None) is None
    assert plan.build([_table()], {}, [], csv_delimiter=None, skip=frozenset({"t1"})) is None


def test_a_listed_block_and_a_csv_file_are_described_as_the_import_reads_them():
    table = _table(
        place={
            "sheetIndex": 1,
            "headerRow": 4,
            "lastRow": 20,
            "block": {"firstColumn": "A", "lastColumn": "D", "lastRow": 20},
        }
    )
    source = _built(table).profile["sources"][0]
    assert source["headerRow"] == 4 and source["block"] == {
        "firstColumn": "A",
        "lastColumn": "D",
        "lastRow": 20,
    }
    csv = plan.build([_table()], {}, [], csv_delimiter=";")
    assert csv.profile["csv"] == {"delimiter": ";"} and "sheet" not in csv.profile["sources"][0]


def test_a_note_row_is_mapped_to_nothing_on_the_key_and_name_columns_and_its_rows_skipped():
    table = _table(place={"sheetIndex": 0, "headerRow": 1, "lastRow": 9, "block": None,
                          "note": 2, "noteText": "(Multiple answer)"})
    built = _built(table)
    (source,) = built.profile["sources"]
    assert source["rowsWithoutKey"] == "skip"
    maps = built.profile["valueMaps"]
    assert [maps[c["valueMap"]] for c in source["columns"] if "valueMap" in c] == [
        {"(Multiple answer)": None},
        {"(Multiple answer)": None},
    ]


def test_a_fixed_parent_of_the_reading_is_the_sources_without_the_note_of_where_it_came_from():
    parent = {"objectTypeKey": "region", "matchBy": {"field": "name"}, "value": "North",
              "source": "records"}
    (source,) = _built(_table(parent=parent)).profile["sources"]
    assert source["parent"] == {k: v for k, v in parent.items() if k != "source"}


def _followed(**changes):
    stored = {
        "sheet": "Records",
        "headerRow": 1,
        "applicationKey": "atlas",
        "objectTypeKey": "ledger",
        "record": "upsert",
        "key": {"attributeTypeKey": "number"},
        "columns": [
            {"column": "Number", "attributeTypeKey": "number", "valueMap": "blank"},
            {"column": "Name", "field": "name"},
            {"column": "Token", "relation": {"relationTypeKey": "pairs", "objectTypeKey": "token",
                                              "matchBy": {"field": "name"}}},
        ],
        "valueMaps": {},
    }
    stored.pop("valueMaps")
    table = _table(
        profile={"key": "layout", "name": "Layout", "version": 1, "source": 0},
        owner="profile",
        profileSource=stored,
        columns=[
            {"column": "A", "header": "Number", "binding": {"attributeTypeKey": "number"}, "owner": "profile"},
            {"column": "B", "header": "Name", "binding": {"field": "name"}, "owner": "profile"},
            {"column": "C", "header": "Token", "binding": {"relation": {}}, "owner": "profile"},
        ],
    )
    table.update(changes)
    return table


def test_a_table_that_followed_a_profile_is_the_source_as_stored_and_names_the_profile():
    maps = {"blank": {"N/A": None}}
    built = plan.build([_followed()], {}, [], csv_delimiter=None,
                       profile={"key": "layout", "name": "Layout", "sources": 1}, profile_maps=maps)
    assert built is not None and built.profile_key == "layout"
    (source,) = built.profile["sources"]
    assert source["columns"][2]["relation"]["relationTypeKey"] == "pairs"
    assert built.profile["valueMaps"] == maps and "rowsWithoutKey" not in source


def test_choices_added_to_a_followed_profile_extend_its_value_maps_and_it_is_no_longer_unchanged():
    table = _followed()
    table["choices"]["newRecords"] = {"value": "leaveOut", "owner": "person"}
    maps = {"blank": {"N/A": None}}
    built = plan.build([table], {"t1": plan.Computed(new_keys=["N-1"])}, [], csv_delimiter=None,
                       profile={"key": "layout", "name": "Layout", "sources": 1}, profile_maps=maps)
    assert built is not None and built.profile_key is None
    (source,) = built.profile["sources"]
    assert source["rowsWithoutKey"] == "skip"
    # The profile's own entries stay in the map the binding now names.
    assert built.profile["valueMaps"][source["columns"][0]["valueMap"]] == {"N/A": None, "N-1": None}
