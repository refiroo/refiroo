"""OAuth clients and their secrets (Product 0.12 I1, D226, D253).

A secret is 32 random bytes, answered once and stored as an Argon2id hash. A new secret leaves the
client's others valid for an overlap, after which only the new one signs in (J41.3). A client is
deactivated, never deleted (D237); a deactivated client obtains no token, and the tokens it holds are
refused on their next request.
"""

import base64
import secrets
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, or_, select, update
from sqlalchemy.orm import Session

from ...common.pagination import Page, PageRequest, integer_key, paginate_statement
from ...errors import ApiError, api_error
from ...models.commands import ClientCreate, ClientSecretCreate, ClientUpdate
from ...models.database import AuditEvent, OAuthClient, OAuthClientSecret, SignInFailure
from ..authorization.administration import grant_roles
from ..reads.object_query import name_contains
from . import security_events, sign_in
from .passwords import hash_secret, verify_secret
from .principals import actors

_KEYS = (integer_key("sequenceId", OAuthClient.id, "id"),)


def _changing[T](session: Session, change: Callable[[], T]) -> T:
    try:
        result = change()
    except ApiError:
        session.rollback()
        raise
    session.commit()
    return result


def _new_secret() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()


def load_client(session: Session, public_id: str, *, for_update: bool = False) -> OAuthClient:
    statement = select(OAuthClient).where(OAuthClient.public_id == public_id)
    client = session.scalar(statement.with_for_update() if for_update else statement)
    if client is None:
        raise api_error(404, "CLIENT_NOT_FOUND", f"Client '{public_id}' not found")
    return client


def _claimed(session: Session, public_id: str, expected_version: int) -> OAuthClient:
    client = load_client(session, public_id, for_update=True)
    if client.version != expected_version:
        raise api_error(
            409,
            "VERSION_CONFLICT",
            "Client version has changed",
            {"currentVersion": client.version},
        )
    return client


def _touch(client: OAuthClient) -> None:
    client.version += 1
    client.updated_at = datetime.now(UTC)


def secrets_of(session: Session, client: OAuthClient) -> list[OAuthClientSecret]:
    """The client's secrets still valid, oldest first."""
    now = datetime.now(UTC)
    return list(
        session.scalars(
            select(OAuthClientSecret)
            .where(
                OAuthClientSecret.client_id == client.id,
                or_(OAuthClientSecret.expires_at.is_(None), OAuthClientSecret.expires_at > now),
            )
            .order_by(OAuthClientSecret.id)
        )
    )


def create_client(
    session: Session, payload: ClientCreate, *, roles: tuple[str, ...] = ()
) -> tuple[OAuthClient, str]:
    """A client and its first secret, answered once; with ``roles`` (``create_client --role``),
    holding them at the instance (Z1)."""
    secret = _new_secret()

    def change() -> OAuthClient:
        client = OAuthClient(name=payload.name, active=True, kind=payload.kind)
        session.add(client)
        session.flush()
        session.add(
            OAuthClientSecret(
                client_id=client.id, secret_hash=hash_secret(secret), hint=secret[-4:]
            )
        )
        if roles:
            grant_roles(session, "client", client.id, roles)
        session.flush()
        security_events.record(
            session, "client", client.public_id, "created", about=[client.public_id],
            details={"name": client.name, "kind": client.kind, "roles": list(roles)},
        )  # fmt: skip
        return client

    return _changing(session, change), secret


def update_client(session: Session, public_id: str, payload: ClientUpdate) -> OAuthClient:
    def change() -> OAuthClient:
        client = _claimed(session, public_id, payload.expectedVersion)
        if payload.name is not None:
            client.name = payload.name
        if payload.active is not None:
            client.active = payload.active
        _touch(client)
        fields = sorted(payload.model_fields_set - {"expectedVersion"})
        security_events.record(
            session, "client", client.public_id, "updated", about=[client.public_id],
            version=client.version,
            details=security_events.changed(fields, name=client.name, active=client.active),
        )  # fmt: skip
        return client

    return _changing(session, change)


