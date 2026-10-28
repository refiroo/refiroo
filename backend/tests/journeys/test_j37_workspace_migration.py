"""J37 — Move a workspace to another release (USER_JOURNEYS.md, Base 0.11 V1).

A migration previews every conversion, type change, loss and refusal of one workspace's data under
a target release, item by item, and changes nothing until it is confirmed (D68–D74). Each test runs
on one configuration ``X``: ``X1`` is ``X`` with a probe added (two optional text attributes on
``R``, a root type in ``R``'s application with a relationship to ``R``), activated into a workspace
of its own; ``X2`` is derived from ``X1`` in the test (D77), naming no configuration key. A second
workspace on ``Y``, the other generated configuration, stands beside it where the test needs one.
"""

import copy
from types import SimpleNamespace
from uuid import uuid4

import pytest
from scenario import ok, refused
from test_j36_workspace_models import BOTH, _beside, _model, _on


def _probe(world):
    r = world.key("R")
    return SimpleNamespace(
        count=f"{r}-probe-count",
        note=f"{r}-probe-note",
        label=f"{r}-probe-label",
        kind=f"{r}-probe",
        renamed=f"{r}-probe-renamed",
        cites=f"{r}-probe-cites",
    )


def _x1(world):
    """``X`` with the probe."""
    model = copy.deepcopy(world.configuration.model)
    k = _probe(world)
    model["attributeTypes"] += [
        {"key": k.count, "name": "Probe count"},
        {"key": k.note, "name": "Probe note"},
        {"key": k.label, "name": "Probe label"},
    ]
    r_type = next(t for t in model["objectTypes"] if t["key"] == world.key("R"))
    r_type["attributes"] += [
        {"attributeTypeKey": k.count, "order": 901},
        {"attributeTypeKey": k.note, "order": 902},
    ]
    model["objectTypes"].append(
        {
            "key": k.kind,
            "name": "Probe",
            "pluralName": "Probes",
            "displayAttributeTypeKey": k.label,
            "attributes": [{"attributeTypeKey": k.label, "order": 10}],
            "features": {"rootCreatable": True},
        }
    )
    application = next(a for a in model["applications"] if a["key"] == world.app("R"))
    application["objectTypeKeys"].append(k.kind)
    model["relationTypes"].append(
        {"key": k.cites, "reverseKey": f"{k.cites}--rev", "name": "cites", "reverseName": "cited by"}
    )
    model["objectTypeRelations"].append(
        {
            "relationTypeKey": k.cites,
            "fromObjectTypeKey": k.kind,
            "toObjectTypeKey": world.key("R"),
            "cardinality": "many-to-many",
        }
    )
    model["release"]["version"] = f"{model['release']['version']}-probe"
    return model


