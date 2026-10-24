"""Who made each change (Product 0.12 Z4, D313, D315).

``audit_events`` gain the actor beside the cause: ``actor_kind`` (``user``, ``client`` or
``engine``) and the person or client, never removed while an entry names them (D237); entries from
before name nobody and read "Before sign-in". Change sets gain their creator, publications their
publisher and withdrawer, and draft and mapping operations their author, replacing the ``author``
string no path ever wrote. The new indexes are partial, so existing rows add nothing to them. One
transaction, so an interrupted run leaves the database at ``20261031_01``.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261101_01"
down_revision = "20261031_01"
branch_labels = None
depends_on = None

# (table, column prefix, constraint and index stem)
_PRINCIPALS = (
    ("change_sets", "created_by", "change_sets_created_by"),
    ("publications", "published_by", "publications_published_by"),
    ("publications", "withdrawn_by", "publications_withdrawn_by"),
    ("model_draft_operations", "author", "model_draft_operations_author"),
    ("model_mapping_operations", "author", "model_mapping_operations_author"),
)
_KINDS = (("user", "users"), ("client", "oauth_clients"))


def _principal_columns(table: str, prefix: str, stem: str) -> None:
    for kind, target in _KINDS:
        op.add_column(
            table,
            sa.Column(
                f"{prefix}_{kind}_id",
                sa.Integer(),
                sa.ForeignKey(f"{target}.id", ondelete="RESTRICT"),
                nullable=True,
            ),
        )
        op.create_index(
            f"ix_{stem}_{kind}",
            table,
            [f"{prefix}_{kind}_id"],
            postgresql_where=sa.text(f"{prefix}_{kind}_id IS NOT NULL"),
        )
    op.create_check_constraint(
        f"ck_{stem}_one", table, f"num_nonnulls({prefix}_user_id, {prefix}_client_id) <= 1"
    )


def upgrade() -> None:
    op.add_column("audit_events", sa.Column("actor_kind", sa.String(20), nullable=True))
    _principal_columns("audit_events", "actor", "audit_events_actor")
    op.create_check_constraint(
        "ck_audit_events_actor_kind",
        "audit_events",
        "(actor_kind IS NULL AND num_nonnulls(actor_user_id, actor_client_id) = 0)"
        " OR (actor_kind = 'engine' AND num_nonnulls(actor_user_id, actor_client_id) = 0)"
        " OR (actor_kind = 'user' AND actor_user_id IS NOT NULL)"
        " OR (actor_kind = 'client' AND actor_client_id IS NOT NULL)",
    )
    # Security events newest first (D317): outside every workspace, so the feed's indexes miss them.
    op.create_index(
        "ix_audit_events_security",
        "audit_events",
        ["occurred_at", "sequence_id"],
        postgresql_where=sa.text(
            "aggregate_type IN ('user', 'group', 'role', 'grant', 'client', "
            "'token-signing-key', 'sign-in')"
        ),
    )
    for table, prefix, stem in _PRINCIPALS:
        _principal_columns(table, prefix, stem)
    op.drop_column("model_draft_operations", "author")
    op.drop_column("model_mapping_operations", "author")


def downgrade() -> None:
    for table in ("model_mapping_operations", "model_draft_operations"):
        op.add_column(table, sa.Column("author", sa.String(300), nullable=True))
    for table, prefix, stem in (
        *reversed(_PRINCIPALS),
        ("audit_events", "actor", "audit_events_actor"),
    ):
        if table == "audit_events":
            op.drop_index("ix_audit_events_security", "audit_events")
            op.drop_constraint("ck_audit_events_actor_kind", "audit_events")
        op.drop_constraint(f"ck_{stem}_one", table)
        for kind, _ in reversed(_KINDS):
            op.drop_index(f"ix_{stem}_{kind}", table)
            op.drop_column(table, f"{prefix}_{kind}_id")
    op.drop_column("audit_events", "actor_kind")
