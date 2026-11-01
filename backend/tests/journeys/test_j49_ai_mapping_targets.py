"""J49 — Targets for unmapped values (USER_JOURNEYS.md § AI proposals, 0.16 AP2).

A steward asks the AI provider for targets for a mapping view's unmapped values. The proposals land
in a change set as edits marked with their provenance, to be corrected in the grid and published
through the normal approval; live data is never changed. The provider is the deterministic fake
(``app.engine.proposals.fake``), which records what it was sent. The view is read from either end of
its relationship (an outgoing and an incoming view of the same binding), and every case runs on two
configurations through the public API.
"""

import json
from typing import Any
from uuid import uuid4

import pytest
from scenario import W1, ok, refused
from test_j34_onboard import _all, _run
from test_j40_authorization import _client

from app.engine.proposals import fake
from app.engine.proposals.mapping_targets import INSTRUCTIONS
from app.engine.proposals.provider import ProviderError

FAKE = "app.engine.proposals.fake:provider"
PAIRS = (("Quartz", "Quartz mine"), ("Basalt", "Basalt pit"), ("Granite", "Granite hill"))
VIEWS = ("Vnn", "Vnnr")
STRUCTURES = ("H", "K", "Bnn", "Vnn", "Vnnr", "Bcand", "Vcand", "K.code")


@pytest.fixture(autouse=True)
def _fresh_fake():
    fake.reset()
    yield
    fake.reset()


def _view(world, structure) -> tuple[str, dict[str, Any]]:
    key = world.key(structure)
    for application in world.configuration.model["applications"]:
        for view in application["views"]:
            if view["key"] == key:
                return application["key"], view["config"]
    raise KeyError(structure)


def _identity(world, structure) -> dict[str, str]:
    application, _config = _view(world, structure)
    return {"applicationKey": application, "viewKey": world.key(structure)}


def _binding(world, structure) -> dict[str, str]:
    _application, config = _view(world, structure)
    return {
        name: config[name]
        for name in ("relationTypeKey", "fromObjectTypeKey", "toObjectTypeKey", "direction")
    }


def _ends(world, view) -> tuple[str, str]:
    """The structures a view's sources and targets are: H and K, or K and H where it is read from
    the other end."""
    return ("H", "K") if _view(world, view)[1]["direction"] == "outgoing" else ("K", "H")


def _records(world, view, tag, pairs=PAIRS, **values) -> list[tuple[dict, dict]]:
    """A source and a target record per pair, named from the pair and the run's tag."""
    source_type, target_type = _ends(world, view)
    return [
        (
            world.made(source_type, f"{source} {tag}"),
            world.made(target_type, f"{target} {tag}", **values),
        )
        for source, target in pairs
    ]


def _propose(world, view, **body) -> Any:
    return world.api.post(
        f"/workspaces/{W1}/mapping-proposals",
        {**_identity(world, view), **body},
    )


def _run_job(world, view, **body) -> tuple[dict[str, Any], dict[str, Any]]:
    """Ask, run the worker and read the finished job and its change set."""
    job = ok(_propose(world, view, **body), 202)
    assert (job["kind"], job["state"]) == ("aiProposal", "queued")
    _run(world)
    done = ok(world.api.get(f"/jobs/{job['id']}"))
    return done, ok(world.api.get(f"/change-sets/{done['changeSetId']}"))


def _coverage(world, view, change_set=None, **params) -> list[dict[str, Any]]:
    return _all(
        world,
        f"/workspaces/{W1}/mapping-coverage",
        page_size=100,
        **_identity(world, view),
        **_binding(world, view),
        **({"changeSetId": change_set["id"]} if change_set else {}),
        **params,
    )


def _row(rows, source) -> dict[str, Any]:
    return next(row for row in rows if row["source"]["id"] == source["id"])


def _targets(row) -> list[dict[str, Any]]:
    return row["targets"]


