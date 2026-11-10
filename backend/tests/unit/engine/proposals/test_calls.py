"""Asking the provider (``engine/proposals/calls.py``, AP-D1, AP-D4): an answer out of the asked
shape is a failed call, every failure is a sentence and a record, and content is kept only when
the operator asked for it."""

from decimal import Decimal

from pydantic import BaseModel

from app.engine.proposals import calls
from app.engine.proposals.context import Policy
from app.engine.proposals.provider import ProposalRequest, ProviderAnswer, ProviderError
from app.engine.proposals.registry import AiConfiguration


class Answer(BaseModel):
    ready: bool


class Provider:
    name, model = "stub", "stub-1"

    def __init__(self, answer, cost=None):
        self.answer = answer
        self.cost = cost

    def propose(self, request):
        if isinstance(self.answer, BaseException):
            raise self.answer
        return ProviderAnswer(self.answer, "stub-1b", 7, 3, cost_usd=self.cost)


REQUEST = ProposalRequest("connectionTest", "Say ready", "t/1", {"test": True}, Answer)


def _ask(answer, *, log_content=False, cost=None):
    recorded = []
    ai = AiConfiguration(Provider(answer, cost), Policy("values", 20), 0.5, log_content, 7)
    outcome = calls.ask(ai, REQUEST, record=recorded.append, requester=calls.Requester(user_id=4))
    assert len(recorded) == 1 and recorded[0].public_id == outcome.call_id
    return outcome, recorded[0]


def test_an_answer_of_the_asked_shape_is_answered_and_recorded_without_content():
    outcome, row = _ask({"ready": True})
    assert outcome.answer == Answer(ready=True) and outcome.failure is None
    assert (row.outcome, row.model, row.tokens_in, row.tokens_out) == ("answered", "stub-1b", 7, 3)
    assert (row.requested_by_user_id, row.send_level, row.prompt_version) == (4, "values", "t/1")
    assert row.bytes_in > 0 and row.bytes_out == len(b'{"ready": true}')
    assert row.content is None and row.content_expires_at is None


def test_a_cost_the_provider_reports_reaches_the_call_and_none_leaves_it_empty():
    assert _ask({"ready": True}, cost=0.01234)[1].cost_usd == Decimal("0.0123")
    assert _ask({"ready": True})[1].cost_usd is None


def test_an_answer_out_of_shape_is_a_failed_call_never_a_guess():
    outcome, row = _ask({"names": ["x"]})
    assert outcome.answer is None and "shape" in outcome.failure
    assert (row.outcome, row.failure_kind) == ("failed", "malformed")


def test_a_provider_error_and_any_other_failure_are_named():
    outcome, row = _ask(ProviderError("unauthorized", "The provider refused the key"))
    assert (outcome.failure, row.failure_kind) == ("The provider refused the key", "unauthorized")
    outcome, row = _ask(ValueError("boom"))
    assert (outcome.failure, row.failure_kind) == ("The provider failed (ValueError)", "failed")


def test_content_is_kept_for_the_configured_days_only_when_asked():
    _, row = _ask({"ready": True}, log_content=True)
    assert row.content == {
        "instructions": "Say ready",
        "context": {"test": True},
        "answer": {"ready": True},
    }
    assert (row.content_expires_at - row.started_at).days == 7
