"""What a background thread logs while it keeps failing (Base 0.9 C12; AGENTS.md "Error handling")."""

import logging
import time

import psycopg
import pytest
from psycopg import errors as psycopg_errors
from sqlalchemy.exc import OperationalError
from sqlalchemy.exc import TimeoutError as PoolTimeout

from app.common import outage as outage_module
from app.common.outage import OutageLog, database_unavailable, database_unreachable


class _Driver(Exception):
    def __init__(self, sqlstate):
        super().__init__("server closed the connection unexpectedly")
        self.sqlstate = sqlstate


def _database(sqlstate=None, invalidated=False):
    return OperationalError("SELECT 1", {}, _Driver(sqlstate), connection_invalidated=invalidated)


@pytest.mark.parametrize(
    ("error", "unreachable"),
    [
        (_database(), True),
        (_database("08006"), True),
        (_database("57P01"), True),
        (_database("40001", invalidated=True), True),
        (_database("40001"), False),
        (_database("40P01"), False),
        (ValueError("a defect"), False),
        # A connection of psycopg's own, as the job listener holds (0.9 J1u): lost, shut down, or a
        # statement failing on a live connection.
        (psycopg.OperationalError("server closed the connection unexpectedly"), True),
        (psycopg_errors.AdminShutdown("terminating connection"), True),
        (psycopg_errors.SerializationFailure("could not serialize"), False),
    ],
)
def test_an_unreachable_database_is_told_apart_from_a_failing_statement(error, unreachable):
    assert database_unreachable(error) is unreachable


@pytest.mark.parametrize(
    ("error", "reason"),
    [
        (PoolTimeout("QueuePool limit of size 1 overflow 0 reached"), "poolExhausted"),
        # The server's own limit (SQLSTATE 53300), through SQLAlchemy and from psycopg directly.
        (_database("53300"), "tooManyConnections"),
        (psycopg_errors.TooManyConnections("sorry, too many clients already"), "tooManyConnections"),
        # Refused while connecting, psycopg names no SQLSTATE, only the server's message.
        (
            psycopg.OperationalError('connection failed: FATAL:  too many connections for role "rdm"'),
            "tooManyConnections",
        ),
        (_database(), "unreachable"),
        (_database("08006"), "unreachable"),
        (_database("40001"), None),
        (ValueError("a defect"), None),
    ],
)
def test_why_no_connection_was_had(error, reason):
    """0.11 Q1, D180: the three ways a caller gets no database connection, told apart from a failing
    statement and from a defect."""
    assert database_unavailable(error) == reason


def test_an_exhausted_pool_is_logged_as_an_expected_failure(caplog):
    logger = logging.getLogger("tests.outage")
    log = OutageLog(logger, "The worker", 2.0)
    with caplog.at_level("INFO", logger=logger.name):
        log.failed(PoolTimeout("QueuePool limit of size 1 overflow 0 reached"))
    [record] = caplog.records
    assert record.levelname == "ERROR" and record.exc_info is None
    assert "no database connection" in record.getMessage()
    assert "DATABASE_POOL_SIZE" in record.getMessage()


def test_an_outage_is_one_plain_error_then_a_reminder_an_interval_then_the_recovery(monkeypatch, caplog):
    logger = logging.getLogger("tests.outage")
    log = OutageLog(logger, "The worker", 2.0)
    monkeypatch.setattr(outage_module, "REMINDER_SECONDS", 0.05)
    with caplog.at_level("DEBUG", logger=logger.name):
        log.failed(_database())
        log.failed(_database())
        time.sleep(0.06)
        log.failed(_database())
        log.succeeded()
        log.succeeded()
    records = [(r.levelname, r.getMessage(), r.exc_info is not None) for r in caplog.records]
    assert [level for level, _message, _trace in records] == ["ERROR", "DEBUG", "WARNING", "INFO"]
    assert "The worker cannot reach the database" in records[0][1] and not records[0][2]
    assert records[1][2], "the traceback is kept at DEBUG"
    assert "still cannot reach the database" in records[2][1]
    assert records[3][1] == "The worker reaches the database again"


def test_any_other_failure_keeps_its_traceback(caplog):
    logger = logging.getLogger("tests.outage")
    log = OutageLog(logger, "The worker", 2.0)
    with caplog.at_level("DEBUG", logger=logger.name):
        log.failed(ValueError("a defect"))
        log.succeeded()
    (error, recovered) = caplog.records
    assert error.levelname == "ERROR" and error.exc_info is not None
    assert recovered.getMessage() == "The worker works again"
