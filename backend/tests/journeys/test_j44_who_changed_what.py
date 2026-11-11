"""J44 — see who changed what (USER_JOURNEYS.md § Security, 0.12 Z4).

Every audit entry names its actor beside its cause (D313): the person or client whose request made
it, a job's requester for the job's changes, a publication's publisher for what it applied. Names
are resolved when read, so a renamed or deactivated person reads as they are now (D237). A change
set names its creator, a publication its publisher and withdrawer, a job its requester and an
editor operation its author (D315). Consumer events carry no actor (D239, D314). People and
clients are made and granted through the API by the harness as Security administrator; every case
runs on two configurations.
"""

import copy

import pytest
from scenario import W1, W2, World, consumer_events, derive_events, ok, refused
from sqlalchemy import create_engine, text
from test_j05_j06_publish import _update_in
from test_j11_bulk_change import _batch
from test_j30_consumer_events import _activate
from test_j38_1_model_mapping import _create as _create_mapping
from test_j38_1_model_mapping import _operate
from test_j39_sign_in import (
    _browser,
    _person,
    _pkce,
    _post_form,
    _reset_link,
    _set_password,
    _sign_in,
)
from test_j40_authorization import _as, _client, _grant

LEDGER = ("Capi", "R", "R2", "D", "K", "G", "B11", "Bown", "R.n")


def _signed_in(world, username: str, *grants: tuple[str, dict]) -> tuple[dict, World]:
    """A person holding ``grants`` (role, scope), signed in, and the world as they see it."""
    person = _person(world, username)
    for role, scope in grants:
        _grant(world, "user", person["id"], role, **scope)
    return person, _as(world, _sign_in(_browser(world), username))


def _actor(principal: dict, kind: str = "user") -> dict:
    return {"kind": kind, "id": principal["id"], "name": principal["name"]}


def _history(world, structure: str, object_id: str, **params) -> list[dict]:
    page = world.api.get(f"/objects/{world.key(structure)}/{object_id}/history", **params)
    return ok(page)["items"]


def _feed(world, workspace: str = W1, after: int = 0) -> list[dict]:
    return ok(world.api.get(f"/workspaces/{workspace}/feed", after=after))["items"]


def _head(world, workspace: str = W1) -> int:
    return ok(world.api.get(f"/workspaces/{workspace}/feed", after=0, pageSize=1))["headPosition"]


IN_W1 = {"workspaceKey": W1}
AT_INSTANCE = {"instance": True}


@pytest.mark.journey("J44.1")
@pytest.mark.structures(*LEDGER)
def test_a_single_write_names_its_caller(world):
    """Given person P and client C, both Editors in A. When P changes a record live and C changes it
    next, then its history lists C then P (`actor` kind, id and name, no `cause`), the feed's two
    entries name the same actors with `cause.kind: "user"`, and the consumer events derived from
    them carry no actor."""
    _activate(world, "who")
    record = world.made("R", "Changed by two")
    person, as_person = _signed_in(world, "petra", ("steward", IN_W1))
    client, as_client = _client(world, "Catalogue sync", ("steward", IN_W1))
    head = _head(world)

    first = ok(as_person.update("R", record["id"], record["version"], name="Renamed by Petra"))
    ok(as_client.update("R", record["id"], first["version"], name="Renamed by the sync"))

    latest, previous = _history(world, "R", record["id"])[:2]
    assert latest["actor"] == _actor(client, "client") and "cause" not in latest
    assert previous["actor"] == _actor(person) and "cause" not in previous
    entries = _feed(world, after=head)
    assert [(entry["actor"], entry["cause"]) for entry in entries] == [
        (_actor(person), {"kind": "user"}),
        (_actor(client, "client"), {"kind": "user"}),
    ]
    derive_events(world)
    events = ok(consumer_events(world))["items"]
    assert events and all("actor" not in event for event in events)


