"""What a message the engine sends says (Product 0.12 M1, D421)."""

import re
from datetime import UTC, datetime
from html import unescape

import pytest

from app.engine.mail import smtp, templates

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


# --- the HTML part (branded layout, same facts as the text) ---------------------------------------

CONNECTION = smtp.Connection("localhost", 25, smtp.NONE, None, None, "no-reply@refiroo.example.org")
NASTY = "<b>Sam & Co</b>"


def _built(message):
    return smtp.build(CONNECTION, "sam@example.org", message.subject, message.body, message.html)


def _visible(html: str) -> str:
    html = re.sub(r"<(title|head)>.*?</\1>", " ", html, flags=re.DOTALL)
    return " ".join(unescape(re.sub(r"<[^>]+>", " ", html)).split())


def test_a_message_is_the_text_then_the_html_with_both_images_inline():
    message = templates.password_reset("refiroo", "Ada", LINK, 1)
    built = _built(message)
    assert built.get_content_type() == "multipart/alternative"
    text, related = built.get_payload()
    assert text.get_content_type() == "text/plain" and text.get_content() == message.body
    assert related.get_content_type() == "multipart/related"
    page, *images = related.get_payload()
    assert page.get_content_type() == "text/html" and page.get_content() == message.html
    cids = {image["Content-ID"].strip("<>") for image in images}
    assert {i.get_content_type() for i in images} == {"image/png"}
    assert cids == {"refiroo-mascot", "refiroo-wordmark"}
    assert all(f"cid:{cid}" in message.html for cid in cids)
    assert all(image.get_content().startswith(b"\x89PNG") for image in images)
    assert built["Auto-Submitted"] == "auto-generated" and built["Subject"] == message.subject
    assert "http://" not in message.html.replace(LINK, "") and 'src="https' not in message.html


def test_a_message_without_html_stays_plain_text():
    built = smtp.build(CONNECTION, "sam@example.org", "s", "just text\n")
    assert built.get_content_type() == "text/plain"


def test_values_are_escaped_and_the_link_is_the_only_one():
    message = templates.activation(NASTY, NASTY, LINK + "&x=<1>", 48)
    assert NASTY not in message.html and "&lt;b&gt;Sam &amp; Co&lt;/b&gt;" in message.html
    assert "x=<1>" not in message.html and "&amp;x=&lt;1&gt;" in message.html
    assert "Welcome aboard, &lt;b&gt;Sam" in message.html
    assert "Works once · for 2 days" in message.html
    assert message.body.startswith(f"Hello {NASTY},")  # the text stays as it was


def test_a_renamed_product_shows_its_name_beside_the_mark_and_a_default_one_does_not():
    renamed = templates.password_reset("Acme Reference Data", "Ada", LINK, 1)
    assert "Acme Reference Data" in _visible(renamed.html)
    assert "Let&#x27;s get you a new password" in renamed.html
    plain = templates.password_reset("refiroo", "Ada", LINK, 1)
    assert _visible(plain.html).count("refiroo") == _visible(plain.html).count("refiroo")
    assert "border-left:1px solid #d5daf5" in renamed.html
    assert "border-left:1px solid #d5daf5" not in plain.html


def test_every_message_carries_a_heading_and_no_fact_the_text_lacks():
    when = datetime(2026, 11, 2, 17, 30, tzinfo=UTC)
    lines = [
        templates.DigestLine(
            "n-1", "job.failed", when, "import", {"applied": 1286, "rejected": 14}
        ),
        templates.DigestLine("n-2", "change-set.submitted", when),
    ]
    messages = {
        "Welcome aboard, Ada": templates.activation("refiroo", "Ada", LINK, 24),
        "Let&#x27;s get you a new password": templates.password_reset("refiroo", "Ada", LINK, 24),
        "Hop hop, mail works!": templates.test_message("refiroo", "https://refiroo.example.org"),
        "Something&#x27;s waiting for you": templates.notice(
            "refiroo", "job.failed", "https://refiroo.example.org"
        ),
        "Your weekly digest": templates.digest(
            "refiroo", "https://refiroo.example.org", "weekly", {"job.failed": 1, "x": 4}, lines
        ),
    }
    for heading, message in messages.items():
        assert "<h1" in message.html and heading in message.html
        links = set(re.findall(r'href="([^"]+)"', message.html))
        assert all(
            link in message.body or link.rstrip("/") in message.body for link in links
        )
    digest = messages["Your weekly digest"].html
    assert "Ada" not in digest and "job.failed" not in digest
    assert "An import, 1,286 rows applied, 14 rows rejected" in digest
    assert "#f2a48f" in digest and "#7d95f0" in digest and "and 3 more in your inbox." in digest
    assert "https://refiroo.example.org/notifications?notice=n-1" in digest
