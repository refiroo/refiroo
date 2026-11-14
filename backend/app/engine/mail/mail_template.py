"""The e-mail template an operator edits in Settings, used for every mail the engine sends.

One template per instance: Markdown with ``{{placeholders}}`` and a logo. It is rendered to HTML (and
a plain-text alternative) around the content of each message: the message's own heading, text and
button replace ``{{content}}``, which the template holds exactly once. Without a saved template the
engine's own layout (``html.layout``) applies; "reset to default" deletes the row.

The Markdown is converted with raw HTML switched off, images off and links limited to http, https and
mailto, so what an operator writes cannot carry script or an event handler. The logo is sent inline
(``cid:``): an uploaded PNG, JPEG or SVG (no script in it, at most 512 KB), else the refiroo mark.
"""

import hashlib
import re
import secrets
from base64 import b64encode
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from html import escape
from xml.etree import ElementTree

from markdown_it import MarkdownIt
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from ...errors import api_error, version_conflict
from ...models.database import MailLogo, MailOutbox, MailTemplate
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
# A DTD (entities, external subsets) and processing instructions other than the XML declaration
# are refused before parsing, so the parser never expands or fetches anything.
_SVG_PROLOG = re.compile(r"<!\s*(doctype|entity)|<\?(?!xml[\s?])", re.IGNORECASE)
_SVG_ELEMENTS = {"script", "foreignobject", "iframe", "object", "embed"}
_CSS_URL = re.compile(r"url\(\s*(['\"]?)(.*?)\1\s*\)", re.IGNORECASE | re.DOTALL)
_ADDRESSED = re.compile(r"^\s*(#|data:image/)", re.IGNORECASE)
_CONTENT = re.compile(
    rf"<!--{mailhtml.CONTENT_OPEN}-->(.*?)<!--{mailhtml.CONTENT_CLOSE}-->", re.DOTALL
)
_GREETING = re.compile(
    rf"<!--{mailhtml.GREETING_OPEN}-->.*?<!--{mailhtml.GREETING_CLOSE}-->", re.DOTALL
)
_FOOTER = re.compile(
    rf"<!--{mailhtml.FOOTER_OPEN}-->(.*?)<!--{mailhtml.FOOTER_CLOSE}-->", re.DOTALL
)
_PARAGRAPH = '<p style="margin:0 0 14px;font-size:15px;line-height:1.6">'
_SAFE_LINK = re.compile(r"^(https?:|mailto:)", re.IGNORECASE)


# --- the stored template -------------------------------------------------------------------------


def load(session: Session, *, for_update: bool = False) -> MailTemplate | None:
    statement = select(MailTemplate).where(MailTemplate.id == 1)
    return session.scalar(statement.with_for_update() if for_update else statement)


def _check_version(row: MailTemplate | None, expected: int | None, session: Session) -> None:
    if (row.version if row else None) != expected:
        session.rollback()
        raise version_conflict(
            row.version if row else 0, "", message="The e-mail template has changed"
        )


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
        row = _first_save(session, body=markdown, now=now)
    elif row.body != markdown:
        row.body, row.version, row.updated_at = markdown, row.version + 1, now
    session.commit()
    return row


def _first_save(session: Session, *, now: datetime, **values) -> MailTemplate:
    """Insert the one row; a first save at the same moment by another request has the row already,
    so this one is stale (``409 VERSION_CONFLICT``) instead of failing on the key (R17-F26)."""
    inserted = session.execute(
        insert(MailTemplate)
        .values(id=1, version=1, updated_at=now, **values)
        .on_conflict_do_nothing(index_elements=["id"])
    ).rowcount
    if not inserted:
        session.rollback()
        current = load(session)
        raise version_conflict(
            current.version if current else 0, "", message="The e-mail template has changed"
        )
    return load(session)  # type: ignore[return-value]


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
    if text is not None and "<svg" in text.lower() and _check_svg(data, text):
        return "image/svg+xml"
    raise api_error(
        422,
        "MAIL_LOGO_UNSUPPORTED",
        "The logo must be a PNG, JPEG or SVG image",
        {"accepted": list(LOGO_TYPES)},
    )


