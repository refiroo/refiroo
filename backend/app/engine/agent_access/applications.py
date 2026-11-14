"""The assistants people sign in with (Product 0.16 AG-D12, RFC 7591).

An assistant is a public client: it holds no secret and proves each sign-in with PKCE. It registers
itself, when the operator allows, and may then return only to this computer (a loopback address, any
port, RFC 8252 §7.3) or an HTTPS host the operator listed; an administrator may register one with any
HTTPS address. Its name is its own claim, so the sign-in page says it is. Blocking one ends its
sessions, so it stops on its next call. One unused for 30 days, with no open session, is removed.
"""

from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from typing import Literal
from urllib.parse import urlsplit

from sqlalchemy import delete, exists, func, or_, select, update
from sqlalchemy.orm import Session

from ...common.addresses import LOOPBACK
from ...common.pagination import Page, PageRequest, integer_key, paginate_statement
from ...errors import api_error
from ...models.database import AgentApplication, UserSession
from ..identity import security_events, sign_in
from ..identity.settings import IdentitySettings

Source = Literal["registered", "administrator"]

_UNUSED_DAYS = 30
# Self-registration takes no credentials, so what it can store is bounded: registrations nobody has
# signed in with yet, across the instance.
MOST_UNUSED = 1000
# What one registration may carry (R-F10).
MOST_REDIRECT_URIS = 10
LONGEST_REDIRECT_URI = 2000
_KEYS = (integer_key("sequenceId", AgentApplication.id, "id"),)


class RegistrationRefused(Exception):
    """A registration this instance does not take: RFC 7591's ``error`` and why."""

    def __init__(self, error: str, description: str) -> None:
        super().__init__(description)
        self.error = error
        self.description = description


def is_loopback(uri: str) -> bool:
    parts = urlsplit(uri)
    return parts.scheme == "http" and parts.hostname in LOOPBACK and not parts.fragment


def _allowed(uri: str, hosts: tuple[str, ...] | None) -> bool:
    """Whether a redirect address may be registered; ``hosts`` None takes any HTTPS host."""
    if is_loopback(uri):
        return True
    parts = urlsplit(uri)
    return (
        parts.scheme == "https"
        and bool(parts.hostname)
        and not parts.fragment
        and (hosts is None or (parts.hostname or "").lower() in hosts)
    )


def _checked(
    name: str | None, redirect_uris: object, hosts: tuple[str, ...] | None
) -> tuple[str, list[str]]:
    if (
        not isinstance(redirect_uris, list)
        or not redirect_uris
        or not all(isinstance(uri, str) for uri in redirect_uris)
    ):
        raise RegistrationRefused("invalid_redirect_uri", "redirect_uris is a list of addresses")
    if len(redirect_uris) > MOST_REDIRECT_URIS or any(
        len(uri) > LONGEST_REDIRECT_URI for uri in redirect_uris
    ):
        raise RegistrationRefused(
            "invalid_redirect_uri",
            f"redirect_uris holds at most {MOST_REDIRECT_URIS} addresses of at most "
            f"{LONGEST_REDIRECT_URI} characters",
        )
    for uri in redirect_uris:
        if not _allowed(uri, hosts):
            raise RegistrationRefused(
                "invalid_redirect_uri",
                f"{uri!r} is not an address this instance lets an assistant return to",
            )
    if name is not None and not isinstance(name, str):
        raise RegistrationRefused("invalid_client_metadata", "client_name is text")
    return ((name or "").strip()[:200] or "An unnamed assistant"), list(redirect_uris)


def register(
    session: Session,
    settings: IdentitySettings,
    name: str | None,
    redirect_uris: object,
    address: str | None = None,
) -> AgentApplication:
    """An assistant registering itself. The caller checked that the operator allows it. Registrations
    from one address are slowed as failed sign-ins are, with a growing wait (R-F10). Commits."""
    now = datetime.now(UTC)
    wait = sign_in.seconds_to_wait(session, "", address, now, sign_in.REGISTER)
    if wait > 0:
        raise RegistrationRefused(
            "temporarily_unavailable",
            f"Too many registrations from this address; try again in {wait} seconds",
        )
    checked_name, uris = _checked(name, redirect_uris, settings.agent_redirect_hosts)
    unused = session.scalar(
        select(func.count())
        .select_from(AgentApplication)
        .where(AgentApplication.last_used_at.is_(None), AgentApplication.source == "registered")
    )
    if (unused or 0) >= MOST_UNUSED:
        raise RegistrationRefused(
            "temporarily_unavailable", "Too many assistants registered and never used; try later"
        )
    application = AgentApplication(name=checked_name, redirect_uris=uris, source="registered")
    session.add(application)
    sign_in.record_failure(session, "", address, now, sign_in.REGISTER)
    session.commit()
    return application


def register_by_administrator(
    session: Session, name: str, redirect_uris: list[str]
) -> AgentApplication:
    """An assistant an administrator registered. Commits."""
    try:
        checked_name, uris = _checked(name, redirect_uris, None)
    except RegistrationRefused as refused:
        raise api_error(422, "AGENT_APPLICATION_INVALID", refused.description) from None
    application = AgentApplication(name=checked_name, redirect_uris=uris, source="administrator")
    session.add(application)
    session.flush()
    security_events.record(
        session, "client", application.public_id, "application-registered",
        details={"name": application.name},
    )  # fmt: skip
    session.commit()
    return application


