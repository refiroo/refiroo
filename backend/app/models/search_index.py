"""Trigram search indexes over attribute text values (Base 0.8 S8, decision D25; PG-D7).

Each index is a ``pg_trgm`` GIN index over the ``text_value`` column of a value table, live
``attribute_values`` or ``snapshot_attribute_values``. PostgreSQL keeps it equal to the column on
every write, ORM or bulk, and answers a case-insensitive ``LIKE`` pattern of three characters or
more from it.

An index only narrows a search to candidate values. Search itself still applies the
case-insensitive "contains" predicate to each candidate (``engine/reads/object_query.py``), so the index
decides how fast a search answers, never which records it returns. Names need no trigram index:
a search reads them from the (type, name) index it already walks, which costs about 20 ms per
100,000 records, while a correlated look-up of each record's values cost 0.7-0.9 s (S7).

The baseline creates the ``pg_trgm`` extension; revision ``20261001_02`` creates the indexes.
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

SEARCH_INDEXES = (LIVE_VALUES, SNAPSHOT_VALUES)

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