def _unsafe_svg():
    return api_error(
        422,
        "MAIL_LOGO_UNSAFE",
        "The SVG holds script or an external object, which is refused",
    )


def _local(name: str) -> str:
    return name.rpartition("}")[2].rpartition(":")[2].lower()


def _css_unsafe(css: str) -> bool:
    """A style that imports a sheet, escapes its own words or reaches outside the picture."""
    lowered = css.lower()
    if "@import" in lowered or "\\" in css or "expression(" in lowered:
        return True
    return any(not _ADDRESSED.match(found.group(2)) for found in _CSS_URL.finditer(css))


def _check_svg(data: bytes, text: str) -> bool:
    """Whether ``data`` is an SVG; ``422 MAIL_LOGO_UNSAFE`` when it can run or fetch anything. It is
    parsed as XML (no DTD, so no entities); no script or foreignObject element in any namespace, no
    ``on*`` attribute, no link but to the picture itself (``#``) or an inline image, no style that
    imports or reaches out."""
    if _SVG_PROLOG.search(text):
        raise _unsafe_svg()
    try:
        root = ElementTree.fromstring(data)
    except ElementTree.ParseError:
        return False
    if _local(root.tag) != "svg":
        return False
    for element in root.iter():
        if not isinstance(element.tag, str):
            raise _unsafe_svg()
        name = _local(element.tag)
        if name in _SVG_ELEMENTS:
            raise _unsafe_svg()
        if name == "style" and _css_unsafe(element.text or ""):
            raise _unsafe_svg()
        animated = _local(element.get("attributeName", ""))
        if name in ("set", "animate") and (animated == "href" or animated.startswith("on")):
            raise _unsafe_svg()
        for key, value in element.attrib.items():
            attribute = _local(key)
            if attribute.startswith("on"):
                raise _unsafe_svg()
            if attribute == "href" and not _ADDRESSED.match(value):
                raise _unsafe_svg()
            if attribute == "style" and _css_unsafe(value):
                raise _unsafe_svg()
            if re.sub(r"[\s\x00-\x20]", "", value).lower().startswith("javascript:"):
                raise _unsafe_svg()
    return True


def set_logo(
    session: Session, data: bytes, content_type: str, expected_version: int | None
) -> MailTemplate:
    """Store the logo with the template (creating it from the default Markdown when none is saved)."""
    media_type = check_logo(data, content_type)
    row = load(session, for_update=True)
    _check_version(row, expected_version, session)
    now = datetime.now(UTC)
    digest = keep_logo(session, data, media_type)
    if row is None:
        row = _first_save(
            session,
            body=DEFAULT_MARKDOWN,
            logo=data,
            logo_type=media_type,
            logo_digest=digest,
            now=now,
        )
    else:
        row.logo, row.logo_type, row.logo_digest, row.version, row.updated_at = (
            data,
            media_type,
            digest,
            row.version + 1,
            now,
        )
    session.commit()
    return row


def keep_logo(session: Session, data: bytes, media_type: str) -> str:
    """Keep a copy of the logo by its SHA-256, which a message rendered with it refers to until it
    is sent (R17-F22); the digest."""
    digest = hashlib.sha256(data).hexdigest()
    session.execute(
        insert(MailLogo)
        .values(digest=digest, logo=data, logo_type=media_type)
        .on_conflict_do_nothing(index_elements=["digest"])
    )
    return digest


def logo_by_digest(session: Session, digest: str) -> tuple[bytes, str] | None:
    found = session.execute(
        select(MailLogo.logo, MailLogo.logo_type).where(MailLogo.digest == digest)
    ).one_or_none()
    return None if found is None else (found[0], found[1])


