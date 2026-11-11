"""The steps of the browser's sign-in, once (Product 0.12 I5, D415).

The engine's HTML pages (I2) and the application's own sign-in screen (I5) both sign a person in
with the authorization code flow and PKCE. Everything that decides is here: whether an
authorization request is one the engine serves, what a password leads to, what a second step
accepts. The routes only read their input (a form or JSON), call these functions and present the
outcome (a page, a redirect or JSON), so a rule is never written twice.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from sqlalchemy.orm import Session

from ...models.database import User
from ..agent_access import applications
from . import providers, second_factor, sign_in
from .settings import IdentitySettings

# The fields of an authorization request that travel with the sign-in.
REQUEST_FIELDS = (
    "response_type",
    "client_id",
    "redirect_uri",
    "code_challenge",
    "code_challenge_method",
    "state",
)


@dataclass(frozen=True)
class RequestRefused:
    """An authorization request the engine does not serve. ``unknown_client`` (also an address that
    is not registered) is never redirected to (RFC 6749 §4.1.2.1); any other carries the error the
    application is sent back with."""

    kind: Literal["unknown_client", "error"]
    redirect_uri: str = ""
    error: str = ""
    description: str | None = None
    state: str | None = None


def check_request(
    settings: IdentitySettings, fields: dict[str, str | None], session: Session | None = None
) -> dict[str, str] | RequestRefused:
    """The authorization request's fields when the engine may serve it; otherwise why not. With
    ``session``, the client may also be an assistant people sign in with (0.16 AG-D12); the
    application's own sign-in screen passes none."""
    redirect_uri = fields.get("redirect_uri") or ""
    client_id = fields.get("client_id")
    if client_id == sign_in.BROWSER_CLIENT_ID:
        known = redirect_uri in settings.redirect_uris()
    else:
        application = (
            applications.usable(session, settings, client_id) if session is not None else None
        )
        known = application is not None and applications.accepts(
            application, redirect_uri, settings.agent_redirect_hosts
        )
    if not known:
        return RequestRefused("unknown_client")
    state = fields.get("state")
    if fields.get("response_type") != "code":
        return RequestRefused("error", redirect_uri, "unsupported_response_type", None, state)
    if fields.get("code_challenge_method") != "S256" or not sign_in.valid_challenge(
        fields.get("code_challenge")
    ):
        return RequestRefused(
            "error",
            redirect_uri,
            "invalid_request",
            "A PKCE code_challenge with code_challenge_method=S256 is required",
            state,
        )
    return {name: value for name in REQUEST_FIELDS if (value := fields.get(name)) is not None}


@dataclass(frozen=True)
class SignedIn:
    """The sign-in is whole: the one-time code the application exchanges for its session."""

    code: str
    request: dict[str, str]


@dataclass(frozen=True)
class NeedsSecondFactor:
    """The password was right and a second step follows: ``code`` or ``setup`` (I4b, D388)."""

    user: User
    token: str
    stage: str


def _issue(session: Session, checked: dict[str, str], user: User, now: datetime) -> SignedIn:
    code = sign_in.issue_code(
        session,
        user,
        redirect_uri=checked["redirect_uri"],
        code_challenge=checked["code_challenge"],
        signed_in_with="password",
        now=now,
        client_id=checked["client_id"],
    )
    return SignedIn(code, checked)


def password_step(
    session: Session,
    checked: dict[str, str],
    email: str,
    password: str,
    address: str | None,
    now: datetime,
) -> SignedIn | NeedsSecondFactor | sign_in.Refused:
    """An e-mail address and password: refused (a wrong pair, never saying which part, or a wait running,
    D271), a second step, or signed in."""
    outcome = sign_in.check_password(
        session,
        email,
        password,
        address,
        now,
        kept_only=not providers.local_enabled(session),
        finish=False,
    )
    if isinstance(outcome, sign_in.Refused):
        return outcome
    stage = second_factor.required_step(session, outcome)
    if stage is None:
        sign_in.complete(session, outcome, email, address)
        session.commit()
        return _issue(session, checked, outcome, now)
    return NeedsSecondFactor(
        outcome, second_factor.open_step(session, outcome, checked, stage, now), stage
    )


@dataclass(frozen=True)
class StepGone:
    """The step is unknown, used or older than five minutes."""


@dataclass(frozen=True)
class AskAgain:
    """The step stays open: nothing typed, a wrong code, or a wait (``wait_seconds``)."""

    user: User
    stage: str
    recovering: bool
    request: dict[str, str]
    wrong: bool = False
    wait_seconds: int = 0


@dataclass(frozen=True)
class RecoveryCodes:
    """The set-up is confirmed; the codes are shown once before the sign-in continues."""

    codes: list[str]


def second_factor_step(
    session: Session,
    settings: IdentitySettings,
    token: str,
    code: str,
    recovery: str,
    *,
    view: str | None,
    address: str | None,
    now: datetime,
) -> SignedIn | AskAgain | RecoveryCodes | StepGone | RequestRefused:
    """The second step of a password sign-in (I4b, D388): the code from the authenticator app or a
    recovery code; or, when the instance requires a second factor and the person has none, the
    set-up (a code to confirm, then the recovery codes before the sign-in continues). A wrong code
    is counted like a wrong password (D271). The step's token is the only state; it lasts five
    minutes and is used once."""
    loaded = second_factor.load_step(session, token, now)
    if loaded is None:
        return StepGone()
    row, user = loaded
    checked = check_request(settings, dict(row.request), session)
    if isinstance(checked, RequestRefused):
        return checked

    def done() -> SignedIn:
        second_factor.finish_step(session, row, user, address, now)
        session.commit()
        return _issue(session, checked, user, now)

    if row.stage == "codes":
        return done()
    typed = recovery.strip() or code.strip()
    recovering = bool(recovery.strip()) or (view == "recovery" and not code.strip())
    if not typed:
        return AskAgain(user, row.stage, recovering, checked)
    try:
        if row.stage == "setup":
            codes = second_factor.confirm(
                session, settings, user, typed, now=now, address=address, api=False
            )
        else:
            second_factor.check(
                session, settings, user, typed, now=now, address=address,
                kind="recovery" if recovering else "app",
            )  # fmt: skip
    except second_factor.CodeRefused as refused:
        return AskAgain(
            user,
            row.stage,
            recovering,
            checked,
            wrong=refused.reason == "wrong",
            wait_seconds=refused.wait_seconds,
        )
    if row.stage == "setup":
        second_factor.advance(row, "codes", now)
        session.commit()
        return RecoveryCodes(codes)
    return done()
