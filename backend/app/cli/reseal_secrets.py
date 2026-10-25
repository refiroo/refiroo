"""Re-seal every sealed secret under a new ``SECRETS_ENCRYPTION_KEY`` (Product 0.12 K1, D414).

    NEW_SECRETS_ENCRYPTION_KEY=$(python -m app.cli.generate_key) python -m app.cli.reseal_secrets

Stop the engine first. The current key is ``SECRETS_ENCRYPTION_KEY`` in the environment, the new one
``NEW_SECRETS_ENCRYPTION_KEY`` (never an argument, which a shell keeps in its history). Every sealed
value is opened with the current key before any is written; if one does not open, nothing changes
and the command names it. On success set ``SECRETS_ENCRYPTION_KEY`` to the new key, keep it beside
the backups, and start the engine. ``--check`` only proves that every value opens with the current
key.
"""

import argparse
import os
import sys

from ..config import encryption_key, get_settings
from ..db import DatabaseStartupError, SessionLocal, create_database
from ..engine.identity.resealing import ResealRefused, reseal

NEW_KEY = "NEW_SECRETS_ENCRYPTION_KEY"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--check", action="store_true", help="only prove every sealed value opens; change nothing"
    )
    arguments = parser.parse_args(argv)
    try:
        old_key = get_settings().secrets_encryption_key
        new_key = encryption_key(os.environ.get(NEW_KEY, ""))
    except RuntimeError as exc:
        print(f"Not re-sealed: {exc}.", file=sys.stderr)
        return 2
    if old_key is None:
        print("Not re-sealed: SECRETS_ENCRYPTION_KEY is not set.", file=sys.stderr)
        return 2
    if new_key is None and not arguments.check:
        print(
            f"Not re-sealed: {NEW_KEY} is not set; generate one with "
            "`python -m app.cli.generate_key`.",
            file=sys.stderr,
        )
        return 2
    if new_key == old_key and not arguments.check:
        print(f"Not re-sealed: {NEW_KEY} is the current key.", file=sys.stderr)
        return 2
    try:
        create_database()
        with SessionLocal() as session:
            counts = reseal(session, old_key, new_key or old_key, check_only=arguments.check)
    except DatabaseStartupError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except ResealRefused as exc:
        print(f"Not re-sealed: {exc}.", file=sys.stderr)
        return 1
    total = sum(counts.values())
    detail = ", ".join(f"{count} {kind}" for kind, count in counts.items()) or "nothing sealed yet"
    if arguments.check:
        print(f"Every sealed value opens with the current key ({total}: {detail}).")
    else:
        print(f"Re-sealed {total} value(s): {detail}.")
        print(
            "Set SECRETS_ENCRYPTION_KEY to the new key before starting the engine.", file=sys.stderr
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
