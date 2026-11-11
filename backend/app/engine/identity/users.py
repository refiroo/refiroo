"""People: created, changed, deactivated and listed; never deleted (Product 0.12 I1, D237)."""

from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ...common.pagination import Page, PageRequest, integer_key, paginate_statement
from ...errors import ApiError, api_error
from ...models.commands import UserCreate, UserUpdate
from ...models.database import PasswordResetLink, User
from ..authorization.administration import (
    grant_roles,
    refuse_last_administrator,
    security_administrators,
)
from . import providers, security_events, sessions
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
    return api_error(409, "EMAIL_TAKEN", "Another person has this e-mail address")


def _refuse_taken_email(session: Session, email: str, *, except_id: int | None = None) -> None:
    statement = select(User.id).where(func.lower(User.email) == email.lower())
    if except_id is not None:
        statement = statement.where(User.id != except_id)
    if session.scalar(statement) is not None:
        raise _taken()


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
    roles: tuple[str, ...] = (),
    local_kept: bool = False,
) -> User:
    """A person; with ``password`` (``create_admin``), checked against the rules first; with
    ``roles``, holding them at the instance (the first administrator's, D282); with
    ``local_kept``, signing in with a password while local sign-in is off (I3, D365)."""
    if password is not None:
        check_password(password, payload.email, min_length)

    def change() -> User:
        _refuse_taken_email(session, payload.email)
        user = User(
            name=payload.name,
            email=payload.email,
            password_hash=hash_secret(password) if password is not None else None,
            active=True,
            local_kept=local_kept,
            sign_in_managed=payload.signInManaged,
        )
        session.add(user)
        session.flush()
        if roles:
            grant_roles(session, "user", user.id, roles)
        security_events.record(
            session, "user", user.public_id, "created", about=[user.public_id],
            details={
                "email": user.email, "name": user.name, "roles": list(roles),
                "signInManaged": user.sign_in_managed,
            },
        )  # fmt: skip
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
        will_be_active = payload.active if payload.active is not None else user.active
        will_have = payload.email if "email" in fields else user.email
        if will_be_active and will_have is None:
            raise api_error(
                422,
                "EMAIL_REQUIRED",
                "An active person needs an e-mail address: it is the name they sign in with",
            )
        if "email" in fields and payload.email is not None:
            _refuse_taken_email(session, payload.email, except_id=user.id)
        if "name" in fields and payload.name is not None:
            user.name = payload.name
        # A flush must never see an active person without an address: the address is set before a
        # person is restored or stays active, and cleared after one is deactivated.
        if "email" in fields and will_be_active:
            user.email = payload.email
        if "localKept" in fields and payload.localKept is not None:
            if not payload.localKept:
                providers.refuse_last_kept(session, user)
            user.local_kept = payload.localKept
        if "signInManaged" in fields and payload.signInManaged is not None:
            if payload.signInManaged and not user.sign_in_managed:
                # Links the person asked for stop working; an administrator's link stays.
                session.execute(
                    delete(PasswordResetLink).where(
                        PasswordResetLink.user_id == user.id,
                        PasswordResetLink.requested.is_(True),
                    )
                )
            user.sign_in_managed = payload.signInManaged
        now = datetime.now(UTC)
        if "active" in fields and payload.active is not None:
            if user.active and not payload.active:
                providers.refuse_last_kept(session, user)
                before = security_administrators(session)
                sessions.end_all(session, user.id, "deactivated", now)
                user.active = False
                session.flush()
                refuse_last_administrator(session, before)
            user.active = payload.active
        if "email" in fields and not will_be_active:
            user.email = payload.email
        user.version += 1
        user.updated_at = now
        changed = sorted(fields - {"expectedVersion"})
        security_events.record(
            session, "user", user.public_id, "updated", about=[user.public_id],
            version=user.version,
            details=security_events.changed(
                changed,
                name=user.name,
                active=user.active,
                localKept=user.local_kept,
                signInManaged=user.sign_in_managed,
            ),
        )  # fmt: skip
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
    """People in the order they were created; ``q`` matches the name or e-mail."""
    statement = select(User)
    if q:
        pattern = f"%{q.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')}%"
        statement = statement.where(or_(User.name.ilike(pattern), User.email.ilike(pattern)))
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
