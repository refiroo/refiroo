"""Moving a provider identity onto the person who already had a local account (Product 0.12 I4a,
D377, D378).

A provider sign-in makes a new person when no identity matches (D363); the matching by e-mail that
would join them to the person the sign-in belongs to is the takeover I3 refused. An administrator
joins them afterwards: the new person's identities and provider-group memberships move onto the
person they name and the new person is deactivated, their sessions ended and their history left
under their name (D237). Refused when the person moved from has a password, direct grants or local
groups (``PERSON_HAS_ACCESS``): those are a real person's, removed deliberately first. An identity
unlinked makes the next sign-in with that provider a new person again.
"""

from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy import delete, exists, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ...errors import ApiError, api_error
from ...models.commands import IdentityLink
from ...models.database import (
    Grant,
    SignInProvider,
    User,
    UserGroup,
    UserGroupMember,
    UserIdentity,
)
from ..authorization.administration import refuse_last_administrator, security_administrators
from . import security_events, sessions
from .users import load_user


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
    return api_error(
        409, "IDENTITY_PROVIDER_TAKEN", "This person already signs in with that provider"
    )


def _held_access(session: Session, source: User) -> list[str]:
    """What makes the person a real person's: ``password``, ``grants``, ``local groups``."""
    held = []
    if source.password_hash is not None:
        held.append("a password")
    if session.scalar(select(exists().where(Grant.user_id == source.id))):
        held.append("direct roles")
    if session.scalar(
        select(
            exists()
            .where(UserGroupMember.user_id == source.id)
            .where(UserGroupMember.group_id == UserGroup.id)
            .where(UserGroup.provider_id.is_(None))
        )
    ):
        held.append("local groups")
    return held


def link(session: Session, public_id: str, payload: IdentityLink) -> User:
    """Move the provider identities and provider-group memberships of ``fromUserId`` onto this
    person; the other person is deactivated. Commits."""

    def change() -> User:
        if payload.fromUserId == public_id:
            raise api_error(422, "LINK_SAME_PERSON", "A person cannot be linked to themselves")
        # Both rows locked in one order, so two links the opposite way round cannot deadlock.
        session.execute(
            select(User.id)
            .where(User.public_id.in_([public_id, payload.fromUserId]))
            .order_by(User.id)
            .with_for_update()
        )
        target = load_user(session, public_id, for_update=True)
        if not target.active:
            raise api_error(
                409,
                "LINK_TARGET_DEACTIVATED",
                f"{target.name} is deactivated; activate them first, so they can sign in",
            )
        if target.version != payload.expectedVersion:
            raise api_error(
                409,
                "VERSION_CONFLICT",
                "User version has changed",
                {"currentVersion": target.version},
            )
        source = load_user(session, payload.fromUserId, for_update=True)
        held = _held_access(session, source)
        if held:
            raise api_error(
                409,
                "PERSON_HAS_ACCESS",
                f"{source.name} has {', '.join(held)} of their own; remove them first, or link "
                "the other way",
                {"held": held},
            )
        moved = list(
            session.execute(
                select(UserIdentity.id, SignInProvider.key)
                .join(SignInProvider, SignInProvider.id == UserIdentity.provider_id)
                .where(UserIdentity.user_id == source.id)
                .order_by(UserIdentity.id)
            )
        )
        if not moved:
            raise api_error(
                409, "NO_IDENTITY_TO_LINK", f"{source.name} has no provider identity to move"
            )
        taken = session.scalar(
            select(exists().where(UserIdentity.user_id == target.id).where(
                UserIdentity.provider_id.in_(
                    select(UserIdentity.provider_id).where(UserIdentity.user_id == source.id)
                )
            ))
        )  # fmt: skip
        if taken:
            raise _taken()
        now = datetime.now(UTC)
        before = security_administrators(session)
        session.execute(
            update(UserIdentity).where(UserIdentity.user_id == source.id).values(user_id=target.id)
        )
        groups = list(
            session.scalars(
                select(UserGroupMember.group_id).where(UserGroupMember.user_id == source.id)
            )
        )
        session.execute(
            update(UserGroupMember)
            .where(UserGroupMember.user_id == source.id)
            .values(user_id=target.id)
        )
        sessions.end_all(session, source.id, "deactivated", now)
        source.active = False
        source.version += 1
        source.updated_at = now
        target.version += 1
        target.updated_at = now
        session.flush()
        refuse_last_administrator(session, before)
        security_events.record(
            session, "user", target.public_id, "identity-linked",
            about=[target.public_id, source.public_id], version=target.version,
            details={"fromUserId": source.public_id, "fromUsername": source.username,
                     "providers": [key for _, key in moved], "groups": len(groups)},
        )  # fmt: skip
        security_events.record(
            session, "user", source.public_id, "updated", about=[source.public_id],
            version=source.version,
            details=security_events.changed(["active"], name=source.name, active=False),
        )  # fmt: skip
        return target

    return _changing(session, change)


def unlink(session: Session, public_id: str, provider_key: str) -> User:
    """Remove the person's identity at a provider, with their memberships in its groups and the
    sessions it started; their next sign-in with it makes a new person. Commits."""

    def change() -> User:
        user = load_user(session, public_id, for_update=True)
        row = session.execute(
            select(UserIdentity, SignInProvider)
            .join(SignInProvider, SignInProvider.id == UserIdentity.provider_id)
            .where(UserIdentity.user_id == user.id, SignInProvider.key == provider_key)
        ).one_or_none()
        if row is None:
            raise api_error(
                404,
                "IDENTITY_NOT_FOUND",
                f"{user.name} has no sign-in with the provider '{provider_key}'",
            )
        identity, provider = row
        now = datetime.now(UTC)
        session.execute(delete(UserIdentity).where(UserIdentity.id == identity.id))
        session.execute(
            delete(UserGroupMember).where(
                UserGroupMember.user_id == user.id,
                UserGroupMember.group_id.in_(
                    select(UserGroup.id).where(UserGroup.provider_id == provider.id)
                ),
            )
        )
        sessions.end_provider_sessions(session, user.id, provider.key, now)
        user.version += 1
        user.updated_at = now
        security_events.record(
            session, "user", user.public_id, "identity-unlinked", about=[user.public_id],
            version=user.version,
            details={"provider": provider.key, "subject": identity.subject},
        )  # fmt: skip
        return user

    return _changing(session, change)
