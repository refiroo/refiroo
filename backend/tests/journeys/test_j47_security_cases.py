"""J47.2–J47.5, J47.7 and J47.9 — the security cases a sweep cannot express (0.12 E1, phase B).

B1 a Reader on every write path, with the state read before and after; B2 every operation a grant can
narrow is named with the test that proves its narrowed refusal; B3 false tokens run nothing; B4 the
reset-by-mail ask and the mail it sends. What earlier journeys already prove is listed in each case
and not repeated. Every case runs on two configurations through the public API.
"""

import base64
import json
import re
import time
from uuid import uuid4

import jwt
import pytest
import test_j40_authorization as j40
from harness_identity import TestClient, request_token
from scenario import W1, W2, ok, refused, send_mail
from test_j30_consumer_events import LEDGER, _activate
from test_j30_subscriptions import PATH, SUBSCRIPTIONS, _body, _subscribe
from test_j39_provider_sign_in import PAT, _provider, _signed_in, idp  # noqa: F401
from test_j39_second_factor import _password_step, _second, _set_up, _step, _totp
from test_j39_sign_in import (
    PASSWORD,
    _bearer,
    _browser,
    _code,
    _exchange,
    _invalid_grant,
    _pkce,
    _renew,
    _request,
    _revoked,
    _sign_in,
)
from test_j40_authorization import _as, _client, _publication_body
from test_j46_mail import _save, _token, smtp  # noqa: F401  (smtp is a fixture)
from test_j46_reset_by_mail import APP as APP_ORIGIN
from test_j46_reset_by_mail import SET_TO, _ask, _outbox, _with_password
from test_j47_security_sweep import CONSUMER, app_routes, operations
from test_openapi_contract import OPEN_OPERATIONS

from app.common.outage import unavailable_counts
from app.engine.authorization.catalogue import GROUPS
from app.engine.identity import keys


def _denied(response, action: str, groups: list[str], workspace: str | None) -> None:
    """``403 FORBIDDEN`` naming the action, the groups that would allow it and the workspace."""
    error = refused(response, 403, "FORBIDDEN")
    assert error["details"] == {"action": action, "groups": groups, "workspaceKey": workspace}


def _state(world) -> dict:
    """What a write would change: the records of a type, the change sets, the publications, the
    subscriptions and the jobs."""

    def ids(path: str, **params) -> list[str]:
        return sorted(
            item["id"] for item in ok(world.api.get(path, pageSize=500, **params))["items"]
        )

    return {
        "records": ok(
            world.api.get(f"/objects/{world.key('R')}", workspaceKey=W1, includeTotal=True)
        )["totalCount"],
        "changeSets": ids(f"/workspaces/{W1}/change-sets"),
        "publications": ids(f"/workspaces/{W1}/publications"),
        "subscriptions": ids(PATH) if world.api.get(PATH).status_code == 200 else [],
        "jobs": ids("/jobs"),
    }


# --- B1 --------------------------------------------------------------------------------------------
# Covered by test_j40_authorization.py::test_a_reader_reads_and_changes_nothing: the 403s of a live
# write, a change set created, a record written in one, a batch, an import and a publication, and the
# reads of workspace B. Not covered there, and added below with the proof that nothing changed: a
# move, a feed read of another workspace, a subscription write, a webhook key rotation and a consumer
# route without its grant.


@pytest.mark.journey("J47.2")
@pytest.mark.settings(**SUBSCRIPTIONS)
@pytest.mark.structures(*LEDGER)
def test_a_reader_is_refused_on_every_write_path_and_nothing_changes(world):
    """Given a Reader in workspace A, a change set, a subscription and the state of A read. When it
    writes live, writes in a change set, creates one, publishes, sends a batch and an import, moves
    records, reads the feed of workspace B, creates a subscription and rotates its key, and calls a
    consumer route without a consumer grant, then each answers `403 FORBIDDEN` and the state read
    again is the same."""
    _activate(world, "events")
    subscription = _subscribe(world, W1)
    change_set = world.change_set()
    client, reader = _client(world, "Reader", ("reader", {"workspaceKey": W1}))
    before = _state(world)

    _denied(reader.create("R", "Not by a reader"), "records.write", ["edit-live"], W1)
    _denied(
        reader.create("R", "Not in a change set", change_set=world.current(change_set)),
        "records.write",
        ["change-sets"],
        W1,
    )
    _denied(
        reader.api.post(f"/workspaces/{W1}/change-sets", {"source": "currentLive"}),
        "change-sets.write",
        ["change-sets"],
        W1,
    )
    _denied(
        reader.api.post(
            f"/change-sets/{change_set['id']}/publication",
            _publication_body(world, change_set),
        ),
        "change-sets.publish",
        ["publish"],
        W1,
    )
    _denied(
        reader.api.post("/batches", {"workspaceKey": W1, "items": []}),
        "bulk.write",
        ["bulk"],
        W1,
    )
    imported = reader.api.upload(
        "/imports",
        {"file": ("rows.csv", b"name\nx\n", "text/csv")},
        {"request": json.dumps({"workspaceKey": W1, "policy": "independent"})},
    )
    _denied(imported, "bulk.write", ["bulk"], W1)
    move = {
        "sourceWorkspaceKey": W1,
        "targetWorkspaceKey": W2,
        "mapping": {"key": "none", "expectedVersion": 1},
        "selection": {},
        "stage": "execute",
    }
    _denied(reader.api.post("/moves", move), "moves.create", ["copy-move"], W2)
    _denied(reader.api.get(f"/workspaces/{W2}/feed"), "feed.read", ["feed"], W2)
    _denied(
        reader.api.post(PATH, _body(world, W1)),
        "subscriptions.manage",
        ["integration-admin"],
        W1,
    )
    _denied(
        reader.api.post(
            f"{PATH}/{subscription['id']}/rotate-secret",
            {"expectedVersion": subscription["version"]},
        ),
        "subscriptions.manage",
        ["integration-admin"],
        W1,
    )
    # The same client asks for a `consumer` token: it holds Browse, not a consumer API grant (D306).
    anonymous = TestClient(world.api.client.app, authenticated=False)
    api = world.key("Capi")
    consumer = ok(request_token(anonymous.post, client["id"], client["secret"], "consumer"))[
        "access_token"
    ]
    response = anonymous.get(
        f"/api/consumer/{api}/v1/publications", headers={"Authorization": f"Bearer {consumer}"}
    )
    error = refused(response, 403, "FORBIDDEN")
    assert error["details"] == {"consumerApi": api, "workspaceKey": W1}

    assert _state(world) == before


