"""J30.6–J30.7 — Subscribe to a consumer API's events (USER_JOURNEYS.md, Base 0.9 C11).

Each test starts the application with the subscriptions capability on, an allowlist naming
``hooks.example.test`` and ``localhost``, and a key to encrypt signing keys with, and activates a
release whose ``Capi`` declares events, as J30 does. Nothing is delivered before C12: these tests
manage subscriptions and check what suspends them. An expired position (J30.7) needs entries older
than the retention period; the test moves their times back in the database, as J30.5 does.
"""

import base64
from uuid import uuid4

import pytest
from scenario import derive_events, ok, refused
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
from test_j30_consumer_events import (
    CHURN,
    EVERY,
    LEDGER,
    WATCHED,
    _activate,
    _age,
    _events,
    _head,
    _workspace,
)

KEY = base64.urlsafe_b64encode(b"k" * 32).decode()
SUBSCRIPTIONS = {
    "CONSUMER_SUBSCRIPTIONS_ENABLED": "true",
    "CONSUMER_WEBHOOK_ALLOWED_HOSTS": "hooks.example.test, localhost",
    "CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY": KEY,
}
PATH = "/consumer-subscriptions"
URL = "https://hooks.example.test/rdm"


def _token(world, workspace):
    return world.made("K", f"Token {uuid4().hex[:6]}", workspace=workspace)


def _body(world, workspace, **changes):
    body = {
        "consumerApi": world.key("Capi"),
        "workspaceKey": workspace,
        "events": [WATCHED, EVERY],
        "url": URL,
    }
    body.update(changes)
    return body


def _subscribe(world, workspace, **changes):
    return ok(world.api.post(PATH, _body(world, workspace, **changes)), 201)


def _read(world, subscription):
    return ok(world.api.get(f"{PATH}/{subscription['id']}"))


def _suspend(world, subscription):
    current = _read(world, subscription)
    return world.api.post(f"{PATH}/{current['id']}/suspend", {"expectedVersion": current["version"]})


def _resume(world, subscription, **body):
    current = _read(world, subscription)
    return world.api.post(f"{PATH}/{current['id']}/resume", {"expectedVersion": current["version"], **body})


def _workspace_version(world, key):
    return ok(world.api.get(f"/workspaces/{key}"))["version"]


def _set_status(world, key, status):
    body = {"status": status, "expectedVersion": _workspace_version(world, key)}
    return ok(world.api.patch(f"/workspaces/{key}", body))


