"""J48 — Use AI proposals (USER_JOURNEYS.md § AI proposals, 0.16 AP1).

An operator sets an AI provider up in the environment and sees it ready on Settings › AI and
sends a test; an instance without a provider and a failing provider each say so. The features that
ask the provider have their own journeys (J49). The provider is the deterministic fake
(``app.engine.proposals.fake``, AP-D11). Every case runs on two configurations through the public
API.
"""

from typing import Any

import pytest
from scenario import ok, refused
from sqlalchemy import create_engine, text
from test_j34_onboard import _all

from app.engine.proposals import fake
from app.engine.proposals.provider import ProviderError

FAKE = "app.engine.proposals.fake:provider"


@pytest.fixture(autouse=True)
def _fresh_fake():
    fake.reset()
    yield
    fake.reset()


def _calls(world) -> list[dict[str, Any]]:
    return _all(world, "/ai/calls")


@pytest.mark.journey("J48.1")
@pytest.mark.settings(AI_PROVIDER=FAKE)
def test_an_operator_sees_the_provider_ready_and_every_call_it_made(world):
    """Given a provider set in the environment, when the operator opens Settings › AI and sends the
    test, then the status names the provider and model, says no key is shown, offers the
    mapping targets feature at send level values and not the assistant (it has its own switch), and the test is the newest call, answered, recorded
    with who sent it and nothing of its content."""
    system = ok(world.api.get("/system"))
    assert system["ai"] == {
        "configured": True,
        "provider": "fake",
        "model": fake.MODEL,
        "sendLevel": "values",
        "assistant": False,
    }
    status = ok(world.api.get("/ai/status"))
    assert (status["configured"], status["provider"], status["model"]) == (True, "fake", fake.MODEL)
    assert (status["keySet"], status["sendLevel"], status["sampleValues"]) == (False, "values", 20)
    assert [(f["purpose"], f["available"]) for f in status["features"]] == [
        ("mappingTarget", True),
        ("queryTranslation", True),
        ("impactSummary", True),
        ("historyAccount", True),
    ]
    assert status["assistant"] is False
    assert "apiKey" not in str(status).replace("keySet", "")

    tested = ok(world.api.post("/ai/test", {}))
    assert (tested["purpose"], tested["outcome"], tested["failure"]) == (
        "connectionTest",
        "answered",
        None,
    )
    assert tested["requestedBy"]["kind"] == "client" and tested["content"] is None
    assert tested["bytesIn"] > 0 and tested["tokensIn"] == 100
    assert _calls(world)[0]["id"] == tested["id"]
    status = ok(world.api.get("/ai/status"))
    assert status["lastCall"]["id"] == tested["id"]
    assert status["totals"]["calls"] >= 1 and status["totals"]["days"] == 30


@pytest.mark.journey("J48.1")
@pytest.mark.settings(AI_PROVIDER=FAKE, AI_LOG_CONTENT="true")
def test_with_content_logging_on_a_call_keeps_what_was_sent_and_answered(world):
    """Given AI_LOG_CONTENT on, when a call is made, then its record holds the request and the
    answer for an operator debugging a prompt."""
    tested = ok(world.api.post("/ai/test", {}))
    assert tested["content"]["answer"] == {"ready": True}
    assert tested["content"]["context"] == {"test": True}


@pytest.mark.journey("J48.4")
def test_without_a_provider_nothing_is_sent_and_no_ai_action_is_offered(world):
    """Given no provider, then the system says so, no feature is offered, and the test is refused
    with 409 AI_NOT_CONFIGURED with no call recorded."""
    assert ok(world.api.get("/system"))["ai"]["configured"] is False
    status = ok(world.api.get("/ai/status"))
    assert status["configured"] is False
    assert [f["available"] for f in status["features"]] == [False, False, False, False]
    before = len(_calls(world))
    refused(world.api.post("/ai/test", {}), 409, "AI_NOT_CONFIGURED")
    assert len(_calls(world)) == before


@pytest.mark.journey("J48.5")
@pytest.mark.settings(AI_PROVIDER=FAKE)
@pytest.mark.parametrize(
    ("answer", "kind"),
    [
        (ProviderError("unreachable", "The provider could not be reached"), "unreachable"),
        ({"names": ["not the shape asked for"]}, "malformed"),
    ],
    ids=["unreachable", "out-of-shape"],
)
def test_a_failing_provider_gives_a_failed_call_with_its_kind(world, answer, kind):
    """Given a provider that cannot be reached, or answers out of shape, when the operator sends
    the test, then the call is answered as failed with its kind and is the newest one recorded."""
    fake.script("connectionTest", answer)
    tested = ok(world.api.post("/ai/test", {}))
    assert (tested["outcome"], tested["failureKind"]) == ("failed", kind)
    assert _calls(world)[0]["id"] == tested["id"]
    assert ok(world.api.get("/ai/status"))["lastCall"]["failureKind"] == kind


@pytest.mark.journey("J48.1")
@pytest.mark.settings(AI_PROVIDER=FAKE)
def test_a_call_made_for_a_feature_since_removed_stays_readable(world):
    """Given the newest call was made for the inference's names, a feature removed in 0.16 AP6a
    (written by this test, as calls recorded before the removal hold it), when the operator opens
    Settings › AI, then the status and the calls list answer with it under its own purpose. Found
    on the user's instance: the status failed with an internal error."""
    tested = ok(world.api.post("/ai/test", {}))
    engine = create_engine(world.database)
    try:
        with engine.begin() as connection:
            connection.execute(
                text("UPDATE ai_calls SET purpose = 'modelNames' WHERE public_id = :id"),
                {"id": tested["id"]},
            )
    finally:
        engine.dispose()
    assert ok(world.api.get("/ai/status"))["lastCall"]["purpose"] == "modelNames"
    assert _calls(world)[0]["purpose"] == "modelNames"
