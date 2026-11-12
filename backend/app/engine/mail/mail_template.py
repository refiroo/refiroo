"""The e-mail template an operator edits in Settings, used for every mail the engine sends.

One template per instance: Markdown with ``{{placeholders}}`` and a logo. It is rendered to HTML (and
a plain-text alternative) around the content of each message: the message's own heading, text and
button replace ``{{content}}``, which the template holds exactly once. Without a saved template the
engine's own layout (``html.layout``) applies; "reset to default" deletes the row.

The Markdown is converted with raw HTML switched off, images off and links limited to http, https and
mailto, so what an operator writes cannot carry script or an event handler. The logo is sent inline
(``cid:``): an uploaded PNG, JPEG or SVG (no script in it, at most 512 KB), else the refiroo mark.
"""

import re
from base64 import b64encode
from dataclasses import dataclass
from datetime import UTC, datetime
from html import escape
from xml.etree import ElementTree

from markdown_it import MarkdownIt
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ...errors import api_error
from ...models.database import MailTemplate
from ..identity.settings import IdentitySettings
from . import html as mailhtml
from . import settings as mail_settings
from .smtp import LOGO_CID
from .templates import Rendered, product

MAX_LOGO_BYTES = 512 * 1024
MAX_MARKDOWN_CHARS = 20_000
PLACEHOLDERS = ("content", "product_name", "instance_url", "recipient_name", "logo")
LOGO_TYPES = ("image/png", "image/jpeg", "image/svg+xml")
# What a message says when it has no name for the person (a notice, a client).
NO_NAME = "there"

DEFAULT_MARKDOWN = """{{logo}}

Hello {{recipient_name}},

{{content}}

---

This message was sent by [{{product_name}}]({{instance_url}}).
"""

_PLACEHOLDER = re.compile(r"\{\{(.*?)\}\}", re.DOTALL)
_SVG_UNSAFE = re.compile(
    r"<\s*(script|foreignobject|iframe|object|embed)\b|\bon[a-z]+\s*=|javascript:|<!\s*(doctype|entity)",
    re.IGNORECASE,
)
_CONTENT = re.compile(
    rf"<!--{mailhtml.CONTENT_OPEN}-->(.*?)<!--{mailhtml.CONTENT_CLOSE}-->", re.DOTALL
)
_FOOTER = re.compile(
    rf"<!--{mailhtml.FOOTER_OPEN}-->(.*?)<!--{mailhtml.FOOTER_CLOSE}-->", re.DOTALL
)
_TOKEN = "zzph"
_PARAGRAPH = '<p style="margin:0 0 14px;font-size:15px;line-height:1.6">'
_SAFE_LINK = re.compile(r"^(https?:|mailto:)", re.IGNORECASE)


# --- the stored template -------------------------------------------------------------------------


def load(session: Session, *, for_update: bool = False) -> MailTemplate | None:
    statement = select(MailTemplate).where(MailTemplate.id == 1)
    return session.scalar(statement.with_for_update() if for_update else statement)


def _stale(current: int):
    return api_error(
        409, "VERSION_CONFLICT", "The e-mail template has changed", {"currentVersion": current}
    )


def _check_version(row: MailTemplate | None, expected: int | None, session: Session) -> None:
    if (row.version if row else None) != expected:
        session.rollback()
        raise _stale(row.version if row else 0)


def check_markdown(markdown: str) -> None:
    """Refuse an unknown placeholder (``422 MAIL_TEMPLATE_UNKNOWN_PLACEHOLDER``) and a template that
    does not hold ``{{content}}`` exactly once (``422 MAIL_TEMPLATE_CONTENT_REQUIRED``)."""
    if len(markdown) > MAX_MARKDOWN_CHARS:
        raise api_error(
            422,
            "MAIL_TEMPLATE_TOO_LONG",
            f"The template is longer than {MAX_MARKDOWN_CHARS} characters",
            {"limit": MAX_MARKDOWN_CHARS},
        )
    found = [name.strip() for name in _PLACEHOLDER.findall(markdown)]
    for name in found:
        if name not in PLACEHOLDERS:
            raise api_error(
                422,
                "MAIL_TEMPLATE_UNKNOWN_PLACEHOLDER",
                f"{{{{{name}}}}} is not a placeholder; use {', '.join('{{' + p + '}}' for p in PLACEHOLDERS)}",
                {"placeholder": name, "known": list(PLACEHOLDERS)},
            )
    count = found.count("content")
    if count != 1:
        raise api_error(
            422,
            "MAIL_TEMPLATE_CONTENT_REQUIRED",
            "The template must hold {{content}} exactly once: it is where the message goes"
            f" (it holds it {count} times)",
            {"placeholder": "content", "count": count},
        )


