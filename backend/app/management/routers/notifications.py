"""The caller's inbox (Product 0.12 A2, D233): notices of requests waiting for their approval,
decisions on their requests and jobs they started that finished. For anyone signed in, a client
included; the live stream is read with ``fetch`` and the ``Authorization`` header (D247)."""

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Literal

from fastapi import APIRouter, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse

from ...engine.identity.principals import Ref
from ...engine.jobs.events import JobListener
from ...engine.notifications import inbox
from ..access import SIGNED_IN, AuthorizedRoute, requires
from ..dependencies import CurrentPrincipal, DbSession
from ..paging import PageQuery
from ..projections import notifications as present
from ..schemas.notifications import (
    NotificationPage,
    NotificationsRead,
    NotificationsReadResult,
    NotificationsRemoval,
    NotificationsRemovalResult,
)

router = APIRouter(route_class=AuthorizedRoute, prefix="/api/v1", tags=["notifications"])

# A stream sends a comment this often while nothing changes, so proxies keep it open.
KEEP_ALIVE_SECONDS = 15.0


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
    page_size: int = Query(default=50, ge=1, le=500, alias="pageSize"),
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
    listener: JobListener = request.app.state.job_listener
    subscription = listener.subscribe(inbox.principal_key(owner))
    try:
        seen, count = await run_in_threadpool(_position, request, owner)
    except BaseException:
        listener.unsubscribe(subscription)
        raise

    async def stream() -> AsyncIterator[str]:
        nonlocal seen, count
        try:
            yield _event("unread", {"unreadCount": count})
            while True:
                try:
                    await asyncio.wait_for(subscription.woken.wait(), KEEP_ALIVE_SECONDS)
                except TimeoutError:
                    yield ": keep-alive\n\n"
                    continue
                subscription.woken.clear()
                while True:
                    new, current = await run_in_threadpool(_changes, request, owner, seen)
                    for notice in new:
                        seen = max(seen, notice["sequenceId"])
                        yield _event("notification", notice["body"])
                    if new or current != count:
                        count = current
                        yield _event("unread", {"unreadCount": count})
                    # A full read may have left notices behind: read on until one comes back short.
                    if len(new) < inbox.CATCH_UP_LIMIT:
                        break
        finally:
            listener.unsubscribe(subscription)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _position(request: Request, owner: Ref) -> tuple[int, int]:
    """The newest notice's sequence ID and the unread count: where the stream begins."""
    with request.app.state.session_factory() as session:
        return inbox.newest_id(session, owner), inbox.unread_count(session, owner)


def _changes(request: Request, owner: Ref, seen: int) -> tuple[list[dict], int]:
    """The notices after ``seen`` (each with its sequence ID) and the unread count now. A stream
    outlives any one request session, so each read opens a short session of its own."""
    with request.app.state.session_factory() as session:
        new = [
            {
                "sequenceId": item.sequence_id,
                "body": present.notification_response(item).model_dump(mode="json"),
            }
            for item in inbox.after(session, owner, seen)
        ]
        return new, inbox.unread_count(session, owner)


def _event(name: str, body: dict) -> str:
    return f"event: {name}\ndata: {json.dumps(body, separators=(',', ':'))}\n\n"
