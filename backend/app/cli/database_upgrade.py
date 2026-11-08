"""Upgrade the configured database with operator-facing errors and no traceback."""

import argparse
import sys

from ..db import DatabaseStartupError, create_database


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.cli.database_upgrade",
        description=(
            "Bring the configured database to the schema this version of the engine needs, "
            "creating it first when it is empty. It takes no options. It prints "
            "'Database migration completed successfully.' and exits 0, or prints the reason to "
            "standard error and exits 1."
        ),
    )
    parser.parse_args(argv)
    try:
        create_database()
    except DatabaseStartupError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print("Database migration completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
