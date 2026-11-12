"""The plain-text messages the engine sends (Product 0.12 M1, D421).

A message names the product, the person, the link and how long it works, and says in one sentence
to ignore it if it was not expected. It never carries a password, a code or record content: mail
travels and sits in mailboxes.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from ...common.brand import is_default_product_name
from ..identity.product import product_name
from ..notifications import kinds
from . import html as mailhtml

# What a message calls the product when no model names one.
PRODUCT = "refiroo"

ACTIVATION = "activation"
PASSWORD_RESET = "password-reset"
TEST = "test"
NOTICE = "notice"
DIGEST = "digest"
SECURITY = "security"
KINDS = (ACTIVATION, PASSWORD_RESET, TEST, NOTICE, DIGEST, SECURITY)

IGNORE = "If you did not expect this message, ignore it; nothing changes."
SETTINGS_POINTER = "on Settings › Notifications."


def product(session: Session) -> str:
    """What every message calls the product: the name the default workspace's model gives it, and
    ``refiroo`` where the model keeps a default name. One answer for every message, whatever
    caused it."""
    name = product_name(session, PRODUCT)
    return PRODUCT if is_default_product_name(name) else name


@dataclass(frozen=True)
class Rendered:
    kind: str
    subject: str
    body: str
    html: str = ""


def lasts(hours: int) -> str:
    """How long a link works, in the words people use."""
    if hours % 24 == 0:
        days = hours // 24
        return f"{days} day" if days == 1 else f"{days} days"
    return f"{hours} hour" if hours == 1 else f"{hours} hours"


def activation(product: str, name: str, link: str, hours: int) -> Rendered:
    """Welcome to a new person: the link where they choose a password."""
    html = mailhtml.layout(
        product,
        f"Welcome aboard, {name}",
        [
            mailhtml.paragraph(
                f"An account was made for you in {mailhtml.e(product)}. "
                "Choose your password with this link."
            ),
            mailhtml.button(link, "Choose my password"),
            mailhtml.pill(f"Works once · for {lasts(hours)}"),
            mailhtml.paragraph(mailhtml.e(IGNORE), small=True),
            mailhtml.link_fallback(link),
        ],
        f"Sent by {mailhtml.e(product)} because an account was made for you.",
        f"An account was made for you in {product}.",
    )
    return Rendered(
        ACTIVATION,
        f"Your {product} account",
        f"Hello {name},\n\n"
        f"An account was made for you in {product}. Choose your password with this link:\n\n"
        f"{link}\n\n"
        f"The link works once and for {lasts(hours)}. {IGNORE}\n",
        html,
    )


def password_reset(product: str, name: str, link: str, hours: int) -> Rendered:
    """A link where a person chooses a new password."""
    html = mailhtml.layout(
        product,
        "Let's get you a new password",
        [
            mailhtml.paragraph(
                f"Hello {mailhtml.e(name)}, a new password was asked for your "
                f"{mailhtml.e(product)} account. Choose it with this link."
            ),
            mailhtml.button(link, "Choose a new password"),
            mailhtml.pill(f"Works once · for {lasts(hours)}"),
            mailhtml.paragraph(mailhtml.e(IGNORE), small=True),
            mailhtml.link_fallback(link),
        ],
        f"Sent by {mailhtml.e(product)} because a new password was asked for your account.",
        f"A new password was asked for your {product} account.",
    )
    return Rendered(
        PASSWORD_RESET,
        f"Choose a new {product} password",
        f"Hello {name},\n\n"
        f"A new password was asked for your {product} account. Choose it with this link:\n\n"
        f"{link}\n\n"
        f"The link works once and for {lasts(hours)}. {IGNORE}\n",
        html,
    )


def test_message(product: str, application_url: str) -> Rendered:
    """Proves the settings work, and shows the address the links will point to (D422)."""
    html = mailhtml.layout(
        product,
        "Hop hop, mail works!",
        [
            mailhtml.paragraph(
                f"This is a test message from {mailhtml.e(product)}. "
                "Mail is set up and this address received it."
            ),
            mailhtml.paragraph(f"Links in the mail {mailhtml.e(product)} sends point to:"),
            mailhtml.pill(application_url),
            mailhtml.paragraph("If that address is wrong, change it on the Mail page.", small=True),
        ],
        f"Sent by {mailhtml.e(product)} from the Mail page.",
        "Mail is set up and this address received it.",
    )
    return Rendered(
        TEST,
        f"{product}: test message",
        f"This is a test message from {product}. Mail is set up and this address received it.\n\n"
        f"Links in the mail {product} sends point to:\n\n{application_url}\n\n"
        "If that address is wrong, change it on the Mail page.\n",
        html,
    )


def template_test(product: str, application_url: str) -> Rendered:
    """What the operator's e-mail template wraps in a preview or a test: a short sample message."""
    html = mailhtml.layout(
        product,
        "This is how your mail looks",
        [
            mailhtml.paragraph(
                f"This is a sample message from {mailhtml.e(product)}. Every message it sends "
                "(invitations, password resets, notices and digests) appears in this place."
            ),
            mailhtml.button(application_url, "Open the application"),
        ],
        f"Sent by {mailhtml.e(product)} to try the e-mail template.",
        "A sample of the e-mail template.",
    )
    return Rendered(
        TEST,
        f"{product}: e-mail template test",
        "This is how your mail looks\n\n"
        f"This is a sample message from {product}. Every message it sends (invitations, password "
        "resets, notices and digests) appears in this place.\n\n"
        f"Open the application: {application_url}\n\n"
        f"Sent by {product} to try the e-mail template.\n",
        html,
    )