@pytest.mark.journey("J30.6")
@pytest.mark.settings(**SUBSCRIPTIONS)
@pytest.mark.structures(*LEDGER)
def test_an_operator_subscribes_and_manages_the_subscription(world):
    """Given Capi's events and a workspace with a token. When an operator subscribes to two events,
    narrowed by kind and token. Then the subscription is active under the contract version served,
    starts after the feed's head, and its signing key is answered once, never stored in the clear
    and never read back. One subscribed from an earlier position starts there. The operator edits
    it with the version read, and a stale version is refused; suspends and resumes it, each once;
    lists, narrows and pages the subscriptions; and deletes it."""
    _activate(world, "events")
    ws = _workspace(world)
    token = _token(world, ws)
    world.made("R", "Ledger", workspace=ws)
    head = _head(world, ws)
    kind, related = world.key("Capi.kind"), world.key("Capi.token")

    created = _subscribe(
        world, ws, filters={kind: world.key("Capi.R"), related: [token["name"]]}, payload="identity"
    )
    secret = created.pop("signingSecret")
    assert secret.startswith("rdmwh_") and len(secret) > 40
    assert created["consumerApi"] == world.key("Capi") and created["workspaceKey"] == ws
    assert (created["status"], created["suspension"], created["contractVersion"]) == ("active", None, 1)
    assert created["acknowledgedThrough"] == head
    assert created["filters"] == {kind: [world.key("Capi.R")], related: [token["name"]]}
    assert (created["mode"], created["debounceSeconds"], created["payload"]) == ("perChange", None, "identity")
    assert created["events"] == [WATCHED, EVERY] and created["version"] == 1
    assert _read(world, created) == created
    engine = create_engine(world.database, poolclass=NullPool)
    with engine.connect() as connection:
        stored = connection.scalar(
            text("SELECT signing_key FROM consumer_subscriptions WHERE public_id = :i"), {"i": created["id"]}
        )
    engine.dispose()
    assert secret.encode() not in bytes(stored) and secret.removeprefix("rdmwh_").encode() not in bytes(stored)

    world.made("R", "Later", workspace=ws)
    earlier = _subscribe(world, ws, startAfter=head - 1, mode="coalesced")
    assert earlier["acknowledgedThrough"] == head - 1
    assert (earlier["mode"], earlier["debounceSeconds"], earlier["payload"]) == ("coalesced", 60, "full")

    edited = ok(
        world.api.patch(
            f"{PATH}/{created['id']}",
            {"expectedVersion": 1, "url": "https://hooks.example.test/other", "filters": {kind: world.key("Capi.R2")}},
        )
    )
    assert edited["url"] == "https://hooks.example.test/other"
    assert edited["filters"] == {kind: [world.key("Capi.R2")]}
    assert edited["version"] == 2 and "signingSecret" not in edited
    refused(world.api.patch(f"{PATH}/{created['id']}", {"expectedVersion": 1, "payload": "full"}), 409, "VERSION_CONFLICT")

    suspended = ok(_suspend(world, created))
    assert suspended["status"] == "suspended" and suspended["suspension"]["reason"] == "SUSPENDED_BY_USER"
    assert suspended["suspension"]["suspendedAt"]
    refused(_suspend(world, created), 409, "SUBSCRIPTION_ALREADY_SUSPENDED")
    listed = ok(world.api.get(PATH, consumerApi=world.key("Capi"), status="suspended"))
    assert [item["id"] for item in listed["items"]] == [created["id"]]
    assert "signingSecret" not in listed["items"][0]
    resumed = ok(_resume(world, created))
    assert (resumed["status"], resumed["suspension"]) == ("active", None)
    refused(_resume(world, created), 409, "SUBSCRIPTION_NOT_SUSPENDED")

    first = ok(world.api.get(PATH, workspaceKey=ws, pageSize=1))
    assert [item["id"] for item in first["items"]] == [earlier["id"]]
    second = ok(world.api.get(PATH, workspaceKey=ws, pageSize=1, cursor=first["nextCursor"]))
    assert [item["id"] for item in second["items"]] == [created["id"]]
    assert ok(world.api.get(PATH, consumerApi="no-such-api"))["items"] == []

    current = _read(world, created)
    refused(world.api.delete(f"{PATH}/{created['id']}", expectedVersion=current["version"] - 1), 409, "VERSION_CONFLICT")
    deleted = world.api.delete(f"{PATH}/{created['id']}", expectedVersion=current["version"])
    assert deleted.status_code == 204, deleted.text
    refused(world.api.get(f"{PATH}/{created['id']}"), 404, "SUBSCRIPTION_NOT_FOUND")


