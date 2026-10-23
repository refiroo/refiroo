"""When a browser session is open: until it is ended, idle too long, or at its absolute end."""

from datetime import UTC, datetime, timedelta

from app.engine.identity.sessions import is_open
from app.models.database import UserSession

NOW = datetime(2026, 10, 23, 12, tzinfo=UTC)


def _session(**changes) -> UserSession:
    fields = {
        "idle_ends_at": NOW + timedelta(hours=1),
        "ends_at": NOW + timedelta(days=1),
        "ended_at": None,
    }
    return UserSession(**{**fields, **changes})


def test_a_session_is_open_before_both_ends():
    assert is_open(_session(), NOW)


def test_a_session_idle_too_long_is_closed_at_that_moment():
    assert not is_open(_session(idle_ends_at=NOW), NOW)
    assert is_open(_session(idle_ends_at=NOW + timedelta(microseconds=1)), NOW)


def test_a_session_past_its_absolute_end_is_closed_however_recently_used():
    assert not is_open(_session(idle_ends_at=NOW + timedelta(hours=12), ends_at=NOW), NOW)


def test_an_ended_session_is_closed():
    assert not is_open(_session(ended_at=NOW - timedelta(minutes=1)), NOW)
