"""The e-mail template's rendering and its logo check (0.17 release review R17-F21 to F25)."""

from datetime import UTC, datetime

import pytest

from app.engine.mail import mail_template, templates
from app.engine.mail.mail_template import DEFAULT_MARKDOWN, Values
from app.errors import ApiError
from app.models.database import MailTemplate

LINK = "https://refiroo.example.org/reset?token=Zm9v-_abc_-YmFy"
WHEN = datetime(2026, 11, 2, 17, 30, tzinfo=UTC)
SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10">{}</svg>'


def _row(markdown: str = DEFAULT_MARKDOWN) -> MailTemplate:
    return MailTemplate(id=1, body=markdown, version=1, updated_at=WHEN)


def _values(name: str = "Ada") -> Values:
    return Values("refiroo", "https://refiroo.example.org", name)


def test_markdown_is_stripped_from_the_template_alone_not_from_what_is_inserted():
    """A token with `-_abc_-` and a name with `*x*` reach the text as they are."""
    message = templates.password_reset("refiroo", "*x* Ada", LINK, 24)
    wrapped = mail_template.wrap(
        _row("**{{product_name}}**\n\n{{content}}"), message, _values("*x* Ada")
    )
    assert LINK in wrapped.body and "token=Zm9v-_abc_-YmFy" in wrapped.body
    assert wrapped.body.startswith("refiroo\n") and "**" not in wrapped.body.splitlines()[0]
    named = mail_template.wrap(
        _row("Dear {{recipient_name}},\n\n{{content}}"), message, _values("*x* Ada")
    )
    assert named.body.startswith("Dear *x* Ada,")


def test_a_value_that_looks_like_a_stand_in_or_a_placeholder_is_never_filled():
    nasty = "zzphcontentzz {{content}} zzph0z"
    message = templates.notice("refiroo", "job.failed", "https://refiroo.example.org")
    html = mail_template.wrap(_row(), message, _values(nasty)).html
    assert html.count("Hello zzphcontentzz {{content}} zzph0z,") == 1
    assert html.count("Something&#x27;s waiting for you") == 1


def _kinds():
    lines = [templates.DigestLine("n-1", "job.failed", WHEN, "import", {"applied": 3})]
    return {
        "activation": templates.activation("refiroo", "Ada", LINK, 24),
        "password-reset": templates.password_reset("refiroo", "Ada", LINK, 24),
        "security": templates.security_change("refiroo", "Ada", "password-changed", WHEN),
        "test": templates.test_message("refiroo", "https://refiroo.example.org"),
        "template-test": templates.template_test("refiroo", "https://refiroo.example.org"),
        "notice": templates.notice("refiroo", "job.failed", "https://refiroo.example.org"),
        "digest": templates.digest(
            "refiroo", "https://refiroo.example.org", "weekly", {"job.failed": 1}, lines
        ),
    }


@pytest.mark.parametrize("kind", list(_kinds()))
def test_every_message_kind_greets_the_person_once_inside_the_default_template(kind):
    message = _kinds()[kind]
    wrapped = mail_template.wrap(_row(), message, _values())
    assert wrapped.body.count("Hello Ada") == 1, wrapped.body
    assert wrapped.html.count("Hello Ada") == 1


@pytest.mark.parametrize("kind", ["activation", "password-reset", "security"])
def test_a_message_that_greets_itself_does_so_once_without_a_template(kind):
    message = _kinds()[kind]
    assert message.body.count("Hello Ada") == 1
    if kind != "activation":  # its HTML greets in the heading
        assert message.html.count("Hello Ada") == 1


@pytest.mark.parametrize(
    "inner",
    [
        "<svg:script>alert(1)</svg:script>",
        '<script xmlns="http://www.w3.org/2000/svg">alert(1)</script>',
        '<rect onload="x()" width="1" height="1"/>',
        '<a href="javascript&#58;alert(1)"><rect width="1" height="1"/></a>',
        '<image href="https://example.org/x.png"/>',
        '<use xlink:href="https://example.org/x.svg#a" xmlns:xlink="http://www.w3.org/1999/xlink"/>',
        "<style>@import url(https://example.org/x.css);</style>",
        '<rect style="fill:url(https://example.org/x)" width="1" height="1"/>',
        '<foreignObject><p xmlns="http://www.w3.org/1999/xhtml">x</p></foreignObject>',
        '<set attributeName="href" to="javascript:alert(1)"/>',
    ],
)
def test_an_svg_that_can_run_or_fetch_is_refused(inner):
    data = SVG.format(inner).replace("<svg ", '<svg xmlns:svg="http://www.w3.org/2000/svg" ', 1)
    with pytest.raises(ApiError) as refusal:
        mail_template.check_logo(data.encode(), "image/svg+xml")
    assert (refusal.value.status, refusal.value.code) == (422, "MAIL_LOGO_UNSAFE")


@pytest.mark.parametrize(
    "data",
    [
        b'<?xml version="1.0"?><!DOCTYPE svg [<!ENTITY a "b">]><svg xmlns="http://www.w3.org/2000/svg"/>',
        b'<?xml-stylesheet href="https://example.org/x.css"?><svg xmlns="http://www.w3.org/2000/svg"/>',
    ],
)
def test_an_svg_with_a_dtd_or_a_stylesheet_instruction_is_refused(data):
    with pytest.raises(ApiError):
        mail_template.check_logo(data, "image/svg+xml")


def test_a_plain_svg_with_internal_references_is_accepted():
    good = SVG.format(
        '<defs><linearGradient id="g"/></defs><rect fill="url(#g)" width="1" height="1"/>'
        '<use href="#g"/><image href="data:image/png;base64,AAAA"/>'
        "<style>.a{fill:url(#g)}</style>"
    )
    assert mail_template.check_logo(good.encode(), "image/svg+xml") == "image/svg+xml"