def prune_logos(session: Session) -> int:
    """Delete the logo copies nothing refers to: not the saved logo, not a waiting message's."""
    wanted = select(MailOutbox.logo_digest).where(
        MailOutbox.status == "pending", MailOutbox.logo_digest.is_not(None)
    )
    saved = select(MailTemplate.logo_digest).where(MailTemplate.logo_digest.is_not(None))
    return session.execute(
        delete(MailLogo).where(MailLogo.digest.not_in(wanted), MailLogo.digest.not_in(saved))
    ).rowcount


def clear_logo(session: Session, expected_version: int | None) -> MailTemplate:
    """Remove the logo: the refiroo mark is used. ``409 MAIL_TEMPLATE_NOT_SAVED`` without a template."""
    row = load(session, for_update=True)
    _check_version(row, expected_version, session)
    if row is None:
        session.rollback()
        raise api_error(409, "MAIL_TEMPLATE_NOT_SAVED", "No template is saved: there is no logo")
    if row.logo is not None:
        row.logo, row.logo_type, row.logo_digest = None, None, None
        row.version += 1
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


def _markdown(prefix: str) -> MarkdownIt:
    md = MarkdownIt("commonmark", {"html": False, "breaks": False})
    md.disable(["image", "html_block", "html_inline"])
    # A link is http, https or mailto, or a placeholder (which stands for such an address).
    md.validateLink = lambda url: bool(_SAFE_LINK.match(url.strip())) or url.startswith(prefix)
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


def _tokens(markdown: str) -> tuple[str, str, list[str]]:
    """The Markdown with each placeholder replaced by a word Markdown leaves alone: a prefix made
    for this call (so no text can hold it), then the placeholder's index. The prefix and the names."""
    prefix = f"zzph{secrets.token_hex(6)}x"
    names: list[str] = []

    def swap(match: re.Match[str]) -> str:
        names.append(match.group(1).strip())
        return f"{prefix}{len(names) - 1}z"

    return _PLACEHOLDER.sub(swap, markdown), prefix, names


def _fill(text: str, prefix: str, names: list[str], value: Callable[[str, bool], str]) -> str:
    """Each token of ``text`` replaced by its value in one pass: a value is never read again, so one
    that holds a token (or any placeholder text) stays as it is. ``value(name, alone)`` says what a
    placeholder stands for; ``alone`` is true when it is a paragraph by itself."""
    token = rf"{prefix}(\d+)z"
    pattern = re.compile(rf"{re.escape(_PARAGRAPH)}{token}</p>|{token}")

    def put(found: re.Match[str]) -> str:
        alone = found.group(1) is not None
        return value(names[int(found.group(1) or found.group(2))], alone)

    return pattern.sub(put, text)


def _logo_tag(values: Values, src: str) -> str:
    return (
        f'<img src="{escape(src, quote=True)}" alt="{escape(values.product_name, quote=True)}" '
        'style="display:block;border:0;max-height:48px;max-width:240px;height:auto;width:auto">'
    )