# --- B2 --------------------------------------------------------------------------------------------
# Each operation whose action allows a group a grant can narrow, with the J40 test that proves the
# narrowed refusal on its write path, or the reason it writes no record. The records and
# relationships are one write unit (D281): a route is mapped to the path its writes take.
_LIVE = "test_a_narrowed_live_write"
# A deletion goes through the deletion path, not the write unit's `remove_records`: live, with its
# cascade, in a batch or import and in a change set, each with its own case beside this one.
_DELETE = "test_a_narrowed_live_delete"
_BATCH = "test_a_narrowed_batch_and_import"
_RELATE = "test_a_narrowed_relationship"
_PUBLISH = "test_a_narrowed_change_set_and_publication"
_RESHAPE = "test_a_narrowed_type_change"
_MOVE = "test_a_narrowed_move"
_JOB = "test_a_job_keeps_its_requesters_permissions"
_SOURCE = "test_a_source_file_belongs_to_its_uploader_and_workspace"
_NO_RECORD = "no record is written"
_NOT_NARROWED = "a migration and a withdrawal are not narrowed (API.md § Narrowed writes)"

NARROWED_PATHS: dict[tuple[str, str], str] = {}
for _test, _routes in {
    _LIVE: [
        "post /objects",
        "patch /objects/{object_type_key}/{object_id}",
        "post /objects/{object_type_key}/{object_id}/attributes/{attribute_type_key}",
        "patch /objects/{object_type_key}/{object_id}/attributes/{attribute_type_key}",
        "delete /objects/{object_type_key}/{object_id}/attributes/{attribute_type_key}",
    ],
    _DELETE: ["delete /objects/{object_type_key}/{object_id}"],
    _RELATE: [
        "post /relations",
        "patch /relations/{relation_id}",
        "delete /relations/{relation_id}",
        "put /workspaces/{workspace_key}/mappings",
    ],
    _BATCH: ["post /batches", "post /imports"],
    _PUBLISH: ["post /change-sets/{change_set_id}/publication"],
    _RESHAPE: [
        "post /change-sets/{change_set_id}/restructurings/preview",
        "post /change-sets/{change_set_id}/restructurings",
    ],
    _MOVE: ["post /moves"],
    _JOB: [
        "get /jobs/{job_id}",
        "get /jobs/{job_id}/items",
        "get /jobs/{job_id}/rows",
        "get /jobs/{job_id}/output",
        "get /jobs/{job_id}/events",
        "post /jobs/{job_id}/cancel",
        "post /jobs/{job_id}/confirm",
        # The proposal job and an assistant task's load write as their requester (0.16 AP2, AP6a).
        "post /workspaces/{workspace_key}/mapping-proposals",
        "post /ai/tasks/{task_id}/run",
    ],
    _SOURCE: [
        "get /source-files",
        "post /source-files",
        "get /source-files/{source_file_id}",
        "delete /source-files/{source_file_id}",
        "get /source-files/{source_file_id}/profile/sheets",
        "get /source-files/{source_file_id}/profile/sheets/{sheet}/columns",
        "get /source-files/{source_file_id}/profile/sheets/{sheet}/cells",
    ],
    _NOT_NARROWED: [
        "post /publications/{publication_id}/withdrawal",
        "post /change-sets/{change_set_id}/model-migrations",
    ],
    _NO_RECORD + ": change sets are made, renamed, validated and discarded": [
        "post /workspaces/{workspace_key}/change-sets",
        "patch /change-sets/{change_set_id}",
        "delete /change-sets/{change_set_id}",
        "patch /change-sets/{change_set_id}/model-release",
        "post /change-sets/{change_set_id}/validation",
    ],
    _NO_RECORD + ": a change set is submitted for publication and its submission withdrawn": [
        "post /change-sets/{change_set_id}/submission",
        "delete /change-sets/{change_set_id}/submission",
    ],
    _NO_RECORD + ": an assistant task designs a load, takes answers, checks and cancels it": [
        "post /ai/tasks",
        "get /ai/tasks/{task_id}",
        "get /ai/tasks/{task_id}/changes",
        "post /ai/tasks/{task_id}/plan",
        "post /ai/tasks/{task_id}/answers",
        "post /ai/tasks/{task_id}/model",
        "post /ai/tasks/{task_id}/accept",
        "post /ai/tasks/{task_id}/discard",
        "post /ai/tasks/{task_id}/cancel",
    ],
    _NO_RECORD + ": an import profile holds a column layout": [
        "get /import-profiles",
        "post /import-profiles",
        "get /import-profiles/{profile_key}",
        "put /import-profiles/{profile_key}",
        "delete /import-profiles/{profile_key}",
        "get /import-profiles/{profile_key}/check",
        "post /import-profiles/{profile_key}/check",
        "get /import-profiles/{profile_key}/check/new-values",
        "get /import-profiles/{profile_key}/check/drift",
        "get /import-profiles/{profile_key}/check/missing-records",
        "get /import-profiles/{profile_key}/check/rows",
    ],
    _NO_RECORD + ": a mapping relates two models": [
        "get /model-mappings",
        "post /model-mappings",
        "get /model-mappings/{key}",
        "delete /model-mappings/{key}",
        "get /model-mappings/{key}/operations",
        "post /model-mappings/{key}/operations",
        "get /model-mappings/{key}/inference",
        "post /model-mappings/{key}/inference",
        "get /model-mappings/{key}/inference/proposals",
        "post /model-mappings/{key}/undo",
        "post /model-mappings/{key}/redo",
        "post /model-mappings/{key}/inference/application",
    ],
}.items():
    for _route in _routes:
        _method, _path = _route.split(" ")
        NARROWED_PATHS[(_method, "/api/v1" + _path)] = _test


