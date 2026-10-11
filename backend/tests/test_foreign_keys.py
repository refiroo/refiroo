"""Every foreign key's ``ondelete`` rule, checked against the service that deletes (PG-D4).

PostgreSQL enforces foreign keys, so each rule is behaviour: ``CASCADE`` removes the dependants
with the row, ``RESTRICT`` refuses the delete while one remains, ``SET NULL`` clears the
reference. Each rule below names the service that deletes the referenced row and what it relies
on; the services' own tests run against these constraints in every group. A changed rule fails
here until the table, and the service it names, are reviewed.
"""

from sqlalchemy import create_engine, text

from app.models.database import Base

# (table, column) -> (referenced table, rule), grouped by the service that deletes the referenced row.
RULES = {
    # A record is deleted by the write unit (``LiveWrites.remove_records``) or by publishing over
    # it (``writes.apply_merge``). Both delete values and relations themselves first, for matrix
    # states and audit; the cascades are a second line. Both detach parent pointers before
    # deleting, since a record's children must never vanish with it unseen.
    ("attribute_values", "object_id"): ("objects", "CASCADE"),
    # A unique value's row goes with its value (0.9 J2a).
    ("unique_attribute_values", "value_id"): ("attribute_values", "CASCADE"),
    ("object_relations", "from_object_id"): ("objects", "CASCADE"),
    ("object_relations", "to_object_id"): ("objects", "CASCADE"),
    ("objects", "parent_object_id"): ("objects", "RESTRICT"),
    # A change set is deleted when discarded or published (``lifecycle.delete_change_set_and_base``):
    # its rows and set versions go with it, then its private base, which no change set may
    # still name.
    ("change_set_objects", "change_set_id"): ("change_sets", "CASCADE"),
    ("change_set_relations", "change_set_id"): ("change_sets", "CASCADE"),
    ("relation_set_versions", "change_set_id"): ("change_sets", "CASCADE"),
    ("change_sets", "base_id"): ("change_set_bases", "RESTRICT"),
    ("change_set_base_objects", "base_id"): ("change_set_bases", "CASCADE"),
    ("change_set_base_relations", "base_id"): ("change_set_bases", "CASCADE"),
    # A workspace is deleted only when nothing names it (``catalogue.delete_workspace``, D27): no
    # record, change set, base or publication, and not the default. Its set versions go with it.
    ("objects", "workspace_key"): ("workspaces", "RESTRICT"),
    ("change_sets", "workspace_key"): ("workspaces", "RESTRICT"),
    ("change_set_bases", "workspace_key"): ("workspaces", "RESTRICT"),
    ("publications", "workspace_key"): ("workspaces", "RESTRICT"),
    ("workspace_runtime_state", "default_workspace_key"): ("workspaces", "RESTRICT"),
    ("relation_set_versions", "workspace_key"): ("workspaces", "CASCADE"),
    # Consumer events and the deriver's checkpoint are derived from the workspace's feed (0.9 C10);
    # they go with it.
    ("consumer_events", "workspace_key"): ("workspaces", "CASCADE"),
    ("consumer_event_checkpoints", "workspace_key"): ("workspaces", "CASCADE"),
    # A workspace with subscriptions cannot be deleted (C11, C-D99).
    ("consumer_subscriptions", "workspace_key"): ("workspaces", "RESTRICT"),
    # The delivery log goes with its subscription, and a request's events and attempts with it (U5a).
    ("consumer_webhook_requests", "subscription_sequence_id"): ("consumer_subscriptions", "CASCADE"),
    ("consumer_webhook_request_events", "request_sequence_id"): ("consumer_webhook_requests", "CASCADE"),
    ("consumer_webhook_attempts", "request_sequence_id"): ("consumer_webhook_requests", "CASCADE"),
    # Publications are history and never deleted; withdrawal changes a status. Their rows would go
    # with them.
    ("publication_objects", "publication_id"): ("publications", "CASCADE"),
    ("publication_relations", "publication_id"): ("publications", "CASCADE"),
    ("publications", "derived_from_publication_id"): ("publications", "RESTRICT"),
    ("publications", "supersedes_publication_id"): ("publications", "RESTRICT"),
    ("change_sets", "derived_from_publication_id"): ("publications", "RESTRICT"),
    ("workspaces", "active_publication_id"): ("publications", "RESTRICT"),
    # Model releases are immutable and never deleted while anything is pinned to them; a draft
    # outlives the release it started from. The release's own catalogue rows go with it.
    ("model_runtime_state", "active_model_release_id"): ("model_releases", "RESTRICT"),
    ("change_sets", "model_release_id"): ("model_releases", "RESTRICT"),
    ("change_set_bases", "model_release_id"): ("model_releases", "RESTRICT"),
    ("publications", "model_release_id"): ("model_releases", "RESTRICT"),
    ("jobs", "model_release_id"): ("model_releases", "RESTRICT"),
    # A feed entry names the release its change ran under (Base 0.9 F1).
    ("audit_events", "model_release_id"): ("model_releases", "RESTRICT"),
    # A consumer event names the release that derived it (0.9 C10, C-D88).
    ("consumer_events", "model_release_id"): ("model_releases", "RESTRICT"),
    # An import profile names the release it was last checked against (0.9 J2).
    ("import_profiles", "checked_release_id"): ("model_releases", "RESTRICT"),
    ("model_drafts", "base_model_release_id"): ("model_releases", "SET NULL"),
    # A draft's history goes with its draft (0.10 A2, D4).
    ("model_draft_operations", "draft_id"): ("model_drafts", "CASCADE"),
    ("model_applications", "model_release_id"): ("model_releases", "CASCADE"),
    ("model_application_object_types", "model_release_id"): ("model_releases", "CASCADE"),
    ("model_attribute_types", "model_release_id"): ("model_releases", "CASCADE"),
    ("model_object_types", "model_release_id"): ("model_releases", "CASCADE"),
    ("model_object_type_attributes", "model_release_id"): ("model_releases", "CASCADE"),
    ("model_object_type_relations", "model_release_id"): ("model_releases", "CASCADE"),
    ("model_relation_types", "model_release_id"): ("model_releases", "CASCADE"),
    ("model_view_definitions", "model_release_id"): ("model_releases", "CASCADE"),
    # Job retention (``jobs.store``) deletes a job's inputs, items and keys itself, in chunks.
    ("job_inputs", "job_id"): ("jobs", "CASCADE"),
    ("job_items", "job_id"): ("jobs", "CASCADE"),
    ("idempotency_keys", "job_id"): ("jobs", "CASCADE"),
    # Audit events are never deleted; their subjects belong to them.
    ("audit_event_subjects", "audit_event_id"): ("audit_events", "CASCADE"),
}

