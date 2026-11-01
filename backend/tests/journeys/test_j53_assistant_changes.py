"""J53 — An assistant prepares a change (USER_JOURNEYS.md § AI, Product 0.16 AG3).

Through ``/mcp`` with the protocol's own client: a person has their assistant create a change set,
fill it, check it and submit it, and a steward edits one value and publishes, so live data changes
only then. An assistant works only in change sets its own principal created, and only as far as its
person's grants reach; a refusal says the engine's code and details, so it can correct itself. Every
case runs on two configurations, whose definitions differ, through the public API.
"""

from uuid import uuid4

import pytest
from scenario import W1, W2, ok, refused
from test_j39_sign_in import _bearer
from test_j40_authorization import _client
from test_j42_approvals import _active, _decide, _policy, _publish
from test_j44_changes import _changes
from test_j44_who_changed_what import _signed_in
from test_j51_agent_access import (
    ON,
    _agent_client,
    _browser,
    _client_token,
    _grant,
    _register,
    _tools,
)
from test_j51_agent_access import _sign_in as assistant_sign_in
from test_j52_assistant_reads import _answer, _reader, _refusal

NAME = "Claude Code"
CHANGE_SET_TOOLS = {
    "my_change_sets",
    "read_change_set",
    "change_set_changes",
    "validate_change_set",
    "create_change_set",
    "add_record",
    "change_record",
    "set_field",
    "add_relation",
    "change_relation",
    "submit_change_set",
}
SCOPES = ("R", "G", "M", "D", "D.active", "Bown")


def _assistant(world, username: str, *grants: tuple[str, dict]):
    """A person with ``grants`` signed in through an assistant: the person, how they see the API in
    their browser, and the assistant's token."""
    person, own = _signed_in(world, username, *grants)
    application = ok(_register(_browser(world)), 201)["client_id"]
    token = ok(assistant_sign_in(_browser(world), application, username))["access_token"]
    return person, own, token


def _contributor(world, username: str, **scope):
    return _assistant(world, username, ("contributor", {"workspaceKey": W1, **scope}))


def _started(world, token: str, name: str) -> dict:
    """A change set the assistant created, as its ID and the version it was last answered with."""
    answer = _answer(world, token, "create_change_set", workspace=W1, name=name)
    return {"id": answer["changeSetId"], "version": answer["version"]}


def _stage(change_set: dict) -> dict:
    return {
        "changeSetId": change_set["id"],
        "expectedChangeSetVersion": change_set["version"],
    }


def _written(change_set: dict, answer: dict) -> dict:
    """What a write answered, after checking it moved the change set on by one."""
    assert answer["changeSetVersion"] == change_set["version"] + 1, answer
    change_set["version"] = answer["changeSetVersion"]
    return answer


def _add(world, token: str, change_set: dict, name: str, **values) -> dict:
    return _written(
        change_set,
        _answer(
            world,
            token,
            "add_record",
            **_stage(change_set),
            applicationKey=world.app("R"),
            objectTypeKey=world.key("R"),
            name=name,
            attributes={**world.required_values("R"), **values},
        ),
    )


def _submitted(world, token: str, change_set: dict, comment: str | None = None) -> dict:
    more = {} if comment is None else {"comment": comment}
    return _answer(world, token, "submit_change_set", **_stage(change_set), **more)


def _live_names(world) -> list[str]:
    return world.names(
        ok(world.api.get(f"/objects/{world.key('R')}", workspaceKey=W1, pageSize=500))
    )