@pytest.mark.journey("J30.6")
@pytest.mark.settings(**SUBSCRIPTIONS)
@pytest.mark.structures(*LEDGER)
def test_a_subscription_the_definition_or_deployment_cannot_serve_is_refused(world):
    """Given a definition without events. When an operator subscribes to it, it is refused. Given
    Capi's events. Then each of these is refused at its pointer: an unknown consumer API, an
    unknown event, an undeclared filter, a read's own name or a crosswalk target as a filter, an
    unknown type, a filter value no record has, plain HTTP to a host that is not loopback, a host
    outside the allowlist, a URL with credentials, a retired workspace, a debounce without
    coalescing, and a start past the feed's head. HTTP to an allowlisted loopback host is accepted.
    An edit is checked the same way."""
    ws = _workspace(world)
    error = refused(world.api.post(PATH, _body(world, ws)), 400, "EVENTS_NOT_DECLARED")
    assert error["details"]["pointer"] == "/consumerApi"

    _activate(world, "events")
    token = _token(world, ws)
    kind, related, permit = (world.key(f"Capi.{n}") for n in ("kind", "token", "permit"))
    retired = _workspace(world)
    _set_status(world, retired, "retired")
    for changes, status, code, pointer in [
        ({"consumerApi": "no-such-api"}, 400, "CONSUMER_API_NOT_FOUND", "/consumerApi"),
        ({"events": [EVERY, "no-such-event"]}, 400, "UNKNOWN_EVENT", "/events/1"),
        ({"filters": {"no-such-filter": "x"}}, 400, "UNKNOWN_PARAMETER", "/filters/no-such-filter"),
        ({"filters": {"asOf": "2026-01-01"}}, 400, "PARAMETER_NOT_SUPPORTED", "/filters/asOf"),
        ({"filters": {f"to.{permit}": "x"}}, 400, "PARAMETER_NOT_SUPPORTED", f"/filters/to.{permit}"),
        ({"filters": {kind: "No such kind"}}, 400, "UNKNOWN_OBJECT_TYPE", f"/filters/{kind}"),
        ({"filters": {related: [token["name"], "No such token"]}}, 400, "FILTER_MATCHES_NOTHING", f"/filters/{related}"),
        ({"url": "http://hooks.example.test/rdm"}, 400, "INVALID_WEBHOOK_URL", "/url"),
        ({"url": "https://user:secret@hooks.example.test/rdm"}, 400, "INVALID_WEBHOOK_URL", "/url"),
        ({"url": "https://elsewhere.example.test/rdm"}, 400, "WEBHOOK_HOST_NOT_ALLOWED", "/url"),
        ({"workspaceKey": retired}, 404, "WORKSPACE_NOT_FOUND", "/workspaceKey"),
        ({"workspaceKey": "no-such-site"}, 404, "WORKSPACE_NOT_FOUND", "/workspaceKey"),
        ({"startAfter": _head(world, ws) + 1}, 409, "EVENT_POSITION_AHEAD", "/startAfter"),
    ]:
        error = refused(world.api.post(PATH, _body(world, ws, **changes)), status, code)
        assert error["details"]["pointer"] == pointer, (changes, error)
    refused(world.api.post(PATH, _body(world, ws, debounceSeconds=30)), 422, "REQUEST_VALIDATION_ERROR")

    local = _subscribe(world, ws, url="http://localhost:9000/hook", filters={related: token["name"]})
    assert local["url"] == "http://localhost:9000/hook"
    for changes, code, pointer in [
        ({"url": "https://elsewhere.example.test/rdm"}, "WEBHOOK_HOST_NOT_ALLOWED", "/url"),
        ({"filters": {related: "No such token"}}, "FILTER_MATCHES_NOTHING", f"/filters/{related}"),
        ({"events": ["no-such-event"]}, "UNKNOWN_EVENT", "/events/0"),
    ]:
        body = {"expectedVersion": local["version"], **changes}
        error = refused(world.api.patch(f"{PATH}/{local['id']}", body), 400, code)
        assert error["details"]["pointer"] == pointer
    assert _read(world, local)["version"] == local["version"]


