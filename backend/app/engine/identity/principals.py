"""Principals as a read names them (Product 0.12 Z4, D237, D316).

A row names a person or a client by its row ID, in a ``…_user_id``/``…_client_id`` pair; a read
shows ``{kind, id, name}`` with the public ID and the name as they are now, so a renamed or
deactivated principal reads as it is. ``names`` resolves a page's principals in one statement per
kind. An audit entry's actor may also be the engine, or nobody for an entry from before Z4.
"""

from collections.abc import Iterable
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...models.database import OAuthClient, User

# A principal as rows hold it: ``("user" | "client", row ID)``.
Ref = tuple[str, int]

_MODELS = {"user": User, "client": OAuthClient}
ENGINE = {"kind": "engine"}


def ref(user_id: int | None, client_id: int | None) -> Ref | None:
    """The principal a ``…_user_id``/``…_client_id`` pair names, if any."""
    if user_id is not None:
        return ("user", user_id)
    if client_id is not None:
        return ("client", client_id)
    return None


def columns(found: Ref | None, prefix: str) -> dict[str, int | None]:
    """The pair of columns ``prefix_user_id`` and ``prefix_client_id`` that name ``found``."""
    kind, row_id = found if found is not None else (None, None)
    return {
        f"{prefix}_user_id": row_id if kind == "user" else None,
        f"{prefix}_client_id": row_id if kind == "client" else None,
    }


def names(session: Session, refs: Iterable[Ref | None]) -> dict[Ref, dict[str, str]]:
    """Each principal as it reads now: ``kind``, public ``id`` and ``name``."""
    wanted: dict[str, set[int]] = {}
    for item in refs:
        if item is not None:
            wanted.setdefault(item[0], set()).add(item[1])
    found: dict[Ref, dict[str, str]] = {}
    for kind, row_ids in wanted.items():
        model = _MODELS[kind]
        rows = session.execute(
            select(model.id, model.public_id, model.name).where(model.id.in_(row_ids))
        )
        for row_id, public_id, name in rows:
            found[(kind, row_id)] = {"kind": kind, "id": public_id, "name": name}
    return found


def named(session: Session, found: Ref | None) -> dict[str, str] | None:
    """One principal as it reads, or None; a row the session already holds is not read again, so
    a page naming a few principals reads each once."""
    if found is None:
        return None
    row = session.get(_MODELS[found[0]], found[1])
    return {"kind": found[0], "id": row.public_id, "name": row.name} if row is not None else None


def actor_ref(row: Any) -> Ref | None:
    """The person or client an audit entry names as its actor."""
    return ref(row.actor_user_id, row.actor_client_id)


def actors(session: Session, rows: Iterable[Any]) -> dict[int, dict[str, str] | None]:
    """Each audit entry's actor as it reads, by sequence ID: a principal, ``{kind: "engine"}``, or
    None for an entry from before Z4 ("Before sign-in", D313)."""
    rows = list(rows)
    resolved = names(session, (actor_ref(row) for row in rows))
    found: dict[int, dict[str, str] | None] = {}
    for row in rows:
        if row.actor_kind == "engine":
            found[row.sequence_id] = ENGINE
        else:
            principal = actor_ref(row)
            found[row.sequence_id] = resolved.get(principal) if principal else None
    return found
