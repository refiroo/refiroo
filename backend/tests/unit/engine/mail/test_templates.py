"""What a message the engine sends says (Product 0.12 M1, D421)."""

import pytest

from app.engine.mail import templates

LINK = "https://refiroo.example.org/reset?token=abc"


@pytest.mark.parametrize(
    ("hours", "words"),
    [
        (1, "1 hour"),
        (2, "2 hours"),
        (24, "1 day"),
        (48, "2 days"),
        (36, "36 hours"),
        (168, "7 days"),
    ],
)
def test_how_long_a_link_works_is_said_in_the_words_people_use(hours, words):
    assert templates.lasts(hours) == words


@pytest.mark.parametrize("make", [templates.activation, templates.password_reset])
def test_a_link_message_names_the_product_the_person_and_how_long_and_says_to_ignore_it(make):
    message = make("refiroo", "Ada", LINK, 24)
    assert message.kind in templates.KINDS
    assert "refiroo" in message.subject
    assert "Hello Ada" in message.body and LINK in message.body
    assert "1 day" in message.body and templates.IGNORE in message.body
    assert message.body.count("http") == 1


def test_the_test_message_shows_where_links_point_and_carries_no_link_of_its_own():
    message = templates.test_message("refiroo", "https://refiroo.example.org")
    assert message.kind == templates.TEST
    assert "https://refiroo.example.org" in message.body and "token" not in message.body


@pytest.mark.parametrize(
    ("kind", "words"),
    [
        ("change-set.submitted", "waiting for your approval"),
        ("change-set.approved", "was approved"),
        ("change-set.sent-back", "was sent back"),
        ("job.completed", "has finished"),
        ("job.failed", "has failed"),
        ("job.awaiting-confirmation", "waiting for your confirmation"),
        ("something.new", "waiting in your inbox"),
    ],
)
def test_a_notice_names_its_kind_and_the_link_and_nothing_else(kind, words):
    message = templates.notice("refiroo", kind, "https://refiroo.example.org")
    assert message.kind == templates.NOTICE and message.kind in templates.KINDS
    assert words in message.body and "https://refiroo.example.org" in message.body
    assert "Hello" not in message.body
