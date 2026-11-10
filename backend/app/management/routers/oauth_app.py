"""The sign-in steps for the application's own sign-in screen (Product 0.12 I5, D415, D416).

The same sign-in as the engine's pages in ``oauth.py``, answering in JSON: the browser application
draws the screens (so they follow its theme) and reads what happened as data. Every rule is in
``engine/identity/browser_sign_in.py`` and the engine modules it calls; these routes read JSON,
call them and present the outcome, as the pages do. The sign-in ends as theirs does: a one-time
code in an address of the application, which it exchanges at ``/oauth/token`` with its PKCE
verifier. A sign-in provider's button is the same redirect (``/oauth/providers/{key}/start``), and
the passkey ceremonies are the routes of ``oauth.py``, which already answer in JSON.
"""

from datetime import UTC, datetime
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import JSONResponse

from ...build_reference import build_reference
from ...config import ENGINE_VERSION
from ...engine.identity import (
    browser_sign_in,
    passkeys,
    providers,
    resets,
    second_factor,
    sign_in,
)
from ...engine.mail import links as mail_links
from ...engine.mail import settings as mail_settings
from ...errors import ApiError
from ...models.commands import (
    AppPasswordReset,
    AppPasswordSignIn,
    AppResetRequest,
    AppSecondFactor,
)
from .. import sign_in_pages as pages
from ..dependencies import DbSession, started
from . import oauth

# In maintenance mode every route answers 503 before a session is opened, as ``oauth.py``'s do.
router = APIRouter(
    prefix="/oauth/sign-in",
    tags=["oauth"],
    include_in_schema=False,
    dependencies=[Depends(started)],
)

_NO_STORE = oauth._NO_STORE


def _problem(status: int, error: str, message: str, wait_seconds: int = 0) -> JSONResponse:
    headers = {"Retry-After": str(wait_seconds)} if wait_seconds else {}
    body: dict[str, object] = {"error": error, "message": message}
    if wait_seconds:
        body["waitSeconds"] = wait_seconds
    return JSONResponse(body, status_code=status, headers={**_NO_STORE, **headers})


def _refused(refused: browser_sign_in.RequestRefused) -> JSONResponse:
    if refused.kind == "unknown_client":
        return _problem(
            400,
            "unknown_client",
            "This application is not one the engine signs people in to. Open it from its usual "
            "address and try again.",
        )
    return _problem(400, refused.error, refused.description or "The sign-in request is not valid.")


def _forged(request: Request, settings) -> JSONResponse | None:
    if oauth._foreign(request, settings):
        return _problem(403, "foreign_origin", "This was sent from another site.")
    return None


def _done(signed_in: browser_sign_in.SignedIn) -> JSONResponse:
    request = signed_in.request
    query = urlencode(
        {"code": signed_in.code, **({"state": request["state"]} if "state" in request else {})}
    )
    return JSONResponse(
        {"status": "signed_in", "redirect": f"{request['redirect_uri']}?{query}"},
        headers=_NO_STORE,
    )


@router.get("/options")
def options(
    request: Request,
    session: DbSession,
    response_type: str | None = None,
    client_id: str | None = None,
    redirect_uri: str | None = None,
    code_challenge: str | None = None,
    code_challenge_method: str | None = None,
    state: str | None = None,
) -> Response:
    """What the sign-in screen offers for an authorization request: whether a password is accepted
    (``local``, off for most people once a provider is in use, D365), whether a passkey can be
    used, and each enabled provider's button (a path to navigate to)."""
    settings = oauth._settings(request)
    checked = browser_sign_in.check_request(
        settings,
        {
            "response_type": response_type,
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "code_challenge": code_challenge,
            "code_challenge_method": code_challenge_method,
            "state": state,
        },
    )
    if isinstance(checked, browser_sign_in.RequestRefused):
        return _refused(checked)
    return JSONResponse(
        {
            "product": oauth._product(session),
            "local": providers.local_enabled(session),
            "reset": providers.local_enabled(session) and mail_settings.load(session) is not None,
            "passkey": passkeys.any_exist(session),
            "build": {
                "version": ENGINE_VERSION,
                "commit": build_reference().commit,
                "tag": build_reference().tag,
            },
            "providers": [
                {"key": provider.key, "name": provider.name, "start": path}
                for provider, path in (
                    (provider, oauth._query(f"/oauth/providers/{provider.key}/start", checked))
                    for provider in providers.enabled_providers(session)
                )
            ],
        },
        headers=_NO_STORE,
    )


def _second_step(
    session: DbSession, request: Request, user, token: str, stage: str, now: datetime
) -> JSONResponse:
    settings = oauth._settings(request)
    body: dict[str, object] = {
        "status": "second_factor",
        "step": token,
        "stage": stage,
        "app": second_factor.summary(session, user) is not None,
        "passkey": passkeys.has_any(session, user),
        "username": user.username,
    }
    if stage == "setup":
        made = second_factor.begin(session, settings, user, oauth._product(session), now)
        body["setup"] = {"secret": made.secret, "svg": made.svg}
    return JSONResponse(body, headers=_NO_STORE)


