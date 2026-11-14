"""``management/ai.ai_requested``: the operator's send-level ceiling applies before the omitted
flag answers (FX1, D8). An omitted ``asked`` with a level above the ceiling answers false and never
refuses; only ``asked=true`` refuses it."""

from types import SimpleNamespace

import pytest

from app.engine.proposals.context import Policy
from app.engine.proposals.registry import AiConfiguration
from app.errors import ApiError
from app.management.ai import ai_requested


class _Permissions:
    def allows(self, group, workspace_key):
        return True


class _Provider:
    name, model = "stub", "stub-1"


def _request(ceiling):
    ai = AiConfiguration(_Provider(), Policy(ceiling, 20), 0.5, False, 7)
    return SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(ai=ai)),
        state=SimpleNamespace(permissions=_Permissions()),
    )


def test_an_omitted_flag_with_a_level_above_the_ceiling_answers_false_and_never_refuses():
    request = _request("structure")
    assert (
        ai_requested(request, "connectionTest", None, workspace_key=None, send_level="values")
        is False
    )


def test_an_omitted_flag_within_the_ceiling_still_asks():
    request = _request("values")
    assert (
        ai_requested(request, "connectionTest", None, workspace_key=None, send_level="values")
        is True
    )
    assert ai_requested(request, "connectionTest", None, workspace_key=None) is True


def test_only_an_explicit_true_refuses_a_level_above_the_ceiling():
    request = _request("structure")
    with pytest.raises(ApiError) as raised:
        ai_requested(request, "connectionTest", True, workspace_key=None, send_level="values")
    assert raised.value.code == "AI_SEND_LEVEL_TOO_LOW"
    assert (
        ai_requested(request, "connectionTest", False, workspace_key=None, send_level="values")
        is False
    )
