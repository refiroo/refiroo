"""The inbox (Product 0.12 A2, D233)."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from .common import CollectionPage


class NotificationSubject(BaseModel):
    """What a notice is about: a change set or a job, by ID."""

    kind: Literal["change-set", "job"]
    id: str


class NotificationResponse(BaseModel):
    """A notice. ``kind`` is ``change-set.submitted`` (a request waiting for your approval),
    ``change-set.approved`` or ``change-set.sent-back`` (a decision on yours), or ``job.completed``,
    ``job.failed`` or ``job.awaiting-confirmation`` (a job you started). ``details`` holds what a
    client words it from: for a change set ``changeSetName``, ``version``, ``comment``, ``actor``
    (who submitted or decided: kind, id, name) and ``publicationId``; for a job ``jobKind`` and
    ``state``. A change set's name is as it was when the step happened."""

    id: str
    kind: str
    workspaceKey: str
    subject: NotificationSubject
    details: dict[str, Any]
    read: bool
    readAt: datetime | None
    createdAt: datetime


class NotificationPage(CollectionPage[NotificationResponse]):
    """The caller's notices, newest first (ADR-030). ``unreadCount`` counts every unread notice,
    whatever the page and filter."""

    unreadCount: int


class NotificationsRead(BaseModel):
    """Mark notices read, or unread with ``read`` false: those named in ``ids`` (another's or an
    unknown one is left alone), those about ``subjectId`` (a change set or job the caller opened),
    or ``all``."""

    ids: list[str] | None = Field(default=None, min_length=1, max_length=500)
    subjectId: str | None = Field(default=None, min_length=1, max_length=36)
    all: bool | None = None
    read: bool = Field(default=True, description="false marks the notices unread (0.12 NT1)")

    @model_validator(mode="after")
    def one_selection(self) -> NotificationsRead:
        given = [self.ids is not None, self.subjectId is not None, self.all is True]
        if sum(given) != 1:
            raise ValueError("Give one of 'ids', 'subjectId' or 'all': true")
        return self


class NotificationsReadResult(BaseModel):
    marked: int = Field(description="How many notices changed")
    unreadCount: int


class NotificationsRemoval(BaseModel):
    """Delete notices for good (0.12 NT1, D461): those named in ``ids`` (another's or an unknown
    one is left alone), or every read one with ``read`` true. What they were about stays."""

    ids: list[str] | None = Field(default=None, min_length=1, max_length=500)
    read: bool | None = None

    @model_validator(mode="after")
    def one_of_ids_or_read(self) -> NotificationsRemoval:
        if (self.ids is None) == (self.read is not True):
            raise ValueError("Give 'ids' or 'read': true")
        return self


class NotificationsRemovalResult(BaseModel):
    removed: int = Field(description="How many notices were deleted")
    unreadCount: int
