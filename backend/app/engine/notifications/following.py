"""Following a workspace (Product 0.16 AO3, AO-D38).

A person follows workspaces they may browse, off by default (``workspace_followers``). A change set
published in a followed workspace, from an approved request or directly, puts a ``change-set.published``
notice in the inbox of each follower who still holds Browse there, except the publisher, in the
publication's transaction: one ``INSERT … SELECT`` over the followers, however many they are. From
there it is a kind like the others (mailed at once, in the digest or not, AO-D33). Publications only,
not withdrawals; people only (a client has the webhooks and the change feed).
"""

from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, String, delete, func, insert, literal, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from ...models.database import ChangeSet, Notification, Publication, WorkspaceFollower
from ..authorization.administration import active_holders
from ..identity.principals import names, ref

PUBLISHED = "change-set.published"


def follow(session: Session, user_id: int, workspace_key: str) -> datetime:
    """The person follows the workspace, in the caller's transaction (it commits); since when. A
    repeat keeps the first time."""
    session.execute(
        pg_insert(WorkspaceFollower)
        .values(user_id=user_id, workspace_key=workspace_key, created_at=datetime.now(UTC))
        .on_conflict_do_nothing()
    )
    since = session.scalar(
        select(WorkspaceFollower.created_at).where(
            WorkspaceFollower.user_id == user_id, WorkspaceFollower.workspace_key == workspace_key
        )
    )
    session.commit()
    return since


def unfollow(session: Session, user_id: int, workspace_key: str) -> None:
    """The person stops following the workspace; harmless when they did not. Commits."""
    session.execute(
        delete(WorkspaceFollower).where(
            WorkspaceFollower.user_id == user_id, WorkspaceFollower.workspace_key == workspace_key
        )
    )
    session.commit()


def followed_among(session: Session, user_id: int, workspace_keys: Iterable[str]) -> set[str]:
    """Which of ``workspace_keys`` the person follows."""
    return set(
        session.scalars(
            select(WorkspaceFollower.workspace_key).where(
                WorkspaceFollower.user_id == user_id,
                WorkspaceFollower.workspace_key.in_(list(workspace_keys)),
            )
        )
    )


def announce_publication(session: Session, publication: Publication, change_set: ChangeSet) -> int:
    """Put a ``change-set.published`` notice in each follower's inbox, in the publication's
    transaction; how many. The followers are the active people who follow the workspace and still hold
    Browse there, but not the publisher. One statement, read and written in the database."""
    publisher = ref(publication.published_by_user_id, publication.published_by_client_id)
    details: dict[str, Any] = {
        "changeSetName": change_set.name,
        "version": change_set.version,
        "comment": None,
        "actor": names(session, [publisher]).get(publisher) if publisher is not None else None,
        "publicationId": publication.id,
    }
    followers = select(
        func.gen_random_uuid().cast(String),
        WorkspaceFollower.user_id,
        literal(PUBLISHED),
        literal(change_set.workspace_key),
        literal("change-set"),
        literal(change_set.id),
        literal(details, JSON),
        func.now(),
    ).where(
        WorkspaceFollower.workspace_key == change_set.workspace_key,
        WorkspaceFollower.user_id.in_(active_holders("browse", change_set.workspace_key)),
    )
    if publication.published_by_user_id is not None:
        followers = followers.where(WorkspaceFollower.user_id != publication.published_by_user_id)
    result = session.execute(
        insert(Notification).from_select(
            [
                "id",
                "user_id",
                "kind",
                "workspace_key",
                "subject_kind",
                "subject_id",
                "details",
                "created_at",
            ],
            followers,
        )
    )
    return result.rowcount
