"""J46.11 — send mail through Microsoft 365 (USER_JOURNEYS.md § Security, 0.13 MS).

A Security administrator chooses Microsoft 365 instead of SMTP: the engine takes a token with the
client-credentials grant (a client secret, or a signed assertion of a certificate) and sends with
Microsoft Graph's ``sendMail``. The harness (``tests/graph_server.py``) stands in for the token endpoint
and Graph on ``127.0.0.1``; the settings point the token and Graph addresses at it. The outbox, the
retries and the 24 hour give-up are J46's: only what differs for this method is tested here.
"""

import datetime as dt
import json
import socket
from datetime import UTC, datetime, timedelta

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from cryptography.x509.oid import NameOID
from graph_server import FakeGraph
from scenario import ok, queue_mail, refused, send_mail
from test_j46_mail import PASSWORD, _database, _reset_mail, smtp  # noqa: F401  (smtp is a fixture)

from app.engine.identity.resealing import reseal
from app.engine.mail import graph

SECRET = "graph-client-secret-Z9"
TENANT = "11111111-2222-3333-4444-555555555555"
CLIENT = "66666666-7777-8888-9999-000000000000"
MAILBOX = "refiroo@example.org"


@pytest.fixture(autouse=True)
def _no_cached_tokens():
    graph.forget_tokens()
    yield
    graph.forget_tokens()


@pytest.fixture
def stub():
    with FakeGraph(secret=SECRET) as server:
        yield server


def _certificate(*, days: int = 365, key=None) -> tuple[str, bytes]:
    """A key and a self-signed certificate as one PEM text, and the certificate's own PEM."""
    key = key or rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "refiroo mail")])
    now = dt.datetime.now(dt.UTC)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(days=30))
        .not_valid_after(now + dt.timedelta(days=days))
        .sign(key, hashes.SHA256())
    )
    pem = certificate.public_bytes(serialization.Encoding.PEM)
    private = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    return (private + pem).decode(), pem


def _settings(stub: FakeGraph, **changes) -> dict:
    return {
        "method": "microsoft365",
        "tenantId": TENANT,
        "clientId": CLIENT,
        "clientSecret": SECRET,
        "authorityUrl": stub.url,
        "graphUrl": stub.url,
        "fromAddress": MAILBOX,
        **changes,
    }


def _save(world, stub: FakeGraph, **changes) -> dict:
    return ok(world.api.put("/mail-settings", _settings(stub, **changes)))


@pytest.mark.journey("J46.11")
def test_microsoft365_is_set_up_and_a_test_and_a_reset_mail_reach_graph(world, stub):
    """Given an instance with no mail settings, when the administrator saves Microsoft 365 with a
    client secret, then the settings are answered without the secret, a test message and a queued
    reset message reach Graph as the saved mailbox with the same text and HTML as through SMTP, its
    MIME with CRLF line ends (with a bare LF Exchange delivers the message empty), one token serves
    both, and the change is a security event that never holds the secret."""
    saved = _save(world, stub, applicationUrl="https://refiroo.example.org")
    assert saved["configured"] is True and saved["method"] == "microsoft365"
    assert saved["tenantId"] == TENANT and saved["clientId"] == CLIENT
    assert saved["clientSecretSet"] is True and saved["certificateThumbprint"] is None
    assert saved["fromAddress"] == MAILBOX and saved["authorityUrl"] == stub.url
    assert saved["host"] is None and saved["passwordSet"] is False
    assert SECRET not in json.dumps(ok(world.api.get("/mail-settings")))

    assert ok(world.api.post("/mail-settings/test", {"to": "ada@example.org"})) == {
        "sentTo": "ada@example.org"
    }
    queue_mail(world, "ada@example.org", _reset_mail())
    assert send_mail(world) == 1
    assert len(stub.messages) == 2 and stub.mailboxes == [MAILBOX, MAILBOX]
    test_mail, reset = stub.messages
    assert test_mail["From"] == MAILBOX and test_mail["To"] == "ada@example.org"
    assert "test message" in test_mail["Subject"]
    assert "https://refiroo.example.org" in test_mail.get_body(("html",)).get_content()
    assert reset["To"] == "ada@example.org" and reset["Subject"].startswith("Choose a new")
    assert "Hello Ada" in reset.get_body(("plain",)).get_content()
    assert "<html" in reset.get_body(("html",)).get_content().lower()
    for mime in stub.raw_messages:
        assert b"\r\n" in mime and b"\n" not in mime.replace(b"\r\n", b"")
    assert stub.tokens_issued == 1
    [token_request, *_] = [r for r in stub.requests if r[1].endswith("/token")]
    assert token_request[3]["scope"] == f"{stub.url}/.default"
    assert token_request[3]["grant_type"] == "client_credentials"
    sends = [r for r in stub.requests if r[1].endswith("/sendMail")]
    assert sends[0][2]["content-type"] == "text/plain"
    assert ok(world.api.get("/mail-outbox", status="sent"))["items"]

    app = world.api.client.app
    with app.state.session_factory() as session:
        key = app.state.identity_settings.encryption_key
        assert reseal(session, key, key, check_only=True)["Microsoft 365 client secret"] == 1

    events = ok(world.api.get("/security-events", aggregateType="mail-settings"))["items"]
    assert [(e["action"], e["aggregateId"]) for e in events] == [("created", "mail")]
    assert "clientSecret" in events[0]["details"]["changedFields"]
    assert SECRET not in json.dumps(events)


