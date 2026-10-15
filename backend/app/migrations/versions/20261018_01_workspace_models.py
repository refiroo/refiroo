"""Each workspace runs a model release of its own (Product 0.11 M1, ADR-042, D4, D24, D28, D30).

``workspace_models`` holds one row per workspace naming the release it runs, with the assignment's
own version; every existing workspace is given the release ``model_runtime_state`` selected, at
version 1. The singleton and ``model_releases.is_active`` are dropped. The unique-values triggers
(``20261007_07``) read each written record's workspace release instead of the singleton's, and the
trigger that refills ``unique_attribute_values`` when a release changes moves to
``workspace_models``, refilling only that workspace's rows. PostgreSQL runs the DDL in the
migration's transaction, so an interrupted run leaves the database at ``20261017_01``.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261018_01"
down_revision = "20261017_01"
branch_labels = None
depends_on = None

UNIQUE = "(t.definition -> 'features' ->> 'unique') = 'true'"
DIGEST = """rdm_value_digest(
    s.value_type, s.text_value, s.integer_value, s.decimal_value, s.boolean_value,
    s.date_value, s.datetime_value, s.json_value
)"""

# The rows of ``source`` (``attribute_values`` columns) whose attribute the record's workspace
# release declares unique, narrowed by ``where``.
WORKSPACE_ROWS = f"""
    INSERT INTO unique_attribute_values
        (value_id, workspace_key, attribute_type_key, object_id, value_digest)
    SELECT v.sequence_id, v.workspace_key, v.attribute_type_key, v.object_id, v.digest
    FROM (
        SELECT s.sequence_id, o.workspace_key, s.attribute_type_key, s.object_id, {DIGEST} AS digest
        FROM {{source}} s
        JOIN objects o ON o.id = s.object_id
        JOIN workspace_models m ON m.workspace_key = o.workspace_key
        JOIN model_attribute_types t
          ON t.model_release_id = {{release}} AND t.key = s.attribute_type_key AND {UNIQUE}
        WHERE {{where}}
    ) v
    WHERE v.digest IS NOT NULL
"""

KEYS = f"SELECT t.key FROM model_attribute_types t WHERE t.model_release_id = {{release}} AND {UNIQUE}"


def upgrade() -> None:
    op.create_table(
        "workspace_models",
        sa.Column("workspace_key", sa.String(160), nullable=False),
        sa.Column("model_release_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("workspace_key"),
        sa.ForeignKeyConstraint(
            ["workspace_key"],
            ["workspaces.key"],
            name="fk_workspace_models_workspace_key_workspaces",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["model_release_id"],
            ["model_releases.id"],
            name="fk_workspace_models_model_release_id_model_releases",
            ondelete="RESTRICT",
        ),
    )
    op.create_index("ix_workspace_models_model_release_id", "workspace_models", ["model_release_id"])
    op.execute("""
        INSERT INTO workspace_models (workspace_key, model_release_id, version, updated_at)
        SELECT w.key, s.active_model_release_id, 1, s.updated_at
        FROM workspaces w CROSS JOIN model_runtime_state s
    """)

    op.execute("DROP TRIGGER model_runtime_state_unique_values ON model_runtime_state")
    op.execute("DROP FUNCTION rdm_unique_values_release()")
    op.execute(f"""
        CREATE OR REPLACE FUNCTION rdm_unique_values_written() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'UPDATE' THEN
                DELETE FROM unique_attribute_values u
                USING written w WHERE u.value_id = w.sequence_id;
            END IF;
            {WORKSPACE_ROWS.format(source="written", release="m.model_release_id", where="true")};
            RETURN NULL;
        END
        $$
    """)
    # The attributes the workspace's new release makes unique gain their rows; those it no longer
    # declares unique lose them. Other workspaces' rows are untouched (D28).
    new_keys = KEYS.format(release="NEW.model_release_id")
    old_keys = KEYS.format(release="OLD.model_release_id")
    op.execute(f"""
        CREATE FUNCTION rdm_unique_values_assignment() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'INSERT' THEN
                {WORKSPACE_ROWS.format(
                    source="attribute_values",
                    release="NEW.model_release_id",
                    where="o.workspace_key = NEW.workspace_key",
                )};
            ELSIF NEW.model_release_id <> OLD.model_release_id THEN
                DELETE FROM unique_attribute_values
                WHERE workspace_key = NEW.workspace_key AND attribute_type_key NOT IN ({new_keys});
                {WORKSPACE_ROWS.format(
                    source="attribute_values",
                    release="NEW.model_release_id",
                    where=f"o.workspace_key = NEW.workspace_key AND t.key NOT IN ({old_keys})",
                )};
            END IF;
            RETURN NULL;
        END
        $$
    """)
    op.execute(
        "CREATE TRIGGER workspace_models_unique_values AFTER INSERT OR UPDATE "
        "ON workspace_models FOR EACH ROW EXECUTE FUNCTION rdm_unique_values_assignment()"
    )

    op.drop_index("ix_model_runtime_state_active_model_release_id", table_name="model_runtime_state")
    op.drop_table("model_runtime_state")
    op.drop_index("ix_model_releases_is_active", table_name="model_releases")
    op.drop_column("model_releases", "is_active")


# 20261007_07's functions, restored by the downgrade.
ACTIVE = "(SELECT active_model_release_id FROM model_runtime_state WHERE id = 1)"
SINGLETON_ROWS = f"""
    INSERT INTO unique_attribute_values
        (value_id, workspace_key, attribute_type_key, object_id, value_digest)
    SELECT v.sequence_id, o.workspace_key, v.attribute_type_key, v.object_id, v.digest
    FROM (
        SELECT s.sequence_id, s.attribute_type_key, s.object_id, {DIGEST} AS digest
        FROM {{source}} s
        WHERE s.attribute_type_key IN ({{keys}})
    ) v
    JOIN objects o ON o.id = v.object_id
    WHERE v.digest IS NOT NULL
