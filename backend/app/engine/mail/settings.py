"""The mail settings an administrator saves (Product 0.12 M1, D419, D422; 0.13 MS).

One row, absent until mail is set up: SMTP or Microsoft 365, one method at a time. The password, client
secret and certificate are each sealed with ``SECRETS_ENCRYPTION_KEY`` (D253)
and never answered. Without a row no mail is sent and nothing else changes (``MAIL_NOT_SET_UP``).
Saving, changing and removing the settings are security events: they decide where one-time links go.
"""

from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ...common.sealing import seal, unseal
from ...errors import ApiError, api_error
from ...models.commands import DEFAULT_AUTHORITY_URL, DEFAULT_GRAPH_URL, MailSettingsUpdate
from ...models.database import MailSettings
from ..identity import security_events
from ..identity.settings import IdentitySettings
from . import graph
from .graph import GraphConnection
from .smtp import NONE, Connection
from .transport import Transport

AGGREGATE = "mail-settings"
# The one setting's identity in a security event.
EVENT_ID = "mail"
# The sealed values' identities: one per secret, so one cannot be opened as another.
SECRET = "client-secret"
CERTIFICATE = "certificate"


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
            "Mail is not set up: an administrator saves the mail settings on Settings › Mail first",
        )
    return row


def connection(identity: IdentitySettings, row: MailSettings) -> Transport:
    """How to reach what sends the mail: the SMTP server or Microsoft 365."""
    if row.method == "microsoft365":
        assert row.ms_authority_url and row.ms_graph_url
        secret = (
            unseal(identity.encryption_key, row.ms_client_secret, password_context(SECRET)).decode()
            if row.ms_client_secret is not None
            else None
        )
        certificate = (
            unseal(
                identity.encryption_key, row.ms_certificate, password_context(CERTIFICATE)
            ).decode()
            if row.ms_certificate is not None
            else None
        )
        return GraphConnection(
            row.ms_tenant_id,
            row.ms_client_id,
            row.ms_authority_url,
            row.ms_graph_url,
            row.from_address,
            secret,
            certificate,
            row.ms_identity_mode,
            row.ms_identity_client_id,
        )
    assert row.host is not None and row.port is not None and row.security is not None
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


def reset_link_base(session: Session, identity: IdentitySettings) -> str:
    """The address a password link is built on: the application's reset page, or the engine's own
    page when no address of the application is known (I6, D422)."""
    row = load(session)
    if (row is None or not row.application_url) and not identity.browser_origins:
        return f"{identity.issuer}/oauth/password"
    return f"{application_url(identity, row)}/reset-password"


def uses_default_address(row: MailSettings | None) -> bool:
    return row is None or not row.application_url


def _stale(current: int) -> ApiError:
    return api_error(
        409, "VERSION_CONFLICT", "The mail settings have changed", {"currentVersion": current}
    )


def save(session: Session, identity: IdentitySettings, payload: MailSettingsUpdate) -> MailSettings:
    """Create or replace the settings; commits. Saving one method clears the other's fields."""
    row = load(session, for_update=True)
    if (row.version if row else None) != payload.expectedVersion:
        session.rollback()
        raise _stale(row.version if row else 0)
    try:
        plain, sealed, sent = (
            _smtp_fields(identity, row, payload)
            if payload.method == "smtp"
            else _microsoft_fields(identity, row, payload)
        )
    except ApiError:
        session.rollback()
        raise
    plain |= {"method": payload.method, "from_address": payload.fromAddress}
    plain["application_url"] = payload.applicationUrl
    now = datetime.now(UTC)
    if row is None:
        row = MailSettings(id=1, version=1, updated_at=now, **plain, **sealed)
        session.add(row)
        changed = [name for name, value in plain.items() if value is not None and name != _EXPIRY]
        changed += [name for name, value in sealed.items() if value is not None]
        action = "created"
    else:
        changed = [
            name for name, value in plain.items() if name != _EXPIRY and getattr(row, name) != value
        ]
        changed += [
            name
            for name, value in sealed.items()
            if name in sent or (value is None) != (getattr(row, name) is None)
        ]
        for name, value in {**plain, **sealed}.items():
            setattr(row, name, value)
        action = "updated"
        if changed:
            row.version += 1
            row.updated_at = now
    if changed:
        session.flush()
        # A secret's value is never recorded; the others are what an administrator set.
        shown = {name: getattr(row, name) for name in _SHOWN if getattr(row, name) is not None}
        security_events.record(
            session, AGGREGATE, EVENT_ID, action, version=row.version,
            details=security_events.changed(
                [_name(field) for field in changed],
                **{_name(field): value for field, value in shown.items()},
            ),
        )  # fmt: skip
    session.commit()
    return row


_SHOWN = (
    "method",
    "host",
    "port",
    "security",
    "username",
    "ms_tenant_id",
    "ms_client_id",
    "ms_authority_url",
    "ms_graph_url",
    "ms_certificate_thumbprint",
    "ms_identity_mode",
    "ms_identity_client_id",
    "from_address",
    "application_url",
)
_EXPIRY = "ms_certificate_expires_at"
_NO_MICROSOFT = {
    "ms_tenant_id": None,
    "ms_client_id": None,
    "ms_authority_url": None,
    "ms_graph_url": None,
    "ms_certificate_thumbprint": None,
    "ms_certificate_expires_at": None,
    "ms_identity_mode": None,
    "ms_identity_client_id": None,
}
_NO_SMTP = {"host": None, "port": None, "security": None, "username": None}


