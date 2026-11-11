"""J25.9, J28.15, J30.11 — An earlier contract version served beside the new one (0.13 DF3).

A definition may keep frozen copies of itself at older contract versions (``earlierVersions``, each
with the day it was superseded and an optional sunset day). The consumer tier answers every route and
OpenAPI document of a kept version from the current data through that version's definition, with the
``Deprecation`` and ``Sunset`` headers; a webhook accepted under it keeps receiving its shape;
removing it from the model ends it. The tests use the events-capable ``Capi`` of J30.
"""

import copy
from datetime import UTC, datetime

import pytest
from scenario import consumer_events, consumer_object, derive_events, dispatch, ok, refused
from test_j30_consumer_events import CHURN, EVERY, LEDGER, _activate, _permit, _rename, _workspace
from test_j30_delivery import _subscribe, receiver  # noqa: F401 - the receiver fixture
from test_j30_subscriptions import SUBSCRIPTIONS

PARTS = ("exposes", "publicNames", "object", "operations", "filters")
DEPRECATED = "2026-11-01"
SUNSET = "2027-06-30"


def _keep_version_one(world, **kept):
    """A change for ``_activate``: raise ``Capi`` to version 2 without its ``score`` field, keeping
    version 1 as it was frozen from the definition (the editor's raise does the same)."""
    score = world.key("Capi.n")

    def change(_model, definition):
        earlier = {name: copy.deepcopy(definition[name]) for name in PARTS if name in definition}
        definition["earlierVersions"] = [
            {"contractVersion": 1, "deprecated": DEPRECATED, **earlier, **kept}
        ]
        definition["contractVersion"] = 2
        del definition["object"]["fields"][score]

    return change


def _stop_version_one(world):
    score = world.key("Capi.n")

    def change(_model, definition):
        definition["contractVersion"] = 2
        del definition["object"]["fields"][score]

    return change


@pytest.mark.journey("J25.9", "J28.15", "J30.11")
@pytest.mark.settings(**SUBSCRIPTIONS)
@pytest.mark.structures(*LEDGER)
def test_a_kept_version_is_read_and_delivered_in_its_shape_until_it_is_removed(world, receiver):  # noqa: F811
    """Given a webhook on version 1 of an API. When the model raises to version 2 keeping version 1
    (with a sunset day). Then both versions answer a record, version 1 with its score and
    ``Deprecation`` and ``Sunset`` headers, version 2 without either; the index and the version's
    OpenAPI document say version 1 is deprecated; the webhook stays active and the next change
    reaches it in version 1's shape, and a webhook created on version 2 gets version 2's. When the
    model stops serving version 1, reading it is ``404 CONTRACT_VERSION_NOT_FOUND`` naming version
    2, its webhook is suspended, and version 2 goes on."""
    _activate(world, "one")
    ws = _workspace(world)
    old = _subscribe(world, ws, receiver.url + "/v1", events=[EVERY], maxEventsPerBatch=100)
    assert old["contractVersion"] == 1
    api, score = world.key("Capi"), world.key("Capi.n")

    _activate(world, "two", change=_keep_version_one(world, sunset=SUNSET))
    new = _subscribe(world, ws, receiver.url + "/v2", events=[EVERY], maxEventsPerBatch=100)
    assert new["contractVersion"] == 2
    unknown = world.api.post(
        "/consumer-subscriptions",
        {
            "name": "Nope",
            "consumerApi": api,
            "contractVersion": 7,
            "workspaceKey": ws,
            "events": [EVERY],
            "url": receiver.url,
        },
    )
    assert refused(unknown, 400, "CONTRACT_VERSION_NOT_FOUND")["details"][
        "servedContractVersions"
    ] == [2, 1]
    record = world.made("R", "Ledger A", workspace=ws)

    first = consumer_object(world, record["id"], version=1, workspace=ws)
    second = consumer_object(world, record["id"], version=2, workspace=ws)
    assert score in ok(first) and score not in ok(second)
    assert first.headers["Deprecation"] == f"@{int(datetime(2026, 11, 1, tzinfo=UTC).timestamp())}"
    assert first.headers["Sunset"] == "Wed, 30 Jun 2027 00:00:00 GMT"
    assert "Deprecation" not in second.headers and "Sunset" not in second.headers

    index = ok(world.api.get("/api/consumer", workspace=ws))["items"]
    mine = {item["contractVersion"]: item for item in index if item["consumerApi"] == api}
    assert (
        mine[1]["deprecated"] is True
        and mine[1]["sunset"] == SUNSET
        and "deprecated" not in mine[2]
    )
    document = world.api.get(f"/api/consumer/{api}/v1/openapi.json", workspace=ws)
    assert ok(document)["info"]["version"] == "1" and "Deprecation" in document.headers
    assert all(
        op["deprecated"] for methods in ok(document)["paths"].values() for op in methods.values()
    )

    assert ok(world.api.get(f"/consumer-subscriptions/{old['id']}"))["status"] == "active"
    derive_events(world)
    dispatch(world)
    sent = {r["path"]: r["body"] for r in receiver.requests}
    assert set(sent) == {"/hook/v1", "/hook/v2"}
    assert sent["/hook/v1"]["contractVersion"] == 1 and sent["/hook/v2"]["contractVersion"] == 2
    assert all(score in e["object"] for e in sent["/hook/v1"]["events"])
    assert all(score not in e["object"] for e in sent["/hook/v2"]["events"])

    _activate(world, "three", change=_stop_version_one(world))
    gone = refused(
        consumer_object(world, record["id"], version=1, workspace=ws),
        404,
        "CONTRACT_VERSION_NOT_FOUND",
    )
    assert gone["details"]["servedContractVersions"] == [2]
    assert ok(consumer_object(world, record["id"], version=2, workspace=ws))
    suspended = ok(world.api.get(f"/consumer-subscriptions/{old['id']}"))
    assert (suspended["status"], suspended["suspension"]["reason"]) == (
        "suspended",
        "CONTRACT_VERSION_CHANGED",
    )
    assert ok(world.api.get(f"/consumer-subscriptions/{new['id']}"))["status"] == "active"


