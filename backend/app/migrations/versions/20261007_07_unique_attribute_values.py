"""Unique attribute values held by the database (Base 0.9 J2a, ADR-010, D75–D78).

``unique_attribute_values`` has one row per live value of an attribute the active release declares
``unique`` (empty text is no value), keyed by workspace, attribute and the SHA-256 of the value's
canonical JSON (``rdm_value_digest``), under a deferred unique constraint. PostgreSQL keeps it:
statement triggers on ``attribute_values`` add the rows of written values, the foreign key's
cascade removes them, and a trigger on ``model_runtime_state`` adds and removes rows as the active
release declares ``unique`` on more or fewer attributes. The revision fills the table from the
stored values. PostgreSQL runs the DDL in the migration's transaction, so an interrupted run leaves
the database at ``20261007_06``.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261007_07"
down_revision = "20261007_06"
branch_labels = None
depends_on = None

# The keys of the attributes ``release`` declares unique.
UNIQUE_KEYS = """
    SELECT t.key FROM model_attribute_types t
    WHERE t.model_release_id = {release}
      AND (t.definition -> 'features' ->> 'unique') = 'true'
"""

# The rows of ``source`` (``attribute_values`` columns) whose attribute is in ``keys``.
ROWS = """
    INSERT INTO unique_attribute_values
        (value_id, workspace_key, attribute_type_key, object_id, value_digest)
    SELECT v.sequence_id, o.workspace_key, v.attribute_type_key, v.object_id, v.digest
    FROM (
        SELECT s.sequence_id, s.attribute_type_key, s.object_id, rdm_value_digest(
            s.value_type, s.text_value, s.integer_value, s.decimal_value, s.boolean_value,
            s.date_value, s.datetime_value, s.json_value
        ) AS digest
        FROM {source} s
        WHERE s.attribute_type_key IN ({keys})
    ) v
    JOIN objects o ON o.id = v.object_id
    WHERE v.digest IS NOT NULL
"""

ACTIVE = "(SELECT active_model_release_id FROM model_runtime_state WHERE id = 1)"


def upgrade() -> None:
    op.create_table(
        "unique_attribute_values",
        sa.Column(
            "value_id",
            sa.Integer(),
            sa.ForeignKey("attribute_values.sequence_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("workspace_key", sa.String(160), nullable=False),
        sa.Column("attribute_type_key", sa.String(160), nullable=False),
        sa.Column("object_id", sa.String(36), nullable=False),
        sa.Column("value_digest", sa.LargeBinary(), nullable=False),
        sa.UniqueConstraint(
            "workspace_key",
            "attribute_type_key",
            "value_digest",
            name="uq_unique_attribute_values",
            deferrable=True,
            initially="DEFERRED",
        ),
    )
    op.create_index(
        "ix_unique_attribute_values_object_id", "unique_attribute_values", ["object_id"]
    )
    # Empty text is no value, so records may share it (the write rule's E-D4 exemption).
    op.execute("""
        CREATE FUNCTION rdm_value_digest(
            value_type text, text_value text, integer_value integer,
            decimal_value numeric, boolean_value boolean, date_value date,
            datetime_value timestamptz, "json_value" json
        ) RETURNS bytea LANGUAGE sql STABLE PARALLEL SAFE AS $$
            SELECT CASE WHEN text_value = '' THEN NULL ELSE sha256(convert_to(rdm_value_json(
                value_type, text_value, integer_value, decimal_value, boolean_value,
                date_value, datetime_value, "json_value"
            )::text, 'UTF8')) END
        $$
    """)
    op.execute(f"""
        CREATE FUNCTION rdm_unique_values_written() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'UPDATE' THEN
                DELETE FROM unique_attribute_values u
                USING written w WHERE u.value_id = w.sequence_id;
            END IF;
            {ROWS.format(source="written", keys=UNIQUE_KEYS.format(release=ACTIVE))};
            RETURN NULL;
        END
        $$
    """)
    for event in ("INSERT", "UPDATE"):
        op.execute(
            f"CREATE TRIGGER attribute_values_unique_{event.lower()} AFTER {event} "
            "ON attribute_values REFERENCING NEW TABLE AS written "
            "FOR EACH STATEMENT EXECUTE FUNCTION rdm_unique_values_written()"
        )
    # The attributes the new release makes unique gain their rows; those it no longer declares
    # unique lose them.
    new_keys = UNIQUE_KEYS.format(release="NEW.active_model_release_id")
    old_keys = UNIQUE_KEYS.format(release="OLD.active_model_release_id")
    op.execute(f"""
        CREATE FUNCTION rdm_unique_values_release() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'INSERT' THEN
                {ROWS.format(source="attribute_values", keys=new_keys)};
            ELSIF NEW.active_model_release_id <> OLD.active_model_release_id THEN
                DELETE FROM unique_attribute_values WHERE attribute_type_key NOT IN ({new_keys});
                {ROWS.format(source="attribute_values", keys=f"{new_keys} AND t.key NOT IN ({old_keys})")};
            END IF;
            RETURN NULL;
        END
        $$
    """)
    op.execute(
        "CREATE TRIGGER model_runtime_state_unique_values AFTER INSERT OR UPDATE "
        "ON model_runtime_state FOR EACH ROW EXECUTE FUNCTION rdm_unique_values_release()"
    )
    op.execute(ROWS.format(source="attribute_values", keys=UNIQUE_KEYS.format(release=ACTIVE)))


def downgrade() -> None:
    op.execute("DROP TRIGGER model_runtime_state_unique_values ON model_runtime_state")
    op.execute("DROP FUNCTION rdm_unique_values_release()")
    for event in ("insert", "update"):
        op.execute(f"DROP TRIGGER attribute_values_unique_{event} ON attribute_values")
    op.execute("DROP FUNCTION rdm_unique_values_written()")
    op.execute(
        "DROP FUNCTION rdm_value_digest(text, text, integer, numeric, boolean, date, timestamptz, json)"
    )
    op.drop_index("ix_unique_attribute_values_object_id", table_name="unique_attribute_values")
    op.drop_table("unique_attribute_values")
