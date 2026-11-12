"""Mail settings and the outbox as the API answers them (Product 0.12 M1)."""

from sqlalchemy.orm import Session

from ...common.pagination import Page
from ...common.time import as_utc
from ...engine.identity.settings import IdentitySettings
from ...engine.mail import mail_template, outbox, settings
from ...engine.notifications.mailing import NoticeMail
from ...models.database import MailOutbox, MailSettings, MailTemplate
from ..schemas.mail import (
    DigestResponse,
    MailCounts,
    MailMessagePage,
    MailMessageResponse,
    MailSettingsResponse,
    MailTemplateResponse,
    NoticeKindResponse,
    NoticeMailResponse,
)


def settings_response(
    session: Session, identity: IdentitySettings, row: MailSettings | None
) -> MailSettingsResponse:
    return MailSettingsResponse(
        configured=row is not None,
        method=row.method if row else None,  # type: ignore[arg-type]
        host=row.host if row else None,
        port=row.port if row else None,
        security=row.security if row else None,  # type: ignore[arg-type]
        username=row.username if row else None,
        passwordSet=bool(row and row.password is not None),
        credential=_credential(row),  # type: ignore[arg-type]
        identityMode=row.ms_identity_mode if row else None,  # type: ignore[arg-type]
        identityClientId=row.ms_identity_client_id if row else None,
        tenantId=row.ms_tenant_id if row else None,
        clientId=row.ms_client_id if row else None,
        clientSecretSet=bool(row and row.ms_client_secret is not None),
        certificateThumbprint=row.ms_certificate_thumbprint if row else None,
        certificateExpiresAt=as_utc(row.ms_certificate_expires_at)
        if row and row.ms_certificate_expires_at
        else None,
        authorityUrl=row.ms_authority_url if row else None,
        graphUrl=row.ms_graph_url if row else None,
        fromAddress=row.from_address if row else None,
        applicationUrl=settings.application_url(identity, row),
        applicationUrlIsDefault=settings.uses_default_address(row),
        outbox=MailCounts(**outbox.counts(session)),
        version=row.version if row else None,
        updatedAt=as_utc(row.updated_at) if row else None,
    )


def _credential(row: MailSettings | None) -> str | None:
    if row is None or row.method != "microsoft365":
        return None
    if row.ms_identity_mode is not None:
        return "managedIdentity"
    return "certificate" if row.ms_certificate is not None else "secret"


def message_response(message: MailOutbox) -> MailMessageResponse:
    pending = message.status == "pending"
    return MailMessageResponse(
        id=message.public_id,
        kind=message.kind,
        to=message.to_address,
        subject=message.subject,
        status=message.status,  # type: ignore[arg-type]
        attempts=message.attempts,
        lastError=message.last_error,
        lastErrorKind=message.last_error_kind,
        createdAt=as_utc(message.created_at),
        nextAttemptAt=as_utc(message.next_attempt_at) if pending else None,
        finishedAt=as_utc(message.finished_at) if message.finished_at else None,
    )


def message_page(page: Page[MailOutbox]) -> MailMessagePage:
    return MailMessagePage(items=[message_response(m) for m in page.items], **page.links())


def notice_mail_response(found: NoticeMail) -> NoticeMailResponse:
    digest = found.digest
    return NoticeMailResponse(
        enabled=found.enabled,
        available=found.reason is None,
        reason=found.reason,  # type: ignore[arg-type]
        email=found.email,
        kinds=[
            NoticeKindResponse(kind=kind, label=label, delivery=delivery)  # type: ignore[arg-type]
            for kind, label, delivery in found.kinds
        ],
        digest=DigestResponse(
            every=digest.every,  # type: ignore[arg-type]
            timeZone=digest.time_zone,
            nextAt=as_utc(digest.next_at) if found.enabled else None,
        )
        if digest
        else None,
    )


def template_response(row: MailTemplate | None) -> MailTemplateResponse:
    has_logo = row is not None and row.logo is not None and row.logo_type is not None
    return MailTemplateResponse(
        markdown=row.body if row else mail_template.DEFAULT_MARKDOWN,
        defaultMarkdown=mail_template.DEFAULT_MARKDOWN,
        saved=row is not None,
        placeholders=list(mail_template.PLACEHOLDERS),
        logoType=row.logo_type if has_logo and row else None,
        logoDataUrl=(
            mail_template.data_url(row.logo, row.logo_type)  # type: ignore[arg-type]
            if has_logo and row
            else None
        ),
        logoMaxBytes=mail_template.MAX_LOGO_BYTES,
        version=row.version if row else None,
        updatedAt=as_utc(row.updated_at) if row else None,
    )
