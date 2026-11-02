"""What the summaries share (Product 0.16 AO1, AO-D15, AO-D26; AO2 and AO3 reuse it).

A summary is the words an answer gave to a set of facts the engine wrote. The facts, the statements
that cite them, the context the provider is sent (at most ``FACT_LIMIT`` facts of a kind with each
kind's true total), the check of an answer (a statement that cites no fact that exists is dropped and
counted, AO-D2) and the asking itself are the same for every purpose: each purpose brings its
instructions, its prompt version and how its facts are made. The words are kept an hour under the
hash of everything that was asked, in the database, so the same request on another worker process is
answered with no provider call. Expired rows are removed in the statement that writes the next one.
"""

import hashlib
import json
from collections.abc import Collection, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from ...models.database import AiSummary
from . import calls
from .provider import ProposalRequest, Purpose
from .registry import AiConfiguration, model_label, provider_label

# One hour: the preview's session (AO-D4).
LIFETIME = timedelta(hours=1)
# The most facts of one kind the provider is sent; the person is given them all (AO-D14).
FACT_LIMIT = 40
# The longest before or after text sent for a change.
TEXT_LIMIT = 200
DEFAULT_LANGUAGE = "en"


class _Statement(BaseModel):
    text: str
    factIds: list[str] = Field(default_factory=list)


class SummaryAnswer(BaseModel):
    """What the provider answers: statements, each citing the facts it rests on."""

    statements: list[_Statement] = Field(default_factory=list)


@dataclass(frozen=True)
class Fact:
    id: str
    kind: str
    text: str
    path: str | None = None
    count: int | None = None
    # A change's two sides, for the provider's context only.
    before: Any = None
    after: Any = None
    # For an account of history (AO2): ``plain`` is the line without any name of a record, person,
    # change set or file, which the provider is sent in ``text``'s place; ``data`` holds those names,
    # sent only at send level ``values``; ``keys`` says what the fact counts; ``link`` where the
    # reader follows it.
    plain: str | None = None
    data: dict[str, Any] | None = None
    keys: dict[str, Any] = field(default_factory=dict)
    link: dict[str, Any] | None = None


@dataclass(frozen=True)
class Statement:
    text: str
    fact_ids: tuple[str, ...]


@dataclass(frozen=True)
class Summary:
    facts: list[Fact]
    statements: list[Statement]
    removed: int
    failure: str | None
    cached: bool
    call_id: str | None


def group_id(kind: str) -> str:
    return f"more-{kind}"


def cut(value: Any) -> Any:
    """A before or after for the context: text, or a definition as JSON text, longer than
    ``TEXT_LIMIT`` is cut."""
    if isinstance(value, dict | list):
        value = json.dumps(value, ensure_ascii=False, sort_keys=True)
    if isinstance(value, str) and len(value) > TEXT_LIMIT:
        return value[: TEXT_LIMIT - 1] + "…"
    return value


def context_of(
    facts: Sequence[Fact],
    language: str,
    kinds: Sequence[str],
    *,
    largest_first: Collection[str] = (),
    names: bool = False,
) -> dict[str, Any]:
    """What the provider is sent: at most ``FACT_LIMIT`` facts per kind, the largest counts first
    for the kinds in ``largest_first``, and per kind the true total with a group a statement may
    cite. A fact with a ``plain`` line is sent that line; its ``data`` (names) only with ``names``."""
    shown: list[dict[str, Any]] = []
    groups: list[dict[str, Any]] = []
    totals: dict[str, int] = {}
    for kind in kinds:
        of_kind = [fact for fact in facts if fact.kind == kind]
        if not of_kind:
            continue
        totals[kind] = len(of_kind)
        if kind in largest_first:
            of_kind = sorted(of_kind, key=lambda fact: -(fact.count or 0))
        for fact in of_kind[:FACT_LIMIT]:
            entry: dict[str, Any] = {
                "id": fact.id,
                "kind": kind,
                "text": fact.plain if fact.plain is not None else fact.text,
            }
            if fact.count is not None:
                entry["count"] = fact.count
            if fact.path:
                entry["path"] = fact.path
            if fact.before is not None:
                entry["before"] = cut(fact.before)
            if fact.after is not None:
                entry["after"] = cut(fact.after)
            if names and fact.data:
                entry["data"] = fact.data
            shown.append(entry)
        if len(of_kind) > FACT_LIMIT:
            groups.append(
                {
                    "id": group_id(kind),
                    "kind": kind,
                    "count": len(of_kind) - FACT_LIMIT,
                    "text": f"and {len(of_kind) - FACT_LIMIT} more {kind} facts",
                }
            )
    return {"language": language, "totals": totals, "facts": shown, "more": groups}


