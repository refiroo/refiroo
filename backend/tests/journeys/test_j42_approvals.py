"""J42 — propose and approve a change (0.12 A1).

A Contributor prepares a change set and submits it; an approver (a holder of Approve publications)
approves, which publishes it, or sends it back with a comment. A workspace's policy can require an
approval for every publication and a second person to give it. Written from the A1 plan and
API.md § Approvals, before any implementation. Each case runs on two configurations through the
public API, with clients holding predefined roles.
"""

import pytest
from scenario import W1, ok, refused
from test_j40_authorization import _client

REQUESTS = f"/workspaces/{W1}/publication-requests"
POLICY = f"/workspaces/{W1}/approval-policy"


def _actors(world, **roles: str):
    return {
        name: _client(world, name, (role, {"workspaceKey": W1}))[1] for name, role in roles.items()
    }


def _proposal(world, actor, name: str = "Proposed") -> dict:
    """A change set made by ``actor`` with one new record in it."""
    change_set = actor.change_set()
    ok(actor.create("R", name, change_set=change_set), 201)
    return actor.current(change_set)


def _edit(world, actor, change_set: dict, name: str, **params):
    body = {
        "applicationKey": world.app("R"),
        "objectTypeKey": world.key("R"),
        "name": name,
        "attributes": [
            {"attributeTypeKey": k, "value": v} for k, v in world.required_values("R").items()
        ],
        "changeSetId": change_set["id"],
        "expectedChangeSetVersion": change_set["version"],
    }
    return actor.api.post("/objects", body, **params)


def _submit(actor, change_set: dict, comment: str | None = None):
    body = {"expectedChangeSetVersion": change_set["version"]}
    if comment is not None:
        body["comment"] = comment
    return actor.api.post(f"/change-sets/{change_set['id']}/submission", body)


def _active(world) -> str | None:
    items = ok(world.api.get(f"/workspaces/{W1}/publications", pageSize=1))["items"]
    active = [item for item in items if item.get("status") == "active"]
    return active[0]["id"] if active else None


def _decide(world, actor, change_set: dict, outcome: str, comment: str | None = None, **body):
    payload = {
        "outcome": outcome,
        "expectedChangeSetVersion": change_set["version"],
        "expectedActivePublicationId": _active(world),
        **body,
    }
    if comment is not None:
        payload["comment"] = comment
    return actor.api.post(f"/change-sets/{change_set['id']}/decisions", payload)


def _publish(world, actor, change_set: dict):
    body = {
        "expectedChangeSetVersion": actor.current(change_set)["version"],
        "expectedActivePublicationId": _active(world),
    }
    return actor.api.post(f"/change-sets/{change_set['id']}/publication", body)


def _requests(actor, **params) -> list[dict]:
    return ok(actor.api.get(REQUESTS, **params))["items"]


def _policy(world, **flags):
    current = ok(world.api.get(POLICY))
    body = {"requireApproval": False, "secondPerson": False, **flags}
    return world.api.put(POLICY, {**body, "expectedVersion": current["version"]})


def _groups(error: dict) -> list[str]:
    return error["details"]["groups"]


@pytest.mark.journey("J42")
def test_a_contributor_submits_and_an_approver_approves_and_publishes(world):
    """Given a Contributor with a change set holding a new record. When they submit it and an
    approver approves, then the answer is the publication, the record is live, and the request
    lists as approved with one decision row (decider, version, comment)."""
    actors = _actors(world, contributor="contributor", approver="owner")
    contributor, approver = actors["contributor"], actors["approver"]
    change_set = _proposal(world, contributor, "Awaiting approval")
    ok(_submit(contributor, change_set, "Please check"), 201)
    submitted = _requests(contributor, state="submitted")
    assert [item["comment"] for item in submitted] == ["Please check"]
    assert contributor.current(change_set)["submission"]["state"] == "submitted"

    version = contributor.current(change_set)["version"]
    published = ok(_decide(world, approver, {**change_set, "version": version}, "approve", "Fine"))
    assert published["id"] and _active(world) == published["id"]
    names = world.names(ok(world.api.get(f"/objects/{world.key('R')}", workspaceKey=W1)))
    assert "Awaiting approval" in names

    [approved] = _requests(contributor, state="approved")
    assert approved["state"] == "approved"
    [decision] = approved["decisions"]
    assert decision["outcome"] == "approve" and decision["comment"] == "Fine"
    assert decision["version"] == version
    assert decision["decider"]["id"] == actors_id(world, approver)


