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
from ..identity.second_factor import product_name
from ..notifications import kinds

# What a message calls the product when no model names one.
PRODUCT = "refiroo"

ACTIVATION = "activation"
PASSWORD_RESET = "password-reset"
TEST = "test"
NOTICE = "notice"
DIGEST = "digest"
KINDS = (ACTIVATION, PASSWORD_RESET, TEST, NOTICE, DIGEST)

IGNORE = "If you did not expect this message, ignore it; nothing changes."


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


def lasts(hours: int) -> str:
    """How long a link works, in the words people use."""
    if hours % 24 == 0:
        days = hours // 24
        return f"{days} day" if days == 1 else f"{days} days"
    return f"{hours} hour" if hours == 1 else f"{hours} hours"


def activation(product: str, name: str, link: str, hours: int) -> Rendered:
    """Welcome to a new person: the link where they choose a password."""
    return Rendered(
        ACTIVATION,
        f"Your {product} account",
        f"Hello {name},\n\n"
        f"An account was made for you in {product}. Choose your password with this link:\n\n"
        f"{link}\n\n"
        f"The link works once and for {lasts(hours)}. {IGNORE}\n",
    )


def password_reset(product: str, name: str, link: str, hours: int) -> Rendered:
    """A link where a person chooses a new password."""
    return Rendered(
        PASSWORD_RESET,
        f"Choose a new {product} password",
        f"Hello {name},\n\n"
        f"A new password was asked for your {product} account. Choose it with this link:\n\n"
        f"{link}\n\n"
        f"The link works once and for {lasts(hours)}. {IGNORE}\n",
    )


def test_message(product: str, application_url: str) -> Rendered:
    """Proves the settings work, and shows the address the links will point to (D422)."""
    return Rendered(
        TEST,
        f"{product}: test message",
        f"This is a test message from {product}. Mail is set up and this address received it.\n\n"
        f"Links in the mail {product} sends point to:\n\n{application_url}\n\n"
        "If that address is wrong, change it on the Mail page.\n",
    )


# What one inbox notice says, by its kind: the kind of event and nothing of what it is about (D432).
_NOTICE_SENTENCES = {kind: f"{label}." for kind, label in kinds.LABELS.items()}
_NOTICE_OTHER = "Something is waiting in your inbox."


def notice(product: str, notice_kind: str, application_url: str) -> Rendered:
    """One inbox notice: names the kind of event and links to the application, and carries no
    record, change set, workspace or person content (D239, D421, D432)."""
    sentence = _NOTICE_SENTENCES.get(notice_kind, _NOTICE_OTHER)
    return Rendered(
        NOTICE,
        f"{product}: something is waiting in your inbox",
        f"{sentence}\n\n"
        f"Open {product} to see it:\n\n{application_url}\n\n"
        "You get this message because you asked for mail when something arrives in your inbox. "
        "Choose which messages you get, or switch them off, on Settings > Notifications.\n",
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
    return Rendered(
        DIGEST,
        f"{product}: {_plural(total, 'notice', 'notices')} in your inbox",
        f"{'; '.join(parts)}.\n\n"
        "Since your last digest:\n\n" + "\n\n".join(blocks) + "\n" + after + "\n"
        f"Open your inbox:\n\n{base}/notifications\n\n"
        f"You get this message because you asked for a {every} digest of your inbox. Choose which "
        f"notices are in it, change it to {other_every}, or switch it off, on Settings > "
        "Notifications.\n",
    )
