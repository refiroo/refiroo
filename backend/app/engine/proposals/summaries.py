"""The cache of the summaries (Product 0.16 AO1, AO-D15; AO2 and AO3 reuse it).

A summary is the words an answer gave to a set of facts. It is kept an hour under the hash of
everything that was asked, in the database, so the same request on another worker process is
answered with no provider call. Expired rows are removed in the statement that writes the next one.
"""

import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from ...models.database import AiSummary

# One hour: the preview's session (AO-D4).
LIFETIME = timedelta(hours=1)


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
