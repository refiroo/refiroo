"""J55 — An account of a model change (USER_JOURNEYS.md § Model change impact summary, 0.16 AO1).

A model administrator about to activate a release, or to apply a draft, asks for a short account of
what the change does. The engine writes the facts (the diff, the check of the workspace's data, the
consumer API check, the records per touched type); the provider, the deterministic fake, only words
them, each statement citing the facts it rests on. Every case runs on two configurations through the
public API.
"""

import copy
import json
from uuid import uuid4

import pytest
from scenario import W1, ok, refused
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
from test_j34_onboard import _all
from test_j40_authorization import _client

from app.engine.proposals import fake
from app.engine.proposals.provider import ProviderError

FAKE = "app.engine.proposals.fake:provider"
STRUCTURES = ("R", "R.u", "R.b", "K")


@pytest.fixture(autouse=True)
def _fresh_fake():
    fake.reset()
    yield
    fake.reset()


def _release(world, kind="compatible", **changes):
    model, key = world.candidate(kind)
    model["release"]["version"] += f"-{uuid4().hex[:6]}"
    for change in changes.values():
        change(model)
    return world.install(model)["id"], key


def _summary(world, release, **body):
    return world.api.post(f"/model-releases/{release}/impact-summary", {"workspaceKey": W1, **body})


def _records(world, type_key):
    engine = create_engine(world.database, poolclass=NullPool)
    with engine.connect() as connection:
        count = connection.scalar(
            text("SELECT count(*) FROM objects WHERE workspace_key = :w AND object_type_key = :k"),
            {"w": W1, "k": type_key},
        )
    engine.dispose()
    return count


def _kinds(answer):
    return {fact["kind"] for fact in answer["facts"]}


def _last_call(world):
    return _all(world, "/ai/calls")[0]


@pytest.mark.journey("J55.1")
@pytest.mark.structures(*STRUCTURES)
@pytest.mark.settings(AI_PROVIDER=FAKE, AI_SEND_LEVEL="structure")
def test_a_release_is_explained_by_statements_that_cite_the_engines_facts(world):
    """Given a release that adds an optional attribute and a type, when a model administrator asks,
    then each statement cites facts the answer holds, the change facts are the diff's, the record
    count of the touched type is a count taken directly, and the call is recorded as answered with
    no record name sent."""
    planted = world.made("R", f"Planted {uuid4().hex[:8]}")["name"]
    release, added = _release(world)
    state = world.workspace_model()
    diff = ok(world.api.get(f"/model-releases/{release}/diff", againstReleaseId=state["releaseId"]))
    answer = ok(_summary(world, release))
    ids = {fact["id"] for fact in answer["facts"]}
    assert answer["statements"] and answer["failure"] is None and answer["cached"] is False
    assert all(item["factIds"] and set(item["factIds"]) <= ids for item in answer["statements"])
    changes = {fact["path"]: fact for fact in answer["facts"] if fact["kind"] == "change"}
    assert set(changes) == {change["path"] for change in diff["changes"]}
    assert any("optional" in fact["text"] and added in fact["path"] for fact in changes.values())
    (records,) = [
        f for f in answer["facts"] if f["kind"] == "records" and world.key("R") in f["path"]
    ]
    assert records["count"] == _records(world, world.key("R")) and records["count"] > 0
    call = _last_call(world)
    assert (call["purpose"], call["outcome"], call["id"]) == (
        "impactSummary",
        "answered",
        answer["callId"],
    )
    assert planted not in json.dumps([fake.seen[-1].context, fake.seen[-1].instructions])


@pytest.mark.journey("J55.2")
@pytest.mark.structures(*STRUCTURES)
@pytest.mark.settings(AI_PROVIDER=FAKE)
def test_a_draft_is_explained_as_its_compilation_shows_it_and_a_bad_draft_is_refused(world):
    """Given a draft, when the account is asked, then its change facts are the compilation's
    changes; and an invalid draft is 422 IMPACT_SUMMARY_DRAFT_INVALID and a stale version 409."""
    model, _ = world.candidate("compatible")
    model["release"]["version"] += "-draft"
    draft = ok(world.api.post("/model-drafts", {"name": "Draft", "model": model}), 201)
    path = f"/model-drafts/{draft['id']}"
    compiled = ok(world.api.post(f"{path}/compile", {"expectedVersion": draft["version"]}))
    answer = ok(
        world.api.post(
            f"{path}/impact-summary", {"workspaceKey": W1, "expectedVersion": draft["version"]}
        )
    )
    assert {f["path"] for f in answer["facts"] if f["kind"] == "change"} == {
        change["path"] for change in compiled["changes"]
    }
    assert answer["statements"]
    refused(
        world.api.post(f"{path}/impact-summary", {"workspaceKey": W1, "expectedVersion": 99}),
        409,
        "VERSION_CONFLICT",
    )
    broken = copy.deepcopy(model)
    broken["objectTypes"][0]["attributes"].append({"attributeTypeKey": "no-such-attribute"})
    bad = ok(world.api.post("/model-drafts", {"name": "Broken", "model": broken}), 201)
    refused(
        world.api.post(
            f"/model-drafts/{bad['id']}/impact-summary",
            {"workspaceKey": W1, "expectedVersion": bad["version"]},
        ),
        422,
        "IMPACT_SUMMARY_DRAFT_INVALID",
    )