@pytest.mark.journey("J49.1")
@pytest.mark.structures(*STRUCTURES)
@pytest.mark.settings(AI_PROVIDER=FAKE)
@pytest.mark.parametrize("view", VIEWS)
def test_targets_are_proposed_into_a_new_change_set_with_their_provenance(world, view):
    """Given unmapped sources and a provider, when a steward asks for proposals into a new change
    set, then a job runs and finishes with the tally, the change set holds each source mapped to
    the target its name says, every target carries the AI's provenance, and live data is unchanged."""
    tag = uuid4().hex[:6]
    pairs = _records(world, view, tag)
    done, change_set = _run_job(world, view, search=tag, changeSetName="Proposed targets")
    assert (done["state"], done["result"], done["progress"]) == (
        "completed",
        "applied",
        {"total": 3, "processed": 3},
    )
    assert done["aiProposal"] == {
        "proposed": 3,
        "unmatched": 0,
        "changed": 0,
        "refused": 0,
        "notAnswered": 0,
        "changeSetId": change_set["id"],
        "warnings": [],
    }
    assert change_set["name"] == "Proposed targets"
    assert done["changeSetVersion"] == change_set["version"] > 1
    rows = _coverage(world, view, change_set, search=tag)
    for source, target in pairs:
        row = _row(rows, source)
        assert row["state"] == "mapped", row
        (found,) = _targets(row)
        assert found["object"]["id"] == target["id"]
        assert found["origin"] == {
            "kind": "ai",
            "provider": "fake",
            "model": fake.MODEL,
            "promptVersion": "mapping-targets/2",
            "confidence": 0.8,
            "reason": "Closest name",
            "proposedBy": done["requestedBy"]["id"],
        }
    # Live data and the grid outside the change set know nothing of it.
    assert {row["state"] for row in _coverage(world, view, search=tag)} == {"unmapped"}
    call = _all(world, "/ai/calls")[0]
    assert (call["purpose"], call["outcome"], call["jobId"]) == (
        "mappingTarget",
        "answered",
        done["id"],
    )
    assert call["requestedBy"]["id"] == done["requestedBy"]["id"]


@pytest.mark.journey("J49.1")
@pytest.mark.structures(*STRUCTURES)
@pytest.mark.settings(AI_PROVIDER=FAKE)
def test_proposals_go_into_a_change_set_the_steward_already_has_and_no_source_is_asked_twice(world):
    """Given a change set with one source already mapped by hand, when proposals are asked for into
    it, then only the sources still unmapped are asked about, and asking again finds nothing."""
    tag = uuid4().hex[:6]
    pairs = _records(world, "Vnn", tag)
    change_set = world.change_set(name="Mine")
    binding = _binding(world, "Vnn")
    ok(
        world.api.put(
            f"/workspaces/{W1}/mappings",
            {
                **binding,
                "sourceObjectId": pairs[0][0]["id"],
                "targetObjectId": pairs[0][1]["id"],
                "expectedMappingVersion": 0,
                "changeSetId": change_set["id"],
                "expectedChangeSetVersion": change_set["version"],
            },
        )
    )
    current = world.current(change_set)
    done, after = _run_job(
        world,
        "Vnn",
        search=tag,
        changeSetId=change_set["id"],
        expectedChangeSetVersion=current["version"],
    )
    assert done["aiProposal"]["proposed"] == 2 and done["progress"]["total"] == 2
    assert after["id"] == change_set["id"]
    asked = fake.seen[-1].context["sources"]
    assert sorted(s["name"] for s in asked) == sorted(f"{name} {tag}" for name, _ in PAIRS[1:])
    again, _ = _run_job(
        world,
        "Vnn",
        search=tag,
        changeSetId=change_set["id"],
        expectedChangeSetVersion=after["version"],
    )
    assert (again["state"], again["progress"]["total"], again["aiProposal"]["proposed"]) == (
        "completed",
        0,
        0,
    )


@pytest.mark.journey("J49.2")
@pytest.mark.structures(*STRUCTURES)
@pytest.mark.settings(AI_PROVIDER=FAKE)
def test_an_invented_null_or_doubtful_answer_leaves_the_source_unmapped_and_counted(world):
    """Given a provider that invents a target, answers null, answers below the confidence floor and
    leaves a source out, when the job runs, then those sources stay unmapped, each counted as the
    kind of miss it was, and the one good answer is written."""
    tag = uuid4().hex[:6]
    _records(world, "Vnn", tag, PAIRS + (("Marble", "Marble hall"), ("Slate", "Slate yard")))

    def answering(context):
        refs = [s["ref"] for s in context["sources"]]
        by_name = {s["name"]: s["ref"] for s in context["sources"]}
        real = context["candidates"][0]["ref"]
        names = [f"{name} {tag}" for name, _ in PAIRS]
        return {
            "answers": [
                {"source": by_name[names[0]], "target": "t999", "reason": "x", "confidence": 0.9},
                {"source": by_name[names[1]], "target": None, "reason": "", "confidence": 0},
                {"source": by_name[names[2]], "target": real, "reason": "x", "confidence": 0.2},
                {
                    "source": by_name[f"Marble {tag}"],
                    "target": next(
                        c["ref"] for c in context["candidates"] if c["name"] == f"Marble hall {tag}"
                    ),
                    "reason": "Same name",
                    "confidence": 0.9,
                },
            ]
            # Slate is left out.
            if refs
            else []
        }

    fake.script("mappingTarget", answering)
    done, change_set = _run_job(world, "Vnn", search=tag, changeSetName="Doubtful")
    assert done["aiProposal"]["proposed"] == 1
    assert done["aiProposal"]["unmatched"] == 3 and done["aiProposal"]["notAnswered"] == 1
    rows = _coverage(world, "Vnn", change_set, search=tag)
    states = {row["source"]["name"]: row["state"] for row in rows}
    assert states == {
        f"Quartz {tag}": "unmapped",
        f"Basalt {tag}": "unmapped",
        f"Granite {tag}": "unmapped",
        f"Marble {tag}": "mapped",
        f"Slate {tag}": "unmapped",
    }
    assert (done["state"], done["result"]) == ("completed", "partial")


