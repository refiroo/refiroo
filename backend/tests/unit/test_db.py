"""The database locks that make several processes take turns (0.11 N1): the installation lock, held
by an install's transaction, the startup lock, held by ``create_database`` while it checks,
migrates and runs the caller's startup writes, and the lock of a job submission's subject (N2)."""

import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import text

from app.db import (
    INSTALLATION_LOCK,
    STARTUP_LOCK,
    SessionLocal,
    create_database,
    lock_installation,
    lock_job_subject,
)


def _held(statement: str, lock: dict) -> bool:
    """Whether another session holds ``lock``: a try that fails while it is held."""
    with SessionLocal() as probe:
        taken = probe.scalar(text(statement), lock)
        probe.rollback()
        if taken and "xact" not in statement:
            probe.execute(text("SELECT pg_advisory_unlock(:namespace, :key)"), lock)
        return not taken


def test_a_second_install_waits_for_the_first_to_end(seeded):
    """Given one session holding the installation lock. When another takes it. Then it waits until
    the first transaction ends, and holds it then."""
    with SessionLocal() as first, SessionLocal() as second, ThreadPoolExecutor(1) as pool:
        lock_installation(first)
        waiting = pool.submit(lock_installation, second)
        with pytest.raises(TimeoutError):
            waiting.result(timeout=1)
        first.rollback()
        waiting.result(timeout=10)
        second.rollback()


def test_a_second_submission_of_one_subject_waits_for_the_first_to_end(seeded):
    """Given one session holding the lock of a kind and subject (0.11 N2, D171). When another
    takes it, it waits until the first transaction ends; another subject's is free meanwhile."""
    with (
        SessionLocal() as first,
        SessionLocal() as second,
        SessionLocal() as third,
        ThreadPoolExecutor(1) as pool,
    ):
        lock_job_subject(first, "inference", "draft-1")
        lock_job_subject(third, "inference", "draft-2")
        third.rollback()
        waiting = pool.submit(lock_job_subject, second, "inference", "draft-1")
        with pytest.raises(TimeoutError):
            waiting.result(timeout=1)
        first.rollback()
        waiting.result(timeout=10)
        second.rollback()


def test_startup_holds_its_lock_while_the_callers_writes_run(seeded):
    """When ``create_database`` runs a caller's startup writes. Then the startup lock is held while
    they run, a second startup waits for it, and it is released once the first returns."""
    observed = []
    release = threading.Event()

    def startup_writes():
        observed.append(_held("SELECT pg_try_advisory_lock(:namespace, :key)", STARTUP_LOCK))
        release.wait(10)

    with ThreadPoolExecutor(2) as pool:
        first = pool.submit(create_database, startup_writes)
        while not observed:
            time.sleep(0.05)
        second = pool.submit(create_database, lambda: observed.append("second"))
        with pytest.raises(TimeoutError):
            second.result(timeout=1)
        release.set()
        first.result(timeout=30)
        second.result(timeout=30)
    assert observed == [True, "second"]
    assert not _held("SELECT pg_try_advisory_lock(:namespace, :key)", STARTUP_LOCK)
    assert not _held("SELECT pg_try_advisory_xact_lock(:namespace, :key)", INSTALLATION_LOCK)