@pytest.mark.journey("J47.3")
@pytest.mark.settings(**SUBSCRIPTIONS)
@pytest.mark.structures(*LEDGER)
def test_every_operation_a_grant_can_narrow_names_its_narrowing_test(world):
    """Given the document's operations. When those whose action allows a narrowable group are listed,
    then each is in `NARROWED_PATHS`, naming a journey test of J40 (a function of that module named
    `test_…` and marked `J40`) or the reason it writes no record; a route added without a decision
    fails here, and so does an entry for no route, and so does a name that is no J40 test. That the
    named test exercises the route is read in review, not here."""
    declared, _ = operations(world.api.client.app)
    narrowable = {key for key, group in GROUPS.items() if group.narrowable}
    found = {op.key for op in declared if narrowable.intersection(op.groups)}
    assert found - set(NARROWED_PATHS) == set(), "no narrowing decision for these operations"
    assert set(NARROWED_PATHS) - found == set(), "a decision for an operation that is not there"
    for name in set(NARROWED_PATHS.values()):
        if name.startswith(("no record", "a migration")):
            continue
        test = getattr(j40, name, None)
        assert callable(test) and name.startswith("test_"), f"{name} is no test of J40"
        marks = [mark for mark in getattr(test, "pytestmark", []) if mark.name == "journey"]
        assert any(str(arg).startswith("J40") for mark in marks for arg in mark.args), (
            f"{name} is not marked as a J40 journey"
        )


# --- B3 --------------------------------------------------------------------------------------------
# Covered by test_j39_j41_j43_identity.py: a token signed by a key never held and one signed by the
# wrong key with the right header (`unknownKey`, `signature`), a malformed token, the other API's
# audience both ways (`audience`), the signing key retired by "rotate now" (`unknownKey`), a
# deactivated client (`revoked`); by test_j39_sign_in.py::test_a_deactivated_person_is_refused_at_once
# a deactivated person (`revoked`); by test_j40_authorization.py::test_a_change_applies_on_the_next_
# request_in_every_process a removed grant (a token proves who: the next request is `403`, not `401`).
# Added below, through the API with a write that would change data if it ran: an expired token, an
# altered payload and signature, `alg: none` and HS256, and a rotated client secret.


def _b64(value: dict | bytes) -> str:
    raw = json.dumps(value).encode() if isinstance(value, dict) else value
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _claims(world, subject: str, **changes) -> dict:
    now = int(time.time())
    return {
        "iss": world.api.client.app.state.identity_settings.issuer,
        "sub": subject,
        "aud": "management",
        "iat": now,
        "exp": now + 3600,
        "jti": uuid4().hex,
        "principalKind": "client",
        **changes,
    }


def _signed(world, subject: str, **changes) -> str:
    """A token the engine's own current key signs, with the claims asked for."""
    app = world.api.client.app
    with app.state.session_factory() as session:
        kid, private = keys.signing_key(session, app.state.identity_settings)
    return jwt.encode(_claims(world, subject, **changes), private, "ES256", {"kid": kid})


def _kid(world) -> str:
    app = world.api.client.app
    with app.state.session_factory() as session:
        return keys.signing_key(session, app.state.identity_settings)[0]


def _reason(response, reason: str) -> None:
    error = refused(response, 401, "TOKEN_INVALID")
    assert error["details"] == {"reason": reason}, error
    assert response.headers["www-authenticate"] == 'Bearer error="invalid_token"'


@pytest.mark.journey("J47.4")
@pytest.mark.structures("R")
def test_a_false_token_runs_nothing(world):
    """Given a client holding Data steward and a control token the engine's key signs, which writes.
    When the same write is sent with a token that is expired, one whose payload names another
    caller, one with its signature cut, one with `alg: none` and one signed with HS256, then each is
    `401 TOKEN_INVALID` (`expired`, `signature`, `signature`, `malformed`, `malformed`) and no record
    is made; a request that would make a client, sent with the payload of the administrator's token
    over the steward's signature, makes none."""
    client, steward = _client(world, "Steward", ("steward", {"workspaceKey": W1}))
    control = _signed(world, client["id"])
    ok(_as(world, control).create("R", "Control"), 201)
    made = _state(world)["records"]

    real = steward.api.client.headers["Authorization"].removeprefix("Bearer ")
    harness = next(
        item
        for item in ok(world.api.get("/clients", q="Test harness"))["items"]
        if item["name"] == "Test harness"
    )
    head, payload, signature = real.split(".")
    altered = json.loads(base64.urlsafe_b64decode(payload + "=="))
    altered["sub"] = harness["id"]
    kid = _kid(world)
    header = {"alg": "none", "kid": kid}
    claims = _claims(world, client["id"])
    attempts = {
        "expired": (_signed(world, client["id"], exp=int(time.time()) - 10), "expired"),
        "payload": (f"{head}.{_b64(altered)}.{signature}", "signature"),
        "signature": (f"{head}.{payload}.{signature[:-6]}", "signature"),
        "none": (f"{_b64(header)}.{_b64(claims)}.", "malformed"),
        "hs256": (jwt.encode(claims, "secret" * 8, "HS256", {"kid": kid}), "malformed"),
    }
    for name, (token, reason) in attempts.items():
        _reason(_as(world, token).create("R", f"By {name}"), reason)
    _reason(
        _as(world, attempts["payload"][0]).api.post("/clients", {"name": "Escalated"}), "signature"
    )
    assert _state(world)["records"] == made
    assert ok(world.api.get("/clients", q="Escalated"))["items"] == []


@pytest.mark.journey("J47.4")
@pytest.mark.structures("R")
def test_a_rotated_secret_does_not_end_a_token_already_issued(world):
    """Given a client with a token. When its secret is rotated with no overlap, then the old secret
    obtains no token and the new one does; the token already issued still works until it expires or
    the client is deactivated (a token proves who, never what: API.md § Authentication, D226). A
    removed grant is `403`, not `401` (J40.6)."""
    client, steward = _client(world, "Rotated", ("steward", {"workspaceKey": W1}))
    ok(steward.create("R", "Before"), 201)
    rotated = ok(
        world.api.post(
            f"/clients/{client['id']}/secrets",
            {"expectedVersion": client["version"], "overlapHours": 0},
        ),
        201,
    )
    anonymous = TestClient(world.api.client.app, authenticated=False)
    assert request_token(anonymous.post, client["id"], client["secret"]).status_code == 401
    assert request_token(anonymous.post, client["id"], rotated["secret"]).status_code == 200
    ok(steward.create("R", "After"), 201)
    changed = ok(
        world.api.patch(
            f"/clients/{client['id']}", {"expectedVersion": rotated["version"], "active": False}
        )
    )
    assert changed["active"] is False
    _reason(steward.create("R", "Never"), "revoked")