_CONFDELTYPE = {"a": "NO ACTION", "r": "RESTRICT", "c": "CASCADE", "n": "SET NULL", "d": "SET DEFAULT"}


def test_the_orm_declares_the_reviewed_rules():
    declared = {
        (table.name, key.parent.name): (key.column.table.name, key.ondelete)
        for table in Base.metadata.tables.values()
        for key in table.foreign_keys
    }
    assert declared == RULES


def test_a_migrated_database_enforces_the_reviewed_rules(migrated_database):
    engine = create_engine(migrated_database())
    try:
        with engine.connect() as connection:
            rows = connection.execute(
                text(
                    "SELECT source.relname, attribute.attname, target.relname, constraint_.confdeltype "
                    "FROM pg_constraint AS constraint_ "
                    "JOIN pg_class AS source ON source.oid = constraint_.conrelid "
                    "JOIN pg_class AS target ON target.oid = constraint_.confrelid "
                    "JOIN pg_attribute AS attribute ON attribute.attrelid = constraint_.conrelid "
                    "AND attribute.attnum = constraint_.conkey[1] "
                    "WHERE constraint_.contype = 'f' AND constraint_.convalidated"
                )
            ).all()
    finally:
        engine.dispose()
    enforced = {(table, column): (target, _CONFDELTYPE[rule]) for table, column, target, rule in rows}
    assert enforced == RULES
