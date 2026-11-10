"""The API reference page at ``/docs/api``: Scalar over the engine's OpenAPI documents (0.9 V1, V2).

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
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Query, Request
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy.orm import Session

from ...config import ApiReferenceScript
from ...engine.model.consumer_definitions import consumer_apis, served_versions
from ...engine.model.consumer_openapi import consumer_openapi_path
from ...engine.model.registry import resolve_model_snapshot
from ...errors import ApiError
from ..dependencies import DbSession

SCALAR_VERSION = "1.72.2"
SCALAR_SCRIPT = Path(__file__).resolve().parent / "scalar" / "standalone.js"
# Subresource integrity of the bundled script; the CDN serves the same bytes for the pinned version.
SCALAR_INTEGRITY = "sha384-mc6GgHVwdYe1ZSU5XmJBa2pe6QzCRDSd0Pk8TqiqM7iiAOFMKtpBTOOa2RZDHkYN"
SCALAR_CDN_URL = f"https://cdn.jsdelivr.net/npm/@scalar/api-reference@{SCALAR_VERSION}/dist/browser/standalone.js"
BUNDLED_SCRIPT_PATH = "/docs/api/scalar/standalone.js"

# The mount point is not "api-reference": the Scalar script mounts a second, unconfigured instance
# on an element with that id by itself, which would load web fonts and show hosted services.
_PAGE = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>refiroo API reference</title>
{canonical_element}    <link rel="icon" href="{favicon}" />
    <link rel="stylesheet" href="{stylesheet}" />
{theme_head}    <style>
      .rdm-header {{ position: fixed; inset: 0 0 auto 0; z-index: 100; }}
      body {{ margin: 0; }}
{extra_style}    </style>
    <script>{theme_script}</script>
  </head>
  <body>
{header_element}{older_element}    <div id="rdm-api-reference"></div>
    <script src="{script}"{integrity}></script>
    <script>window.rdmReference = Scalar.createApiReference("#rdm-api-reference", {configuration});</script>
{sign_in_element}    <script>{theme_wiring_script}</script>
  </body>
</html>
"""


_HEADER = """    <header class="rdm-header">
      <a class="rdm-mark" href="{home}" aria-label="refiroo home">
        <img src="{mascot}" alt="" />
        <img class="rdm-wordmark" src="{wordmark}" alt="refiroo" />
      </a>
      <nav class="rdm-tabs" aria-label="Documentation">
        <a class="rdm-tab" href="{docs}"><span class="rdm-full">Documentation</span><span class="rdm-short">Docs</span></a>
        <a class="rdm-tab" href="{api}" aria-current="page"><span class="rdm-full">API reference</span><span class="rdm-short">API</span></a>
      </nav>
{version_element}      <div class="rdm-spacer"></div>
      <label class="rdm-theme">
        <select id="rdm-theme" aria-label="Theme">
          <option value="system">System</option>
          <option value="light">Light</option>
          <option value="dark">Dark</option>
        </select>
      </label>
    </header>
"""


# The theme is the application's own choice (HD): ``rdm:theme:v1``, JSON "system", "light" or "dark".
# This runs in the head, before the first paint, and sets ``data-theme`` to the resolved light or dark.
# The colour theme (TH) is a second, independent key, ``rdm:scheme:v1`` (JSON "normal" or "purple"): Website purple
# sets ``data-scheme="purple"``, Normal sets nothing. A public host's page (its own look) leaves that part out.
_THEME = """
(function () {
  var KEY = "rdm:theme:v1";
  function read() {
    try {
      var value = JSON.parse(localStorage.getItem(KEY) || '"system"');
      return value === "light" || value === "dark" ? value : "system";
    } catch (error) { return "system"; }
  }
  function resolved() {
    var choice = read();
    if (choice !== "system") return choice;
    return matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  /*SCHEME*/
  function apply() { document.documentElement.dataset.theme = resolved(); scheme(); }
  apply();
  window.rdmTheme = { key: KEY, schemeKey: SCHEME_KEY, read: read, resolved: resolved, apply: apply };
})();
"""

_SCHEME = """var SCHEME_KEY = "rdm:scheme:v1";
  function scheme() {
    var purple = false;
    try { purple = JSON.parse(localStorage.getItem(SCHEME_KEY) || '"normal"') === "purple"; } catch (error) {}
    if (purple) document.documentElement.dataset.scheme = "purple";
    else delete document.documentElement.dataset.scheme;
  }"""
