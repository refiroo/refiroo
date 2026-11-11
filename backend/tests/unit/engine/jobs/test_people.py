"""The workbook for people's cells (0.9 J6, ``engine/jobs/people.py``): an ``ancestor:`` field."""

from psycopg import sql
from sqlalchemy import text

from app.db import SessionLocal
from app.engine.jobs import people


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
                sql.SQL("SELECT {} FROM people_records o WHERE o.object_id = 'leaf'").format(expression)
            )
            assert cursor.fetchone()[0] == "Outer"
        session.rollback()
