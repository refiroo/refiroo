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


def test_a_message_is_given_up_on_after_a_day():
    assert GIVE_UP_AFTER == timedelta(hours=24)
