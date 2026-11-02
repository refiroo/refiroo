"""Data and model changes across workspaces (Product 0.12 Z6, D340–D344)."""

from datetime import datetime

from fastapi import APIRouter, Query

from ...engine.reads import changes
from ...engine.reads.changes import ChangeKind
from ..access import SIGNED_IN, AuthorizedRoute, CurrentPermissions, requires
from ..dependencies import DbSession
from ..paging import PageQuery
from ..projections.changes import change_page
from ..schemas.changes import ChangePage

router = APIRouter(route_class=AuthorizedRoute, prefix="/api/v1", tags=["changes"])
_KIND = Query(default=None)
_SINCE = Query(default=None)
_UNTIL = Query(default=None)


@router.get("/changes", response_model=ChangePage)
@requires("changes.read", at=SIGNED_IN)
def list_changes(
    session: DbSession,
    permissions: CurrentPermissions,
    paging: PageQuery,
    actor_id: str | None = Query(default=None, alias="actorId", max_length=36),
    workspace_key: str | None = Query(default=None, alias="workspaceKey", max_length=160),
    kind: list[ChangeKind] | None = _KIND,
    since: datetime | None = _SINCE,
    until: datetime | None = _UNTIL,
    object_type_key: str | None = Query(default=None, alias="objectTypeKey", max_length=160),
    relation_type_key: str | None = Query(default=None, alias="relationTypeKey", max_length=160),
    cause_id: str | None = Query(default=None, alias="causeId", max_length=36),
    action: str | None = Query(default=None, max_length=80),
    attribute_key: str | None = Query(default=None, alias="attributeKey", max_length=160),
    live: bool = Query(default=False),
    page_size: int = Query(default=50, ge=1, le=500, alias="pageSize"),
) -> ChangePage:
    """Data and model changes newest first, each naming its workspace, its change set, what it
    changed as it is named now, its cause and who made it (D340, D343). ``actorId`` keeps those a
    person or client made; ``since`` is included and ``until`` is not (``from`` is the
    paging's, ADR-030). Always only what the caller
    may see: Browse in an entry's workspace, Model authoring at the instance for model
    administration (D342). Security events are at ``/security-events``.

    The list narrows, over the whole set, to what an account of history counted (0.16 AO2):
    ``objectTypeKey`` and ``relationTypeKey`` (the type of the record or relationship, as it stood
    when changed), ``causeId`` (the job or publication that made the change), ``action``
    (`created`, `updated`, `deleted`, `reclassified` or `moved`, an update that changed the
    record's parent), ``attributeKey`` (an update that changed that attribute) and ``live=true``,
    which keeps the changes that changed live data: a change set's staged entries, which a
    publication repeats, are left out."""
    return change_page(
        session,
        changes.change_page(
            session,
            permissions,
            actor_id=actor_id,
            workspace_key=workspace_key,
            kinds=kind or [],
            since=since,
            until=until,
            object_type_key=object_type_key,
            relation_type_key=relation_type_key,
            cause_id=cause_id,
            action=action,
            attribute_key=attribute_key,
            live=live,
            page=paging,
            page_size=page_size,
        ),
    )