@pytest.mark.journey("J49.3")
@pytest.mark.structures("H", "K", "H.code", "K.code", "Bsrc", "Vsrc")
@pytest.mark.settings(AI_PROVIDER=FAKE)
def test_the_provider_is_not_asked_about_a_source_outside_the_bindings_criteria(world):
    """Given a view whose binding takes only sources whose code starts with OK, an unmapped source
    that meets it and one that does not, when a job asks for targets, then the provider is sent the
    first alone and the job's total counts one."""
    tag = uuid4().hex[:6]
    meets = world.made("H", f"Quartz {tag}", values={"H.code": f"OK-{tag}"})
    world.made("H", f"Quartz other {tag}", values={"H.code": f"NO-{tag}"})
    world.made("K", f"Quartz mine {tag}", values={"K.code": f"K-{tag}"})
    done, _change_set = _run_job(world, "Vsrc", search=tag, changeSetName="Sources")
    sent = fake.seen[-1].context
    assert [s["name"] for s in sent["sources"]] == [meets["name"]]
    assert done["progress"]["total"] == 1


@pytest.mark.journey("J49.3")
@pytest.mark.structures(*STRUCTURES)
@pytest.mark.settings(AI_PROVIDER=FAKE)
def test_the_provider_is_sent_only_the_eligible_targets_and_names(world):
    """Given a view whose binding takes only targets whose code starts with OK, when a job asks for
    targets, then the provider receives the eligible records alone, the whole list once, each source
    as its name and the fields the view shows, and an answer is written for an eligible one."""
    tag = uuid4().hex[:6]
    source = world.made("H", f"Quartz {tag}")
    good = world.made("K", f"Quartz mine {tag}", values={"K.code": f"OK-{tag}"})
    world.made("K", f"Quartz pit {tag}", values={"K.code": f"NO-{tag}"})
    done, change_set = _run_job(world, "Vcand", search=tag, changeSetName="Eligible")
    sent = fake.seen[-1].context
    assert [s["name"] for s in sent["sources"]] == [f"Quartz {tag}"]
    assert all("candidates" not in s for s in sent["sources"])
    names = {c["name"] for c in sent["candidates"]}
    assert f"Quartz mine {tag}" in names and f"Quartz pit {tag}" not in names
    # The seed's K records have codes of their own: the criteria hold for them too.
    assert all(
        c["fields"].get(world.key("K.code"), "").startswith("OK") for c in sent["candidates"]
    )
    assert {key for c in sent["candidates"] for key in c} == {"ref", "name", "fields"}
    row = _row(_coverage(world, "Vcand", change_set, search=tag), source)
    assert [t["object"]["id"] for t in _targets(row)] == [good["id"]] and done["aiProposal"][
        "proposed"
    ] == 1


