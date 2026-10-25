"""J44 — one person's or client's changes across workspaces (USER_JOURNEYS.md § Security, 0.12 Z6).

`GET /changes` reads the data and model changes the caller may see, newest first (D340): each entry
names its workspace, its change set, what it changed as it is named now (from that workspace's own
model) and who made it (D343). Entries are filtered as every list is (D342): Browse in an entry's
workspace, Model authoring at the instance for model administration, Browse at the instance for an
entry whose workspace is gone. Every case runs on two configurations; the second workspace of a case
runs the other configuration's model.
"""

from dataclasses import replace

import pytest
from scenario import W1, ok, refused
from test_j11_bulk_change import _batch
from test_j17_review import _claim
from test_j36_workspace_models import _beside
from test_j40_authorization import _client
from test_j44_who_changed_what import AT_INSTANCE, IN_W1, _actor, _signed_in

STRUCTURES = ("R", "K", "B1n")


def _changes(world, **params) -> list[dict]:
    return ok(world.api.get("/changes", pageSize=500, **params))["items"]


def _label(world, workspace: str) -> str:
    return ok(world.api.get(f"/workspaces/{workspace}"))["label"]


def _type_name(world, workspace: str, structure: str) -> str:
    model = ok(world.api.get("/model", workspaceKey=workspace))
    key = world.key(structure)
    return next(item["name"] for item in model["objectTypes"] if item["key"] == key)


def _in(workspace: str) -> dict:
    return {"workspaceKey": workspace}


@pytest.mark.journey("J44.7")
@pytest.mark.structures(*STRUCTURES)
def test_one_persons_changes_across_workspaces(world):
    """Given P (Data steward in A and B, B on another model) changes a record live in A, creates a
    change set in B, adds two records and a relationship in it and publishes it, and Q changes a
    record in A. When the harness reads `/changes?actorId=P`, then it lists, newest first, the
    publication and the entries it applied (B, cause the publication), the relationship and the
    records added in the change set (B, with its change set), the change set's creation (B) and the
    live change (A), each with its workspace's label, the record's type and name from its own model
    and actor P; nothing of Q's."""
    other, _, b = _beside(world)
    person, as_person = _signed_in(world, "pavla", ("steward", IN_W1), ("steward", _in(b)))
    _, as_other = _client(world, "Another steward", ("steward", IN_W1))
    live = world.made("R", "Changed live in A")
    ok(as_person.update("R", live["id"], live["version"], name="Renamed by Pavla"))

    there = replace(as_person, configuration=other.configuration, ids={})
    change_set = there.change_set(b, name="Spring work")
    record = there.made("R", "Added in B", change_set=there.current(change_set))
    token = there.made("K", "Token in B", change_set=there.current(change_set))
    ok(there.relate("B1n", record["id"], token["id"], **_claim(there, change_set)), 201)
    published = there.publish(change_set, b)
    theirs = world.made("R", "Changed by someone else")
    ok(as_other.update("R", theirs["id"], theirs["version"], name="Not Pavla's"))

    items = _changes(world, actorId=person["id"])
    assert all(item["actor"] == _actor(person) for item in items)
    times = [item["occurredAt"] for item in items]
    assert times == sorted(times, reverse=True)
    assert theirs["id"] not in {item["subject"]["id"] for item in items}
    a_label, b_label = _label(world, W1), _label(world, b)

    first = items[0]
    assert (first["kind"], first["action"]) == ("publication", "published")
    assert first["subject"]["id"] == published["id"] and first["workspace"]["key"] == b
    applied = [item for item in items if (item["cause"] or {}).get("kind") == "publication"]
    assert {item["kind"] for item in applied} == {"record", "relationship"} and len(applied) == 3
    assert all(
        item["cause"]["id"] == published["id"] and item["changeSet"] is None for item in applied
    )

    staged = [item for item in items if (item["changeSet"] or {}).get("id") == change_set["id"]]
    assert all(item["workspace"] == {"key": b, "label": b_label} for item in staged)
    assert all(item["changeSet"]["name"] == "Spring work" for item in staged)
    added = {item["subject"]["name"]: item for item in staged if item["kind"] == "record"}
    assert set(added) == {"Added in B", "Token in B"}
    assert added["Added in B"]["subject"]["objectTypeName"] == _type_name(other, b, "R")
    assert added["Added in B"]["subject"]["objectTypeKey"] == other.key("R")
    (link,) = [item for item in staged if item["kind"] == "relationship"]
    assert link["subject"]["relationTypeKey"] == other.key("B1n")
    assert link["subject"]["fromObject"] == {"id": record["id"], "name": "Added in B"}
    assert link["subject"]["toObject"] == {"id": token["id"], "name": "Token in B"}
    created = next(i for i in staged if (i["kind"], i["action"]) == ("change-set", "created"))
    assert created["subject"] == {"id": change_set["id"], "name": "Spring work"}

    last = items[-1]
    assert (last["kind"], last["action"], last["subject"]["id"]) == (
        "record",
        "updated",
        live["id"],
    )
    assert last["workspace"] == {"key": W1, "label": a_label} and last["changeSet"] is None
    assert last["subject"]["name"] == "Renamed by Pavla"
    assert last["subject"]["objectTypeName"] == _type_name(world, W1, "R")
    assert "name" in last["changedFields"] and last["cause"] == {"kind": "user"}


