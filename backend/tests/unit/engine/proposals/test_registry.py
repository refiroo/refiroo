"""``AI_PROVIDER`` resolved at start (``engine/proposals/registry.py``, AP-D2): a setting that cannot
work refuses the start and names the setting; none sends nothing."""

import sys
import types

import pytest

from app.config import Settings
from app.engine.proposals.claude import ClaudeProvider
from app.engine.proposals.fake import FakeProvider
from app.engine.proposals.openai_compatible import OpenAICompatibleProvider
from app.engine.proposals.registry import configure, load_provider


def _settings(**environ: str) -> Settings:
    return Settings.from_env(environ)


def test_no_provider_is_the_default_and_offers_nothing():
    ai = configure(_settings())
    assert ai.provider is None and not ai.configured and not ai.offers("mappingTarget")
    assert (ai.policy.level, ai.policy.samples, ai.min_confidence) == ("values", 20, 0.5)


def test_each_provider_is_resolved_from_its_settings():
    assert isinstance(
        load_provider(_settings(AI_PROVIDER="claude", AI_API_KEY="k")), ClaudeProvider
    )
    found = load_provider(
        _settings(AI_PROVIDER="openai-compatible", AI_BASE_URL="http://h/v1", AI_MODEL="m")
    )
    assert isinstance(found, OpenAICompatibleProvider) and found.model == "m"
    assert isinstance(
        load_provider(_settings(AI_PROVIDER="app.engine.proposals.fake:provider")), FakeProvider
    )


@pytest.mark.parametrize(
    ("environ", "message"),
    [
        ({"AI_PROVIDER": "claude"}, "needs AI_API_KEY"),
        ({"AI_PROVIDER": "openai-compatible"}, "needs AI_BASE_URL and AI_MODEL"),
        ({"AI_PROVIDER": "gemini"}, "must be claude, openai-compatible or a factory"),
        ({"AI_PROVIDER": "rdm_missing_module:make"}, "could not be loaded"),
        ({"AI_PROVIDER": "rdm_no_propose:make"}, "without propose"),
    ],
)
def test_a_setting_that_cannot_work_refuses_the_start(monkeypatch, environ, message):
    module = types.ModuleType("rdm_no_propose")
    module.make = lambda: object()
    monkeypatch.setitem(sys.modules, "rdm_no_propose", module)
    with pytest.raises(RuntimeError, match=message):
        load_provider(_settings(**environ))


@pytest.mark.parametrize(
    ("environ", "message"),
    [
        ({"INFERENCE_ASSISTANT": "x:y"}, "INFERENCE_ASSISTANT is no longer read.*AI_PROVIDER"),
        (
            {"INFERENCE_ASSISTANT_ROWS": "5"},
            "INFERENCE_ASSISTANT_ROWS is no longer read.*AI_SAMPLE_VALUES",
        ),
        (
            {"AI_SEND_LEVEL": "everything"},
            "AI_SEND_LEVEL must be one of structure, samples, values",
        ),
        ({"AI_MIN_CONFIDENCE": "2"}, "AI_MIN_CONFIDENCE must be a number from 0 to 1"),
    ],
)
def test_retired_and_invalid_settings_refuse_the_start(environ, message):
    with pytest.raises(RuntimeError, match=message):
        _settings(**environ)
