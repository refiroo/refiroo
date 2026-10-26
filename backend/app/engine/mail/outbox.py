"""The outbox: messages waiting to be sent (Product 0.12 M1, D419).

A message is queued in the caller's transaction (``enqueue``), so a link made and its mail commit
together, and sent later by the background worker (``sender``): a request never waits for the mail
server. A message is retried with a growing delay and given up on after 24 hours; the body, which
holds a one-time link, is sealed and emptied once the message is finished.
"""

import logging
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...common.pagination import Page, PageRequest, datetime_key, integer_key, paginate_statement
from ...common.sealing import seal
from ...errors import api_error
from ...models.database import MailOutbox
from ..identity.settings import IdentitySettings
from . import settings as mail_settings
from .templates import Rendered

logger = logging.getLogger(__name__)

STOPPED = "Stopped by an administrator"
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


def stop(session: Session, public_id: str, *, now: datetime | None = None) -> MailOutbox:
    """Stop sending a message that is waiting: it fails now, saying an administrator stopped it, and
    its sealed text is erased (the link in it works until it expires, as any unused link does).
    ``404 NOT_FOUND`` for an unknown message, ``409 MESSAGE_NOT_WAITING`` once it is sent or failed,
    ``409 MESSAGE_BEING_SENT`` while a sender holds it (try again in a moment). Commits."""
    at = now or datetime.now(UTC)
    message = session.scalar(
        select(MailOutbox).where(MailOutbox.public_id == public_id).with_for_update()
    )
    if message is None:
        session.rollback()
        raise api_error(404, "NOT_FOUND", "There is no such message")
    if message.status != "pending":
        session.rollback()
        raise api_error(
            409, "MESSAGE_NOT_WAITING", f"The message is already {message.status}; nothing to stop"
        )
    if message.lease_owner is not None and message.lease_expires_at > at:
        session.rollback()
        raise api_error(
            409, "MESSAGE_BEING_SENT", "The message is being sent just now; try again in a moment"
        )
    message.status, message.body, message.finished_at = "failed", None, at
    message.lease_owner = message.lease_expires_at = None
    message.last_error = STOPPED
    message.last_error_kind = "stopped"
    session.commit()
    logger.info("A %s mail to %s was stopped by an administrator", message.kind, message.to_address)
    return message


def counts(session: Session) -> dict[str, int]:
    """How many messages are in each status (finished ones for the last 30 days)."""
    found = {
        status: count
        for status, count in session.execute(
            select(MailOutbox.status, func.count()).group_by(MailOutbox.status)
        )
    }
    return {status: found.get(status, 0) for status in STATUSES}