def _x2(world, *changes):
    """``X1`` with ``changes``: ``count-integer`` (the count attribute becomes an integer),
    ``drop-note`` (the note binding and attribute go), ``drop-probe`` (the probe type, its
    relationship and its label go), ``rename-probe`` (the probe type's key changes) and
    ``require-note`` (``R`` requires the note), ``move-probe`` (the probe type stands in another
    application), ``same`` (nothing but the version) and ``unique-note`` (the note is unique)."""
    model = _x1(world)
    k = _probe(world)
    r_type = next(t for t in model["objectTypes"] if t["key"] == world.key("R"))
    application = next(a for a in model["applications"] if a["key"] == world.app("R"))
    for change in changes:
        if change == "count-integer":
            next(a for a in model["attributeTypes"] if a["key"] == k.count)["valueType"] = "integer"
        elif change == "drop-note":
            r_type["attributes"] = [b for b in r_type["attributes"] if b["attributeTypeKey"] != k.note]
            model["attributeTypes"] = [a for a in model["attributeTypes"] if a["key"] != k.note]
        elif change == "drop-probe":
            model["objectTypes"] = [t for t in model["objectTypes"] if t["key"] != k.kind]
            application["objectTypeKeys"].remove(k.kind)
            model["relationTypes"] = [r for r in model["relationTypes"] if r["key"] != k.cites]
            model["objectTypeRelations"] = [
                p for p in model["objectTypeRelations"] if p["relationTypeKey"] != k.cites
            ]
            model["attributeTypes"] = [a for a in model["attributeTypes"] if a["key"] != k.label]
        elif change == "rename-probe":
            next(t for t in model["objectTypes"] if t["key"] == k.kind)["key"] = k.renamed
            application["objectTypeKeys"] = [
                k.renamed if key == k.kind else key for key in application["objectTypeKeys"]
            ]
            for pair in model["objectTypeRelations"]:
                if pair["fromObjectTypeKey"] == k.kind:
                    pair["fromObjectTypeKey"] = k.renamed
        elif change == "require-note":
            next(b for b in r_type["attributes"] if b["attributeTypeKey"] == k.note)["required"] = True
        elif change == "move-probe":
            # The editor's setContainment with an application: the probe type keeps its key and
            # stands in another application (0.11 R, R-F3).
            application["objectTypeKeys"].remove(k.kind)
            other = next(a for a in model["applications"] if a["key"] != world.app("R"))
            other["objectTypeKeys"].append(k.kind)
        elif change == "same":
            pass
        elif change == "unique-note":
            note = next(a for a in model["attributeTypes"] if a["key"] == k.note)
            note["features"] = {**(note.get("features") or {}), "unique": True}
    model["release"]["version"] = f"{model['release']['version']}-{'-'.join(changes)}"
    return model


def _probe_record(world, workspace, label):
    k = _probe(world)
    body = {
        "workspaceKey": workspace,
        "applicationKey": world.app("R"),
        "objectTypeKey": k.kind,
        "name": label,
        "attributes": [{"attributeTypeKey": k.label, "value": label}],
    }
    return ok(world.api.post("/objects", body), 201)


def _workspace(world):
    """A workspace on ``X1`` with R records holding counts and notes, and two probes, the first
    citing an R: its key, the records by name and the citation."""
    x1 = world.install(_x1(world), name="Probe")
    key = _on(world, x1["id"])
    k = _probe(world)
    made = {
        name: world.made("R", name, workspace=key, values=values)
        for name, values in (
            ("twelve", {k.count: "12", k.note: "kept note"}),
            ("forty", {k.count: "40"}),
            ("words", {k.count: "a dozen"}),
            ("empty", {}),
        )
    }
    made["first probe"] = _probe_record(world, key, "first probe")
    made["second probe"] = _probe_record(world, key, "second probe")
    citation = ok(
        world.api.post(
            "/relations",
            {
                "relationTypeKey": k.cites,
                "fromObjectId": made["first probe"]["id"],
                "toObjectId": made["twelve"]["id"],
                "attributes": {},
            },
        ),
        201,
    )
    return key, made, citation


def _start(world, workspace, target_id, **body):
    current = _model(world, workspace)
    request = {"targetReleaseId": target_id, "expectedVersion": current["version"], **body}
    return world.api.post(f"/workspaces/{workspace}/model/migrations", request)


def _run(world):
    world.api.client.app.state.job_worker.run_until_idle()


def _previewed(world, workspace, target_id, **body):
    job = ok(_start(world, workspace, target_id, **body), 202)
    _run(world)
    return ok(world.api.get(f"/jobs/{job['id']}"))


def _rows(world, job_id, **params):
    items, cursor = [], None
    while True:
        page = ok(world.api.get(f"/jobs/{job_id}/rows", pageSize=100, cursor=cursor, **params))
        items += page["items"]
        cursor = page.get("nextCursor")
        if not cursor:
            return items


def _confirm(world, job, **body):
    summary = job["migration"]
    request = {
        "expectedVersion": summary["expectedVersion"],
        "expectedFeedPosition": summary["feedPosition"],
        **body,
    }
    return world.api.post(f"/jobs/{job['id']}/confirm", request)


def _head(world, workspace):
    return ok(world.api.get(f"/workspaces/{workspace}/feed", after=0, pageSize=1))["headPosition"]


def _read(world, workspace, record):
    return ok(world.api.get(f"/objects/{record['objectTypeKey']}/{record['id']}", workspaceKey=workspace))


