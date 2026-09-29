"""Query parameters that select a page of any collection (ADR-030).

``PageQuery`` serves every collection; ``SeekablePageQuery`` adds ``seek`` for the lists that
support it (objects, relations and mapping coverage).
"""

from typing import Annotated, Literal

from fastapi import Depends, Query

from ..common.pagination import PageRequest

_CURSOR = Query(
    default=None,
    description="Opaque cursor from nextCursor, prevCursor or anchor; pass it back unchanged",
)
_FROM = Query(
    default="start",
    alias="from",
    description="Without a cursor, read the first page (start) or the last page (end)",
)
_POSITION = Query(
    default=None,
    ge=0,
    description=(
        "Read the page starting at this zero-based row of the filtered, sorted list. Position reads"
        " can repeat or miss a row when data changes between requests; read whole lists with cursors"
    ),
)
_INCLUDE_TOTAL = Query(
    default=False,
    alias="includeTotal",
    description="Add totalCount and startIndex, counted under the same filters",
)


def _page(
    cursor: str | None = _CURSOR,
    from_: Literal["start", "end"] = _FROM,
    position: int | None = _POSITION,
    include_total: bool = _INCLUDE_TOTAL,
) -> PageRequest:
    return PageRequest(
        cursor=cursor,
        position=position,
        from_end=from_ == "end",
        include_total=include_total,
    )


def _seekable_page(
    cursor: str | None = _CURSOR,
    from_: Literal["start", "end"] = _FROM,
    position: int | None = _POSITION,
    include_total: bool = _INCLUDE_TOTAL,
    seek: str | None = Query(
        default=None,
        description=(
            "Start at the first row whose sort value is at or after this value (at or before it"
            " for a descending sort)"
        ),
    ),
) -> PageRequest:
    return PageRequest(
        cursor=cursor,
        position=position,
        seek=seek,
        from_end=from_ == "end",
        include_total=include_total,
    )


PageQuery = Annotated[PageRequest, Depends(_page)]
SeekablePageQuery = Annotated[PageRequest, Depends(_seekable_page)]
