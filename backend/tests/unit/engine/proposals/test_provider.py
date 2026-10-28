"""The answer schema structured output is asked for (``engine/proposals/provider.py``)."""

from pydantic import BaseModel

from app.engine.proposals.provider import answer_schema


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
