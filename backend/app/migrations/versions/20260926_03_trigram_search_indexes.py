"""Trigram search indexes over attribute text values (Base 0.8 S8, decision D25).

A search is a case-insensitive "contains" match over a record's name and searchable text values. No
B-tree index serves a contains match on a value, so a search over a whole type looked up the values
of every record whose name did not match: 0.7 to 0.9 s at 100,000 records. This revision adds an
SQLite FTS5 index with the ``trigram`` tokenizer over the text values of live records
(``attribute_values``) and of revision, draft-base and draft records
(``snapshot_attribute_values``). Each index stores no text of its own (external content keyed by
``sequence_id``), and three triggers per value table keep it equal to its column on every write.

No data changes. Every run drops whatever an interrupted run left and creates and fills the indexes
again, so an interrupted upgrade completes on the next start. The DDL is copied here rather than
imported, so this revision keeps its meaning when ``app/models/search_index.py`` changes.

FTS5 is SQLite's. On another dialect the revision changes nothing and search reads each record's
values as before; the PostgreSQL form (trigram GIN) arrives with 0.11.
"""

from alembic import op
from sqlalchemy import text

revision = "20260926_03"
down_revision = "20260926_02"
branch_labels = None
depends_on = None

# (index, source table, column)
_INDEXES = (
    ("attribute_values_text_search", "attribute_values", "text_value"),
    ("snapshot_attribute_values_text_search", "snapshot_attribute_values", "text_value"),
)


def _drop(index: str) -> list[str]:
    return [
        *(f"DROP TRIGGER IF EXISTS {index}_{name}" for name in ("insert", "delete", "update")),
        f"DROP TABLE IF EXISTS {index}",
    ]


def _create(index: str, source: str, value: str) -> list[str]:
    return [
        (
            f"CREATE VIRTUAL TABLE {index} USING fts5({value}, content='{source}', "
            "content_rowid='sequence_id', tokenize='trigram')"
        ),
        (
            f"CREATE TRIGGER {index}_insert AFTER INSERT ON {source} BEGIN "
            f"INSERT INTO {index}(rowid, {value}) VALUES (new.sequence_id, new.{value}); END"
        ),
        (
            f"CREATE TRIGGER {index}_delete AFTER DELETE ON {source} BEGIN "
            f"INSERT INTO {index}({index}, rowid, {value}) "
            f"VALUES ('delete', old.sequence_id, old.{value}); END"
        ),
        (
            f"CREATE TRIGGER {index}_update AFTER UPDATE OF {value} ON {source} BEGIN "
            f"INSERT INTO {index}({index}, rowid, {value}) "
            f"VALUES ('delete', old.sequence_id, old.{value}); "
            f"INSERT INTO {index}(rowid, {value}) VALUES (new.sequence_id, new.{value}); END"
        ),
        f"INSERT INTO {index}({index}) VALUES ('rebuild')",
    ]


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        return
    for index, source, value in _INDEXES:
        for statement in (*_drop(index), *_create(index, source, value)):
            bind.execute(text(statement))


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        return
    for index, _source, _value in _INDEXES:
        for statement in _drop(index):
            bind.execute(text(statement))
