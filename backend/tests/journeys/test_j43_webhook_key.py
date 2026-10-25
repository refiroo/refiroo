"""J43.3–J43.5 — Rotate a webhook's signing key, and re-seal the engine's secrets (0.12 K1).

A rotation answers a new key once. For the overlap, a delivery is signed with both keys and a
receiver accepts it when either verifies; afterwards, or at once with an overlap of 0, only the new
key signs, so the old one stops verifying. Re-sealing runs as the command an operator runs, against
the journey's database: every sealed secret moves to a new ``SECRETS_ENCRYPTION_KEY`` or, if one does
not open, none does. Each case runs on two configurations through the public API.
"""

import base64
import hashlib
import hmac
import os
import secrets
import subprocess
import sys
from datetime import UTC, datetime, timedelta

import pytest
from harness_identity import TestClient, request_token
from scenario import derive_events, dispatch, ok, refused
from service import BACKEND, render
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
from test_j30_consumer_events import LEDGER, _activate, _workspace
from test_j30_delivery import Receiver, _read, _subscribe
from test_j30_subscriptions import PATH, SUBSCRIPTIONS

from app.common.sealing import unseal

OVERLAP = timedelta(hours=24)


@pytest.fixture
def receiver():
    with Receiver() as running:
        yield running


def _now() -> datetime:
    return datetime.now(UTC)


def _rotate(world, subscription, **body):
    current = _read(world, subscription)
    return world.api.post(
        f"{PATH}/{current['id']}/rotate-secret", {"expectedVersion": current["version"], **body}
    )


def _signatures(request) -> list[str]:
    return request["headers"]["rdm-signature"].split(",")


def _verifies(secret: str, request) -> bool:
    """What a receiver does: the request is genuine when any signature in the list verifies."""
    timestamp = request["headers"]["rdm-timestamp"]
    digest = hmac.new(secret.encode(), timestamp.encode() + b"." + request["raw"], hashlib.sha256)
    return f"sha256={digest.hexdigest()}" in _signatures(request)


def _send_one(world, workspace, name, at=None):
    world.made("R", name, workspace=workspace)
    derive_events(world)
    dispatch(world, at)


@pytest.mark.journey("J43.3")
@pytest.mark.settings(**SUBSCRIPTIONS)
@pytest.mark.structures(*LEDGER)
def test_a_rotated_webhook_key_signs_beside_the_old_one_for_the_overlap_and_alone_after(
    world, receiver
):
    """Given a subscription delivering. When its key is rotated with the default overlap. Then the
    answer holds a new key once, no read shows it, the subscription's version moves and it names
    when the overlap ends. A delivery during the overlap lists two signatures, the new key's first,
    and either key verifies it. A delivery after the overlap lists one, the new key's, and the old
    key no longer verifies it. A second rotation inside an overlap ends the first key's at once."""
    _activate(world, "events")
    ws = _workspace(world)
    created = _subscribe(world, ws, receiver.url)
    first = created["signingSecret"]

    rotated = ok(_rotate(world, created))
    second = rotated["signingSecret"]
    assert second.startswith("rdmwh_") and second != first
    assert rotated["version"] == created["version"] + 1
    assert rotated["signingKeyCreatedAt"] >= created["signingKeyCreatedAt"]
    ends = datetime.fromisoformat(rotated["previousSigningKeyExpiresAt"])
    assert abs(ends - (_now() + OVERLAP)) < timedelta(minutes=1)
    read = _read(world, rotated)
    assert (
        "signingSecret" not in read
        and read["previousSigningKeyExpiresAt"] == rotated["previousSigningKeyExpiresAt"]
    )

    _send_one(world, ws, "Ledger During")
    (during,) = receiver.requests
    assert len(_signatures(during)) == 2
    assert _verifies(second, during) and _verifies(first, during)

    after = _now() + OVERLAP + timedelta(hours=1)
    _send_one(world, ws, "Ledger After", after)
    last = receiver.requests[-1]
    assert len(_signatures(last)) == 1
    assert _verifies(second, last) and not _verifies(first, last)

    third = ok(_rotate(world, _read(world, rotated), overlapHours=168))["signingSecret"]
    fourth = ok(_rotate(world, _read(world, rotated), overlapHours=1))["signingSecret"]
    _send_one(world, ws, "Ledger Twice")
    twice = receiver.requests[-1]
    assert _verifies(fourth, twice) and _verifies(third, twice)
    assert not _verifies(second, twice) and not _verifies(first, twice)