@pytest.mark.journey("J46.11")
def test_a_refused_token_is_a_server_wide_login_failure_an_administrator_can_act_on(world, stub):
    """Given Microsoft 365 settings and Entra refusing the secret, when the test message is sent,
    then it is refused with kind `login` and a sentence that names the cause without the secret or
    Entra's text; when three queued messages are sent, the first request's failure is shared by all
    three and Entra was asked once."""
    _save(world, stub)
    stub.token_refusal = (401, 7000215)
    error = refused(
        world.api.post("/mail-settings/test", {"to": "ada@example.org"}), 422, "MAIL_SEND_FAILED"
    )
    assert error["details"]["kind"] == "login" and "client secret" in error["message"]
    assert "AADSTS7000215" in error["message"]
    assert SECRET not in error["message"] and "secret-trace" not in error["message"]

    start = datetime.now(UTC)
    before = len(stub.requests)
    for _ in range(3):
        queue_mail(world, "ada@example.org", _reset_mail(), now=start)
    assert send_mail(world, start) == 3
    assert len(stub.requests) - before == 1
    pending = ok(world.api.get("/mail-outbox", status="pending"))["items"]
    assert [m["lastErrorKind"] for m in pending] == ["login"] * 3
    assert all(m["attempts"] == 1 for m in pending)
    assert stub.messages == []

    stub.token_refusal = None
    assert send_mail(world, start + timedelta(seconds=30)) == 3
    assert len(stub.messages) == 3


@pytest.mark.journey("J46.11")
def test_graph_throttling_is_waited_out_and_a_missing_mailbox_fails_for_good(world, stub):
    """Given Graph answering 429 with Retry-After 600, when a message is sent, then it waits at
    least 600 seconds (not the usual 30) and goes once Graph accepts; a 403 is a `login` failure
    naming the permission and the access policy; a mailbox Graph does not know waits, as with SMTP."""
    _save(world, stub)
    start = datetime.now(UTC)
    queue_mail(world, "ada@example.org", _reset_mail(), now=start)
    stub.send_answer = (429, {"Retry-After": "600"})
    assert send_mail(world, start) == 1
    [waiting] = ok(world.api.get("/mail-outbox", status="pending"))["items"]
    assert waiting["lastErrorKind"] == "connection" and "429" in waiting["lastError"]
    assert "raw Graph text" not in waiting["lastError"]
    assert datetime.fromisoformat(waiting["nextAttemptAt"]) == start + timedelta(seconds=600)
    assert send_mail(world, start + timedelta(seconds=599)) == 0

    stub.send_answer = None
    assert send_mail(world, start + timedelta(seconds=600)) == 1
    assert len(stub.messages) == 1

    stub.send_answer = (403, {})
    error = refused(
        world.api.post("/mail-settings/test", {"to": "ada@example.org"}), 422, "MAIL_SEND_FAILED"
    )
    assert error["details"]["kind"] == "login"
    assert "Mail.Send" in error["message"] and "access policy" in error["message"]

    stub.send_answer = (404, {})
    held = queue_mail(world, "ada@example.org", _reset_mail(), now=start)
    assert send_mail(world, start + timedelta(seconds=601)) == 1
    pending = {m["id"]: m for m in ok(world.api.get("/mail-outbox", status="pending"))["items"]}
    assert pending[held]["lastErrorKind"] == "sender" and MAILBOX in pending[held]["lastError"]
    assert pending[held]["nextAttemptAt"] is not None


