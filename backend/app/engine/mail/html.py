"""The branded HTML of the messages the engine sends (D421, D432).

One layout for all five: a lavender band with the mascot and wordmark (and, for a renamed product,
its name after a thin divider, as the application's top bar shows it), a heading, the text, a
button, and a footer saying why the person got the message. It carries exactly the facts the plain
text carries, nothing more: every value is escaped here, and the images are ``cid:`` parts of the
message (``smtp.build``), never loaded from the application's address. Tables and inline styles
only, because mail clients ignore the rest.
"""

from dataclasses import dataclass
from html import escape
from pathlib import Path

from ...common.brand import is_default_product_name

MASCOT_CID = "refiroo-mascot"
WORDMARK_CID = "refiroo-wordmark"
BRAND_DIR = Path(__file__).parent / "brand"
IMAGES = {MASCOT_CID: "refiroo-mascot.png", WORDMARK_CID: "refiroo-wordmark.png"}

PAGE = "#f3f4fb"
INK = "#24244f"
HEADING = "#2a2a5e"
MUTED = "#66688c"
FAINT = "#8587a8"
LINK = "#5468d4"
BUTTON = "#6c7fe0"
RULE = "#eceefa"
# The dot before a notice: waiting on the person, done, failed.
WAITING, DONE, FAILED = "#7d95f0", "#8fe3c4", "#f2a48f"

FONT = "system-ui,-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"


def e(value: object) -> str:
    return escape(str(value), quote=True)


@dataclass(frozen=True)
class Block:
    """A piece of the message body, already safe HTML."""

    html: str


def paragraph(text: str, *, small: bool = False, raw: bool = False) -> Block:
    size, colour = ("13px", MUTED) if small else ("15px", INK)
    if raw:
        size, colour = "12px", MUTED
    word = "word-break:break-all;" if raw else ""
    return Block(
        f'<p style="margin:0 0 14px;font-size:{size};line-height:1.6;color:{colour};{word}">'
        f"{text}</p>"
    )


def button(href: str, label: str) -> Block:
    return Block(
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0" '
        'style="margin:4px 0 16px"><tr>'
        f'<td bgcolor="{BUTTON}" style="background:{BUTTON};border-radius:999px">'
        f'<a href="{e(href)}" style="display:inline-block;padding:12px 22px;font-size:15px;'
        f'font-weight:600;color:#ffffff;text-decoration:none">{e(label)}</a></td></tr></table>'
    )


def pill(text: str) -> Block:
    return Block(
        '<p style="margin:0 0 14px"><span style="display:inline-block;background:#e9faf3;'
        "color:#1f6b52;font-size:13px;font-weight:600;border-radius:999px;"
        f'padding:3px 10px">{e(text)}</span></p>'
    )


def link_fallback(href: str) -> Block:
    """The raw link, for a client that does not show the button."""
    return paragraph(f"Button not working? Paste this into your browser:<br>{e(href)}", raw=True)


def dot_row(colour: str, title: str, detail: str | None, href: str | None, *, rule: bool) -> str:
    """One notice: a coloured dot, its kind, a line of detail and an Open link."""
    border = f"border-top:1px solid {RULE};" if rule else ""
    more = f'<br><span style="font-size:13px;color:{MUTED}">{e(detail)}</span>' if detail else ""
    open_cell = ""
    if href:
        open_cell = (
            f'<td valign="top" style="{border}padding:12px 0 12px 12px;white-space:nowrap">'
            f'<a href="{e(href)}" style="font-size:13px;font-weight:600;color:{LINK};'
            'text-decoration:none">Open</a></td>'
        )
    return (
        f'<tr><td width="10" valign="top" style="{border}padding:19px 12px 0 0">'
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>'
        f'<td width="10" height="10" bgcolor="{colour}" '
        f'style="width:10px;height:10px;border-radius:50%;background:{colour};font-size:0;'
        'line-height:0">&nbsp;</td></tr></table></td>'
        f'<td valign="top" style="{border}padding:12px 0;font-size:15px;line-height:1.5;'
        f'color:{INK}"><b>{e(title)}</b>{more}</td>'
        f"{open_cell}</tr>"
    )


def rows(items: list[str]) -> Block:
    return Block(
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" '
        f'style="margin:4px 0 16px;border-bottom:1px solid {RULE}">' + "".join(items) + "</table>"
    )


def layout(product: str, heading: str, blocks: list[Block], footer: str, preheader: str) -> str:
    """The whole document. ``footer`` is safe HTML (the caller escapes what it puts in it)."""
    name = ""
    if not is_default_product_name(product):
        name = (
            f'<td style="padding-left:10px"><table role="presentation" cellpadding="0" '
            f'cellspacing="0" border="0"><tr><td style="border-left:1px solid #d5daf5;'
            f'padding-left:10px;font-size:15px;font-weight:700;color:{HEADING}">'
            f"{e(product)}</td></tr></table></td>"
        )
    body = "".join(block.html for block in blocks)
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<meta name="color-scheme" content="light only">'
        '<meta name="supported-color-schemes" content="light only">'
        f"<title>{e(heading)}</title></head>"
        f'<body style="margin:0;padding:0;background:{PAGE};color:{INK};font-family:{FONT}">'
        f'<div style="display:none;max-height:0;overflow:hidden;opacity:0">{e(preheader)}</div>'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" '
        f'bgcolor="{PAGE}" style="background:{PAGE}"><tr><td align="center" style="padding:24px 12px">'
        '<table role="presentation" width="560" cellpadding="0" cellspacing="0" border="0" '
        'style="width:100%;max-width:560px;background:#ffffff;border-radius:18px">'
        '<tr><td bgcolor="#eef1fe" style="background:#eef1fe;'
        "background-image:linear-gradient(180deg,#eef1fe 0%,#ffffff 100%);"
        'border-radius:18px 18px 0 0;padding:22px 28px 6px">'
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>'
        f'<td valign="middle"><img src="cid:{MASCOT_CID}" alt="" width="34" height="34" '
        'style="display:block;border:0"></td>'
        f'<td valign="middle" style="padding-left:10px"><img src="cid:{WORDMARK_CID}" alt="refiroo" '
        'height="18" style="display:block;border:0;height:18px;width:auto"></td>'
        f"{name}</tr></table></td></tr>"
        f'<tr><td style="padding:12px 28px 28px;font-size:15px;line-height:1.6;color:{INK}">'
        f'<h1 style="margin:8px 0 12px;font-size:22px;line-height:1.3;color:{HEADING}">'
        f"{e(heading)}</h1>{body}</td></tr></table>"
        '<table role="presentation" width="560" cellpadding="0" cellspacing="0" border="0" '
        'style="width:100%;max-width:560px"><tr><td align="center" '
        f'style="padding:18px 20px 4px;font-size:12px;line-height:1.6;color:{FAINT}">'
        f'<img src="cid:{MASCOT_CID}" alt="" width="40" height="40" '
        'style="display:block;margin:0 auto 6px;border:0">'
        f"{footer}</td></tr></table></td></tr></table></body></html>\n"
    )


def anchor(href: str, label: str) -> str:
    return f'<a href="{e(href)}" style="color:{LINK}">{e(label)}</a>'
