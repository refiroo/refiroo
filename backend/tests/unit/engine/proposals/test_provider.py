"""The answer schema structured output is asked for (``engine/proposals/provider.py``)."""

from pydantic import BaseModel

from app.engine.proposals.provider import answer_example, answer_schema


class Inner(BaseModel):
    name: str
    confidence: float = 0.5


class Answer(BaseModel):
    items: list[Inner]


def test_the_schema_closes_every_object_and_requires_every_property():
    schema = answer_schema(Answer)
    inner = schema["$defs"]["Inner"]
    assert schema["additionalProperties"] is False and schema["required"] == ["items"]
    assert inner["additionalProperties"] is False and inner["required"] == ["name", "confidence"]


def test_the_example_shows_the_answer_to_fill_in_not_the_schema():
    assert answer_example(Answer) == {"items": [{"name": "<name>", "confidence": 0}]}
