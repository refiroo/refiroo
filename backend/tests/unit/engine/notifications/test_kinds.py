"""The kinds of inbox notice and the mail sentence of each (Product 0.12 M2 follow-up, D434)."""

from app.engine.mail import templates
from app.engine.notifications import kinds

URL = "https://refiroo.example.org"


def test_every_listed_kind_has_a_label_and_its_label_is_the_mail_sentence():
    listed = [kind for kind, _ in kinds.NOTICE_KINDS]
    assert len(listed) == len(set(listed)) == 6
    for kind, label in kinds.NOTICE_KINDS:
        assert label and not label.endswith(".")
        assert f"{label}.\n" in templates.notice("refiroo", kind, URL).body


def test_an_unknown_kind_falls_back_to_a_general_sentence():
    body = templates.notice("refiroo", "something.new", URL).body
    assert body.startswith("Something is waiting in your inbox.")
