"""Run IDs: who owns a test database, readable from its name (TS2).

Several test runs share one PostgreSQL server (``postgres_server.py``). Each names the databases it
clones with its run ID, so a starting run can tell its own and the databases of runs that ended (it
drops those) from the databases of runs still alive (it leaves those). The ID is the owning
process's number and the time that process started: a process number reused by an unrelated process
has another start time, so it is never mistaken for the old run.

A database name is ``<kind>_<run ID>_<rest>`` (``t_`` a test's, ``r_`` a browser runner's), the run ID
``p<pid>_<start>``, for example ``t_p4012_1763020800_s1b2c3d4``. A ``pytest -n`` run's workers belong
to their controller's run: the controller sets ``RDM_TEST_RUN_ID`` before they start and they read it.
A browser runner's databases belong to the process that started ``browser_seeds.py`` (the runner),
which outlives the ``clone`` command that created them.
"""

import os
import re
import subprocess
import time
from uuid import uuid4

ENVIRONMENT = "RDM_TEST_RUN_ID"
RUN = re.compile(r"p(\d+)_(\d+)")
NAME = re.compile(rf"^[tr]_({RUN.pattern})_")
# The names runs gave before run IDs existed (an interrupted old run may have left them).
LEGACY_TEST = re.compile(r"^t_(session_(gw\d+_)?[0-9a-f]{8}|[0-9a-f]{16})$")
LEGACY_RUNNER = re.compile(r"^r_(\d+)_[0-9a-f]{8}$")
LEGACY_RUNNER_ABANDONED_AFTER_SECONDS = 6 * 3600


def started(pid: int) -> int | None:
    """When process ``pid`` started (epoch seconds, as ``ps`` reports it), None when it is not running."""
    result = subprocess.run(
        ("ps", "-o", "lstart=", "-p", str(pid)),
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "LC_ALL": "C"},
    )
    text = result.stdout.strip()
    if result.returncode != 0 or not text:
        return None
    try:
        return int(time.mktime(time.strptime(text, "%a %b %d %H:%M:%S %Y")))
    except ValueError:
        return None


def of_process(pid: int) -> str:
    """The run ID of the process ``pid``."""
    return f"p{pid}_{started(pid) or 0}"


def current() -> str:
    """This run's ID: the controller's (set in the environment before workers start), else its own."""
    run = os.environ.get(ENVIRONMENT)
    if run is None or not RUN.fullmatch(run):
        run = of_process(os.getpid())
        os.environ[ENVIRONMENT] = run
    return run


def is_live(run: str) -> bool:
    """Whether the process that owns ``run`` is still the one that started it."""
    match = RUN.fullmatch(run)
    if match is None:
        return False
    began = started(int(match.group(1)))
    if began is None:
        return False
    # A start time of 0 means ``ps`` could not tell when the owner started: the process number alone.
    return int(match.group(2)) in (0, began)


def name(kind: str = "t", run: str | None = None, label: str = "") -> str:
    """A new database name owned by ``run`` (this run by default); ``label`` ends up in the name."""
    return f"{kind}_{run or current()}_{label}{uuid4().hex[:12]}"


VOLUME_CLONE = re.compile(rf"^[tr]_{RUN.pattern}_v_")


def volume_holders(databases: list[str]) -> list[str]:
    """The volume seed clones among ``databases`` whose run is still live."""
    return [
        database
        for database in databases
        if VOLUME_CLONE.match(database) and is_live(run_of(database) or "")
    ]


def run_of(database: str) -> str | None:
    match = NAME.match(database)
    return match.group(1) if match else None


def abandoned(database: str, now: float | None = None) -> bool:
    """Whether ``database`` is a test or runner clone whose run has ended (safe to drop).

    A name that is not a clone's, and a clone of a live run, are not abandoned.
    """
    run = run_of(database)
    if run is not None:
        return not is_live(run)
    if LEGACY_TEST.match(database):
        return True
    legacy = LEGACY_RUNNER.match(database)
    if legacy is not None:
        return (now or time.time()) - int(legacy.group(1)) > LEGACY_RUNNER_ABANDONED_AFTER_SECONDS
    return False
