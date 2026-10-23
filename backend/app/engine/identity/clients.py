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

from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from ...common.pagination import Page, PageRequest, integer_key, paginate_statement
from ...errors import ApiError, api_error
from ...models.commands import ClientCreate, ClientSecretCreate, ClientUpdate
from ...models.database import OAuthClient, OAuthClientSecret
from .passwords import hash_secret, verify_secret

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


def create_client(session: Session, payload: ClientCreate) -> tuple[OAuthClient, str]:
    """A client and its first secret, answered once."""
    secret = _new_secret()

    def change() -> OAuthClient:
        client = OAuthClient(name=payload.name, active=True)
        session.add(client)
        session.flush()
        session.add(OAuthClientSecret(client_id=client.id, secret_hash=hash_secret(secret)))
        session.flush()
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
        added = OAuthClientSecret(client_id=client.id, secret_hash=hash_secret(secret))
        session.add(added)
        _touch(client)
        session.flush()
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
        session.delete(removed)
        _touch(client)
        return client

    return _changing(session, change)


def authenticate_client(session: Session, client_id: str, secret: str) -> OAuthClient | None:
    """The active client whose valid secret ``secret`` is, its use recorded; none otherwise."""
    client = session.scalar(
        select(OAuthClient).where(OAuthClient.public_id == client_id, OAuthClient.active.is_(True))
    )
    if client is None:
        return None
    for candidate in secrets_of(session, client):
        if verify_secret(secret, candidate.secret_hash):
            now = datetime.now(UTC)
            candidate.last_used_at = now
            client.last_used_at = now
            session.commit()
            return client
    return None


def client_page(
    session: Session, *, active: bool | None, page: PageRequest, page_size: int
) -> Page[OAuthClient]:
    """Clients in the order they were created."""
    statement = select(OAuthClient)
    if active is not None:
        statement = statement.where(OAuthClient.active.is_(active))
    return paginate_statement(
        session,
        statement,
        keys=_KEYS,
        scope="clients",
        filters={"active": active},
        page=page,
        page_size=page_size,
        message="Client list cursor is invalid",
    )
