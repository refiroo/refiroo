"""How a background thread reports that it keeps failing (Base 0.9 C12; AGENTS.md "Error handling").

The job worker, the event deriver, the webhook dispatcher and the job listener retry a failed round every few seconds.
A database they cannot reach is an expected operational failure: it is reported in one plain ERROR
line saying what failed and how often the thread retries, with the traceback kept at DEBUG. Any
other exception is a defect in the engine's code and keeps its traceback at ERROR, since with no
request to attach it to, the traceback is the only way to find it. While the failure lasts, one
WARNING a minute; when a round succeeds again, one INFO line. An outage of hours never fills the log.
"""

import logging
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

import psycopg
from sqlalchemy.exc import DBAPIError
from sqlalchemy.exc import TimeoutError as PoolTimeout

REMINDER_SECONDS = 60.0
# SQLSTATEs of a server that went away or refuses connections: connection exceptions (class 08) and
# an administrator's or a crash's shutdown (57P01–57P03).
_UNREACHABLE_CLASS = "08"
_UNREACHABLE_STATES = frozenset({"57P01", "57P02", "57P03"})
# The server refuses a new connection because it has as many as it takes. A refusal while connecting
# carries no SQLSTATE in psycopg (checked 2026-10-20), only the server's FATAL message: "too many
# clients already", "too many connections for role/database", "remaining connection slots are
# reserved".
_TOO_MANY_CONNECTIONS = "53300"
_TOO_MANY_PHRASES = ("too many clients", "too many connections", "connection slots are reserved")
# The server ended a session left idle inside its transaction for longer than
# ``DATABASE_IDLE_TRANSACTION_TIMEOUT`` (0.11 N3, D183): the process had stalled. The connection is
# invalidated, so without this it would read as unreachable.
_IDLE_TRANSACTION_ENDED = "25P03"

Unavailable = Literal["poolExhausted", "tooManyConnections", "transactionEnded", "unreachable"]


def database_unreachable(exc: BaseException) -> bool:
    """Whether ``exc`` says the database cannot be reached, rather than that a statement failed: a
    connection that was lost, one that could not be opened (no SQLSTATE: the server never answered,
    or refused the connection), or a server shutting down. Through SQLAlchemy, or from a connection
    of psycopg's own (the job listener's, 0.9 J1u)."""
    if isinstance(exc, psycopg.OperationalError):
        return _unreachable_state(exc.sqlstate)
    if not isinstance(exc, DBAPIError):
        return False
    if client_data_error(exc):
        return False
    if exc.connection_invalidated:
        return True
    return _unreachable_state(getattr(exc.orig, "sqlstate", None))


def client_data_error(exc: BaseException) -> bool:
    """Whether the driver refused a value before sending it, which the caller supplied: a text with
    a NUL character (``PostgreSQL text fields cannot contain NUL``), a ``DataError`` with no
    SQLSTATE since the server never saw the statement. Not a database condition (0.12 E1, F4)."""
    cause = exc.orig if isinstance(exc, DBAPIError) else exc
    return isinstance(cause, psycopg.DataError) and cause.sqlstate is None


def database_unavailable(exc: BaseException) -> Unavailable | None:
    """Why ``exc`` left its caller without a database connection (0.11 Q1, D180): this process's
    pool had none free within ``DATABASE_POOL_TIMEOUT``, the server takes no more clients, the
    server ended this caller's idle transaction (0.11 N3, D183), or it cannot be reached. ``None``
    when a statement failed or the code has a defect."""
    if isinstance(exc, PoolTimeout):
        return "poolExhausted"
    state = (
        exc.sqlstate
        if isinstance(exc, psycopg.Error)
        else getattr(getattr(exc, "orig", None), "sqlstate", None)
    )
    if isinstance(exc, (psycopg.Error, DBAPIError)) and (
        state == _TOO_MANY_CONNECTIONS
        or any(phrase in str(exc).lower() for phrase in _TOO_MANY_PHRASES)
    ):
        return "tooManyConnections"
    if state == _IDLE_TRANSACTION_ENDED:
        return "transactionEnded"
    return "unreachable" if database_unreachable(exc) else None


