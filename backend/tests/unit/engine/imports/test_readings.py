"""A source's readings (``engine/imports/readings.py``, 0.17 PL3b, PP-D6 and PP-D7).

J58 loads a wide sheet and grouped rows through the API. Here are the rows the three readings make
of a table, with the edge cases: the order they apply in, an empty cell skipped, a heading row that
is no record, the same heading kept across blank rows, and a name the table already has.
"""

from app.engine.imports.readers import Table
from app.engine.imports.readings import apply_readings, clashes, virtual_columns
from app.engine.sources.profile_check import _follow
from app.models.imports import Source


def _source(**readings) -> Source:
    return Source.model_validate(
        {
            "applicationKey": "a",
            "objectTypeKey": "t",
            "columns": [{"column": "Item", "field": "name"}],
            **readings,
        }
    )


def _table(rows):
    return Table(["Item", "Cat", "EN", "DE"], iter(rows), 1)


def test_the_three_readings_apply_in_their_order_and_add_their_columns_at_the_end():
    source = _source(
        headings={"column": "Item", "into": "Group"},
        fillDown=["Cat"],
        unpivot={"columns": ["EN", "DE"], "nameColumn": "Lang", "valueColumn": "Text"},
    )
    read = apply_readings(
        _table(
            [
                (2, ["Fruit", None, None, None]),
                (3, ["apple", "c1", "a", "Apfel"]),
                (4, ["pear", None, "p", None]),
                (5, ["Veg", None, None, None]),
                (6, ["leek", None, None, "Lauch"]),
                (7, ["bare", None, None, None]),
            ]
        ),
        source,
    )
    assert read.header == ["Item", "Cat", "EN", "DE", "Group", "Lang", "Text"]
    assert virtual_columns(source) == ["Group", "Lang", "Text"]
    assert list(read.rows) == [
        (3, ["apple", "c1", "a", "Apfel", "Fruit", "EN", "a"]),
        (3, ["apple", "c1", "a", "Apfel", "Fruit", "DE", "Apfel"]),
        (4, ["pear", "c1", "p", None, "Fruit", "EN", "p"]),
        # "Veg" starts a new group, so "leek" takes no value from the group above.
        # "bare" holds only its name, so it reads as a heading and is no record; "leek" is kept.
        (6, ["leek", None, None, "Lauch", "Veg", "DE", "Lauch"]),
    ]


def test_a_source_without_readings_is_read_as_it_is_and_a_taken_name_is_a_clash():
    plain = _source()
    table = _table([(2, ["a", "b", "c", "d"])])
    assert apply_readings(table, plain) is table
    taken = _source(unpivot={"columns": ["EN", "DE"], "nameColumn": "Cat", "valueColumn": "Text"})
    assert clashes(taken, table) == [("/unpivot/nameColumn", "Cat")]


def test_a_column_missing_from_the_next_file_takes_its_reading_and_the_added_columns_with_it():
    source = _source(
        unpivot={"columns": ["EN", "DE"], "nameColumn": "Lang", "valueColumn": "Text"}
    ).model_dump(mode="json", exclude_none=True)
    source["columns"] += [{"column": "Lang", "attributeTypeKey": "lang"}]
    followed = _follow(source, {}, {"DE"})
    assert followed is not None
    assert "unpivot" not in followed
    assert [b["column"] for b in followed["columns"]] == ["Item"]
    renamed = _follow(source, {"DE": "Deutsch"}, set())
    assert renamed is not None
    assert renamed["unpivot"]["columns"] == ["EN", "Deutsch"]


def test_a_filled_down_value_does_not_carry_across_a_heading():
    source = _source(headings={"column": "Item", "into": "Group"}, fillDown=["Cat"])
    read = apply_readings(
        _table(
            [
                (2, ["Fruit", None, None, None]),
                (3, ["apple", "c1", "a", None]),
                (4, ["pear", None, "p", None]),
                (5, ["Veg", None, None, None]),
                (6, ["leek", None, "l", None]),
                (7, ["kale", "c2", "k", None]),
                (8, ["chard", None, "c", None]),
            ]
        ),
        source,
    )
    assert [(row[0], row[1], row[4]) for _, row in read.rows] == [
        ("apple", "c1", "Fruit"),
        ("pear", "c1", "Fruit"),
        ("leek", None, "Veg"),
        ("kale", "c2", "Veg"),
        ("chard", "c2", "Veg"),
    ]


def test_every_member_that_names_a_column_a_reading_added_goes_with_it():
    source = _source(headings={"column": "Item", "into": "Group"}).model_dump(
        mode="json", exclude_none=True
    )
    source["columns"] += [
        {
            "column": "Cat",
            "relatedRecord": {
                "relationTypeKey": "r",
                "applicationKey": "a",
                "objectTypeKey": "t",
                "field": "name",
                "parent": {"objectTypeKey": "g", "matchBy": {"field": "name"}, "column": "Group"},
            },
        },
        {
            "column": "EN",
            "relation": {
                "relationTypeKey": "r",
                "objectTypeKey": "t",
                "matchBy": {"field": "name"},
                "idColumn": "Group",
            },
        },
        {"column": "DE", "attributeTypeKey": "de"},
    ]
    followed = _follow(source, {}, {"Item"})
    assert followed is not None
    assert "headings" not in followed
    # The Group-naming members are left out as a missing column's are: the parent's binding goes,
    # the relationship loses its ID column and stays.
    assert [binding["column"] for binding in followed["columns"]] == ["EN", "DE"]
    assert "idColumn" not in followed["columns"][0]["relation"]


def test_a_binding_names_a_column_in_any_of_its_members():
    from app.engine.model.authoring.profile_side import names_column

    gone = {"Group"}
    assert names_column({"column": "Group"}, gone)
    assert names_column(
        {"columns": ["A", "Group"], "relationFlags": {"targets": {"Group": "x"}}}, gone
    )
    assert names_column({"column": "A", "relation": {"idColumn": "Group"}}, gone)
    assert names_column({"column": "A", "relation": {"attributes": [{"column": "Group"}]}}, gone)
    assert names_column({"column": "A", "relatedRecord": {"parent": {"column": "Group"}}}, gone)
    assert names_column({"column": "A", "relatedRecord": {"versionColumn": "Group"}}, gone)
    assert not names_column({"column": "A", "relation": {"idColumn": "B"}}, gone)


def test_a_cell_beyond_the_header_is_kept_after_the_added_columns_not_overwritten():
    source = _source(headings={"column": "Item", "into": "Group"})
    read = apply_readings(
        Table(["Item", "Cat"], iter([(2, ["Fruit", None]), (3, ["apple", "c1", "stray"])]), 1),
        source,
    )
    assert read.header == ["Item", "Cat", "Group"]
    assert list(read.rows) == [(3, ["apple", "c1", "Fruit", "stray"])]
