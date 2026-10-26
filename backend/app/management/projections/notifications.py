"""The inbox as the API answers it (Product 0.12 A2)."""

from ...common.pagination import Page
from ...models.database import Notification
from ..schemas.notifications import NotificationPage, NotificationResponse, NotificationSubject


def notification_response(item: Notification) -> NotificationResponse:
    return NotificationResponse(
        id=item.id,
        kind=item.kind,
        workspaceKey=item.workspace_key,
        subject=NotificationSubject(kind=item.subject_kind, id=item.subject_id),
        details=item.details,
        read=item.read_at is not None,
        readAt=item.read_at,
        createdAt=item.created_at,
    )


def notification_page(page: Page[Notification], unread_count: int) -> NotificationPage:
    return NotificationPage(
        items=[notification_response(item) for item in page.items],
        unreadCount=unread_count,
        **page.links(),
    )
