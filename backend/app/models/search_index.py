"""Trigram search indexes over attribute text values and record names (Base 0.8 S8, decision
D25; PG-D7; 0.9.0-alpha.1 PG5).

Each index is a ``pg_trgm`` GIN index over a text column: ``text_value`` of a value table, live
``attribute_values`` or ``snapshot_attribute_values``, and ``name`` of each record table, live
``objects``, ``publication_objects``, ``change_set_base_objects`` and ``change_set_objects``.
PostgreSQL keeps it equal to the column on every write, ORM or bulk, and answers a
case-insensitive ``LIKE`` pattern of three characters or more from it.

An index only narrows a search to candidate records. Search itself still applies the
case-insensitive "contains" predicate to each candidate (``engine/reads/object_query.py``), so the
index decides how fast a search answers, never which records it returns. Names were matched on
every record of the walked (type, name) index until PG5: 20 ms per 100,000 records on SQLite, but
90 ms on PostgreSQL, twice over in a change set.

The baseline creates the ``pg_trgm`` extension; revision ``20261001_02`` creates the value indexes
and ``20261003_01`` the name indexes. The consumer API's contains matches of names read their own
trigram index, with the workspace and type beside the trigrams (``btree_gin``, revision
``20261005_02``, declared on ``objects`` in ``database.py``).
"""

from dataclasses import dataclass
from typing import Any

from sqlalchemy import Index, Select, column, select, table


@dataclass(frozen=True)
class SearchIndex:
    """One trigram index over ``source.<column>``; its matches are the source's ``sequence_id``."""

    name: str
    source: str
    column: str

    def matches(self, pattern: str) -> Select[Any]:
        """The source rows whose value matches the ``ILIKE`` pattern (escaped with ``\\``)."""
        source = table(self.source, column("sequence_id"), column(self.column))
        return select(source.c.sequence_id).where(
            source.c[self.column].ilike(pattern, escape="\\")
        )


LIVE_VALUES = SearchIndex("ix_attribute_values_text_search", "attribute_values", "text_value")
SNAPSHOT_VALUES = SearchIndex(
    "ix_snapshot_attribute_values_text_search", "snapshot_attribute_values", "text_value"
)

LIVE_NAMES = SearchIndex("ix_objects_name_search", "objects", "name")
PUBLICATION_NAMES = SearchIndex("ix_publication_objects_name_search", "publication_objects", "name")
CHANGE_SET_BASE_NAMES = SearchIndex(
    "ix_change_set_base_objects_name_search", "change_set_base_objects", "name"
)
CHANGE_SET_NAMES = SearchIndex("ix_change_set_objects_name_search", "change_set_objects", "name")

SEARCH_INDEXES = (LIVE_VALUES, SNAPSHOT_VALUES)
NAME_INDEXES = (LIVE_NAMES, PUBLICATION_NAMES, CHANGE_SET_BASE_NAMES, CHANGE_SET_NAMES)

# A trigram index holds three-character sequences; a shorter pattern has none to look up.
MIN_INDEXED_LENGTH = 3


def search_index(index: SearchIndex) -> Index:
    """The index's declaration, for its source table's ``__table_args__``."""
    return Index(
        index.name,
        index.column,
        postgresql_using="gin",
        postgresql_ops={index.column: "gin_trgm_ops"},
    )
