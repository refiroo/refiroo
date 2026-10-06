"""The pull feed of a consumer API's events (Base 0.9 C10, CONSUMER_API "Pull feed").

A reader starts after a position (``after``: ``0``, or a publication's ``eventSequence``, C-D15)
and continues by ``cursor``, inside a position too, which a container rename can fill with
thousands of events (C-D91). Events never change, so a cursor is a lasting resume token. The read
answers up to the position events are derived to (``headPosition``); a position past the feed's
head is ``409 EVENT_POSITION_AHEAD``, one below the earliest still kept ``410 EVENTS_EXPIRED`` naming
the active publication to re-read (C-D92).

Every event of the consumer API is served, whatever contract version derived it, each naming its
own (C-D88). The definition's parameters filter as on a list, against live data at the read; the
type parameter against the type stored with the event; an event whose object no longer exists
passes every other parameter (C-D90). A filtered page scans at most ten pages of events and may
come back short or empty with the cursor advanced, as the raw feed's does (F4).

``payload=full`` carries each object as get by ID answers it with the read's parameters, composed
by get by ID's code under the contract version served and labelled ``stateAt``, the feed position
the read's snapshot holds; ``payload=identity`` leaves it out (C-D7 revised). ``code`` and ``name``
are read the same way, never stored (C-D89).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import exists, or_, select, tuple_
from sqlalchemy.orm import Session, aliased

from ...common.cursors import encode_cursor
from ...common.time import as_utc
from ...errors import api_error
from ...models.database import ConsumerEvent, ConsumerEventCheckpoint, RdmObject, Workspace
from ...models.schema import ConsumerApiDefinition, EngineModel, ObjectTypeParameter
from .consumer_objects import ConsumerObjects
from .consumer_parameters import consumer_filter
from .consumer_source import ConsumerSource
from .feed import SCAN_PAGES, retention_floor

SCOPE = "consumer-events"
SORT = ("position", "ordinal")
# An ordinal after every event of a position: ``after=p`` starts at the next position.
AFTER_POSITION = 2**31 - 1
FULL, IDENTITY = "full", "identity"
# The page sizes each payload allows and its default (C-D91 amended): whole objects page as lists do.
PAGE_SIZES = {FULL: (100, 100), IDENTITY: (1000, 500)}


@dataclass(frozen=True)
class EventsRequest:
    """What a read asks: where to start (a position, or a cursor's key), how much, in which shape,
    and which events and definition parameters narrow it."""

    start: tuple[int, int]
    page_size: int
    payload: str
    event_keys: tuple[str, ...]
    parameters: Mapping[str, Sequence[str]]


def cursor_filters(event_keys: Sequence[str], parameters: Mapping[str, Sequence[str]]) -> dict[str, Any]:
    """What a cursor binds: the events and parameters it pages, not the payload or page size."""
    return {
        "events": sorted(event_keys),
        "parameters": {name: sorted(values) for name, values in sorted(parameters.items())},
    }


def cursor_scope(definition: ConsumerApiDefinition, workspace_key: str) -> str:
    return f"{SCOPE}:{definition.key}:{workspace_key}"


def derived_head(session: Session, workspace_key: str) -> tuple[int, int]:
    """How far the workspace's events are derived, and where derivation began (C-D92); a
    workspace the deriver has not seen yet is at 0."""
    row = session.execute(
        select(ConsumerEventCheckpoint.position, ConsumerEventCheckpoint.start_position).where(
            ConsumerEventCheckpoint.workspace_key == workspace_key
        )
    ).one_or_none()
    return (0, 0) if row is None else (row.position, row.start_position)


@dataclass(frozen=True)
class EventWindow:
    """What a workspace's events cover: derived up to ``head``, kept from ``earliest`` on, with the
    feed's head and the publication a reader re-syncs from once a position expired (C-D92)."""

    head: int
    earliest: int
    feed_head: int
    publication_id: str | None
    publication_position: int | None

    @property
    def publication(self) -> dict[str, Any] | None:
        if self.publication_id is None:
            return None
        return {"id": self.publication_id, "eventSequence": self.publication_position}


def event_window(session: Session, workspace_key: str, retention_days: int) -> EventWindow:
    head, start_position = derived_head(session, workspace_key)
    floor = retention_floor(session, workspace_key, retention_days)
    return EventWindow(
        head=head,
        earliest=max(floor.earliest_position, start_position + 1),
        feed_head=floor.head_position,
        publication_id=floor.publication_id,
        publication_position=floor.publication_position,
    )


def check_after(window: EventWindow, position: int, pointer: str | None = None) -> None:
    """Refuse a position to read or deliver after: past the feed's head ``409
    EVENT_POSITION_AHEAD``, below the earliest kept ``410 EVENTS_EXPIRED`` naming the publication to
    re-sync from. ``pointer`` names the request field that gave it, for a body (C11)."""
    at = {} if pointer is None else {"pointer": pointer}
    if position > window.feed_head:
        raise api_error(
            409,
            "EVENT_POSITION_AHEAD",
            f"Position {position} is past the feed's head, {window.feed_head}: it was not read from "
            "this workspace's events, or the database was restored to an earlier state. Read again "
            "from a publication",
            {"headPosition": window.feed_head, **at},
        )
    if position < window.earliest - 1:
        raise api_error(
            410,
            "EVENTS_EXPIRED",
            f"Position {position} has expired: events are kept from position {window.earliest} on. Read "
            "the publication named in the details, then follow the events from its eventSequence",
            {
                "earliestPosition": window.earliest,
                "headPosition": window.head,
                "publication": window.publication,
                **at,
            },
        )


def event_filters(
    session: Session,
    model: EngineModel,
    definition: ConsumerApiDefinition,
    workspace_key: str,
    event_keys: Sequence[str],
    parameters: Mapping[str, Sequence[str]],
) -> tuple[list[Any], Any]:
    """The conditions on ``ConsumerEvent`` that narrow a read to ``event_keys`` and the definition's
    ``parameters`` (C-D90), and the filter that narrows each composed object's projections."""
    event = ConsumerEvent
    source = ConsumerSource(workspace_key)
    narrowed = consumer_filter(session, model, definition, source, parameters)
    typed = {
        name: values
        for name, values in parameters.items()
        if isinstance(definition.parameters[name], ObjectTypeParameter)
    }
    others = {name: values for name, values in parameters.items() if name not in typed}
    filters = []
    if event_keys:
        filters.append(event.event_key.in_(event_keys))
    if typed:
        filters += consumer_filter(session, model, definition, source, typed).on(event)
    rest = consumer_filter(session, model, definition, source, others).on if others else None
    if rest is not None:
        live, matching = aliased(RdmObject), aliased(RdmObject)
        exists_live = exists().where(live.id == event.object_id, live.workspace_key == workspace_key)
        exists_matching = exists().where(
            matching.id == event.object_id, matching.workspace_key == workspace_key, *rest(matching)
        )
        filters.append(or_(~exists_live, exists_matching))
    return filters, narrowed


@dataclass(frozen=True)
class EventPage:
    """A page of events: its items as the pull feed answers them, the key it read through (the last
    item's, or further when a narrowed read scanned past events it left out), and whether every
    event derived so far is read."""

    items: list[dict[str, Any]]
    keys: list[tuple[int, int]]
    last: tuple[int, int]
    caught_up: bool
    window: EventWindow


def event_page(
    session: Session,
    model: EngineModel,
    definition: ConsumerApiDefinition,
    workspace: Workspace,
    request: EventsRequest,
    *,
    retention_days: int,
    through: tuple[int, int] | None = None,
) -> EventPage:
    """One page of the consumer API's events in the workspace after ``request.start``, and no further
    than ``through`` when given (a webhook batch read again, C12)."""
    window = event_window(session, workspace.key, retention_days)
    head = window.head
    position, ordinal = request.start
    check_after(window, position)

    event = ConsumerEvent
    after = tuple_(event.position, event.ordinal) > tuple_(position, ordinal)
    scope = [event.workspace_key == workspace.key, event.consumer_api == definition.key, event.position <= head]
    ceiling = (head, AFTER_POSITION)
    if through is not None:
        scope.append(tuple_(event.position, event.ordinal) <= tuple_(*through))
        ceiling = min(ceiling, through)
    filters, narrowed = event_filters(
        session, model, definition, workspace.key, request.event_keys, request.parameters
    )

    bound = []
    end: tuple[int, int] | None = None
    if filters:
        found = session.execute(
            select(event.position, event.ordinal)
            .where(*scope, after)
            .order_by(event.position, event.ordinal)
            .offset(SCAN_PAGES * request.page_size - 1)
            .limit(1)
        ).one_or_none()
        if found is not None:
            end = (found.position, found.ordinal)
            bound.append(tuple_(event.position, event.ordinal) <= end)
    rows = session.scalars(
        select(event).where(*scope, after, *filters, *bound).order_by(event.position, event.ordinal).limit(request.page_size)
    ).all()
    if len(rows) == request.page_size:
        last = (rows[-1].position, rows[-1].ordinal)
    elif end is not None:
        last = end
    else:
        last = max((position, ordinal), ceiling)
    caught_up = not session.scalar(
        select(exists().where(*scope, tuple_(event.position, event.ordinal) > tuple_(*last)))
    )
    source = ConsumerSource(workspace.key)
    return EventPage(
        items=_items(session, model, definition, source, rows, request, narrowed, workspace.feed_position),
        keys=[(row.position, row.ordinal) for row in rows],
        last=last,
        caught_up=caught_up,
        window=window,
    )


def read_consumer_events(
    session: Session,
    model: EngineModel,
    definition: ConsumerApiDefinition,
    workspace: Workspace,
    request: EventsRequest,
    *,
    retention_days: int,
) -> dict[str, Any]:
    """One page of the consumer API's events in the workspace."""
    page = event_page(session, model, definition, workspace, request, retention_days=retention_days)
    return {
        "items": page.items,
        "workspace": workspace.key,
        "pageSize": request.page_size,
        "cursor": encode_cursor(
            (str(page.last[0]), str(page.last[1])),
            scope=cursor_scope(definition, workspace.key),
            sort=SORT,
            filters=cursor_filters(request.event_keys, request.parameters),
        ),
        "caughtUp": page.caught_up,
        "headPosition": page.window.head,
        "earliestPosition": page.window.earliest,
    }


def _items(
    session: Session,
    model: EngineModel,
    definition: ConsumerApiDefinition,
    source: ConsumerSource,
    rows: Sequence[ConsumerEvent],
    request: EventsRequest,
    narrowed: Any,
    state_at: int,
) -> list[dict[str, Any]]:
    """The page's events, each with its object's identity and, with the full payload, the object."""
    if not rows:
        return []
    objects = ConsumerObjects(model, definition)
    ids = list(dict.fromkeys(row.object_id for row in rows))
    identities = objects.identities(session, source, ids)
    composed = objects.compose(session, source, ids, narrowed) if request.payload == FULL else {}
    items = []
    for row in rows:
        gone = row.change == "deleted"
        code, name = (None, None) if gone else identities.get(row.object_id, (None, None))
        item: dict[str, Any] = {
            "eventId": row.event_id,
            "position": row.position,
            "occurredAt": as_utc(row.occurred_at),
            "event": row.event_key,
            "change": row.change,
            "contractVersion": row.contract_version,
            "objectType": row.object_type,
            "id": row.object_id,
            "code": code,
            "name": name,
            "changed": list(row.changed),
            "cause": {"kind": row.cause_kind or "user", **({"id": row.cause_id} if row.cause_id else {})},
        }
        if not gone and row.object_id in composed:
            item["stateAt"] = state_at
            item["object"] = composed[row.object_id]
        items.append(item)
    return items
