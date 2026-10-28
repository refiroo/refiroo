"""J48 — Use AI proposals (USER_JOURNEYS.md § AI proposals, 0.16 AP1).

An operator sets an AI provider up in the environment and sees it ready on Settings › AI; a model
administrator's inference asks it for better names, which arrive as proposals marked with their
provenance and become steps that say so once applied; a caller without Use AI proposals, an
instance without a provider, a failing provider and a low send level each leave the deterministic
inference standing. The provider is the deterministic fake (``app.engine.proposals.fake``, AP-D11),
which records what it was sent. Every case runs on two configurations through the public API.
"""

from typing import Any

import pytest
import workbooks
from scenario import ok, refused
from test_j34_onboard import _all, _draft, _profiled, _proposals, _run, _workspace
from test_j40_authorization import _client

from app.engine.proposals import fake
from app.engine.proposals.provider import ProviderError

FAKE = "app.engine.proposals.fake:provider"


@pytest.fixture(autouse=True)
def _fresh_fake():
    fake.reset()
    yield
    fake.reset()


def _prepared(world) -> dict[str, Any]:
    """A draft of the active model with W1 profiled in a new workspace."""
    workspace = _workspace(world)
    draft = _draft(world)
    book = workbooks.w1(rows=40)
    _profiled(
        world, {"draftId": draft["id"]}, "catalogue.xlsx", book.content, workspaceKey=workspace
    )
    return draft


def _infer(world, draft: dict[str, Any], **body: Any) -> dict[str, Any]:
    started = ok(
        world.api.post(
            f"/model-drafts/{draft['id']}/inference", {"mode": "newApplication", **body}
        ),
        202,
    )
    _run(world)
    done = ok(world.api.get(f"/model-drafts/{draft['id']}/inference"))
    assert (done["jobId"], done["state"]) == (started["jobId"], "completed"), done
    return done


