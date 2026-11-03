"""The refiroo mark for the engine's own pages (sign-in, API reference): ``/brand/<file>``.

The pages the engine renders itself cannot load the interface's files, so the few images they show
are served here, from ``brand/``, a copy of ``frontend/public/brand/`` (a test keeps the stylesheet equal).
``refiroo-header.css`` is the header the API reference shares with the guide and the interface (HD).
The names are fixed; nothing else is served.
"""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

from ..errors import ApiError

BRAND_DIR = Path(__file__).resolve().parent / "brand"
BRAND_FILES = ("favicon.png", "refiroo-mascot.png", "refiroo-wordmark.png", "refiroo-header.css")


def brand_router() -> APIRouter:
    router = APIRouter(include_in_schema=False)

    @router.get("/brand/{name}")
    def brand_file(name: str) -> FileResponse:
        if name not in BRAND_FILES:
            raise ApiError(404, "NOT_FOUND", "There is no such file")
        return FileResponse(
            BRAND_DIR / name,
            media_type="text/css" if name.endswith(".css") else "image/png",
            headers={"Cache-Control": "public, max-age=86400"},
        )

    return router
