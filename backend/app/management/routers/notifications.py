"""The caller's inbox (Product 0.12 A2, D233): notices of requests waiting for their approval,
decisions on their requests and jobs they started that finished. For anyone signed in, a client
included; the live stream is read with ``fetch`` and the ``Authorization`` header (D247)."""

import time
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import select

from ...common.pagination import paginate_statement, text_key
from ...engine.authorization.visibility import in_workspaces
from ...engine.identity.principals import Ref
from ...engine.notifications import following, inbox
from ...errors import api_error
from ...models.database import Workspace, WorkspaceFollower
from .. import sse
from ..access import SIGNED_IN, AuthorizedRoute, CurrentPermissions, requires
from ..dependencies import CurrentPrincipal, DbSession
from ..paging import PageQuery, PageSize
from ..projections import notifications as present
from ..schemas.notifications import (
    FollowedWorkspacePage,
    FollowedWorkspaceResponse,
    NotificationPage,
    NotificationResponse,
    NotificationsRead,
    NotificationsReadResult,
    NotificationsRemoval,
    NotificationsRemovalResult,
)

router = APIRouter(route_class=AuthorizedRoute, prefix="/api/v1", tags=["notifications"])

# How long a sent notice is remembered, and how far back a read looks for one that committed late.
RECENT_SECONDS = 60.0


def _owner(principal: CurrentPrincipal) -> Ref:
    return (principal.kind, principal.row_id)


@router.get("/me/notifications", response_model=NotificationPage)
@requires("signed-in", at=SIGNED_IN)
def list_my_notifications(
    principal: CurrentPrincipal,
    session: DbSession,
    paging: PageQuery,
    unread: bool | None = Query(
        default=None, description="true: only unread notices; false: only read ones"
    ),
    q: str | None = Query(
        default=None,
        max_length=200,
        description="Words a person sees in the notice: its kind, the change set's name, the "
        "comment, who acted, the job's kind (0.12 NT1)",
    ),
    kind: str | None = Query(default=None, max_length=40, description="Only notices of this kind"),
    workspace: str | None = Query(
        default=None, max_length=160, description="Only notices of this workspace"
    ),
    sort: Literal["newest", "oldest"] = Query(default="newest"),
    page_size: int = PageSize(50, 500),
) -> NotificationPage:
    """The caller's notices, newest (or oldest) first, with the count of all their unread ones."""
    page = inbox.notification_page(
        session,
        _owner(principal),
        unread=unread,
        page=paging,
        page_size=page_size,
        search=q,
        kind=kind,
        workspace_key=workspace,
        sort=sort,
    )
    return present.notification_page(page, inbox.unread_count(session, _owner(principal)))


@router.post("/me/notifications/read", response_model=NotificationsReadResult)
@requires("signed-in", at=SIGNED_IN)
def mark_my_notifications_read(
    payload: NotificationsRead, principal: CurrentPrincipal, session: DbSession
) -> NotificationsReadResult:
    """Mark notices read (or unread), by ID, by what they are about, or all of them; idempotent."""
    marked = inbox.mark_read(
        session,
        _owner(principal),
        payload.ids,
        subject_id=payload.subjectId,
        read=payload.read,
    )
    return NotificationsReadResult(
        marked=marked, unreadCount=inbox.unread_count(session, _owner(principal))
    )


@router.post("/me/notifications/removal", response_model=NotificationsRemovalResult)
@requires("signed-in", at=SIGNED_IN)
def remove_my_notifications(
    payload: NotificationsRemoval, principal: CurrentPrincipal, session: DbSession
) -> NotificationsRemovalResult:
    """Delete notices for good, by ID or every read one (0.12 NT1, D461); what they were about
    stays. A notice is removed only by its owner."""
    removed = inbox.remove(session, _owner(principal), payload.ids)
    return NotificationsRemovalResult(
        removed=removed, unreadCount=inbox.unread_count(session, _owner(principal))
    )


def _follower(principal: CurrentPrincipal) -> int:
    if principal.kind != "user":
        raise api_error(403, "NOT_A_PERSON", "Only a signed-in person can follow a workspace")
    return principal.row_id


