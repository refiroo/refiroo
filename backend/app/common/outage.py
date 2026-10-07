"""How a background thread reports that it keeps failing (Base 0.9 C12; AGENTS.md "Error handling").

The job worker, the event deriver, the webhook dispatcher and the job listener retry a failed round every few seconds.
A database they cannot reach is an expected operational failure: it is reported in one plain ERROR
line saying what failed and how often the thread retries, with the traceback kept at DEBUG. Any
other exception is a defect in the engine's code and keeps its traceback at ERROR, since with no
request to attach it to, the traceback is the only way to find it. While the failure lasts, one
WARNING a minute; when a round succeeds again, one INFO line. An outage of hours never fills the log.
"""

import logging
import time

import psycopg
from sqlalchemy.exc import DBAPIError

REMINDER_SECONDS = 60.0
# SQLSTATEs of a server that went away or refuses connections: connection exceptions (class 08) and
# an administrator's or a crash's shutdown (57P01–57P03).
_UNREACHABLE_CLASS = "08"
_UNREACHABLE_STATES = frozenset({"57P01", "57P02", "57P03"})


def database_unreachable(exc: BaseException) -> bool:
    """Whether ``exc`` says the database cannot be reached, rather than that a statement failed: a
    connection that was lost, one that could not be opened (no SQLSTATE: the server never answered,
    or refused the connection), or a server shutting down. Through SQLAlchemy, or from a connection
    of psycopg's own (the job listener's, 0.9 J1u)."""
    if isinstance(exc, psycopg.OperationalError):
        return _unreachable_state(exc.sqlstate)
    if not isinstance(exc, DBAPIError):
        return False
    if exc.connection_invalidated:
        return True
    return _unreachable_state(getattr(exc.orig, "sqlstate", None))


def _unreachable_state(state: str | None) -> bool:
    return state is None or state.startswith(_UNREACHABLE_CLASS) or state in _UNREACHABLE_STATES


def _summary(exc: BaseException) -> str:
    """The cause in one line, without SQLAlchemy's statement and background link."""
    cause = exc.orig if isinstance(exc, DBAPIError) and exc.orig is not None else exc
    return " ".join(str(cause).split())[:200] or type(cause).__name__


class OutageLog:
    """What one thread logs about its failing rounds: ``failed`` after each, ``succeeded`` after
    each round that works."""

    def __init__(self, logger: logging.Logger, thread: str, retry_seconds: float) -> None:
        self.logger = logger
        self.thread = thread
        self.retry_seconds = retry_seconds
        self.failing = False
        self._unreachable = False
        self._next_reminder = 0.0

    def failed(self, exc: BaseException) -> None:
        now = time.monotonic()
        if not self.failing:
            self.failing, self._next_reminder = True, now + REMINDER_SECONDS
            self._unreachable = database_unreachable(exc)
            if self._unreachable:
                self.logger.error(
                    "%s cannot reach the database (%s); it retries every %s s and continues where it "
                    "stopped once the database answers",
                    self.thread,
                    _summary(exc),
                    self.retry_seconds,
                )
                self.logger.debug("%s: the database error", self.thread, exc_info=exc)
            else:
                self.logger.error(
                    "%s failed unexpectedly; it retries every %s s", self.thread, self.retry_seconds, exc_info=exc
                )
        elif now >= self._next_reminder:
            self._next_reminder = now + REMINDER_SECONDS
            self.logger.warning(
                "%s still cannot reach the database (%s); it retries every %s s"
                if self._unreachable
                else "%s still fails (%s); it retries every %s s",
                self.thread,
                _summary(exc),
                self.retry_seconds,
            )

    def succeeded(self) -> None:
        if self.failing:
            self.logger.info(
                "%s reaches the database again" if self._unreachable else "%s works again", self.thread
            )
            self.failing = False
