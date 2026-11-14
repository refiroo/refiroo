"""Where the rows of an update table stand in the model's hierarchy (Product 0.16 AP6a).

A type contained in a parent type has its records under a parent. The rules read where the file's
rows belong, in this order:

1. every stored record the file's keys match sits under one parent: that is the source's fixed
   parent, and new rows go there too;
2. else the table's list title or its sheet's name equals the name of a stored record of a type that
   may contain the table's type: that record;
3. else, when the type may stand at the top, no parent;
4. else new rows cannot be placed: they are left out by default and the table says so.

A parent is found by its name; by a unique attribute of its type when its name is not unique.
"""

from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from .catalog import TypeInfo, Types
from .sql import FILE_KEYS, attribute_of, parameters_of, stored_query

SHARED = "records"
TITLED = "title"
PROFILE = "profile"


@dataclass(frozen=True)
class Placement:
    # The source's fixed parent (``FixedParent`` plus ``source``), or ``None``.
    parent: dict[str, Any] | None
    # False when new rows have nowhere to go.
    placed: bool


def _parent_ref(
    session: Session, workspace: str, types: Types, parent_id: str, source: str
) -> dict[str, Any] | None:
    row = session.execute(
        text("SELECT object_type_key, name FROM objects WHERE id = :id"), {"id": parent_id}
    ).one_or_none()
    if row is None:
        return None
    type_key, name = row
    same = session.scalar(
        text(
            "SELECT count(*) FROM objects WHERE workspace_key = :workspace"
            " AND object_type_key = :type AND name = :name"
        ),
        {"workspace": workspace, "type": type_key, "name": name},
    )
    if same == 1:
        return {
            "objectTypeKey": type_key,
            "matchBy": {"field": "name"},
            "value": name,
            "source": source,
        }
    info = types.get(type_key)
    attributes = [key for key, _ in info.unique] if info else []
    found = session.execute(
        text(
            "SELECT attribute_type_key, text_value FROM attribute_values WHERE object_id = :id"
            " AND attribute_type_key = ANY(:attributes) AND text_value IS NOT NULL"
            " ORDER BY attribute_type_key LIMIT 1"
        ),
        {"id": parent_id, "attributes": attributes},
    ).one_or_none()
    if found is None:
        return None
    return {
        "objectTypeKey": type_key,
        "matchBy": {"attributeTypeKey": found[0]},
        "value": found[1],
        "source": source,
    }


def choose(
    session: Session,
    workspace: str,
    types: Types,
    info: TypeInfo,
    file_id: int,
    place: dict[str, Any],
    key_column: int,
    key: dict[str, Any],
    name_column: int | None,
    titles: list[str],
) -> Placement:
    if not info.parents:
        return Placement(None, True)
    stored = stored_query(attribute_of(key))
    shared = (
        session.execute(
            text(
                f"WITH f AS ({FILE_KEYS}), s AS ({stored})"
                " SELECT DISTINCT s.parent_id FROM f JOIN s ON s.key = f.key"
            ),
            parameters_of(place, file_id, workspace, info.key, key_column, key, name_column),
        )
        .scalars()
        .all()
    )
    if len(shared) == 1 and shared[0] is not None:
        parent = _parent_ref(session, workspace, types, shared[0], SHARED)
        if parent is not None:
            return Placement(parent, True)
    # The title is casefolded here and compared with ``lower(name)``: one of five comparisons of a
    # name kept apart on purpose (see ``matching._FACTS``).
    wanted = sorted({t.strip().casefold() for t in titles if t and t.strip()})
    if wanted:
        named = (
            session.execute(
                text(
                    "SELECT id FROM objects WHERE workspace_key = :workspace"
                    " AND object_type_key = ANY(:types) AND lower(name) = ANY(:wanted)"
                ),
                {"workspace": workspace, "types": list(info.parents), "wanted": wanted},
            )
            .scalars()
            .all()
        )
        if len(named) == 1:
            parent = _parent_ref(session, workspace, types, named[0], TITLED)
            if parent is not None:
                return Placement(parent, True)
    return Placement(None, info.top)