def _value(record, key):
    return next((a["value"] for a in record["attributes"] if a["attributeTypeKey"] == key), None)


def _state(world, workspace, made):
    """What a refused or cancelled migration must leave as it was: release, feed head, records."""
    records = {}
    for name, record in made.items():
        answer = world.api.get(
            f"/objects/{record['objectTypeKey']}/{record['id']}", workspaceKey=workspace
        )
        records[name] = answer.json() if answer.status_code == 200 else answer.status_code
    return _model(world, workspace), _head(world, workspace), records


@pytest.mark.journey("J37.1")
@pytest.mark.structures(*BOTH)
def test_a_preview_lists_every_item_and_changes_nothing(world):
    """Given a workspace on X1 and X2 that makes the count an integer, drops the note and drops the
    probe type. When a migration to X2 is started, then the job waits for confirmation; its summary
    counts two conversions, five losses and no refusal; its rows name each item with its record,
    attribute or relationship, value before and after, and code; the workspace's release, feed and
    records are unchanged."""
    key, made, citation = _workspace(world)
    k = _probe(world)
    x2 = world.install(_x2(world, "count-integer", "drop-note", "drop-probe"), name="Probe")
    before = _state(world, key, made)

    job = _previewed(world, key, x2["id"])

    assert job["kind"] == "migration" and job["state"] == "awaiting_confirmation"
    summary = job["migration"]
    assert summary["targetReleaseId"] == x2["id"]
    assert summary["counts"] == {"conversion": 2, "reclassified": 0, "loss": 5, "refused": 0}
    assert summary["feedPosition"] == before[1]
    assert summary["expectedVersion"] == before[0]["version"]

    conversions = {
        (row["objectId"], row["attributeTypeKey"]): (row["before"], row["after"], row["code"])
        for row in _rows(world, job["id"], status="conversion")
    }
    assert conversions == {
        (made["twelve"]["id"], k.count): ("12", 12, "VALUE_CONVERTED"),
        (made["forty"]["id"], k.count): ("40", 40, "VALUE_CONVERTED"),
    }
    losses = {
        (row["objectId"], row.get("attributeTypeKey"), row.get("relationId"), row["code"])
        for row in _rows(world, job["id"], status="loss")
    }
    assert losses == {
        (made["words"]["id"], k.count, None, "VALUE_NOT_CONVERTIBLE"),
        (made["twelve"]["id"], k.note, None, "ATTRIBUTE_BINDING_IN_USE"),
        (made["first probe"]["id"], None, None, "OBJECT_TYPE_IN_USE"),
        (made["second probe"]["id"], None, None, "OBJECT_TYPE_IN_USE"),
        (made["first probe"]["id"], None, citation["id"], "RELATION_PAIR_IN_USE"),
    }
    assert _rows(world, job["id"], status="refused") == []
    assert _state(world, key, made) == before


