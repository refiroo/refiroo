"""The API reference's token (Product 0.12 C1, D240).

The reference page at ``/docs/api`` is served by the engine, so it can ask, from the same address, who
is signed in: the session's refresh cookie, which only ``/oauth`` reads (D234), names the person,
and the engine answers an access token for them. The cookie is read without renewing it, so the
page never uses a refresh token the application's own tabs hold (D269). The page's "try it" console
then sends what that person may do; a client's token may be pasted over it.
"""

from datetime import UTC, datetime
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from ...engine.identity import sessions, tokens
from ..dependencies import DbSession, started
from .oauth import REFRESH_COOKIE

router = APIRouter(tags=["oauth"])

_NO_STORE = {"Cache-Control": "no-store", "Pragma": "no-cache"}


def _refused(status: int, error: str, description: str) -> JSONResponse:
    return JSONResponse(
        {"error": error, "error_description": description}, status_code=status, headers=_NO_STORE
    )


def _from_elsewhere(request: Request) -> bool:
    """Asked by a page that is not the engine's own: only the reference, served from the address
    this request reached, may have a person's token (the cookie is ``SameSite=Strict`` besides)."""
    origin = request.headers.get("origin")
    if origin is None:
        return False
    own = urlsplit(str(request.base_url))
    return origin != f"{own.scheme}://{own.netloc}"


@router.post("/oauth/console-token", dependencies=[Depends(started)], include_in_schema=False)
def console_token(request: Request, session: DbSession) -> JSONResponse:
    """A ``management`` access token for the person signed in at this browser, ``{access_token,
    expires_in}``; ``401 not_signed_in`` without a session, which ended sessions included."""
    if _from_elsewhere(request):
        return _refused(403, "access_denied", "This was sent from another site.")
    presented = request.cookies.get(REFRESH_COOKIE)
    held = (
        sessions.open_session_of_refresh_token(session, presented, datetime.now(UTC))
        if presented
        else None
    )
    if held is None:
        return _refused(401, "not_signed_in", "No one is signed in at this browser.")
    user_session, user = held
    settings = request.app.state.identity_settings
    access_token = tokens.issue(
        session,
        settings,
        subject=user.public_id,
        kind="user",
        audience="management",
        session_id=user_session.public_id,
    )
    return JSONResponse(
        {"access_token": access_token, "expires_in": settings.access_token_seconds},
        headers=_NO_STORE,
    )