def actors_id(world, actor) -> str:
    return ok(actor.api.get("/me"))["id"]


@pytest.mark.journey("J42")
def test_a_contributor_cannot_publish_or_approve_and_a_reader_cannot_submit(world):
    """Given a Contributor with a submitted change set and a Reader. When the Contributor publishes
    directly or approves, and the Reader submits, then each is `403 FORBIDDEN` naming the groups
    that would allow it."""
    actors = _actors(world, contributor="contributor", reader="reader")
    contributor, reader = actors["contributor"], actors["reader"]
    change_set = _proposal(world, contributor)
    ok(_submit(contributor, change_set), 201)
    published = refused(_publish(world, contributor, change_set), 403, "FORBIDDEN")
    assert _groups(published) == ["publish"]
    decided = refused(_decide(world, contributor, change_set, "approve"), 403, "FORBIDDEN")
    assert _groups(decided) == ["approve"]
    submitted = refused(_submit(reader, change_set), 403, "FORBIDDEN")
    assert _groups(submitted) == ["change-sets"]
    assert [item["state"] for item in _requests(contributor)] == ["submitted"]


@pytest.mark.journey("J42.1")
def test_a_change_set_sent_back_with_a_comment_is_edited_and_submitted_again(world):
    """Given a submitted change set. When an approver sends it back without a comment, then `422
    COMMENT_REQUIRED`; with one, the change set is open again, the Contributor reads the comment,
    edits and submits again, and the request list shows both requests."""
    actors = _actors(world, contributor="contributor", approver="owner")
    contributor, approver = actors["contributor"], actors["approver"]
    change_set = _proposal(world, contributor)
    ok(_submit(contributor, change_set), 201)
    refused(_decide(world, approver, change_set, "sendBack"), 422, "COMMENT_REQUIRED")
    assert contributor.current(change_set)["submission"]["state"] == "submitted"
    ok(_decide(world, approver, change_set, "sendBack", "Name it properly"))

    [returned] = _requests(contributor, state="sentBack")
    assert [item["comment"] for item in returned["decisions"]] == ["Name it properly"]
    assert contributor.current(change_set)["submission"]["state"] != "submitted"
    ok(_edit(world, contributor, contributor.current(change_set), "Named properly"), 201)
    ok(_submit(contributor, contributor.current(change_set), "Again"), 201)
    states = sorted(item["state"] for item in _requests(contributor))
    assert states == ["sentBack", "submitted"]


@pytest.mark.journey("J42.2")
def test_an_edit_of_a_submitted_change_set_needs_to_withdraw_the_submission(world):
    """Given a submitted change set. When it is edited, then `409 CHANGE_SET_SUBMITTED`; with
    `withdrawSubmission=true` the edit passes and the submission is withdrawn. Approving the version
    submitted earlier is refused (`VERSION_CONFLICT` or `NOT_SUBMITTED`) and publishes nothing;
    submitting the new version, then approving it, works."""
    actors = _actors(world, contributor="contributor", approver="owner")
    contributor, approver = actors["contributor"], actors["approver"]
    change_set = _proposal(world, contributor)
    ok(_submit(contributor, change_set), 201)
    before = _active(world)
    refused(_edit(world, contributor, change_set, "Too late"), 409, "CHANGE_SET_SUBMITTED")
    ok(_edit(world, contributor, change_set, "Withdrawing", withdrawSubmission=True), 201)
    assert [item["state"] for item in _requests(contributor)] == ["withdrawn"]

    stale = _decide(world, approver, change_set, "approve")
    refused(stale, 409, "NOT_SUBMITTED")
    assert _active(world) == before

    newer = contributor.current(change_set)
    ok(_submit(contributor, newer), 201)
    ok(_decide(world, approver, newer, "approve"))
    assert _active(world) != before


