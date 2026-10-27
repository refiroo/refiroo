"""J41.2 — a consumer API with and without its grant (USER_JOURNEYS.md § Security, 0.12 Z3).

A client reads a consumer API in a workspace only with a grant of that API there (D306, D307): the
harness, as Security administrator, makes clients and grants them through ``POST /grants``. A
refusal is ``403 FORBIDDEN`` naming the API and the workspace, after the workspace and before the
definition (D309). With a ``consumer`` token the index lists the granted APIs; with a
``management`` token the describing routes need Browse (D308). Each OpenAPI document declares the
client credentials scheme (D311). A subscription names the client or person that created it
(D310). Every case runs on two configurations through the public API.
"""

from uuid import uuid4

import pytest
from harness_identity import TestClient, request_token
from scenario import (
    W1,
    W2,
    Api,
    World,
    consumer_events,
    consumer_list,
    consumer_object,
    consumer_publications,
    consumer_resolve,
    consumer_xref,
    ok,
    refused,
)
from test_j30_consumer_events import LEDGER, _activate
from test_j30_subscriptions import PATH, SUBSCRIPTIONS, _body
from test_j39_sign_in import _browser, _person, _sign_in

STRUCTURES = (*LEDGER, "R.u", "R.b", "B1n")
# The second API the tests activate beside Capi (``World.with_consumer_api``).
OTHER = "journey-api"


def _anonymous(world) -> TestClient:
    return TestClient(world.api.client.app, authenticated=False)


def _grant(world, principal: dict, *, kind: str = "client", **body) -> dict:
    body.setdefault("scope", {"workspaceKey": W1})
    return ok(
        world.api.post("/grants", {"principal": {"kind": kind, "id": principal["id"]}, **body}), 201
    )


def _consumer(world, name: str, *apis: tuple[str, str]) -> tuple[dict, TestClient]:
    """A client granted each ``(consumerApi, workspace)`` and a client of the engine sending its
    ``consumer`` token."""
    client = ok(world.api.post("/clients", {"name": name}), 201)
    for api, workspace in apis:
        _grant(world, client, consumerApi=api, scope={"workspaceKey": workspace})
    token = ok(request_token(_anonymous(world).post, client["id"], client["secret"], "consumer"))
    caller = TestClient(
        world.api.client.app,
        authenticated=False,
        headers={"Authorization": f"Bearer {token['access_token']}"},
    )
    return client, caller


def _as(world, caller: TestClient):
    """``world`` calling with ``caller``'s token, for the scenario's consumer helpers."""
    return World(world.configuration, Api(caller), world.database, world.ids)


def _forbidden(response, api: str, workspace: str) -> None:
    error = refused(response, 403, "FORBIDDEN")
    assert error["details"] == {"consumerApi": api, "workspaceKey": workspace}
    assert api in error["message"] and workspace in error["message"]


def _with_other(world, suffix: str) -> None:
    """Capi declaring events, and the second API, active in every workspace."""
    _activate(world, suffix, change=lambda model, _definition: world.with_consumer_api(model))


def _version(world) -> int:
    (definition,) = [
        d for d in world.configuration.model["consumerApis"] if d["key"] == world.key("Capi")
    ]
    return definition["contractVersion"]


@pytest.mark.journey("J41.2")
@pytest.mark.structures(*STRUCTURES)
def test_a_granted_api_answers_and_others_are_refused(world):
    """Given client C granted consumer API X in workspace A. When it reads an object, a list, xref,
    resolve and the events of X in A, then all answer `200`; X in workspace B and API Y in A answer
    `403 FORBIDDEN` with `consumerApi` and `workspaceKey`; a pinned read of X in A answers."""
    _with_other(world, "granted")
    api = world.key("Capi")
    record = world.made("R", "Granted ledger")
    published = world.publish(world.change_set())
    _, caller = _consumer(world, "Catalogue sync", (api, W1))
    seen = _as(world, caller)

    ok(consumer_object(seen, record["id"]))
    ok(consumer_list(seen, world.key("Capi.all")))
    ok(consumer_xref(seen, query="Granted"))
    ok(consumer_resolve(seen, {"items": [{"query": "Granted ledger"}]}))
    ok(consumer_events(seen))
    ok(consumer_publications(seen))
    pinned = consumer_object(seen, record["id"], publication=published["id"])
    assert pinned.status_code == 200 and pinned.headers["RDM-Publication"] == published["id"]

    _forbidden(consumer_object(seen, record["id"], workspace=W2), api, W2)
    _forbidden(consumer_list(seen, world.key("Capi.all"), workspace=W2), api, W2)
    _forbidden(caller.get(f"/api/consumer/{OTHER}/v1/objects/{record['id']}"), OTHER, W1)