@pytest.mark.journey("J53.1")
@pytest.mark.settings(**ON)
@pytest.mark.structures("R", "R.n")
def test_a_person_has_their_assistant_prepare_values_and_a_steward_publishes_them(world):
    """Given a person and their assistant, and an owner. The assistant creates a change set, adds
    five records, finds it listed with its version, checks and submits it; live data is unchanged
    and the owner has the notice. The owner edits one value, which withdraws the submission, and
    publishes: live data changes only then. The record says the assistant prepared it for the
    person and the owner edited it, and every change the person made through the assistant is
    marked as made through it, the owner's not."""
    owner, steward = _client(world, "Steward", ("owner", {"workspaceKey": W1}))
    person, _own, token = _contributor(world, "petra")
    change_set = _started(world, token, "Five missing values")
    added = [
        _add(world, token, change_set, f"Missing {n}", **{world.key("R.n"): n}) for n in range(5)
    ]
    assert len({item["id"] for item in added}) == 5

    listed = _answer(world, token, "my_change_sets")["items"]
    [mine] = [item for item in listed if item["id"] == change_set["id"]]
    assert (mine["version"], mine["changeCount"]) == (change_set["version"], 5)
    changes = _answer(world, token, "change_set_changes", changeSetId=change_set["id"])
    assert {item["kind"] for item in changes["items"]} == {"added"} and len(changes["items"]) == 5

    checked = _answer(world, token, "validate_change_set", changeSetId=change_set["id"])
    assert (checked["valid"], checked["count"], checked["diagnostics"]) == (True, 0, [])
    sent = _submitted(world, token, change_set, "Five values were missing")
    assert sent["state"] == "submitted"
    assert not [name for name in _live_names(world) if name.startswith("Missing ")]

    [notice] = ok(steward.api.get("/me/notifications"))["items"]
    assert notice["kind"] == "change-set.submitted"
    assert notice["subject"] == {"kind": "change-set", "id": change_set["id"]}
    assert notice["details"]["actor"]["name"] == person["name"]

    edited = added[0]["id"]
    staged = world.record("R", edited, changeSetId=change_set["id"])
    assert staged["origin"]["kind"] == "agent" and staged["origin"]["application"] == NAME
    assert staged["origin"]["proposedBy"] == person["id"]
    assert staged["origin"]["proposedByName"] == person["name"]
    body = {
        "expectedVersion": staged["version"],
        "attributes": [{"attributeTypeKey": world.key("R.n"), "value": 99}],
        "changeSetId": change_set["id"],
        "expectedChangeSetVersion": steward.current(change_set)["version"],
    }
    ok(steward.api.patch(f"/objects/{world.key('R')}/{edited}", body, withdrawSubmission=True))
    after = world.record("R", edited, changeSetId=change_set["id"])
    assert (
        after["origin"]["editedBy"] == owner["id"] and after["origin"]["editedByName"] == "Steward"
    )
    assert not [name for name in _live_names(world) if name.startswith("Missing ")]

    ok(_publish(world, steward, change_set))
    assert {f"Missing {n}" for n in range(5)} <= set(_live_names(world))
    assert world.value(world.record("R", edited), "R.n") == 99
    history = ok(world.api.get(f"/objects/{world.key('R')}/{edited}/history"))["items"]
    entry = next(item for item in history if item.get("origin"))
    assert entry["origin"]["application"] == NAME and entry["origin"]["proposedBy"] == person["id"]
    assert entry["origin"]["editedBy"] == owner["id"]

    through_it = _changes(world, actorId=person["id"])
    assert through_it and all(item.get("channel") == "mcp" for item in through_it)
    assert "change-set" in {item["kind"] for item in through_it}
    theirs = _changes(world, actorId=owner["id"])
    assert theirs and not any("channel" in item for item in theirs)


@pytest.mark.journey("J53.2")
@pytest.mark.settings(**ON)
@pytest.mark.structures("R", "R.n")
def test_what_an_assistant_submits_is_decided_by_a_second_person_and_never_by_it(world):
    """Given a workspace requiring approval by a second person, and a person holding Approve through
    their browser. When their assistant submits a change set, the person is refused the decision on
    it, and a second owner approves. An agent client's token, whatever role it holds, reaches no
    approve or publish route and is offered no tool for them."""
    ok(_policy(world, requireApproval=True, secondPerson=True))
    _person, own, token = _assistant(world, "olga", ("owner", {"workspaceKey": W1}))
    second = _client(world, "Second owner", ("owner", {"workspaceKey": W1}))[1]
    change_set = _started(world, token, "Needs two people")
    _add(world, token, change_set, "Awaiting a second person")
    _submitted(world, token, change_set)

    own_decision = _decide(world, own, own.current(change_set), "approve")
    assert refused(own_decision, 403, "FORBIDDEN")["details"]["reason"] == "ownApproval"
    assert "Awaiting a second person" not in _live_names(world)
    ok(_decide(world, second, second.current(change_set), "approve"))
    assert _active(world) and "Awaiting a second person" in _live_names(world)

    agent = _agent_client(world, "Nightly agent")
    _grant(world, "client", agent["id"], "owner")
    agent_token = ok(_client_token(world, agent))["access_token"]
    for route in ("decisions", "publication"):
        sent = _browser(world).post(
            f"/api/v1/change-sets/{change_set['id']}/{route}",
            json={},
            headers=_bearer(agent_token),
        )
        refused(sent, 401, "TOKEN_INVALID")
    offered = set(_tools(world, agent_token))
    assert CHANGE_SET_TOOLS <= offered
    assert not [name for name in offered if "approve" in name or "publish" in name]


