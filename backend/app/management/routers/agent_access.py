"""Agent access for security administrators (Product 0.16 AG1): the settings as read at start, the
agent clients, the assistants people sign in with, and each call. MCP itself is at ``/mcp``."""

from datetime import UTC, datetime

from fastapi import APIRouter, Query, Request
from sqlalchemy import select

from ...config import get_settings
from ...engine.agent_access import applications, calls
from ...engine.identity.clients import client_page
from ...models.database import AgentApplication, OAuthClient, User
from ..access import INSTANCE, AuthorizedRoute, requires
from ..dependencies import DbSession
from ..paging import PageQuery
from ..projections import identity as identity_present
from ..schemas.agent_access import (
    AgentAccessStatus,
    AgentApplicationCreate,
    AgentApplicationPage,
    AgentApplicationResponse,
    AgentCallPage,
    AgentCallResponse,
    AgentClientPage,
    AgentClientResponse,
)

router = APIRouter(route_class=AuthorizedRoute, prefix="/api/v1", tags=["agent-access"])


@router.get("/agent-access", response_model=AgentAccessStatus)
@requires("agent-access.read", at=INSTANCE)
def get_agent_access(request: Request, session: DbSession) -> AgentAccessStatus:
    """Whether assistants can reach the instance, where, under which limits, and the calls of the
    last 30 days. The settings are the environment's, read at start."""
    identity = request.app.state.identity_settings
    settings = get_settings()
    totals = calls.totals(session, datetime.now(UTC))
    return AgentAccessStatus(
        enabled=identity.agent_access,
        url=applications.endpoint(identity),
        ratePerMinute=settings.mcp_rate_per_minute,
        openRegistration=identity.agent_open_registration,
        redirectHosts=list(identity.agent_redirect_hosts),
        callsDays=settings.mcp_calls_days,
        calls30Days=totals.calls,
        lastCallAt=totals.last_call_at,
    )


@router.get("/agent-access/clients", response_model=AgentClientPage)
@requires("agent-access.read", at=INSTANCE)
def list_agent_clients(
    session: DbSession,
    paging: PageQuery,
    page_size: int = Query(default=50, ge=1, le=500, alias="pageSize"),
) -> AgentClientPage:
    """Agent clients with their access and their calls of the last 30 days."""
    page = client_page(session, active=None, kind="agent", page=paging, page_size=page_size)
    totals = calls.client_totals(session, [client.id for client in page.items], datetime.now(UTC))
    answered = identity_present.client_page(session, page)
    rows = {client.public_id: client.id for client in page.items}
    items = []
    for item in answered.items:
        held = totals.get(rows[item.id])
        items.append(
            AgentClientResponse(
                **item.model_dump(),
                calls30Days=held.calls if held else 0,
                lastCallAt=held.last_call_at if held else None,
            )
        )
    return AgentClientPage(items=items, **page.links())


def _application(row: AgentApplication, signed_in: int) -> AgentApplicationResponse:
    return AgentApplicationResponse(
        id=row.public_id,
        name=row.name,
        source=row.source,  # type: ignore[arg-type]
        returnsTo=list(dict.fromkeys(applications.returns_to(uri) for uri in row.redirect_uris)),
        blocked=row.blocked_at is not None,
        signedIn=signed_in,
        createdAt=row.created_at,
        lastUsedAt=row.last_used_at,
    )


def _counted(session: DbSession, row: AgentApplication, now: datetime) -> AgentApplicationResponse:
    """The application with the people who have an open session for it now, as the list counts."""
    return _application(row, applications.signed_in(session, [row.id], now).get(row.id, 0))


@router.get("/agent-access/applications", response_model=AgentApplicationPage)
@requires("agent-access.read", at=INSTANCE)
def list_agent_applications(
    session: DbSession,
    paging: PageQuery,
    page_size: int = Query(default=50, ge=1, le=500, alias="pageSize"),
) -> AgentApplicationPage:
    """The assistants people sign in with: what each says of itself, where it returns, and how many
    people have an open session for it."""
    page = applications.page_of(session, page=paging, page_size=page_size)
    counts = applications.signed_in(session, [row.id for row in page.items], datetime.now(UTC))
    return AgentApplicationPage(
        items=[_application(row, counts.get(row.id, 0)) for row in page.items], **page.links()
    )


@router.post("/agent-access/applications", response_model=AgentApplicationResponse, status_code=201)
@requires("agent-access.write", at=INSTANCE)
def post_agent_application(
    payload: AgentApplicationCreate, session: DbSession
) -> AgentApplicationResponse:
    """Register an assistant: it signs people in whether or not self-registration is on, and may
    return to any HTTPS address named here. ``422 AGENT_APPLICATION_INVALID`` for another address."""
    return _application(
        applications.register_by_administrator(session, payload.name, payload.redirectUris), 0
    )


@router.post("/agent-access/applications/{application_id}/block")
@requires("agent-access.write", at=INSTANCE)
def block_agent_application(application_id: str, session: DbSession) -> AgentApplicationResponse:
    """No one signs in with it any more and its sessions end, so it stops on its next call.
    ``404 AGENT_APPLICATION_NOT_FOUND``."""
    now = datetime.now(UTC)
    return _counted(session, applications.block(session, application_id, now), now)


@router.post("/agent-access/applications/{application_id}/restore")
@requires("agent-access.write", at=INSTANCE)
def restore_agent_application(application_id: str, session: DbSession) -> AgentApplicationResponse:
    """People may sign in with it again; the sessions blocking ended stay ended.
    ``404 AGENT_APPLICATION_NOT_FOUND``."""
    return _counted(session, applications.restore(session, application_id), datetime.now(UTC))


@router.get("/agent-access/calls", response_model=AgentCallPage)
@requires("agent-access.read", at=INSTANCE)
def list_agent_calls(
    session: DbSession,
    paging: PageQuery,
    page_size: int = Query(default=50, ge=1, le=500, alias="pageSize"),
) -> AgentCallPage:
    """Each tool call through ``/mcp``, newest first, with the names of its arguments and never their
    values."""
    page = calls.page_of(session, page=paging, page_size=page_size)
    users = {
        row.id: row
        for row in session.scalars(
            select(User).where(User.id.in_({i.user_id for i in page.items if i.user_id}))
        )
    }
    clients = {
        row.id: row
        for row in session.scalars(
            select(OAuthClient).where(
                OAuthClient.id.in_({i.client_id for i in page.items if i.client_id})
            )
        )
    }
    names = applications.names(
        session, {i.application_id for i in page.items if i.application_id is not None}
    )
    items = []
    for item in page.items:
        who = users[item.user_id] if item.user_id else clients[item.client_id]  # type: ignore[index]
        items.append(
            AgentCallResponse(
                id=item.public_id,
                occurredAt=item.occurred_at,
                principal=who.name,
                principalKind="user" if item.user_id else "client",
                principalId=who.public_id,
                application=names.get(item.application_id) if item.application_id else None,
                tool=item.tool,
                arguments=item.arguments,
                outcome=item.outcome,  # type: ignore[arg-type]
                durationMs=item.duration_ms,
                requestId=item.request_id,
            )
        )
    return AgentCallPage(items=items, **page.links())
