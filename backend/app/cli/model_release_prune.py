"""Delete the stored model releases nothing refers to.

    python -m app.cli.model_release_prune [--unused] [--dry-run]

A release may be deleted when no workspace runs it and no record, change set, publication, job,
import profile or model mapping was made under it (0.12 MR1, D457). By default the command deletes
the retired ones among those; ``--unused`` also deletes active ones, such as releases installed for
a try and never activated. Their drafts stay, without their link to the release. One statement for
the whole set, in one transaction; it takes the installation lock, so it waits for an install in
progress. Exit status 0; 1 when the database cannot start or a release was referred to
meanwhile (nothing is deleted then).
"""

import argparse
import sys

from ..db import DatabaseStartupError, SessionLocal, create_database, lock_installation
from ..engine.model.release_lifecycle import deletable_releases, delete_unreferenced
from ..errors import ApiError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--unused",
        action="store_true",
        help="also delete active releases nothing refers to, not only retired ones",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="report what would be deleted and change nothing"
    )
    arguments = parser.parse_args(argv)
    try:
        create_database()
        with SessionLocal() as session:
            lock_installation(session)
            releases = deletable_releases(session, retired_only=not arguments.unused)
            for release in releases:
                print(
                    f"{release.public_id} {release.release_key}@{release.release_version}"
                    f" ({release.status}, schema {release.schema_version})"
                )
            if not arguments.dry_run:
                delete_unreferenced(session, releases)
                session.commit()
    except DatabaseStartupError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except ApiError as exc:
        # A release was referred to after it was listed: nothing was deleted.
        print(f"{exc.message}. Nothing was deleted; run the command again.", file=sys.stderr)
        return 1
    which = "unused" if arguments.unused else "retired and unused"
    if not releases:
        print(f"No {which} release; nothing to do.")
    elif arguments.dry_run:
        print(f"Dry run: {len(releases)} {which} release(s) would be deleted. Nothing changed.")
    else:
        print(f"Deleted {len(releases)} {which} release(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
