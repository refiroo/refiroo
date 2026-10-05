"""A migrated database has the schema the ORM declares (Base 0.8 A6, D28; PostgreSQL baseline, PG1).

Every real database is built by the Alembic migrations, while the ORM declarations are what the
code assumes. The two drifted once: ten single-column indexes declared on the publication and
change set tables were never created by a migration. This module compares the ``schema`` seed, an
empty database migrated to head on PostgreSQL, with ``Base.metadata``: tables, columns and their
types and nullability, indexes, unique constraints and foreign keys, each difference named.

A new ORM declaration without a migration, or a migration without its declaration, fails here.
"""

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, text

from app.models.database import Base


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
            context = MigrationContext.configure(connection, opts={"compare_type": True})
            return sorted(_describe(item) for item in compare_metadata(context, Base.metadata))
    finally:
        engine.dispose()


@pytest.fixture
def migrated(migrated_database) -> str:
    return migrated_database()


def test_a_migrated_database_matches_the_orm(migrated):
    assert _schema_differences(migrated) == []


def test_the_migrations_install_pg_trgm_and_btree_gin(migrated):
    engine = create_engine(migrated)
    try:
        with engine.connect() as connection:
            assert connection.scalar(
                text("SELECT count(*) FROM pg_extension WHERE extname IN ('pg_trgm', 'btree_gin')")
            ) == 2
    finally:
        engine.dispose()


def test_the_comparison_names_a_declaration_no_migration_creates(migrated):
    """The check itself: an index the migrations lack is reported by table, name and columns."""
    engine = create_engine(migrated)
    try:
        with engine.begin() as connection:
            connection.execute(text("DROP INDEX ix_publication_objects_parent_name"))
            connection.execute(text("CREATE INDEX ix_undeclared ON objects (name, version)"))
    finally:
        engine.dispose()
    assert _schema_differences(migrated) == [
        (
            "add_index publication_objects.ix_publication_objects_parent_name "
            "(publication_id, parent_object_id, object_type_key, name, object_id)"
        ),
        "remove_index objects.ix_undeclared (name, version)",
    ]