@router.post("/password")
def password(payload: AppPasswordSignIn, request: Request, session: DbSession) -> Response:
    """A username and password. The answer is ``signed_in`` with the address to go to, or
    ``second_factor`` with the step's token, or ``401 wrong_credentials`` (never saying which part
    was wrong) or ``429 slowed`` with the seconds to wait (D271)."""
    settings = oauth._settings(request)
    if forged := _forged(request, settings):
        return forged
    checked = browser_sign_in.check_request(settings, payload.request.fields())
    if isinstance(checked, browser_sign_in.RequestRefused):
        return _refused(checked)
    now = datetime.now(UTC)
    outcome = browser_sign_in.password_step(
        session, checked, payload.username, payload.password, oauth._address(request), now
    )
    if isinstance(outcome, sign_in.Refused):
        if outcome.reason == "slowed":
            return _problem(
                429,
                "slowed",
                "Too many attempts for this account or from this address. You can try again in "
                f"{pages.wait_text(outcome.wait_seconds)}. An administrator can reset the "
                "password.",
                outcome.wait_seconds,
            )
        return _problem(
            401,
            "wrong_credentials",
            "The username or password is not right. Check both and try again.",
        )
    if isinstance(outcome, browser_sign_in.SignedIn):
        return _done(outcome)
    return _second_step(session, request, outcome.user, outcome.token, outcome.stage, now)


@router.post("/second-factor")
def second_factor_step(payload: AppSecondFactor, request: Request, session: DbSession) -> Response:
    """The second step: ``signed_in``, ``recovery_codes`` (the set-up is confirmed; send the step
    again without a code to go on), ``401 wrong_code``, ``429 slowed``, or ``410 step_gone`` after
    five minutes or a second use."""
    settings = oauth._settings(request)
    if forged := _forged(request, settings):
        return forged
    outcome = browser_sign_in.second_factor_step(
        session,
        settings,
        payload.step,
        payload.code,
        payload.recovery,
        view=None,
        address=oauth._address(request),
        now=datetime.now(UTC),
    )
    if isinstance(outcome, browser_sign_in.StepGone):
        return _problem(
            410, "step_gone", "This sign-in took longer than five minutes, or was already used."
        )
    if isinstance(outcome, browser_sign_in.RequestRefused):
        return _refused(outcome)
    if isinstance(outcome, browser_sign_in.RecoveryCodes):
        return JSONResponse({"status": "recovery_codes", "codes": outcome.codes}, headers=_NO_STORE)
    if isinstance(outcome, browser_sign_in.SignedIn):
        return _done(outcome)
    if outcome.wait_seconds:
        return _problem(
            429,
            "slowed",
            "Too many wrong codes for this account or from this address. You can try again in "
            f"{pages.wait_text(outcome.wait_seconds)}. An administrator can reset the second "
            "factor.",
            outcome.wait_seconds,
        )
    if outcome.wrong:
        return _problem(
            401,
            "wrong_code",
            "That code is not right, or was already used. Wait for the next one and try again.",
        )
    return _problem(422, "code_required", "Type a code.")


# ---------------------------------------------------------------------------------------------
# A forgotten password (Product 0.12 I6, D420, D422)


def _link_gone() -> JSONResponse:
    return _problem(
        410,
        "link_gone",
        "This link has been used, replaced by a newer one, or has expired. Ask for a new one.",
    )


@router.post("/reset-request", status_code=202)
def reset_request(payload: AppResetRequest, request: Request, session: DbSession) -> Response:
    """Ask for a link to a new password with a username or an e-mail address. The answer is the
    same ``202`` whether or not such a person exists or can be written to; ``429 slowed`` counts
    the asks per name and per address (D271) and says nothing of any account; ``409
    mail_not_set_up`` when the engine cannot send mail at all."""
    settings = oauth._settings(request)
    if forged := _forged(request, settings):
        return forged
    try:
        wait = mail_links.request_reset(
            session,
            settings,
            payload.identifier,
            oauth._address(request),
            datetime.now(UTC),
        )
    except ApiError as refusal:
        if refusal.code != "MAIL_NOT_SET_UP":
            raise
        return _problem(
            409,
            "mail_not_set_up",
            "A password cannot be asked for by e-mail here. Ask a security administrator for a "
            "reset link.",
        )
    if wait:
        return _problem(
            429,
            "slowed",
            "Too many requests for this account or from this address. You can try again in "
            f"{pages.wait_text(wait)}.",
            wait,
        )
    return JSONResponse(
        {
            "status": "requested",
            "message": "If there is an account with that username or address that can be reset "
            "by e-mail, a link was sent to it.",
        },
        status_code=202,
        headers=_NO_STORE,
    )


@router.get("/reset")
def reset_page(
    request: Request, session: DbSession, token: str = Query("", max_length=128)
) -> Response:
    """What the reset page needs. Without a token: the product's name and whether a password can
    be asked for by e-mail (``available``). With one: who it is for and the password rule, or
    ``410 link_gone`` when it is used, replaced, expired or unknown."""
    product = oauth._product(session)
    if not token:
        return JSONResponse(
            {"product": product, "available": mail_settings.load(session) is not None},
            headers=_NO_STORE,
        )
    user = resets.link_user(session, token)
    if user is None:
        return _link_gone()
    return JSONResponse(
        {
            "product": product,
            "username": user.username,
            "minLength": oauth._settings(request).password_min_length,
        },
        headers=_NO_STORE,
    )


@router.post("/reset")
def reset_password(payload: AppPasswordReset, request: Request, session: DbSession) -> Response:
    """Set the password a valid link names, under the engine's rules (the same as
    ``/oauth/password``); the person's sessions end. ``410 link_gone`` for a link used, replaced,
    expired or unknown; ``422`` ``passwords_differ`` or ``password_rejected`` (with the rule that
    failed) leave the link as it was."""
    settings = oauth._settings(request)
    if forged := _forged(request, settings):
        return forged
    if not payload.token or resets.link_user(session, payload.token) is None:
        return _link_gone()
    if payload.password != payload.repeat:
        return _problem(
            422, "passwords_differ", "The two passwords differ. Type the same one twice."
        )
    try:
        used = resets.use_link(session, settings, payload.token, payload.password)
    except ApiError as refusal:
        return _problem(422, "password_rejected", refusal.message)
    if not used:
        return _link_gone()
    return JSONResponse({"status": "password_set"}, headers=_NO_STORE)