def _followed(session: DbSession, user_id: int, key: str) -> FollowedWorkspaceResponse:
    row = session.execute(
        select(WorkspaceFollower.created_at, Workspace.label)
        .join(Workspace, Workspace.key == WorkspaceFollower.workspace_key)
        .where(WorkspaceFollower.user_id == user_id, WorkspaceFollower.workspace_key == key)
    ).one()
    return FollowedWorkspaceResponse(workspaceKey=key, label=row.label, since=row.created_at)


def _browsable(session: DbSession, permissions: CurrentPermissions, key: str) -> None:
    """`404 NOT_FOUND` unless the workspace is active and the caller may browse it."""
    active = session.scalar(
        select(Workspace.key).where(Workspace.key == key, Workspace.status == "active")
    )
    if active is None or not permissions.allows("browse", key):
        raise api_error(404, "NOT_FOUND", "There is no such workspace you may browse")


@router.get("/me/followed-workspaces", response_model=FollowedWorkspacePage)
@requires("signed-in", at=SIGNED_IN)
def list_followed_workspaces(
    principal: CurrentPrincipal,
    session: DbSession,
    permissions: CurrentPermissions,
    paging: PageQuery,
    page_size: int = PageSize(100, 500),
) -> FollowedWorkspacePage:
    """The workspaces the caller follows and still may browse, by label (0.16 AO3, AO-D38). A client
    has none."""
    statement = (
        select(Workspace)
        .join(WorkspaceFollower, WorkspaceFollower.workspace_key == Workspace.key)
        .where(
            WorkspaceFollower.user_id == (principal.row_id if principal.kind == "user" else -1),
            Workspace.status == "active",
        )
    )
    visible = in_workspaces(Workspace.key, permissions, frozenset({"browse"}))
    if visible is not None:
        statement = statement.where(visible)
    page = paginate_statement(
        session,
        statement,
        keys=(text_key("label", Workspace.label, "label"), text_key("key", Workspace.key, "key")),
        scope="followed-workspaces",
        filters={},
        page=paging,
        page_size=page_size,
        message="Followed workspace cursor is invalid",
    )
    since = dict(
        session.execute(
            select(WorkspaceFollower.workspace_key, WorkspaceFollower.created_at).where(
                WorkspaceFollower.user_id == (principal.row_id if principal.kind == "user" else -1),
                WorkspaceFollower.workspace_key.in_([item.key for item in page.items]),
            )
        ).all()
    )
    return FollowedWorkspacePage(
        items=[
            FollowedWorkspaceResponse(
                workspaceKey=item.key, label=item.label, since=since[item.key]
            )
            for item in page.items
        ],
        **page.links(),
    )


@router.put("/me/followed-workspaces/{workspace_key}", response_model=FollowedWorkspaceResponse)
@requires("signed-in", at=SIGNED_IN)
def follow_workspace(
    workspace_key: str,
    principal: CurrentPrincipal,
    session: DbSession,
    permissions: CurrentPermissions,
) -> FollowedWorkspaceResponse:
    """Follow a workspace: a notice arrives in the caller's inbox when a change set is published
    there (0.16 AO3, AO-D38). `404 NOT_FOUND` for a workspace the caller may not browse, `403
    NOT_A_PERSON` for a client; repeating is harmless."""
    user_id = _follower(principal)
    _browsable(session, permissions, workspace_key)
    following.follow(session, user_id, workspace_key)
    return _followed(session, user_id, workspace_key)


@router.delete("/me/followed-workspaces/{workspace_key}", status_code=204)
@requires("signed-in", at=SIGNED_IN)
def unfollow_workspace(
    workspace_key: str,
    principal: CurrentPrincipal,
    session: DbSession,
    permissions: CurrentPermissions,
) -> Response:
    """Stop following a workspace; harmless when the caller did not. `404 NOT_FOUND` for a workspace
    that does not exist."""
    user_id = _follower(principal)
    if session.scalar(select(Workspace.key).where(Workspace.key == workspace_key)) is None:
        raise api_error(404, "NOT_FOUND", "There is no such workspace")
    following.unfollow(session, user_id, workspace_key)
    return Response(status_code=204)