# --- B4 --------------------------------------------------------------------------------------------
# Covered by test_j46_reset_by_mail.py: the same answer for a known person (by name, and by address
# in other letters), one with no address, one with no password, a deactivated one and a stranger, and
# only the first queueing a message; the slowing of an ask per typed name, for a stranger as for a
# person, with sign-in unaffected; the link working once; the same text whoever asked. Added below: a
# provider-only person among them, the slowing per address, and the scan of every message sent.


@pytest.mark.journey("J47.5")
def test_a_provider_only_person_is_asked_for_like_a_stranger(world, smtp, idp):  # noqa: F811
    """Given a person who only ever signed in through the organisation's provider (no local
    password, an address) and one with a password. When each, and a stranger, is asked for by
    username and by address, then every answer is the same and one message is queued, to the person
    with the password."""
    _save(world, smtp)
    _provider(world, idp)
    _signed_in(world, idp, **PAT, preferred_username="pat", groups=[])
    _with_password(world, "ada", "ada@example.org")
    from test_j39_sign_in import _browser

    browser = _browser(world)
    names = ("ada", "pat", "PAT@example.org", "nobody", "nobody@example.org")
    answers = [_ask(browser, name) for name in names]
    assert all(answer == answers[0] for answer in answers)
    assert _outbox(world)["pending"] == 1
    send_mail(world)
    assert [mail["To"] for mail in smtp.messages] == ["ada@example.org"]


@pytest.mark.journey("J47.5")
def test_asking_is_slowed_per_address_whatever_the_names(world, smtp):  # noqa: F811
    """Given mail is set up. When one address asks for different names in a row, then it is refused
    `429 slowed` with the seconds to wait within forty asks (the address is allowed more than a name), and then even a name it never
    asked for, a person's, is refused and queues nothing."""
    from test_j39_sign_in import _browser

    _save(world, smtp)
    _with_password(world, "ada", "ada@example.org")
    browser = _browser(world)
    slowed = None
    for number in range(40):
        response = browser.post(
            "/oauth/sign-in/reset-request",
            json={"identifier": f"stranger-{number}"},
            headers={"Origin": "http://localhost:5173"},
        )
        if response.status_code == 429:
            slowed = response.json()
            break
        assert response.status_code == 202, response.text
    assert slowed and slowed["error"] == "slowed" and slowed["waitSeconds"] >= 1
    _ask(browser, "ada", 429)
    assert _outbox(world)["pending"] == 0
    assert send_mail(world) == 0 and smtp.messages == []


def _texts(mail) -> list[str]:
    """Every header and decoded text part of a message."""
    found = [str(value) for value in mail.values()]
    for part in mail.walk():
        if part.get_content_maintype() == "text":
            found.append(part.get_content())
    return found


@pytest.mark.journey("J47.5")
@pytest.mark.structures("R")
def test_no_message_holds_a_password_a_code_or_a_record(world, smtp):  # noqa: F811
    """Given a person with a password, a record and mail set up. When a reset is asked for, an
    administrator mails the person a link, the test message goes, the password is reset through the
    link and mail is sent, then no message holds either password or the record's name, and each
    link's token appears once in its message, inside the one link."""
    from urllib.parse import parse_qs, urlsplit

    from test_j39_sign_in import PASSWORD, _browser
    from test_j46_reset_by_mail import SET_TO

    _save(world, smtp)
    ada = _with_password(world, "ada", "ada@example.org")
    record = world.made("R", "Distinctive record 7731")
    browser = _browser(world)
    _ask(browser, "ada")
    ok(world.api.post(f"/users/{ada['id']}/password-reset", {"send": True}), 201)
    ok(world.api.post("/mail-settings/test", {"to": "ada@example.org"}))
    send_mail(world)
    links = []
    for mail in smtp.messages:
        lines = [line for text in _texts(mail) for line in text.splitlines() if "token=" in line]
        links += [parse_qs(urlsplit(line.strip()).query)["token"][0] for line in lines]
    assert len(links) == 2, "one link in each of the two reset messages"
    done = browser.post(
        "/oauth/sign-in/reset",
        json={"token": links[-1], "password": SET_TO, "repeat": SET_TO},
        headers={"Origin": "http://localhost:5173"},
    )
    assert ok(done)["status"] == "password_set"
    send_mail(world)
    forbidden = [PASSWORD, SET_TO, record["name"], record["id"], "7731"]
    assert len(smtp.messages) >= 3
    for mail in smtp.messages:
        texts = _texts(mail)
        for secret in forbidden:
            assert not any(secret in text for text in texts), (mail["Subject"], secret)
        for token in links:
            assert sum(text.count(token) for text in texts) <= 1, mail["Subject"]


# --- J47.7: every route the document does not list ----------------------------------------------------
# Each route outside the OpenAPI document (and each of the document's open routes, whose junk the sweep
# does not send) is classified from API.md ("Routes that need no token", the OAuth endpoints, the
# console token and the passkey pages), with the reason, and answers as its class says. The
# `/api/consumer` routes are J47.6's and `/metrics` is an operation (J47.1); both are checked here only
# with no credentials, and `/metrics` with the three callers its class names.
OPEN, SESSION = "open by design", "needs a session"
APP = {"Origin": "http://localhost:5173"}
SHAPES = "shaped"  # the key of a route's well-formed body in `Route.shaped`


class Route:
    """A route's class, why, what it answers to a request with nothing but its address (``bare``), a
    well-formed body to refuse for want of credentials or a foreign origin, and whether the origin is
    checked (API.md: `403 foreign_origin`, `403 access_denied`, the page's `403`)."""

    def __init__(
        self, kind, reason, bare, *, body=None, shaped=None, origin=False, redirects=False, valid=()
    ):
        self.kind, self.reason, self.bare = kind, reason, set(bare)
        self.valid = set(valid)  # what a well-formed authorization request is served
        self.body, self.shaped, self.origin, self.redirects = body, shaped, origin, redirects


