"""People: created, changed, deactivated and listed; never deleted (Product 0.12 I1, D237)."""

from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ...common.pagination import Page, PageRequest, integer_key, paginate_statement
from ...errors import ApiError, api_error
from ...models.commands import UserCreate, UserUpdate
from ...models.database import User
from . import sessions
from .passwords import DEFAULT_MIN_LENGTH, check_password, hash_secret

_KEYS = (integer_key("sequenceId", User.id, "id"),)


def _changing[T](session: Session, change: Callable[[], T]) -> T:
    try:
        result = change()
        session.commit()
    except ApiError:
        session.rollback()
        raise
    except IntegrityError:
        session.rollback()
        raise _taken() from None
    return result


def _taken() -> ApiError:
    return api_error(409, "USERNAME_TAKEN", "Another person has this username")


def load_user(session: Session, public_id: str, *, for_update: bool = False) -> User:
    statement = select(User).where(User.public_id == public_id)
    user = session.scalar(statement.with_for_update() if for_update else statement)
    if user is None:
        raise api_error(404, "USER_NOT_FOUND", f"User '{public_id}' not found")
    return user


def create_user(
    session: Session,
    payload: UserCreate,
    *,
    password: str | None = None,
    min_length: int = DEFAULT_MIN_LENGTH,
) -> User:
    """A person; with ``password`` (``create_admin``), checked against the rules first."""
    if password is not None:
        check_password(password, payload.username, min_length)

    def change() -> User:
        taken = session.scalar(
            select(User.id).where(func.lower(User.username) == payload.username.lower())
        )
        if taken is not None:
            raise _taken()
        user = User(
            username=payload.username,
            name=payload.name,
            email=payload.email,
            password_hash=hash_secret(password) if password is not None else None,
            active=True,
        )
        session.add(user)
        session.flush()
        return user

    return _changing(session, change)


def update_user(session: Session, public_id: str, payload: UserUpdate) -> User:
    def change() -> User:
        user = load_user(session, public_id, for_update=True)
        if user.version != payload.expectedVersion:
            raise api_error(
                409,
                "VERSION_CONFLICT",
                "User version has changed",
                {"currentVersion": user.version},
            )
        fields = payload.model_fields_set
        if "name" in fields and payload.name is not None:
            user.name = payload.name
        if "email" in fields:
            user.email = payload.email
        now = datetime.now(UTC)
        if "active" in fields and payload.active is not None:
            if user.active and not payload.active:
                sessions.end_all(session, user.id, "deactivated", now)
            user.active = payload.active
        user.version += 1
        user.updated_at = now
        return user

    return _changing(session, change)


def user_page(
    session: Session,
    *,
    q: str | None,
    active: bool | None,
    page: PageRequest,
    page_size: int,
) -> Page[User]:
    """People in the order they were created; ``q`` matches the username, name or e-mail."""
    statement = select(User)
    if q:
        pattern = f"%{q.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')}%"
        statement = statement.where(
            or_(User.username.ilike(pattern), User.name.ilike(pattern), User.email.ilike(pattern))
        )
    if active is not None:
        statement = statement.where(User.active.is_(active))
    return paginate_statement(
        session,
        statement,
        keys=_KEYS,
        scope="users",
        filters={"q": q, "active": active},
        page=page,
        page_size=page_size,
        message="User list cursor is invalid",
    )
