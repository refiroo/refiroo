"""A workspace's publications as a consumer API lists them (Base 0.9 C6a, C-D66).

A consumer that cannot call the management API finds here a snapshot to pin (``publication``) and
where to follow changes from after extracting it: ``eventSequence``, the feed position of the
publication's ``published`` entry (C-D15), ``null`` for a publication made before positions were
recorded (F1). Newest first, by the workspace's publication number, paged as every engine list is.
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...common.pagination import PageRequest, integer_key, paginate_statement
from ...common.time import as_utc
from ...models.database import Publication


def read_publications(session: Session, workspace_key: str, page: PageRequest, page_size: int) -> dict[str, Any]:
    """One page of the workspace's publications, each with ``id``, ``publishedAt``, ``eventSequence``
    and ``status`` (``active``: the one ``publication=latest`` reads; ``withdrawn``: superseded or
    taken back, still readable by its ID)."""
    found = paginate_statement(
        session,
        select(Publication).where(Publication.workspace_key == workspace_key),
        keys=(integer_key("number", Publication.publication_number, "publication_number", descending=True),),
        scope="consumer-publications",
        filters={"workspace": workspace_key},
        page=page,
        page_size=page_size,
    )
    return {
        "items": [
            {
                "id": item.id,
                "publishedAt": as_utc(item.published_at).isoformat(),
                "eventSequence": item.feed_position,
                "status": item.status,
            }
            for item in found.items
        ],
        "workspace": workspace_key,
        "pageSize": page_size,
        **found.links(),
    }
