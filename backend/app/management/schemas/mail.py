"""Mail settings and the outbox (Product 0.12 M1, API.md § Mail)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from .common import CollectionPage


class MailCounts(BaseModel):
    """Messages in each status: finished ones are kept for 30 days."""

    pending: int
    sent: int
    failed: int


class MailSettingsResponse(BaseModel):
    """The SMTP connection mail is sent through; never its password (D419).

    Without saved settings ``configured`` is false, the connection fields are null and no mail is
    sent. ``applicationUrl`` is where the links in mail point: the saved address, or the first
    browser origin while ``applicationUrlIsDefault``.
    """

    configured: bool
    host: str | None
    port: int | None
    security: Literal["tls", "starttls", "none"] | None
    username: str | None
    passwordSet: bool = Field(description="The password is saved; it is never answered")
    fromAddress: str | None
    applicationUrl: str
    applicationUrlIsDefault: bool
    outbox: MailCounts
    version: int | None = Field(description="Null until saved; send it as expectedVersion")
    updatedAt: datetime | None


class MailTestResponse(BaseModel):
    """The test message went to the server and was accepted for ``sentTo``."""

    sentTo: str


class MailMessageResponse(BaseModel):
    """A message in the outbox. Its text is never answered: it holds a one-time link."""

    id: str
    kind: str = Field(description="`activation`, `password-reset` or `notification`")
    to: str
    subject: str
    status: Literal["pending", "sent", "failed"]
    attempts: int
    lastError: str | None = Field(
        description="Why the last attempt failed, in a sentence; null when none did"
    )
    lastErrorKind: str | None = Field(
        description="`connection`, `tls`, `login`, `recipient`, `sender`, `rejected`, "
        "`not_set_up`, `unreadable` or `expired`"
    )
    createdAt: datetime
    nextAttemptAt: datetime | None = Field(description="While pending: when it is tried next")
    finishedAt: datetime | None = Field(description="When it was sent or given up on")


class MailMessagePage(CollectionPage[MailMessageResponse]):
    """Messages, newest first (ADR-030)."""
