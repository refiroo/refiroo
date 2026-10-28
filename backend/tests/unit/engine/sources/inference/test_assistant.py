"""The inference's assistant (``engine/sources/inference/assistant.py``, 0.10 A6, on the proposal
provider since 0.16 AP1): only names for types the proposals add, above the floor and different,
one per type, each a ``setLabel`` proposal carrying its provenance."""

from app.engine.sources.inference import assistant as assistants
from app.engine.sources.inference.assistant import AssistantType, NameAnswer

TYPES = [AssistantType("p1", "ctry", "Ctry"), AssistantType("p2", "cur", "Cur")]


def _answer(*items: tuple[str, str, str, float]) -> NameAnswer:
    return NameAnswer.model_validate(
        {
            "suggestions": [
                {"proposal": p, "key": k, "name": n, "reason": "Codes", "confidence": c}
                for p, k, n, c in items
            ]
        }
    )


def test_only_names_for_named_types_above_the_floor_and_different_are_kept():
    answer = _answer(
        ("p1", "ctry", "Country", 0.9),
        ("p1", "ctry", "Nation", 0.95),
        ("p9", "other", "Other", 0.9),
        ("p2", "cur", "Cur", 0.9),
        ("p2", "cur", "Currency", 0.4),
        ("p2", "cur", "  ", 0.9),
    )
    found = assistants.suggestions(answer, TYPES, 0.5)
    assert [(s.key, s.name) for s in found] == [("ctry", "Nation")]


def test_the_request_holds_the_sheets_and_types_and_asks_for_the_answer_shape():
    request = assistants.request([{"name": "Items", "headers": ["Ctry"]}], TYPES)
    assert request.purpose == "modelNames" and request.answer is NameAnswer
    assert request.context["types"][0] == {"proposal": "p1", "key": "ctry", "name": "Ctry"}
    assert request.prompt_version == assistants.PROMPT_VERSION


def test_a_proposal_body_renames_the_type_and_carries_its_provenance():
    (suggestion,) = assistants.suggestions(_answer(("p1", "ctry", "Country", 0.834)), TYPES, 0.5)
    body = assistants.proposal_body(suggestion, "Ctry", provider="claude", model="m")
    assert body["operations"] == [
        {"kind": "setLabel", "element": {"objectType": "ctry"}, "name": "Country"}
    ]
    assert body["evidence"]["origin"] == {
        "kind": "ai",
        "provider": "claude",
        "model": "m",
        "promptVersion": assistants.PROMPT_VERSION,
        "confidence": 0.83,
        "reason": "Codes",
    }