@pytest.mark.journey("J46.11")
def test_a_certificate_signs_the_assertion_and_is_answered_by_its_thumbprint(world):
    """Given a certificate with its private key, when the administrator saves it instead of a
    secret, then the answer shows its thumbprint and expiry and never the key, the engine signs an
    assertion the token endpoint verifies with the certificate (RS256, the certificate's
    thumbprint in the header, the client as issuer), and mail is sent; a key that is not RSA, one
    without a certificate and an expired certificate are each refused at `certificate`."""
    text, certificate = _certificate()
    with FakeGraph(certificate=certificate) as stub:
        saved = _save(world, stub, clientSecret=None, certificate=text)
        assert saved["clientSecretSet"] is False and saved["method"] == "microsoft365"
        assert len(saved["certificateThumbprint"]) == 40 and saved["certificateExpiresAt"]
        assert "PRIVATE KEY" not in json.dumps(ok(world.api.get("/mail-settings")))
        assert _database(world, "SELECT ms_certificate IS NOT NULL FROM mail_settings") == [(True,)]

        ok(world.api.post("/mail-settings/test", {"to": "ada@example.org"}))
        assert len(stub.messages) == 1
        [signed] = stub.assertions
        assert signed["header"]["alg"] == "RS256" and signed["header"]["x5t#S256"]
        assert signed["claims"]["iss"] == signed["claims"]["sub"] == CLIENT
        assert signed["claims"]["jti"] and signed["claims"]["exp"] > signed["claims"]["nbf"]

        kept = ok(
            world.api.put(
                "/mail-settings",
                {**_settings(stub, clientSecret=None), "expectedVersion": saved["version"]},
            )
        )
        assert kept["version"] == saved["version"]
        assert kept["certificateThumbprint"] == saved["certificateThumbprint"]

        for bad, why in (
            (_certificate(key=ec.generate_private_key(ec.SECP256R1()))[0], "RSA"),
            (text.split("-----BEGIN CERTIFICATE")[0], "no certificate"),
            (_certificate(days=-1)[0], "expired"),
            ("not a pem", "no private key"),
        ):
            error = refused(
                world.api.put(
                    "/mail-settings",
                    {
                        **_settings(stub, clientSecret=None, certificate=bad),
                        "expectedVersion": saved["version"],
                    },
                ),
                422,
                "MAIL_CERTIFICATE_INVALID",
            )
            assert error["details"] == {"field": "certificate"}, why
            assert "PRIVATE KEY" not in error["message"]


@pytest.mark.journey("J46.11")
def test_switching_the_method_replaces_the_other_methods_fields(world, stub, smtp):  # noqa: F811
    """Given Microsoft 365 saved, when the administrator saves SMTP, then the Microsoft 365 fields
    and secret are gone; the other method's fields in a request, a missing credential and a
    credential for another application are refused at their field; switching back needs the
    credential again."""
    first = _save(world, stub)
    pointer = refused(
        world.api.put(
            "/mail-settings",
            {**_settings(stub), "host": "127.0.0.1", "expectedVersion": first["version"]},
        ),
        422,
        "REQUEST_VALIDATION_ERROR",
    )
    assert "host" in json.dumps(pointer["details"])
    missing = refused(
        world.api.put(
            "/mail-settings",
            {**_settings(stub, clientSecret=None, clientId="other"), "expectedVersion": 1},
        ),
        422,
        "MAIL_CREDENTIAL_REQUIRED",
    )
    assert missing["details"] == {"field": "clientSecret"}
    refused(
        world.api.put("/mail-settings", {**_settings(stub), "authorityUrl": "http://example.org"}),
        422,
        "REQUEST_VALIDATION_ERROR",
    )

    smtp_settings = {
        "method": "smtp",
        "host": "127.0.0.1",
        "port": smtp.port,
        "security": "starttls",
        "username": "mailer",
        "password": PASSWORD,
        "fromAddress": "refiroo@example.org",
        "expectedVersion": first["version"],
    }
    switched = ok(world.api.put("/mail-settings", smtp_settings))
    assert switched["method"] == "smtp" and switched["passwordSet"] is True
    assert switched["tenantId"] is None and switched["clientId"] is None
    assert switched["clientSecretSet"] is False and switched["authorityUrl"] is None
    assert _database(
        world,
        "SELECT ms_tenant_id, ms_client_secret, ms_certificate, ms_graph_url FROM mail_settings",
    ) == [(None, None, None, None)]
    events = ok(world.api.get("/security-events", aggregateType="mail-settings"))["items"]
    assert "method" in events[0]["details"]["changedFields"]
    assert SECRET not in json.dumps(events)

    back = refused(
        world.api.put(
            "/mail-settings",
            {**_settings(stub, clientSecret=None), "expectedVersion": switched["version"]},
        ),
        422,
        "MAIL_CREDENTIAL_REQUIRED",
    )
    assert back["details"] == {"field": "clientSecret"}