@pytest.mark.journey("J42.3")
def test_with_approval_required_an_owner_publishes_in_one_step_and_a_steward_cannot(world):
    """Given `requireApproval`. When an owner (Publish and Approve) publishes their own change set
    directly, then it is published and an approval by them is recorded; when a steward (Publish
    only) does, then `409 APPROVAL_REQUIRED` and nothing is published. With the policy off the
    steward publishes as before."""
    actors = _actors(world, owner="owner", steward="steward")
    owner, steward = actors["owner"], actors["steward"]
    ok(_policy(world, requireApproval=True))
    mine = _proposal(world, owner, "Owner's own")
    ok(_publish(world, owner, mine))
    [approved] = _requests(owner, state="approved")
    assert [d["decider"]["id"] for d in approved["decisions"]] == [actors_id(world, owner)]

    theirs = _proposal(world, steward, "Steward's")
    before = _active(world)
    refused(_publish(world, steward, theirs), 409, "APPROVAL_REQUIRED")
    assert _active(world) == before
    ok(_policy(world))
    ok(_publish(world, steward, steward.current(theirs)))
    assert _active(world) != before


@pytest.mark.journey("J42.4")
def test_with_a_second_person_required_the_submitter_cannot_approve_their_own(world):
    """Given `secondPerson` (which needs `requireApproval`, else `422 APPROVAL_POLICY_INVALID`).
    When the submitter, an owner, approves their own request, then `403 FORBIDDEN` with reason
    `ownApproval`; their direct publication is `409 APPROVAL_REQUIRED`; another owner approves."""
    refused(_policy(world, secondPerson=True), 422, "APPROVAL_POLICY_INVALID")
    ok(_policy(world, requireApproval=True, secondPerson=True))
    actors = _actors(world, submitter="owner", other="owner")
    submitter, other = actors["submitter"], actors["other"]
    change_set = _proposal(world, submitter)
    refused(_publish(world, submitter, change_set), 409, "APPROVAL_REQUIRED")
    ok(_submit(submitter, submitter.current(change_set)), 201)
    own = refused(
        _decide(world, submitter, submitter.current(change_set), "approve"), 403, "FORBIDDEN"
    )
    assert own["details"]["reason"] == "ownApproval"
    assert [item["state"] for item in _requests(submitter)] == ["submitted"]
    ok(_decide(world, other, submitter.current(change_set), "approve"))
    assert [item["state"] for item in _requests(submitter)] == ["approved"]


@pytest.mark.journey("J42.6")
def test_an_approval_after_the_workspace_changed_is_refused_and_records_nothing(world):
    """Given a submitted change set and the active publication seen by the approver. When another
    change set is published meanwhile, then approving with the old active publication is `409
    PUBLICATION_CONFLICT`, no decision is recorded and the request is still submitted."""
    actors = _actors(world, contributor="contributor", approver="owner")
    contributor, approver = actors["contributor"], actors["approver"]
    ok(_policy(world))
    world.publish(world.change_set())
    seen = _active(world)
    change_set = _proposal(world, contributor)
    ok(_submit(contributor, change_set), 201)

    other = world.change_set()
    world.made("R", "Meanwhile", change_set=world.current(other))
    world.publish(other)
    assert _active(world) != seen
    stale = _decide(world, approver, change_set, "approve", expectedActivePublicationId=seen)
    refused(stale, 409, "PUBLICATION_CONFLICT")
    [request] = _requests(approver)
    assert request["state"] == "submitted" and request["decisions"] == []
    assert approver.current(change_set)["submission"]["state"] == "submitted"


