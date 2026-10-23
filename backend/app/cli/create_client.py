"""Create an OAuth client on the server and print its credentials once (Product 0.12 I1, D262).

    python -m app.cli.create_client --name "Nightly import" [--role steward --role operator]

Prints the client's ID and secret; the secret is shown only here. Each ``--role`` (a role's key) is
granted at the instance; without one the client may do nothing until a Security administrator
grants it a role (Z1). The system using it obtains a
token with the client credentials grant at ``POST /oauth/token``. This is how the first client is
made before anyone can sign in, and how an installation is automated without a browser.
"""

import argparse
import json
import sys

from pydantic import ValidationError

from ..db import DatabaseStartupError, SessionLocal, create_database
from ..engine.identity.clients import create_client
from ..errors import ApiError
from ..models.commands import ClientCreate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--name", required=True)
    parser.add_argument(
        "--role", action="append", default=[], help="a role's key, granted at the instance"
    )
    parser.add_argument("--json", action="store_true", help="print one JSON object")
    arguments = parser.parse_args(argv)
    try:
        payload = ClientCreate(name=arguments.name)
    except ValidationError:
        print("Not created: name is not valid.", file=sys.stderr)
        return 2
    try:
        create_database()
        with SessionLocal() as session:
            client, secret = create_client(session, payload, roles=tuple(arguments.role))
            client_id = client.public_id
    except DatabaseStartupError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except ApiError as exc:
        print(f"Not created: {exc.message}.", file=sys.stderr)
        return 2
    if arguments.json:
        print(json.dumps({"clientId": client_id, "clientSecret": secret}))
    else:
        print(f"client_id:     {client_id}\nclient_secret: {secret}")
        print("The secret is not shown again.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
