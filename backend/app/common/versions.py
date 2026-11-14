"""Dotted version text, the one reading of it."""

from typing import Any


def dotted_version(value: Any) -> tuple[int, ...] | None:
    """``"0.8"`` as ``(0, 8)``, to compare versions; ``None`` for text that is not a dotted
    version. What an unreadable version means is the caller's: a schema window says it is
    unreadable, a comparison of two documents reads it as ``(0,)``."""
    try:
        return tuple(int(part) for part in str(value).split("."))
    except ValueError:
        return None
