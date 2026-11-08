"""Print a new key for ``SECRETS_ENCRYPTION_KEY``: 32 random bytes in URL-safe base64.

Keep it with the deployment's other secrets, outside the database it protects (C-D96, D253).
"""

import argparse
import base64
import secrets


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.cli.generate_key",
        description=(
            "Print a new key for SECRETS_ENCRYPTION_KEY: 32 random bytes in URL-safe base64, "
            "on one line. It takes no options and writes nothing else; keep the key with the "
            "deployment's other secrets, outside the database it protects."
        ),
    )
    parser.parse_args(argv)
    print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