@pytest.mark.journey("J44.8")
@pytest.mark.structures(*STRUCTURES)
def test_only_what_the_caller_may_see(world):
    """Given P changed a record in A and one in B and changed a model draft; R holds Browse in A
    only, S is a Security administrator with no data role and M holds Model authoring at the
    instance only. When each reads `/changes?actorId=P`, then R sees only A's entries, S an empty
    list, M only the draft's entries; the harness sees all of them."""
    other, _, b = _beside(world)
    person, as_person = _signed_in(
        world, "pert", ("steward", IN_W1), ("steward", _in(b)), ("model-admin", AT_INSTANCE)
    )
    here = world.made("R", "Here")
    ok(as_person.update("R", here["id"], here["version"], name="Here, changed"))
    there = other.made("R", "There", workspace=b)
    elsewhere = replace(as_person, configuration=other.configuration, ids={})
    ok(elsewhere.update("R", there["id"], there["version"], name="There, changed"))
    active = world.workspace_model()["releaseId"]
    release = ok(world.api.get(f"/model-releases/{active}", includeModel=True))
    body = {"name": "Pert's draft", "model": release["model"], "baseReleaseId": release["id"]}
    draft = ok(as_person.api.post("/model-drafts", body), 201)

    _, reader = _client(world, "Reads A", ("reader", IN_W1))
    _, security = _client(world, "Security only", ("security-admin", AT_INSTANCE))
    _, modeller = _client(world, "Models only", ("model-admin", AT_INSTANCE))

    everything = _changes(world, actorId=person["id"])
    assert {item["subject"]["id"] for item in everything} >= {here["id"], there["id"], draft["id"]}
    seen = _changes(reader, actorId=person["id"])
    assert seen and all(item["workspace"]["key"] == W1 for item in seen)
    assert here["id"] in {item["subject"]["id"] for item in seen}
    assert _changes(security, actorId=person["id"]) == []
    models = _changes(modeller, actorId=person["id"])
    assert models and all(item["kind"] == "model" and item["workspace"] is None for item in models)
    assert models[0]["subject"] == {"id": draft["id"], "name": "Pert's draft"}


