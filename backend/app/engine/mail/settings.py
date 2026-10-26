"""The SMTP settings an administrator saves (Product 0.12 M1, D419, D422).

One row, absent until mail is set up. The password is sealed with ``SECRETS_ENCRYPTION_KEY`` (D253)
and never answered. Without a row no mail is sent and nothing else changes (``MAIL_NOT_SET_UP``).
Saving, changing and removing the settings are security events: they decide where one-time links go.
"""

from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ...common.sealing import seal, unseal
from ...errors import ApiError, api_error
from ...models.commands import MailSettingsUpdate
from ...models.database import MailSettings
from ..identity import security_events
from ..identity.settings import IdentitySettings
from .smtp import NONE, Connection

AGGREGATE = "mail-settings"
# The one setting's identity in a security event.
EVENT_ID = "mail"


def password_context(identity: str = "password") -> bytes:
    return b"mail-settings:" + identity.encode()


def load(session: Session, *, for_update: bool = False) -> MailSettings | None:
    statement = select(MailSettings).where(MailSettings.id == 1)
    return session.scalar(statement.with_for_update() if for_update else statement)


def require(session: Session) -> MailSettings:
    """The saved settings, or ``409 MAIL_NOT_SET_UP``."""
    row = load(session)
    if row is None:
        raise api_error(
            409,
            "MAIL_NOT_SET_UP",
            "Mail is not set up: an administrator saves the SMTP settings on Settings › Mail first",
        )
    return row


def connection(identity: IdentitySettings, row: MailSettings) -> Connection:
    password = (
        unseal(identity.encryption_key, row.password, password_context()).decode()
        if row.password is not None
        else None
    )
    return Connection(row.host, row.port, row.security, row.username, password, row.from_address)


def application_url(identity: IdentitySettings, row: MailSettings | None) -> str:
    """Where the links in mail point: the saved address, else the first browser origin (D422)."""
    if row is not None and row.application_url:
        return row.application_url
    return identity.browser_origins[0].rstrip("/") if identity.browser_origins else identity.issuer


def uses_default_address(row: MailSettings | None) -> bool:
    return row is None or not row.application_url


def _stale(current: int) -> ApiError:
    return api_error(
        409, "VERSION_CONFLICT", "The mail settings have changed", {"currentVersion": current}
    )


def save(session: Session, identity: IdentitySettings, payload: MailSettingsUpdate) -> MailSettings:
    """Create or replace the settings; commits."""
    row = load(session, for_update=True)
    if (row.version if row else None) != payload.expectedVersion:
        session.rollback()
        raise _stale(row.version if row else 0)
    username = payload.username
    if payload.security == NONE and username is not None:
        session.rollback()
        raise api_error(
            422,
            "MAIL_INSECURE_LOGIN",
            "A login is not sent over an unencrypted connection: choose TLS or STARTTLS, or "
            "remove the user name",
        )
    keeps = row.password if row is not None and username is not None else None
    if username is not None and payload.password is None and keeps is None:
        session.rollback()
        raise api_error(422, "MAIL_PASSWORD_REQUIRED", "A user name needs a password")
    sealed = (
        seal(identity.encryption_key, payload.password.encode(), password_context())
        if payload.password is not None and username is not None
        else keeps
    )
    now = datetime.now(UTC)
    new = {
        "host": payload.host,
        "port": payload.port,
        "security": payload.security,
        "username": username,
        "from_address": payload.fromAddress,
        "application_url": payload.applicationUrl,
    }
    if row is None:
        row = MailSettings(id=1, password=sealed, version=1, updated_at=now, **new)
        session.add(row)
        changed = [*new, "password"] if sealed is not None else list(new)
        action = "created"
    else:
        changed = [name for name, value in new.items() if getattr(row, name) != value]
        if (
            payload.password is not None
            and username is not None
            or (sealed is None) != (row.password is None)
        ):
            changed.append("password")
        for name, value in new.items():
            setattr(row, name, value)
        row.password = sealed
        action = "updated"
        if changed:
            row.version += 1
            row.updated_at = now
    if changed:
        session.flush()
        # The password's value is never recorded; the others are what an administrator set.
        shown = {
            "host": row.host,
            "port": row.port,
            "security": row.security,
            "username": row.username,
            "from_address": row.from_address,
            "application_url": row.application_url,
        }
        security_events.record(
            session, AGGREGATE, EVENT_ID, action, version=row.version,
            details=security_events.changed(
                [_name(field) for field in changed],
                **{_name(field): value for field, value in shown.items()},
            ),
        )  # fmt: skip
    session.commit()
    return row


def _name(column: str) -> str:
    """A column's name as the API words it."""
    return {"from_address": "fromAddress", "application_url": "applicationUrl"}.get(column, column)


def remove(session: Session) -> None:
    """Remove the settings: mail is no longer sent. Messages waiting stay until they fail; commits."""
    row = load(session, for_update=True)
    if row is None:
        session.rollback()
        raise api_error(409, "MAIL_NOT_SET_UP", "Mail is not set up")
    version = row.version + 1
    session.execute(delete(MailSettings).where(MailSettings.id == 1))
    security_events.record(session, AGGREGATE, EVENT_ID, "deleted", version=version)
    session.commit()