@pytest.mark.journey("J55.3")
@pytest.mark.structures(*STRUCTURES)
@pytest.mark.settings(AI_PROVIDER=FAKE)
def test_the_person_gets_every_fact_and_the_provider_forty_of_a_kind_with_the_true_count(world):
    """Given a release with more than 40 changes, when the account is asked, then the answer holds
    every change fact, the context 40 with the true total and a group a statement may cite, and the
    record count equals a count taken directly."""

    def many(model):
        r_type = next(t for t in model["objectTypes"] if t["key"] == world.key("R"))
        for number in range(45):
            key = f"{world.key('R')}-extra-{number:02d}"
            model["attributeTypes"].append({"key": key, "name": f"Extra {number:02d}"})
            r_type["attributes"].append({"attributeTypeKey": key, "order": 1000 + number})

    release, _ = _release(world, extra=many)
    for number in range(3):
        world.made("R", f"Counted {number} {uuid4().hex[:6]}")
    fake.script(
        "impactSummary",
        lambda context: {
            "statements": [{"text": "More changes follow.", "factIds": ["more-change"]}]
        },
    )
    answer = ok(_summary(world, release))
    changes = [f for f in answer["facts"] if f["kind"] == "change"]
    assert len(changes) >= 90
    context = fake.seen[-1].context
    assert len([f for f in context["facts"] if f["kind"] == "change"]) == 40
    assert context["totals"]["change"] == len(changes)
    assert {"id": "more-change", "kind": "change"}.items() <= context["more"][0].items()
    assert context["more"][0]["count"] == len(changes) - 40
    assert (
        answer["statements"][0]["factIds"] == ["more-change"] and answer["removedStatements"] == 0
    )
    (records,) = [
        f for f in answer["facts"] if f["kind"] == "records" and world.key("R") in f["path"]
    ]
    assert records["count"] == _records(world, world.key("R"))


@pytest.mark.journey("J55.4")
@pytest.mark.structures(*STRUCTURES)
@pytest.mark.settings(AI_PROVIDER=FAKE)
def test_a_statement_that_cites_no_fact_is_dropped_and_counted(world):
    """Given an answer with a statement citing an unknown fact and one citing none, when the account
    is asked, then they are dropped and counted and the cited one stays; when none cites a fact, the
    facts stand alone and the call is still recorded as answered."""
    release, _ = _release(world)
    fake.script(
        "impactSummary",
        lambda context: {
            "statements": [
                {"text": "Cited.", "factIds": [context["facts"][0]["id"]]},
                {"text": "Unknown.", "factIds": [context["facts"][0]["id"], "ch-00000000"]},
                {"text": "Uncited.", "factIds": []},
            ]
        },
    )
    answer = ok(_summary(world, release))
    assert [item["text"] for item in answer["statements"]] == ["Cited."]
    assert answer["removedStatements"] == 2 and answer["failure"] is None
    fake.script(
        "impactSummary",
        {"statements": [{"text": "Unknown.", "factIds": ["ch-00000000"]}]},
    )
    alone = ok(_summary(world, release, language="fr"))
    assert alone["statements"] == [] and alone["removedStatements"] == 1
    assert alone["facts"] == answer["facts"] and alone["failure"] is None
    assert _last_call(world)["outcome"] == "answered"
    # An account with nothing left is not kept: asking again calls the provider again.
    ok(_summary(world, release, language="fr"))
    assert len(fake.seen) == 3


@pytest.mark.journey("J55.5")
@pytest.mark.structures(*STRUCTURES)
@pytest.mark.settings(AI_PROVIDER=FAKE)
def test_a_failing_provider_gives_the_facts_alone_and_holds_no_transaction(world):
    """Given a provider that fails, and one that answers out of shape, when the account is asked,
    then each gives 200 with the facts, no statements and the failure, each is a failed call, and no
    transaction was open while the provider answered."""
    release, _ = _release(world)
    idle = []
    engine = create_engine(world.database, poolclass=NullPool)

    def refusing(context):
        with engine.connect() as connection:
            idle.append(
                connection.scalar(
                    text(
                        "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()"
                        " AND state = 'idle in transaction' AND pid <> pg_backend_pid()"
                    )
                )
            )
        raise ProviderError("unreachable", "The provider could not be reached")

    fake.script("impactSummary", refusing)
    answer = ok(_summary(world, release))
    engine.dispose()
    assert idle == [0]
    assert answer["statements"] == [] and answer["facts"] and answer["cached"] is False
    assert answer["failure"] == "The provider could not be reached"
    call = _last_call(world)
    assert (call["outcome"], call["failureKind"], call["id"]) == (
        "failed",
        "unreachable",
        answer["callId"],
    )
    fake.script("impactSummary", {"statements": "none"})
    answer = ok(_summary(world, release))
    assert answer["statements"] == [] and answer["failure"] and answer["facts"]
    assert _last_call(world)["failureKind"] == "malformed"


