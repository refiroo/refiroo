"""Consumer API grants, and who created a subscription (Product 0.12 Z3, D306, D310).

A grant names a role or a consumer API, exactly one: ``grants.role_id`` becomes nullable beside the
new ``consumer_api``, and a consumer API grant is always in one workspace and never narrowed.
``consumer_subscriptions`` gain the person or client that created them, at most one, never removed
while a row names them (D237); subscriptions from before name nobody. One transaction, so an
interrupted run leaves the database at ``20261030_01``.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261031_01"
down_revision = "20261030_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("grants", "role_id", existing_type=sa.Integer(), nullable=True)
    op.add_column("grants", sa.Column("consumer_api", sa.String(160), nullable=True))
    op.create_check_constraint(
        "ck_grants_role_or_consumer_api", "grants", "num_nonnulls(role_id, consumer_api) = 1"
    )
    op.create_check_constraint(
        "ck_grants_consumer_api_scope",
        "grants",
        "consumer_api IS NULL OR (workspace_key IS NOT NULL AND cardinality(applications) = 0 "
        "AND cardinality(record_types) = 0)",
    )
    op.create_index("ix_grants_consumer_api", "grants", ["consumer_api", "workspace_key"])
    for kind, table in (("user", "users"), ("client", "oauth_clients")):
        op.add_column(
            "consumer_subscriptions",
            sa.Column(
                f"created_by_{kind}_id",
                sa.Integer(),
                sa.ForeignKey(f"{table}.id", ondelete="RESTRICT"),
                nullable=True,
            ),
        )
        op.create_index(
            f"ix_consumer_subscriptions_created_by_{kind}",
            "consumer_subscriptions",
            [f"created_by_{kind}_id"],
        )
    op.create_check_constraint(
        "ck_consumer_subscriptions_one_created_by",
        "consumer_subscriptions",
        "num_nonnulls(created_by_user_id, created_by_client_id) <= 1",
    )


def downgrade() -> None:
    op.drop_constraint("ck_consumer_subscriptions_one_created_by", "consumer_subscriptions")
    for kind in ("client", "user"):
        op.drop_index(f"ix_consumer_subscriptions_created_by_{kind}", "consumer_subscriptions")
        op.drop_column("consumer_subscriptions", f"created_by_{kind}_id")
    op.drop_index("ix_grants_consumer_api", "grants")
    op.drop_constraint("ck_grants_consumer_api_scope", "grants")
    op.drop_constraint("ck_grants_role_or_consumer_api", "grants")
    op.execute("DELETE FROM grants WHERE consumer_api IS NOT NULL")
    op.drop_column("grants", "consumer_api")
    op.alter_column("grants", "role_id", existing_type=sa.Integer(), nullable=False)
