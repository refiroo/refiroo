"""A relationships grid's filter on the relationship's own value (0.13 RV)."""

from types import SimpleNamespace

from sqlalchemy import JSON, column, table
from sqlalchemy.dialects import postgresql

from app.engine.reads.relation_grid import _relation_condition


def _condition(value_type: str, operator: str, lexical: str) -> str:
    model = SimpleNamespace(attribute_type=lambda _key: SimpleNamespace(valueType=value_type))
    relation = table("relation", column("attributes", JSON))
    expression = _relation_condition(model, relation, "flag", operator, lexical)
    return str(expression.compile(dialect=postgresql.dialect()))


def test_a_yes_or_no_value_filters_by_equality_alone():
    """Given a Yes or no relationship value. When the grid filters it with eq true or false. Then
    the condition is built (only the asked comparison, not every operator's)."""
    assert "= true" in _condition("boolean", "eq", "true")
    assert "= false" in _condition("boolean", "eq", "false")
