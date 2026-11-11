"""Create the first administrator on the server (Product 0.12 I1, D235).

    python -m app.cli.create_admin --email ada@example.org --name "Ada Lovelace"

The password is read from the terminal twice, or from standard input with ``--password-stdin``, and
must meet the password rules (D252, its least length ``PASSWORD_MIN_LENGTH`` as amended by D276). There is no other
way to create a person without signing in,
and no setting turns authentication off. The person holds, at the instance, Security administration
and every role needed to set the instance up: Data owner, Model, Workspace and Integration
administrator, and Operator (D282). It is also the way back into an instance whose Security
administrators are all locked out.
"""

import argparse
import getpass
import sys

from pydantic import ValidationError

from ..config import get_settings
from ..db import DatabaseStartupError, SessionLocal, create_database
from ..engine.authorization.catalogue import FIRST_ADMINISTRATOR_ROLES
from ..engine.identity.users import create_user
from ..errors import ApiError
from ..models.commands import UserCreate


def _password(from_stdin: bool) -> str | None:
    if from_stdin:
        return sys.stdin.readline().rstrip("\r\n")
    if not sys.stdin.isatty():
        print(
            "No terminal to ask for the password: pipe it with --password-stdin.",
            file=sys.stderr,
        )
        return None
    first = getpass.getpass("Password: ")
    if getpass.getpass("Password again: ") != first:
        print("The passwords differ; nothing was created.", file=sys.stderr)
        return None
    return first


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument(
        "--password-stdin", action="store_true", help="read the password from standard input"
    )
    arguments = parser.parse_args(argv)
    try:
        payload = UserCreate(name=arguments.name, email=arguments.email)
    except ValidationError as exc:
        fields = ", ".join(str(error["loc"][0]) for error in exc.errors())
        print(f"Not created: {fields} is not valid.", file=sys.stderr)
        return 2
    password = _password(arguments.password_stdin)
    if password is None:
        return 2
    try:
        create_database()
        with SessionLocal() as session:
            user = create_user(
                session,
                payload,
                password=password,
                min_length=get_settings().password_min_length,
                roles=FIRST_ADMINISTRATOR_ROLES,
                local_kept=True,
            )
            user_id = user.public_id
    except DatabaseStartupError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except ApiError as exc:
        print(f"Not created: {exc.message}.", file=sys.stderr)
        return 2
    print(f"Created administrator '{payload.email}' ({user_id}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