# What one inbox notice says, by its kind: the kind of event and nothing of what it is about (D432).
_NOTICE_SENTENCES = {kind: f"{label}." for kind, label in kinds.LABELS.items()}
_NOTICE_OTHER = "Something is waiting in your inbox."


def _colour(kind: str) -> str:
    """The dot before a notice: waiting on the person, done, or failed."""
    if kind == "job.failed":
        return mailhtml.FAILED
    if kind in ("change-set.approved", "job.completed", "change-set.published"):
        return mailhtml.DONE
    return mailhtml.WAITING


def notice(product: str, notice_kind: str, application_url: str) -> Rendered:
    """One inbox notice: names the kind of event and links to the application, and carries no
    record, change set, workspace or person content (D239, D421, D432)."""
    sentence = _NOTICE_SENTENCES.get(notice_kind, _NOTICE_OTHER)
    html = mailhtml.layout(
        product,
        "Something's waiting for you",
        [
            mailhtml.rows(
                [mailhtml.dot_row(_colour(notice_kind), sentence, None, None, rule=False)]
            ),
            mailhtml.button(application_url, "Open my inbox"),
        ],
        "You get this because you asked for mail when something arrives in your inbox.<br>"
        "Choose which messages you get, or switch them off, " + SETTINGS_POINTER,
        sentence,
    )
    return Rendered(
        NOTICE,
        f"{product}: something is waiting in your inbox",
        f"{sentence}\n\n"
        f"Open {product} to see it:\n\n{application_url}\n\n"
        "You get this message because you asked for mail when something arrives in your inbox. "
        "Choose which messages you get, or switch them off, on Settings > Notifications.\n",
        html,
    )


# What a count of notices of one kind says in the digest's opening sentence: singular, plural (the
# kinds' words, ``notifications/kinds.py``). A kind not listed counts as "other".
_DIGEST_PHRASES = {
    "change-set.submitted": (
        "change set waits for your approval",
        "change sets wait for your approval",
    ),
    "change-set.approved": (
        "change set you submitted was approved",
        "change sets you submitted were approved",
    ),
    "change-set.sent-back": (
        "change set you submitted was sent back",
        "change sets you submitted were sent back",
    ),
    "job.completed": ("job you started has finished", "jobs you started have finished"),
    "job.failed": ("job you started failed", "jobs you started failed"),
    "job.awaiting-confirmation": (
        "job you started waits for your confirmation",
        "jobs you started wait for your confirmation",
    ),
    "change-set.published": (
        "change set was published in a workspace you follow",
        "change sets were published in a workspace you follow",
    ),
}
_DIGEST_OTHER = ("other notice", "other notices")
_JOB_WORDS = {
    "batch": "A batch",
    "import": "An import",
    "export": "An export",
    "migration": "A migration",
    "move": "A move",
    "aiProposal": "An AI proposal",
    "aiTask": "An AI task",
}


@dataclass(frozen=True)
class DigestLine:
    """One notice of a digest: its ID (the link), kind, when (in the person's time zone), and for a
    job its kind and, while the job is kept, its counts. Never a name (D432, AO-D31)."""

    notice_id: str
    kind: str
    when: datetime
    job_kind: str | None = None
    job_counts: dict[str, Any] | None = None


def _plural(count: int, one: str, many: str) -> str:
    return f"{count} {one if count == 1 else many}"


def _job_line(line: DigestLine) -> str:
    """ "An import, 1,286 rows applied, 14 rows rejected": the job's kind and, while it is kept, its
    applied and rejected counts."""
    words = [_JOB_WORDS.get(line.job_kind or "", "A job")]
    counts = line.job_counts or {}
    unit = ("row", "rows") if line.job_kind == "import" else ("item", "items")
    applied, rejected = counts.get("applied"), counts.get("rejected")
    if isinstance(applied, int):
        words.append(f"{applied:,} {unit[applied != 1]} applied")
    if isinstance(rejected, int) and rejected > 0:
        words.append(f"{rejected:,} {unit[rejected != 1]} rejected")
    return ", ".join(words)