_CER = {"ceremony": "x", "credential": {}, "name": "n"}
CLASSIFICATION: dict[tuple[str, str], Route] = {
    ("get", "/health"): Route(OPEN, "probe: status only", {200}),
    ("get", "/health/live"): Route(OPEN, "probe: the process answers", {200}),
    ("get", "/.well-known/oauth-authorization-server"): Route(OPEN, "RFC 8414 metadata", {200}),
    ("get", "/oauth/jwks"): Route(OPEN, "the public keys that verify tokens", {200}),
    ("post", "/oauth/token"): Route(OPEN, "the credentials are the request", {400}, body="form"),
    ("post", "/oauth/revoke"): Route(OPEN, "the token is the credential; always 200", {200}, body="form"),
    ("get", "/metrics"): Route("needs the operations role", "Prometheus scrape (operations.read)", {401}),
    ("get", "/openapi.json"): Route(OPEN, "the contract a client needs before it has a token (D412)", {200}),
    ("get", "/docs"): Route(OPEN, "the API reference page; its console signs in by session (C1)", {200}),
    ("get", "/docs/scalar/standalone.js"): Route(OPEN, "the page's bundled script", {200}),
    ("get", "/brand/{name}"): Route(OPEN, "the mark on the engine's own pages", {404}),
    ("get", "/oauth/authorize"): Route(OPEN, "the sign-in page", {400}, valid={200}),
    ("post", "/oauth/authorize"): Route(OPEN, "the sign-in form", {400}, body="form", origin=True),
    ("post", "/oauth/second-factor"): Route(OPEN, "the sign-in page's second step (a step token)", {410}, body="form", origin=True),
    ("get", "/oauth/providers/{key}/start"): Route(OPEN, "the provider button's address", {400, 404}),
    ("get", "/oauth/providers/{key}/callback"): Route(OPEN, "where a provider returns the browser (state, nonce, PKCE are the proof)", {400, 404}),
    ("get", "/oauth/sign-out"): Route(SESSION, "ends the session its cookie holds; with none it only redirects", {303}, redirects=True),
    ("get", "/oauth/providers/{key}/signed-out"): Route(OPEN, "where a provider returns after sign-out; only redirects", {303}, redirects=True),
    ("get", "/oauth/passkey.js"): Route(OPEN, "the sign-in pages' one script", {200}),
    ("get", "/oauth/passkeys/new"): Route(SESSION, "adds a passkey for the person the cookie holds", {401}),
    ("post", "/oauth/passkeys/registration/options"): Route(SESSION, "registration ceremony: the cookie's person", {401}, body="json", shaped={}, origin=True),
    ("post", "/oauth/passkeys/registration/verify"): Route(SESSION, "registration ceremony: the cookie's person", {422}, body="json", shaped=_CER, origin=True),
    ("post", "/oauth/passkeys/authentication/options"): Route(OPEN, "a passkey sign-in starts without a session", {422}, body="json", shaped={}, origin=True),
    ("post", "/oauth/passkeys/authentication/verify"): Route(OPEN, "a passkey sign-in ends in a session", {422}, body="json", shaped={"ceremony": "x", "credential": {}}, origin=True),
    ("get", "/oauth/password"): Route(OPEN, "a reset link's page; the token is the proof", {410}),
    ("post", "/oauth/password"): Route(OPEN, "a reset link sets a password; the token is the proof", {410}, body="form"),
    ("get", "/oauth/sign-in/options"): Route(OPEN, "the sign-in screen's choices", {400}, valid={200}),
    ("post", "/oauth/sign-in/password"): Route(OPEN, "the sign-in screen's password step", {422}, body="json", origin=True),
    ("post", "/oauth/sign-in/second-factor"): Route(OPEN, "the sign-in screen's second step (a step token)", {422}, body="json", shaped={"step": "nope", "code": "000000"}, origin=True),
    ("post", "/oauth/sign-in/reset-request"): Route(OPEN, "asks for a reset link; answers alike for everyone", {422}, body="json", shaped={"identifier": "nobody"}, origin=True),
    ("get", "/oauth/sign-in/reset"): Route(OPEN, "the reset screen's state; a link token is the proof", {200}),
    ("post", "/oauth/sign-in/reset"): Route(OPEN, "a reset link sets a password; the token is the proof", {422}, body="json", shaped={"token": "nope", "password": "a long enough pass 1", "repeat": "a long enough pass 1"}, origin=True),
    ("post", "/oauth/console-token"): Route(SESSION, "the API console's token for the cookie's person", {401}, body="json", shaped={}, origin=True),
}  # fmt: skip

_COUNTED = (
    "users", "user_sessions", "session_refresh_tokens", "authorization_codes", "password_reset_links",
    "mail_outbox", "grants", "user_identities", "user_passkeys", "user_second_factors",
    "user_recovery_codes", "sign_in_steps", "provider_sign_ins", "oauth_clients", "oauth_client_secrets",
)  # fmt: skip


def _counts(world) -> dict[str, int]:
    """Rows of every table a sign-in route could change. The failures counted per name and address
    (`sign_in_failures`) are left out: slowing wrong sign-ins is their purpose."""
    from sqlalchemy import text

    with world.api.client.app.state.session_factory() as session:
        return {
            table: session.execute(text(f"select count(*) from {table}")).scalar_one()
            for table in _COUNTED
        }


def _structured(response, where: str) -> str | None:
    """What is wrong with a refusal, or None: never a `5xx`, never a traceback, and a refusal in the
    engine's shape or an HTML page."""
    text_ = response.text
    if response.status_code >= 500:
        return f"{where}: {response.status_code} {text_[:120]!r}"
    if "Traceback" in text_ or 'File "' in text_:
        return f"{where}: a traceback in the body"
    kind = response.headers.get("content-type", "")
    if response.status_code >= 400:
        if "json" in kind:
            body = response.json()
            if not (isinstance(body, dict) and "error" in body):
                return f"{where}: JSON with no `error`: {body!r:.100}"
        elif not ("html" in kind and text_.lstrip().lower().startswith("<!doctype html")):
            return f"{where}: neither the engine's shape nor a page ({kind})"
    return None


