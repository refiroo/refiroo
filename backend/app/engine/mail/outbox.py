"""The outbox: messages waiting to be sent (Product 0.12 M1, D419).

A message is queued in the caller's transaction (``enqueue``), so a link made and its mail commit
together, and sent later by the background worker (``sender``): a request never waits for the mail
server. A message is retried with a growing delay and given up on after 24 hours; the body, which
holds a one-time link, is sealed and emptied once the message is finished.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...common.pagination import Page, PageRequest, datetime_key, integer_key, paginate_statement
from ...common.sealing import seal
from ...models.database import MailOutbox
from ..identity.settings import IdentitySettings
from . import settings as mail_settings
from .templates import Rendered

GIVE_UP_AFTER = timedelta(hours=24)
RETAIN_FINISHED = timedelta(days=30)
FIRST_DELAY_SECONDS = 30
LONGEST_DELAY_SECONDS = 3600
STATUSES = ("pending", "sent", "failed")
_KEYS = (
    datetime_key("createdAt", MailOutbox.created_at, "created_at", descending=True),
    integer_key("sequenceId", MailOutbox.id, "id", descending=True),
)


def body_context(public_id: str) -> bytes:
    return b"mail-outbox:" + public_id.encode()


def retry_delay(attempts: int) -> timedelta:
    """The wait after the ``attempts``-th failure: 30 seconds, doubling, at most an hour."""
    seconds = FIRST_DELAY_SECONDS * 2 ** max(attempts - 1, 0)
    return timedelta(seconds=min(seconds, LONGEST_DELAY_SECONDS))


def enqueue(
    session: Session,
    identity: IdentitySettings,
    to_address: str,
    message: Rendered,
    *,
    now: datetime | None = None,
) -> MailOutbox:
    """Queue ``message`` for ``to_address`` in the caller's transaction (the caller commits).
    ``409 MAIL_NOT_SET_UP`` without saved settings."""
    mail_settings.require(session)
    at = now or datetime.now(UTC)
    public_id = str(uuid4())
    row = MailOutbox(
        public_id=public_id,
        kind=message.kind,
        to_address=to_address,
        subject=message.subject,
        body=seal(identity.encryption_key, message.body.encode(), body_context(public_id)),
        status="pending",
        attempts=0,
        created_at=at,
        next_attempt_at=at,
    )
    session.add(row)
    session.flush()
    return row


def message_page(
    session: Session, *, status: str | None, page: PageRequest, page_size: int
) -> Page[MailOutbox]:
    """Messages newest first, optionally one status."""
    statement = select(MailOutbox)
    if status is not None:
        statement = statement.where(MailOutbox.status == status)
    return paginate_statement(
        session,
        statement,
        keys=_KEYS,
        scope="mail-outbox",
        filters={"status": status},
        page=page,
        page_size=page_size,
        message="Mail outbox cursor is invalid",
    )


def counts(session: Session) -> dict[str, int]:
    """How many messages are in each status (finished ones for the last 30 days)."""
    found = {
        status: count
        for status, count in session.execute(
            select(MailOutbox.status, func.count()).group_by(MailOutbox.status)
        )
    }
    return {status: found.get(status, 0) for status in STATUSES}
