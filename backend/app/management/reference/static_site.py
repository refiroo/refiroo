"""The API reference as files, for the public site (HD): ``python -m app.management.reference.static_site <guide build>``.

It writes into a built guide (``guide/dist``, or ``GUIDE_OUT``) the page ``api/index.html`` (the
engine's own ``render_page``, in its static form), the two OpenAPI documents it reads
(``api/management.json``, the engine's management API; ``api/stops.json``, the ``stops`` consumer API
of the guide's reference domain, ``guide/samples/model.json``), Scalar's bundled script
(``api/scalar/standalone.js``) and the shared header stylesheet (``brand/refiroo-header.css``).
The public build's settings are read from the guide build's variables: ``PUBLIC_GUIDE_BASE`` (default ``/docs``),
``PUBLIC_GUIDE_SITE_URL`` (the canonical address), ``PUBLIC_GUIDE_VERSION`` and ``PUBLIC_GUIDE_OLDER``
(the version mark, and the line of a version before the latest); the logo leads to the site's home (``/``).
``PUBLIC_GUIDE_THEME`` (DOC12), a host's theme directory, may hold an ``api/`` folder with the host's own header for
this page: ``head.html`` (elements for the head), ``header.html`` (the markup that stands where the refiroo header
would), and ``theme/`` (files they name, copied to ``theme/`` in the build). In the text files ``/__BASE__`` stands for
the build's base path (``/docs``) and ``__VERSION__`` for the guide's version; the page then carries the host's header and not
the refiroo one. The guide's own files already carry the logo and favicon. No instance and no database are involved:
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
import tempfile
from pathlib import Path

from ...config import reload_settings
from ...engine.model.consumer_definitions import consumer_api
from ...engine.model.consumer_openapi import consumer_openapi
from ...engine.model.loader import load_model
from . import (
    BUNDLED_SCRIPT_PATH,
    SCALAR_SCRIPT,
    ApiTheme,
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
    engine's settings to be valid but touches no database; a throw-away key satisfies them. Every gated
    capability is switched on so the public reference lists every operation (model drafts, jobs, imports,
    consumer subscriptions...); job files would go to a scratch directory, never an instance's.
    The settings are put back afterwards: a caller in the same process (a test run) keeps its own."""
    from ...main import create_app

    with tempfile.TemporaryDirectory(prefix="rdm-reference-") as scratch:
        wanted = {
            "SECRETS_ENCRYPTION_KEY": base64.urlsafe_b64encode(secrets.token_bytes(32)).decode(),
            "INTEGRATION_JOBS_ENABLED": "true",
            "MODEL_ADMIN_MUTATIONS_ENABLED": "true",
            "WORKSPACE_ADMIN_MUTATIONS_ENABLED": "true",
            "CONSUMER_SUBSCRIPTIONS_ENABLED": "true",
            "JOB_FILE_DIR": scratch,
        }
        saved = {key: os.environ.get(key) for key in wanted}
        os.environ.update(wanted)
        try:
            return create_app().openapi()
        finally:
            for key, value in saved.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
            reload_settings()


_TEXT_SUFFIXES = {".html", ".css", ".js", ".mjs", ".json", ".svg"}


def _fill(text: str, base: str, version: str) -> str:
    return text.replace("/__BASE__", base).replace("__VERSION__", version)


def load_api_theme(theme: Path, out: Path, *, base: str, version: str) -> ApiTheme | None:
    """The host's header for the page, from ``<theme>/api/`` (see the module text); its ``theme/`` files are
    written to ``out/theme/``. None when the directory has no ``api/head.html`` and ``api/header.html``."""
    folder = theme / "api"
    head, header = folder / "head.html", folder / "header.html"
    if not (head.is_file() and header.is_file()):
        return None
    assets = folder / "theme"
    for source in sorted(assets.rglob("*")) if assets.is_dir() else []:
        if not source.is_file():
            continue
        target = out / "theme" / source.relative_to(assets)
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.suffix in _TEXT_SUFFIXES:
            target.write_text(
                _fill(source.read_text(encoding="utf-8"), base, version), encoding="utf-8"
            )
        else:
            shutil.copyfile(source, target)
    return ApiTheme(
        head=_fill(head.read_text(encoding="utf-8"), base, version),
        header=_fill(header.read_text(encoding="utf-8"), base, version),
    )


def build(
    out: Path,
    *,
    base: str = "/docs",
    site_url: str = "",
    version: str = "",
    older: bool = False,
    theme: Path | None = None,
) -> None:

    if not (out / "index.html").is_file():
        raise SystemExit(f"{out} is not a built guide (no index.html); build the guide first")
    api_theme = load_api_theme(theme, out, base=base, version=version) if theme else None
    site = StaticSite(base=base, site_url=site_url, version=version, older=older, theme=api_theme)
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
    script = out / BUNDLED_SCRIPT_PATH.removeprefix("/docs/")  # the page names it under ``base``
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
    # The public build's settings are the guide build's (guide/astro.config.mjs), read from the same variables.
    build(
        arguments.guide_build.resolve(),
        base=os.environ.get("PUBLIC_GUIDE_BASE") or "/docs",
        site_url=os.environ.get("PUBLIC_GUIDE_SITE_URL", ""),
        version=os.environ.get("PUBLIC_GUIDE_VERSION", ""),
        older=bool(os.environ.get("PUBLIC_GUIDE_OLDER")),
        theme=Path(os.environ["PUBLIC_GUIDE_THEME"])
        if os.environ.get("PUBLIC_GUIDE_THEME")
        else None,
    )
    print(f"API reference written to {arguments.guide_build / 'api'}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