def add_secret(
    session: Session, public_id: str, payload: ClientSecretCreate
) -> tuple[OAuthClient, OAuthClientSecret, str]:
    """A new secret; the client's other valid secrets expire after ``overlapHours``."""
    secret = _new_secret()

    def change() -> tuple[OAuthClient, OAuthClientSecret]:
        client = _claimed(session, public_id, payload.expectedVersion)
        now = datetime.now(UTC)
        ends = now + timedelta(hours=payload.overlapHours)
        session.execute(
            update(OAuthClientSecret)
            .where(
                OAuthClientSecret.client_id == client.id,
                or_(OAuthClientSecret.expires_at.is_(None), OAuthClientSecret.expires_at > ends),
            )
            .values(expires_at=ends)
        )
        added = OAuthClientSecret(
            client_id=client.id, secret_hash=hash_secret(secret), hint=secret[-4:]
        )
        session.add(added)
        _touch(client)
        session.flush()
        security_events.record(
            session, "client", client.public_id, "secret-added", about=[client.public_id],
            version=client.version,
            details={"secretId": added.public_id, "overlapHours": payload.overlapHours},
        )  # fmt: skip
        return client, added

    client, added = _changing(session, change)
    return client, added, secret


def remove_secret(session: Session, public_id: str, secret_id: str) -> OAuthClient:
    """Stop a secret at once, before its overlap ends."""

    def change() -> OAuthClient:
        client = load_client(session, public_id, for_update=True)
        removed = session.scalar(
            select(OAuthClientSecret).where(
                OAuthClientSecret.client_id == client.id,
                OAuthClientSecret.public_id == secret_id,
            )
        )
        if removed is None:
            raise api_error(
                404, "CLIENT_SECRET_NOT_FOUND", f"Client '{public_id}' has no secret '{secret_id}'"
            )
        session.execute(delete(OAuthClientSecret).where(OAuthClientSecret.id == removed.id))
        _touch(client)
        security_events.record(
            session, "client", client.public_id, "secret-removed", about=[client.public_id],
            version=client.version, details={"secretId": secret_id},
        )  # fmt: skip
        return client

    return _changing(session, change)


def creators(session: Session, public_ids: list[str]) -> dict[str, dict[str, str] | None]:
    """Who created each client, from its ``created`` security event (D349): a person or client, or
    None when made on the server (``create_client``) or before Z4."""
    if not public_ids:
        return {}
    events = list(
        session.scalars(
            select(AuditEvent).where(
                AuditEvent.aggregate_type == "client",
                AuditEvent.action == "created",
                AuditEvent.aggregate_id.in_(public_ids),
            )
        )
    )
    named = actors(session, events)
    found: dict[str, dict[str, str] | None] = {}
    for event in events:
        actor = named[event.sequence_id]
        found[event.aggregate_id] = actor if actor and actor.get("kind") != "engine" else None
    return found


def authenticate_client(
    session: Session, client_id: str, secret: str, address: str | None, now: datetime
) -> OAuthClient | sign_in.Refused:
    """The active client whose valid secret ``secret`` is, its use recorded, or why not. A wrong
    secret is counted against the client ID and the address and slows the next attempts like a
    wrong password (D271); an ID that matches no active client costs the same work as a wrong
    secret, so the time does not show which IDs exist. Commits."""
    wait = sign_in.seconds_to_wait(session, client_id, address, now, sign_in.CLIENT)
    if wait > 0:
        return sign_in.Refused("slowed", wait)
    client = session.scalar(
        select(OAuthClient).where(OAuthClient.public_id == client_id, OAuthClient.active.is_(True))
    )
    if client is None:
        sign_in.spend_verification(secret)
    else:
        for candidate in secrets_of(session, client):
            if verify_secret(secret, candidate.secret_hash):
                candidate.last_used_at = now
                client.last_used_at = now
                session.execute(
                    delete(SignInFailure).where(
                        SignInFailure.kind == f"{sign_in.CLIENT}account",
                        SignInFailure.key == client_id.strip().casefold()[:320],
                    )
                )
                session.commit()
                return client
    sign_in.record_failure(session, client_id, address, now, sign_in.CLIENT)
    session.commit()
    return sign_in.Refused("wrong")


def client_page(
    session: Session,
    *,
    q: str | None = None,
    active: bool | None,
    page: PageRequest,
    page_size: int,
    kind: str | None = None,
) -> Page[OAuthClient]:
    """Clients in the order they were created; ``q`` matches the name (D300)."""
    statement = select(OAuthClient)
    if q:
        statement = statement.where(name_contains(OAuthClient.name, q))
    if active is not None:
        statement = statement.where(OAuthClient.active.is_(active))
    if kind is not None:
        statement = statement.where(OAuthClient.kind == kind)
    return paginate_statement(
        session,
        statement,
        keys=_KEYS,
        scope="clients",
        filters={"q": q, "active": active, **({"kind": kind} if kind else {})},
        page=page,
        page_size=page_size,
        message="Client list cursor is invalid",
    )
