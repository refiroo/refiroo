"""The mail sender's thread (Product 0.12 M1, D419): sends what the outbox holds.

Every couple of seconds it queues the mail of due inbox notices (``notifications.mailing``, M2),
gives up on messages older than 24 hours, leases the ones that are due
and hands each to the SMTP server. A message that fails waits longer each time (30 seconds,
doubling, at most an hour); one the server refuses for good (an address that does not exist) fails
at once. When the whole server fails (it cannot be reached, TLS, the login), the other leased
messages share that failure instead of each waiting out a timeout. Every process runs one; leases
and ``FOR UPDATE SKIP LOCKED`` keep them off the same message. Tests drive it themselves
(``run_once``, ``run_until_idle``) with ``run_mail_sender`` False.
"""

import logging
import os
import socket
import threading
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from sqlalchemy import case, delete, func, or_, select, update
from sqlalchemy.orm import Session

from ...common.outage import OutageLog
from ...common.sealing import SealError, unseal
from ...models.database import MailOutbox
from ..identity.settings import IdentitySettings
from ..notifications import mailing
from . import settings as mail_settings
from .outbox import GIVE_UP_AFTER, RETAIN_FINISHED, body_context, retry_delay
from .smtp import SERVER_WIDE, Connection, MailError, build, deliver

logger = logging.getLogger(__name__)

POLL_SECONDS = 2.0
RETRY_SECONDS = 5.0
PRUNE_SECONDS = 3600.0
LEASE_SECONDS = 120
BATCH = 10
THREAD_NAME = "rdm-mail-sender"
NOT_SET_UP = "not_set_up"
UNREADABLE = "unreadable"


