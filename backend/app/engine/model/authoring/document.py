"""A model document being changed by operations, with every change recorded so it can be taken back.

Operations change the draft's JSON document in place through :class:`Document`, which logs, for each
primitive change, the change that reverses it. A compound kind (a removal, a split, a merge) stores
that log as its inverse, ``restoreElements``, so its undo puts back exactly what it took and only that
(ADR-041: the inverse is stored when the operation is applied).

A change names its place by a **path** of keys, never by position: a segment is a member name, or an
object naming a list item by its identity (``{"key": …}``, ``{"objectTypeKey": …}``,
``{"attributeTypeKey": …}``, a relation binding's three keys) or, in a list of strings, by the string
itself (``{"value": …}``). So a change still finds its place after other steps changed the lists
around it.
"""

import copy
from collections.abc import Callable
from typing import Any

Path = list[Any]

# The members that identify an item in a list of objects, tried in order.
_IDENTITIES: tuple[tuple[str, ...], ...] = (
    ("relationTypeKey", "fromObjectTypeKey", "toObjectTypeKey"),
    ("key",),
    ("objectTypeKey",),
    ("attributeTypeKey",),
)


class Refusal(Exception):
    """An operation that cannot be applied to the document: ``field`` is the parameter at fault
    (a pointer below the operation, without the leading slash), ``reason`` a machine-readable word."""

    def __init__(self, field: str, reason: str, message: str) -> None:
        super().__init__(message)
        self.field = field
        self.reason = reason
        self.message = message


def identity(item: Any) -> dict[str, Any]:
    """The path segment naming ``item`` within its list."""
    if isinstance(item, dict):
        for fields in _IDENTITIES:
            if all(field in item for field in fields):
                return {field: item[field] for field in fields}
    return {"value": item}


def _matches(item: Any, segment: dict[str, Any]) -> bool:
    if "value" in segment and len(segment) == 1:
        return item == segment["value"]
    return isinstance(item, dict) and all(item.get(key) == value for key, value in segment.items())


def _step(node: Any, segment: Any) -> Any:
    if isinstance(segment, str):
        if not isinstance(node, dict) or segment not in node:
            raise LookupError(segment)
        return node[segment]
    if not isinstance(node, list):
        # A path that does not resolve is a missing place, whatever stands there instead.
        raise LookupError(segment)  # noqa: TRY004
    if isinstance(segment, int):
        if 0 <= segment < len(node):
            return node[segment]
        raise LookupError(segment)
    for item in node:
        if _matches(item, segment):
            return item
    raise LookupError(segment)


class Document:
    """The model document, changed only through these methods so every change is logged."""

    def __init__(self, data: dict[str, Any]) -> None:
        self.data = data
        self.log: list[dict[str, Any]] = []

    # --- reading ---

    def at(self, path: Path) -> Any:
        node: Any = self.data
        for segment in path:
            node = _step(node, segment)
        return node

    def find(self, path: Path) -> Any | None:
        try:
            return self.at(path)
        except LookupError:
            return None

    def items(self, name: str) -> list[dict[str, Any]]:
        value = self.data.get(name)
        return value if isinstance(value, list) else []

    # --- changing ---

    def insert(self, path: Path, value: Any, index: int | None = None) -> None:
        """Insert ``value`` into the list at ``path`` (created when missing), at ``index`` or last."""
        container = self._list(path)
        position = len(container) if index is None else max(0, min(index, len(container)))
        container.insert(position, value)
        self.log.append({"change": "remove", "path": copy.deepcopy(path), "item": identity(value)})

    def remove(self, path: Path, item: Any) -> Any:
        """Remove ``item`` (a value, or the item a path segment names) from the list at ``path``."""
        container = self.at(path)
        segment = item if isinstance(item, dict) and _is_segment(item) else {"value": item}
        for position, candidate in enumerate(container):
            if _matches(candidate, segment):
                removed = container.pop(position)
                self.log.append(
                    {
                        "change": "insert",
                        "path": copy.deepcopy(path),
                        "index": position,
                        "value": copy.deepcopy(removed),
                    }
                )
                return removed
        raise LookupError(item)

    def remove_where(self, path: Path, predicate: Callable[[Any], bool]) -> list[Any]:
        container = self.find(path)
        if not isinstance(container, list):
            return []
        removed = []
        for candidate in [item for item in container if predicate(item)]:
            removed.append(self.remove(path, identity(candidate)))
        return removed

    def set(self, path: Path, field: str, value: Any) -> None:
        """Set member ``field`` of the object at ``path``; ``None`` removes the member."""
        node = self.at(path)
        absent = field not in node
        before = copy.deepcopy(node.get(field))
        if value is None:
            if absent:
                return
            del node[field]
        else:
            if not absent and node[field] == value:
                return
            node[field] = value
        self.log.append(
            {"change": "set", "path": copy.deepcopy(path), "field": field, "value": None if absent else before}
        )

    def move(self, path: Path, item: Any, index: int) -> int:
        """Move ``item`` within the list at ``path`` to ``index``; returns its old index."""
        container = self.at(path)
        segment = item if isinstance(item, dict) and _is_segment(item) else {"value": item}
        old = next(i for i, candidate in enumerate(container) if _matches(candidate, segment))
        value = self.remove(path, identity(container[old]))
        self.insert(path, value, index)
        return old

    def _list(self, path: Path) -> list[Any]:
        parent = self.at(path[:-1])
        name = path[-1]
        if isinstance(name, str) and isinstance(parent, dict) and name not in parent:
            self.set(path[:-1], name, [])
        container = self.at(path)
        if not isinstance(container, list):
            raise LookupError(name)  # noqa: TRY004 - a missing list, as at()
        return container

    def reversal(self) -> list[dict[str, Any]]:
        """The changes that take back everything logged, in the order to apply them."""
        return list(reversed(self.log))


def _is_segment(value: dict[str, Any]) -> bool:
    return any(all(field in value for field in fields) and len(value) == len(fields) for fields in _IDENTITIES) or (
        set(value) == {"value"}
    )


def apply_changes(document: Document, changes: list[dict[str, Any]]) -> None:
    """Apply logged changes (a ``restoreElements`` operation's), each logged again in turn."""
    for change in changes:
        path = change["path"]
        if change["change"] == "insert":
            document.insert(path, copy.deepcopy(change["value"]), change["index"])
        elif change["change"] == "remove":
            document.remove(path, change["item"])
        else:
            document.set(path, change["field"], copy.deepcopy(change["value"]))
