"""Mail settings and the outbox as the API answers them (Product 0.12 M1)."""

from sqlalchemy.orm import Session

from ...common.pagination import Page
from ...common.time import as_utc
from ...engine.identity.settings import IdentitySettings
from ...engine.mail import outbox, settings
from ...models.database import MailOutbox, MailSettings
from ..schemas.mail import MailCounts, MailMessagePage, MailMessageResponse, MailSettingsResponse


def settings_response(
    session: Session, identity: IdentitySettings, row: MailSettings | None
) -> MailSettingsResponse:
    return MailSettingsResponse(
        configured=row is not None,
        host=row.host if row else None,
        port=row.port if row else None,
        security=row.security if row else None,  # type: ignore[arg-type]
        username=row.username if row else None,
        passwordSet=bool(row and row.password is not None),
        fromAddress=row.from_address if row else None,
        applicationUrl=settings.application_url(identity, row),
        applicationUrlIsDefault=settings.uses_default_address(row),
        outbox=MailCounts(**outbox.counts(session)),
        version=row.version if row else None,
        updatedAt=as_utc(row.updated_at) if row else None,
    )


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
