"""J46.12 — the e-mail template an Operator edits (Settings › E-mail template).

One template per instance: Markdown with placeholders and a logo, around the content of every mail
the engine sends. The tests walk it through the API as the Operator's client and as a signed-in
person (the test mail goes to the caller's own address), and read what the harness's SMTP server
receives (``tests/smtp_server.py``); the sender is run by the test, as in J46.
"""

import base64

import pytest
from scenario import ok, queue_mail, refused, send_mail
from test_j39_sign_in import _browser, _reset_link, _set_password, _sign_in, address
from test_j40_authorization import _as, _client, _grant
from test_j46_mail import _person, _reset_mail, _save, smtp  # noqa: F401 - a fixture

TEMPLATE = "/mail-template"
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)
SVG = b'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"><rect width="10" height="10"/></svg>'
BRANDED = "Dear {{recipient_name}},\n\n{{logo}}\n\n{{content}}\n\nYours, **{{product_name}}** ([open]({{instance_url}}))\n"


def _operator(world, name: str = "Operates"):
    return _client(world, name, ("operator", {"instance": True}))[1]


def _logo(api, data: bytes, kind: str, **fields):
    return api.client.put(
        "/api/v1/mail-template/logo", files={"file": ("logo", data, kind)}, data=fields
    )


def _html(message) -> str:
    return message.get_body(("html",)).get_content()


@pytest.mark.journey("J46.12")
def test_the_default_is_read_edited_saved_and_reset(world):
    """Given no saved template, when an Operator reads, saves and resets it, then the default is
    answered unsaved, a save is versioned and a stale one refused, and a reset restores the default."""
    operator = _operator(world)
    found = ok(operator.api.get(TEMPLATE))
    assert found["saved"] is False and found["version"] is None
    assert found["markdown"] == found["defaultMarkdown"] and "{{content}}" in found["markdown"]
    assert found["placeholders"] == [
        "content",
        "product_name",
        "instance_url",
        "recipient_name",
        "logo",
    ]
    saved = ok(operator.api.put(TEMPLATE, {"markdown": BRANDED}))
    assert saved["saved"] is True and saved["version"] == 1 and saved["markdown"] == BRANDED
    stale = refused(operator.api.put(TEMPLATE, {"markdown": BRANDED}), 409, "VERSION_CONFLICT")
    assert stale["details"] == {"currentVersion": 1}
    again = ok(operator.api.put(TEMPLATE, {"markdown": "{{content}}", "expectedVersion": 1}))
    assert again["version"] == 2
    assert operator.api.delete(TEMPLATE).status_code == 204
    assert operator.api.delete(TEMPLATE).status_code == 204
    reset = ok(operator.api.get(TEMPLATE))
    assert reset["saved"] is False and reset["markdown"] == reset["defaultMarkdown"]


@pytest.mark.journey("J46.12")
def test_an_unknown_placeholder_and_a_missing_content_are_refused_by_code(world):
    """Given an Operator, when the Markdown holds an unknown placeholder, no {{content}} or two,
    then each is refused by its code and nothing is saved."""
    operator = _operator(world)
    unknown = refused(
        operator.api.put(TEMPLATE, {"markdown": "{{content}} {{nickname}}"}),
        422,
        "MAIL_TEMPLATE_UNKNOWN_PLACEHOLDER",
    )
    assert unknown["details"]["placeholder"] == "nickname"
    missing = refused(
        operator.api.put(TEMPLATE, {"markdown": "Hello {{recipient_name}}"}),
        422,
        "MAIL_TEMPLATE_CONTENT_REQUIRED",
    )
    assert missing["details"]["count"] == 0
    twice = refused(
        operator.api.put(TEMPLATE, {"markdown": "{{content}}\n\n{{content}}"}),
        422,
        "MAIL_TEMPLATE_CONTENT_REQUIRED",
    )
    assert twice["details"]["count"] == 2
    assert ok(operator.api.get(TEMPLATE))["saved"] is False


@pytest.mark.journey("J46.12")
def test_a_logo_is_uploaded_shown_and_removed(world):
    """Given an Operator, when a PNG is uploaded, an SVG with script, a text file and a file over
    the limit are tried, and the logo is removed, then the good logo is answered as a thumbnail and
    each bad one is refused by its code."""
    operator = _operator(world)
    refused(operator.api.delete(f"{TEMPLATE}/logo"), 409, "MAIL_TEMPLATE_NOT_SAVED")
    uploaded = ok(_logo(operator.api, PNG, "image/png"))
    assert uploaded["logoType"] == "image/png" and uploaded["version"] == 1
    assert uploaded["logoDataUrl"] == "data:image/png;base64," + base64.b64encode(PNG).decode()
    assert uploaded["saved"] is True and "{{content}}" in uploaded["markdown"]
    ok(_logo(operator.api, SVG, "image/svg+xml", expectedVersion=1))
    scripted = SVG.replace(b"<rect", b"<script>alert(1)</script><rect")
    refused(
        _logo(operator.api, scripted, "image/svg+xml", expectedVersion=2), 422, "MAIL_LOGO_UNSAFE"
    )
    handler = SVG.replace(b"<rect", b'<rect onload="x()"')
    refused(
        _logo(operator.api, handler, "image/svg+xml", expectedVersion=2), 422, "MAIL_LOGO_UNSAFE"
    )
    refused(
        _logo(operator.api, b"not an image", "text/plain", expectedVersion=2),
        422,
        "MAIL_LOGO_UNSUPPORTED",
    )
    large = PNG + b"0" * (512 * 1024)
    refused(_logo(operator.api, large, "image/png", expectedVersion=2), 413, "MAIL_LOGO_TOO_LARGE")
    refused(_logo(operator.api, PNG, "image/png", expectedVersion=1), 409, "VERSION_CONFLICT")
    removed = ok(operator.api.delete(f"{TEMPLATE}/logo", expectedVersion=2))
    assert (
        removed["logoType"] is None and removed["logoDataUrl"] is None and removed["version"] == 3
    )


