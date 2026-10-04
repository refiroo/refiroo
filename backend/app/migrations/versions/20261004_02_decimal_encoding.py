"""Decimal encoding for every stored scale (0.9 T1a fix).

``20261004_01`` rounded decimals with a ``numeric`` step of scale 28 plus the value's leading zeros.
A value below about 1e-16356 overflowed that step (capture and publish answered 500), and below
about 1e-974 the halved step fell under PostgreSQL's 1,000-digit division scale, so a 28-digit
value with an odd last digit lost one in its last place. ``rdm_decimal_text`` now works on the
digit string: no ``numeric`` is ever built beyond the value's own scale.

``rdm_value_json`` becomes one ``CASE`` expression declared ``STABLE`` (``to_char`` is stable), so
PostgreSQL inlines it into the copy statements instead of calling it per value. PostgreSQL runs the
DDL in the migration's transaction, so an interrupted run leaves the database at ``20261004_01``.
"""

from alembic import op

revision = "20261004_02"
down_revision = "20261004_01"
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Python's form: ``format(canonical_decimal(value), "f")``, which rounds to 28 significant
    # digits, half to even, and drops trailing zeros and the exponent.
    op.execute("""
        CREATE FUNCTION rdm_decimal_text(value numeric) RETURNS text
        LANGUAGE plpgsql IMMUTABLE STRICT PARALLEL SAFE AS $$
        DECLARE
            plain text := abs(value)::text;
            whole text := split_part(plain, '.', 1);
            digits text := whole || split_part(plain, '.', 2);
            -- Digits before the decimal point, counted from the first significant digit.
            point integer := length(whole) - (length(digits) - length(ltrim(digits, '0')));
            rest text;
        BEGIN
            IF value = 0 THEN
                RETURN '0';
            END IF;
            digits := rtrim(ltrim(digits, '0'), '0');
            IF length(digits) > 28 THEN
                -- ``rest`` ends in a non-zero digit, so a lone '5' is an exact tie.
                rest := substr(digits, 29);
                digits := left(digits, 28);
                IF left(rest, 1) > '5' OR (left(rest, 1) = '5' AND (
                    length(rest) > 1 OR right(digits, 1) IN ('1', '3', '5', '7', '9')
                )) THEN
                    digits := (digits::numeric + 1)::text;
                    IF length(digits) > 28 THEN
                        point := point + 1;  -- 99..9 carried to 100..0
                    END IF;
                END IF;
                digits := rtrim(digits, '0');
            END IF;
            RETURN CASE WHEN value < 0 THEN '-' ELSE '' END || CASE
                WHEN point <= 0 THEN '0.' || repeat('0', -point) || digits
                WHEN point >= length(digits) THEN digits || repeat('0', point - length(digits))
                ELSE left(digits, point) || '.' || substr(digits, point + 1)
            END;
        END
        $$
    """)
    op.execute("""
        CREATE OR REPLACE FUNCTION rdm_value_json(
            value_type text, text_value text, integer_value integer,
            decimal_value numeric, boolean_value boolean, date_value date,
            datetime_value timestamptz, "json_value" json
        ) RETURNS json LANGUAGE sql STABLE PARALLEL SAFE AS $$
            SELECT CASE value_type
                WHEN 'text' THEN to_json(text_value)
                WHEN 'longText' THEN to_json(text_value)
                WHEN 'integer' THEN to_json(integer_value)
                WHEN 'decimal' THEN to_json(rdm_decimal_text(decimal_value))
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
    # Revision 20261004_01's definition, as that revision installed it.
    op.execute("""
        CREATE OR REPLACE FUNCTION rdm_value_json(
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
    op.execute("DROP FUNCTION rdm_decimal_text(numeric)")