def _identity_settings(stub: FakeGraph, **changes) -> dict:
    """Managed identity in the organisation's own tenant (no tenant, no application, no secret)."""
    return {
        "method": "microsoft365",
        "identityMode": "direct",
        "authorityUrl": stub.url,
        "graphUrl": stub.url,
        "fromAddress": MAILBOX,
        **changes,
    }


@pytest.mark.journey("J46.11")
def test_a_managed_identity_sends_with_the_hosts_own_token_and_no_tenant_request(
    world, monkeypatch
):
    """Given Azure App Service or Container Apps (`IDENTITY_ENDPOINT`), when the administrator saves a
    direct managed identity with a user-assigned client ID, then no secret is stored, the host is
    asked for a Graph token with its header and the client ID, mail is sent with that token and the
    tenant token endpoint is never called; a virtual machine's metadata service works the same, for
    the system-assigned identity (no client ID asked for)."""
    with FakeGraph() as stub:
        monkeypatch.setenv("IDENTITY_ENDPOINT", f"{stub.url}/identity")
        monkeypatch.setenv("IDENTITY_HEADER", stub.identity_header)
        saved = ok(
            world.api.put("/mail-settings", _identity_settings(stub, identityClientId="uai-0001"))
        )
        assert saved["credential"] == "managedIdentity" and saved["identityMode"] == "direct"
        assert saved["identityClientId"] == "uai-0001"
        assert saved["tenantId"] is None and saved["clientId"] is None
        assert saved["clientSecretSet"] is False and saved["certificateThumbprint"] is None
        assert _database(world, "SELECT ms_client_secret, ms_certificate FROM mail_settings") == [
            (None, None)
        ]

        ok(world.api.post("/mail-settings/test", {"to": "ada@example.org"}))
        queue_mail(world, "ada@example.org", _reset_mail())
        assert send_mail(world) == 1
        assert len(stub.messages) == 2 and stub.tokens_issued == 0
        assert not [r for r in stub.requests if r[1].endswith("/token")]
        [(path, query, headers)] = stub.host_requests
        assert path == "/identity" and query["client_id"] == "uai-0001"
        assert query["resource"] == stub.url and query["api-version"] == "2019-08-01"
        assert headers["x-identity-header"] == stub.identity_header

        monkeypatch.delenv("IDENTITY_ENDPOINT")
        monkeypatch.delenv("IDENTITY_HEADER")
        monkeypatch.setattr(graph, "IMDS_URL", f"{stub.url}/metadata/identity/oauth2/token")
        graph.forget_tokens()
        version = saved["version"]
        ok(
            world.api.put(
                "/mail-settings", {**_identity_settings(stub), "expectedVersion": version}
            )
        )
        ok(world.api.post("/mail-settings/test", {"to": "ada@example.org"}))
        path, query, headers = stub.host_requests[-1]
        assert path == "/metadata/identity/oauth2/token" and "client_id" not in query
        assert headers["metadata"] == "true" and query["api-version"] == "2018-02-01"
        assert len(stub.messages) == 3

        events = ok(world.api.get("/security-events", aggregateType="mail-settings"))["items"]
        assert "identityMode" in json.dumps(events) and "uai-0001" in json.dumps(events)