@pytest.mark.journey("J55.6")
@pytest.mark.structures(*STRUCTURES)
@pytest.mark.settings(AI_PROVIDER=FAKE)
def test_the_same_facts_are_answered_from_the_cache_and_a_changed_count_asks_again(world):
    """Given an account asked once, when the same request is repeated, then it is answered from the
    cache with no provider call and the same call; when a record of a touched type is added, then
    the provider is called again."""
    release, _ = _release(world)
    first = ok(_summary(world, release))
    again = ok(_summary(world, release))
    assert (first["cached"], again["cached"]) == (False, True)
    assert again["statements"] == first["statements"] and again["callId"] == first["callId"]
    assert len(fake.seen) == 1
    world.made("R", f"One more {uuid4().hex[:6]}")
    third = ok(_summary(world, release))
    assert third["cached"] is False and len(fake.seen) == 2
    assert third["callId"] != first["callId"]


@pytest.mark.journey("J55.7")
@pytest.mark.structures(*STRUCTURES)
@pytest.mark.settings(AI_PROVIDER=FAKE)
def test_a_release_needing_a_migration_gives_blocked_and_data_facts_and_changes_nothing(world):
    """Given a release that makes an optional attribute required while records lack it, when the
    account is asked, then a blocked fact and data facts carry the counts the check gives, and the
    workspace's model and records are as they were."""
    world.made("R", f"Without it {uuid4().hex[:6]}")
    release, _ = _release(world, "incompatible")
    state = world.workspace_model()
    before = _records(world, world.key("R"))
    diff = ok(world.api.get(f"/model-releases/{release}/diff", againstReleaseId=state["releaseId"]))
    assert diff["compatibility"]["classification"] == "migration_required"
    answer = ok(_summary(world, release))
    assert {"blocked", "data", "change"} <= _kinds(answer)
    data = {f["path"]: f["count"] for f in answer["facts"] if f["kind"] == "data"}
    assert data == {d["path"]: d["count"] for d in diff["compatibility"]["diagnostics"]}
    assert all(count >= 1 for count in data.values())
    assert world.workspace_model() == state and _records(world, world.key("R")) == before


@pytest.mark.journey("J55.8")
@pytest.mark.structures(*STRUCTURES)
@pytest.mark.settings(AI_PROVIDER=FAKE, AI_SEND_LEVEL="structure")
def test_only_those_who_may_activate_and_use_ai_proposals_may_ask(world):
    """Given a client with Browse and Use AI proposals only, and one with Model release but no Use
    AI proposals, when they ask, then each is refused 403 naming the missing group and no call is
    made; and a level above the ceiling is 409 AI_SEND_LEVEL_TOO_LOW."""
    release, _ = _release(world)
    readers = ok(
        world.api.post("/roles", {"name": "Askers", "actionGroups": ["browse", "ai-proposals"]}),
        201,
    )
    releasers = ok(
        world.api.post(
            "/roles", {"name": "Releasers", "actionGroups": ["browse", "model-release"]}
        ),
        201,
    )
    _, asker = _client(world, "asker", (readers["key"], {"instance": True}))
    _, releaser = _client(world, "releaser", (releasers["key"], {"instance": True}))
    error = refused(_summary(asker, release), 403, "FORBIDDEN")
    assert error["details"]["groups"] == ["model-release"]
    error = refused(_summary(releaser, release), 403, "FORBIDDEN")
    assert error["details"]["groups"] == ["ai-proposals"]
    assert fake.seen == [] and _all(world, "/ai/calls") == []
    error = refused(_summary(world, release, sendLevel="values"), 409, "AI_SEND_LEVEL_TOO_LOW")
    assert error["details"] == {"sendLevel": "values", "ceiling": "structure"}
    ok(_summary(world, release, sendLevel="structure", language="de"))
    assert fake.seen[-1].context["language"] == "de"


@pytest.mark.journey("J55.8")
@pytest.mark.structures(*STRUCTURES)
def test_without_a_provider_the_account_is_refused(world):
    """Given no provider, then asking is 409 AI_NOT_CONFIGURED."""
    release, _ = _release(world)
    refused(_summary(world, release), 409, "AI_NOT_CONFIGURED")
