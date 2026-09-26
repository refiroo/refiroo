"""Trigram search indexes over attribute text values (Base 0.8 S8, decision D25).

Each index is an SQLite FTS5 table with the ``trigram`` tokenizer over the ``text_value`` column of
a value table, live ``attribute_values`` or ``snapshot_attribute_values``, stored as external
content: the index holds no copy of the text, and its rows are the source table's rows by
``sequence_id``. Triggers on the source table keep the index equal to the column on every insert,
update and delete, so each write path, ORM or bulk, maintains it at the cost of the rows it writes.

An index only narrows a search to candidate values. Search itself still applies the
case-insensitive "contains" predicate to each candidate (``services/objects.py``), so the index
decides how fast a search answers, never which records it returns. Names need no trigram index:
a search reads them from the (type, name) index it already walks, which costs about 20 ms per
100,000 records, while a correlated look-up of each record's values cost 0.7-0.9 s (S7).

``alembic`` revision ``20260926_03`` creates these objects on upgrade with its own copy of the DDL;
``Base.metadata.create_all`` creates them through :func:`register` for databases built without it.
"""

from dataclasses import dataclass

from sqlalchemy import Connection, MetaData, column, event, table, text


@dataclass(frozen=True)
class SearchIndex:
    """One FTS5 index over ``source.<column>``, addressed by the source's ``sequence_id``."""

    name: str
    source: str
    column: str

    @property
    def fts(self):
        """The index as a selectable: ``rowid`` is the source ``sequence_id``."""
        return table(self.name, column("rowid"), column(self.column))

    def ddl(self) -> list[str]:
        """Create the index and its triggers; the caller fills it with :meth:`rebuild`."""
        index, source, value = self.name, self.source, self.column
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
        ]

    def rebuild(self) -> str:
        return f"INSERT INTO {self.name}({self.name}) VALUES ('rebuild')"

    def drop(self) -> list[str]:
        return [
            *(
                f"DROP TRIGGER IF EXISTS {self.name}_{event_name}"
                for event_name in ("insert", "delete", "update")
            ),
            f"DROP TABLE IF EXISTS {self.name}",
        ]


LIVE_VALUES = SearchIndex("attribute_values_text_search", "attribute_values", "text_value")
SNAPSHOT_VALUES = SearchIndex(
    "snapshot_attribute_values_text_search", "snapshot_attribute_values", "text_value"
)

SEARCH_INDEXES = (LIVE_VALUES, SNAPSHOT_VALUES)

# The trigram tokenizer indexes three-character sequences; a shorter search has none to look up.
MIN_INDEXED_LENGTH = 3


def match_phrase(search: str) -> str:
    """An FTS5 query matching ``search`` as a literal substring: one quoted phrase."""
    return '"' + search.replace('"', '""') + '"'


def install(connection: Connection) -> None:
    """Create every index with its triggers and fill it from its source table."""
    for index in SEARCH_INDEXES:
        for statement in (*index.drop(), *index.ddl(), index.rebuild()):
            connection.execute(text(statement))


def uninstall(connection: Connection) -> None:
    for index in SEARCH_INDEXES:
        for statement in index.drop():
            connection.execute(text(statement))


def register(metadata: MetaData) -> None:
    """Create and drop the indexes with ``metadata`` on SQLite."""

    @event.listens_for(metadata, "after_create")
    def _create(_target: MetaData, connection: Connection, **_kw: object) -> None:
        if connection.dialect.name == "sqlite":
            install(connection)

    @event.listens_for(metadata, "before_drop")
    def _drop(_target: MetaData, connection: Connection, **_kw: object) -> None:
        if connection.dialect.name == "sqlite":
            uninstall(connection)