@pytest.mark.journey("J44.9")
@pytest.mark.structures(*STRUCTURES)
def test_filters_and_pages(world):
    """Given P's changes in A (two live changes, a change set with a record) and in B. Then
    `workspaceKey`, `kind` and a `since`/`until` range each keep only theirs; pages of two continue
    without repeats or gaps; an unknown `kind` is refused with `422 REQUEST_VALIDATION_ERROR`."""
    other, _, b = _beside(world)
    person, as_person = _signed_in(world, "fia", ("steward", IN_W1), ("steward", _in(b)))
    one, two = world.made("R", "One"), world.made("R", "Two")
    ok(as_person.update("R", one["id"], one["version"], name="One, changed"))
    middle = _changes(world, actorId=person["id"])[0]["occurredAt"]
    ok(as_person.update("R", two["id"], two["version"], name="Two, changed"))
    change_set = as_person.change_set(name="Filtered")
    as_person.made("R", "Staged", change_set=as_person.current(change_set))
    there = other.made("R", "Elsewhere", workspace=b)
    elsewhere = replace(as_person, configuration=other.configuration, ids={})
    ok(elsewhere.update("R", there["id"], there["version"], name="Elsewhere, changed"))

    everything = _changes(world, actorId=person["id"])
    assert {item["workspace"]["key"] for item in _changes(world, actorId=person["id"],
                                                         workspaceKey=b)} == {b}  # fmt: skip
    records = _changes(world, actorId=person["id"], kind="record")
    assert records and all(item["kind"] == "record" for item in records)
    assert any(item["kind"] == "change-set" for item in everything)
    both = _changes(world, actorId=person["id"], kind=["record", "change-set"])
    assert {item["kind"] for item in both} == {"record", "change-set"}
    since = _changes(world, actorId=person["id"], since=middle)
    assert one["id"] in {item["subject"]["id"] for item in since}
    assert since == [item for item in everything if item["occurredAt"] >= middle]
    before = _changes(world, actorId=person["id"], until=middle)
    assert before == [item for item in everything if item["occurredAt"] < middle]

    walked, cursor = [], None
    while True:
        params = {"actorId": person["id"], "pageSize": 2, **({"cursor": cursor} if cursor else {})}
        page = ok(world.api.get("/changes", **params))
        walked += page["items"]
        cursor = page.get("nextCursor")
        if not cursor:
            break
    assert [item["id"] for item in walked] == [item["id"] for item in everything]

    refused(world.api.get("/changes", kind="nothing"), 422, "REQUEST_VALIDATION_ERROR")


@pytest.mark.journey("J44.10")
@pytest.mark.structures(*STRUCTURES)
def test_a_clients_changes(world):
    """Given client C (Data steward in A) submits a batch changing two records. When C reads
    `/changes?actorId=<C>`, then both entries name C with the job as cause."""
    client, as_client = _client(world, "Catalogue sync", ("steward", IN_W1))
    one, two = world.made("R", "Synced one"), world.made("R", "Synced two")
    items = [
        {"op": "update", "target": {"id": item["id"]}, "expectedVersion": item["version"],
         "name": f"{item['name']}, synced"}
        for item in (one, two)
    ]  # fmt: skip
    job = ok(_batch(as_client, items, run="background"), 202)
    world.api.client.app.state.job_worker.run_until_idle()

    mine = _changes(as_client, actorId=client["id"])
    changed = [item for item in mine if item["subject"]["id"] in {one["id"], two["id"]}]
    assert len(changed) == 2
    assert all(item["actor"] == _actor(client, "client") for item in changed)
    assert all(item["cause"] == {"kind": "job", "id": job["id"]} for item in changed)


@pytest.mark.journey("J44.11")
@pytest.mark.structures(*STRUCTURES)
def test_after_things_go(world):
    """Given P adds a record in workspace C and deletes it, and R holds Browse in C. Then P's
    entries read the record as removed; when C is deleted, the harness reads them with
    `workspace: null` and R no longer sees them."""
    key = "gone-site"
    ok(world.api.post("/workspaces", {"key": key, "label": "Gone site"}), 201)
    person, as_person = _signed_in(world, "gus", ("steward", _in(key)))
    _, reader = _client(world, "Reads C", ("reader", _in(key)))
    record = as_person.made("R", "Short-lived", workspace=key)
    deleted = as_person.api.delete(
        f"/objects/{world.key('R')}/{record['id']}", expectedVersion=record["version"]
    )
    assert deleted.status_code == 204

    items = _changes(world, actorId=person["id"])
    assert {item["action"] for item in items} >= {"created", "deleted"}
    assert all(item["subject"]["removed"] is True for item in items)
    assert all(item["workspace"]["key"] == key for item in items)
    assert len(_changes(reader, actorId=person["id"])) == len(items)

    version = ok(world.api.get(f"/workspaces/{key}"))["version"]
    assert world.api.delete(f"/workspaces/{key}", expectedVersion=version).status_code == 204
    after = _changes(world, actorId=person["id"])
    assert [item["id"] for item in after] == [item["id"] for item in items]
    assert all(item["workspace"] is None for item in after)
    assert _changes(reader, actorId=person["id"]) == []