class MailSender:
    """Sends the outbox in this process: ``run_until_idle`` once; ``start`` on a thread."""

    def __init__(
        self,
        session_factory: Callable[[], Session],
        identity: IdentitySettings,
        *,
        owner: str | None = None,
        timeout_seconds: float | None = None,
        batch: int = BATCH,
    ) -> None:
        self.session_factory = session_factory
        self.identity = identity
        self.owner = owner or f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:8]}"
        self.timeout_seconds = timeout_seconds
        self.batch = batch
        self._stopping = threading.Event()
        self._thread: threading.Thread | None = None

    # --- one round --------------------------------------------------------------------------------

    def expire(self, now: datetime) -> int:
        """Give up on messages still pending after 24 hours; how many."""
        with self.session_factory() as session:
            count = session.execute(
                update(MailOutbox)
                .where(
                    MailOutbox.status == "pending",
                    MailOutbox.created_at <= now - GIVE_UP_AFTER,
                    or_(MailOutbox.lease_owner.is_(None), MailOutbox.lease_expires_at < now),
                )
                .values(
                    status="failed",
                    body=None,
                    finished_at=now,
                    lease_owner=None,
                    lease_expires_at=None,
                    last_error=case(
                        (
                            MailOutbox.last_error.is_(None),
                            "Not sent within 24 hours",
                        ),
                        else_=func.concat(
                            "Not sent within 24 hours. Last error: ", MailOutbox.last_error
                        ),
                    ),
                    last_error_kind=func.coalesce(MailOutbox.last_error_kind, "expired"),
                )
                .execution_options(synchronize_session=False)
            ).rowcount
            session.commit()
        return count

    def claim(self, now: datetime) -> list[int]:
        """Lease up to ``batch`` messages that are due; their IDs, oldest first."""
        due = (
            select(MailOutbox.id)
            .where(
                MailOutbox.status == "pending",
                MailOutbox.next_attempt_at <= now,
                or_(MailOutbox.lease_owner.is_(None), MailOutbox.lease_expires_at < now),
            )
            .order_by(MailOutbox.next_attempt_at, MailOutbox.id)
            .limit(self.batch)
            .with_for_update(skip_locked=True)
        )
        with self.session_factory() as session:
            claimed = list(
                session.scalars(
                    update(MailOutbox)
                    .where(MailOutbox.id.in_(due))
                    .values(
                        lease_owner=self.owner,
                        lease_expires_at=now + timedelta(seconds=LEASE_SECONDS),
                    )
                    .returning(MailOutbox.id)
                    .execution_options(synchronize_session=False)
                )
            )
            session.commit()
        return sorted(claimed)

    def run_once(self, now: datetime | None = None) -> int:
        """Send what is due; how many messages were handled (sent, retried later or failed)."""
        at = now or datetime.now(UTC)
        self.expire(at)
        with self.session_factory() as session:
            mailing.queue_notices(session, self.identity, at)
        claimed = self.claim(at)
        if not claimed:
            return 0
        with self.session_factory() as session:
            row = mail_settings.load(session)
            connection = mail_settings.connection(self.identity, row) if row else None
        server_failure: MailError | None = None
        for message_id in claimed:
            failure = self._send(message_id, connection, server_failure, at)
            if failure is not None and failure.kind in SERVER_WIDE:
                server_failure = failure
        return len(claimed)

    def run_until_idle(self, now: datetime | None = None) -> int:
        """Send until nothing is due; how many messages were handled."""
        handled = 0
        while step := self.run_once(now):
            handled += step
        return handled

    def _send(
        self,
        message_id: int,
        connection: Connection | None,
        server_failure: MailError | None,
        now: datetime,
    ) -> MailError | None:
        """One leased message; the failure, if it did not go.

        The row is locked from here to the commit that records the outcome: a lease that runs out
        while the server is slow cannot be taken over by another process, whose claim skips locked
        rows, and one that was taken over before this point is no longer ours (``lease_owner``), so
        the message is sent by one process only (0.12 R)."""
        with self.session_factory() as session:
            message = session.scalar(
                select(MailOutbox)
                .where(
                    MailOutbox.id == message_id,
                    MailOutbox.lease_owner == self.owner,
                    MailOutbox.status == "pending",
                )
                .with_for_update(skip_locked=True)
            )
            if message is None:
                return None
            failure = server_failure
            if failure is None:
                failure = self._try(message, connection)
            message.lease_owner = None
            message.lease_expires_at = None
            if failure is None:
                message.status, message.body, message.finished_at = "sent", None, now
                message.last_error = message.last_error_kind = None
                message.attempts += 1
            else:
                message.attempts += 1
                message.last_error, message.last_error_kind = str(failure), failure.kind
                if failure.permanent or now - message.created_at >= GIVE_UP_AFTER:
                    message.status, message.body, message.finished_at = "failed", None, now
                else:
                    message.next_attempt_at = now + retry_delay(message.attempts)
            kind = message.kind
            session.commit()
        if failure is not None and failure is not server_failure:
            logger.warning("A %s mail was not sent: %s", kind, failure)
        return failure

    def _try(self, message: MailOutbox, connection: Connection | None) -> MailError | None:
        if connection is None:
            return MailError(NOT_SET_UP, "Mail is not set up: the SMTP settings were removed")
        try:
            body = unseal(
                self.identity.encryption_key, message.body or b"", body_context(message.public_id)
            ).decode()
        except SealError:
            return MailError(
                UNREADABLE,
                "The message cannot be read: SECRETS_ENCRYPTION_KEY has changed since it was queued",
                permanent=True,
            )
        built = build(connection, message.to_address, message.subject, body)
        kwargs = {} if self.timeout_seconds is None else {"timeout": self.timeout_seconds}
        try:
            deliver(connection, built, **kwargs)
        except MailError as error:
            return error
        return None

    def prune(self, now: datetime) -> int:
        """Delete messages finished more than 30 days ago; how many."""
        with self.session_factory() as session:
            count = session.execute(
                delete(MailOutbox).where(
                    MailOutbox.status != "pending", MailOutbox.finished_at < now - RETAIN_FINISHED
                )
            ).rowcount
            session.commit()
        return count

    # --- the thread -------------------------------------------------------------------------------

    def start(self) -> None:
        self._stopping.clear()
        self._thread = threading.Thread(target=self._loop, name=THREAD_NAME, daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 30.0) -> None:
        """Stop after the running message; one still leased is sent again once its lease ends."""
        self._stopping.set()
        if self._thread is not None:
            self._thread.join(timeout)
            self._thread = None

    def _loop(self) -> None:
        outage = OutageLog(logger, "The mail sender", RETRY_SECONDS)
        next_prune = 0.0
        while not self._stopping.is_set():
            wait = POLL_SECONDS
            try:
                if time.monotonic() >= next_prune:
                    self.prune(datetime.now(UTC))
                    next_prune = time.monotonic() + PRUNE_SECONDS
                while self.run_once() and not self._stopping.is_set():
                    pass
                outage.succeeded()
            except Exception as exc:  # noqa: BLE001 - every failure is logged by OutageLog
                outage.failed(exc)
                wait = RETRY_SECONDS
            self._stopping.wait(wait)
