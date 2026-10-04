"""Value encoding for database-local snapshot copies (0.9 T1a)."""

from alembic import op

revision = "20261004_01"
down_revision = "20261003_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE FUNCTION rdm_value_json(
            value_type text, text_value text, integer_value integer,
            decimal_value numeric, boolean_value boolean, date_value date,
            datetime_value timestamptz, "json_value" json
        ) RETURNS json LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
            SELECT CASE value_type
                WHEN 'text' THEN to_json(text_value)
                WHEN 'longText' THEN to_json(text_value)
                WHEN 'integer' THEN to_json(integer_value)
                WHEN 'decimal' THEN (
                    -- Decimal.normalize uses Python's default precision (28) and half-even
                    -- rounding. PostgreSQL round uses half-away, so correct exact odd ties.
                    WITH precision AS (
                        SELECT 28 - CASE WHEN abs(decimal_value) >= 1
                            THEN length(split_part(abs(decimal_value)::text, '.', 1))
                            ELSE -length(substring(split_part(abs(decimal_value)::text, '.', 2) from '^0*'))
                        END AS scale
                    ), rounded AS (
                        SELECT round(decimal_value, scale) AS value,
                               ('1e' || (-scale)::text)::numeric AS step FROM precision
                    )
                    SELECT to_json(trim_scale(CASE
                        WHEN abs(decimal_value - value) = step / 2
                             AND mod(abs(value / step), 2) = 1
                        THEN value - sign(decimal_value) * step
                        ELSE value END)::text) FROM rounded
                )
                WHEN 'boolean' THEN to_json(boolean_value)
                WHEN 'date' THEN to_json(to_char(date_value, 'YYYY-MM-DD'))
                WHEN 'dateTime' THEN to_json(
                    to_char(datetime_value AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS')
                    || CASE WHEN extract(microseconds FROM datetime_value AT TIME ZONE 'UTC')::bigint % 1000000 = 0
                            THEN '' ELSE to_char(datetime_value AT TIME ZONE 'UTC', '.US') END
                    || '+00:00')
                WHEN 'json' THEN "json_value"
            END
        $$
    """)


def downgrade() -> None:
    op.execute(
        "DROP FUNCTION rdm_value_json(text, text, integer, numeric, boolean, date, timestamptz, json)"
    )
