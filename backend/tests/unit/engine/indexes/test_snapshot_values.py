"""``engine/indexes/snapshot_values.copy_live``: live data frozen into a publication or a change
set's base with set statements.

0.11 X5 found the publication of a moved workspace's change set running for hours at 26,000
records: the copy of its relationships joined both ends to ``objects``, and the records the move
had just written were not in the statistics, so PostgreSQL estimated one record a side and paired
every record of the workspace with every other, and the copy of the records recomputed the
workspace's values for every record. A relationship belongs to its ``from`` record's workspace (as
``resolve_relation_snapshot`` reads it; relationships never cross workspaces, D8), and a record's
values are read through its own index entries, so each copy reads ``objects`` once.
"""

from sqlalchemy import event, select, text

from app.db import SessionLocal, get_engine
from app.engine.indexes.snapshot_values import copy_live
from app.models.database import Publication, WorkspaceModel

W1 = "default"


def _scans(plan: dict, relation: str) -> int:
    own = 1 if plan.get("Relation Name") == relation else 0
    return own + sum(_scans(child, relation) for child in plan.get("Plans", []))


def test_freezing_live_data_reads_the_workspace_records_once(seeded):
    """Given a workspace whose statistics hold none of its records, as after a move loaded them.
    When its live data is frozen into a publication. Then the copies of its records and of its
    relationships each scan ``objects`` once, and every record and relationship is copied with its
    values."""
    plans = []

    def explain(connection, cursor, statement, parameters, context, executemany):
        if statement.lstrip().startswith(
            ("INSERT INTO publication_objects", "INSERT INTO publication_relations")
        ):
            cursor.execute("EXPLAIN (FORMAT JSON) " + statement, parameters)
            plans.append(cursor.fetchone()[0][0]["Plan"])

    engine = get_engine()
    with SessionLocal() as session:
        session.execute(text("ANALYZE objects, object_relations"))
        release_id = session.scalar(
            select(WorkspaceModel.model_release_id).where(WorkspaceModel.workspace_key == W1)
        )
        publication = Publication(
            workspace_key=W1,
            model_release_id=release_id,
            publication_number=999_999,
            status="withdrawn",
        )
        session.add(publication)
        session.flush()
        expected = session.execute(
            text(
                "SELECT count(*) FROM object_relations r JOIN objects o ON o.id = r.from_object_id"
                " WHERE o.workspace_key = :w"
            ),
            {"w": W1},
        ).scalar_one()
        event.listen(engine, "before_cursor_execute", explain)
        try:
            copy_live(session, "publication", publication.id, W1)
        finally:
            event.remove(engine, "before_cursor_execute", explain)
        copied = session.execute(
            text("SELECT count(*) FROM publication_relations WHERE publication_id = :p"),
            {"p": publication.id},
        ).scalar_one()
        records = session.execute(
            text(
                "SELECT (SELECT count(*) FROM objects WHERE workspace_key = :w),"
                " count(*), count(*) FILTER (WHERE p.attributes::text <> '{}')"
                " FROM publication_objects p WHERE p.publication_id = :p"
            ),
            {"w": W1, "p": publication.id},
        ).one()
        valued = session.execute(
            text(
                "SELECT count(DISTINCT v.object_id) FROM attribute_values v"
                " JOIN objects o ON o.id = v.object_id WHERE o.workspace_key = :w"
            ),
            {"w": W1},
        ).scalar_one()
        session.rollback()
    assert len(plans) == 2
    for plan in plans:
        assert _scans(plan, "objects") == 1, plan
    assert expected > 0 and copied == expected
    assert records[0] == records[1] and records[2] == valued > 0