@pytest.mark.journey("J49.3")
@pytest.mark.structures(*STRUCTURES)
@pytest.mark.settings(AI_PROVIDER=FAKE)
def test_with_more_than_a_hundred_eligible_targets_each_source_gets_its_closest_twenty(world):
    """Given more than 100 eligible targets, when a job asks for targets, then each source is sent
    its own 20 closest by name, the shared list is the union of those, and the best match is among
    them and is chosen."""
    tag = uuid4().hex[:6]
    pairs = _records(world, "Vnn", tag)
    items = [
        {
            "op": "create",
            "id": str(uuid4()),
            "applicationKey": world.app("K"),
            "objectTypeKey": world.key("K"),
            "name": f"Filler {tag} {n:03d}",
            "attributes": [
                {"attributeTypeKey": k, "value": v} for k, v in world.required_values("K").items()
            ],
        }
        for n in range(110)
    ]
    result = ok(
        world.api.post(
            "/batches", {"workspaceKey": W1, "policy": "atomic", "run": "inline", "items": items}
        )
    )
    assert result["job"]["result"] == "applied"
    done, change_set = _run_job(world, "Vnn", search=tag, changeSetName="Closest")
    sent = fake.seen[-1].context
    assert len(sent["sources"]) == 3
    shown = {c["ref"]: c["name"] for c in sent["candidates"]}
    for source in sent["sources"]:
        assert len(source["candidates"]) == 20
        own = {shown[ref] for ref in source["candidates"]}
        assert any(name.startswith(source["name"].split()[0]) for name in own), (source, own)
    assert len(shown) < 110 + 30  # not every target was sent
    assert done["aiProposal"]["proposed"] == 3
    rows = _coverage(world, "Vnn", change_set, search=tag)
    for source, target in pairs:
        assert [t["object"]["id"] for t in _targets(_row(rows, source))] == [target["id"]]


@pytest.mark.journey("J49.4")
@pytest.mark.structures(*STRUCTURES)
@pytest.mark.settings(AI_PROVIDER=FAKE)
def test_a_failing_provider_is_a_warning_and_writes_nothing(world):
    """Given a provider that cannot be reached, when the job runs, then it completes with a warning
    naming the failure, no source is proposed, each counts as not answered, the failed call is
    recorded against the job and the change set is as it was."""
    tag = uuid4().hex[:6]
    _records(world, "Vnn", tag)
    fake.script("mappingTarget", ProviderError("unreachable", "The provider could not be reached"))
    done, change_set = _run_job(world, "Vnn", search=tag, changeSetName="Nothing")
    result = done["aiProposal"]
    assert (result["proposed"], result["notAnswered"]) == (0, 3)
    assert result["warnings"] and "could not be reached" in result["warnings"][0]
    assert (done["state"], done["result"]) == ("completed", "rejected")
    assert change_set["version"] == done["changeSetVersion"]
    assert {r["state"] for r in _coverage(world, "Vnn", change_set, search=tag)} == {"unmapped"}
    call = _all(world, "/ai/calls")[0]
    assert (call["outcome"], call["failureKind"], call["jobId"]) == (
        "failed",
        "unreachable",
        done["id"],
    )


@pytest.mark.journey("J49.5")
@pytest.mark.structures(*STRUCTURES)
@pytest.mark.settings(AI_PROVIDER=FAKE)
def test_a_source_mapped_while_the_provider_answers_is_refused_by_its_token_and_counted(world):
    """Given a source a person maps in the change set while the provider is answering, when the
    answer arrives, then that source keeps the person's target without a mark, is counted as
    changed, and the others are proposed."""
    tag = uuid4().hex[:6]
    pairs = _records(world, "Vnn", tag)
    change_set = world.change_set(name="Busy")
    binding = _binding(world, "Vnn")
    other_target = pairs[1][1]

    def meanwhile(context):
        current = world.current(change_set)
        ok(
            world.api.put(
                f"/workspaces/{W1}/mappings",
                {
                    **binding,
                    "sourceObjectId": pairs[0][0]["id"],
                    "targetObjectId": other_target["id"],
                    "expectedMappingVersion": 0,
                    "changeSetId": change_set["id"],
                    "expectedChangeSetVersion": current["version"],
                },
            )
        )
        return fake.DEFAULTS["mappingTarget"](context)

    fake.script("mappingTarget", meanwhile)
    done, after = _run_job(
        world,
        "Vnn",
        search=tag,
        changeSetId=change_set["id"],
        expectedChangeSetVersion=world.current(change_set)["version"],
    )
    assert done["state"] == "completed"
    assert (done["aiProposal"]["proposed"], done["aiProposal"]["changed"]) == (2, 1)
    rows = _coverage(world, "Vnn", after, search=tag)
    mine = _row(rows, pairs[0][0])
    assert [t["object"]["id"] for t in _targets(mine)] == [other_target["id"]]
    assert "origin" not in _targets(mine)[0]
    assert all("origin" in _targets(_row(rows, source))[0] for source, _ in pairs[1:])
    assert done["changeSetVersion"] == after["version"]


