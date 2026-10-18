"""A workspace's data migrated to another release (Product 0.11 V1, D68–D74).

``jobs.kind`` gains ``migration``, and ``job_items`` an index of a migration's items by outcome. ``rdm_convert_value(value, from, to)`` converts one value's JSON
form from one value type to another (D69), answering SQL ``NULL`` when it does not convert: a
migration converts attribute values and relation attribute values with it in set statements.
PostgreSQL runs the DDL in the migration's transaction, so an interrupted run leaves the database
at ``20261018_01``.
"""

from alembic import op

revision = "20261019_01"
down_revision = "20261018_01"
branch_labels = None
depends_on = None

KINDS = (
    "kind IN ('batch', 'import', 'export', 'profile', 'dryRun', 'inference', 'profileCheck', "
    "'migration')"
)
OLD_KINDS = (
    "kind IN ('batch', 'import', 'export', 'profile', 'dryRun', 'inference', 'profileCheck')"
)

# The value's text, as an import reads a cell (``imports/cells.py``): a whole number, a decimal
# without an exponent's surprises, ``true``/``false`` ignoring case, an ISO 8601 date or instant
# (one without a zone is UTC). Values come in their stored JSON form (``rdm_value_json``) and leave
# in it: a decimal as its canonical text, a date as ``YYYY-MM-DD``, an instant in UTC.
CONVERT = r"""
CREATE FUNCTION rdm_convert_value(value json, from_type text, to_type text) RETURNS json
LANGUAGE plpgsql STABLE PARALLEL SAFE AS $$
DECLARE
    raw text := CASE WHEN jsonb_typeof(value::jsonb) = 'string' THEN value #>> '{}' ELSE value::text END;
    trimmed text := btrim(raw);
    instant timestamptz;
BEGIN
    IF value IS NULL OR jsonb_typeof(value::jsonb) = 'null' THEN
        RETURN NULL;
    END IF;
    IF from_type = to_type
        OR (from_type IN ('text', 'longText') AND to_type IN ('text', 'longText')) THEN
        RETURN value;
    END IF;
    IF to_type IN ('text', 'longText') THEN
        -- JSON as its text, so that it converts back.
        RETURN to_json(CASE WHEN from_type = 'json' THEN value::text ELSE raw END);
    END IF;
    IF to_type = 'json' THEN
        IF from_type IN ('text', 'longText') THEN
            RETURN CASE WHEN pg_input_is_valid(raw, 'json') THEN raw::json END;
        END IF;
        RETURN value;
    END IF;
    IF from_type = 'json' THEN
        RETURN NULL;
    END IF;
    IF to_type = 'integer' THEN
        IF from_type IN ('text', 'longText') AND trimmed ~ '^[+-]?\d+$'
            AND trimmed::numeric BETWEEN -2147483648 AND 2147483647 THEN
            RETURN to_json(trimmed::integer);
        ELSIF from_type = 'decimal' AND raw::numeric = trunc(raw::numeric)
            AND raw::numeric BETWEEN -2147483648 AND 2147483647 THEN
            RETURN to_json(raw::numeric::integer);
        END IF;
        RETURN NULL;
    END IF;
    IF to_type = 'decimal' THEN
        IF from_type = 'integer'
            OR (from_type IN ('text', 'longText')
                AND trimmed ~ '^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d{1,4})?$') THEN
            RETURN to_json(rdm_decimal_text(trimmed::numeric));
        END IF;
        RETURN NULL;
    END IF;
    IF to_type = 'boolean' THEN
        IF from_type IN ('text', 'longText') AND lower(trimmed) IN ('true', 'false') THEN
            RETURN to_json(lower(trimmed) = 'true');
        END IF;
        RETURN NULL;
    END IF;
    IF to_type = 'date' THEN
        IF from_type IN ('text', 'longText') AND trimmed ~ '^\d{4}-\d{2}-\d{2}$'
            AND pg_input_is_valid(trimmed, 'date') THEN
            RETURN to_json(to_char(trimmed::date, 'YYYY-MM-DD'));
        ELSIF from_type = 'dateTime' THEN
            instant := raw::timestamptz;
            IF (instant AT TIME ZONE 'UTC')::time = '00:00' THEN
                RETURN to_json(to_char(instant AT TIME ZONE 'UTC', 'YYYY-MM-DD'));
            END IF;
        END IF;
        RETURN NULL;
    END IF;
    IF to_type = 'dateTime' THEN
        IF from_type = 'date' THEN
            instant := (raw::date)::timestamp AT TIME ZONE 'UTC';
        ELSIF from_type IN ('text', 'longText')
            AND trimmed ~ '^\d{4}-\d{2}-\d{2}([T ]\d{2}:\d{2}(:\d{2}(\.\d{1,6})?)?)?(Z|[+-]\d{2}(:?\d{2})?)?$'
            AND pg_input_is_valid(trimmed, 'timestamptz') THEN
            instant := CASE WHEN trimmed ~ '(Z|[+-]\d{2}(:?\d{2})?)$' AND length(trimmed) > 10
                THEN trimmed::timestamptz ELSE trimmed::timestamp AT TIME ZONE 'UTC' END;
        ELSE
            RETURN NULL;
        END IF;
        RETURN rdm_value_json('dateTime', NULL, NULL, NULL, NULL, NULL, instant, NULL);
    END IF;
    RETURN NULL;
END
$$
"""


def upgrade() -> None:
    op.drop_constraint("ck_job_kind", "jobs", type_="check")
    op.create_check_constraint("ck_job_kind", "jobs", KINDS)
    op.execute(CONVERT)
    # A migration's items read by outcome.
    op.execute(
        "CREATE INDEX ix_job_items_outcome ON job_items (job_id, (outcome ->> 'outcome'), "
        "item_index) WHERE (outcome ->> 'outcome') IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX ix_job_items_outcome")
    op.execute("DROP FUNCTION rdm_convert_value(json, text, text)")
    op.execute("DELETE FROM jobs WHERE kind = 'migration'")
    op.drop_constraint("ck_job_kind", "jobs", type_="check")
    op.create_check_constraint("ck_job_kind", "jobs", OLD_KINDS)