@pytest.mark.journey("J37.2")
@pytest.mark.structures(*BOTH)
def test_confirm_accepting_the_loss(world):
    """Given that preview and a workspace on Y beside it. When it is confirmed without acceptLoss,
    then 422 MIGRATION_LOSS_NOT_ACCEPTED and it still waits. With acceptLoss, the workspace runs X2;
    converted counts read as integers; the note, the unconvertible count, the probes and the
    citation are gone; the feed has an entry for each changed record and relationship, caused by
    the job; the converted record's history names the attributes the migration changed. Y's
    workspace keeps its release, records and feed."""
    other, _y, beside = _beside(world)
    theirs = other.made("R", "Theirs", workspace=beside)
    beside_before = (_model(world, beside), _head(world, beside))
    key, made, citation = _workspace(world)
    k = _probe(world)
    x2 = world.install(_x2(world, "count-integer", "drop-note", "drop-probe"), name="Probe")
    job = _previewed(world, key, x2["id"])
    head = job["migration"]["feedPosition"]

    refused(_confirm(world, job), 422, "MIGRATION_LOSS_NOT_ACCEPTED")
    assert ok(world.api.get(f"/jobs/{job['id']}"))["state"] == "awaiting_confirmation"

    ok(_confirm(world, job, acceptLoss=True), 202)
    _run(world)
    done = ok(world.api.get(f"/jobs/{job['id']}"))
    assert done["state"] == "completed", done
    assert done["migration"]["counts"] == job["migration"]["counts"]

    assert _model(world, key)["releaseId"] == x2["id"]
    twelve = _read(world, key, made["twelve"])
    assert _value(twelve, k.count) == 12 and _value(twelve, k.note) is None
    assert _value(_read(world, key, made["forty"]), k.count) == 40
    assert _value(_read(world, key, made["words"]), k.count) is None
    for name in ("first probe", "second probe"):
        gone = world.api.get(f"/objects/{k.kind}/{made[name]['id']}", workspaceKey=key)
        assert gone.status_code == 404

    entries = ok(world.api.get(f"/workspaces/{key}/feed", after=head, pageSize=100))["items"]
    changed = {(entry["kind"], entry["action"], entry["id"]) for entry in entries}
    assert changed == {
        ("object", "updated", made["twelve"]["id"]),
        ("object", "updated", made["forty"]["id"]),
        ("object", "updated", made["words"]["id"]),
        ("object", "deleted", made["first probe"]["id"]),
        ("object", "deleted", made["second probe"]["id"]),
        ("relation", "deleted", citation["id"]),
    }
    assert {entry["cause"]["kind"] for entry in entries} == {"job"}
    assert {entry["modelReleaseId"] for entry in entries} == {x2["id"]}
    history = ok(
        world.api.get(f"/objects/{world.key('R')}/{made['twelve']['id']}/history", pageSize=5)
    )["items"]
    own = next(entry for entry in history if entry["aggregateType"] == "object")
    assert own["action"] == "updated"
    assert set(own["attributeTypeKeys"]) == {k.count, k.note}
    assert own["cause"]["id"] == job["id"]

    assert (_model(world, beside), _head(world, beside)) == beside_before
    assert other.record("R", theirs["id"], workspaceKey=beside)["name"] == "Theirs"


@pytest.mark.journey("J37.2")
@pytest.mark.structures(*BOTH)
def test_a_renamed_type_is_carried_by_a_type_mapping(world):
    """Given X2 renames the probe type. When previewed without a mapping, then its records and the
    citation are losses. When previewed with typeMappings naming the new key, then they are type
    changes and nothing is lost; after confirming, the probes keep their IDs, names and labels under
    the new type and the citation still joins the first probe to its R."""
    key, made, citation = _workspace(world)
    k = _probe(world)
    x2 = world.install(_x2(world, "rename-probe"), name="Probe")

    unmapped = _previewed(world, key, x2["id"])
    assert unmapped["migration"]["counts"]["loss"] == 3
    assert unmapped["migration"]["counts"]["reclassified"] == 0
    ok(world.api.post(f"/jobs/{unmapped['id']}/cancel"), 202)

    mapping = [{"fromObjectTypeKey": k.kind, "toObjectTypeKey": k.renamed}]
    mapped = _previewed(world, key, x2["id"], typeMappings=mapping)
    assert mapped["migration"]["counts"] == {
        "conversion": 0,
        "reclassified": 2,
        "loss": 0,
        "refused": 0,
    }
    rows = _rows(world, mapped["id"], status="reclassified")
    assert {(row["objectId"], row["objectTypeKey"], row["targetObjectTypeKey"]) for row in rows} == {
        (made["first probe"]["id"], k.kind, k.renamed),
        (made["second probe"]["id"], k.kind, k.renamed),
    }

    ok(_confirm(world, mapped), 202)
    _run(world)
    assert ok(world.api.get(f"/jobs/{mapped['id']}"))["state"] == "completed"
    probe = ok(world.api.get(f"/objects/{k.renamed}/{made['first probe']['id']}", workspaceKey=key))
    assert probe["name"] == "first probe" and _value(probe, k.label) == "first probe"
    relation = ok(world.api.get(f"/relations/{citation['id']}", workspaceKey=key))
    assert (relation["fromObjectId"], relation["toObjectId"]) == (
        made["first probe"]["id"],
        made["twelve"]["id"],
    )