@pytest.mark.journey("J40")
def test_the_policy_is_read_by_a_reader_and_changed_by_a_workspace_administrator(world):
    """Given the predefined roles. When a Reader reads the policy, then both flags are off; when a
    Reader, a steward or an owner changes it, then `403 FORBIDDEN`; a workspace administrator
    changes it, and a stale `expectedVersion` is `409 VERSION_CONFLICT`. Data owner holds the
    `approve` group, Data steward does not."""
    actors = _actors(world, reader="reader", steward="steward", owner="owner")
    admin = _client(world, "Admin", ("workspace-admin", {"instance": True}))[1]
    policy = ok(actors["reader"].api.get(POLICY))
    assert (policy["requireApproval"], policy["secondPerson"]) == (False, False)
    approvers = policy["approverCount"]
    _actors(world, second_owner="owner")
    assert ok(actors["reader"].api.get(POLICY))["approverCount"] == approvers + 1
    body = {"requireApproval": True, "secondPerson": False, "expectedVersion": policy["version"]}
    for name in ("reader", "steward", "owner"):
        refused(actors[name].api.put(POLICY, body), 403, "FORBIDDEN")
    changed = ok(admin.api.put(POLICY, body))
    assert changed["requireApproval"] is True
    refused(admin.api.put(POLICY, body), 409, "VERSION_CONFLICT")
    assert "approve" in ok(world.api.get("/roles/owner"))["actionGroups"]
    assert "approve" not in ok(world.api.get("/roles/steward"))["actionGroups"]


@pytest.mark.journey("J42")
def test_an_approval_binds_the_version_that_was_submitted(world):
    """Given a submitted change set whose version moved on without a new submission (the state
    arrives from outside the API: no client route changes a submitted change set without
    withdrawing the request). When an approver decides with the version they read, then `409
    VERSION_CONFLICT`, nothing is published and the request stays submitted (0.12 R-F7)."""
    from sqlalchemy import create_engine, text
    from sqlalchemy.pool import NullPool

    actors = _actors(world, contributor="contributor", approver="owner")
    contributor, approver = actors["contributor"], actors["approver"]
    change_set = _proposal(world, contributor, "Moved on")
    ok(_submit(contributor, change_set), 201)
    engine = create_engine(world.database, poolclass=NullPool)
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE change_sets SET version = version + 1 WHERE id = :id"),
            {"id": change_set["id"]},
        )
    engine.dispose()
    current = contributor.current(change_set)

    error = refused(_decide(world, approver, current, "approve"), 409, "VERSION_CONFLICT")
    assert error["details"]["currentVersion"] == current["version"]
    assert [item["state"] for item in _requests(contributor)] == ["submitted"]
    assert "Moved on" not in world.names(
        ok(world.api.get(f"/objects/{world.key('R')}", workspaceKey=W1))
    )


@pytest.mark.journey("J42.2")
def test_a_request_is_withdrawn_only_by_its_submitter_or_an_approver(world):
    """Given a submitted change set. When another Contributor edits it with
    `withdrawSubmission=true` or withdraws it, then each answers `403 FORBIDDEN` (`reason:
    notSubmitter`) and the request stays submitted; an approver holding Approve and Browse but not
    Work in change sets withdraws it, and the submitter withdraws a request of their own with
    either route (0.12 R-F9, the one rule)."""
    actors = _actors(world, contributor="contributor", other="contributor")
    contributor, other = actors["contributor"], actors["other"]
    approver_role = ok(
        world.api.post("/roles", {"name": "Only approves", "copiedFrom": "owner"}), 201
    )
    ok(
        world.api.patch(
            f"/roles/{approver_role['key']}",
            {"expectedVersion": approver_role["version"], "actionGroups": ["browse", "approve"]},
        )
    )
    _, approver = _client(world, "Approver", (approver_role["key"], {"workspaceKey": W1}))
    change_set = _proposal(world, contributor)
    ok(_submit(contributor, change_set), 201)
    path = f"/change-sets/{change_set['id']}/submission"

    edit = _edit(world, other, change_set, "Not theirs", withdrawSubmission=True)
    assert refused(edit, 403, "FORBIDDEN")["details"]["reason"] == "notSubmitter"
    assert refused(other.api.delete(path), 403, "FORBIDDEN")["details"]["reason"] == "notSubmitter"
    assert [item["state"] for item in _requests(contributor)] == ["submitted"]

    assert approver.api.delete(path).status_code == 204
    assert [item["state"] for item in _requests(contributor)] == ["withdrawn"]

    again = _proposal(world, contributor, "Again")
    ok(_submit(contributor, again), 201)
    ok(_edit(world, contributor, again, "Own edit", withdrawSubmission=True), 201)
    assert [item["state"] for item in _requests(contributor)].count("withdrawn") == 2
