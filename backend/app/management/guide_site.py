"""The documentation at ``/docs``: the static site built from ``guide/``, served by the engine (0.13 DOC1).

The documentation (pages, and the step-by-step guides under ``/docs/guide/``) is served offline and
from the version the engine runs: the built files travel with the engine (the image carries
``/opt/refiroo/rdm-engine/guide/dist``, the checkout's layout; a development checkout has them in ``guide/dist`` once ``npm run build`` has run there). Nothing in the page reaches outside the engine, and the headers say
so: a browser that is told to load a font, a script or a frame from elsewhere refuses.

Where the build is absent (a checkout that has not built the guide) the engine starts and works as
usual, and ``/docs`` answers a page that says how to build it. The routes stay outside the OpenAPI
document. The API reference page lives at ``/docs/api``; its route is registered before this
mount, so the mount never shadows it.
"""

import base64
import hashlib
import re
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import Response
from starlette.types import Scope

GUIDE_PATH = "/docs"
# Where the built site is: the repository's build folder, which the image lays out the same way
# (``/opt/refiroo/rdm-engine/guide/dist`` beside ``backend/``).
_HERE = Path(__file__).resolve()
BUILT_GUIDE_CANDIDATES = (_HERE.parents[3] / "guide" / "dist",)

# Starlight writes inline scripts and Pagefind's search runs WebAssembly. A page's own inline scripts are
# allowed by their hash (``_page_headers``), so a script that got into a page some other way does not run; inline
# styles are allowed; everything else, fonts and images included, comes only from the engine.
_POLICY = (
    "default-src 'none'; "
    "script-src 'self'{hashes} 'wasm-unsafe-eval'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "font-src 'self'; "
    "connect-src 'self'; "
    "manifest-src 'self'; "
    "object-src 'none'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'none'"
)
_FIXED_HEADERS = {
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "same-origin",
}
GUIDE_HEADERS = {"Content-Security-Policy": _POLICY.format(hashes=""), **_FIXED_HEADERS}
_INLINE_SCRIPT = re.compile(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", re.DOTALL)


@lru_cache(maxsize=1024)
def _script_hashes(path: str, modified: int) -> str:
    """The CSP sources naming each inline script of a built page (cached by file and modification time)."""
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    digests = {
        base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
        for script in _INLINE_SCRIPT.findall(text)
    }
    return "".join(f" 'sha256-{digest}'" for digest in sorted(digests))


def _page_headers(response: Response) -> dict[str, str]:
    """The guide's headers for an answer: a built HTML page names its own inline scripts by hash."""
    path = getattr(response, "path", None)
    if path is None or not str(path).endswith(".html"):
        return GUIDE_HEADERS
    hashes = _script_hashes(str(path), Path(path).stat().st_mtime_ns)
    return {"Content-Security-Policy": _POLICY.format(hashes=hashes), **_FIXED_HEADERS}


_NOT_BUILT = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>The guide is not built here</title>
  </head>
  <body>
    <h1>The guide is not built here</h1>
    <p>This engine runs from a checkout that has not built the guide, so there is nothing to show at
    <code>/docs</code>. The engine itself works as usual.</p>
    <p>To build it, run <code>npm ci</code> and <code>npm run build</code> in the <code>guide</code>
    folder of the repository, then reload this page. The engine image includes the built guide.</p>
  </body>
</html>
"""


def built_guide() -> Path | None:
    """The folder holding the built site, or None when this installation has none."""
    for candidate in BUILT_GUIDE_CANDIDATES:
        if (candidate / "index.html").is_file():
            return candidate
    return None


class GuideFiles(StaticFiles):
    """The built site's files, each answer carrying the guide's security headers."""

    async def get_response(self, path: str, scope: Scope) -> Response:
        response = await super().get_response(path, scope)
        response.headers.update(_page_headers(response))
        return response


def guide_not_built_router() -> APIRouter:
    """The guide's routes when its build is absent: a page that says how to build it."""
    router = APIRouter(include_in_schema=False)

    def not_built() -> HTMLResponse:
        return HTMLResponse(_NOT_BUILT, status_code=404, headers=GUIDE_HEADERS)

    router.add_api_route(GUIDE_PATH, not_built, methods=["GET"])
    router.add_api_route(f"{GUIDE_PATH}/{{path:path}}", not_built, methods=["GET"])
    return router


def mount_guide(application: FastAPI) -> None:
    """Serve the built documentation at ``/docs``, or the page that says it is not built."""
    directory = built_guide()
    if directory is None:
        application.include_router(guide_not_built_router())
    else:
        application.mount(GUIDE_PATH, GuideFiles(directory=directory, html=True), name="guide")