@pytest.mark.journey("J37.2")
@pytest.mark.structures(*BOTH)
def test_named_attribute_sources_trade_values(world):
    """Given a release that changes nothing but its version (0.11 R, R-F1, R-F2). When the
    migration maps R onto itself with the count taking the note's values and the note the count's,
    then the preview lists each carried value with its target and loses nothing; after confirming,
    the record that held both now holds them the other way round."""
    key, made, _citation = _workspace(world)
    k = _probe(world)
    same = world.install(_x2(world, "same"), name="Probe")
    mapping = [
        {
            "fromObjectTypeKey": world.key("R"),
            "toObjectTypeKey": world.key("R"),
            "attributes": [
                {"attributeTypeKey": k.count, "from": k.note},
                {"attributeTypeKey": k.note, "from": k.count},
            ],
        }
    ]
    job = _previewed(world, key, same["id"], typeMappings=mapping)
    assert job["state"] == "awaiting_confirmation"
    assert job["migration"]["counts"]["loss"] == 0
    carried = {
        (row["objectId"], row["attributeTypeKey"]): row.get("targetAttributeTypeKey")
        for row in _rows(world, job["id"], status="conversion")
    }
    assert carried[(made["twelve"]["id"], k.count)] == k.note
    assert carried[(made["twelve"]["id"], k.note)] == k.count

    ok(_confirm(world, job), 202)
    _run(world)
    assert ok(world.api.get(f"/jobs/{job['id']}"))["state"] == "completed"
    twelve = _read(world, key, made["twelve"])
    assert (_value(twelve, k.count), _value(twelve, k.note)) == ("kept note", "12")


@pytest.mark.journey("J37.2")
@pytest.mark.structures(*BOTH)
def test_a_type_moved_to_another_application_keeps_its_records(world):
    """Given a release in which the probe type keeps its key but stands in another application, as
    the editor's move does (0.11 R, R-F3). When previewed without a mapping, then both probes change
    application and nothing is lost; after confirming, each probe reads in that application."""
    key, made, _citation = _workspace(world)
    k = _probe(world)
    moved = world.install(_x2(world, "move-probe"), name="Probe")

    job = _previewed(world, key, moved["id"])
    assert job["migration"]["counts"]["loss"] == 0
    rows = _rows(world, job["id"], status="reclassified")
    assert {row["objectId"] for row in rows} == {
        made["first probe"]["id"],
        made["second probe"]["id"],
    }
    target_application = rows[0]["targetApplicationKey"]
    assert target_application != world.app("R")

    ok(_confirm(world, job), 202)
    _run(world)
    assert ok(world.api.get(f"/jobs/{job['id']}"))["state"] == "completed"
    probe = _read(world, key, made["first probe"])
    assert probe["applicationKey"] == target_application and probe["objectTypeKey"] == k.kind


@pytest.mark.journey("J37.4")
@pytest.mark.structures(*BOTH)
def test_a_workspace_retired_after_the_preview_is_not_migrated(world):
    """Given a migration previewed and confirmed (0.11 R, R-F5). When the workspace is retired
    before the migration runs, then the job fails with WORKSPACE_RETIRED and the workspace keeps
    its release, its feed and its records; a preview of another migration, confirmed after the
    retirement in another workspace, is refused the same way."""
    x2 = world.install(_x2(world, "drop-note"), name="Probe")

    def retire(key):
        workspace = ok(world.api.get(f"/workspaces/{key}"))
        body = {"expectedVersion": workspace["version"], "status": "retired"}
        ok(world.api.patch(f"/workspaces/{key}", body))

    key, made, _citation = _workspace(world)
    job = _previewed(world, key, x2["id"])
    ok(_confirm(world, job, acceptLoss=True), 202)
    before = _state(world, key, made)
    retire(key)
    _run(world)
    failed = ok(world.api.get(f"/jobs/{job['id']}"))
    assert failed["state"] == "failed" and failed["error"]["code"] == "WORKSPACE_RETIRED", failed
    assert _state(world, key, made) == before

    other_key = _on(world, job["migration"]["currentReleaseId"])
    waiting = _previewed(world, other_key, x2["id"])
    retire(other_key)
    refused(_confirm(world, waiting, acceptLoss=True), 409, "WORKSPACE_RETIRED")


