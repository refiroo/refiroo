"""Raise stored model releases of a schema older than the window to the window's schema, in place.

    python -m app.cli.model_release_raise [--dry-run]

Before 1.0 the schema window is cleaned at every release and the running engine does not carry old
schemas forward (0.12 L2a, D439). A developer database that holds releases of a schema that left the
window keeps working after this offline command rewrites each such release's schema version, canonical
document and hash; its identity (id, key, version) is unchanged, so workspaces, change sets and
publications that refer to it follow. A document of schema 0.8 or earlier also has its ``consumerApis``
rewritten from the old internal shape to the present syntax. A release whose raised document is not
valid, or whose hash another release already has, is left as it is and reported. Exit status 0 when
nothing failed, 1 otherwise. Run it with the service stopped; it takes the installation lock.
"""

import argparse
import shlex
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import DatabaseStartupError, SessionLocal, create_database, lock_installation
from ..engine.model.raising import (
    TARGET,
    Outcome,
    apply_raising,
    hashes_taken,
    plan_release,
    schema_side,
)
from ..models.database import ModelRelease

MODULE = "app.cli.model_release_raise"


def release_raise_command() -> str:
    """The command that raises the stored releases, as an operator pastes it."""
    backend_path = Path(__file__).resolve().parents[2]
    command = shlex.join([sys.executable, "-m", MODULE])
    return f"cd {shlex.quote(str(backend_path))} && {command}"


def plan(session: Session) -> tuple[list[Outcome], int]:
    """What raising each older release comes to, and how many releases are of a later schema."""
    releases = session.scalars(select(ModelRelease).order_by(ModelRelease.id)).all()
    taken = hashes_taken(session)
    outcomes: list[Outcome] = []
    later = 0
    for release in releases:
        side = schema_side(release.schema_version)
        if side == "inside":
            continue
        if side == "after":
            later += 1
            continue
        outcomes.append(plan_release(release, taken))
    return outcomes, later


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--dry-run", action="store_true", help="report what would change and change nothing"
    )
    arguments = parser.parse_args(argv)
    try:
        create_database()
        with SessionLocal() as session:
            lock_installation(session)
            outcomes, later = plan(session)
            failed = 0
            for outcome in outcomes:
                release = outcome.release
                name = f"{release.id} {release.release_key}@{release.release_version}"
                if outcome.skipped:
                    failed += 1
                    print(f"{name}: skipped, {outcome.skipped}")
                    continue
                print(f"{name}: schema {outcome.old_schema} -> {TARGET}")
                if not arguments.dry_run:
                    apply_raising(outcome)
            if not arguments.dry_run:
                session.commit()
    except DatabaseStartupError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if later:
        print(f"{later} release(s) are of a schema later than {TARGET} and were left as they are.")
    raised = len(outcomes) - failed
    if not outcomes:
        print(f"No stored release is of a schema older than {TARGET}; nothing to do.")
    elif arguments.dry_run:
        print(f"Dry run: {raised} release(s) would be raised, {failed} skipped. Nothing changed.")
    else:
        print(f"Raised {raised} release(s) to schema {TARGET}; {failed} skipped.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