@pytest.mark.journey("J25.9")
@pytest.mark.structures(*LEDGER)
def test_a_kept_version_that_reads_what_the_model_lacks_or_would_change_is_refused(world):
    """Given version 1 active. When a draft keeps version 1 reading an attribute that does not
    exist, the draft is invalid at that field of the earlier version and the message names version
    1. When a draft keeps version 1 without a field the active version 1 serves, compiling reports
    the change and activating is refused, naming version 1."""
    _activate(world, "one")
    api = world.key("Capi")

    def draft(change):
        model = copy.deepcopy(world.configuration.model)
        model["release"]["version"] += "-kept"
        (definition,) = [d for d in model["consumerApis"] if d["key"] == api]
        change(model, definition)
        created = ok(world.api.post("/model-drafts", {"name": "Kept", "model": model}), 201)
        return created, ok(
            world.api.post(
                f"/model-drafts/{created['id']}/compile", {"expectedVersion": created["version"]}
            )
        )

    def broken(model, definition):
        _keep_version_one(world)(model, definition)
        definition["earlierVersions"][0]["object"]["fields"]["ghost"] = "no-such-attribute"

    _created, compiled = draft(broken)
    assert compiled["valid"] is False
    found = [
        d
        for d in compiled["diagnostics"]
        if d["path"].startswith(f"/consumerApis/{api}/earlierVersions/0/object/fields/ghost")
    ]
    assert found and "version 1" in found[0]["message"], compiled["diagnostics"]

    def changed(model, definition):
        definition["contractVersion"] = 2
        earlier = {name: copy.deepcopy(definition[name]) for name in PARTS if name in definition}
        del earlier["object"]["fields"][world.key("Capi.n")]
        definition["earlierVersions"] = [
            {"contractVersion": 1, "deprecated": DEPRECATED, **earlier}
        ]

    created, compiled = draft(changed)
    assert compiled["valid"] is True
    codes = {d["code"] for d in compiled["consumerContracts"]["diagnostics"]}
    assert "CONSUMER_KEPT_VERSION_CHANGED" in codes, compiled["consumerContracts"]
    release = ok(
        world.api.post(
            f"/model-drafts/{created['id']}/installation", {"expectedVersion": created["version"]}
        ),
        201,
    )
    error = refused(world.activate(release["id"]), 409, "CONSUMER_CONTRACT_VERSION_REQUIRED")
    assert "version 1" in str(error["details"])