@router.get(
    "/me/notifications/events",
    response_class=StreamingResponse,
    responses={
        200: {
            "description": "Server-sent events: `event: unread` with `{unreadCount}` at once and "
            "whenever the count changes, and `event: notification` with the notice (as the list "
            "answers it) for each new one; it ends when the client closes it",
            "content": {"text/event-stream": {}},
        }
    },
)
@requires("signed-in", at=SIGNED_IN)
async def my_notification_events(
    request: Request, principal: CurrentPrincipal
) -> StreamingResponse:
    """Follow the caller's inbox: the unread count at once, then each new notice as it is made and
    the count after every change. Nothing is polled: the database tells the engine of each notice
    (like the job stream, D58). A comment line every 15 s keeps an idle stream open."""
    owner = _owner(principal)
    connected = datetime.now(UTC)
    subscription, (seen, count) = await sse.subscribe(
        request, inbox.principal_key(owner), _position, owner
    )

    # The notices sent, by when: a notice made by a transaction that commits late has a lower ID
    # than one already sent, so each read also lists the notices of the last minute and drops the
    # ones it sent (the ID alone would skip it).
    sent: dict[int, float] = {}

    async def stream() -> AsyncIterator[str]:
        nonlocal seen, count, sent
        yield sse.frame("unread", {"unreadCount": count})
        while True:
            if not await sse.woken(subscription):
                yield sse.KEEP_ALIVE
                continue
            while True:
                clock = time.monotonic()
                sent = {key: at for key, at in sent.items() if clock - at < RECENT_SECONDS}
                fetched, current = await run_in_threadpool(
                    _changes,
                    request,
                    owner,
                    seen,
                    max(connected, datetime.now(UTC) - timedelta(seconds=RECENT_SECONDS)),
                    frozenset(sent),
                )
                new = [notice for notice in fetched if notice["sequenceId"] not in sent]
                for notice in new:
                    seen = max(seen, notice["sequenceId"])
                    sent[notice["sequenceId"]] = clock
                    yield sse.frame("notification", notice["body"])
                if new or current != count:
                    count = current
                    yield sse.frame("unread", {"unreadCount": count})
                # A full read may have left notices behind: read on until one comes back short.
                if not new or len(fetched) < inbox.CATCH_UP_LIMIT:
                    break

    return sse.respond(request, subscription, stream())


@router.get("/me/notifications/{notification_id}", response_model=NotificationResponse)
@requires("signed-in", at=SIGNED_IN)
def get_my_notification(
    notification_id: str, principal: CurrentPrincipal, session: DbSession
) -> NotificationResponse:
    """One of the caller's notices by ID: where a digest's link leads (0.16 AO3). `404 NOT_FOUND`
    for an unknown notice or another's."""
    found = inbox.find(session, _owner(principal), notification_id)
    if found is None:
        raise api_error(404, "NOT_FOUND", "There is no such notification")
    return present.notification_response(found)


def _position(request: Request, owner: Ref) -> tuple[int, int]:
    """The newest notice's sequence ID and the unread count: where the stream begins."""
    with request.app.state.session_factory() as session:
        return inbox.newest_id(session, owner), inbox.unread_count(session, owner)


def _changes(
    request: Request, owner: Ref, seen: int, recent_since: datetime, known: frozenset[int]
) -> tuple[list[dict], int]:
    """The notices after ``seen`` and those created since ``recent_since`` (each with its sequence
    ID) and the unread count now. A stream
    outlives any one request session, so each read opens a short session of its own."""
    with request.app.state.session_factory() as session:
        new = [
            {
                "sequenceId": item.sequence_id,
                "body": present.notification_response(item).model_dump(mode="json"),
            }
            for item in inbox.after(session, owner, seen, recent_since=recent_since, known=known)
        ]
        return new, inbox.unread_count(session, owner)
