"""A count with its noun, as the engine's sentences write it."""


def count_noun(count: int, one: str, many: str | None = None, *, thousands: bool = False) -> str:
    """``count`` and its noun: ``1 row``, ``2 rows``. ``many`` is the plural where it is not
    ``one`` and an ``s`` (``person``, ``people``). The count is written as it is; ``thousands``
    groups it (``1,286 rows``), as the assistant's and the digest's lines do."""
    noun = one if count == 1 else (many if many is not None else f"{one}s")
    return f"{count:,} {noun}" if thousands else f"{count} {noun}"