_NO_SCHEME = """var SCHEME_KEY = null;
  function scheme() {}"""

# Sets Scalar's colour mode at once (right after it is created, before the first paint) and wires the
# picker (when the header has one) and the other tabs to the choice: a pick here is saved for the
# application and the guide, and a pick made there (the storage event) or a change of the operating
# system's theme (while the choice is System) reaches this page.
_THEME_WIRING = """
(function () {
  var theme = window.rdmTheme;
  var picker = document.getElementById("rdm-theme");
  // A mounted Scalar does not switch on updateConfiguration, so its colour class on the body is set
  // here, and put back if Scalar changes it (it sets the class itself when it mounts).
  function paint() {
    var mode = theme.resolved();
    var body = document.body;
    if (body.classList.contains(mode + "-mode") && !body.classList.contains((mode === "dark" ? "light" : "dark") + "-mode")) return;
    body.classList.remove("light-mode", "dark-mode");
    body.classList.add(mode + "-mode");
  }
  var shown = null;
  function follow() {
    theme.apply();
    shown = document.documentElement.dataset.theme;
    if (picker) picker.value = theme.read();
    var reference = window.rdmReference;
    reference.updateConfiguration(Object.assign({}, reference.getConfiguration(), {
      forceDarkModeState: theme.resolved(),
    }));
    paint();
  }
  new MutationObserver(paint).observe(document.body, { attributes: true, attributeFilter: ["class"] });
  follow();
  if (picker) picker.addEventListener("change", function () {
    try { localStorage.setItem(theme.key, JSON.stringify(picker.value)); } catch (error) {}
    follow();
  });
  // A public site's own header toggles the theme itself (it stores the choice and sets data-theme): follow that too.
  new MutationObserver(function () {
    if (document.documentElement.dataset.theme !== shown) follow();
  }).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  window.addEventListener("storage", function (event) {
    if (event.key === null || event.key === theme.key || event.key === theme.schemeKey) follow();
  });
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", function () {
    if (theme.read() === "system") follow();
  });
})();
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
  // The Token URL field shows this engine's own token endpoint, as the browser reaches it.
  var tokenUrl = location.origin + __ROOT__ + "/oauth/token";
  function configured(credentials) {
    var securitySchemes = {};
    schemes.forEach(function (name) {
      securitySchemes[name] = { flows: { clientCredentials: Object.assign({ tokenUrl: tokenUrl }, credentials) } };
    });
    return securitySchemes;
  }
  reference.updateConfiguration(Object.assign({}, reference.getConfiguration(), {
    authentication: { securitySchemes: configured({}) },
  }));
  function ask() {
    return fetch(__ROOT__ + "/oauth/console-token", { method: "POST", credentials: "same-origin" })
      .then(function (response) { return response.ok ? response.json() : null; })
      .catch(function () { return null; });
  }
  function give(answer) {
    token = answer.access_token;
    expiresAt = Date.now() + answer.expires_in * 1000;
    var securitySchemes = configured({ token: token });
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

    # Both spellings answer: the documentation site is mounted at /docs and would otherwise take the
    # trailing-slash address.
    @router.get("/docs/api/", response_class=HTMLResponse, include_in_schema=False)
    @router.get("/docs/api", response_class=HTMLResponse)
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
            "title": f"{definition.name} · v{definition.contractVersion}"
            + ("" if served.is_current else " (deprecated)"),
            "slug": f"consumer-{definition.key}-v{definition.contractVersion}",
            "url": f"{root_path}{consumer_openapi_path(definition)}{suffix}",
        }
        for current in sorted(consumer_apis(model), key=lambda item: item.key)
        # The versions the API keeps beside the current one are documented too (0.13 DF3).
        for served in served_versions(model, current.key)
        for definition in (served.definition,)
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
    # The theme is the application's choice, picked in the page's header (HD), not Scalar's own toggle.
    "hideDarkModeToggle": True,
}


# Scalar leaves room under the page's fixed refiroo header (56 px, as in the guide and the interface).
HEADER_CSS = ":root { --scalar-custom-header-height: 56px; }"


# The public site's page-to-page flights (DOC12, E4): the mascot flies into the guide's logo and the page's content
# is the end of the home's terminal flight, under the names the website uses. Not under reduced motion.
_FLIGHT_STYLE = """      @media (prefers-reduced-motion: no-preference) {
        @view-transition { navigation: auto; }
        ::view-transition-group(*) { animation-duration: .65s; animation-timing-function: cubic-bezier(.4, 0, .2, 1); }
        ::view-transition-old(*), ::view-transition-new(*) { animation-duration: .65s; }
        .rdm-mark img:first-child { view-transition-name: mascot; }
        #rdm-api-reference { view-transition-name: terminal; }
      }
      .rdm-version { align-self: center; margin-inline-start: -8px; padding: 4px 8px; border: 1px solid var(--rdm-line); border-radius: 999px; color: var(--rdm-muted); font: 12px/1 ui-monospace, monospace; }
      .rdm-older { position: fixed; inset: var(--rdm-header-h, 56px) 0 auto 0; z-index: 99; box-sizing: border-box; height: 36px; padding: 8px 20px; border-bottom: 1px solid var(--rdm-line); background: var(--rdm-top); color: var(--rdm-ink); font: 14px/20px system-ui, sans-serif; text-align: center; }
      .rdm-older a { color: inherit; font-weight: 600; }
      @media (max-width: 50rem) { .rdm-version { display: none; } }