def _smtp_fields(
    identity: IdentitySettings, row: MailSettings | None, payload: MailSettingsUpdate
) -> tuple[dict, dict, set[str]]:
    """The columns of the SMTP method; refuses what cannot be saved. ``sent``: sealed columns the
    payload gave a new value for."""
    username = payload.username
    if payload.security == NONE and username is not None:
        raise api_error(
            422,
            "MAIL_INSECURE_LOGIN",
            "A login is not sent over an unencrypted connection: choose TLS or STARTTLS, or "
            "remove the user name",
        )
    if (
        row is not None
        and row.password is not None
        and username is not None
        and payload.password is None
        and (row.host, row.port) != (payload.host, payload.port)
    ):
        # The saved password was given for the old server: it is never carried to another one, where
        # whoever runs that server would receive it (0.12 E1, C6).
        raise api_error(
            422,
            "MAIL_PASSWORD_REQUIRED",
            "The password is not kept when the host or the port changes: send the password again",
            {"field": "password"},
        )
    keeps = row.password if row is not None and username is not None else None
    if username is not None and payload.password is None and keeps is None:
        raise api_error(422, "MAIL_PASSWORD_REQUIRED", "A user name needs a password")
    password = (
        seal(identity.encryption_key, payload.password.encode(), password_context())
        if payload.password is not None and username is not None
        else keeps
    )
    plain = {
        **_NO_MICROSOFT,
        "host": payload.host,
        "port": payload.port,
        "security": payload.security,
        "username": username,
    }
    sealed = {"password": password, "ms_client_secret": None, "ms_certificate": None}
    return plain, sealed, {"password"} if payload.password is not None and username else set()


def _microsoft_fields(
    identity: IdentitySettings, row: MailSettings | None, payload: MailSettingsUpdate
) -> tuple[dict, dict, set[str]]:
    authority = payload.authorityUrl or DEFAULT_AUTHORITY_URL
    graph_url = payload.graphUrl or DEFAULT_GRAPH_URL
    plain = {
        **_NO_SMTP,
        "ms_tenant_id": payload.tenantId,
        "ms_client_id": payload.clientId,
        "ms_authority_url": authority,
        "ms_graph_url": graph_url,
        "ms_certificate_thumbprint": None,
        "ms_certificate_expires_at": None,
        "ms_identity_mode": payload.identityMode,
        "ms_identity_client_id": payload.identityClientId,
    }
    sealed: dict[str, bytes | None] = {
        "password": None,
        "ms_client_secret": None,
        "ms_certificate": None,
    }
    if payload.identityMode is not None:
        # A managed identity stores no secret: saving it clears a saved secret or certificate.
        return plain, sealed, set()
    if payload.clientSecret is not None:
        sealed["ms_client_secret"] = seal(
            identity.encryption_key, payload.clientSecret.encode(), password_context(SECRET)
        )
        return plain, sealed, {"ms_client_secret"}
    if payload.certificate is not None:
        try:
            certificate = graph.read_certificate(payload.certificate)
        except ValueError as exc:
            raise api_error(
                422,
                "MAIL_CERTIFICATE_INVALID",
                f"The certificate cannot be used: {exc}",
                {"field": "certificate"},
            ) from None
        sealed["ms_certificate"] = seal(
            identity.encryption_key, certificate.pem, password_context(CERTIFICATE)
        )
        plain["ms_certificate_thumbprint"] = certificate.thumbprint
        plain["ms_certificate_expires_at"] = certificate.expires_at
        return plain, sealed, {"ms_certificate"}
    same_application = (
        row is not None
        and row.method == "microsoft365"
        and row.ms_identity_mode is None
        and (row.ms_tenant_id, row.ms_client_id, row.ms_authority_url)
        == (payload.tenantId, payload.clientId, authority)
    )
    if row is None or not same_application:
        # A credential saved for another application or authority is never carried to this one.
        raise api_error(
            422,
            "MAIL_CREDENTIAL_REQUIRED",
            "Send a client secret or a certificate: a saved one is kept only for the same tenant, "
            "application and token address",
            {"field": "clientSecret"},
        )
    sealed["ms_client_secret"] = row.ms_client_secret
    sealed["ms_certificate"] = row.ms_certificate
    plain["ms_certificate_thumbprint"] = row.ms_certificate_thumbprint
    plain["ms_certificate_expires_at"] = row.ms_certificate_expires_at
    return plain, sealed, set()


def _name(column: str) -> str:
    """A column's name as the API words it."""
    return {
        "from_address": "fromAddress",
        "application_url": "applicationUrl",
        "ms_tenant_id": "tenantId",
        "ms_client_id": "clientId",
        "ms_authority_url": "authorityUrl",
        "ms_graph_url": "graphUrl",
        "ms_certificate_thumbprint": "certificateThumbprint",
        "ms_identity_mode": "identityMode",
        "ms_identity_client_id": "identityClientId",
        "ms_client_secret": "clientSecret",
        "ms_certificate": "certificate",
    }.get(column, column)


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
