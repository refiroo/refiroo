"""The API reference as files, for the public site (HD): ``python -m app.management.reference.static_site <guide build>``.

It writes into a built guide (``guide/dist``, or ``GUIDE_OUT``) the page ``api/index.html`` (the
engine's own ``render_page``, in its static form), the two OpenAPI documents it reads
(``api/management.json``, the engine's management API; ``api/stops.json``, the ``stops`` consumer API
of the guide's reference domain, ``guide/samples/model.json``), Scalar's bundled script
(``api/scalar/standalone.js``) and the shared header stylesheet (``brand/refiroo-header.css``).
The guide's own files already carry the logo and favicon. No instance and no database are involved:
the documents are produced from the code and the model file.

The engine does not use this: an instance serves ``/docs/api`` itself, from its route, which comes
before the guide's mount, so a page left in an instance's ``guide/dist`` is never served.
"""

import argparse
import base64
import json
import os
import secrets
import shutil
import sys
from pathlib import Path

from . import (
    BUNDLED_SCRIPT_PATH,
    SCALAR_SCRIPT,
    StaticSite,
    render_page,
    with_meta_policy,
)

_REPOSITORY = Path(__file__).resolve().parents[4]
EXAMPLE_MODEL = _REPOSITORY / "guide" / "samples" / "model.json"
EXAMPLE_API = "stops"
HEADER_STYLESHEET = _REPOSITORY / "frontend" / "public" / "brand" / "refiroo-header.css"
# The documents the page names, as paths in the built site; the page itself is the site's /docs/api/.
MANAGEMENT_FILE = "api/management.json"
EXAMPLE_FILE = f"api/{EXAMPLE_API}.json"
# The engine's default for the resolve limit (``CONSUMER_RESOLVE_MAX_ITEMS``), as the document words it.
_RESOLVE_MAX_ITEMS = 1_000


def _management_document() -> dict:
    """The management API's document, from the application's code. Building the application needs the
    engine's settings to be valid but touches no database; a throw-away key and no jobs satisfy them."""
    os.environ["SECRETS_ENCRYPTION_KEY"] = base64.urlsafe_b64encode(
        secrets.token_bytes(32)
    ).decode()
    os.environ["INTEGRATION_JOBS_ENABLED"] = "false"
    from ...main import create_app

    return create_app().openapi()


def build(out: Path) -> None:
    from ...engine.model.consumer_definitions import consumer_api
    from ...engine.model.consumer_openapi import consumer_openapi
    from ...engine.model.loader import load_model

    if not (out / "index.html").is_file():
        raise SystemExit(f"{out} is not a built guide (no index.html); build the guide first")
    site = StaticSite(base="/docs")
    model = load_model(EXAMPLE_MODEL)
    definition = consumer_api(model, EXAMPLE_API)
    if definition is None:
        raise SystemExit(f"{EXAMPLE_MODEL} has no consumer API '{EXAMPLE_API}'")
    # The OAuth token address is the one of whichever instance a reader runs; on the public site it is
    # shown as a path only.
    example = consumer_openapi(
        model,
        definition,
        root_path="",
        resolve_max_items=_RESOLVE_MAX_ITEMS,
        token_url="/oauth/token",
    )
    sources = [
        {
            "title": "Management API",
            "slug": "management",
            "url": f"{site.base}/{MANAGEMENT_FILE}",
            "default": True,
        },
        {
            "title": f"Example: {definition.name} · v{definition.contractVersion}",
            "slug": f"consumer-{definition.key}-v{definition.contractVersion}",
            "url": f"{site.base}/{EXAMPLE_FILE}",
        },
    ]
    page = with_meta_policy("bundled", render_page("bundled", "", sources, static=site))

    files = {
        "api/index.html": page,
        MANAGEMENT_FILE: json.dumps(_management_document(), indent=2) + "\n",
        EXAMPLE_FILE: json.dumps(example, indent=2) + "\n",
    }
    for name, text in files.items():
        target = out / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    script = out / BUNDLED_SCRIPT_PATH.removeprefix("/docs/")
    script.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SCALAR_SCRIPT, script)
    stylesheet = out / "brand" / "refiroo-header.css"
    stylesheet.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(HEADER_STYLESHEET, stylesheet)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Write the static API reference into a built guide."
    )
    parser.add_argument("guide_build", type=Path, help="the built guide: guide/dist, or GUIDE_OUT")
    arguments = parser.parse_args(argv)
    build(arguments.guide_build.resolve())
    print(f"API reference written to {arguments.guide_build / 'api'}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