@pytest.mark.journey("J43.4")
@pytest.mark.settings(**SUBSCRIPTIONS)
@pytest.mark.structures(*LEDGER)
def test_a_webhook_key_rotated_at_once_stops_verifying_with_the_next_delivery_even_a_retry(
    world, receiver
):
    """Given a subscription whose receiver is failing, with a batch waiting to be retried. When
    the key is rotated with an overlap of 0 (a leaked key). Then the subscription names no overlap,
    and the retry of the waiting batch, the same delivery, is signed with the new key alone: the
    old key does not verify it. Rotating a suspended subscription works and leaves it suspended."""
    _activate(world, "events")
    ws = _workspace(world)
    created = _subscribe(world, ws, receiver.url)
    leaked = created["signingSecret"]
    receiver.answer(503)
    now = _now()
    _send_one(world, ws, "Ledger First", now)
    (failed,) = receiver.requests
    assert _verifies(leaked, failed)

    rotated = ok(_rotate(world, created, overlapHours=0))
    assert rotated["previousSigningKeyExpiresAt"] is None
    assert rotated["delivery"]["pending"]["attempts"] == 1
    receiver.answer(200)
    dispatch(world, now + timedelta(minutes=1))
    retry = receiver.requests[-1]
    assert retry["headers"]["rdm-delivery-id"] == failed["headers"]["rdm-delivery-id"]
    assert len(_signatures(retry)) == 1
    assert _verifies(rotated["signingSecret"], retry) and not _verifies(leaked, retry)

    current = _read(world, rotated)
    suspended = ok(
        world.api.post(f"{PATH}/{current['id']}/suspend", {"expectedVersion": current["version"]})
    )
    again = ok(_rotate(world, suspended, overlapHours=0))
    assert again["status"] == "suspended" and again["signingSecret"] != rotated["signingSecret"]


@pytest.mark.journey("J43.3", "J43.4")
@pytest.mark.settings(**SUBSCRIPTIONS)
@pytest.mark.structures(*LEDGER)
def test_a_rotation_is_refused_for_a_stale_version_an_unknown_subscription_and_a_reader(
    world, receiver
):
    """Given a subscription. When it is rotated with a version already moved on, an overlap past a
    week or a negative one, or an unknown ID, or by a client that only reads the workspace. Then each
    is refused with its code and the key does not change: a delivery is signed with the first key."""
    _activate(world, "events")
    ws = _workspace(world)
    created = _subscribe(world, ws, receiver.url)
    key = created["signingSecret"]
    ok(_rotate(world, created, overlapHours=1))
    stale = world.api.post(
        f"{PATH}/{created['id']}/rotate-secret", {"expectedVersion": created["version"]}
    )
    assert (
        refused(stale, 409, "VERSION_CONFLICT")["details"]["currentVersion"]
        == created["version"] + 1
    )
    current = _read(world, created)
    for overlap in (169, -1):
        response = _rotate(world, current, overlapHours=overlap)
        assert response.status_code == 422, response.text
    refused(
        world.api.post(f"{PATH}/{uuid_text()}/rotate-secret", {"expectedVersion": 1}),
        404,
        "SUBSCRIPTION_NOT_FOUND",
    )

    client = ok(world.api.post("/clients", {"name": "Reader"}), 201)
    principal = {"kind": "client", "id": client["id"]}
    ok(
        world.api.post(
            "/grants", {"principal": principal, "role": "reader", "scope": {"workspaceKey": ws}}
        ),
        201,
    )
    anonymous = TestClient(world.api.client.app, authenticated=False)
    token = ok(request_token(anonymous.post, client["id"], client["secret"]))["access_token"]
    forbidden = anonymous.post(
        f"/api/v1{PATH}/{current['id']}/rotate-secret",
        json={"expectedVersion": current["version"]},
        headers={"Authorization": f"Bearer {token}"},
    )
    refused(forbidden, 403, "FORBIDDEN")
    after = _read(world, current)
    assert after["version"] == current["version"]
    # Only the rotation with an overlap of one hour happened, and it left the first key signing.
    _send_one(world, ws, "Ledger Check")
    (request,) = receiver.requests
    assert _verifies(key, request)


