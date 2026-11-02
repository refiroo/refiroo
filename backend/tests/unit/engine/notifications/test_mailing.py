"""When a digest is next sent (0.16 AO3, AO-D34): 07:00 in the person's zone, daily or on Monday,
across a daylight-saving change."""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest

from app.engine.notifications.mailing import next_digest

ZONE = "Europe/Budapest"


def _at(moment: datetime) -> datetime:
    return moment.astimezone(ZoneInfo(ZONE))


def test_daily_is_the_next_seven_in_the_zone_even_across_the_clocks_going_forward():
    # Saturday 28 March 2026, 08:00 CET; the clocks go forward on the night to Sunday.
    after = datetime(2026, 3, 28, 7, 0, tzinfo=UTC)
    found = next_digest("daily", ZONE, after)
    assert found == datetime(2026, 3, 29, 5, 0, tzinfo=UTC)  # 07:00 CEST, not 06:00 UTC
    assert _at(found).hour == 7
    assert next_digest("daily", ZONE, found) == datetime(2026, 3, 30, 5, 0, tzinfo=UTC)


def test_daily_is_the_next_seven_across_the_clocks_going_back():
    found = next_digest("daily", ZONE, datetime(2026, 10, 24, 6, 0, tzinfo=UTC))
    assert found == datetime(2026, 10, 25, 6, 0, tzinfo=UTC)  # 07:00 CET is 06:00 UTC
    after = next_digest("daily", ZONE, found)
    assert after == datetime(2026, 10, 26, 6, 0, tzinfo=UTC)  # 07:00 CET
    assert _at(after).hour == 7


def test_daily_before_seven_is_today_and_after_seven_is_tomorrow():
    assert next_digest("daily", "UTC", datetime(2026, 5, 4, 6, 59, tzinfo=UTC)) == datetime(
        2026, 5, 4, 7, 0, tzinfo=UTC
    )
    assert next_digest("daily", "UTC", datetime(2026, 5, 4, 7, 0, tzinfo=UTC)) == datetime(
        2026, 5, 5, 7, 0, tzinfo=UTC
    )


def test_weekly_is_the_next_monday_at_seven_and_keeps_seven_across_a_change():
    # Friday 27 March 2026 -> Monday 30 March 07:00 CEST.
    found = next_digest("weekly", ZONE, datetime(2026, 3, 27, 12, 0, tzinfo=UTC))
    assert found == datetime(2026, 3, 30, 5, 0, tzinfo=UTC)
    assert _at(found).weekday() == 0
    # The Monday itself, at seven, is not "after": the week after.
    assert next_digest("weekly", ZONE, found) == datetime(2026, 4, 6, 5, 0, tzinfo=UTC)
    # Across the autumn change: Monday 19 October -> Monday 26 October is 07:00 CET.
    week = next_digest("weekly", ZONE, datetime(2026, 10, 19, 5, 0, tzinfo=UTC))
    assert week == datetime(2026, 10, 26, 6, 0, tzinfo=UTC)


def test_an_unknown_frequency_is_refused():
    with pytest.raises(ValueError):
        next_digest("hourly", ZONE, datetime(2026, 1, 1, tzinfo=UTC))