def usable(
    session: Session, settings: IdentitySettings, client_id: str | None
) -> AgentApplication | None:
    """The assistant of ``client_id`` while it may sign people in: agent access on, not blocked, and
    registered by an administrator when self-registration is off."""
    if not settings.agent_access or not client_id:
        return None
    application = session.scalar(
        select(AgentApplication).where(AgentApplication.public_id == client_id)
    )
    if application is None or application.blocked_at is not None:
        return None
    if application.source != "administrator" and not settings.agent_open_registration:
        return None
    return application


def accepts(
    application: AgentApplication, redirect_uri: str, hosts: tuple[str, ...] | None = None
) -> bool:
    """Whether a sign-in may return there: an address as registered, or for a loopback address the
    same one on any port, since a local assistant takes a free port each time (RFC 8252 §7.3). A
    self-registered assistant's other addresses count only while their host is still one the operator
    lists (``hosts``), as the list may have changed since it registered (R-F11)."""
    if redirect_uri in application.redirect_uris:
        return (
            application.source != "registered"
            or is_loopback(redirect_uri)
            or _allowed(redirect_uri, hosts)
        )
    if not is_loopback(redirect_uri):
        return False
    asked = urlsplit(redirect_uri)
    return any(
        is_loopback(uri)
        and (held := urlsplit(uri)).hostname == asked.hostname
        and held.path == asked.path
        for uri in application.redirect_uris
    )


def returns_to(redirect_uri: str) -> str:
    """Where a sign-in returns, in the words a person reads: the host, which they must see."""
    if is_loopback(redirect_uri):
        return "this computer (localhost)"
    return urlsplit(redirect_uri).hostname or redirect_uri


def endpoint(settings: IdentitySettings) -> str:
    """The canonical address of this instance's MCP endpoint."""
    return f"{settings.issuer.rstrip('/')}/mcp"


def names_this_instance(settings: IdentitySettings, resource: str) -> bool:
    """Whether a ``resource`` (RFC 8707) names this instance's endpoint."""
    return resource.rstrip("/").lower() == endpoint(settings).lower()


def _load(session: Session, public_id: str) -> AgentApplication:
    application = session.scalar(
        select(AgentApplication).where(AgentApplication.public_id == public_id).with_for_update()
    )
    if application is None:
        raise api_error(
            404, "AGENT_APPLICATION_NOT_FOUND", f"No assistant has the ID '{public_id}'"
        )
    return application


def block(session: Session, public_id: str, now: datetime) -> AgentApplication:
    """No one signs in with it any more, and its sessions end: it stops on its next call. Commits."""
    application = _load(session, public_id)
    if application.blocked_at is None:
        application.blocked_at = now
        session.execute(
            update(UserSession)
            .where(
                UserSession.agent_application_id == application.id, UserSession.ended_at.is_(None)
            )
            .values(ended_at=now, ended_reason="applicationBlocked", provider_id_token=None)
        )
        security_events.record(
            session, "client", application.public_id, "application-blocked",
            details={"name": application.name},
        )  # fmt: skip
    session.commit()
    return application


def restore(session: Session, public_id: str) -> AgentApplication:
    """It may sign people in again; the sessions blocking ended stay ended. Commits."""
    application = _load(session, public_id)
    if application.blocked_at is not None:
        application.blocked_at = None
        security_events.record(
            session, "client", application.public_id, "application-restored",
            details={"name": application.name},
        )  # fmt: skip
    session.commit()
    return application


def page_of(session: Session, *, page: PageRequest, page_size: int) -> Page[AgentApplication]:
    return paginate_statement(
        session,
        select(AgentApplication),
        keys=_KEYS,
        scope="agent-applications",
        filters={},
        page=page,
        page_size=page_size,
        message="Assistant list cursor is invalid",
    )


def signed_in(session: Session, application_ids: Iterable[int], now: datetime) -> dict[int, int]:
    """How many people each assistant has an open session for."""
    rows = session.execute(
        select(UserSession.agent_application_id, func.count(func.distinct(UserSession.user_id)))
        .where(
            UserSession.agent_application_id.in_(list(application_ids)),
            UserSession.ended_at.is_(None),
            UserSession.idle_ends_at > now,
            UserSession.ends_at > now,
        )
        .group_by(UserSession.agent_application_id)
    )
    return {application: count for application, count in rows}


def names(session: Session, application_ids: Iterable[int]) -> dict[int, str]:
    ids = list(application_ids)
    if not ids:
        return {}
    rows = session.execute(
        select(AgentApplication.id, AgentApplication.name).where(AgentApplication.id.in_(ids))
    )
    return {application_id: name for application_id, name in rows}


def expire(session: Session, now: datetime | None = None) -> int:
    """Remove self-registered assistants unused for 30 days that no open session holds; a blocked one
    stays, so it does not simply register again unseen. The caller commits."""
    cut = (now or datetime.now(UTC)) - timedelta(days=_UNUSED_DAYS)
    moment = now or datetime.now(UTC)
    open_session = exists().where(
        UserSession.agent_application_id == AgentApplication.id,
        UserSession.ended_at.is_(None),
        UserSession.ends_at > moment,
    )
    return session.execute(
        delete(AgentApplication).where(
            AgentApplication.source == "registered",
            AgentApplication.blocked_at.is_(None),
            or_(
                AgentApplication.last_used_at < cut,
                AgentApplication.last_used_at.is_(None) & (AgentApplication.created_at < cut),
            ),
            ~open_session,
        )
    ).rowcount