"""


@dataclass(frozen=True)
class ApiTheme:
    """A public host's header for the static API page (a theme directory's ``api/`` folder, written by the
    host's build from the same component as its other pages): ``head`` holds the elements for ``<head>``
    (its stylesheets and scripts), ``header`` the markup that stands where the refiroo header would."""

    head: str
    header: str


@dataclass(frozen=True)
class StaticSite:
    """Where the page's neighbours are when it is a file on a static host (HD): the public site, which
    has no engine behind it. The guide sits at ``base`` and ships the logo files and favicon at its
    root; the shared header stylesheet is written beside the page by ``static_site``.

    The public build's own settings (DOC12): ``site_url`` names the page's address as canonical,
    ``version`` is shown after the Documentation | API reference pair, ``older`` adds the line that
    links a version before the latest to ``/docs/``. The logo leads to the site's home, ``/``.

    ``theme`` (``PUBLIC_GUIDE_THEME``, DOC12) is the host's own header for the page: its markup replaces the
    refiroo header and its elements are added to the head. The host also names the header's height, as
    ``--rdm-header-h`` in its stylesheet, for the room Scalar leaves under it."""

    base: str = "/docs"
    site_url: str = ""
    version: str = ""
    older: bool = False
    theme: ApiTheme | None = None

    @property
    def stylesheet(self) -> str:
        return f"{self.base}/brand/refiroo-header.css"


def _links(root_path: str, static: StaticSite | None) -> dict[str, str]:
    """The addresses the header uses: the instance's ``/brand/`` files and routes, or, on the public
    site, the guide's own (the logo then leads to the site's home, W4-D5)."""
    if static is not None:
        base = static.base
        return {
            "favicon": f"{base}/favicon.png",
            "stylesheet": static.stylesheet,
            "home": "/",
            "mascot": f"{base}/refiroo-mascot.png",
            "wordmark": f"{base}/refiroo-wordmark.png",
            "docs": f"{base}/",
            "api": f"{base}/api/",
        }
    return {
        "favicon": f"{root_path}/brand/favicon.png",
        "stylesheet": f"{root_path}/brand/refiroo-header.css",
        "home": f"{root_path}/",
        "mascot": f"{root_path}/brand/refiroo-mascot.png",
        "wordmark": f"{root_path}/brand/refiroo-wordmark.png",
        "docs": f"{root_path}/docs/",
        "api": f"{root_path}/docs/api/",
    }


def render_page(
    script: ApiReferenceScript,
    root_path: str,
    sources: list[dict],
    *,
    static: StaticSite | None = None,
) -> str:
    """The page. With ``static`` it is the public site's copy: no sign-in script (no engine to ask),
    no "test request" button (nothing to send it to), and the header's links point inside the site."""
    configuration = {**OFFLINE_OPTIONS, "customCss": HEADER_CSS, "sources": sources}
    if static is not None:
        configuration["hideTestRequestButton"] = True
        # The line under the header (36 px) is part of what Scalar leaves room for; a host's header names its height.
        if static.theme is not None:
            extra = " + 36px" if static.older else ""
            configuration["customCss"] = (
                f":root {{ --scalar-custom-header-height: calc(var(--rdm-header-h, 56px){extra}); }}"
            )
        elif static.older:
            configuration["customCss"] = ":root { --scalar-custom-header-height: 92px; }"
    if script == "cdn":
        source, integrity = (
            SCALAR_CDN_URL,
            f' integrity="{SCALAR_INTEGRITY}" crossorigin="anonymous"',
        )
    else:
        source = f"{root_path}{BUNDLED_SCRIPT_PATH}"
        if static is not None:
            source = f"{static.base}/api/scalar/standalone.js"
        integrity = ""
    static_parts = _static_parts(static)
    links = {key: escape(value) for key, value in _links(root_path, static).items()}
    header = _HEADER.format(**links, version_element=static_parts["version_element"])
    if static is not None and static.theme is not None:
        header = static.theme.header
    sign_in = _SIGN_IN.replace("__ROOT__", json.dumps(root_path).replace("<", "\\u003c"))
    return _PAGE.format(
        **links,
        **static_parts,
        header_element=header,
        script=source,
        integrity=integrity,
        # JSON is a JavaScript literal; escaping "<" keeps a value from closing the script element.
        configuration=json.dumps(configuration).replace("<", "\\u003c"),
        theme_script=_THEME.replace(
            "/*SCHEME*/", _NO_SCHEME if static is not None and static.theme is not None else _SCHEME
        ),
        theme_wiring_script=_THEME_WIRING,
        sign_in_element="" if static is not None else f"    <script>{sign_in}</script>\n",
    )


