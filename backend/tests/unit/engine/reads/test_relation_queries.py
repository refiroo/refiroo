"""Unit tests for the relation reads (``app.engine.reads.relation_queries``)."""

from scenario import W1
from sqlalchemy import event

from app.db import SessionLocal, get_engine
from app.engine.reads.relation_queries import expansion_rows


def test_an_expansion_counts_its_total_before_reading_its_page(seeded):
    """0.9 R (R-F28): a query's 20-row expansion of 20,000 children in a publication took 107 ms,
    41 ms before: joined after the page, the total was counted again for every row of the page
    (20 times at full volume; smaller data plans it once, so this pins the statement's shape). The
    total depends on the anchor alone and is joined before the page."""
    statements: list[str] = []

    def capture(connection, cursor, statement, parameters, context, executemany):
        if "expansion_page" in statement:
            statements.append(statement)

    event.listen(get_engine(), "before_cursor_execute", capture)
    try:
        with SessionLocal() as session:
            expansion_rows(
                session,
                None,
                workspace_key=W1,
                anchor_ids=["an-anchor"],
                direction="outgoing",
                relation_type_key="a-relation-type",
                limit=20,
            )
    finally:
        event.remove(get_engine(), "before_cursor_execute", capture)

    (statement,) = statements
    joins = statement[statement.index("FROM") :]
    assert joins.index("expansion_total") < joins.index("expansion_page"), joins
