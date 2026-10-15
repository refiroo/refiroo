"""The API reference page at ``/docs``: Scalar over the engine's OpenAPI documents (0.9 V1, V2).

The sources are the management API and, beside it, every consumer API of the active release at its
contract version (V2), built per request, so a release that adds, removes or re-versions a
definition shows on the next page load.

The Scalar standalone script is pinned to one version and bundled beside this module, so the page
works without internet access; ``RDM_API_REFERENCE_SCRIPT=cdn`` loads the same version from a CDN
instead, held to the bundled file's bytes by its integrity hash. The routes stay outside the OpenAPI
document, so the OpenAPI locks do not change with the page.
"""

import json
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Query, Request
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy.orm import Session

from ...config import ApiReferenceScript
from ...engine.model.consumer_definitions import consumer_apis
from ...engine.model.consumer_openapi import consumer_openapi_path
from ...engine.model.registry import resolve_model_snapshot
from ...errors import ApiError
from ..dependencies import DbSession

SCALAR_VERSION = "1.72.2"
SCALAR_SCRIPT = Path(__file__).resolve().parent / "scalar" / "standalone.js"
# Subresource integrity of the bundled script; the CDN serves the same bytes for the pinned version.
SCALAR_INTEGRITY = "sha384-mc6GgHVwdYe1ZSU5XmJBa2pe6QzCRDSd0Pk8TqiqM7iiAOFMKtpBTOOa2RZDHkYN"
SCALAR_CDN_URL = (
    f"https://cdn.jsdelivr.net/npm/@scalar/api-reference@{SCALAR_VERSION}/dist/browser/standalone.js"
)
BUNDLED_SCRIPT_PATH = "/docs/scalar/standalone.js"

# The mount point is not "api-reference": the Scalar script mounts a second, unconfigured instance
# on an element with that id by itself, which would load web fonts and show hosted services.
_PAGE = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>RDM Engine API reference</title>
  </head>
  <body>
    <div id="rdm-api-reference"></div>
    <script src="{script}"{integrity}></script>
    <script>Scalar.createApiReference("#rdm-api-reference", {configuration});</script>
  </body>
</html>
"""


def api_reference_router(script: ApiReferenceScript) -> APIRouter:
    """The page and its bundled script, both left out of the OpenAPI document."""
    router = APIRouter(include_in_schema=False)

    @router.get("/docs", response_class=HTMLResponse)
    def api_reference(
        request: Request,
        session: DbSession,
        # Scalar writes the selected source's slug into the address (``?api=consumer-…``) and reads it
        # back on load, so a reloaded or shared link opens that source. The page itself ignores it.
        api: Annotated[str | None, Query()] = None,
    ) -> HTMLResponse:
        root_path = request.scope.get("root_path", "").rstrip("/")
        sources = [
            {
                "title": "Management API",
                "slug": "management",
                "url": f"{root_path}{request.app.openapi_url}",
                "default": True,
            },
            *consumer_sources(session, root_path),
        ]
        return HTMLResponse(render_page(script, root_path, sources))

    @router.get(BUNDLED_SCRIPT_PATH)
    def bundled_script() -> FileResponse:
        return FileResponse(
            SCALAR_SCRIPT,
            media_type="text/javascript",
            headers={"Cache-Control": "public, max-age=86400"},
        )

    return router


def consumer_sources(session: Session, root_path: str) -> list[dict]:
    """One source per consumer API of the default workspace's release, in ``consumerApi`` order as
    the API index lists them, labelled ``{name} · v{contractVersion}``. The slug is prefixed so no
    definition's key can take the management source's. While that model cannot be read (none
    installed, the registry unhealthy, an unsupported schema) the page still documents the
    management API, whose own routes then report the cause."""
    try:
        model = resolve_model_snapshot(session, None).model
    except ApiError:
        return []
    return [
        {
            "title": f"{definition.name} · v{definition.contractVersion}",
            "slug": f"consumer-{definition.key}-v{definition.contractVersion}",
            "url": f"{root_path}{consumer_openapi_path(definition)}",
        }
        for definition in sorted(consumer_apis(model), key=lambda item: item.key)
    ]


# Nothing on the page reaches outside the engine: no web fonts, telemetry, hosted agent, MCP
# generator, developer toolbar or link to the hosted API client. The options apply to every source.
OFFLINE_OPTIONS: dict = {
    "withDefaultFonts": False,
    "telemetry": False,
    "agent": {"disabled": True},
    "mcp": {"disabled": True},
    "showDeveloperTools": "never",
    "hideClientButton": True,
}


def render_page(script: ApiReferenceScript, root_path: str, sources: list[dict]) -> str:
    configuration = {**OFFLINE_OPTIONS, "sources": sources}
    if script == "cdn":
        source, integrity = SCALAR_CDN_URL, f' integrity="{SCALAR_INTEGRITY}" crossorigin="anonymous"'
    else:
        source, integrity = f"{root_path}{BUNDLED_SCRIPT_PATH}", ""
    return _PAGE.format(
        script=source,
        integrity=integrity,
        # JSON is a JavaScript literal; escaping "<" keeps a value from closing the script element.
        configuration=json.dumps(configuration).replace("<", "\\u003c"),
    )