def _static_parts(static: StaticSite | None) -> dict[str, str]:
    """The pieces of the page only the public build has; empty for an instance's page."""
    if static is None:
        return {
            "extra_style": "",
            "theme_head": "",
            "canonical_element": "",
            "version_element": "",
            "older_element": "",
        }
    canonical = ""
    if static.site_url:
        address = f"{static.site_url.rstrip('/')}{static.base}/api/"
        canonical = f'    <link rel="canonical" href="{escape(address)}" />\n'
    version = (
        f'      <span class="rdm-version">v{escape(static.version)}</span>\n'
        if static.version
        else ""
    )
    older = (
        f'    <div class="rdm-older">Guide for {escape(static.version)} · <a href="/docs/">Latest version</a></div>\n'
        if static.older
        else ""
    )
    return {
        "extra_style": _FLIGHT_STYLE,
        "theme_head": static.theme.head if static.theme is not None else "",
        "canonical_element": canonical,
        "version_element": version,
        "older_element": older,
    }


def _policy(script: ApiReferenceScript, page: str, *, header: bool) -> str:
    hashes = [
        "'sha256-" + base64.b64encode(hashlib.sha256(text.encode()).digest()).decode() + "'"
        for text in re.findall(r"<script>(.*?)</script>", page, flags=re.DOTALL)
    ]
    sources = ["'self'", *(["https://cdn.jsdelivr.net"] if script == "cdn" else []), *hashes]
    return "; ".join(
        [
            "default-src 'none'",
            f"script-src {' '.join(sources)}",
            "connect-src 'self'",
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data: blob:",
            "font-src 'self' data:",
            "object-src 'none'",
            # A <meta> policy cannot carry frame-ancestors (browsers ignore it and log an error).
            *(["frame-ancestors 'none'"] if header else []),
            "base-uri 'none'",
            "form-action 'none'",
        ]
    )


def with_meta_policy(script: ApiReferenceScript, page: str) -> str:
    """The page carrying its own Content-Security-Policy in a ``<meta>`` element, for a static host
    that sends no headers: the same policy as ``page_headers``, with the same hashes of the inline
    scripts, less ``frame-ancestors``, which only a header can set."""
    policy = _policy(script, page, header=False)
    meta = f'<meta http-equiv="Content-Security-Policy" content="{escape(policy)}" />'
    marker = '<meta charset="utf-8" />'
    return page.replace(marker, f"{marker}\n    {meta}", 1)


def page_headers(script: ApiReferenceScript, page: str) -> dict[str, str]:
    """The page's security headers (0.12 E1, C10). The page can ask ``/oauth/console-token`` for a
    management token from the browser's session cookie, so what runs in it is restricted to the
    engine's own: the bundled script (or the pinned CDN file, under its integrity hash) and the
    page's own inline scripts, each named by its hash, so a script that got into the page
    through a description a model author wrote does not run. Nothing is evaluated, nothing is
    embedded, and the page reaches only the engine. Styles may be inline (Scalar writes its own)."""
    policy = _policy(script, page, header=True)
    return {
        "Content-Security-Policy": policy,
        "X-Frame-Options": "DENY",
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "same-origin",
    }
