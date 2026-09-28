"""A migrated database has the schema the ORM declares (Base 0.8 A6, D28).

Every real database is built by the Alembic migrations, while the ORM declarations are what the
code and a ``metadata.create_all`` database assume. The two drifted once: ten single-column
indexes declared on the publication and change set tables were never created by a migration, so
production ran without them while ``create_all`` test databases had them. This module migrates an
empty database to head and compares it with ``Base.metadata``: tables, columns and their types and
nullability, indexes, unique constraints and foreign keys, each difference named. The trigram
search indexes, which ``models/search_index.py`` registers outside the metadata, are compared with
the objects ``create_all`` builds for them.

A new ORM declaration without a migration, or a migration without its declaration, fails here.
"""

import re

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, text

from app.models.database import Base
from app.models.search_index import SEARCH_INDEXES

# An FTS5 index is a virtual table over shadow tables that SQLite creates itself.
SEARCH_TABLES = {
    f"{index.name}{suffix}"
    for index in SEARCH_INDEXES
    for suffix in ("", "_data", "_idx", "_docsize", "_config")
}


def _include(item, name, type_, reflected, compare_to) -> bool:
    return not (type_ == "table" and name in SEARCH_TABLES)


def _describe(difference) -> str:
    """One line naming the difference, e.g. ``add_index publication_objects.ix_… (parent_object_id)``."""
    if isinstance(difference, list):
        return "; ".join(_describe(item) for item in difference)
    kind, *rest = difference
    if kind in {"add_index", "remove_index"}:
        index = rest[0]
        columns = ", ".join(column.name for column in index.columns)
        return f"{kind} {index.table.name}.{index.name} ({columns})"
    if kind in {"add_table", "remove_table"}:
        return f"{kind} {rest[0].name}"
    if kind in {"add_column", "remove_column"}:
        return f"{kind} {rest[1]}.{rest[2].name}"
    if kind in {"add_constraint", "remove_constraint", "add_fk", "remove_fk"}:
        constraint = rest[0]
        columns = ", ".join(column.name for column in constraint.columns)
        return f"{kind} {constraint.table.name}.{constraint.name} ({columns})"
    if kind.startswith("modify_"):
        _schema, table, column, _options, migrated, declared = rest
        return f"{kind} {table}.{column}: migrated {migrated!r}, declared {declared!r}"
    return repr(difference)


def _schema_differences(url: str) -> list[str]:
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            context = MigrationContext.configure(
                connection, opts={"compare_type": True, "include_object": _include}
            )
            return sorted(_describe(item) for item in compare_metadata(context, Base.metadata))
    finally:
        engine.dispose()


def _search_objects(url: str) -> dict[tuple[str, str], str]:
    """The search indexes' tables and triggers by (type, name), with their normalised SQL."""
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            rows = connection.execute(
                text("SELECT type, name, sql FROM sqlite_master WHERE sql IS NOT NULL")
            )
            return {
                (row.type, row.name): re.sub(r"\s+", " ", row.sql).strip()
                for row in rows
                if any(row.name.startswith(index.name) for index in SEARCH_INDEXES)
            }
    finally:
        engine.dispose()


def test_a_migrated_database_matches_the_orm(_migrated_template):
    assert _schema_differences(f"sqlite:///{_migrated_template}") == []


def test_a_migrated_database_holds_the_search_indexes_create_all_builds(_migrated_template, tmp_path):
    created = tmp_path / "created.db"
    engine = create_engine(f"sqlite:///{created}")
    try:
        Base.metadata.create_all(engine)
    finally:
        engine.dispose()
    migrated = _search_objects(f"sqlite:///{_migrated_template}")
    expected = {("table", index.name) for index in SEARCH_INDEXES} | {
        ("trigger", f"{index.name}_{event}")
        for index in SEARCH_INDEXES
        for event in ("insert", "delete", "update")
    }
    assert expected <= set(migrated)
    assert migrated == _search_objects(f"sqlite:///{created}")


def test_the_comparison_names_a_declaration_no_migration_creates(_migrated_template, tmp_path):
    """The check itself: an index the migrations lack is reported by table, name and columns."""
    database = tmp_path / "drifted.db"
    database.write_bytes(_migrated_template.read_bytes())
    engine = create_engine(f"sqlite:///{database}")
    try:
        with engine.begin() as connection:
            connection.execute(text("DROP INDEX ix_publication_objects_parent_name"))
            connection.execute(text("CREATE INDEX ix_undeclared ON objects (name, version)"))
    finally:
        engine.dispose()
    assert _schema_differences(f"sqlite:///{database}") == [
        (
            "add_index publication_objects.ix_publication_objects_parent_name "
            "(publication_id, parent_object_id, object_type_key, name, object_id)"
        ),
        "remove_index objects.ix_undeclared (name, version)",
    ]
