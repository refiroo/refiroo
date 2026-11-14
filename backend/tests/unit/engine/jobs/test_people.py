"""The workbook for people's cells (0.9 J6, ``engine/jobs/people.py``): an ``ancestor:`` field."""

import pytest
from psycopg import sql
from sqlalchemy import text

from app.db import SessionLocal
from app.engine.jobs import people
from app.errors import ApiError


def test_an_ancestor_field_shows_the_ancestor_nearest_the_root(seeded):
    """0.9 R-F15, D209: a record under two ancestors of one type (a type that nests) shows the one
    nearest the root, as a list and ``path`` show it."""
    with SessionLocal() as session:
        for statement in people._TEMPORARY_TABLES:
            session.execute(text(statement))
        session.execute(
            text(
                "INSERT INTO people_records (object_id, object_type_key, name) VALUES"
                " ('leaf', 'item', 'Leaf'), ('inner', 'group', 'Inner'), ('outer', 'group', 'Outer')"
            )
        )
        session.execute(
            text(
                "INSERT INTO people_ancestors (object_id, ancestor_id, level) VALUES"
                " ('leaf', 'inner', 1), ('leaf', 'outer', 2)"
            )
        )
        # An ancestor's name reads no model.
        expression = people.field_sql(None, "o", "ancestor:group.name")
        connection = session.connection().connection.driver_connection
        with connection.cursor() as cursor:
            cursor.execute(
                sql.SQL("SELECT {} FROM people_records o WHERE o.object_id = 'leaf'").format(
                    expression
                )
            )
            assert cursor.fetchone()[0] == "Outer"
        session.rollback()


def _first_value(statement) -> object:
    with SessionLocal() as session:
        connection = session.connection().connection.driver_connection
        with connection.cursor() as cursor:
            cursor.execute(statement)
            return cursor.fetchone()[0]


def test_a_separator_in_a_name_is_written_as_a_comma_by_the_one_guard(seeded):
    """One guard for the people export's relation columns and the matrix's cells: the import cuts a
    cell at ``;``, so a name holding one would read back as two."""
    expression = people.separator_safe(sql.SQL("{}").format(sql.Literal("Acme; Inc;Co")))
    assert _first_value(sql.SQL("SELECT {}").format(expression)) == "Acme, Inc,Co"


def test_a_row_of_many_fields_is_built_under_the_100_argument_limit(seeded):
    """``jsonb_build_object`` takes 100 arguments: 130 pairs are built in groups, joined."""
    pairs = [(sql.Literal(f"f{n}"), sql.Literal(n)) for n in range(130)]
    built = _first_value(sql.SQL("SELECT {}").format(people.build_object(pairs)))
    assert len(built) == 130 and built["f129"] == 129
    assert _first_value(sql.SQL("SELECT {}").format(people.build_object([]))) == {}


def test_a_text_a_cell_cannot_hold_refuses_the_export_naming_record_and_field():
    """A text over 32,767 characters was written whole (a cell Excel cannot open whole); the sheet's
    ID column names the record and the column's label the field."""
    cells = [
        people.CellSpec("Name", sql.SQL("r.name")),
        people.CellSpec("Notes", sql.SQL("r.notes")),
        people.CellSpec(people.ID_LABEL, sql.SQL("r.object_id"), hidden=True),
    ]
    encode = people.row_encoder(["A", "B", "C"], cells, "Systems")
    assert "<c" in encode(["Acme", "x" * 32_767, "id-1"], 2)
    with pytest.raises(ApiError) as refused:
        encode(["Acme", "x" * 32_768, "id-1"], 2)
    assert refused.value.code == "EXPORT_TEXT_TOO_LONG"
    assert refused.value.details == {
        "sheet": "Systems",
        "row": 2,
        "recordId": "id-1",
        "field": "Notes",
        "length": 32_768,
        "limit": 32_767,
    }