def uuid_text() -> str:
    from uuid import uuid4

    return str(uuid4())


def _reseal(world, *arguments: str, key: str | None = None, new: str | None = None):
    environment = {**os.environ, "DATABASE_URL": render(world.database)}
    if key is not None:
        environment["SECRETS_ENCRYPTION_KEY"] = key
    if new is not None:
        environment["NEW_SECRETS_ENCRYPTION_KEY"] = new
    return subprocess.run(
        [sys.executable, "-m", "app.cli.reseal_secrets", *arguments],
        cwd=BACKEND,
        env=environment,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def _new_key() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()


def _sealed(world, column: str, table: str = "consumer_subscriptions") -> list[bytes]:
    engine = create_engine(world.database, poolclass=NullPool)
    try:
        with engine.connect() as connection:
            rows = connection.execute(text(f"SELECT {column} FROM {table} ORDER BY 1"))
            return [bytes(row[0]) for row in rows if row[0] is not None]
    finally:
        engine.dispose()


@pytest.mark.journey("J43.5")
@pytest.mark.settings(**SUBSCRIPTIONS)
@pytest.mark.structures(*LEDGER)
def test_every_sealed_secret_is_resealed_under_a_new_key_or_none_is(world, receiver):
    """Given an instance with a subscription rotated with an overlap and a token signing key. When
    the re-sealing command is run with the wrong current key, then it names the values that do not
    open, exits 1 and changes nothing. When it is run with the new key equal to the current one, it
    refuses. When `--check` is run, it proves every value opens and changes nothing. When it is run
    with a new key, then it exits 0 and counts what it re-sealed, the stored signing keys open
    under the new key to the secrets the API answered, and no longer under the old one."""
    _activate(world, "events")
    ws = _workspace(world)
    created = _subscribe(world, ws, receiver.url)
    rotated = ok(_rotate(world, created))
    old = os.environ["SECRETS_ENCRYPTION_KEY"]
    before = (_sealed(world, "signing_key"), _sealed(world, "private_key", "token_signing_keys"))

    wrong = _reseal(world, key=_new_key(), new=_new_key())
    assert wrong.returncode == 1, wrong.stderr
    assert "do not open" in wrong.stderr and "token signing key" in wrong.stderr
    assert "webhook signing key" in wrong.stderr and rotated["id"] in wrong.stderr
    assert rotated["signingSecret"] not in wrong.stdout + wrong.stderr
    same = _reseal(world, new=old)
    assert same.returncode == 2 and "current key" in same.stderr
    missing = _reseal(world)
    assert missing.returncode == 2 and "NEW_SECRETS_ENCRYPTION_KEY" in missing.stderr
    checked = _reseal(world, "--check")
    assert checked.returncode == 0, checked.stderr
    assert "previous webhook signing key" in checked.stdout
    assert (
        _sealed(world, "signing_key"),
        _sealed(world, "private_key", "token_signing_keys"),
    ) == before

    new = _new_key()
    done = _reseal(world, new=new)
    assert done.returncode == 0, done.stderr
    assert "previous webhook signing key" in done.stdout and "token signing key" in done.stdout

    context = created["id"].encode()
    [current] = _sealed(world, "signing_key")
    [previous] = _sealed(world, "previous_signing_key")
    new_bytes = base64.urlsafe_b64decode(new)
    assert _text(unseal(new_bytes, current, context)) == rotated["signingSecret"]
    assert _text(unseal(new_bytes, previous, context)) == created["signingSecret"]
    stale = _reseal(world, "--check")
    assert stale.returncode == 1 and "do not open" in stale.stderr
    assert _reseal(world, "--check", key=new).returncode == 0
    # The engine, stopped for the re-sealing, starts with the new key: a second re-sealing back
    # to the old one is the same move, and it too opens every value.
    back = _reseal(world, key=new, new=old)
    assert back.returncode == 0, back.stderr
    assert _reseal(world, "--check").returncode == 0


def _text(key: bytes) -> str:
    return "rdmwh_" + base64.urlsafe_b64encode(key).decode().rstrip("=")