@pytest.mark.journey("J44.2")
def test_a_job_names_its_requester(world):
    """Given P submits a batch that changes two records. When it runs, then their history entries
    carry `cause` the job and `actor` P, and the job reads `requestedBy` P."""
    one, two = world.made("R", "Batched one"), world.made("R", "Batched two")
    person, as_person = _signed_in(world, "bruno", ("steward", IN_W1))
    items = [
        {"op": "update", "target": {"id": item["id"]}, "expectedVersion": item["version"],
         "name": f"{item['name']} again"}
        for item in (one, two)
    ]  # fmt: skip
    job = ok(_batch(as_person, items, run="background"), 202)
    world.api.client.app.state.job_worker.run_until_idle()

    assert ok(world.api.get(f"/jobs/{job['id']}"))["requestedBy"] == _actor(person)
    for item in (one, two):
        latest = _history(world, "R", item["id"])[0]
        assert latest["cause"]["kind"] == "job" and latest["cause"]["id"] == job["id"]
        assert latest["actor"] == _actor(person)


@pytest.mark.journey("J44.3")
def test_a_change_set_names_who_created_changed_and_published_it(world):
    """Given P creates a change set in A, Q (Contributor) changes a record in it and R (Editor)
    publishes it. Then the change set reads `createdBy` P, the record's history in the change set
    names Q, the publication reads `publishedBy` R, and the live entries it applied name R with the
    publication as cause; when R withdraws it, `withdrawnBy` is R."""
    record = world.made("R", "Proposed rename")
    creator, as_creator = _signed_in(world, "pia", ("contributor", IN_W1))
    changer, as_changer = _signed_in(world, "quinn", ("contributor", IN_W1))
    publisher, as_publisher = _signed_in(world, "rosa", ("steward", IN_W1))

    change_set = as_creator.change_set()
    assert change_set["createdBy"] == _actor(creator)
    ok(_update_in(as_changer, change_set, "R", record["id"], name="Renamed in the change set"))
    in_change_set = _history(world, "R", record["id"], changeSetId=change_set["id"])[0]
    assert in_change_set["actor"] == _actor(changer)
    assert world.current(change_set)["createdBy"] == _actor(creator)
    listed = ok(world.api.get(f"/workspaces/{W1}/change-sets"))["items"]
    assert next(i for i in listed if i["id"] == change_set["id"])["createdBy"] == _actor(creator)

    published = as_publisher.publish(change_set)
    assert published["publishedBy"] == _actor(publisher) and published["withdrawnBy"] is None
    live = _history(world, "R", record["id"])[0]
    assert live["cause"]["kind"] == "publication" and live["cause"]["id"] == published["id"]
    assert live["actor"] == _actor(publisher)

    withdrawn = as_publisher.api.post(f"/publications/{published['id']}/withdrawal")
    assert withdrawn.status_code == 204
    read = ok(world.api.get(f"/publications/{published['id']}"))
    assert read["withdrawnBy"] == _actor(publisher)


@pytest.mark.journey("J44.4")
def test_the_model_editor_names_each_author(world):
    """Given P with Model authoring. When P applies an operation to a draft and to a model mapping,
    then each history's entry reads `author` P; an activation P makes reads `actor` P."""
    person, as_person = _signed_in(
        world,
        "mira",
        ("model-admin", AT_INSTANCE),
        ("owner", IN_W1),
        ("owner", {"workspaceKey": W2}),
    )
    active = world.workspace_model()["releaseId"]
    release = ok(world.api.get(f"/model-releases/{active}", includeModel=True))
    body = {"name": "Authored", "model": release["model"], "baseReleaseId": release["id"]}
    draft = ok(as_person.api.post("/model-drafts", body), 201)
    operation = {"kind": "addApplication", "name": "J44 Authored"}
    ok(
        as_person.api.post(
            f"/model-drafts/{draft['id']}/operations",
            {"expectedVersion": draft["version"], "operations": [operation]},
        )
    )
    (entry,) = ok(as_person.api.get(f"/model-drafts/{draft['id']}/operations"))["items"]
    assert entry["author"] == _actor(person)

    mapping = _create_mapping(as_person, W1, W2)
    ok(_operate(as_person, mapping["key"], {"kind": "setValueMap", "name": "blanks",
                                             "values": {"N/A": None}}))  # fmt: skip
    entries = ok(as_person.api.get(f"/model-mappings/{mapping['key']}/operations"))["items"]
    assert entries[-1]["author"] == _actor(person)

    model = copy.deepcopy(world.configuration.model)
    model["release"]["version"] += "-authored"
    candidate = world.install(model)
    ok(as_person.activate(candidate["id"]))
    (activation,) = ok(world.api.get(f"/model-releases/{candidate['id']}/activations"))["items"]
    assert activation["actor"] == _actor(person)


