"""The optional assistant's interface (``engine/sources/inference/assistant.py``, 0.10 A6, D95): off
unless configured, its suggestions only for types the proposals add, and a failure a warning."""

import sys
import types

import pytest

from app.engine.sources.inference import assistant as assistants
from app.engine.sources.inference.assistant import (
    AssistantRequest,
    AssistantSheet,
    AssistantSuggestion,
    AssistantType,
)

REQUEST = AssistantRequest(
    [AssistantSheet("Items", ["Ctry", "Name"], [["DE", "Pen"], ["FR", "Ruler"]])],
    [AssistantType("p1", "ctry", "Ctry")],
)


class Fake:
    def __init__(self, answer=None, fails=False):
        self.answer, self.fails, self.seen = answer or [], fails, []

    def suggest(self, request):
        self.seen.append(request)
        if self.fails:
            raise RuntimeError("provider down")
        return self.answer


def test_no_setting_no_assistant_and_a_setting_names_a_factory(monkeypatch):
    assert assistants.load_assistant("") is None
    module = types.ModuleType("rdm_fake_assistant")
    module.make = lambda: Fake()
    monkeypatch.setitem(sys.modules, "rdm_fake_assistant", module)
    assert isinstance(assistants.load_assistant("rdm_fake_assistant:make"), Fake)
    with pytest.raises(ImportError):
        assistants.load_assistant("rdm_missing_assistant:make")


def test_only_suggestions_for_types_the_proposals_add_are_kept():
    fake = Fake([AssistantSuggestion("p1", "ctry", "Country", "ISO codes"), AssistantSuggestion("p9", "other", "Other"), AssistantSuggestion("p1", "ctry", " ")])
    found, warning = assistants.suggestions(fake, REQUEST)
    assert warning is None and [s.name for s in found] == ["Country"]
    assert fake.seen == [REQUEST]
    body = assistants.proposal_body(found[0], "Ctry")
    assert body["operations"] == [{"kind": "setLabel", "element": {"objectType": "ctry"}, "name": "Country"}]


def test_a_failing_assistant_is_a_warning_and_suggests_nothing():
    found, warning = assistants.suggestions(Fake(fails=True), REQUEST)
    assert found == [] and "RuntimeError" in warning
