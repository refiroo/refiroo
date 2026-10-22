"""Check a restored copy of this instance's database and record the result (Product 0.11 O2).

Run from the backend directory with the instance's own ``DATABASE_URL``::

    python -m app.cli.restore_check --restored postgresql+psycopg://rdm@db/rdm_restore_check \\
        --backup rdm-20261021-0200.dump

The copy is prepared as startup would prepare it (and so changed), each workspace's release is
loaded and its data counted, and the result is recorded in the instance, where Settings ›
Operations and ``GET /api/v1/system/backup-rehearsals`` show it. Exit status 0 when it passed, 1
when it failed (recorded too), 2 when nothing was checked.
"""

import argparse
import sys

from sqlalchemy import URL, make_url
from sqlalchemy.exc import ArgumentError

from ..db import DRIVER, DatabaseStartupError, configured_url
from ..engine.backups.rehearsal import Rehearsal, SameDatabase, rehearse


def _restored(raw: str) -> URL:
    try:
        url = make_url(raw)
    except ArgumentError:
        raise SystemExit(_refusal(f"--restored is not a database URL: '{raw}'.")) from None
    if url.get_backend_name() != "postgresql" or url.drivername not in ("postgresql", DRIVER):
        raise SystemExit(
            _refusal(f"--restored must be a PostgreSQL URL (postgresql+psycopg://…), not '{raw}'.")
        )
    return url.set(drivername=DRIVER)


def _refusal(message: str) -> int:
    print(f"{message} Nothing was checked or recorded.", file=sys.stderr)
    return 2


def _report(rehearsal: Rehearsal) -> None:
    print(f"Backup rehearsal {'passed' if rehearsal.passed else 'failed'}.")
    if rehearsal.backup:
        print(f"Backup: {rehearsal.backup}")
    if rehearsal.revision_after:
        before = rehearsal.revision_before or "unversioned"
        print(f"Copy's revision: {before} -> {rehearsal.revision_after}")
    if rehearsal.data_as_of:
        print(f"Data as of: {rehearsal.data_as_of.isoformat()}")
    for item in rehearsal.workspaces:
        release = (
            f"{item.release['key']} {item.release['version']} (schema {item.release['schemaVersion']})"
            if item.release
            else "no release"
        )
        state = "served" if item.state == "served" else f"not served: {item.reason}"
        print(
            f"  {item.workspace_key}: {release}, {state}; {item.records} records "
            f"({item.live_records} live now), {item.relations} relationships, "
            f"{item.open_change_sets} open change sets, {item.publications} publications"
        )
    if not rehearsal.passed:
        print(f"{rehearsal.failure_message}", file=sys.stderr)
    print("Recorded in the instance (Settings › Operations). Delete the copy when done.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.cli.restore_check",
        description="Check a restored copy of this instance's database and record the result.",
    )
    parser.add_argument(
        "--restored",
        required=True,
        help="URL of the separate database the backup was restored into",
    )
    parser.add_argument("--backup", help="the backup's name, recorded with the result")
    arguments = parser.parse_args(argv)
    restored = _restored(arguments.restored)
    try:
        instance = configured_url()
        rehearsal = rehearse(instance, restored, arguments.backup)
    except SameDatabase as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except DatabaseStartupError as exc:
        # The instance itself: there is nowhere to record the result.
        return _refusal(f"The instance's database (DATABASE_URL) cannot be used: {exc}")
    _report(rehearsal)
    return 0 if rehearsal.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
