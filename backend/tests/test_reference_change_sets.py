"""The ``change-sets`` area of the management API's reference, recorded from a run on the guide's
reference data (see ``test_reference_recording.py``, whose seed, scenario and normaliser this file uses).

An integrator who maintains the Graubünden timetable data prepares a change set (a new stop, a corrected
name, a stop moved to another municipality), reviews what it changes, checks it and publishes it. The
workspace then requires an approval from a second person: a change is submitted, sent back, withdrawn,
submitted again and approved, and the publication is withdrawn. A change set is discarded, and two are
moved onto a second release of the model. Each step records the main successful use of the operation it
calls; the refusals the area's text names are asserted without being recorded. The second person is
made through the API, as an administrator makes one.

    cd backend && RDM_RECORD_EXAMPLES=1 .venv/bin/python -m pytest tests/test_reference_change_sets.py -q
"""

import copy
import json
import time
from collections.abc import Iterator
from urllib.parse import parse_qs, urlsplit

import pytest
import seeds
from test_reference_recording import (
    BASE,
    RECORDING,
    SAMPLES,
    SEED,
    Scenario,
    _application,
    _loader,
    _register_seed,
    _send,
)
from test_reference_records import _one

WS = "/api/v1/workspaces/{workspace_key}"
GRAUBUENDEN = {"workspace_key": "graubuenden"}
CHANGE_SETS = WS + "/change-sets"
ONE = "/api/v1/change-sets/{change_set_id}"
PUBLICATIONS = WS + "/publications"
POLICY = WS + "/approval-policy"
PASSPHRASE = "a long passphrase for approving"


class Person(Scenario):
    """Another signed-in person's calls; the exchanges they record join the first scenario's."""

    def __init__(self, first: Scenario, email: str, password: str) -> None:
        self.client = first.client
        self.exchanges = first.exchanges
        self.api = _loader().Api(
            _send(first.client), base=BASE, email=email, password=password, log=lambda text: None
        )
        self.api.login()


@pytest.fixture(scope="module")
def change_sets() -> Iterator[Scenario]:
    _register_seed()
    seeds.ensure(SEED)
    url = seeds.clone(SEED)
    try:
        with _application(url) as client:
            scenario = Scenario(client)
            yield scenario
            if RECORDING:
                scenario.write_examples()
    finally:
        seeds.drop(url.database)


def _approver(s: Scenario) -> Person:
    """A second person who may approve in the workspace: made, given a password and a role."""
    made = s.call(
        "POST",
        "/api/v1/users",
        body={"name": "Reference Approver", "email": "approver@example.org"},
        status=201,
    )
    link = s.call(
        "POST",
        "/api/v1/users/{user_id}/password-reset",
        path={"user_id": made["id"]},
        body={},
        status=201,
    )
    token = parse_qs(urlsplit(link["url"]).query)["token"][0]
    answer = s.client.post(
        "/oauth/password", data={"token": token, "password": PASSPHRASE, "repeat": PASSPHRASE}
    )
    assert answer.status_code == 200, answer.text
    s.call(
        "POST",
        "/api/v1/grants",
        body={
            "principal": {"kind": "user", "id": made["id"]},
            "role": "owner",
            "scope": {"workspaceKey": "graubuenden"},
        },
        status=201,
    )
    return Person(s, "approver@example.org", PASSPHRASE)


def _version(s: Scenario, change_set_id: str) -> int:
    return s.call("GET", ONE, path={"change_set_id": change_set_id}, status=200)["version"]


def _active(s: Scenario) -> str | None:
    page = s.call("GET", PUBLICATIONS, path=GRAUBUENDEN, query={"pageSize": 1}, status=200)
    active = [item for item in page["items"] if item["status"] == "active"]
    return active[0]["id"] if active else None


def _publish_body(s: Scenario, change_set_id: str) -> dict:
    return {
        "expectedChangeSetVersion": _version(s, change_set_id),
        "expectedActivePublicationId": _active(s),
    }