@pytest.mark.journey("J25.9", "J30.11")
@pytest.mark.structures(*LEDGER)
def test_a_kept_version_has_the_events_and_output_names_its_own_declaration_gives(world):
    """Given version 1 declaring two events, and a model that raises to version 2 keeping version 1,
    renaming the name output and declaring only one of the events. When a record is renamed and a
    permit created. Then version 1's pull feed tells the permit event and names the changed output as
    version 1 does, and version 2's has neither the event nor the old name."""
    _activate(world, "one")
    ws = _workspace(world)
    old_name = world.key("Capi.name")

    def diverge(_model, definition):
        earlier = {name: copy.deepcopy(definition[name]) for name in PARTS if name in definition}
        definition["earlierVersions"] = [
            {"contractVersion": 1, "deprecated": DEPRECATED, **earlier}
        ]
        definition["contractVersion"] = 2
        fields = definition["object"]["fields"]
        fields["title"] = fields.pop(old_name)
        events = definition["operations"]["events"]
        events["custom"] = [event for event in events["custom"] if event["key"] == EVERY]

    _activate(world, "two", change=diverge)
    record = world.made("R", "Ledger A", workspace=ws)
    _rename(world, "R", record["id"], ws, "Ledger B")
    _permit(world, record["id"], ws)
    derive_events(world)

    def feed(version):
        page = ok(
            consumer_events(
                world, version=version, workspace=ws, after=0, payload="identity", pageSize=1000
            )
        )
        return page["items"]

    first, second = feed(1), feed(2)
    assert CHURN in {e["event"] for e in first} and CHURN not in {e["event"] for e in second}

    def renamed(items):
        return [e["changed"] for e in items if e["event"] == EVERY and e["change"] == "updated"]

    assert [old_name] in renamed(first) and ["title"] not in renamed(first)
    assert ["title"] in renamed(second) and not any(
        old_name in changed for changed in renamed(second)
    )


@pytest.mark.journey("J25.9", "J30.11")
@pytest.mark.settings(**SUBSCRIPTIONS)
@pytest.mark.structures(*LEDGER)
def test_a_change_only_a_kept_version_sees_wakes_its_webhook(world, receiver):  # noqa: F811
    """Given a webhook on version 1 for an event of every change, and a model that raises to version
    2 keeping version 1 but narrowing the event to creations. When a record is renamed. Then version
    2 has no event of it, yet the dispatcher wakes the webhook on version 1 and delivers it
    (R13-F4)."""
    _activate(world, "one")
    ws = _workspace(world)
    old = _subscribe(world, ws, receiver.url + "/v1", events=[EVERY])

    def diverge(_model, definition):
        earlier = {name: copy.deepcopy(definition[name]) for name in PARTS if name in definition}
        definition["earlierVersions"] = [
            {"contractVersion": 1, "deprecated": DEPRECATED, **earlier}
        ]
        definition["contractVersion"] = 2
        events = definition["operations"]["events"]
        events["custom"] = [
            {**event, "changes": ["created"]} for event in events["custom"] if event["key"] == EVERY
        ]

    _activate(world, "two", change=diverge)
    assert ok(world.api.get(f"/consumer-subscriptions/{old['id']}"))["status"] == "active"
    record = world.made("R", "Ledger A", workspace=ws)
    derive_events(world)
    dispatch(world)
    receiver.requests.clear()
    _rename(world, "R", record["id"], ws, "Ledger B")
    derive_events(world)
    seen = ok(consumer_events(world, version=2, workspace=ws, after=0, pageSize=100))["items"]
    assert [e["change"] for e in seen if e["event"] == EVERY] == ["created"]
    dispatch(world)
    sent = [e for r in receiver.requests if r["path"] == "/hook/v1" for e in r["body"]["events"]]
    assert [e["change"] for e in sent] == ["updated"]


@pytest.mark.journey("J25.9", "J28.15")
@pytest.mark.structures(*LEDGER)
def test_an_error_answered_before_the_read_still_announces_a_kept_version(world):
    """Given version 1 kept beside version 2 with a sunset day. When a request for version 1 is
    refused before any read (a page size the feed does not allow), then the error carries the
    ``Deprecation`` and ``Sunset`` headers too, and version 2's does not (R13-F18)."""
    _activate(world, "one")
    ws = _workspace(world)
    _activate(world, "two", change=_keep_version_one(world, sunset=SUNSET))

    first = consumer_events(world, version=1, workspace=ws, after=0, pageSize=1000)
    refused(first, 400, "INVALID_PAGE_SIZE")
    assert first.headers["Deprecation"] == f"@{int(datetime(2026, 11, 1, tzinfo=UTC).timestamp())}"
    assert first.headers["Sunset"] == "Wed, 30 Jun 2027 00:00:00 GMT"
    second = consumer_events(world, version=2, workspace=ws, after=0, pageSize=1000)
    refused(second, 400, "INVALID_PAGE_SIZE")
    assert "Deprecation" not in second.headers and "Sunset" not in second.headers
