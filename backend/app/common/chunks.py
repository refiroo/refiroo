"""Lists of at most ``CHUNK_SIZE`` items, so one statement never binds more IDs than PostgreSQL's
65,535 parameters allow (0.11 X5)."""

from collections.abc import Iterable, Iterator
from itertools import islice

# IDs bound into one statement.
CHUNK_SIZE = 500


def chunks[T](items: Iterable[T], size: int = CHUNK_SIZE) -> Iterator[list[T]]:
    """``items`` in lists of ``size``, in the order given: a caller that needs an order sorts first."""
    iterator = iter(items)
    while chunk := list(islice(iterator, size)):
        yield chunk