@pytest.mark.journey("J30.7")
@pytest.mark.settings(**SUBSCRIPTIONS)
@pytest.mark.structures(*LEDGER)
def test_a_model_activation_suspends_the_subscriptions_it_leaves_behind(world):
    """Given four subscriptions: to the watched event, to every change narrowed by token, to the D
    event, and one suspended by hand. When a release adding an event is activated, nothing changes.
    When a release at contract version 2 drops the watched event and the token parameter is
    activated. Then the first is suspended as a model change at its event, the second at its
    filter, the third as a contract version change; the fourth keeps its reason. Resuming the first
    unedited is refused, listing what to fix; edited, it resumes under version 2, as do the others."""
    _activate(world, "events")
    ws = _workspace(world)
    token = _token(world, ws)
    related = world.key("Capi.token")
    watched = _subscribe(world, ws, events=[WATCHED])
    narrowed = _subscribe(world, ws, events=[EVERY], filters={related: token["name"]})
    churn = _subscribe(world, ws, events=[CHURN])
    paused = _subscribe(world, ws, events=[CHURN])
    ok(_suspend(world, paused))

    born = {"key": "ledger-born", "objectTypes": [world.key("R")], "changes": ["created"]}
    _activate(world, "born", events=[*_events(world), born])
    assert [_read(world, s)["status"] for s in (watched, narrowed, churn, paused)] == [
        "active",
        "active",
        "active",
        "suspended",
    ]

    def version_two(_model, definition):
        definition["contractVersion"] = 2
        del definition["parameters"][related]

    _activate(world, "v2", events=[e for e in _events(world) if e["key"] != WATCHED], change=version_two)
    first, second, third, fourth = (_read(world, s) for s in (watched, narrowed, churn, paused))
    assert first["suspension"]["reason"] == "MODEL_CHANGED"
    assert [f["pointer"] for f in first["suspension"]["details"]["errors"]] == ["/events/0"]
    assert [f["code"] for f in first["suspension"]["details"]["errors"]] == ["UNKNOWN_EVENT"]
    assert second["suspension"]["reason"] == "MODEL_CHANGED"
    assert [f["pointer"] for f in second["suspension"]["details"]["errors"]] == [f"/filters/{related}"]
    assert third["suspension"]["reason"] == "CONTRACT_VERSION_CHANGED"
    assert third["suspension"]["details"] == {"contractVersion": 1, "servedContractVersion": 2}
    assert fourth["suspension"]["reason"] == "SUSPENDED_BY_USER"
    assert all(s["contractVersion"] == 1 for s in (first, second, third, fourth))

    error = refused(_resume(world, watched), 409, "SUBSCRIPTION_NEEDS_EDIT")
    assert [(f["code"], f["pointer"]) for f in error["details"]["errors"]] == [("UNKNOWN_EVENT", "/events/0")]
    edited = ok(world.api.patch(f"{PATH}/{first['id']}", {"expectedVersion": first["version"], "events": [EVERY]}))
    assert edited["status"] == "suspended"
    resumed = ok(_resume(world, watched))
    assert (resumed["status"], resumed["contractVersion"]) == ("active", 2)
    ok(world.api.patch(f"{PATH}/{second['id']}", {"expectedVersion": second["version"], "filters": {}}))
    for subscription in (narrowed, churn, paused):
        resumed = ok(_resume(world, subscription))
        assert (resumed["status"], resumed["contractVersion"]) == ("active", 2)


@pytest.mark.journey("J30.7")
@pytest.mark.settings(**SUBSCRIPTIONS)
@pytest.mark.structures(*LEDGER)
def test_retiring_a_workspace_suspends_its_subscriptions(world):
    """Given a subscription in a workspace that is not the default. When the workspace is retired,
    the subscription is suspended for it, and a resume is refused while the workspace is retired;
    reactivated, the subscription resumes. A workspace with a subscription cannot be deleted until
    the subscription is."""
    _activate(world, "events")
    ws = _workspace(world)
    subscription = _subscribe(world, ws)
    other = _subscribe(world, _workspace(world))

    _set_status(world, ws, "retired")
    suspended = _read(world, subscription)
    assert suspended["suspension"]["reason"] == "WORKSPACE_RETIRED"
    assert _read(world, other)["status"] == "active"
    error = refused(_resume(world, subscription), 409, "SUBSCRIPTION_NEEDS_EDIT")
    assert [(f["code"], f["pointer"]) for f in error["details"]["errors"]] == [
        ("WORKSPACE_NOT_FOUND", "/workspaceKey")
    ]
    _set_status(world, ws, "active")
    assert ok(_resume(world, subscription))["status"] == "active"

    refused(
        world.api.delete(f"/workspaces/{ws}", expectedVersion=_workspace_version(world, ws)),
        409,
        "WORKSPACE_HAS_SUBSCRIPTIONS",
    )
    current = _read(world, subscription)
    assert world.api.delete(f"{PATH}/{current['id']}", expectedVersion=current["version"]).status_code == 204
    deleted = world.api.delete(f"/workspaces/{ws}", expectedVersion=_workspace_version(world, ws))
    assert deleted.status_code == 204, deleted.text


