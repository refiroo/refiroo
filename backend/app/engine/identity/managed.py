"""A person whose sign-in an administrator manages (0.17 SA1).

While ``User.sign_in_managed`` is on, the person changes none of their own credentials and ends
no session but the one they hold: an account several people share by a known password cannot be
taken from all of them by one. This is the one rule; every own-credential operation calls
``refuse`` (or ``refuse_for``) before it does anything. What an administrator does for the person
(a reset link, removing a second factor or a passkey, ending sessions) never asks it.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...errors import ApiError, api_error
from ...models.database import User

MESSAGE = "An administrator manages the sign-in of this account"


def _refusal() -> ApiError:
    return api_error(403, "SIGN_IN_MANAGED", MESSAGE)


def refuse(user: User) -> None:
    """``403 SIGN_IN_MANAGED`` when an administrator manages this person's sign-in."""
    if user.sign_in_managed:
        raise _refusal()


def is_managed(session: Session, user_public_id: str) -> bool:
    """Whether an administrator manages the sign-in of the person with this public ID."""
    return bool(
        session.scalar(select(User.sign_in_managed).where(User.public_id == user_public_id))
    )


def refuse_for(session: Session, user_public_id: str) -> None:
    """``refuse`` for a person named by public ID."""
    if is_managed(session, user_public_id):
        raise _refusal()