def save(session: Session, markdown: str, expected_version: int | None) -> MailTemplate:
    """Create or replace the template's Markdown; commits. The logo stays as it is."""
    check_markdown(markdown)
    row = load(session, for_update=True)
    _check_version(row, expected_version, session)
    now = datetime.now(UTC)
    if row is None:
        row = MailTemplate(id=1, body=markdown, version=1, updated_at=now)
        session.add(row)
    elif row.body != markdown:
        row.body, row.version, row.updated_at = markdown, row.version + 1, now
    session.commit()
    return row


def remove(session: Session) -> None:
    """Back to the default: delete the row (the Markdown and the logo); commits. Repeats harmlessly."""
    session.execute(delete(MailTemplate).where(MailTemplate.id == 1))
    session.commit()


def check_logo(data: bytes, content_type: str) -> str:
    """The logo's media type when it is a PNG, JPEG or SVG without script within the size limit;
    ``413 MAIL_LOGO_TOO_LARGE``, ``422 MAIL_LOGO_UNSUPPORTED`` or ``422 MAIL_LOGO_UNSAFE`` else."""
    if len(data) > MAX_LOGO_BYTES:
        raise api_error(
            413,
            "MAIL_LOGO_TOO_LARGE",
            f"The logo is larger than {MAX_LOGO_BYTES // 1024} KB",
            {"limit": MAX_LOGO_BYTES},
        )
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    text = None
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        pass
    if text is not None and "<svg" in text.lower():
        if _SVG_UNSAFE.search(text):
            raise api_error(
                422,
                "MAIL_LOGO_UNSAFE",
                "The SVG holds script or an external object, which is refused",
            )
        try:
            root = ElementTree.fromstring(data)
        except ElementTree.ParseError:
            root = None
        if root is not None and root.tag.rpartition("}")[2].lower() == "svg":
            return "image/svg+xml"
    raise api_error(
        422,
        "MAIL_LOGO_UNSUPPORTED",
        "The logo must be a PNG, JPEG or SVG image",
        {"accepted": list(LOGO_TYPES)},
    )


def set_logo(
    session: Session, data: bytes, content_type: str, expected_version: int | None
) -> MailTemplate:
    """Store the logo with the template (creating it from the default Markdown when none is saved)."""
    media_type = check_logo(data, content_type)
    row = load(session, for_update=True)
    _check_version(row, expected_version, session)
    now = datetime.now(UTC)
    if row is None:
        row = MailTemplate(
            id=1, body=DEFAULT_MARKDOWN, logo=data, logo_type=media_type, version=1, updated_at=now
        )
        session.add(row)
    else:
        row.logo, row.logo_type, row.version, row.updated_at = (
            data,
            media_type,
            row.version + 1,
            now,
        )
    session.commit()
    return row


def clear_logo(session: Session, expected_version: int | None) -> MailTemplate:
    """Remove the logo: the refiroo mark is used. ``409 MAIL_TEMPLATE_NOT_SAVED`` without a template."""
    row = load(session, for_update=True)
    _check_version(row, expected_version, session)
    if row is None:
        session.rollback()
        raise api_error(409, "MAIL_TEMPLATE_NOT_SAVED", "No template is saved: there is no logo")
    if row.logo is not None:
        row.logo, row.logo_type, row.version = None, None, row.version + 1
        row.updated_at = datetime.now(UTC)
    session.commit()
    return row


