"""The outbox's retry schedule (Product 0.12 M1, D419)."""

from datetime import timedelta

import pytest

from app.engine.mail.outbox import GIVE_UP_AFTER, retry_delay


@pytest.mark.parametrize(
    ("attempts", "seconds"),
    [(0, 30), (1, 30), (2, 60), (3, 120), (4, 240), (7, 1920), (8, 3600), (40, 3600)],
)
def test_the_wait_after_each_failure_doubles_up_to_an_hour(attempts, seconds):
    assert retry_delay(attempts) == timedelta(seconds=seconds)


def test_the_retry_schedule_stays_within_a_day_and_keeps_trying_until_it_ends():
    """Messages are given up on after a day (``GIVE_UP_AFTER``, tested by J46.4 through the
    sender); until then the waits are bounded, so a message is still tried about hourly late in
    the day instead of waiting out the deadline."""
    elapsed, attempts = timedelta(0), 0
    while elapsed < GIVE_UP_AFTER:
        attempts += 1
        elapsed += retry_delay(attempts)
    assert 20 <= attempts <= 40
    assert retry_delay(attempts) <= timedelta(hours=1)
