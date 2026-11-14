"""How long each test takes: one file beside the test server's data (TS4).

Every pytest run records the duration of the tests it ran (``conftest.py``); ``affected.py`` reads
the file for a selection's expected time. The file is ``durations.json`` in the data root of the
test server (``postgres_server.ROOT``, on the local volume): test node ID -> seconds, the latest
value. It is not in git and not written in CI, against an external server
(``RDM_TEST_DATABASE_SERVER``) or by a recording run under coverage. Runs side by side (TS2) merge into it under a lock, so none clobbers
another.
"""

import fcntl
import json
import os
from pathlib import Path

import postgres_server

FILE = postgres_server.ROOT / "durations.json"


def enabled() -> bool:
    """False in CI and against an external server, which have no local data root, and in a recording
    run (``journey_trace --record``): coverage slows the tests, so their times are not the tests'."""
    return not (
        os.environ.get("CI")
        or os.environ.get(postgres_server.EXTERNAL_SERVER)
        or os.environ.get("RDM_JOURNEY_COVERAGE")
    )


def load(file: Path = FILE) -> dict[str, float]:
    try:
        data = json.loads(file.read_text())
    except OSError, ValueError:
        return {}
    return {key: float(value) for key, value in data.items()} if isinstance(data, dict) else {}


def record(seconds: dict[str, float], file: Path = FILE) -> None:
    """Merge ``seconds`` (node ID -> duration) into the file, the new value replacing the old."""
    if not seconds or not file.parent.is_dir():
        return
    with (file.parent / f"{file.name}.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        merged = load(file) | seconds
        temporary = file.with_name(f"{file.name}.{os.getpid()}.tmp")
        temporary.write_text(json.dumps(dict(sorted(merged.items())), indent=0))
        temporary.replace(file)
