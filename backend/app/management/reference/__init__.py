"""The API reference page at ``/docs``: Scalar over the engine's OpenAPI documents (0.9 V1, V2).

The sources are the management API and, beside it, every consumer API of the active release at its
contract version (V2), built per request, so a release that adds, removes or re-versions a
definition shows on the next page load.

The Scalar standalone script is pinned to one version and bundled beside this module, so the page
works without internet access; ``RDM_API_REFERENCE_SCRIPT=cdn`` loads the same version from a CDN
instead, held to the bundled file's bytes by its integrity hash. The routes stay outside the OpenAPI
document, so the OpenAPI locks do not change with the page.
"""

import base64
import hashlib
import json
import re
from html import escape
from pathlib import Path
from typing import Annotated
from urllib.parse import urlencode

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
SCALAR_CDN_URL = f"https://cdn.jsdelivr.net/npm/@scalar/api-reference@{SCALAR_VERSION}/dist/browser/standalone.js"
BUNDLED_SCRIPT_PATH = "/docs/scalar/standalone.js"

# The mount point is not "api-reference": the Scalar script mounts a second, unconfigured instance
# on an element with that id by itself, which would load web fonts and show hosted services.
_PAGE = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>refiroo API reference</title>
    <link rel="icon" href="{root_path}/brand/favicon.png" />
    <style>
      .brand-header {{ position: fixed; inset: 0 0 auto 0; z-index: 100; height: 48px; display: flex;
        align-items: center; gap: 10px; padding: 0 16px; box-sizing: border-box;
        background: #fff; border-bottom: 1px solid #e4e2dc; font: 600 14px system-ui, sans-serif; color: #1d1c1a; }}
      .brand-header img {{ display: block; height: 32px; width: auto; }}
      .brand-header img.wordmark {{ height: 16px; }}
      @media (prefers-color-scheme: dark) {{
        .brand-header {{ background: #18181b; border-bottom-color: #2c2c31; color: #ececee; }}
        .brand-header img.wordmark {{ filter: brightness(0) invert(.93); }}
      }}
    </style>
  </head>
  <body>
    <header class="brand-header">
      <img src="{root_path}/brand/refiroo-mascot.png" alt="" />
      <img class="wordmark" src="{root_path}/brand/refiroo-wordmark.png" alt="refiroo" />
      <span>API reference</span>
    </header>
    <div id="rdm-api-reference"></div>
    <script src="{script}"{integrity}></script>
    <script>window.rdmReference = Scalar.createApiReference("#rdm-api-reference", {configuration});</script>
    <script>{sign_in_script}</script>
  </body>
</html>
"""


# Signs the console in as the person signed in at this browser (0.12 C1, D240): the engine answers
# their token from the session cookie, and the console is given it for both kinds of document (the
# management API's scheme and the consumer APIs'). Without a session the console is as before, empty,
# for a client's token to be pasted. A request that goes out carrying this token in its last minute
# renews it first; a token pasted over it is never touched.
_SIGN_IN = """
(function () {
  var reference = window.rdmReference;
  var schemes = ["engineOAuth", "oauth2"];
  var token = null;
  var expiresAt = 0;
  function ask() {
    return fetch(__ROOT__ + "/oauth/console-token", { method: "POST", credentials: "same-origin" })
      .then(function (response) { return response.ok ? response.json() : null; })
      .catch(function () { return null; });
  }
  function give(answer) {
    token = answer.access_token;
    expiresAt = Date.now() + answer.expires_in * 1000;
    var securitySchemes = {};
    schemes.forEach(function (name) {
      securitySchemes[name] = { flows: { clientCredentials: { token: token } } };
    });
    reference.updateConfiguration(Object.assign({}, reference.getConfiguration(), {
      authentication: { preferredSecurityScheme: schemes[0], securitySchemes: securitySchemes },
      onBeforeRequest: beforeRequest,
    }));
  }
  function beforeRequest(context) {
    var ours = (context.requestBuilder.security || []).filter(function (item) {
      return item.value === token;
    });
    if (!ours.length || Date.now() < expiresAt - 60000) return;
    return ask().then(function (answer) {
      if (!answer) return;
      give(answer);
      ours.forEach(function (item) { item.value = answer.access_token; });
    });
  }
  ask().then(function (answer) { if (answer) give(answer); });
})();
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
        # The workspace whose consumer APIs the page lists (0.11 D39); the default workspace without it.
        workspace: Annotated[str | None, Query()] = None,
    ) -> HTMLResponse:
        root_path = request.scope.get("root_path", "").rstrip("/")
        sources = [
            {
                "title": "Management API",
                "slug": "management",
                "url": f"{root_path}{request.app.openapi_url}",
                "default": True,
            },
            *consumer_sources(session, root_path, workspace),
        ]
        page = render_page(script, root_path, sources)
        return HTMLResponse(page, headers=page_headers(script, page))

    @router.get(BUNDLED_SCRIPT_PATH)
    def bundled_script() -> FileResponse:
        return FileResponse(
            SCALAR_SCRIPT,
            media_type="text/javascript",
            headers={"Cache-Control": "public, max-age=86400"},
        )

    return router


def consumer_sources(session: Session, root_path: str, workspace: str | None = None) -> list[dict]:
    """One source per consumer API of the release ``workspace`` runs (the default workspace without
    it, 0.11 D39), in ``consumerApi`` order as the API index lists them, labelled ``{name} ·
    v{contractVersion}``, each document asked for that workspace. The slug is prefixed so no
    definition's key can take the management source's. While that model cannot be read (none
    installed, the registry unhealthy, an unsupported schema, an unknown workspace) the page still
    documents the management API, whose own routes then report the cause."""
    try:
        model = resolve_model_snapshot(session, workspace).model
    except ApiError:
        return []
    suffix = f"?{urlencode({'workspace': workspace})}" if workspace else ""
    return [
        {
            "title": f"{definition.name} · v{definition.contractVersion}",
            "slug": f"consumer-{definition.key}-v{definition.contractVersion}",
            "url": f"{root_path}{consumer_openapi_path(definition)}{suffix}",
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


# Scalar leaves room under the page's fixed refiroo header for this height.
HEADER_CSS = ":root { --scalar-custom-header-height: 48px; }"


def render_page(script: ApiReferenceScript, root_path: str, sources: list[dict]) -> str:
    configuration = {**OFFLINE_OPTIONS, "customCss": HEADER_CSS, "sources": sources}
    if script == "cdn":
        source, integrity = (
            SCALAR_CDN_URL,
            f' integrity="{SCALAR_INTEGRITY}" crossorigin="anonymous"',
        )
    else:
        source, integrity = f"{root_path}{BUNDLED_SCRIPT_PATH}", ""
    return _PAGE.format(
        root_path=escape(root_path),
        script=source,
        integrity=integrity,
        # JSON is a JavaScript literal; escaping "<" keeps a value from closing the script element.
        configuration=json.dumps(configuration).replace("<", "\\u003c"),
        sign_in_script=_SIGN_IN.replace("__ROOT__", json.dumps(root_path).replace("<", "\\u003c")),
    )


def page_headers(script: ApiReferenceScript, page: str) -> dict[str, str]:
    """The page's security headers (0.12 E1, C10). The page can ask ``/oauth/console-token`` for a
    management token from the browser's session cookie, so what runs in it is restricted to the
    engine's own: the bundled script (or the pinned CDN file, under its integrity hash) and the
    page's own two inline scripts, each named by its hash, so a script that got into the page
    through a description a model author wrote does not run. Nothing is evaluated, nothing is
    embedded, and the page reaches only the engine. Styles may be inline (Scalar writes its own)."""
    hashes = [
        "'sha256-" + base64.b64encode(hashlib.sha256(text.encode()).digest()).decode() + "'"
        for text in re.findall(r"<script>(.*?)</script>", page, flags=re.DOTALL)
    ]
    sources = ["'self'", *(["https://cdn.jsdelivr.net"] if script == "cdn" else []), *hashes]
    policy = "; ".join(
        [
            "default-src 'none'",
            f"script-src {' '.join(sources)}",
            "connect-src 'self'",
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data: blob:",
            "font-src 'self' data:",
            "object-src 'none'",
            "frame-ancestors 'none'",
            "base-uri 'none'",
            "form-action 'none'",
        ]
    )
    return {
        "Content-Security-Policy": policy,
        "X-Frame-Options": "DENY",
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "same-origin",
    }