def _assistant(proposals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [p for p in proposals if p["pattern"] == "assistant"]


def _calls(world) -> list[dict[str, Any]]:
    return _all(world, "/ai/calls")


@pytest.mark.journey("J48.1")
@pytest.mark.settings(AI_PROVIDER=FAKE)
def test_an_operator_sees_the_provider_ready_and_every_call_it_made(world):
    """Given a provider set in the environment, when the operator opens Settings › AI and sends the
    test, then the status names the provider and model, says no key is shown, offers the
    inference's names at send level values, and the test is the newest call, answered, recorded
    with who sent it and nothing of its content."""
    system = ok(world.api.get("/system"))
    assert system["ai"] == {"configured": True, "provider": "fake", "sendLevel": "values"}
    status = ok(world.api.get("/ai/status"))
    assert (status["configured"], status["provider"], status["model"]) == (True, "fake", fake.MODEL)
    assert (status["keySet"], status["sendLevel"], status["sampleValues"]) == (False, "values", 20)
    assert [(f["purpose"], f["available"]) for f in status["features"]] == [("modelNames", True)]
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


@pytest.mark.journey("J48.2")
@pytest.mark.settings(AI_PROVIDER=FAKE)
def test_a_model_administrator_gets_named_proposals_marked_as_the_assistants(world):
    """Given a provider and a model administrator, when their inference runs, then the provider is
    sent the sheets with their rows and the types the rules add, each better name above the floor is
    a proposal marked machine-proposed with provider, model, confidence and reason, and once applied
    the step's origin says who proposed it; the call names the job and the person."""
    draft = _prepared(world)
    read = _infer(world, draft)
    assert read["assistant"] is True and read["warnings"] == []
    proposals = _proposals(world, draft)
    named = _assistant(proposals)
    assert named, [p["pattern"] for p in proposals]
    sent = fake.seen[-1]
    assert sent.purpose == "modelNames" and sent.context["types"]
    # At send level values the helper gets the rows it asks for (its own 50), not AI_SAMPLE_VALUES.
    assert all(0 < len(sheet["rows"]) <= 50 for sheet in sent.context["sheets"])
    assert any(len(sheet["rows"]) > 20 for sheet in sent.context["sheets"])
    origin = named[0]["evidence"]["origin"]
    assert origin == {
        "kind": "ai",
        "provider": "fake",
        "model": fake.MODEL,
        "promptVersion": "model-names/1",
        "confidence": 0.8,
        "reason": "Written out from the header",
    }

    first = named[0]
    version = ok(world.api.get(f"/model-drafts/{draft['id']}"))["version"]
    ok(
        world.api.post(
            f"/model-drafts/{draft['id']}/inference/application",
            {"expectedVersion": version},
        )
    )
    entries = _all(world, f"/model-drafts/{draft['id']}/operations")
    assistant_steps = [e for e in entries if e["origin"].get("proposalId") == first["id"]]
    assert assistant_steps and assistant_steps[0]["origin"]["proposedBy"] == origin
    assert assistant_steps[0]["author"]["kind"] == "client"
    call = _calls(world)[0]
    assert (call["purpose"], call["outcome"], call["jobId"]) == (
        "modelNames",
        "answered",
        read["jobId"],
    )
    assert call["requestedBy"]["kind"] == "client"


@pytest.mark.journey("J48.3")
@pytest.mark.settings(AI_PROVIDER=FAKE)
def test_a_caller_without_use_ai_proposals_is_never_offered_the_assistant(world):
    """Given a provider and a client whose role holds Model authoring but not Use AI proposals, when
    it runs the inference, then the provider is not asked and nothing is recorded; asking for the
    assistant explicitly is refused with 403 naming the group."""
    draft = _prepared(world)
    role = ok(
        world.api.post("/roles", {"name": "Drafts only", "actionGroups": ["model-authoring"]}), 201
    )
    _, author = _client(world, "Drafts only", (role["key"], {"instance": True}))
    before = len(_calls(world))
    read = _infer(author, draft)
    assert read["assistant"] is False and not _assistant(_proposals(world, draft))
    assert fake.seen == [] and len(_calls(world)) == before
    error = refused(
        author.api.post(
            f"/model-drafts/{draft['id']}/inference", {"mode": "newApplication", "assistant": True}
        ),
        403,
        "FORBIDDEN",
    )
    assert error["details"]["groups"] == ["ai-proposals"]


@pytest.mark.journey("J48.4")
def test_without_a_provider_nothing_is_sent_and_no_ai_action_is_offered(world):
    """Given no provider, then the system says so, no feature is offered, the test and an explicit
    assistant are refused with 409 AI_NOT_CONFIGURED, and the inference runs on its rules alone
    with no call recorded."""
    assert ok(world.api.get("/system"))["ai"]["configured"] is False
    status = ok(world.api.get("/ai/status"))
    assert status["configured"] is False
    assert [f["available"] for f in status["features"]] == [False]
    refused(world.api.post("/ai/test", {}), 409, "AI_NOT_CONFIGURED")
    draft = _prepared(world)
    refused(
        world.api.post(
            f"/model-drafts/{draft['id']}/inference", {"mode": "newApplication", "assistant": True}
        ),
        409,
        "AI_NOT_CONFIGURED",
    )
    before = len(_calls(world))
    read = _infer(world, draft)
    assert read["assistant"] is False and _proposals(world, draft)
    assert not _assistant(_proposals(world, draft)) and len(_calls(world)) == before


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
def test_a_failing_provider_leaves_the_rules_proposals_standing(world, answer, kind):
    """Given a provider that cannot be reached, or answers out of shape, when the inference runs,
    then it completes with the rules' proposals and a warning saying the assistant failed and why,
    and the failed call is recorded with its kind."""
    fake.script("modelNames", answer)
    draft = _prepared(world)
    read = _infer(world, draft)
    assert read["assistant"] is True
    assert any(
        w.startswith("The assistant failed (") and w.endswith("the proposals of the rules stand")
        for w in read["warnings"]
    )
    assert _proposals(world, draft) and not _assistant(_proposals(world, draft))
    call = _calls(world)[0]
    assert (call["outcome"], call["failureKind"]) == ("failed", kind)


@pytest.mark.journey("J48.6")
@pytest.mark.settings(AI_PROVIDER=FAKE, AI_SEND_LEVEL="structure")
def test_at_send_level_structure_no_value_of_the_file_leaves(world):
    """Given AI_SEND_LEVEL structure, when the inference asks the assistant, then the provider is
    sent sheet names, headers and type names and not one row."""
    draft = _prepared(world)
    _infer(world, draft)
    sent = fake.seen[-1].context
    assert sent["sheets"] and all(set(sheet) == {"name", "headers"} for sheet in sent["sheets"])
    assert _calls(world)[0]["sendLevel"] == "structure"


@pytest.mark.journey("J48.6")
@pytest.mark.settings(AI_PROVIDER=FAKE, AI_SEND_LEVEL="samples", AI_SAMPLE_VALUES="3")
def test_at_send_level_samples_at_most_the_sample_rows_leave(world):
    """Given AI_SEND_LEVEL samples and AI_SAMPLE_VALUES 3, then each sheet is sent with at most 3
    rows."""
    draft = _prepared(world)
    _infer(world, draft)
    sheets = fake.seen[-1].context["sheets"]
    assert sheets and all(0 < len(sheet["rows"]) <= 3 for sheet in sheets)


@pytest.mark.journey("J48.7")
@pytest.mark.settings(AI_PROVIDER=FAKE, AI_MIN_CONFIDENCE="0.9")
def test_a_name_below_the_confidence_floor_is_not_offered(world):
    """Given AI_MIN_CONFIDENCE 0.9 and an answer at 0.8, then the inference offers no assistant
    proposal, and the call still counts as answered."""
    draft = _prepared(world)
    _infer(world, draft)
    assert not _assistant(_proposals(world, draft))
    assert _calls(world)[0]["outcome"] == "answered"