def _junk_bodies() -> list[tuple[str, dict]]:
    json_ = {"content-type": "application/json"}
    names = ("request", "username", "password", "step", "token", "identifier", "code")
    wrong = {name: [1] for name in names}
    nested = {name: {"a": 1} for name in names}
    long = "x" * 70000
    return [
        ("empty", {}),
        ("not json", {"content": "not json {", "headers": json_}),
        ("a list", {"content": "[]", "headers": json_}),
        ("null", {"content": "null", "headers": json_}),
        ("lists for text", {"content": json.dumps(wrong), "headers": json_}),
        ("objects for text", {"content": json.dumps(nested), "headers": json_}),
        ("long values", {"content": json.dumps({k: long for k in ("identifier", "token", "step", "password", "username", "ceremony", "name")}), "headers": json_}),
        ("nul and emoji", {"content": json.dumps({"identifier": "\u0000\u00e9\U0001f4a5", "token": "\u0000", "username": "\u0000", "step": "\u0000"}), "headers": json_}),
        ("deep", {"content": "[" * 50000, "headers": json_}),
        ("form", {"data": {"step": "x", "token": "y", "username": "\x00", "password": "p" * 5000, "code": "1", "grant_type": "\u0000", "client_id": "z"}}),
        ("a cookie", {"headers": {"Cookie": "oauth_refresh=" + "c" * 4000 + "; oauth_provider=junk; oauth_signed_out=//evil.example"}}),
    ]  # fmt: skip


def _junk_queries(challenge: str) -> list[dict]:
    long = "q" * 20000
    return [
        {},
        _request(challenge),  # a well-formed authorization request, so a route reads its address
        {"token": long},
        {"token": "\u0000\u00e9", "return": "https://evil.example/", "state": "s", "code": "c"},
        {"return": "//evil.example", "request": "\u0000"},
        {"return": "javascript:alert(1)", "client_id": "browser", "redirect_uri": "https://evil.example/"},
        {"return": "http://localhost:5173\\@evil.example", "response_type": "token", "code_challenge": long},
        {"error": "x", "error_description": "<script>alert(1)</script>", "iss": "https://evil.example"},
    ]  # fmt: skip


def _filled(path: str, junk: str = "nothing") -> str:
    return path.replace("{name}", junk).replace("{key}", junk)


def _location(response, where: str) -> str | None:
    """A redirect goes to one of the browser's origins or this engine, never to the address asked for."""
    if 300 <= response.status_code < 400:
        location = response.headers["location"]
        if not location.startswith(("http://localhost:5173/", "http://testserver")) or any(
            bad in location for bad in ("evil.example", "javascript:")
        ):
            return f"{where}: redirects to {location}"
    return None


@pytest.mark.journey("J47.7")
@pytest.mark.structures("R")
def test_every_route_outside_the_document_answers_as_its_class_says(world):
    """Given the application's routes. When each route outside the OpenAPI document, and each open
    route in it, is called with nothing, with a well-formed body and no credentials, with a foreign
    origin, and with junk (not JSON, a list or an object where text belongs, a list, `null`,
    70,000-character values, NUL and emoji, a cut-off deep document, a form, cookies that mean
    nothing, queries that try to redirect; and, for a route with a path parameter, five addresses
    that try to traverse, the first two junk bodies or queries each), then the table
    `CLASSIFICATION` is complete and each route answers as its class says: never `5xx`, never a
    traceback, a refusal in the engine's shape or a page, a redirect only to the browser's origins,
    no person, session, grant, link, code or message made or ended; a session-class route serves
    the person whose cookie it is and nobody else; `/metrics` is `401` with no token, `403` for a
    client holding nothing and served to one holding Operator. (A binary body is the next test's.)"""
    app = world.api.client.app
    _, open_ = operations(app)
    documented = {key for key, _ in [((m, p), 0) for m, p in OPEN_OPERATIONS]}
    outside = set()
    for route in app_routes(app):
        if route.path == CONSUMER or route.path.startswith(CONSUMER + "/"):
            continue
        for method in route.methods - {"HEAD"}:
            outside.add((method.lower(), route.path))
    spec = {(m, p) for p, ms in app.openapi()["paths"].items() for m in ms if m != "parameters"}
    outside -= spec
    assert ("get", "/metrics") in spec, "metrics is an operation of the document"
    assert set(CLASSIFICATION) == outside | documented | {("get", "/metrics")}, set(
        CLASSIFICATION
    ) ^ (outside | documented | {("get", "/metrics")})
    assert documented == set(open_) | documented  # the open routes the sweep names are the same
    assert {key for key in CLASSIFICATION if key in spec} == documented | {("get", "/metrics")}

    # A person with a session, so the counts of sessions are not zero and a route that ended or
    # copied one would show.
    person = _with_password(world, "ada", "ada@example.org")
    holder = _browser(world)
    _sign_in(holder, "ada")
    assert person["id"]

    # The session class serves the person whose cookie it is.
    own = {"Origin": str(holder.base_url).rstrip("/")}
    page = holder.get("/oauth/passkeys/new", headers=own)
    assert page.status_code == 200, page.text[:200]
    console = holder.post("/oauth/console-token", json={}, headers=own)
    assert ok(console)["access_token"]
    # A client that returns a `500` instead of raising it, so every one is listed.
    anonymous = TestClient(app, authenticated=False, raise_server_exceptions=False)
    before = _counts(world)
    assert before["user_sessions"] >= 1

    _, challenge = _pkce()
    shaped_sign_in = {"request": _request(challenge), "username": "nobody", "password": "x"}
    junk_bodies, junk_queries = _junk_bodies(), _junk_queries(challenge)
    problems: list[str] = []
    requests = 0

    def check(response, where: str, statuses=None, *, session_class: bool = False) -> None:
        for problem in (_structured(response, where), _location(response, where)):
            if problem:
                problems.append(problem)
        if (
            statuses is not None
            and response.status_code not in statuses
            and not 400 <= response.status_code < 500
        ):
            problems.append(f"{where}: {response.status_code}, expected {sorted(statuses)} or 4xx")
        if session_class and response.status_code == 200:
            problems.append(f"{where}: served without a session")

    for (method, path), route in CLASSIFICATION.items():
        if path == "/metrics":
            continue
        guarded = route.kind == SESSION or (route.kind != OPEN and method == "post")
        # Junk in the address (a path parameter) and in what is sent.
        addresses = [path]
        if "{" in path:
            addresses = [
                _filled(path, junk)
                for junk in (
                    "nothing",
                    "..%2f..%2fetc%2fpasswd",
                    "k" * 3000,
                    "%C3%A9%F0%9F%92%A5",
                    "%2e%2e%5c",
                )
            ]
        for address in addresses:
            shallow = address != path and "{" in path and address != addresses[0]
            tries = junk_queries if method == "get" else [body for _, body in junk_bodies]
            for number, kwargs in enumerate(tries[:2] if shallow else tries):
                kwargs = {key: value for key, value in kwargs.items()}
                # A post comes from the application's address, and again from the engine's own (the
                # passkey ceremonies and the console accept no other).
                for origin in (None,) if method == "get" else (APP, own):
                    request = (
                        {"params": kwargs}
                        if method == "get"
                        else {**kwargs, "headers": {**origin, **kwargs.get("headers", {})}}
                    )
                    response = anonymous.request(method, address, follow_redirects=False, **request)
                    requests += 1
                    served = route.bare | (
                        route.valid if method == "get" and number == 1 else set()
                    )
                    check(response, f"{method.upper()} {address[:50]!r} #{number}", served,
                          session_class=guarded)  # fmt: skip

        # With nothing but its address, the route answers as its class says.
        bare = anonymous.request(
            method, _filled(path), headers=own if method == "post" else {}, follow_redirects=False
        )
        check(bare, f"bare {method} {path}")
        if bare.status_code not in route.bare:
            problems.append(
                f"bare {method} {path}: {bare.status_code}, expected {sorted(route.bare)}"
            )

        # A well-formed body with no credentials is refused for want of them, and a foreign origin
        # is refused before anything is read (API.md: foreign_origin, access_denied).
        shaped = shaped_sign_in if path == "/oauth/sign-in/password" else route.shaped
        if route.origin and (shaped is not None or route.body == "form"):
            if route.body == "form":
                form = {**_request(challenge), "username": "nobody", "password": "x"}
                if path == "/oauth/second-factor":
                    form = {"step": "nope", "code": "000000"}
                send = {"data": form}
            else:
                send = {"json": shaped}
            foreign = anonymous.post(
                path, headers={"Origin": "http://evil.example"}, follow_redirects=False, **send
            )
            check(foreign, f"foreign origin {path}")
            if foreign.status_code != 403:
                problems.append(f"foreign origin {path}: {foreign.status_code}, expected 403")
            requests += 1
            if route.kind == SESSION:
                again = anonymous.post(path, headers=own, follow_redirects=False, **send)
                check(again, f"no session {path}")
                if again.status_code not in (401, 403):
                    problems.append(f"no session {path}: {again.status_code}, expected 401")
                requests += 1

    assert not problems, f"{len(problems)} problems in {requests} requests\n" + "\n".join(
        dict.fromkeys(problems[:60])
    )
    assert requests > 400, requests
    changed = {
        table: (before[table], now) for table, now in _counts(world).items() if now != before[table]
    }
    assert not changed, changed
    # Nothing above ended the person's session.
    assert holder.get("/oauth/passkeys/new", headers=own).status_code == 200

    # The consumer routes are J47.6's; with no token the index and a data route are refused.
    for path in (CONSUMER, f"{CONSUMER}/anything/v1/publications"):
        response = anonymous.get(path)
        assert response.status_code == 401, (path, response.status_code)
        assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"

    # `/metrics`: no token, a caller holding nothing, a caller holding Operator.
    refused(anonymous.get("/metrics"), 401, "AUTHENTICATION_REQUIRED")
    _, nobody = _client(world, "Metrics nobody")
    error = refused(nobody.api.client.get("/metrics"), 403, "FORBIDDEN")
    assert error["details"]["action"] == "operations.read"
    _, operator = _client(world, "Metrics operator", ("operator", {"instance": True}))
    scraped = operator.api.client.get("/metrics")
    assert scraped.status_code == 200 and scraped.headers["content-type"].startswith("text/plain")
    assert "Traceback" not in scraped.text