@pytest.mark.journey("J41.2")
@pytest.mark.structures(*STRUCTURES)
def test_the_index_and_documents_follow_the_grants(world):
    """Given C. The index of A lists X only and the index of B is empty; X's document in A declares
    the `clientCredentials` scheme with the token URL and `401` and `403` on its operations; Y's
    document in A answers `403`. With a `management` token, a person holding Reader in A sees every
    API in A's index, and a person without Browse in A gets `403`."""
    _with_other(world, "index")
    api = world.key("Capi")
    _, caller = _consumer(world, "Catalogue sync", (api, W1))

    assert [item["consumerApi"] for item in ok(caller.get("/api/consumer"))["items"]] == [api]
    assert ok(caller.get("/api/consumer", params={"workspace": W2}))["items"] == []
    document = ok(caller.get(f"/api/consumer/{api}/v{_version(world)}/openapi.json"))
    (scheme,) = document["components"]["securitySchemes"].values()
    assert scheme["type"] == "oauth2"
    flow = scheme["flows"]["clientCredentials"]
    assert flow["tokenUrl"].endswith("/oauth/token") and "consumer" in flow["scopes"]
    assert document["security"] == [
        {name: ["consumer"]} for name in document["components"]["securitySchemes"]
    ]
    for path in document["paths"].values():
        for operation in path.values():
            assert {"401", "403"} <= set(operation["responses"])
    _forbidden(caller.get(f"/api/consumer/{OTHER}/v1/openapi.json"), OTHER, W1)

    reader = _person(world, f"reader{uuid4().hex[:6]}")
    _grant(world, reader, kind="user", role="reader")
    browser = _browser(world)
    token = _sign_in(browser, reader["username"])
    listed = ok(browser.get("/api/consumer", headers={"Authorization": f"Bearer {token}"}))
    assert sorted(item["consumerApi"] for item in listed["items"]) == sorted([api, OTHER])

    outsider = _person(world, f"outsider{uuid4().hex[:6]}")
    _grant(world, outsider, kind="user", role="reader", scope={"workspaceKey": W2})
    other_browser = _browser(world)
    other_token = _sign_in(other_browser, outsider["username"])
    refused(
        other_browser.get("/api/consumer", headers={"Authorization": f"Bearer {other_token}"}),
        403,
        "FORBIDDEN",
    )


@pytest.mark.journey("J41.2")
@pytest.mark.structures(*STRUCTURES)
def test_a_refusal_reveals_nothing_about_other_apis(world):
    """A client without grants asking for a key no model declares answers `403`, not `404`; C asking
    for X at another contract version answers `404 CONTRACT_VERSION_NOT_FOUND`; an unknown workspace
    answers `404 WORKSPACE_NOT_FOUND`."""
    api = world.key("Capi")
    record = world.made("R", "Probed ledger")
    _, nobody = _consumer(world, "Prober")
    _forbidden(
        nobody.get(f"/api/consumer/no-such-api/v1/objects/{record['id']}"), "no-such-api", W1
    )

    _, caller = _consumer(world, "Catalogue sync", (api, W1))
    refused(
        caller.get(f"/api/consumer/{api}/v{_version(world) + 7}/objects/{record['id']}"),
        404,
        "CONTRACT_VERSION_NOT_FOUND",
    )
    refused(
        caller.get(
            f"/api/consumer/{api}/v{_version(world)}/objects/{record['id']}",
            params={"workspace": "nowhere"},
        ),
        404,
        "WORKSPACE_NOT_FOUND",
    )


@pytest.mark.journey("J41.2")
@pytest.mark.structures(*STRUCTURES)
def test_a_removed_grant_applies_on_the_next_request(world):
    """Given C reading X in A. When its grant is removed, then its next request answers `403`."""
    api = world.key("Capi")
    record = world.made("R", "Removed ledger")
    client, caller = _consumer(world, "Catalogue sync", (api, W1))
    seen = _as(world, caller)
    ok(consumer_object(seen, record["id"]))
    (grant,) = ok(world.api.get("/grants", principalId=client["id"]))["items"]
    assert world.api.delete(f"/grants/{grant['id']}").status_code == 204
    _forbidden(consumer_object(seen, record["id"]), api, W1)


