"""Upgrade the configured database with operator-facing errors and no traceback."""

import sys

from ..db import DatabaseStartupError, create_database


def main() -> int:
    try:
        create_database()
    except DatabaseStartupError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print("Database migration completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