def data_url(data: bytes, media_type: str) -> str:
    return f"data:{media_type};base64,{b64encode(data).decode()}"


def default_mark() -> bytes:
    return (mailhtml.BRAND_DIR / mailhtml.IMAGES[mailhtml.MASCOT_CID]).read_bytes()


# --- rendering -----------------------------------------------------------------------------------


@dataclass(frozen=True)
class Values:
    """What the placeholders stand for in one message."""

    product_name: str
    instance_url: str
    recipient_name: str


def _markdown() -> MarkdownIt:
    md = MarkdownIt("commonmark", {"html": False, "breaks": False})
    md.disable(["image", "html_block", "html_inline"])
    # A link is http, https or mailto, or a placeholder (which stands for such an address).
    md.validateLink = lambda url: bool(_SAFE_LINK.match(url.strip())) or url.startswith(_TOKEN)
    return md


_STYLES = (
    ("<p>", _PARAGRAPH),
    ("<h1>", '<h1 style="margin:8px 0 12px;font-size:22px;line-height:1.3">'),
    ("<h2>", '<h2 style="margin:8px 0 10px;font-size:19px;line-height:1.3">'),
    ("<h3>", '<h3 style="margin:8px 0 8px;font-size:16px;line-height:1.3">'),
    ("<ul>", '<ul style="margin:0 0 14px;padding-left:22px">'),
    ("<ol>", '<ol style="margin:0 0 14px;padding-left:22px">'),
    ("<hr>", f'<hr style="border:0;border-top:1px solid {mailhtml.RULE};margin:18px 0">'),
    ("<hr />", f'<hr style="border:0;border-top:1px solid {mailhtml.RULE};margin:18px 0">'),
    (
        "<blockquote>",
        f'<blockquote style="margin:0 0 14px;padding-left:12px;border-left:3px solid {mailhtml.RULE}">',
    ),
)


def _tokens(markdown: str) -> tuple[str, dict[str, str]]:
    """The Markdown with each placeholder replaced by a word Markdown leaves alone."""
    names: dict[str, str] = {}

    def swap(match: re.Match[str]) -> str:
        name = match.group(1).strip()
        token = f"{_TOKEN}{name.replace('_', '')}zz"
        names[token] = name
        return token

    return _PLACEHOLDER.sub(swap, markdown), names


def _logo_tag(values: Values, src: str) -> str:
    return (
        f'<img src="{escape(src, quote=True)}" alt="{escape(values.product_name, quote=True)}" '
        'style="display:block;border:0;max-height:48px;max-width:240px;height:auto;width:auto">'
    )


def render_html(markdown: str, values: Values, content_html: str, *, logo_src: str) -> str:
    """The template's Markdown as a whole HTML document around ``content_html``. ``logo_src`` is
    where the logo image is read from (``cid:`` in a message, a data URL in a preview)."""
    swapped, names = _tokens(markdown)
    body = _markdown().render(swapped)
    for plain, styled in _STYLES:
        body = body.replace(plain, styled)
    body = body.replace("<a href=", f'<a style="color:{mailhtml.LINK}" href=')
    text = {
        "product_name": escape(values.product_name),
        "instance_url": escape(values.instance_url, quote=True),
        "recipient_name": escape(values.recipient_name),
    }
    html_values = {
        "content": content_html,
        "logo": _logo_tag(values, logo_src),
        **text,
    }
    for token, name in names.items():
        if name in ("content", "logo"):
            body = body.replace(f"{_PARAGRAPH}{token}</p>", html_values[name])
        body = body.replace(token, html_values[name])
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{escape(values.product_name)}</title></head>"
        f'<body style="margin:0;padding:0;background:{mailhtml.PAGE};color:{mailhtml.INK};'
        f'font-family:{mailhtml.FONT}">'
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" '
        f'bgcolor="{mailhtml.PAGE}"><tr><td align="center" style="padding:24px 12px">'
        '<table role="presentation" width="560" cellpadding="0" cellspacing="0" border="0" '
        'style="width:100%;max-width:560px;background:#ffffff;border-radius:12px"><tr>'
        f'<td style="padding:24px 28px;font-size:15px;line-height:1.6;color:{mailhtml.INK}">'
        f"{body}</td></tr></table></td></tr></table></body></html>\n"
    )


