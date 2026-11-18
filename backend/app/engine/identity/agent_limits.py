"""How long an assistant stays signed in (Product 0.17 AS-D2, AS-D3).

An assistant's session (a ``UserSession`` with ``agent_application_id``) has limits of its own: it
ends after ``session_idle_days`` without a renewal and ``session_days`` in all. They are one row an
administrator sets on the Agent access page; without a row the defaults hold. The browser keeps
``SESSION_IDLE_HOURS`` and ``SESSION_DAYS``. A change applies to a session's next renewal (days
without use) and to new sign-ins (days in all). Saving is a security event.
"""

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...errors import api_error, version_conflict
from ...models.database import AgentAccessSettings
from . import security_events

AGGREGATE = "agent-access-settings"
# The one setting's identity in a security event.
EVENT_ID = "agent-access"
DEFAULT_IDLE_DAYS = 30
DEFAULT_DAYS = 90
LIMIT_DAYS = 365


@dataclass(frozen=True)
class Limits:
    idle_days: int
    days: int
    version: int
    updated_at: datetime | None


def _row(session: Session, *, for_update: bool = False) -> AgentAccessSettings | None:
    statement = select(AgentAccessSettings).where(AgentAccessSettings.id == 1)
    return session.scalar(statement.with_for_update() if for_update else statement)


def load(session: Session) -> Limits:
    """The limits now in force: the saved row, or the defaults before any is saved."""
    row = _row(session)
    if row is None:
        return Limits(DEFAULT_IDLE_DAYS, DEFAULT_DAYS, 0, None)
    return Limits(row.session_idle_days, row.session_days, row.version, row.updated_at)


def save(
    session: Session,
    *,
    idle_days: int | None,
    days: int | None,
    expected_version: int | None,
) -> Limits:
    """Change the limits named (the other keeps its value); commits. ``422
    AGENT_SESSION_LIMITS_INVALID`` when the days in all are fewer than the days without use, ``409
    VERSION_CONFLICT`` for a stale ``expected_version``."""
    row = _row(session, for_update=True)
    held = Limits(DEFAULT_IDLE_DAYS, DEFAULT_DAYS, 0, None) if row is None else load(session)
    if expected_version is not None and expected_version != held.version:
        session.rollback()
        raise version_conflict(held.version, "", message="The sign-in limits have changed")
    new_idle = held.idle_days if idle_days is None else idle_days
    new_days = held.days if days is None else days
    if not 1 <= new_idle <= LIMIT_DAYS or not 1 <= new_days <= LIMIT_DAYS or new_days < new_idle:
        session.rollback()
        raise api_error(
            422,
            "AGENT_SESSION_LIMITS_INVALID",
            "Days without use and days in all are each 1 to 365, and the days in all are not "
            "fewer than the days without use",
        )
    changed = [
        name
        for name, before, after in (
            ("sessionIdleDays", held.idle_days, new_idle),
            ("sessionDays", held.days, new_days),
        )
        if before != after
    ]
    now = datetime.now(UTC)
    if row is None:
        row = AgentAccessSettings(
            id=1, session_idle_days=new_idle, session_days=new_days, version=1, updated_at=now
        )
        session.add(row)
    elif changed:
        row.session_idle_days = new_idle
        row.session_days = new_days
        row.version += 1
        row.updated_at = now
    if changed:
        session.flush()
        security_events.record(
            session, AGGREGATE, EVENT_ID, "updated", version=row.version,
            details=security_events.changed(
                changed, sessionIdleDays=new_idle, sessionDays=new_days
            ),
        )  # fmt: skip
    session.commit()
    return load(session)