def render_html(markdown: str, values: Values, content_html: str, *, logo_src: str) -> str:
    """The template's Markdown as a whole HTML document around ``content_html``. ``logo_src`` is
    where the logo image is read from (``cid:`` in a message, a data URL in a preview)."""
    swapped, prefix, names = _tokens(markdown)
    body = _markdown(prefix).render(swapped)
    for plain, styled in _STYLES:
        body = body.replace(plain, styled)
    body = body.replace("<a href=", f'<a style="color:{mailhtml.LINK}" href=')
    html_values = {
        "content": content_html,
        "logo": _logo_tag(values, logo_src),
        "product_name": escape(values.product_name),
        "instance_url": escape(values.instance_url, quote=True),
        "recipient_name": escape(values.recipient_name),
    }

    def value(name: str, alone: bool) -> str:
        found = html_values.get(name, "")
        if alone and name not in ("content", "logo"):
            return f"{_PARAGRAPH}{found}</p>"
        # Content and the logo are blocks: a paragraph holding only one is replaced by it.
        return found

    body = _fill(body, prefix, names, value)
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
    """The template as text: placeholders filled, links as ``label (address)``, no Markdown marks.
    The marks are stripped from the template alone; the values go in afterwards, as they are."""
    swapped, prefix, names = _tokens(markdown)
    done = re.sub(r"\[([^\]]*)\]\(([^)]*)\)", lambda m: f"{m.group(1)} ({m.group(2)})", swapped)
    done = re.sub(r"(\*\*|__)(.+?)\1", r"\2", done)
    done = re.sub(r"(?<![\w*])[*_]([^*_\n]+)[*_](?![\w*])", r"\1", done)
    done = re.sub(r"^#{1,6}\s+", "", done, flags=re.MULTILINE)
    done = re.sub(r"^-{3,}\s*$", "--", done, flags=re.MULTILINE)
    plain = {
        "product_name": values.product_name,
        "instance_url": values.instance_url,
        "recipient_name": values.recipient_name,
        "content": content_text,
        "logo": "",
    }
    done = _fill(done, prefix, names, lambda name, alone: plain.get(name, ""))
    return re.sub(r"\n{3,}", "\n\n", done).strip() + "\n"


def content_of(message: Rendered) -> str | None:
    """The message's own HTML (heading, text, button, footer sentence), or None for a message
    without the layout's markers, which a template cannot wrap."""
    found = _CONTENT.search(message.html or "")
    if found is None:
        return None
    content = _GREETING.sub("", found.group(1))
    footer = _FOOTER.search(message.html)
    tail = (
        f'<p style="margin:18px 0 0;font-size:12px;line-height:1.6;color:{mailhtml.FAINT}">'
        f"{footer.group(1)}</p>"
        if footer
        else ""
    )
    return content + tail


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
    if row.logo_type is not None:
        src = data_url(row.logo, row.logo_type) if preview else f"cid:{LOGO_CID}"  # type: ignore[arg-type]
    else:
        src = data_url(default_mark(), "image/png") if preview else f"cid:{mailhtml.MASCOT_CID}"
    html = render_html(row.body, values, content, logo_src=src)
    # The template greets (``Hello {{recipient_name}},`` by default): the message's own greeting goes.
    body = message.body.strip().removeprefix(f"Hello {values.recipient_name},").strip()
    text = _plain(row.body, values, body)
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
        logo_digest=row.logo_digest if row else None,
        version=0,
        updated_at=datetime.now(UTC),
    )
    return wrap(draft, sample, values, preview=True)


def apply(
    session: Session, identity: IdentitySettings, message: Rendered, recipient_name: str | None
) -> Rendered:
    """``message`` inside the saved template, for a person called ``recipient_name``; unchanged when
    no template is saved."""
    return apply_queued(session, identity, message, recipient_name)[0]


def apply_queued(
    session: Session, identity: IdentitySettings, message: Rendered, recipient_name: str | None
) -> tuple[Rendered, str | None]:
    """As ``apply``, and the digest of the logo the HTML refers to (``cid:``), if it does: the
    message keeps it so it is sent with that logo, not one saved later (R17-F22)."""
    row = load(session)
    if row is None:
        return message, None
    values = Values(
        product(session),
        mail_settings.application_url(identity, mail_settings.load(session)),
        recipient_name or NO_NAME,
    )
    wrapped = wrap(row, message, values)
    shows_logo = wrapped.html is not None and f"cid:{LOGO_CID}" in wrapped.html
    return wrapped, row.logo_digest if shows_logo else None


def logo_of(session: Session) -> tuple[bytes, str] | None:
    """The uploaded logo and its media type, to attach to a message; None for the refiroo mark."""
    row = load(session)
    return (row.logo, row.logo_type) if row and row.logo and row.logo_type else None
