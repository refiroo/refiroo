"""Asking the provider, checking the answer's shape and recording the call (AP-D1, AP-D4).

``ask`` is the only code that calls a provider. An answer that does not match the requested schema
is a failed call, never a guess; any failure comes back as a sentence for the feature's warning,
so deterministic results stand. Every call becomes an ``ai_calls`` row, written by the ``record``
the caller passes: a job writes it in a session of its own, so a cancelled job keeps the record of
what it spent.
"""

import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ValidationError
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from ...common.pagination import Page, PageRequest, datetime_key, integer_key, paginate_statement
from ...models.database import AiCall
from .provider import ProposalRequest, ProviderError
from .registry import AiConfiguration, model_label, provider_label

_KEYS = (
    datetime_key("startedAt", AiCall.started_at, "started_at", descending=True),
    integer_key("sequenceId", AiCall.id, "id", descending=True),
)
# The period ``totals`` covers on Settings › AI.
TOTALS_DAYS = 30


@dataclass(frozen=True)
class Requester:
    user_id: int | None = None
    client_id: int | None = None


@dataclass(frozen=True)
class Outcome:
    answer: BaseModel | None
    # A sentence naming what failed, for the feature's warning; None when answered.
    failure: str | None
    provider: str
    model: str
    call_id: str


def ask(
    ai: AiConfiguration,
    request: ProposalRequest,
    *,
    record: Callable[[AiCall], None],
    requester: Requester,
    job_id: str | None = None,
) -> Outcome:
    provider = ai.provider
    if provider is None:
        raise RuntimeError("ask needs a provider; a feature is offered only when one is set")
    sent = json.dumps(request.context, ensure_ascii=False)
    started = datetime.now(UTC)
    clock = time.monotonic()
    answer: BaseModel | None = None
    data: Any = None
    model = model_label(provider)
    tokens_in = tokens_out = None
    failure_kind = failure = None
    try:
        answered = provider.propose(request)
        data, model = answered.data, answered.model or model
        tokens_in, tokens_out = answered.tokens_in, answered.tokens_out
        answer = request.answer.model_validate(data)
    except ProviderError as error:
        failure_kind, failure = error.kind, error.message
    except ValidationError as error:
        failure_kind = "malformed"
        failure = f"The answer does not have the shape asked for ({error.error_count()} problems)"
    except Exception as error:  # noqa: BLE001 - an operator's factory may fail in any way
        failure_kind, failure = "failed", f"The provider failed ({type(error).__name__})"
    row = AiCall(
        public_id=str(uuid4()),
        purpose=request.purpose,
        provider=provider_label(provider),
        model=model,
        send_level=ai.policy.level,
        prompt_version=request.prompt_version,
        requested_by_user_id=requester.user_id,
        requested_by_client_id=requester.client_id,
        job_id=job_id,
        started_at=started,
        duration_ms=round((time.monotonic() - clock) * 1000),
        bytes_in=len(request.instructions.encode()) + len(sent.encode()),
        bytes_out=len(json.dumps(data, ensure_ascii=False).encode()) if data is not None else 0,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        outcome="failed" if failure else "answered",
        failure_kind=failure_kind,
        failure=failure,
    )
    if ai.log_content:
        row.content = {
            "instructions": request.instructions,
            "context": request.context,
            "answer": data,
        }
        row.content_expires_at = started + timedelta(days=ai.log_content_days)
    record(row)
    return Outcome(answer, failure, row.provider, row.model, row.public_id)


def record_in(session: Session) -> Callable[[AiCall], None]:
    """Record in ``session``; the caller commits."""

    def record(row: AiCall) -> None:
        expire_content(session)
        session.add(row)
        session.flush()

    return record


def record_apart(session_factory: Callable[[], Session]) -> Callable[[AiCall], None]:
    """Record in a session and transaction of its own, committed at once."""

    def record(row: AiCall) -> None:
        with session_factory() as session:
            expire_content(session)
            session.add(row)
            session.commit()

    return record


def expire_content(session: Session, now: datetime | None = None) -> None:
    """Empty the kept requests and answers whose time is up, in one statement."""
    session.execute(
        update(AiCall)
        .where(AiCall.content_expires_at < (now or datetime.now(UTC)))
        .values(content=None, content_expires_at=None)
    )


def call_page(session: Session, *, page: PageRequest, page_size: int) -> Page[AiCall]:
    """Calls newest first."""
    expire_content(session)
    return paginate_statement(
        session,
        select(AiCall),
        keys=_KEYS,
        scope="ai-calls",
        filters={},
        page=page,
        page_size=page_size,
        message="AI call cursor is invalid",
    )


def last_call(session: Session) -> AiCall | None:
    expire_content(session)
    return session.scalar(
        select(AiCall).order_by(AiCall.started_at.desc(), AiCall.id.desc()).limit(1)
    )


@dataclass(frozen=True)
class Totals:
    days: int
    calls: int
    failed: int
    tokens_in: int
    tokens_out: int
    bytes_in: int
    bytes_out: int


def totals(session: Session, now: datetime | None = None) -> Totals:
    since = (now or datetime.now(UTC)) - timedelta(days=TOTALS_DAYS)
    calls, failed, tokens_in, tokens_out, bytes_in, bytes_out = session.execute(
        select(
            func.count(),
            func.count().filter(AiCall.outcome == "failed"),
            func.coalesce(func.sum(AiCall.tokens_in), 0),
            func.coalesce(func.sum(AiCall.tokens_out), 0),
            func.coalesce(func.sum(AiCall.bytes_in), 0),
            func.coalesce(func.sum(AiCall.bytes_out), 0),
        ).where(AiCall.started_at >= since)
    ).one()
    return Totals(TOTALS_DAYS, calls, failed, tokens_in, tokens_out, bytes_in, bytes_out)
