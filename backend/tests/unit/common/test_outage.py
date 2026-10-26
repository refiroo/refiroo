"""What a background thread logs while it keeps failing (Base 0.9 C12; AGENTS.md "Error handling")."""

import logging
import time

import psycopg
import pytest
from psycopg import errors as psycopg_errors
from sqlalchemy.exc import DataError, OperationalError
from sqlalchemy.exc import TimeoutError as PoolTimeout

from app.common import outage as outage_module
from app.common.outage import (
    OutageLog,
    client_data_error,
    database_unavailable,
    database_unreachable,
)


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


def test_a_value_the_driver_refused_is_not_an_outage():
    """A NUL character in a text never reaches the server: the driver's `DataError` has no
    SQLSTATE, which must not read as an unreachable database (0.12 E1, F4). The same error from
    the server (it has a SQLSTATE) and a lost connection are told apart."""
    refused = psycopg.DataError("PostgreSQL text fields cannot contain NUL (0x00) bytes")
    wrapped = DataError("INSERT", {}, refused)
    for error in (refused, wrapped):
        assert client_data_error(error) is True
        assert database_unavailable(error) is None
    assert database_unreachable(wrapped) is False
    from_server = psycopg_errors.InvalidTextRepresentation("invalid input syntax")
    assert client_data_error(from_server) is False
    assert client_data_error(_database()) is False
    assert database_unavailable(_database()) == "unreachable"
    assert database_unavailable(psycopg.OperationalError("connection refused")) == "unreachable"


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
        # The server ended a transaction left idle past DATABASE_IDLE_TRANSACTION_TIMEOUT (0.11 N3,
        # D183): the connection is invalidated, but the database is reachable.
        (_database("25P03", invalidated=True), "transactionEnded"),
        (psycopg_errors.IdleInTransactionSessionTimeout("terminating connection"), "transactionEnded"),
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


def test_an_ended_transaction_is_one_plain_warning_naming_the_setting(caplog):
    """0.11 N3, D183: a stalled process whose transaction the server ended is told so, without a
    traceback, and not as an unreachable database."""
    logger = logging.getLogger("tests.outage")
    log = OutageLog(logger, "The worker", 2.0)
    with caplog.at_level("INFO", logger=logger.name):
        log.failed(_database("25P03", invalidated=True))
    [record] = caplog.records
    assert record.levelname == "WARNING" and record.exc_info is None
    assert "DATABASE_IDLE_TRANSACTION_TIMEOUT" in record.getMessage()
    assert "cannot reach" not in record.getMessage()


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