def _plain(markdown: str, values: Values, content_text: str) -> str:
    """The template as text: placeholders filled, links as ``label (address)``, no Markdown marks."""
    names = {
        "product_name": values.product_name,
        "instance_url": values.instance_url,
        "recipient_name": values.recipient_name,
        "logo": "",
    }
    done = _PLACEHOLDER.sub(
        lambda m: names.get(
            m.group(1).strip(), content_text if m.group(1).strip() == "content" else ""
        ),
        markdown,
    )
    done = re.sub(r"\[([^\]]*)\]\(([^)]*)\)", lambda m: f"{m.group(1)} ({m.group(2)})", done)
    done = re.sub(r"(\*\*|__)(.+?)\1", r"\2", done)
    done = re.sub(r"(?<![\w*])[*_]([^*_\n]+)[*_](?![\w*])", r"\1", done)
    done = re.sub(r"^#{1,6}\s+", "", done, flags=re.MULTILINE)
    done = re.sub(r"^-{3,}\s*$", "--", done, flags=re.MULTILINE)
    return re.sub(r"\n{3,}", "\n\n", done).strip() + "\n"


def content_of(message: Rendered) -> str | None:
    """The message's own HTML (heading, text, button, footer sentence), or None for a message
    without the layout's markers, which a template cannot wrap."""
    found = _CONTENT.search(message.html or "")
    if found is None:
        return None
    footer = _FOOTER.search(message.html)
    tail = (
        f'<p style="margin:18px 0 0;font-size:12px;line-height:1.6;color:{mailhtml.FAINT}">'
        f"{footer.group(1)}</p>"
        if footer
        else ""
    )
    return found.group(1) + tail


def wrap(
    row: MailTemplate | None, message: Rendered, values: Values, *, preview: bool = False
) -> Rendered:
    """``message`` inside the saved template; the message itself when no template is saved, or when
    the message has no HTML layout. The logo is a ``cid:`` part unless ``preview``."""
    if row is None:
        return message
    content = content_of(message)
    if content is None:
        return message
    if row.logo is not None and row.logo_type is not None:
        src = data_url(row.logo, row.logo_type) if preview else f"cid:{LOGO_CID}"
    else:
        src = data_url(default_mark(), "image/png") if preview else f"cid:{mailhtml.MASCOT_CID}"
    html = render_html(row.body, values, content, logo_src=src)
    text = _plain(row.body, values, message.body.strip())
    return Rendered(message.kind, message.subject, text, html)


def render_draft(session: Session, markdown: str, values: Values, sample: Rendered) -> Rendered:
    """A draft Markdown (saved or not) around ``sample``, as a message would look: the saved logo
    or the refiroo mark, inline as data URLs. Nothing is saved."""
    check_markdown(markdown)
    row = load(session)
    draft = MailTemplate(
        id=1,
        body=markdown,
        logo=row.logo if row else None,
        logo_type=row.logo_type if row else None,
        version=0,
        updated_at=datetime.now(UTC),
    )
    return wrap(draft, sample, values, preview=True)


def apply(
    session: Session, identity: IdentitySettings, message: Rendered, recipient_name: str | None
) -> Rendered:
    """``message`` inside the saved template, for a person called ``recipient_name``; unchanged when
    no template is saved."""
    row = load(session)
    if row is None:
        return message
    values = Values(
        product(session),
        mail_settings.application_url(identity, mail_settings.load(session)),
        recipient_name or NO_NAME,
    )
    return wrap(row, message, values)


def logo_of(session: Session) -> tuple[bytes, str] | None:
    """The uploaded logo and its media type, to attach to a message; None for the refiroo mark."""
    row = load(session)
    return (row.logo, row.logo_type) if row and row.logo and row.logo_type else None