@pytest.mark.journey("J53.3")
@pytest.mark.settings(**ON)
@pytest.mark.structures(*SCOPES)
def test_a_refusal_says_why_and_a_sent_back_change_set_is_fixed_and_submitted_again(world):
    """Given a change set whose record move breaches a scoped uniqueness rule. Then submitting it is
    refused with the code and its diagnostics, validating lists them, a stale version is refused
    with the version it has now, and a write with a stale change set version with its own code.
    Moved back it validates and is submitted, a write to it is refused as submitted, an owner sends
    it back with a comment the assistant reads, and it is fixed and submitted again."""
    owner = _client(world, "Reviewer", ("owner", {"workspaceKey": W1}))[1]
    r = world.made("R", "Owner")
    g1, g2 = world.made("G", "Scope one"), world.made("G", "Scope two")
    m1 = world.made("M", "Container one", parent=g1["id"])
    m2 = world.made("M", "Container two", parent=g2["id"])
    for name, container in (("First", m1), ("Second", m2)):
        world.made(
            "D",
            name,
            parent=container["id"],
            values={"D.active": True},
            relations=[world.owner("Bown", r["id"])],
        )
    _person, _own, token = _contributor(world, "mira")
    change_set = _started(world, token, "Move a container")

    def move(version: int, **more) -> dict:
        return _answer(
            world,
            token,
            "change_record",
            **_stage(change_set),
            objectType=world.key("M"),
            id=m2["id"],
            expectedVersion=version,
            **more,
        )

    moved = _written(change_set, move(m2["version"], parentObjectId=g1["id"]))
    refusal = _refusal(world, token, "submit_change_set", **_stage(change_set))
    assert refusal.startswith("CHANGE_SET_INVALID:") and "DUPLICATE_RELATION_SCOPE" in refusal
    checked = _answer(world, token, "validate_change_set", changeSetId=change_set["id"])
    assert checked["valid"] is False and checked["count"] >= 1
    assert "DUPLICATE_RELATION_SCOPE" in {item["code"] for item in checked["diagnostics"]}

    stale = {**_stage(change_set), "expectedChangeSetVersion": change_set["version"] - 1}
    conflict = _refusal(world, token, "submit_change_set", **stale)
    assert conflict.startswith("VERSION_CONFLICT:")
    assert f'"currentVersion": {change_set["version"]}' in conflict
    write = _refusal(
        world,
        token,
        "change_record",
        **stale,
        objectType=world.key("M"),
        id=m2["id"],
        expectedVersion=moved["version"],
        name="Too late",
    )
    assert write.startswith("CHANGE_SET_VERSION_CONFLICT:")

    fixed = _written(change_set, move(moved["version"], parentObjectId=g2["id"]))
    valid = _answer(world, token, "validate_change_set", changeSetId=change_set["id"])
    assert valid["valid"] is True
    assert _submitted(world, token, change_set)["state"] == "submitted"
    frozen = _refusal(
        world,
        token,
        "change_record",
        **_stage(change_set),
        objectType=world.key("M"),
        id=m2["id"],
        expectedVersion=fixed["version"],
        name="Changed while submitted",
    )
    assert frozen.startswith("CHANGE_SET_SUBMITTED:")

    reason = "Name the container after its scope"
    ok(_decide(world, owner, change_set, "sendBack", reason))
    read = _answer(world, token, "read_change_set", changeSetId=change_set["id"])
    assert read["submission"]["state"] == "sentBack"
    assert read["submission"]["lastDecision"]["outcome"] == "sendBack"
    assert read["submission"]["lastDecision"]["comment"] == reason

    change_set["version"] = read["version"]
    renamed = _written(change_set, move(fixed["version"], name="Container two, scope two"))
    assert renamed["id"] == m2["id"]
    assert _submitted(world, token, change_set, "Renamed as asked")["state"] == "submitted"
    again = _answer(world, token, "read_change_set", changeSetId=change_set["id"])
    assert again["submission"]["state"] == "submitted"
    assert again["submission"]["lastDecision"] is None


