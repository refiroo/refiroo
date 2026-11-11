"""SQL snapshot encoding preserves the stored value's Python JSON form (T1a)."""

from datetime import UTC, date, datetime, timedelta, timezone
from decimal import Decimal
from random import Random

from sqlalchemy import Numeric, func, select
from sqlalchemy.orm import Session

from app.db import get_engine
from app.engine.records.values import VALUE_COLUMNS, canonical_decimal, stored_json_value
from app.models.database import AttributeValue, RdmObject


def test_sql_encoding_equals_python_for_every_stored_value_type(seeded):
    rng = Random(91)
    cases = {
        "text": ["", '"quoted"\\', "ž漢字"],
        "longText": ["", "line\n" * 30],
        "integer": [0, -(2**31), 2**31 - 1, *[rng.randrange(-(2**31), 2**31) for _ in range(8)]],
        "decimal": [
            Decimal(v)
            for v in [
                "0",
                "-0.000",
                "12.3400",
                "1E+30",
                "1E-30",
                "-42.500",
                "123456789012345678901234567890",
                *[
                    f"{sign}{digits}{tail}"
                    for sign in ("", "-")
                    for digits in ("1234567890123456789012345678", "1234567890123456789012345679")
                    for tail in ("49", "50", "51")
                ],
                *[str(rng.randrange(10**29, 10**30)) for _ in range(8)],
                # PostgreSQL's scale limits, and an odd last digit where its division scale ends.
                "1E-16383",
                "-1E-16383",
                "1E+131071",
                "1.000000000000000000000000001E-1000",
                "9999999999999999999999999999.5",
                "-0.99999999999999999999999999995",
                # Every scale a column holds, with up to 28 and with over 28 significant digits.
                *[
                    f"{rng.choice(('', '-'))}{rng.randrange(1, 10**digits)}E{exponent}"
                    for digits in (1, 28, 30)
                    for exponent in (rng.randrange(-16383, -1000), rng.randrange(-1000, 1000))
                ],
            ]
        ],
        "boolean": [True, False],
        "date": [date(1, 1, 1), date(9999, 12, 31), date(2024, 2, 29)],
        "dateTime": [
            datetime(2024, 2, 29, 12, 30, 45, microsecond=us, tzinfo=zone)
            for us in (0, 1, 120000, 999999)
            for zone in (UTC, timezone(timedelta(hours=5, minutes=30)))
        ]
        # The calendar's ends, a day in: the driver reads an instant in the session's time zone.
        + [datetime(1, 1, 2, tzinfo=UTC), datetime(9999, 12, 30, 23, 59, 59, 999999, tzinfo=UTC)],
        "json": [{"nested": [1, False, None]}, ["漢", 2], "scalar", 1, True],
    }
    assert cases.keys() == VALUE_COLUMNS.keys()
    with Session(get_engine()) as session:
        object_id = session.scalar(select(RdmObject.id).limit(1))
        for kind, column in VALUE_COLUMNS.items():
            for value in [*cases[kind], None]:
                row = AttributeValue(
                    object_id=object_id,
                    attribute_type_key="encoding-probe",
                    value_type=kind,
                    **{column: value},
                )
                session.add(row)
                session.flush()
                session.refresh(row)
                encoded = session.scalar(
                    select(
                        func.rdm_value_json(
                            AttributeValue.value_type,
                            *[
                                getattr(AttributeValue, name)
                                for name in dict.fromkeys(VALUE_COLUMNS.values())
                            ],
                        )
                    ).where(AttributeValue.id == row.id)
                )
                assert encoded == stored_json_value(getattr(row, column)), (kind, value, encoded)
                if kind == "decimal" and value is not None:
                    # A copied typed index holds the decimal the flush hook derives from the JSON.
                    indexed = session.scalar(
                        select(
                            func.rdm_decimal_text(AttributeValue.decimal_value).cast(Numeric)
                        ).where(AttributeValue.id == row.id)
                    )
                    assert indexed == canonical_decimal(value), value
                session.delete(row)
                session.flush()


# Stored JSON forms of each value type (``rdm_value_json``): text that reads as every other type and
# as none, numbers with and without a fraction, an instant at midnight and one not.
SAMPLES = {
    "text": ["12", "12.5", "true", "2026-10-18", "2026-10-18T10:00:00Z", '{"a": 1}', "words"],
    "longText": ["12", "12.5", "true", "2026-10-18", "2026-10-18T10:00:00Z", '{"a": 1}', "words"],
    "integer": [12, -3],
    "decimal": ["12", "12.5"],
    "boolean": [True, False],
    "date": ["2026-10-18"],
    "dateTime": ["2026-10-18T00:00:00Z", "2026-10-18T10:30:00Z"],
    "json": [{"a": 1}, [1, 2], "x"],
}


def test_conversion_classes_hold_to_the_database_function(seeded):
    """Every value-type pair's class (``always``, ``partial``, ``never``) is what ``rdm_convert_value``
    does with the samples: always converts each, never none, partial some (0.11 X1, D107)."""
    import json

    from sqlalchemy import text

    from app.engine.records.values import conversion

    with Session(get_engine()) as session:
        for source, values in SAMPLES.items():
            for target in VALUE_COLUMNS:
                converted = [
                    session.scalar(
                        text(
                            "SELECT rdm_convert_value(CAST(:value AS json), :source, :target) IS NOT NULL"
                        ),
                        {"value": json.dumps(value), "source": source, "target": target},
                    )
                    for value in values
                ]
                expected = conversion(source, target)
                found = "always" if all(converted) else "never" if not any(converted) else "partial"
                assert found == expected, (source, target, converted)
    assert conversion("text", "colour") == "never"
