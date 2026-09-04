from dataclasses import dataclass
from typing import Any, Literal


@dataclass(frozen=True)
class SemanticChange:
    kind: Literal["added", "changed", "removed"]
    path: str
    before: Any | None = None
    after: Any | None = None


def semantic_diff(before: dict[str, Any], after: dict[str, Any]) -> tuple[SemanticChange, ...]:
    changes: list[SemanticChange] = []
    _compare(before, after, "", None, changes)
    return tuple(changes)


def _compare(
    before: Any,
    after: Any,
    path: str,
    field_name: str | None,
    changes: list[SemanticChange],
) -> None:
    if isinstance(before, dict) and isinstance(after, dict):
        for key in sorted(set(before) | set(after)):
            child_path = f"{path}/{_pointer_segment(key)}"
            if key not in before:
                changes.append(SemanticChange("added", child_path, after=after[key]))
            elif key not in after:
                changes.append(SemanticChange("removed", child_path, before=before[key]))
            else:
                _compare(before[key], after[key], child_path, key, changes)
        return

    identity = _list_identity(field_name, before, after)
    if isinstance(before, list) and isinstance(after, list) and identity is not None:
        before_items = {identity(item): item for item in before}
        after_items = {identity(item): item for item in after}
        for item_key in sorted(set(before_items) | set(after_items)):
            item_path = path + "".join(f"/{_pointer_segment(part)}" for part in item_key)
            if item_key not in before_items:
                changes.append(SemanticChange("added", item_path, after=after_items[item_key]))
            elif item_key not in after_items:
                changes.append(SemanticChange("removed", item_path, before=before_items[item_key]))
            else:
                _compare(before_items[item_key], after_items[item_key], item_path, None, changes)
        return

    if before != after:
        changes.append(SemanticChange("changed", path, before=before, after=after))


def _list_identity(field_name: str | None, before: Any, after: Any):
    if not isinstance(before, list) or not isinstance(after, list):
        return None
    fields: tuple[str, ...] | None = None
    if field_name in {"attributeTypes", "objectTypes", "relationTypes", "applications", "views", "panels"}:
        fields = ("key",)
    elif field_name == "attributes":
        fields = ("attributeTypeKey",)
    elif field_name == "details":
        fields = ("objectTypeKey",)
    elif field_name == "objectTypeRelations":
        fields = ("relationTypeKey", "fromObjectTypeKey", "toObjectTypeKey")
    if fields is None:
        return None
    if not all(
        isinstance(item, dict) and all(field in item for field in fields)
        for item in before + after
    ):
        return None
    return lambda item: tuple(str(item[field]) for field in fields)


def _pointer_segment(value: Any) -> str:
    return str(value).replace("~", "~0").replace("/", "~1")