@pytest.mark.journey("J53.4")
@pytest.mark.settings(**ON)
@pytest.mark.structures("R", "K", "R.n")
def test_an_assistant_stays_in_its_own_change_sets_and_its_persons_grants(world):
    """Given a colleague's change set. Then every tool naming it answers not found, as for one that
    does not exist, and it is not listed. A person narrowed to one record type has their assistant
    refused another. No write tool takes a call without a change set, and a Browse client lists no
    change-set tool and cannot call one."""
    colleague = world.change_set()
    _person, _own, token = _contributor(world, "pia")
    mine = _started(world, token, "Mine")
    listed = _answer(world, token, "my_change_sets")["items"]
    assert [item["id"] for item in listed] == [mine["id"]]
    closed = _refusal(world, token, "my_change_sets", workspace=W2)
    assert closed == f"WORKSPACE_NOT_FOUND: Workspace '{W2}' not found"

    record = {
        "applicationKey": world.app("R"),
        "objectTypeKey": world.key("R"),
        "name": "Not allowed",
    }
    for change_set_id in (colleague["id"], str(uuid4())):
        staged = {"changeSetId": change_set_id, "expectedChangeSetVersion": 1}
        calls = {
            "read_change_set": {},
            "change_set_changes": {},
            "validate_change_set": {},
            "submit_change_set": {"expectedChangeSetVersion": 1},
            "add_record": {**staged, **record},
            "set_field": {
                **staged,
                "id": str(uuid4()),
                "attributeTypeKey": world.key("R.n"),
                "value": 1,
                "expectedVersion": 1,
            },
            "find_records": {"workspace": W1, "objectTypeKey": world.key("R")},
            "describe_type": {"workspace": W1, "objectType": world.key("R")},
            "read_record": {"workspace": W1, "objectType": world.key("R"), "id": str(uuid4())},
        }
        for tool, more in calls.items():
            arguments = {"changeSetId": change_set_id, **more}
            said = _refusal(world, token, tool, **arguments)
            assert said == f"CHANGE_SET_NOT_FOUND: Change set '{change_set_id}' not found", tool

    _person, _own, narrowed = _contributor(world, "quinn", recordTypes=[world.key("R")])
    own = _started(world, narrowed, "Only one type")
    _add(world, narrowed, own, "Allowed")
    other = {
        **_stage(own),
        "applicationKey": world.app("K"),
        "objectTypeKey": world.key("K"),
        "name": "Refused",
        "attributes": world.required_values("K"),
    }
    said = _refusal(world, narrowed, "add_record", **other)
    assert said.startswith("FORBIDDEN:") and world.key("K") in said and "recordTypes" in said

    version = {"expectedChangeSetVersion": 1}
    needs = {
        "validate_change_set": {},
        "add_record": {**version, **record},
        "change_record": {
            **version,
            "objectType": world.key("R"),
            "id": "x",
            "expectedVersion": 1,
        },
        "set_field": {
            **version,
            "id": "x",
            "attributeTypeKey": "k",
            "value": 1,
            "expectedVersion": 1,
        },
        "add_relation": {**version, "relationTypeKey": "r", "fromObjectId": "a", "toObjectId": "b"},
        "change_relation": {**version, "id": "x", "expectedVersion": 1, "attributes": {}},
        "submit_change_set": version,
    }
    for tool, arguments in needs.items():
        assert "'changeSetId' is a required property" in _refusal(world, token, tool, **arguments)

    browsing = _reader(world)
    offered = set(_tools(world, browsing))
    assert "find_records" in offered and not offered & CHANGE_SET_TOOLS
    assert "no tool named" in _refusal(world, browsing, "create_change_set", workspace=W1, name="x")


@pytest.mark.journey("J53.5")
@pytest.mark.settings(**ON)
@pytest.mark.structures("R", "R.n")
def test_reads_with_a_change_set_show_its_rows_and_the_model_it_is_pinned_to(world):
    """Given a person's change set with a record only it holds, and the workspace moved on to a
    release adding an attribute. Then find_records, read_record and describe_type with the change
    set show the unpublished record and the release it is pinned to, and without it live data
    and the release live data runs."""
    _person, own, token = _contributor(world, "rhea")
    world.made("R", "Already live")
    change_set = own.change_set()
    staged = _answer(
        world,
        token,
        "add_record",
        **_stage(own.current(change_set)),
        applicationKey=world.app("R"),
        objectTypeKey=world.key("R"),
        name="Only staged",
        attributes=world.required_values("R"),
    )
    model, added = world.candidate("compatible")
    ok(world.activate(world.install(model)["id"], W1))

    where = [{"field": "name", "op": "eq", "value": "Only staged"}]
    arguments = {"workspace": W1, "objectTypeKey": world.key("R"), "where": where}
    assert _answer(world, token, "find_records", **arguments)["items"] == []
    found = _answer(world, token, "find_records", **arguments, changeSetId=change_set["id"])
    assert [item["id"] for item in found["items"]] == [staged["id"]]

    one = {"workspace": W1, "objectType": world.key("R"), "id": staged["id"]}
    assert _refusal(world, token, "read_record", **one).startswith("OBJECT_NOT_FOUND:")
    read = _answer(world, token, "read_record", **one, changeSetId=change_set["id"])
    assert read["record"]["name"] == "Only staged" and read["relations"]["items"] == []

    type_of = {"workspace": W1, "objectType": world.key("R")}
    live = _answer(world, token, "describe_type", **type_of)
    pinned = _answer(world, token, "describe_type", **type_of, changeSetId=change_set["id"])
    assert added in {item["attributeTypeKey"] for item in live["attributes"]}
    assert added not in {item["attributeTypeKey"] for item in pinned["attributes"]}