@pytest.mark.journey("J49.6")
@pytest.mark.structures(*STRUCTURES)
@pytest.mark.settings(AI_PROVIDER=FAKE)
def test_a_caller_without_use_ai_proposals_is_refused_naming_the_group(world):
    """Given a client who may work in change sets but does not hold Use AI proposals, when it asks
    for proposals, then it is refused with 403 naming the group, and no job or change set exists."""
    role = ok(
        world.api.post("/roles", {"name": "Editors", "actionGroups": ["change-sets", "browse"]}),
        201,
    )
    _, editor = _client(world, "Editors", (role["key"], {"instance": True}))
    before = len(_all(world, f"/workspaces/{W1}/change-sets"))
    error = refused(_propose(editor, "Vnn", changeSetName="Not allowed"), 403, "FORBIDDEN")
    assert error["details"]["groups"] == ["ai-proposals"]
    assert len(_all(world, f"/workspaces/{W1}/change-sets")) == before


@pytest.mark.journey("J49.6")
@pytest.mark.structures(*STRUCTURES)
def test_without_a_provider_the_request_is_refused(world):
    """Given no provider, then asking is refused with 409 AI_NOT_CONFIGURED."""
    refused(_propose(world, "Vnn", changeSetName="None"), 409, "AI_NOT_CONFIGURED")


@pytest.mark.journey("J49.6")
@pytest.mark.structures(*STRUCTURES)
@pytest.mark.settings(AI_PROVIDER=FAKE, AI_SEND_LEVEL="samples")
def test_a_send_level_too_low_for_the_feature_or_above_the_ceiling_is_refused(world):
    """Given a ceiling of samples, then the feature is not offered, asking is refused with 409
    AI_SEND_LEVEL_TOO_LOW, and so is a request choosing a level above the ceiling, naming both."""
    status = ok(world.api.get("/ai/status"))
    assert {f["purpose"]: f["available"] for f in status["features"]} == {
        "mappingTarget": False,
        "queryTranslation": True,
    }
    refused(_propose(world, "Vnn", changeSetName="Low"), 409, "AI_SEND_LEVEL_TOO_LOW")
    error = refused(
        _propose(world, "Vnn", changeSetName="High", sendLevel="values"),
        409,
        "AI_SEND_LEVEL_TOO_LOW",
    )
    assert error["details"] == {"sendLevel": "values", "ceiling": "samples"}


@pytest.mark.journey("J49.6")
@pytest.mark.structures(*STRUCTURES)
@pytest.mark.settings(AI_PROVIDER=FAKE)
def test_a_person_may_choose_a_lower_level_but_this_feature_needs_values(world):
    """Given the default ceiling, then a request for values is accepted and one for a lower level is
    refused because the feature cannot work from it."""
    ok(_propose(world, "Vnn", changeSetName="Values", sendLevel="values"), 202)
    error = refused(
        _propose(world, "Vnn", changeSetName="Samples", sendLevel="samples"),
        409,
        "AI_SEND_LEVEL_TOO_LOW",
    )
    assert error["details"]["needs"] == "values"


@pytest.mark.journey("J49.6")
@pytest.mark.structures(*STRUCTURES)
@pytest.mark.settings(AI_PROVIDER=FAKE)
def test_a_request_must_name_one_change_set_and_a_real_view(world):
    """Given malformed requests, then both or neither of a change set's ID and name is 422, a
    missing view is 404, and a stale version is 409."""
    change_set = world.change_set(name="Stale")
    both = {"changeSetId": change_set["id"], "expectedChangeSetVersion": 1, "changeSetName": "x"}
    assert _propose(world, "Vnn", **both).status_code == 422
    assert _propose(world, "Vnn").status_code == 422
    assert _propose(world, "Vnn", changeSetId=change_set["id"]).status_code == 422
    assert _propose(world, "Vnn", changeSetName="x", expectedChangeSetVersion=1).status_code == 422
    refused(
        _propose(world, "Vnn", changeSetId=str(uuid4()), expectedChangeSetVersion=1),
        404,
        "CHANGE_SET_NOT_FOUND",
    )
    refused(
        world.api.post(
            f"/workspaces/{W1}/mapping-proposals",
            {"applicationKey": "nope", "viewKey": "nope", "changeSetName": "x"},
        ),
        404,
        "MAPPING_VIEW_NOT_FOUND",
    )
    refused(
        _propose(
            world,
            "Vnn",
            changeSetId=change_set["id"],
            expectedChangeSetVersion=change_set["version"] + 5,
        ),
        409,
        "CHANGE_SET_VERSION_CONFLICT",
    )