# The two junk kinds below are not in the case above, which would otherwise stop at them; each is a
# defect it found and 0.12 E1 fixed (findings F3 and F4).
def _json_operations(app) -> list[tuple[str, str]]:
    declared, _ = operations(app)
    return [(op.method, op.path) for op in declared if op.body == "json"]


@pytest.mark.journey("J47.7")
def test_a_binary_body_is_refused_with_422_never_500(world):
    """When every operation that reads a JSON body, and every JSON route outside the document, is
    sent bytes that are not UTF-8 as `application/octet-stream`, then each answers a `4xx` in the
    engine's shape."""
    app = world.api.client.app
    as_caller = TestClient(app, raise_server_exceptions=False)
    bare = TestClient(app, authenticated=False, raise_server_exceptions=False)
    problems, validated = [], 0
    attempts = [
        (as_caller, method, re.sub(r"{\w+}", str(uuid4()), path), {})
        for method, path in _json_operations(app)
    ] + [
        (bare, method, path, {"Origin": "http://localhost:5173"})
        for (method, path), route in CLASSIFICATION.items()
        if route.body == "json"
    ]
    for client, method, path, headers in attempts:
        response = client.request(
            method,
            path,
            content=b"\xff\xfe\x00\x01",
            headers={"content-type": "application/octet-stream", **headers},
        )
        if response.status_code >= 500:
            problems.append(f"{method.upper()} {path}: {response.status_code}")
        elif response.status_code == 422:
            # The usual shape, without the undecodable bytes echoed.
            error = response.json()["error"]
            validated += error["code"] == "REQUEST_VALIDATION_ERROR"
            if "\\ufffd" in response.text or "\ufffd" in response.text:
                problems.append(f"{method.upper()} {path}: echoes the body")
    assert validated > 50, validated
    assert not problems, f"{len(problems)} of {len(attempts)}\n" + "\n".join(problems[:10])