# What an operator reads about each, in a log line or a 503's message.
UNAVAILABLE_CAUSES: dict[Unavailable, str] = {
    "poolExhausted": (
        "every connection of this process's pool was in use for DATABASE_POOL_TIMEOUT; if this "
        "persists under normal load, raise DATABASE_POOL_SIZE or DATABASE_POOL_MAX_OVERFLOW within "
        "the server's max_connections"
    ),
    "tooManyConnections": (
        "the database server takes no more connections (max_connections); lower WEB_CONCURRENCY, "
        "DATABASE_POOL_SIZE or DATABASE_POOL_MAX_OVERFLOW across the instances, or raise the "
        "server's max_connections"
    ),
    "transactionEnded": (
        "the database ended this process's transaction after it sat idle for "
        "DATABASE_IDLE_TRANSACTION_TIMEOUT, releasing its locks; the process had stalled (frozen, "
        "starved of CPU or cut off from the database). If this happens while the process runs "
        "normally, raise DATABASE_IDLE_TRANSACTION_TIMEOUT"
    ),
    "unreachable": "the database cannot be reached; check that the server is up and DATABASE_URL",
}


def _unreachable_state(state: str | None) -> bool:
    return state is None or state.startswith(_UNREACHABLE_CLASS) or state in _UNREACHABLE_STATES


def _summary(exc: BaseException) -> str:
    """The cause in one line, without SQLAlchemy's statement and background link."""
    cause = exc.orig if isinstance(exc, DBAPIError) and exc.orig is not None else exc
    return " ".join(str(cause).split())[:200] or type(cause).__name__


@dataclass(frozen=True)
class ThreadState:
    """Whether a background thread's rounds work (0.11 O1, D192): ``reason`` is why the current
    failure began (a database reason, or ``error`` for a defect), ``since`` when."""

    failing: bool
    reason: Unavailable | Literal["error"] | None = None
    since: datetime | None = None


# Each background thread's state by thread name, kept by its ``OutageLog``; what a process reports.
_states: dict[str, ThreadState] = {}
_states_lock = threading.Lock()
# How many times each reason left a caller without a database connection (0.11 O1, D194): a
# request's 503 or the start of a thread's outage.
_unavailable_counts: dict[str, int] = {}


def thread_states() -> dict[str, ThreadState]:
    """The state of every background thread that has run in this process, by thread name."""
    with _states_lock:
        return dict(_states)


def note_unavailable(reason: Unavailable) -> None:
    """Count one caller left without a database connection for ``reason``."""
    with _states_lock:
        _unavailable_counts[reason] = _unavailable_counts.get(reason, 0) + 1


def unavailable_counts() -> dict[str, int]:
    with _states_lock:
        return dict(_unavailable_counts)


def _set_state(thread: str, state: ThreadState) -> None:
    with _states_lock:
        _states[thread] = state


class OutageLog:
    """What one thread logs about its failing rounds: ``failed`` after each, ``succeeded`` after
    each round that works. Built on the thread it reports, whose name keys its state."""

    def __init__(self, logger: logging.Logger, thread: str, retry_seconds: float) -> None:
        self.logger = logger
        self.thread = thread
        self.retry_seconds = retry_seconds
        self.failing = False
        self._unreachable = False
        self._reason: Unavailable | None = None
        self._next_reminder = 0.0
        self._name = threading.current_thread().name
        _set_state(self._name, ThreadState(failing=False))

    def failed(self, exc: BaseException) -> None:
        now = time.monotonic()
        if not self.failing:
            self.failing, self._next_reminder = True, now + REMINDER_SECONDS
            reason = self._reason = database_unavailable(exc)
            self._unreachable = reason is not None
            if reason is not None:
                note_unavailable(reason)
            _set_state(self._name, ThreadState(True, reason or "error", datetime.now(UTC)))
            if reason == "unreachable":
                self.logger.error(
                    "%s cannot reach the database (%s); it retries every %s s and continues where it "
                    "stopped once the database answers",
                    self.thread,
                    _summary(exc),
                    self.retry_seconds,
                )
                self.logger.debug("%s: the database error", self.thread, exc_info=exc)
            elif reason is not None:
                self.logger.log(
                    logging.WARNING if reason == "transactionEnded" else logging.ERROR,
                    "%s has no database connection: %s. It retries every %s s and continues where "
                    "it stopped",
                    self.thread,
                    UNAVAILABLE_CAUSES[reason],
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
                (
                    "%s still cannot reach the database (%s); it retries every %s s"
                    if self._reason == "unreachable"
                    else "%s still has no database connection (%s); it retries every %s s"
                )
                if self._unreachable
                else "%s still fails (%s); it retries every %s s",
                self.thread,
                _summary(exc),
                self.retry_seconds,
            )

    def succeeded(self) -> None:
        if self.failing:
            self.logger.info(
                (
                    "%s reaches the database again"
                    if self._reason == "unreachable"
                    else "%s has a database connection again"
                )
                if self._unreachable
                else "%s works again",
                self.thread,
            )
            self.failing = False
            _set_state(self._name, ThreadState(failing=False))