def digest(
    product: str,
    application_url: str,
    every: str,
    counts: dict[str, int],
    lines: list[DigestLine],
) -> Rendered:
    """A person's digest: the counts by kind in a sentence, then the newest notices with their kind,
    time and link (``lines`` newest first; the rest are counted, with "and N more"), and where to
    change it. Carries no record, change set, workspace, person or file name (D239, D421, D432)."""
    total = sum(counts.values())
    kinds_known = [kind for kind, _ in kinds.NOTICE_KINDS if kind in counts]
    parts = [
        f"{counts[kind]} {_DIGEST_PHRASES[kind][counts[kind] != 1]}"
        for kind in kinds_known
        if kind in _DIGEST_PHRASES
    ]
    other = total - sum(counts[kind] for kind in kinds_known if kind in _DIGEST_PHRASES)
    if other:
        parts.append(_plural(other, *_DIGEST_OTHER))
    base = application_url.rstrip("/")
    blocks = []
    for line in lines:
        block = [f"- {kinds.LABELS.get(line.kind, _NOTICE_OTHER.rstrip('.'))}"]
        if line.job_kind is not None:
            block.append(f"  {_job_line(line)}")
        block.append(f"  {line.when:%A} {line.when.day} {line.when:%B}, {line.when:%H:%M}")
        block.append(f"  {base}/notifications?notice={line.notice_id}")
        blocks.append("\n".join(block))
    more = total - len(lines)
    after = f"\nand {more} more in your inbox.\n" if more > 0 else ""
    other_every = "weekly" if every == "daily" else "daily"
    items = []
    for number, line in enumerate(lines):
        detail = f"{_job_line(line)} · " if line.job_kind is not None else ""
        detail += f"{line.when:%A} {line.when.day} {line.when:%B}, {line.when:%H:%M}"
        items.append(
            mailhtml.dot_row(
                _colour(line.kind),
                kinds.LABELS.get(line.kind, _NOTICE_OTHER.rstrip(".")),
                detail,
                f"{base}/notifications?notice={line.notice_id}",
                rule=number > 0,
            )
        )
    page = [mailhtml.paragraph(mailhtml.e(f"{'; '.join(parts)}."))]
    if items:
        page.append(mailhtml.rows(items))
    if more > 0:
        page.append(mailhtml.paragraph(f"and {more} more in your inbox.", small=True))
    page.append(mailhtml.button(f"{base}/notifications", "Open my inbox"))
    html = mailhtml.layout(
        product,
        f"Your {every} digest",
        page,
        f"You get this because you asked for a {mailhtml.e(every)} digest of your inbox.<br>"
        f"Choose which notices are in it, change it to {other_every}, or switch it off, "
        + SETTINGS_POINTER,
        f"{_plural(total, 'notice', 'notices')} in your inbox.",
    )
    return Rendered(
        DIGEST,
        f"{product}: {_plural(total, 'notice', 'notices')} in your inbox",
        f"{'; '.join(parts)}.\n\n"
        "Since your last digest:\n\n" + "\n\n".join(blocks) + "\n" + after + "\n"
        f"Open your inbox:\n\n{base}/notifications\n\n"
        f"You get this message because you asked for a {every} digest of your inbox. Choose which "
        f"notices are in it, change it to {other_every}, or switch it off, on Settings > "
        "Notifications.\n",
        html,
    )


# What a change to a person's sign-in says, by its event (SM1): the subject's words, the heading and
# what changed.
SECURITY_CHANGES = {
    "password-changed": (
        "your password was changed",
        "Your password was changed",
        "the password of your {product} account was changed",
    ),
    "password-reset": (
        "your password was reset",
        "Your password was reset",
        "the password of your {product} account was reset with a one-time link",
    ),
    "second-factor-added": (
        "an authenticator app was added to your account",
        "An authenticator app was added",
        "an authenticator app was added to your {product} account as a second step when you sign in",
    ),
    "second-factor-removed": (
        "the authenticator app was removed from your account",
        "Your authenticator app was removed",
        "the authenticator app was removed from your {product} account",
    ),
    "passkey-added": (
        "a passkey was added to your account",
        "A passkey was added",
        "a passkey was added to your {product} account",
    ),
    "passkey-removed": (
        "a passkey was removed from your account",
        "A passkey was removed",
        "a passkey was removed from your {product} account",
    ),
}
NOT_YOU = "If this was not you, contact an administrator of {product} at once."


def security_change(product: str, name: str, change: str, when: datetime) -> Rendered:
    """A person's sign-in changed: what changed and when, and what to do if it was not them. It
    carries no password, code or link that signs in, and is sent whether or not the person asked
    for mail (D421)."""
    subject_words, heading, what = SECURITY_CHANGES[change]
    what = what.format(product=product)
    at = f"{when:%A} {when.day} {when:%B %Y}, {when:%H:%M} UTC"
    advice = NOT_YOU.format(product=product)
    html = mailhtml.layout(
        product,
        heading,
        [
            mailhtml.paragraph(f"Hello {mailhtml.e(name)}, {mailhtml.e(what)}."),
            mailhtml.pill(at),
            mailhtml.paragraph(mailhtml.e(advice)),
            mailhtml.paragraph("If it was you, nothing more is needed.", small=True),
        ],
        f"Sent by {mailhtml.e(product)} because the way you sign in changed. "
        "These messages cannot be switched off.",
        f"{heading}.",
    )
    return Rendered(
        SECURITY,
        f"{product}: {subject_words}",
        f"Hello {name},\n\n{what[0].upper()}{what[1:]} on {at}.\n\n{advice}\n"
        "If it was you, nothing more is needed.\n",
        html,
    )