@pytest.mark.journey("J46.11")
def test_a_federated_managed_identity_is_the_assertion_of_the_tenant_token_request(
    world, monkeypatch
):
    """Given refiroo hosted in another tenant, when the administrator saves a federated managed
    identity (the identity's client ID, the app's client ID, the customer's tenant), then the host
    is asked for a token for the token-exchange audience, that token is the `client_assertion` of the
    client-credentials grant at the customer's tenant, and mail is sent with the token that returns;
    the audience follows the cloud; missing fields are refused at their own field."""
    with FakeGraph(federated=True) as stub:
        monkeypatch.setenv("IDENTITY_ENDPOINT", f"{stub.url}/identity")
        monkeypatch.setenv("IDENTITY_HEADER", stub.identity_header)
        body = _identity_settings(
            stub, identityMode="federated", identityClientId="uai-0002", clientId=CLIENT,
            tenantId=TENANT,
        )  # fmt: skip
        saved = ok(world.api.put("/mail-settings", body))
        assert saved["credential"] == "managedIdentity" and saved["identityMode"] == "federated"
        assert saved["tenantId"] == TENANT and saved["clientId"] == CLIENT

        ok(world.api.post("/mail-settings/test", {"to": "ada@example.org"}))
        assert len(stub.messages) == 1 and stub.tokens_issued == 1
        [(_, query, _headers)] = stub.host_requests
        assert query["resource"] == "api://AzureADTokenExchange"
        assert query["client_id"] == "uai-0002"
        [request] = [r for r in stub.requests if r[1].endswith("/token")]
        assert request[1] == f"/{TENANT}/oauth2/v2.0/token"
        form = request[3]
        assert form["client_assertion"].startswith("identity-token-")
        assert form["client_assertion_type"].endswith("jwt-bearer")
        assert form["client_id"] == CLIENT and "client_secret" not in form

        assert graph.exchange_audience("https://login.microsoftonline.us") == (
            "api://AzureADTokenExchangeUSGov"
        )
        assert graph.exchange_audience("https://login.partner.microsoftonline.cn") == (
            "api://AzureADTokenExchangeChina"
        )

        for missing in ("identityClientId", "clientId", "tenantId"):
            error = refused(
                world.api.put(
                    "/mail-settings",
                    {**{k: v for k, v in body.items() if k != missing}, "expectedVersion": 1},
                ),
                422,
                "REQUEST_VALIDATION_ERROR",
            )
            assert missing in json.dumps(error["details"])
        direct_with_tenant = _identity_settings(stub, tenantId=TENANT, expectedVersion=1)
        refused(
            world.api.put("/mail-settings", direct_with_tenant), 422, "REQUEST_VALIDATION_ERROR"
        )
        both = {**body, "clientSecret": SECRET, "expectedVersion": 1}
        refused(world.api.put("/mail-settings", both), 422, "REQUEST_VALIDATION_ERROR")


@pytest.mark.journey("J46.11")
def test_without_an_azure_host_a_managed_identity_is_a_shared_login_failure_and_switching_clears(
    world, stub, monkeypatch
):
    """Given a managed identity saved where no Azure host answers, when mail is sent, then the test
    message and every waiting message fail as `login` with a sentence that says refiroo is not
    running with a managed identity; switching to a client secret and back to a managed identity
    clears each other's fields, and the secret is asked for again."""
    monkeypatch.delenv("IDENTITY_ENDPOINT", raising=False)
    monkeypatch.delenv("IDENTITY_HEADER", raising=False)
    with socket.socket() as closed:
        closed.bind(("127.0.0.1", 0))
        unused = closed.getsockname()[1]
    monkeypatch.setattr(graph, "IMDS_URL", f"http://127.0.0.1:{unused}/metadata")
    first = ok(world.api.put("/mail-settings", _identity_settings(stub)))
    error = refused(
        world.api.post("/mail-settings/test", {"to": "ada@example.org"}), 422, "MAIL_SEND_FAILED"
    )
    assert error["details"]["kind"] == "login"
    assert "not running with a managed identity on an Azure host" in error["message"]

    start = datetime.now(UTC)
    for _ in range(3):
        queue_mail(world, "ada@example.org", _reset_mail(), now=start)
    assert send_mail(world, start) == 3
    pending = ok(world.api.get("/mail-outbox", status="pending"))["items"]
    assert [m["lastErrorKind"] for m in pending] == ["login"] * 3
    assert "managed identity" in pending[0]["lastError"]

    secret = ok(
        world.api.put("/mail-settings", {**_settings(stub), "expectedVersion": first["version"]})
    )
    assert secret["credential"] == "secret" and secret["identityMode"] is None
    assert secret["identityClientId"] is None
    back = ok(
        world.api.put(
            "/mail-settings",
            {**_identity_settings(stub, identityClientId="uai-3"), "expectedVersion": 2},
        )
    )
    assert back["credential"] == "managedIdentity" and back["clientSecretSet"] is False
    assert _database(
        world, "SELECT ms_client_secret, ms_tenant_id, ms_client_id FROM mail_settings"
    ) == [(None, None, None)]
    refused(
        world.api.put(
            "/mail-settings",
            {**_settings(stub, clientSecret=None), "expectedVersion": back["version"]},
        ),
        422,
        "MAIL_CREDENTIAL_REQUIRED",
    )