@pytest.mark.journey("J37.2")
@pytest.mark.structures(*BOTH)
def test_writes_elsewhere_go_on_while_a_migration_runs(world, monkeypatch):
    """Given a migration to a release that makes the note unique, so the unique values follow the
    switch (0.11 R, R-F6). When a record with a unique value is written in another workspace while
    the migration runs its last check, then that write commits at once, and the migration then
    completes."""
    from concurrent.futures import ThreadPoolExecutor

    from app.engine.model import migrations

    key, _made, _citation = _workspace(world)
    other, _y, other_key = _beside(world)
    x2 = world.install(_x2(world, "unique-note"), name="Probe")
    job = _previewed(world, key, x2["id"])
    ok(_confirm(world, job), 202)

    checking = migrations._Migration.refusals
    written = []

    def refusals(self, *, listing):
        if not listing and not written:
            pool = ThreadPoolExecutor(1)
            meanwhile = pool.submit(
                other.made, "R", "Meanwhile", workspace=other_key, values={"R.u": f"M-{uuid4().hex[:8]}"}
            )
            try:
                # Waiting on the migration's locks, it times out and fails the test, not hangs it.
                written.append(meanwhile.result(timeout=20))
            finally:
                pool.shutdown(wait=False)
        return checking(self, listing=listing)

    monkeypatch.setattr(migrations._Migration, "refusals", refusals)
    _run(world)
    assert written and written[0]["name"] == "Meanwhile"
    assert ok(world.api.get(f"/jobs/{job['id']}"))["state"] == "completed"


@pytest.mark.journey("J37.3")
@pytest.mark.structures(*BOTH)
def test_cancel_a_waiting_preview(world):
    """Given a waiting preview. When it is cancelled, then nothing changed, and confirming it
    afterwards is 409 JOB_NOT_AWAITING_CONFIRMATION."""
    key, made, _citation = _workspace(world)
    x2 = world.install(_x2(world, "count-integer"), name="Probe")
    before = _state(world, key, made)
    job = _previewed(world, key, x2["id"])

    cancelled = ok(world.api.post(f"/jobs/{job['id']}/cancel"), 202)
    assert cancelled["state"] == "cancelled"
    refused(_confirm(world, job, acceptLoss=True), 409, "JOB_NOT_AWAITING_CONFIRMATION")
    assert _state(world, key, made) == before


@pytest.mark.journey("J37.4")
@pytest.mark.structures(*BOTH)
def test_a_stale_review_is_refused(world):
    """Given a waiting preview and a workspace on Y beside it. When a record is changed in Y's
    workspace, the confirmation is not stale. When a record is then saved in the migrated workspace,
    or another release is activated into it, then confirming is 409 MIGRATION_REVIEW_STALE and
    nothing changed."""
    other, _y, beside = _beside(world)
    key, made, _citation = _workspace(world)
    x2 = world.install(_x2(world, "count-integer"), name="Probe")
    job = _previewed(world, key, x2["id"])

    other.made("R", "Elsewhere", workspace=beside)
    world.made("R", "Afterwards", workspace=key)
    before = _state(world, key, made)
    error = refused(_confirm(world, job, acceptLoss=True), 409, "MIGRATION_REVIEW_STALE")
    assert error["details"]["currentFeedPosition"] == before[1]
    assert _state(world, key, made) == before

    again = _previewed(world, key, x2["id"])
    compatible = _x1(world)
    compatible["release"]["version"] += "-again"
    ok(world.activate(world.install(compatible, name="Probe")["id"], key))
    refused(_confirm(world, again, acceptLoss=True), 409, "MIGRATION_REVIEW_STALE")
    assert _model(world, key)["releaseId"] != x2["id"]