@pytest.mark.journey("J40", "J41.2")
@pytest.mark.structures(*STRUCTURES)
def test_granting_a_consumer_api(world):
    """`POST /grants` with `consumerApi` and a workspace answers `201` with `role: null` and
    `consumerApi`; A's access lists it and `GET /grants?consumerApi=` finds it; an instance scope or
    a narrowing is `422 GRANT_SCOPE_INVALID`; a key A's model lacks is `422 GRANT_SCOPE_UNKNOWN`;
    both a role and a consumer API is `422`; a person or a group holder is
    `422 CONSUMER_API_CLIENTS_ONLY`."""
    api = world.key("Capi")
    client = ok(world.api.post("/clients", {"name": "Catalogue sync"}), 201)
    grant = _grant(world, client, consumerApi=api)
    assert grant["role"] is None
    assert grant["consumerApi"]["key"] == api and grant["consumerApi"]["name"]
    assert grant["scope"]["workspaceKey"] == W1 and grant["stale"] is False
    access = ok(world.api.get(f"/workspaces/{W1}/access", pageSize=500))["items"]
    assert grant["id"] in [item["id"] for item in access]
    assert [item["id"] for item in ok(world.api.get("/grants", consumerApi=api))["items"]] == [
        grant["id"]
    ]

    principal = {"kind": "client", "id": client["id"]}
    refused(
        world.api.post(
            "/grants", {"principal": principal, "consumerApi": api, "scope": {"instance": True}}
        ),
        422,
        "GRANT_SCOPE_INVALID",
    )
    narrowed = {"workspaceKey": W1, "recordTypes": [world.key("R")]}
    refused(
        world.api.post("/grants", {"principal": principal, "consumerApi": api, "scope": narrowed}),
        422,
        "GRANT_SCOPE_INVALID",
    )
    refused(
        world.api.post(
            "/grants",
            {"principal": principal, "consumerApi": "no-such-api", "scope": {"workspaceKey": W1}},
        ),
        422,
        "GRANT_SCOPE_UNKNOWN",
    )
    person = ok(world.api.post("/users", {"username": "consumer.reader", "name": "Consumer Reader"}), 201)
    group = ok(world.api.post("/groups", {"name": "Consumers"}), 201)
    for kind, holder in (("user", person), ("group", group)):
        error = refused(
            world.api.post(
                "/grants",
                {
                    "principal": {"kind": kind, "id": holder["id"]},
                    "consumerApi": api,
                    "scope": {"workspaceKey": W1},
                },
            ),
            422,
            "CONSUMER_API_CLIENTS_ONLY",
        )
        assert error["details"] == {"principalKind": kind}
    both = world.api.post(
        "/grants",
        {
            "principal": principal,
            "role": "reader",
            "consumerApi": api,
            "scope": {"workspaceKey": W1},
        },
    )
    assert both.status_code == 422


@pytest.mark.journey("J41.2")
@pytest.mark.structures(*STRUCTURES)
def test_a_consumer_api_the_model_drops_reads_stale(world):
    """Given C granted X in A. When a release without X is activated in A, then the grant reads
    `stale: true`."""
    _with_other(world, "kept")
    client, _ = _consumer(world, "Catalogue sync", (OTHER, W1))
    (grant,) = ok(world.api.get("/grants", principalId=client["id"]))["items"]
    assert grant["stale"] is False
    _activate(world, "dropped")
    (grant,) = ok(world.api.get("/grants", principalId=client["id"]))["items"]
    assert grant["stale"] is True and grant["consumerApi"]["key"] == OTHER


@pytest.mark.journey("J41.2", "J30.6")
@pytest.mark.settings(**SUBSCRIPTIONS)
@pytest.mark.structures(*STRUCTURES)
def test_a_subscription_names_its_owner(world):
    """Given a client holding Integration administration in A. When it creates a subscription, then
    the subscription's `owner` names it and `ownerId=` lists it; a person holding Integration
    administration in A reads and suspends it."""
    _activate(world, "owned")
    client = ok(world.api.post("/clients", {"name": "Hook setup"}), 201)
    _grant(world, client, role="integration-admin")
    token = ok(request_token(_anonymous(world).post, client["id"], client["secret"]))[
        "access_token"
    ]
    integrator = TestClient(
        world.api.client.app, authenticated=False, headers={"Authorization": f"Bearer {token}"}
    )
    created = ok(integrator.post(f"/api/v1{PATH}", json=_body(world, W1)), 201)
    assert created["owner"] == {"kind": "client", "id": client["id"], "name": "Hook setup"}
    listed = ok(world.api.get(PATH, ownerId=client["id"]))["items"]
    assert [item["id"] for item in listed] == [created["id"]]

    person = _person(world, f"hooks{uuid4().hex[:6]}")
    _grant(world, person, kind="user", role="integration-admin")
    browser = _browser(world)
    bearer = {"Authorization": f"Bearer {_sign_in(browser, person['username'])}"}
    read = ok(browser.get(f"/api/v1{PATH}/{created['id']}", headers=bearer))
    assert read["owner"]["id"] == client["id"]
    suspended = browser.post(
        f"/api/v1{PATH}/{created['id']}/suspend",
        json={"expectedVersion": read["version"]},
        headers=bearer,
    )
    assert ok(suspended)["status"] == "suspended"
