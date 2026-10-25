"""Where each change was made, and what it changed (Product 0.12 Z6, D341, D347).

Every audit entry that belongs to a workspace names it, not only those in its feed: a change set's
work and a workspace's model activation gain ``workspace_key`` without a feed position. A record or
relationship entry made in a change set names what it changed in ``subject`` as a live entry does;
``feed_subject`` is renamed ``subject`` since it no longer belongs to the feed alone.

Existing entries are placed in SQL: a change set's entries from the change set while it is open,
from the publication entry naming it once published, or from its lifecycle entries naming
``workspaceKey`` (only for a workspace that existed then, so a key created again later never
claims them); a change set's records and relationships from the rows still there or the live ones.
An entry without a subject holds SQL ``NULL`` or, as the ORM wrote it, JSON ``null``; both count.
Entries from before the feed, and those of a deleted workspace, stay in no workspace. The actor
indexes gain the time, so one person's changes page as an index range. One transaction, so an
interrupted run leaves the database at ``20261101_01``.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261102_01"
down_revision = "20261101_01"
branch_labels = None
depends_on = None

_PLACES = """
WITH places AS (
    SELECT id AS change_set_id, workspace_key, 0 AS rank FROM change_sets
    UNION ALL
    SELECT changes ->> 'changeSetId', workspace_key, 1 FROM audit_events
    WHERE aggregate_type = 'publication' AND workspace_key IS NOT NULL
        AND changes ->> 'changeSetId' IS NOT NULL
    UNION ALL
    SELECT e.aggregate_id, w.key, 2 FROM audit_events e
    JOIN workspaces w ON w.key = e.changes ->> 'workspaceKey' AND w.created_at <= e.occurred_at
    WHERE e.aggregate_type = 'change-set'
), chosen AS (
    SELECT DISTINCT ON (change_set_id) change_set_id, workspace_key FROM places
    ORDER BY change_set_id, rank
)
UPDATE audit_events a SET workspace_key = chosen.workspace_key
FROM chosen
WHERE a.workspace_key IS NULL
    AND a.aggregate_type IN ('change-set', 'change-set-object', 'relation', 'mapping')
    AND chosen.change_set_id = CASE WHEN a.aggregate_type = 'change-set' THEN a.aggregate_id
        ELSE a.changes ->> 'changeSetId' END
"""

_ACTIVATIONS = """
UPDATE audit_events a SET workspace_key = w.key
FROM workspaces w
WHERE a.aggregate_type = 'workspace_model' AND a.workspace_key IS NULL
    AND w.key = a.changes ->> 'workspaceKey' AND w.created_at <= a.occurred_at
"""

_RECORD_SUBJECTS = """
UPDATE audit_events a SET subject = found.subject
FROM (
    SELECT e.sequence_id, json_build_object(
        'objectTypeKey', coalesce(row.object_type_key, live.object_type_key,
            e.changes ->> 'objectTypeKey'),
        'applicationKey', coalesce(row.application_key, live.application_key),
        'parentObjectId', coalesce(row.parent_object_id, live.parent_object_id)) AS subject
    FROM audit_events e
    LEFT JOIN change_set_objects row ON row.change_set_id = e.changes ->> 'changeSetId'
        AND row.object_id = e.aggregate_id
    LEFT JOIN objects live ON live.id = e.aggregate_id
    WHERE e.aggregate_type = 'change-set-object' AND (e.subject IS NULL OR e.subject::text = 'null')
        AND coalesce(row.object_type_key, live.object_type_key, e.changes ->> 'objectTypeKey')
            IS NOT NULL
) found
WHERE a.sequence_id = found.sequence_id
"""

_RELATION_SUBJECTS = """
UPDATE audit_events a SET subject = found.subject
FROM (
    SELECT e.sequence_id, json_build_object(
        'relationTypeKey', coalesce(row.relation_type_key, live.relation_type_key),
        'fromObjectId', coalesce(row.from_object_id, live.from_object_id),
        'toObjectId', coalesce(row.to_object_id, live.to_object_id)) AS subject
    FROM audit_events e
    LEFT JOIN change_set_relations row ON row.change_set_id = e.changes ->> 'changeSetId'
        AND row.relation_id = e.aggregate_id
    LEFT JOIN object_relations live ON live.id = e.aggregate_id
    WHERE e.aggregate_type = 'relation' AND (e.subject IS NULL OR e.subject::text = 'null')
        AND coalesce(row.relation_type_key, live.relation_type_key) IS NOT NULL
) found
WHERE a.sequence_id = found.sequence_id
"""


def _actor_indexes(*columns: str) -> None:
    for kind in ("user", "client"):
        name = f"ix_audit_events_actor_{kind}"
        op.drop_index(name, table_name="audit_events")
        op.create_index(
            name,
            "audit_events",
            [f"actor_{kind}_id", *columns],
            postgresql_where=sa.text(f"actor_{kind}_id IS NOT NULL"),
        )


def upgrade() -> None:
    op.alter_column("audit_events", "feed_subject", new_column_name="subject")
    op.execute(_PLACES)
    op.execute(_ACTIVATIONS)
    op.execute(_RECORD_SUBJECTS)
    op.execute(_RELATION_SUBJECTS)
    _actor_indexes("occurred_at", "sequence_id")


def downgrade() -> None:
    _actor_indexes()
    op.execute(
        "UPDATE audit_events SET workspace_key = NULL, subject = NULL "
        "WHERE feed_position IS NULL AND workspace_key IS NOT NULL"
    )
    op.alter_column("audit_events", "subject", new_column_name="feed_subject")
