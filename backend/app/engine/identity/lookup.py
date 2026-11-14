"""Finding a person: by public ID and by e-mail address (unique without regard to case, so at most
one person holds an address)."""

from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...errors import api_error
from ...models.database import User


def load_user(session: Session, public_id: str, *, for_update: bool = False) -> User:
    statement = select(User).where(User.public_id == public_id)
    user = session.scalar(statement.with_for_update() if for_update else statement)
    if user is None:
        raise api_error(404, "USER_NOT_FOUND", f"User '{public_id}' not found")
    return user


def user_by_email(
    session: Session,
    email: str,
    *,
    except_id: int | None = None,
    where: Sequence[Any] = (),
) -> User | None:
    """The person holding ``email``, ignoring case, or ``None``. ``email`` is matched as given:
    a caller that takes typed input strips it first. ``except_id`` leaves one person out (the one
    changing their own address); ``where`` adds conditions (the password reset asks only for a
    person who is active, has a local password and is not managed)."""
    statement = select(User).where(func.lower(User.email) == email.lower(), *where)
    if except_id is not None:
        statement = statement.where(User.id != except_id)
    return session.scalar(statement)