"""


def downgrade() -> None:
    op.add_column(
        "model_releases",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("model_releases", "is_active", server_default=None)
    op.create_index("ix_model_releases_is_active", "model_releases", ["is_active"])
    op.create_table(
        "model_runtime_state",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("active_model_release_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_model_runtime_state_singleton"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["active_model_release_id"],
            ["model_releases.id"],
            name="model_runtime_state_active_model_release_id_fkey",
            ondelete="RESTRICT",
        ),
    )
    op.create_index(
        "ix_model_runtime_state_active_model_release_id",
        "model_runtime_state",
        ["active_model_release_id"],
    )
    # The default workspace's release becomes the instance's again.
    op.execute("""
        INSERT INTO model_runtime_state (id, active_model_release_id, version, updated_at)
        SELECT 1, m.model_release_id, m.version, m.updated_at
        FROM workspace_models m
        JOIN workspace_runtime_state s ON s.default_workspace_key = m.workspace_key
    """)
    op.execute("""
        UPDATE model_releases r SET is_active = true
        FROM model_runtime_state s WHERE s.active_model_release_id = r.id
    """)
    op.execute("DROP TRIGGER workspace_models_unique_values ON workspace_models")
    op.execute("DROP FUNCTION rdm_unique_values_assignment()")
    op.execute(f"""
        CREATE OR REPLACE FUNCTION rdm_unique_values_written() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'UPDATE' THEN
                DELETE FROM unique_attribute_values u
                USING written w WHERE u.value_id = w.sequence_id;
            END IF;
            {SINGLETON_ROWS.format(source="written", keys=KEYS.format(release=ACTIVE))};
            RETURN NULL;
        END
        $$
    """)
    new_keys = KEYS.format(release="NEW.active_model_release_id")
    old_keys = KEYS.format(release="OLD.active_model_release_id")
    op.execute(f"""
        CREATE FUNCTION rdm_unique_values_release() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'INSERT' THEN
                {SINGLETON_ROWS.format(source="attribute_values", keys=new_keys)};
            ELSIF NEW.active_model_release_id <> OLD.active_model_release_id THEN
                DELETE FROM unique_attribute_values WHERE attribute_type_key NOT IN ({new_keys});
                {SINGLETON_ROWS.format(source="attribute_values", keys=f"{new_keys} AND t.key NOT IN ({old_keys})")};
            END IF;
            RETURN NULL;
        END
        $$
    """)
    op.execute(
        "CREATE TRIGGER model_runtime_state_unique_values AFTER INSERT OR UPDATE "
        "ON model_runtime_state FOR EACH ROW EXECUTE FUNCTION rdm_unique_values_release()"
    )
    # Values of other workspaces' models that the singleton's release does not declare unique.
    op.execute(f"DELETE FROM unique_attribute_values WHERE attribute_type_key NOT IN ({KEYS.format(release=ACTIVE)})")
    op.drop_index("ix_workspace_models_model_release_id", table_name="workspace_models")
    op.drop_table("workspace_models")
