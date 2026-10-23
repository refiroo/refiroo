"""Roles, groups and grants (Product 0.12 Z1, ADR-044).

``roles`` holds every role: the nine predefined ones, inserted here and read-only, whose action
groups are in the code's catalogue (D279), and custom ones, whose groups are in
``role_action_groups``. ``user_groups`` and ``user_group_members`` are local groups of people
(D229). A ``grants`` row gives a role to one person, client or group at the instance (no
workspace) or in one workspace, optionally narrowing writes to applications and record types
(D228, D243, D281); it goes with its workspace.

``authorization_state`` is one row whose ``generation`` statement-level triggers raise whenever
roles, groups, memberships, grants or a principal's ``active`` change, so every process reads a
caller's permissions again on its next request (D278).

Every active person and client that exists is granted the first administrator's roles at the
instance, so what worked before keeps working (D282). New tables, triggers and rows only, in one
transaction, so an interrupted run leaves the database at ``20261028_01``.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261029_01"
down_revision = "20261028_01"
branch_labels = None
depends_on = None

# The predefined roles (D230, D257), in the catalogue's order; their groups live in the code.
PREDEFINED = (
    ("reader", "Reader", "Reads a workspace"),
    ("contributor", "Contributor", "Reads a workspace and proposes changes in change sets"),
    (
        "steward",
        "Data steward",
        "Keeps a workspace's data: edits live, in change sets and in bulk, and publishes",
    ),
    ("owner", "Data owner", "A steward who also copies and moves data and reads the change feed"),
    ("model-admin", "Model administrator", "Authors models and releases them into workspaces"),
    (
        "workspace-admin",
        "Workspace administrator",
        "Creates, renames, retires and deletes workspaces",
    ),
    (
        "integration-admin",
        "Integration administrator",
        "Manages consumer API subscriptions and reads the change feed",
    ),
    ("operator", "Operator", "Watches the running service: processes, readiness and metrics"),
    (
        "security-admin",
        "Security administrator",
        "Manages people, groups, roles, grants, clients and keys",
    ),
)
# What the first administrator, and every principal existing before Z1, holds at the instance.
FIRST_ADMINISTRATOR = (
    "security-admin",
    "owner",
    "model-admin",
    "workspace-admin",
    "integration-admin",
    "operator",
)

_TABLES = ("roles", "role_action_groups", "user_groups", "user_group_members", "grants")


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("key", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("predefined", sa.Boolean(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ux_roles_name", "roles", [sa.text("lower(name)")], unique=True)
    op.create_table(
        "role_action_groups",
        sa.Column(
            "role_id",
            sa.Integer(),
            sa.ForeignKey("roles.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("group_key", sa.String(64), primary_key=True),
    )
    op.create_table(
        "user_groups",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("public_id", sa.String(36), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ux_user_groups_name", "user_groups", [sa.text("lower(name)")], unique=True)
    op.create_table(
        "user_group_members",
        sa.Column(
            "group_id",
            sa.Integer(),
            sa.ForeignKey("user_groups.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_user_group_members_user", "user_group_members", ["user_id"])
    op.create_table(
        "grants",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("public_id", sa.String(36), nullable=False, unique=True),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True
        ),
        sa.Column(
            "client_id",
            sa.Integer(),
            sa.ForeignKey("oauth_clients.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "group_id",
            sa.Integer(),
            sa.ForeignKey("user_groups.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "role_id", sa.Integer(), sa.ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column(
            "workspace_key",
            sa.String(160),
            sa.ForeignKey("workspaces.key", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("applications", postgresql.ARRAY(sa.String(160)), nullable=False),
        sa.Column("record_types", postgresql.ARRAY(sa.String(160)), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "num_nonnulls(user_id, client_id, group_id) = 1", name="ck_grants_one_principal"
        ),
        sa.CheckConstraint(
            "workspace_key IS NOT NULL OR (cardinality(applications) = 0 "
            "AND cardinality(record_types) = 0)",
            name="ck_grants_instance_not_narrowed",
        ),
    )
    op.create_index("ix_grants_user", "grants", ["user_id"])
    op.create_index("ix_grants_client", "grants", ["client_id"])
    op.create_index("ix_grants_group", "grants", ["group_id"])
    op.create_index("ix_grants_role", "grants", ["role_id"])
    op.create_index("ix_grants_workspace", "grants", ["workspace_key", "id"])
    op.create_table(
        "authorization_state",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("generation", sa.BigInteger(), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_authorization_state_one_row"),
    )
    op.execute("INSERT INTO authorization_state (id, generation) VALUES (1, 1)")
    op.execute(
        """
        CREATE FUNCTION raise_authorization_generation() RETURNS trigger AS $$
        BEGIN
            UPDATE authorization_state SET generation = generation + 1 WHERE id = 1;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    for table in _TABLES:
        op.execute(
            f"CREATE TRIGGER {table}_authorization_generation "
            f"AFTER INSERT OR UPDATE OR DELETE OR TRUNCATE ON {table} "
            "FOR EACH STATEMENT EXECUTE FUNCTION raise_authorization_generation()"
        )
    for table in ("users", "oauth_clients"):
        op.execute(
            f"CREATE TRIGGER {table}_authorization_generation "
            f"AFTER UPDATE OF active ON {table} "
            "FOR EACH STATEMENT EXECUTE FUNCTION raise_authorization_generation()"
        )

    for key, name, description in PREDEFINED:
        op.execute(
            sa.text(
                "INSERT INTO roles (key, name, description, predefined, version, created_at, "
                "updated_at) VALUES (:key, :name, :description, true, 1, now(), now())"
            ).bindparams(key=key, name=name, description=description)
        )
    keys = ", ".join(f"'{key}'" for key in FIRST_ADMINISTRATOR)
    for column, table in (("user_id", "users"), ("client_id", "oauth_clients")):
        op.execute(
            f"""
            INSERT INTO grants (public_id, {column}, role_id, workspace_key, applications,
                                record_types, created_at)
            SELECT gen_random_uuid()::text, principal.id, roles.id, NULL, '{{}}', '{{}}', now()
            FROM {table} AS principal CROSS JOIN roles
            WHERE principal.active AND roles.key IN ({keys})
            """
        )


def downgrade() -> None:
    for table in ("users", "oauth_clients", *_TABLES):
        op.execute(f"DROP TRIGGER IF EXISTS {table}_authorization_generation ON {table}")
    op.execute("DROP FUNCTION IF EXISTS raise_authorization_generation()")
    op.drop_table("authorization_state")
    op.drop_table("grants")
    op.drop_table("user_group_members")
    op.drop_table("user_groups")
    op.drop_table("role_action_groups")
    op.drop_table("roles")
