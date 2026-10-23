"""Databases for the browser runners, cloned from seeds (0.9.0-alpha.1 PG2, H1).

A runner's backend runs on a database of its own on the development server (``scripts/postgres.sh
start``, PG-D8), cloned from a seed in the seed store (``seeds.py``) on that server, and dropped
when the runner ends. The seeds are built once and reused until what built them changes:

* ``schema`` — the migrated empty database; the runner's backend installs its model at start.
* ``starter`` — the harness's starter records (``frontend/e2e/helpers/harness.mjs``) created
  through the API with the model the runner starts with; one seed per model content.
* ``volume`` — the Track S volume fixture at ``--scale``, with the volume model written to
  ``--model``.

Each ``clone`` prints one JSON line: ``database_url`` and the seed's payload (``records`` for the
starter seed, the dataset's identifiers for the volume seed)::

    cd backend && .venv/bin/python tests/browser_seeds.py clone starter --model /tmp/model.json
    .venv/bin/python tests/browser_seeds.py drop <database_url>

``RDM_TEST_DATABASE_SERVER`` names the server (the development server by default). A clone
whose runner was interrupted is dropped by a later ``clone`` once it is six hours old.
"""

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS.parent))
sys.path.insert(0, str(TESTS))

DEVELOPMENT_SERVER = "postgresql+psycopg://postgres@localhost:54320/postgres"
os.environ.setdefault("RDM_TEST_DATABASE_SERVER", DEVELOPMENT_SERVER)

import harness_identity
import postgres_server
import seeds
from sqlalchemy import URL, make_url, text
from sqlalchemy.exc import OperationalError

# A runner's clone is named r_<epoch seconds>_<random>; older than this, it was left behind.
CLONE_PREFIX = "r_"
ABANDONED_AFTER_SECONDS = 6 * 3600


def _create_starter_records(client: Any) -> dict[str, list[dict[str, Any]]]:
    """The records the harness's runners address, as the API created them."""

    def post(path: str, body: dict[str, Any]) -> dict[str, Any]:
        response = client.post(f"/api/v1{path}", json=body)
        if response.status_code != 201:
            raise RuntimeError(f"{path}: {response.status_code} {response.text}")
        return response.json()

    records: dict[str, list[dict[str, Any]]] = {"domain": [], "system": []}
    for object_type, application in (("domain", "rdm-master"), ("system", "rdm-systems")):
        label = "Domain" if object_type == "domain" else "System"
        for index in range(5):
            records[object_type].append(
                post(
                    "/objects",
                    {
                        "applicationKey": application,
                        "workspaceKey": "default",
                        "objectTypeKey": object_type,
                        "name": f"{label} {index:02d}",
                        "attributes": [
                            {"attributeTypeKey": f"{object_type}-code", "value": f"{object_type}-{index}"}
                        ],
                    },
                )
            )
    for suffix in ("Alpha", "Beta"):
        post(
            "/objects",
            {
                "applicationKey": "rdm-master",
                "workspaceKey": "default",
                "objectTypeKey": "codelist",
                "name": f"Codelist {suffix}",
                "parentObjectId": records["domain"][0]["id"],
                "attributes": [{"attributeTypeKey": "codelist-code", "value": suffix.lower()}],
            },
        )
    value = post(
        "/objects",
        {
            "applicationKey": "rdm-systems",
            "workspaceKey": "default",
            "objectTypeKey": "system-value",
            "name": "Value Alpha",
            "parentObjectId": records["system"][0]["id"],
            "attributes": [
                {"attributeTypeKey": "value-code", "value": "VA"},
                {"attributeTypeKey": "value-name", "value": "Value Alpha"},
            ],
        },
    )
    post(
        "/relations",
        {
            "relationTypeKey": "reference-has-system-representation",
            "fromObjectId": records["domain"][0]["id"],
            "toObjectId": value["id"],
        },
    )
    return records


def starter_seed(model_path: Path) -> str:
    """The name of the starter seed for the model at ``model_path``, registered on first use."""
    model_text = json.dumps(json.loads(model_path.read_text()), sort_keys=True)
    name = f"starter-{hashlib.sha256(model_text.encode()).hexdigest()[:6]}"

    def build(url: URL) -> dict[str, Any]:
        from harness_identity import TestClient

        from app.main import create_app

        with seeds.application_environment(url, model_path), TestClient(create_app()) as client:
            return {"records": _create_starter_records(client)}

    def inputs() -> list[str | Path]:
        return [model_text, TESTS / "browser_seeds.py", seeds.APP / "engine" / "model" / "bootstrap.py"]

    seeds.register(seeds.Seed(name, build, inputs, base="schema"))
    return name


def _prune() -> None:
    """Drop runner clones left behind by interrupted runs."""
    with seeds.admin() as server:
        names = server.scalars(
            text("SELECT datname FROM pg_database WHERE starts_with(datname, :prefix)"),
            {"prefix": CLONE_PREFIX},
        ).all()
    now = time.time()
    for name in names:
        started = name.removeprefix(CLONE_PREFIX).split("_", 1)[0]
        if started.isdigit() and now - int(started) > ABANDONED_AFTER_SECONDS:
            seeds.drop(name)


def clone(seed: str, *, model: Path | None, scale: float) -> dict[str, Any]:
    if seed == "schema":
        name, payload = "schema", {}
    elif seed == "starter":
        if model is None:
            raise SystemExit("clone starter needs --model, the model the runner starts with")
        name = starter_seed(model)
        payload = seeds.ensure(name)
    else:
        import volume_fixture

        if model is None:
            raise SystemExit("clone volume needs --model, where to write the volume model")
        model.write_text(json.dumps(volume_fixture.volume_model()))
        name = seeds.volume_seed(volume_fixture.scaled_shape(scale))
        payload = seeds.ensure(name)["dataset"]
    _prune()
    url = seeds.clone(name, f"{CLONE_PREFIX}{int(time.time())}_{uuid4().hex[:8]}")
    # The harness client every clone of the schema seed holds, and the settings its signing key
    # needs, so the runner's backend issues it tokens (0.12 I1, D263).
    harness = {
        **seeds.ensure("schema")["harness"],
        "settings": {
            "SECRETS_ENCRYPTION_KEY": harness_identity.SECRETS_ENCRYPTION_KEY,
            "TOKEN_SIGNING_KEY_DAYS": harness_identity.SIGNING_KEY_DAYS,
        },
    }
    return {"database_url": url.render_as_string(hide_password=False), **payload, "harness": harness}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    cloning = commands.add_parser("clone", help="clone a seed and print its URL and payload")
    cloning.add_argument("seed", choices=("schema", "starter", "volume"))
    cloning.add_argument("--model", type=Path)
    cloning.add_argument("--scale", type=float, default=0.1, help="volume: 1 is the full volume")
    dropping = commands.add_parser("drop", help="drop a database a clone printed")
    dropping.add_argument("database_url")
    arguments = parser.parse_args()
    try:
        if arguments.command == "clone":
            print(json.dumps(clone(arguments.seed, model=arguments.model, scale=arguments.scale)))
        else:
            seeds.drop(make_url(arguments.database_url).database)
    except OperationalError as error:
        server = postgres_server.url().render_as_string(hide_password=False)
        raise SystemExit(
            f"Cannot reach the PostgreSQL server at {server} for the browser runner's database. "
            "Start the development server with 'scripts/postgres.sh start', or set "
            f"RDM_TEST_DATABASE_SERVER to a superuser URL of a running server.\n{error.orig}"
        ) from None


if __name__ == "__main__":
    main()