@pytest.mark.journey("J37")
@pytest.mark.structures(*BOTH)
def test_refusals_block_the_migration_until_the_data_is_fixed(world):
    """Given X2 makes R require the note, which three R records lack. When previewed, then the rows
    refuse those records with REQUIRED_ATTRIBUTE_MISSING and confirming is 409
    MIGRATION_HAS_REFUSALS. When their notes are filled and it is previewed again, it confirms."""
    key, made, _citation = _workspace(world)
    k = _probe(world)
    x2 = world.install(_x2(world, "require-note"), name="Probe")

    job = _previewed(world, key, x2["id"])
    assert job["migration"]["counts"]["refused"] == 3
    refusals = {
        (row["objectId"], row["code"]) for row in _rows(world, job["id"], status="refused")
    }
    assert refusals == {
        (made[name]["id"], "REQUIRED_ATTRIBUTE_MISSING") for name in ("forty", "words", "empty")
    }
    refused(_confirm(world, job, acceptLoss=True), 409, "MIGRATION_HAS_REFUSALS")

    for name in ("forty", "words", "empty"):
        current = _read(world, key, made[name])
        ok(world.update("R", made[name]["id"], current["version"], values={k.note: "filled"}))
    fixed = _previewed(world, key, x2["id"])
    assert fixed["migration"]["counts"]["refused"] == 0
    ok(_confirm(world, fixed), 202)
    _run(world)
    assert _model(world, key)["releaseId"] == x2["id"]


@pytest.mark.journey("J37.5")
@pytest.mark.structures(*BOTH)
def test_a_failed_execution_changes_nothing(world, monkeypatch):
    """Given a confirmed migration whose execution fails at its last step, the switch of the
    workspace's release. No client can make a confirmed migration fail, so the failure is injected
    at that boundary. Then the job is failed with an error saying nothing changed and what to do,
    and the workspace's release, feed and records are as before."""
    key, made, _citation = _workspace(world)
    x2 = world.install(_x2(world, "count-integer", "drop-probe"), name="Probe")
    job = _previewed(world, key, x2["id"])
    before = _state(world, key, made)

    def failing(*args, **kwargs):
        raise RuntimeError(f"injected failure {uuid4().hex[:6]}")

    from app.engine.model import migrations

    monkeypatch.setattr(migrations, "switch_assignment", failing)
    ok(_confirm(world, job, acceptLoss=True), 202)
    _run(world)

    failed = ok(world.api.get(f"/jobs/{job['id']}"))
    assert failed["state"] == "failed"
    assert failed["error"]["code"] == "MIGRATION_FAILED"
    assert "nothing" in failed["error"]["message"].lower()
    assert failed["error"]["details"]["correlationId"]
    assert _state(world, key, made) == before


@pytest.mark.journey("J37.4")
@pytest.mark.structures(*BOTH)
def test_a_migration_whose_requester_lost_model_release_is_not_confirmed(world):
    """Given a previewed migration requested by a client holding Model release in the workspace.
    When the grant is removed and an administrator confirms the job, then it answers `403
    FORBIDDEN` naming the requester and the job keeps waiting (0.12 R-F8)."""
    from test_j40_authorization import _client

    key, _made, _citation = _workspace(world)
    x2 = world.install(_x2(world, "same"), name="Probe")
    client, requester = _client(world, "Requester", ("model-admin", {"workspaceKey": key}))
    current = _model(world, key)
    job = ok(
        requester.api.post(
            f"/workspaces/{key}/model/migrations",
            {"targetReleaseId": x2["id"], "expectedVersion": current["version"]},
        ),
        202,
    )
    _run(world)
    job = ok(world.api.get(f"/jobs/{job['id']}"))
    assert job["state"] == "awaiting_confirmation"
    [grant] = ok(world.api.get("/grants", principalId=client["id"]))["items"]
    assert world.api.delete(f"/grants/{grant['id']}").status_code == 204

    error = refused(_confirm(world, job), 403, "FORBIDDEN")
    assert error["details"]["requestedBy"]["id"] == client["id"]
    assert ok(world.api.get(f"/jobs/{job['id']}"))["state"] == "awaiting_confirmation"