@pytest.mark.journey("J46.12")
def test_a_preview_renders_a_draft_without_saving_it(world):
    """Given a saved logo, when a draft is previewed, then the HTML and the text hold the sample
    values and the logo, raw HTML and an unsafe link are not carried, and nothing is saved."""
    operator = _operator(world)
    ok(_logo(operator.api, PNG, "image/png"))
    draft = (
        "# Hi {{recipient_name}}\n\n{{logo}}\n\n{{content}}\n\n"
        "<script>alert(1)</script> [bad](javascript:alert(1)) [good](https://example.org/x)\n"
    )
    preview = ok(operator.api.post(f"{TEMPLATE}/preview", {"markdown": draft}))
    html, text = preview["html"], preview["text"]
    assert "Hi Alex Example" in html and "Alex Example" in text
    assert "data:image/png;base64," in html
    assert "<script" not in html.lower() and 'href="javascript' not in html.lower()
    assert "&lt;script&gt;" in html
    assert 'href="https://example.org/x"' in html
    assert "This is how your mail looks" in html and "This is how your mail looks" in text
    refused(
        operator.api.post(f"{TEMPLATE}/preview", {"markdown": "no content here"}),
        422,
        "MAIL_TEMPLATE_CONTENT_REQUIRED",
    )
    found = ok(operator.api.get(TEMPLATE))
    assert found["saved"] is True and found["version"] == 1 and found["markdown"] != draft


@pytest.mark.journey("J46.12")
def test_only_the_operator_group_may_use_the_template(world, smtp):  # noqa: F811
    """Given a Reader and an Operator, when each calls the template routes, then the Reader is
    refused every one by code and the Operator is not."""
    _, reader = _client(world, "Reads everything", ("reader", {"instance": True}))
    operator = _operator(world)
    calls = (
        ("GET", TEMPLATE, None),
        ("PUT", TEMPLATE, {"markdown": "{{content}}"}),
        ("DELETE", TEMPLATE, None),
        ("DELETE", f"{TEMPLATE}/logo", None),
        ("POST", f"{TEMPLATE}/preview", {"markdown": "{{content}}"}),
        ("POST", f"{TEMPLATE}/test", None),
    )
    for method, path, body in calls:
        denied = reader.api.client.request(method, f"/api/v1{path}", json=body)
        assert refused(denied, 403, "FORBIDDEN")["details"]["action"] == "mail-template.manage"
    assert ok(operator.api.get(TEMPLATE))["saved"] is False
    refused(operator.api.post(f"{TEMPLATE}/test", {}), 403, "NOT_A_PERSON")


@pytest.mark.journey("J46.12")
def test_a_real_mail_and_a_test_are_wrapped_by_the_saved_template(world, smtp):  # noqa: F811
    """Given mail set up and a saved template with a logo, when a password link is mailed and the
    Operator sends a test to themselves, then both messages are the template around the message's
    own text, with the recipient's name, the logo as an inline part and a text alternative; after a
    reset the engine's own layout is used again."""
    _save(world, smtp, applicationUrl="https://refiroo.example.org")
    operator = _operator(world)
    ok(operator.api.put(TEMPLATE, {"markdown": BRANDED}))
    ok(_logo(operator.api, PNG, "image/png", expectedVersion=1))

    queue_mail(world, "ada@example.org", _reset_mail("Ada"), recipient_name="Ada")
    assert send_mail(world) == 1
    [mail] = smtp.messages
    html = _html(mail)
    assert "Dear Ada," in html and "Choose a new password" in html
    assert "one-time-token" in html and "cid:mail-template-logo" in html
    assert "https://refiroo.example.org" in html and "<strong>" in html
    assert "get you a new password" in html
    text = mail.get_body(("plain",)).get_content()
    assert "Dear Ada," in text and "one-time-token" in text and "**" not in text
    inline = [part for part in mail.walk() if part.get_content_type() == "image/png"]
    assert "<mail-template-logo>" in {part["Content-ID"] for part in inline}

    person = _person(world, "olga", address("olga"))
    _set_password(_browser(world), _reset_link(world, person))
    _grant(world, "user", person["id"], "operator", instance=True)
    olga = _as(world, _sign_in(_browser(world), "olga"))
    assert ok(olga.api.post(f"{TEMPLATE}/test", {})) == {"sentTo": "olga@example.org"}
    sent = smtp.messages[-1]
    assert sent["To"] == "olga@example.org"
    assert "Dear Olga," in _html(sent) and "This is how your mail looks" in _html(sent)

    assert operator.api.delete(TEMPLATE).status_code == 204
    queue_mail(world, "ada@example.org", _reset_mail("Ada"))
    assert send_mail(world) == 1
    assert "Dear Ada," not in _html(smtp.messages[-1])
    assert "cid:mail-template-logo" not in _html(smtp.messages[-1])