def _new_stop(s: Scenario, change_set_id: str, parent_id: str, name: str, mode_id: str) -> dict:
    return s.call(
        "POST",
        "/api/v1/objects",
        body={
            "changeSetId": change_set_id,
            "expectedChangeSetVersion": _version(s, change_set_id),
            "applicationKey": "network",
            "objectTypeKey": "stop",
            "parentObjectId": parent_id,
            "name": name,
            "attributes": [
                {"attributeTypeKey": "designation", "value": name.split(", ")[-1]},
                {"attributeTypeKey": "stop-number", "value": 8599000 + len(name)},
            ],
            "initialRelations": [
                {
                    "relationTypeKey": "stop-served-by-mode",
                    "direction": "outgoing",
                    "otherObjectId": mode_id,
                }
            ],
        },
        status=201,
    )


def test_an_integrator_prepares_reviews_and_publishes_a_change_set(change_sets):
    s = change_sets
    zuoz = _one(s, "municipality", "Zuoz")
    davos = _one(s, "municipality", "Davos")
    pontresina = _one(s, "municipality", "Pontresina")
    train = _one(s, "mode", "Train")
    bus = _one(s, "mode", "Bus")

    # No approval is required yet: the policy holds its defaults.
    policy = s.call("GET", POLICY, path=GRAUBUENDEN, status=200)
    assert policy == {
        "workspaceKey": "graubuenden",
        "requireApproval": False,
        "secondPerson": False,
        "version": 0,
        "approverCount": policy["approverCount"],
    }

    # Start a change set from the live data and put a new stop and a corrected name in it.
    started = s.call(
        "POST",
        CHANGE_SETS,
        path=GRAUBUENDEN,
        body={"name": "Winter 2027: new stops", "source": "currentLive"},
        status=201,
        record="fromLiveData",
        summary="A change set started from the live data of the workspace",
    )
    cs = started["id"]
    assert started["version"] == 1 and started["source"] == "currentLive"
    where = {"change_set_id": cs}
    _new_stop(s, cs, zuoz["id"], "Zuoz, Sportplatz", train["id"])
    davos_stop = s.call(
        "GET",
        "/api/v1/objects/{object_type_key}",
        path={"object_type_key": "stop"},
        query={"parentObjectId": davos["id"], "sort": "name", "pageSize": 1},
        status=200,
    )["items"][0]
    s.call(
        "PATCH",
        "/api/v1/objects/{object_type_key}/{object_id}",
        path={"object_type_key": "stop", "object_id": davos_stop["id"]},
        body={
            "name": davos_stop["name"] + " (Post)",
            "expectedVersion": davos_stop["version"],
            "changeSetId": cs,
            "expectedChangeSetVersion": _version(s, cs),
        },
        status=200,
    )
    renamed = s.call(
        "PATCH",
        ONE,
        path=where,
        body={"name": "Winter 2027: new and renamed stops", "expectedVersion": _version(s, cs)},
        status=200,
        record="rename",
        summary="Rename the change set",
    )
    assert renamed["name"] == "Winter 2027: new and renamed stops"

    listed = s.call(
        "GET",
        CHANGE_SETS,
        path=GRAUBUENDEN,
        query={"pageSize": 5},
        status=200,
        record="inTheWorkspace",
        summary="The open change sets of the workspace, the oldest first",
    )
    assert [item["id"] for item in listed["items"]] == [cs]
    s.call(
        "GET",
        ONE,
        path=where,
        status=200,
        record="theChangeSet",
        summary="The change set with its version and the release it works under",
    )

    # Review what it changes.
    objects = s.call(
        "GET",
        ONE + "/object-changes",
        path=where,
        query={"pageSize": 10},
        status=200,
        record="whatItDoesToRecords",
        summary="The records the change set adds and changes",
    )
    assert {item["kind"] for item in objects["items"]} == {"added", "changed"}
    s.call(
        "GET",
        ONE + "/object-changes",
        path=where,
        query={"kind": "added", "objectTypeKey": "mode"},
        status=200,
    )
    relations = s.call(
        "GET",
        ONE + "/relation-changes",
        path=where,
        query={"containment": "false", "pageSize": 10},
        status=200,
        record="whatItDoesToRelationships",
        summary="The relationships the change set adds, without the parent edges",
    )
    assert [item["kind"] for item in relations["items"]] == ["added"]
    s.call(
        "GET", ONE + "/relation-changes", path=where, query={"relationTypeKey": "nope"}, status=422
    )

    checked = s.call(
        "POST",
        ONE + "/validation",
        path=where,
        status=200,
        record="check",
        summary="The change set checked as a whole: nothing to fix",
    )
    assert checked == {"valid": True, "diagnostics": []}

    # The new stop belongs under Pontresina: plan the move, read the plan, apply it.
    new_stop = next(
        i for i in objects["items"] if i["kind"] == "added" and i["objectTypeKey"] == "stop"
    )
    operation = {
        "kind": "move",
        "objectId": new_stop["objectId"],
        "parentObjectId": pontresina["id"],
    }
    plan = s.call(
        "POST",
        ONE + "/restructurings/preview",
        path=where,
        body={
            "operation": operation,
            "expectedChangeSetVersion": _version(s, cs),
            "pageSize": 5,
        },
        status=200,
        record="planAMove",
        summary="Plan moving the new stop under Pontresina, which writes nothing",
    )
    assert plan["status"] == "ready" and plan["summary"]["moveCount"] == 1
    applied = s.call(
        "POST",
        ONE + "/restructurings",
        path=where,
        body={
            "operation": operation,
            "expectedChangeSetVersion": plan["changeSetVersion"],
            "planDigest": plan["planDigest"],
        },
        status=200,
        record="applyTheMove",
        summary="Apply the planned move",
    )
    assert applied["changeSetVersion"] == plan["changeSetVersion"] + 1
    s.call(
        "POST",
        ONE + "/restructurings",
        path=where,
        body={
            "operation": operation,
            "expectedChangeSetVersion": plan["changeSetVersion"],
            "planDigest": plan["planDigest"],
        },
        status=409,
        code="CHANGE_SET_VERSION_CONFLICT",
    )

    # Publish it: the first publication of the workspace.
    s.call(
        "POST",
        ONE + "/publication",
        path=where,
        body={"expectedChangeSetVersion": _version(s, cs) - 1, "expectedActivePublicationId": None},
        status=409,
        code="CHANGE_SET_VERSION_CONFLICT",
    )
    first = s.call(
        "POST",
        ONE + "/publication",
        path=where,
        body=_publish_body(s, cs),
        status=200,
        record="publishDirectly",
        summary="Publish the change set: its changes are live, as Publication 1",
    )
    assert first["publicationNumber"] == 1 and first["status"] == "active"
    s.call("GET", ONE, path=where, status=404, code="CHANGE_SET_NOT_FOUND")

    # From now on the workspace requires an approval from a second person.
    s.call(
        "PUT",
        POLICY,
        path=GRAUBUENDEN,
        body={"requireApproval": True, "secondPerson": True, "expectedVersion": 0},
        status=200,
        record="requireApproval",
        summary="Require an approval, by a person other than the submitter",
    )
    s.call(
        "PUT",
        POLICY,
        path=GRAUBUENDEN,
        body={"requireApproval": False, "secondPerson": True, "expectedVersion": 1},
        status=422,
        code="APPROVAL_POLICY_INVALID",
    )
    policy = s.call(
        "GET",
        POLICY,
        path=GRAUBUENDEN,
        status=200,
        record="thePolicy",
        summary="The policy, with how many may approve",
    )
    assert policy["requireApproval"] and policy["secondPerson"] and policy["version"] == 1
    approver = _approver(s)

    # A second change set: submitted, sent back, submitted, withdrawn, submitted and approved.
    second = s.call(
        "POST",
        CHANGE_SETS,
        path=GRAUBUENDEN,
        body={"name": "A bus stop for Davos", "source": "currentLive"},
        status=201,
    )["id"]
    _new_stop(s, second, davos["id"], "Davos, Bahnhof Nord", bus["id"])
    s.call(
        "POST",
        ONE + "/publication",
        path={"change_set_id": second},
        body=_publish_body(s, second),
        status=409,
        code="APPROVAL_REQUIRED",
    )
    submitted = s.call(
        "POST",
        ONE + "/submission",
        path={"change_set_id": second},
        body={
            "expectedChangeSetVersion": _version(s, second),
            "comment": "Ready for the timetable",
        },
        status=201,
        record="submit",
        summary="Submit the change set for approval, with a comment",
    )
    assert submitted["state"] == "submitted" and submitted["decisions"] == []
    s.call(
        "PATCH",
        ONE,
        path={"change_set_id": second},
        body={"name": "A bus stop in Davos", "expectedVersion": _version(s, second)},
        status=409,
        code="CHANGE_SET_SUBMITTED",
    )
    s.call(
        "POST",
        ONE + "/decisions",
        path={"change_set_id": second},
        body={
            "outcome": "approve",
            "expectedChangeSetVersion": _version(s, second),
            "expectedActivePublicationId": _active(s),
        },
        status=403,
        code="FORBIDDEN",
    )
    approver.call(
        "POST",
        ONE + "/decisions",
        path={"change_set_id": second},
        body={"outcome": "sendBack", "expectedChangeSetVersion": _version(s, second)},
        status=422,
        code="COMMENT_REQUIRED",
    )
    sent_back = approver.call(
        "POST",
        ONE + "/decisions",
        path={"change_set_id": second},
        body={
            "outcome": "sendBack",
            "comment": "Please name the stop as the timetable does",
            "expectedChangeSetVersion": _version(s, second),
        },
        status=200,
    )
    assert sent_back["id"] == second
    s.call(
        "POST",
        ONE + "/submission",
        path={"change_set_id": second},
        body={"expectedChangeSetVersion": _version(s, second)},
        status=201,
    )
    s.call(
        "DELETE",
        ONE + "/submission",
        path={"change_set_id": second},
        status=204,
        record="withdrawSubmission",
        summary="Take the submission back",
    )
    s.call(
        "DELETE",
        ONE + "/submission",
        path={"change_set_id": second},
        status=409,
        code="NOT_SUBMITTED",
    )
    s.call(
        "POST",
        ONE + "/submission",
        path={"change_set_id": second},
        body={
            "expectedChangeSetVersion": _version(s, second),
            "comment": "Named as the timetable does",
        },
        status=201,
    )
    second_publication = approver.call(
        "POST",
        ONE + "/decisions",
        path={"change_set_id": second},
        body={
            "outcome": "approve",
            "comment": "Checked against the timetable",
            "expectedChangeSetVersion": _version(s, second),
            "expectedActivePublicationId": _active(s),
        },
        status=200,
        record="approve",
        summary="Approve: the change set is published as Publication 2",
    )
    assert second_publication["publicationNumber"] == 2
    requests = s.call(
        "GET",
        WS + "/publication-requests",
        path=GRAUBUENDEN,
        query={"pageSize": 5},
        status=200,
        record="requests",
        summary="The publication requests of the workspace, the newest first, with their decisions",
    )
    assert [item["state"] for item in requests["items"]] == ["approved", "withdrawn", "sentBack"]
    s.call(
        "GET",
        WS + "/publication-requests",
        path=GRAUBUENDEN,
        query={"state": "sentBack"},
        status=200,
    )

    # Read the publications and withdraw the current one.
    publications = s.call(
        "GET",
        PUBLICATIONS,
        path=GRAUBUENDEN,
        query={"pageSize": 5},
        status=200,
        record="ofTheWorkspace",
        summary="The publications of the workspace, the newest first",
    )
    assert [item["status"] for item in publications["items"]] == ["active", "withdrawn"]
    s.call(
        "GET",
        "/api/v1/publications/{publication_id}",
        path={"publication_id": second_publication["id"]},
        status=200,
        record="publication",
        summary="Publication 2, which superseded Publication 1",
    )
    s.call(
        "POST",
        "/api/v1/publications/{publication_id}/withdrawal",
        path={"publication_id": first["id"]},
        status=409,
        code="WORKSPACE_ACTIVE_PUBLICATION_CONFLICT",
    )
    s.call(
        "POST",
        "/api/v1/publications/{publication_id}/withdrawal",
        path={"publication_id": second_publication["id"]},
        status=204,
        record="withdraw",
        summary="Withdraw the current publication; live data stays as it is",
    )
    assert _active(s) is None

    # Turn the policy off again, then start a change set and discard it.
    s.call(
        "PUT",
        POLICY,
        path=GRAUBUENDEN,
        body={"requireApproval": False, "secondPerson": False, "expectedVersion": 1},
        status=200,
    )
    idea = s.call(
        "POST",
        CHANGE_SETS,
        path=GRAUBUENDEN,
        body={"name": "An idea that is dropped", "source": "currentLive"},
        status=201,
    )
    mine = s.call(
        "GET",
        "/api/v1/me/change-sets",
        query={"pageSize": 5},
        status=200,
        record="mine",
        summary="The open change sets the caller started, with the workspace and how many changes each holds",
    )
    assert [item["id"] for item in mine["items"]] == [idea["id"]]
    s.call(
        "DELETE",
        ONE,
        path={"change_set_id": idea["id"]},
        query={"expectedVersion": idea["version"]},
        status=204,
        record="discard",
        summary="Discard a change set that is not wanted",
    )

    # A second release of the model: change sets started before it stay on the first one.
    stays = s.call(
        "POST",
        CHANGE_SETS,
        path=GRAUBUENDEN,
        body={"name": "Moves to the new release", "source": "currentLive"},
        status=201,
    )
    migrates = s.call(
        "POST",
        CHANGE_SETS,
        path=GRAUBUENDEN,
        body={"name": "Migrates to the new release", "source": "currentLive"},
        status=201,
    )
    model = json.loads((SAMPLES / "model.json").read_text(encoding="utf-8"))
    later = copy.deepcopy(model)
    later["release"]["version"] = "1.8.2"
    draft = s.call(
        "POST", "/api/v1/model-drafts", body={"name": "Second release", "model": later}, status=201
    )
    release = s.call(
        "POST",
        "/api/v1/model-drafts/{draft_id}/installation",
        path={"draft_id": draft["id"]},
        body={"expectedVersion": draft["version"]},
        status=201,
    )
    current = s.call("GET", WS + "/model", path=GRAUBUENDEN, status=200)
    s.call(
        "POST",
        WS + "/model/activation",
        path=GRAUBUENDEN,
        body={
            "releaseId": release["id"],
            "expectedVersion": current["version"],
            "expectedReleaseId": current["releaseId"],
        },
        status=200,
    )
    assert stays["modelReleaseId"] == current["releaseId"]
    s.call(
        "POST",
        ONE + "/publication",
        path={"change_set_id": stays["id"]},
        body=_publish_body(s, stays["id"]),
        status=409,
        code="CHANGE_SET_MODEL_RELEASE_CONFLICT",
    )
    moved = s.call(
        "PATCH",
        ONE + "/model-release",
        path={"change_set_id": stays["id"]},
        body={"modelReleaseId": release["id"], "expectedChangeSetVersion": stays["version"]},
        status=200,
        record="moveToTheNewRelease",
        summary="Move a change set onto the release the workspace now runs",
    )
    assert moved["modelReleaseId"] == release["id"] and moved["version"] == stays["version"] + 1
    job = s.call(
        "POST",
        ONE + "/model-migrations",
        path={"change_set_id": migrates["id"]},
        body={"expectedChangeSetVersion": migrates["version"]},
        status=202,
        record="startAMigration",
        summary="Queue the preview of a move onto the release the workspace runs",
    )
    assert job["kind"] == "migration" and job["changeSetId"] == migrates["id"]
    for _ in range(60):  # the preview runs in the background; leave nothing running
        state = s.call("GET", "/api/v1/jobs/{job_id}", path={"job_id": job["id"]}, status=200)
        if state["state"] not in ("queued", "running"):
            break
        time.sleep(0.5)
    assert state["state"] == "awaiting_confirmation", state
