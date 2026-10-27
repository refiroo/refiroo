"""The plain-text messages the engine sends (Product 0.12 M1, D421).

A message names the product, the person, the link and how long it works, and says in one sentence
to ignore it if it was not expected. It never carries a password, a code or record content: mail
travels and sits in mailboxes.
"""

from dataclasses import dataclass

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
KINDS = (ACTIVATION, PASSWORD_RESET, TEST, NOTICE)

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
