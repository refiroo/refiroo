"""A relationships table's field references (0.13 RV).

A filter or sort field of a ``relationTable`` view names the place it reads: ``from:<field>`` or
``to:<field>`` for a record at that end (``name`` or an attribute of its type) and
``relation:<attribute>`` for a value of the relationship itself. ``fromColumns``, ``toColumns`` and
``attributeColumns`` name the field alone, as their list says where it is read.
"""

from typing import Literal

Place = Literal["from", "to", "relation"]

PLACES: tuple[Place, ...] = ("from", "to", "relation")
# What an end record offers besides its attributes.
END_BUILT_INS = frozenset({"name"})


def split_ref(ref: str) -> tuple[Place, str] | None:
    """``("from", "name")`` for ``from:name``; ``None`` when ``ref`` names no place."""
    place, separator, field = ref.partition(":")
    if separator and field and place in PLACES:
        return place, field  # type: ignore[return-value]
    return None


def descending(sort: str) -> tuple[str, bool]:
    """A sort token's field reference and whether it sorts descending."""
    return (sort[1:], True) if sort.startswith("-") else (sort, False)