@pytest.mark.journey("J30.7")
@pytest.mark.settings(**SUBSCRIPTIONS)
@pytest.mark.structures(*LEDGER)
def test_resuming_after_expired_events_needs_the_loss_acknowledged(world):
    """Given a subscription suspended by hand in a new workspace, then writes and a publish whose
    entries age past retention. When it is resumed, the resume is refused as expired, naming the
    lost positions and the publication to re-sync from; with the loss acknowledged it resumes after
    the last expired position. A subscription cannot start at an expired position."""
    _activate(world, "events")
    ws = _workspace(world)
    subscription = _subscribe(world, ws)
    ok(_suspend(world, subscription))
    start = subscription["acknowledgedThrough"]

    world.made("R", "Before", workspace=ws)
    cs = world.change_set(workspace=ws)
    world.made("R", "Added", change_set=world.current(cs), workspace=ws)
    publication = world.publish(cs, workspace=ws)
    world.made("R", "After", workspace=ws)
    derive_events(world)
    sequence = publication["feedPosition"]
    _age(world, ws, 31, sequence)

    error = refused(_resume(world, subscription), 409, "EVENTS_EXPIRED")
    assert error["details"] == {
        "fromPosition": start + 1,
        "toPosition": sequence,
        "publication": {"id": publication["id"], "eventSequence": sequence},
    }
    resumed = ok(_resume(world, subscription, acknowledgeLoss=True))
    assert (resumed["status"], resumed["acknowledgedThrough"]) == ("active", sequence)

    error = refused(world.api.post(PATH, _body(world, ws, startAfter=0)), 410, "EVENTS_EXPIRED")
    assert error["details"]["pointer"] == "/startAfter"
    assert error["details"]["publication"] == {"id": publication["id"], "eventSequence": sequence}
    assert _subscribe(world, ws, startAfter=sequence)["acknowledgedThrough"] == sequence


@pytest.mark.journey("J30.6")
@pytest.mark.structures(*LEDGER)
def test_subscriptions_are_a_capability_the_deployment_turns_on(world):
    """Given the default settings. Then the subscription routes are not served and the capabilities
    say so, naming the setting."""
    capabilities = ok(world.api.get("/capabilities"))["consumerSubscriptions"]
    assert capabilities == {
        "manageSubscriptions": False,
        "allowedHosts": [],
        "setting": "CONSUMER_SUBSCRIPTIONS_ENABLED",
    }
    assert world.api.get(PATH).status_code == 404
    assert world.api.post(PATH, {}).status_code == 404


@pytest.mark.journey("J30.6")
@pytest.mark.settings(**SUBSCRIPTIONS)
@pytest.mark.structures(*LEDGER)
def test_the_capabilities_name_the_allowed_hosts(world):
    """Given the capability on. Then the capabilities report it with the allowlist."""
    assert ok(world.api.get("/capabilities"))["consumerSubscriptions"] == {
        "manageSubscriptions": True,
        "allowedHosts": ["hooks.example.test", "localhost"],
        "setting": "CONSUMER_SUBSCRIPTIONS_ENABLED",
    }