@pytest.mark.journey("J47.7")
def test_a_nul_byte_in_an_address_is_refused_with_4xx_never_503(world):
    """When the first path parameter of every operation that has one, and a name filter, carry a NUL
    byte, then each answers a `4xx` (`404` for an ID nobody has), not `503 DATABASE_UNAVAILABLE`."""
    app = world.api.client.app
    caller = TestClient(app, raise_server_exceptions=False)
    declared, _ = operations(app)
    problems, calls = [], 0
    outages = unavailable_counts()
    for op in declared:
        if op.method != "get" or "{" not in op.path:
            continue
        path = re.sub(r"{\w+}", "%00", op.path, count=1)
        path = re.sub(r"{\w+}", str(uuid4()), path)
        calls += 1
        if caller.get(path).status_code >= 500:
            problems.append(f"GET {path}")
    for path in ("/api/v1/clients?q=%00", "/api/v1/users?q=%00", "/oauth/providers/%00/callback"):
        calls += 1
        if caller.get(path).status_code >= 500:
            problems.append(f"GET {path}")
    # The same character in a JSON string a route stores: a client's name, a workspace's key.
    for path, body in (
        ("/api/v1/clients", {"name": "Nul \u0000 name"}),
        ("/api/v1/workspaces", {"key": "nul\u0000key", "name": "Nul"}),
    ):
        calls += 1
        response = caller.post(path, json=body)
        if not 400 <= response.status_code < 500:
            problems.append(f"POST {path}: {response.status_code}")
        else:
            assert response.json()["error"]["code"] != "DATABASE_UNAVAILABLE"
    assert calls > 50
    assert not problems, f"{len(problems)} of {calls}\n" + "\n".join(problems[:10])
    # A value the database never saw is not an outage: nothing counted.
    assert unavailable_counts() == outages


# --- J47.9 ------------------------------------------------------------------------------------------
# D420: "A second factor is not skipped". Covered by test_j46_reset_by_mail.py: the link sets the
# password once, ends the person's sessions and the old password stops working; the ask is answered
# alike for everyone, writing only to a person with an address, a local password and a kept local
# sign-in (a person with no password among them). Covered by test_j47_security_cases.py::
# test_a_provider_only_person_is_asked_for_like_a_stranger: a person who only signs in through the
# provider is answered like a stranger, and no message is queued for them. Added below: the second
# factor through a reset.


def _open_sessions(world, user_id: str) -> int:
    from sqlalchemy import text

    with world.api.client.app.state.session_factory() as session:
        return session.execute(
            text(
                "select count(*) from user_sessions s join users u on u.id = s.user_id "
                "where u.public_id = :id and s.ended_at is null"
            ),
            {"id": user_id},
        ).scalar_one()


@pytest.mark.journey("J47.9")
def test_a_reset_by_mail_does_not_skip_the_second_factor(world, smtp):  # noqa: F811
    """Given a person with a password and an authenticator app, signed in in one browser. When they
    ask for a reset by mail and set a new password through the link, then every session they had is
    ended (its token is `revoked`, its refresh cookie `invalid_grant`), the answer holds no session
    or token, the app is still on, and signing in with the new password alone, through the page and
    through the application's own sign-in, is answered with the code step and no session exists
    until a code is given: a wrong code is refused, a recovery code (once) signs in."""
    _save(world, smtp)
    ada = _with_password(world, "ada", "ada@example.org")
    first = _browser(world)
    token = _sign_in(first, "ada")
    secret, codes = _set_up(world, token)
    # A second session, signed in as the app asks: the password, then the code.
    second = _browser(world)
    verifier, challenge = _pkce()
    step = _step(_password_step(second, "ada", challenge))
    signed = _second(second, step, code=_totp(secret, ahead=1))
    other = ok(_exchange(second, _code(signed), verifier))["access_token"]
    assert _open_sessions(world, ada["id"]) == 2

    browser = _browser(world)
    assert _ask(browser, "ada")["status"] == "requested"
    assert send_mail(world) == 1
    [mail] = smtp.messages
    link = next(line for line in mail.get_content().splitlines() if "reset-password?token=" in line)
    done = browser.post(
        "/oauth/sign-in/reset",
        json={"token": _token(link), "password": SET_TO, "repeat": SET_TO},
        headers=APP_ORIGIN,
    )
    assert ok(done) == {"status": "password_set"}
    assert "set-cookie" not in done.headers, "a reset makes no session"
    assert _open_sessions(world, ada["id"]) == 0
    for old in (token, other):
        _revoked(world.api.client.get("/api/v1/me", headers=_bearer(old)))
    _invalid_grant(_renew(first))
    _invalid_grant(_renew(second))
    on = ok(world.api.get("/users", q="ada"))["items"][0]["secondFactor"]
    assert on["method"] == "authenticator-app"

    # The new password alone: the application's own sign-in answers the code step.
    _, challenge = _pkce()
    asked = browser.post(
        "/oauth/sign-in/password",
        json={"request": _request(challenge), "username": "ada", "password": SET_TO},
        headers=APP_ORIGIN,
    )
    answer = ok(asked)
    assert answer["status"] == "second_factor" and answer["stage"] == "code"
    assert "redirect" not in answer and "set-cookie" not in asked.headers
    assert _open_sessions(world, ada["id"]) == 0
    wrong = browser.post(
        "/oauth/sign-in/second-factor",
        json={"step": answer["step"], "code": "000000"},
        headers=APP_ORIGIN,
    )
    assert wrong.status_code == 401 and wrong.json()["error"] == "wrong_code"
    assert "redirect" not in wrong.json() and _open_sessions(world, ada["id"]) == 0

    # The same through the sign-in page: the password gives the code page, never a redirect.
    page_browser = _browser(world)
    verifier, challenge = _pkce()
    page = _password_step_with(page_browser, challenge)
    assert "Enter your code" in page.text
    assert _open_sessions(world, ada["id"]) == 0
    # The old password is no password, and a recovery code (once) is what signs in.
    old = page_browser.post(
        "/oauth/authorize",
        data={**_request(challenge), "username": "ada", "password": PASSWORD},
        follow_redirects=False,
    )
    assert old.status_code == 401 and _open_sessions(world, ada["id"]) == 0
    used = _second(page_browser, _step(page), recovery=codes[0])
    assert used.status_code == 303
    access = ok(_exchange(page_browser, _code(used), verifier))["access_token"]
    me = ok(world.api.client.get("/api/v1/me", headers=_bearer(access)))
    assert me["username"] == "ada" and me["signedInWith"] == "password"
    assert _open_sessions(world, ada["id"]) == 1
    again = _browser(world)
    verifier, challenge = _pkce()
    repeat = _second(again, _step(_password_step_with(again, challenge)), recovery=codes[0])
    assert repeat.status_code == 401 and _open_sessions(world, ada["id"]) == 1


def _password_step_with(browser, challenge: str):
    """The new password accepted by the sign-in page: the page that asks for more."""
    page = browser.post(
        "/oauth/authorize",
        data={**_request(challenge), "username": "ada", "password": SET_TO},
        follow_redirects=False,
    )
    assert page.status_code == 200 and "location" not in page.headers
    return page
