"""Mail settings and the outbox (Product 0.12 M1, API.md § Mail)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from .common import CollectionPage


class MailCounts(BaseModel):
    """Messages in each status: finished ones are kept for 30 days."""

    pending: int
    sent: int
    failed: int


class MailSettingsResponse(BaseModel):
    """How mail is sent; never a password, client secret or certificate (D419, 0.13 MS).

    Without saved settings ``configured`` is false, ``method`` and the connection fields are null and
    no mail is sent. With `smtp` the SMTP fields are set; with `microsoft365` the Microsoft 365 ones
    (``fromAddress`` is the sending mailbox; a managed identity stores no secret), and a certificate is answered by its thumbprint (SHA-1,
    as the Entra portal shows it) and expiry. ``applicationUrl`` is where the links in mail point: the
    saved address, or the first browser origin while ``applicationUrlIsDefault``.
    """

    configured: bool
    method: Literal["smtp", "microsoft365"] | None
    host: str | None
    port: int | None
    security: Literal["tls", "starttls", "none"] | None
    username: str | None
    passwordSet: bool = Field(description="SMTP: the password is saved; it is never answered")
    credential: Literal["secret", "certificate", "managedIdentity"] | None = Field(
        description="Microsoft 365: what proves the application to Microsoft; null with SMTP"
    )
    identityMode: Literal["direct", "federated"] | None = Field(
        description="Microsoft 365, managed identity: `direct` (the Azure host's identity in the "
        "organisation's tenant; `tenantId` and `clientId` are null) or `federated`"
    )
    identityClientId: str | None = Field(
        description="Microsoft 365, managed identity: the user-assigned identity's client ID; null "
        "for a system-assigned one"
    )
    tenantId: str | None
    clientId: str | None
    clientSecretSet: bool = Field(
        description="Microsoft 365: a client secret is saved; it is never answered"
    )
    certificateThumbprint: str | None = Field(
        description="Microsoft 365: the saved certificate's SHA-1 thumbprint; null with a secret"
    )
    certificateExpiresAt: datetime | None
    authorityUrl: str | None
    graphUrl: str | None
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
    kind: str = Field(description="`activation`, `password-reset`, `test`, `notice` or `digest`")
    to: str
    subject: str
    status: Literal["pending", "sent", "failed"]
    attempts: int
    lastError: str | None = Field(
        description="Why the last attempt failed, in a sentence; null when none did"
    )
    lastErrorKind: str | None = Field(
        description="`connection`, `tls`, `login`, `recipient`, `sender`, `rejected`, "
        "`not_set_up`, `unreadable`, `expired` or `stopped`"
    )
    createdAt: datetime
    nextAttemptAt: datetime | None = Field(description="While pending: when it is tried next")
    finishedAt: datetime | None = Field(description="When it was sent or given up on")


class MailMessagePage(CollectionPage[MailMessageResponse]):
    """Messages, newest first (ADR-030)."""


class NoticeKindResponse(BaseModel):
    """One kind of inbox notice and how the caller is mailed it."""

    kind: str = Field(description="For example `change-set.submitted` or `job.failed`")
    label: str = Field(description="What the notice says, in a plain sentence")
    delivery: Literal["now", "digest", "off"] = Field(
        description="`now`: one mail when it arrives (until changed); `digest`: in the digest; "
        "`off`: no mail"
    )


class DigestResponse(BaseModel):
    """The caller's digest (0.16 AO3): how often it comes, the time zone 07:00 is read in and when
    the next is due. `nextAt` is the next send time while mail is switched on, else null."""

    every: Literal["daily", "weekly"] = Field(description="Every morning, or on Mondays, at 07:00")
    timeZone: str = Field(description="An IANA time zone, such as `Europe/Budapest`")
    nextAt: datetime | None


class NoticeMailResponse(BaseModel):
    """Whether the caller is mailed when something arrives in their inbox (0.12 M2). Off until the
    person switches it on. ``available`` is false where it cannot work, and ``reason`` says why:
    `mail-not-set-up`, `no-email` (the person has no address) or `not-a-person` (a client has no
    mail)."""

    enabled: bool
    available: bool
    reason: Literal["mail-not-set-up", "no-email", "not-a-person"] | None
    email: str | None = Field(description="Where the mail goes; none without an address")
    kinds: list[NoticeKindResponse] = Field(
        description="Every kind of notice, in the order to show them, with how the person is mailed "
        "it. Everything is `now` until changed; it is listed even where mail is not `available`. "
        "Only the mail changes: the inbox keeps every notice"
    )
    digest: DigestResponse | None = Field(
        description="The digest, once the person has chosen how often it comes; else null"
    )


class DigestUpdate(BaseModel):
    """Choose how often the digest comes and the time zone it is read in."""

    every: Literal["daily", "weekly"]
    timeZone: str = Field(min_length=1, max_length=64, description="An IANA time zone")


class NoticeMailUpdate(BaseModel):
    """Change the caller's notice mail: ``enabled`` switches it on or off, ``kinds`` sets how the
    named kinds are mailed and leaves the others, ``digest`` sets the digest's frequency and time
    zone. All are optional; at least one is needed."""

    enabled: bool | None = None
    kinds: dict[str, Literal["now", "digest", "off"]] | None = Field(
        default=None,
        description="Kind -> `now`, `digest` or `off`; an unknown kind is refused, and `digest` "
        "needs a digest set (here or earlier)",
    )
    digest: DigestUpdate | None = None

    @model_validator(mode="after")
    def _something_to_change(self) -> NoticeMailUpdate:
        if self.enabled is None and self.kinds is None and self.digest is None:
            raise ValueError("Send `enabled`, `kinds`, `digest` or more")
        return self


class MailTemplateResponse(BaseModel):
    """The e-mail template: Markdown with ``{{placeholders}}`` and a logo, around the content of every
    mail the engine sends. Without a saved template (``saved`` false) ``markdown`` is the default and
    the engine's own layout is used until one is saved."""

    markdown: str
    defaultMarkdown: str = Field(
        description="The shipped default; `DELETE /mail-template` restores it"
    )
    saved: bool
    placeholders: list[str] = Field(
        description="The placeholders a template may use; `{{content}}` is required exactly once"
    )
    logoType: str | None = Field(
        description="`image/png`, `image/jpeg` or `image/svg+xml`; null for the refiroo mark"
    )
    logoDataUrl: str | None = Field(
        description="The uploaded logo as a data URL, for a thumbnail; null when none"
    )
    logoMaxBytes: int
    version: int | None = Field(description="Null until saved; send it as expectedVersion")
    updatedAt: datetime | None


class MailTemplatePreviewResponse(BaseModel):
    """A draft rendered around a sample message with sample values: the HTML document (the logo as a
    data URL) and the plain-text alternative."""

    html: str
    text: str
