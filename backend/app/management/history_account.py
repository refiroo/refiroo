"""An account of what changed, read for the routes and the assistant's tool (Product 0.16 AO2).

The route and the tool run this one function, so a refusal, a fact and a statement are the same
whichever way they are asked. The workspace's or the record's facts are counted in the database over
the period; the provider words them; no transaction is held while it answers.
"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import SendLevel
from ..engine.proposals import calls, history_account, summaries
from ..engine.proposals.history_account import PeriodInvalid
from ..engine.proposals.registry import AiConfiguration
from ..engine.records.context import load_object
from ..errors import api_error
from ..models.database import Workspace
from .schemas.ai import (
    HistoryAccountResponse,
    HistoryFact,
    HistoryFactLink,
    HistoryFactsResponse,
    ImpactStatement,
)


def period_of(since: datetime, until: datetime, time_zone: str | None) -> history_account.Period:
    try:
        return history_account.Period.of(since, until, time_zone)
    except PeriodInvalid as invalid:
        raise api_error(422, "HISTORY_PERIOD_INVALID", str(invalid)) from None


def workspace_scope(session: Session, workspace_key: str) -> history_account.Scope:
    if session.scalar(select(Workspace.key).where(Workspace.key == workspace_key)) is None:
        raise api_error(404, "WORKSPACE_NOT_FOUND", f"Workspace '{workspace_key}' not found")
    return history_account.Scope(workspace_key)


def record_scope(session: Session, object_type_key: str, object_id: str) -> history_account.Scope:
    item = load_object(session, object_id, object_type_key)
    return history_account.Scope(item.workspace_key, item.id)


def fact_models(facts: list[history_account.Fact]) -> list[HistoryFact]:
    """The facts as the answer carries them, for the routes and the tool."""
    return [
        HistoryFact(
            id=fact.id,
            kind=fact.kind,  # type: ignore[arg-type]
            text=fact.text,
            count=fact.count,
            keys=fact.keys,
            link=HistoryFactLink(**fact.link) if fact.link else None,
        )
        for fact in facts
    ]


def facts_only(
    session: Session, scope: history_account.Scope, period: history_account.Period
) -> HistoryFactsResponse:
    """The engine's facts of ``scope`` over ``period`` and nothing else: no provider, no call row."""
    return HistoryFactsResponse(
        scope="record" if scope.record else "workspace",
        since=period.since,
        until=period.until,
        timeZone=period.zone_name,
        facts=fact_models(history_account.build_facts(session, scope, period)),
    )


def account(
    session: Session,
    ai: AiConfiguration,
    scope: history_account.Scope,
    period: history_account.Period,
    *,
    send_level: SendLevel | None,
    language: str | None,
    requester: calls.Requester,
) -> HistoryAccountResponse:
    """The facts of ``scope`` over ``period`` and the provider's words for them, at the send level
    the request chose (never above the instance's ceiling)."""
    ai = summaries.with_level(ai, send_level)
    facts = history_account.build_facts(session, scope, period)
    summary = history_account.explain(
        session,
        ai,
        facts,
        period,
        language=language or summaries.DEFAULT_LANGUAGE,
        requester=requester,
    )
    session.commit()
    return HistoryAccountResponse(
        scope="record" if scope.record else "workspace",
        since=period.since,
        until=period.until,
        timeZone=period.zone_name,
        facts=fact_models(summary.facts),
        statements=[
            ImpactStatement(text=item.text, factIds=list(item.fact_ids))
            for item in summary.statements
        ],
        removedStatements=summary.removed,
        failure=summary.failure,
        cached=summary.cached,
        callId=summary.call_id,
    )