def checked(
    answer: SummaryAnswer, facts: Sequence[Fact], kinds: Sequence[str]
) -> tuple[list[Statement], int]:
    """The statements that cite at least one fact and no fact that does not exist (a group of the
    facts not shown counts as one), and how many were dropped (AO-D2)."""
    known = {fact.id for fact in facts} | {group_id(kind) for kind in kinds}
    kept: list[Statement] = []
    removed = 0
    for item in answer.statements:
        text = item.text.strip()
        ids = tuple(dict.fromkeys(item.factIds))
        if text and ids and all(identifier in known for identifier in ids):
            kept.append(Statement(text, ids))
        else:
            removed += 1
    return kept, removed


def explain(
    session: Session,
    ai: AiConfiguration,
    facts: list[Fact],
    *,
    purpose: Purpose,
    prompt_version: str,
    instructions: str,
    kinds: Sequence[str],
    largest_first: Collection[str] = (),
    names: bool = False,
    language: str,
    requester: calls.Requester,
    context_extra: dict[str, Any] | None = None,
) -> Summary:
    """The facts, worded. The same request inside the hour is answered from the cache with no call;
    otherwise the provider is asked, with no transaction held, and the call is recorded in
    ``session`` (the caller commits). No facts: nothing to word and no call."""
    provider = ai.provider
    assert provider is not None
    if not facts:
        return Summary(facts, [], 0, None, False, None)
    context = {
        **context_of(facts, language, kinds, largest_first=largest_first, names=names),
        **(context_extra or {}),
    }
    key = input_hash(
        purpose,
        prompt_version,
        [
            context,
            [(fact.id, fact.kind, fact.text, fact.count) for fact in facts],
            ai.policy.level,
            provider_label(provider),
            model_label(provider),
        ],
    )
    hit = find(session, purpose, key)
    if hit is not None:
        answer, call_id = hit
        return Summary(
            facts,
            [Statement(item["text"], tuple(item["factIds"])) for item in answer["statements"]],
            int(answer["removed"]),
            None,
            True,
            call_id,
        )
    # The provider can take seconds: no transaction is held while it answers (J48.8).
    session.commit()
    outcome = calls.ask(
        ai,
        ProposalRequest(
            purpose=purpose,
            instructions=instructions,
            prompt_version=prompt_version,
            context=context,
            answer=SummaryAnswer,
        ),
        record=calls.record_in(session),
        requester=requester,
    )
    if outcome.answer is None:
        return Summary(facts, [], 0, outcome.failure, False, outcome.call_id)
    assert isinstance(outcome.answer, SummaryAnswer)
    statements, removed = checked(outcome.answer, facts, kinds)
    if statements:
        store(
            session,
            purpose,
            key,
            {
                "statements": [
                    {"text": item.text, "factIds": list(item.fact_ids)} for item in statements
                ],
                "removed": removed,
            },
            outcome.call_id,
        )
    return Summary(facts, statements, removed, None, False, outcome.call_id)


def with_level(ai: AiConfiguration, level: Any) -> AiConfiguration:
    """``ai`` with the lower send level a request chose."""
    if level is None:
        return ai
    return replace(ai, policy=replace(ai.policy, level=level))


def input_hash(purpose: str, prompt_version: str, parts: Any) -> str:
    """The hash of what was asked: the purpose, the prompt's version and ``parts`` (the facts, the
    language, the send level, the provider and the model)."""
    text = json.dumps(
        [purpose, prompt_version, parts], ensure_ascii=False, sort_keys=True, default=str
    )
    return hashlib.sha256(text.encode()).hexdigest()


def find(
    session: Session, purpose: str, key: str, now: datetime | None = None
) -> tuple[dict[str, Any], str] | None:
    """The answer kept for ``key`` and the call that made it, while it is fresh."""
    row = session.execute(
        select(AiSummary.answer, AiSummary.call_id).where(
            AiSummary.purpose == purpose,
            AiSummary.input_hash == key,
            AiSummary.expires_at > (now or datetime.now(UTC)),
        )
    ).first()
    return (row[0], row[1]) if row else None


def store(
    session: Session,
    purpose: str,
    key: str,
    answer: dict[str, Any],
    call_id: str,
    now: datetime | None = None,
) -> None:
    """Keep ``answer`` for an hour, replacing any row for ``key``; expired rows go in one statement."""
    moment = now or datetime.now(UTC)
    session.execute(delete(AiSummary).where(AiSummary.expires_at <= moment))
    values = {
        "purpose": purpose,
        "input_hash": key,
        "answer": answer,
        "call_id": call_id,
        "expires_at": moment + LIFETIME,
    }
    session.execute(
        insert(AiSummary)
        .values(**values)
        .on_conflict_do_update(index_elements=[AiSummary.input_hash], set_=values)
    )
