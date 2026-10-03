"""``models/database.py``: the indexes the engine's reads seek by.

The live unique-value check once read every value of the attribute, so a write with a unique
attribute cost in proportion to the records holding it (a B2 budget finding). The value index lets
it seek to the value.
"""

from sqlalchemy import create_engine, text


def test_a_unique_value_is_found_through_the_value_index(migrated_database):
    engine = create_engine(migrated_database())
    try:
        with engine.connect() as connection:
            # An empty table plans a sequential scan; forbidding it shows the index answers.
            connection.execute(text("SET enable_seqscan = off"))
            plan = " ".join(
                row[0]
                for row in connection.execute(
                    text(
                        "EXPLAIN SELECT objects.id FROM objects JOIN attribute_values "
                        "ON attribute_values.object_id = objects.id "
                        "WHERE attribute_values.attribute_type_key = 'code' "
                        "AND attribute_values.text_value = 'A-1' AND objects.workspace_key = 'default' "
                        "LIMIT 1"
                    )
                )
            )
    finally:
        engine.dispose()
    assert "ix_attribute_values_key_text" in plan, plan
