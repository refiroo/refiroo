"""The plain-text messages the engine sends (Product 0.12 M1, D421).

A message names the product, the person, the link and how long it works, and says in one sentence
to ignore it if it was not expected. It never carries a password, a code or record content: mail
travels and sits in mailboxes.
"""

from dataclasses import dataclass

# What a message calls the product when no model names one.
PRODUCT = "refiroo"

ACTIVATION = "activation"
PASSWORD_RESET = "password-reset"
TEST = "test"
KINDS = (ACTIVATION, PASSWORD_RESET, TEST)

IGNORE = "If you did not expect this message, ignore it; nothing changes."


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
