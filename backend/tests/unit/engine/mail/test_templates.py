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


def test_a_digest_counts_by_kind_lists_the_newest_with_links_and_names_nothing():
    from datetime import UTC, datetime

    when = datetime(2026, 11, 2, 17, 30, tzinfo=UTC)
    lines = [
        templates.DigestLine("n-1", "change-set.published", when),
        templates.DigestLine(
            "n-2", "job.failed", when, "import", {"applied": 1286, "rejected": 14}
        ),
        templates.DigestLine("n-3", "job.failed", when, "export", None),
    ]
    counts = {"change-set.published": 1, "job.failed": 2, "change-set.submitted": 3}
    message = templates.digest("refiroo", "https://refiroo.example.org/", "daily", counts, lines)
    assert message.kind == templates.DIGEST in templates.KINDS
    assert message.subject == "refiroo: 6 notices in your inbox"
    assert message.body.startswith(
        "3 change sets wait for your approval; 2 jobs you started failed; "
        "1 change set was published in a workspace you follow.\n\nSince your last digest:\n"
    )
    assert "  An import, 1,286 rows applied, 14 rows rejected\n" in message.body
    assert "  An export\n" in message.body and "  Monday 2 November, 17:30\n" in message.body
    assert "https://refiroo.example.org/notifications?notice=n-1\n" in message.body
    assert "and 3 more in your inbox." in message.body
    assert "daily digest" in message.body and "change it to weekly" in message.body