@pytest.mark.journey("J44.5")
def test_names_are_read_as_they_are_now(world):
    """Given P's change in A's history. When P is renamed and then deactivated, then the entry
    reads P's new name."""
    record = world.made("R", "Changed before a rename")
    person, as_person = _signed_in(world, "nora", ("steward", IN_W1))
    ok(as_person.update("R", record["id"], record["version"], name="Changed by Nora"))

    current = ok(world.api.get(f"/users/{person['id']}"))
    renamed = ok(
        world.api.patch(
            f"/users/{person['id']}", {"name": "Nora Field", "expectedVersion": current["version"]}
        )
    )
    ok(
        world.api.patch(
            f"/users/{person['id']}", {"active": False, "expectedVersion": renamed["version"]}
        )
    )

    latest = _history(world, "R", record["id"])[0]
    assert latest["actor"] == {"kind": "user", "id": person["id"], "name": "Nora Field"}


@pytest.mark.journey("J44.6")
def test_an_entry_from_before_sign_in_names_nobody(world):
    """An audit entry from an older release (written without an actor: this test clears it, as
    the migration leaves every entry from before Z4) reads `actor: null`."""
    record = world.made("R", "Changed before sign-in")
    engine = create_engine(world.database)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE audit_events SET actor_kind = NULL, actor_user_id = NULL, "
                    "actor_client_id = NULL WHERE sequence_id IN (SELECT audit_event_id FROM "
                    "audit_event_subjects WHERE object_id = :id)"
                ),
                {"id": record["id"]},
            )
    finally:
        engine.dispose()
    (created,) = _history(world, "R", record["id"])
    assert created["actor"] is None


def _security_events(world, **params) -> list[dict]:
    return ok(world.api.get("/security-events", **params))["items"]


@pytest.mark.journey("J40.11")
def test_security_changes_and_sign_ins_are_recorded(world):
    """Given S (Security administrator) creates person P, grants P a role in A and adds P to a
    group, and P signs in once with a wrong password and once rightly. Then
    `/security-events?principalId=P` lists, newest first, the sign-in (by P), the failed sign-in
    (address, no actor), the membership, the grant and the creation (by S), and no entry holds a
    password or link; a person without Security administration gets `403 FORBIDDEN`."""
    administrator, as_administrator = _signed_in(world, "sam", ("security-admin", AT_INSTANCE))
    person = ok(
        as_administrator.api.post("/users", {"email": "pat@example.org", "name": "Pat"}), 201
    )
    grant = {"principal": {"kind": "user", "id": person["id"]}, "role": "reader", "scope": IN_W1}
    granted = ok(as_administrator.api.post("/grants", grant), 201)
    group = ok(as_administrator.api.post("/groups", {"name": "J44 Stewards"}), 201)
    member = {"userId": person["id"]}
    ok(as_administrator.api.post(f"/groups/{group['id']}/members", member), 201)
    token = _reset_link(as_administrator, person)
    _set_password(_browser(world), token)
    browser = _browser(world)
    _post_form(browser, "pat", "not the password at all", _pkce()[1])
    _sign_in(browser, "pat")

    events = _security_events(world, principalId=person["id"])
    actions = [(event["aggregateType"], event["action"]) for event in events]
    assert actions[:2] == [("sign-in", "succeeded"), ("sign-in", "failed")]
    assert ("group", "member-added") in actions and ("grant", "created") in actions
    assert actions[-1] == ("user", "created")
    signed_in, failed = events[0], events[1]
    assert signed_in["actor"] == _actor(person)
    assert failed["actor"] is None and failed["details"]["address"]
    created = next(event for event in events if event["aggregateType"] == "grant")
    assert created["actor"] == _actor(administrator) and created["aggregateId"] == granted["id"]
    assert events[-1]["actor"] == _actor(administrator)
    times = [event["occurredAt"] for event in events]
    assert times == sorted(times, reverse=True)
    assert "not the password at all" not in str(events) and token not in str(events)

    _, reader = _signed_in(world, "rex", ("reader", IN_W1))
    refused(reader.api.get("/security-events", principalId=person["id"]), 403, "FORBIDDEN")
