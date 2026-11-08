"""The import profile a draft's profile stands for (Product 0.10 A5, D75), shared by the draft's
profile read and its dry run."""

from typing import Any


def definition(profile: dict[str, Any] | None) -> tuple[dict[str, Any] | None, list[int]]:
    """The import profile the draft's profile stands for, and, per source in it, its position in
    the draft's profile: no ``id``, no editor members, and no source without columns."""
    if not profile or not profile.get("sources"):
        return None, []
    sources, positions = [], []
    for position, source in enumerate(profile["sources"]):
        if not source.get("columns"):
            continue
        sources.append({name: value for name, value in source.items() if name != "id"})
        positions.append(position)
    if not sources:
        return None, []
    return {"sources": sources, "valueMaps": profile.get("valueMaps") or {}}, positions