@pytest.mark.journey("J49.7")
@pytest.mark.structures(*STRUCTURES)
@pytest.mark.settings(AI_PROVIDER=FAKE)
def test_the_proposed_filter_a_changed_target_and_the_published_history(world):
    """Given proposals in a change set, when the grid lists the Proposed sources, a steward changes
    one target and the change set is published, then the filter lists the sources whose target is
    still the AI's, the changed one has lost its mark, and the history of a proposed mapping
    carries its origin while its actor is the publisher."""
    tag = uuid4().hex[:6]
    pairs = _records(world, "Vnn", tag)
    done, change_set = _run_job(world, "Vnn", search=tag, changeSetName="Review")
    refused(
        world.api.get(
            f"/workspaces/{W1}/mapping-coverage",
            **_identity(world, "Vnn"),
            **_binding(world, "Vnn"),
            proposed=True,
        ),
        422,
        "MAPPING_PROPOSED_NEEDS_CHANGE_SET",
    )
    proposed = _coverage(world, "Vnn", change_set, search=tag, proposed=True)
    assert {r["source"]["id"] for r in proposed} == {s["id"] for s, _ in pairs}

    # A steward points the first source somewhere else.
    first, _ = pairs[0]
    row = _row(proposed, first)
    elsewhere = pairs[2][1]
    current = world.current(change_set)
    ok(
        world.api.put(
            f"/workspaces/{W1}/mappings",
            {
                **_binding(world, "Vnn"),
                "sourceObjectId": first["id"],
                "targetObjectId": elsewhere["id"],
                "expectedMappingVersion": row["mappingVersion"],
                "changeSetId": change_set["id"],
                "expectedChangeSetVersion": current["version"],
            },
        )
    )
    after = world.current(change_set)
    still = _coverage(world, "Vnn", after, search=tag, proposed=True)
    assert {r["source"]["id"] for r in still} == {s["id"] for s, _ in pairs[1:]}
    changed = _row(_coverage(world, "Vnn", after, search=tag), first)
    assert [t["object"]["id"] for t in _targets(changed)] == [elsewhere["id"]]
    assert "origin" not in _targets(changed)[0]

    published = world.publish(change_set)
    assert published
    second_source, second_target = pairs[1]
    history = _all(world, f"/objects/{world.key('H')}/{second_source['id']}/history")
    entries = [e for e in history if e["aggregateType"] == "relation" and "origin" in e]
    assert len(entries) == 1, history
    assert entries[0]["origin"]["kind"] == "ai" and entries[0]["origin"]["reason"] == "Closest name"
    assert entries[0]["actor"]["id"] == done["requestedBy"]["id"]
    assert entries[0]["related"]["objectId"] == second_target["id"]
    # The corrected mapping was a person's: its entry has no origin.
    first_history = _all(world, f"/objects/{world.key('H')}/{first['id']}/history")
    assert not [e for e in first_history if "origin" in e]


@pytest.mark.journey("J49.3")
@pytest.mark.structures(*STRUCTURES)
@pytest.mark.settings(AI_PROVIDER=FAKE, AI_CONTEXT_TOKENS="4096")
def test_with_a_small_context_window_each_call_fits_half_of_it_and_every_source_is_asked(world):
    """Given a model whose window is 4,096 tokens, when a job asks about several sources, then it
    makes as many calls as it needs, none larger than half the window, and every source is asked
    once and proposed."""
    tag = uuid4().hex[:6]
    pairs = tuple(
        (f"{word} {'long ' * 80}", f"{word} target")
        for word in (
            "Quartz",
            "Basalt",
            "Granite",
            "Marble",
            "Slate",
            "Shale",
            "Flint",
            "Gneiss",
            "Chalk",
            "Pumice",
        )
    )
    _records(world, "Vnn", tag, pairs=pairs)
    done, _change_set = _run_job(world, "Vnn", search=tag, changeSetName="Small window")
    calls = [request for request in fake.seen if request.purpose == "mappingTarget"]
    assert len(calls) > 1, done["aiProposal"]
    for request in calls:
        size = (len(INSTRUCTIONS) + len(json.dumps(request.context, ensure_ascii=False))) // 3
        assert size + 60 * len(request.context["sources"]) <= 2048
    asked = [s["name"] for request in calls for s in request.context["sources"]]
    assert len(asked) == len(set(asked)) == len(pairs)
    assert done["aiProposal"]["proposed"] == len(pairs)
