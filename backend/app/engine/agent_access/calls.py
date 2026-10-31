"""Each tool call through ``/mcp`` (Product 0.16 AG-D16, AG-D17).

A row names who called, through which assistant, the tool, how it ended and the names of its
arguments, never their values. The rate limit counts these rows in one statement, so it holds across
processes with no store of its own. Rows are removed after ``MCP_CALLS_DAYS``.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from ...common.pagination import Page, PageRequest, datetime_key, integer_key, paginate_statement
from ...models.database import AgentCall
from ..identity.authentication import Principal

Outcome = Literal["answered", "refused", "limited", "failed"]

_WINDOW = timedelta(minutes=1)
_KEYS = (
    datetime_key("occurredAt", AgentCall.occurred_at, "occurred_at", descending=True),
    integer_key("sequenceId", AgentCall.id, "id", descending=True),
)


def _caller(principal: Principal):
    return (
        AgentCall.user_id == principal.row_id
        if principal.kind == "user"
        else AgentCall.client_id == principal.row_id
    )


def record(
    session: Session,
    principal: Principal,
    *,
    tool: str,
    arguments: Iterable[str],
    outcome: Outcome,
    duration_ms: int,
    request_id: str | None,
) -> None:
    """One call in the caller's transaction."""
    session.add(
        AgentCall(
            user_id=principal.row_id if principal.kind == "user" else None,
            client_id=principal.row_id if principal.kind == "client" else None,
            application_id=principal.application_row_id,
            tool=tool[:120],
            arguments=sorted(argument[:120] for argument in arguments),
            outcome=outcome,
            duration_ms=duration_ms,
            request_id=request_id,
        )
    )


def seconds_to_wait(session: Session, principal: Principal, limit: int, now: datetime) -> int:
    """How long until this caller may call again; 0 while within ``limit`` calls a minute. A call
    refused for the limit does not count, so waiting always ends."""
    since = now - _WINDOW
    count, oldest = session.execute(
        select(func.count(), func.min(AgentCall.occurred_at)).where(
            _caller(principal), AgentCall.occurred_at > since, AgentCall.outcome != "limited"
        )
    ).one()
    if count < limit or oldest is None:
        return 0
    return max(1, int((oldest + _WINDOW - now).total_seconds()) + 1)


def page_of(session: Session, *, page: PageRequest, page_size: int) -> Page[AgentCall]:
    return paginate_statement(
        session,
        select(AgentCall),
        keys=_KEYS,
        scope="agent-calls",
        filters={},
        page=page,
        page_size=page_size,
        message="Agent call cursor is invalid",
    )


@dataclass(frozen=True)
class Totals:
    calls: int
    last_call_at: datetime | None


def totals(session: Session, now: datetime, days: int = 30) -> Totals:
    count, last = session.execute(
        select(func.count(), func.max(AgentCall.occurred_at)).where(
            AgentCall.occurred_at > now - timedelta(days=days)
        )
    ).one()
    return Totals(count, last)


def client_totals(
    session: Session, client_ids: Iterable[int], now: datetime, days: int = 30
) -> dict[int, Totals]:
    """Each client's calls in the last ``days``, and its last call."""
    rows = session.execute(
        select(AgentCall.client_id, func.count(), func.max(AgentCall.occurred_at))
        .where(
            AgentCall.client_id.in_(list(client_ids)),
            AgentCall.occurred_at > now - timedelta(days=days),
        )
        .group_by(AgentCall.client_id)
    )
    return {client: Totals(count, last) for client, count, last in rows}


def expire(session: Session, now: datetime | None = None, days: int = 90) -> int:
    """Remove the rows past their time. The caller commits."""
    cut = (now or datetime.now(UTC)) - timedelta(days=days)
    return session.execute(delete(AgentCall).where(AgentCall.occurred_at < cut)).rowcount
