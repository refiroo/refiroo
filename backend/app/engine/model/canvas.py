"""What the board of a draft keeps (0.17 PL3b, PP-D54; CE1, PP-D81).

The canvas is a view of the draft; what it keeps is its own and nothing else: not part of the draft's
model, its version, its history, an undo step or a release, so a move never changes ``expectedVersion``
and is never undone with a model step. It keeps the card positions, the folded cards and the chosen
scope. Positions are a map of card key to ``x`` and ``y``, and folded cards a map of card key to
``true``; both are merged by key: two editors moving or folding different cards do not overwrite each
other, and a card changed by both keeps the later change. The scope (``model``, ``changed`` or
``workbook``) is replaced; ``null`` is the default.

Stored as one JSON document, ``{"positions": ..., "folded": ..., "scope": ...}``; a document written
before folding and scope existed was the positions map alone and is read as such.
"""

from typing import Any

from sqlalchemy.orm import Session

from ...errors import api_error
from ...models.database import ModelDraft
from .drafts import load_draft, load_draft_for_update

MAX_CARDS = 500
SCOPES = ("model", "changed", "workbook")

_UNSET: Any = object()


def read_canvas(session: Session, draft_id: str) -> dict[str, Any]:
    return _answer(load_draft(session, draft_id))


def merge_canvas(
    session: Session,
    draft_id: str,
    positions: dict[str, dict[str, float] | None] | None = None,
    folded: dict[str, bool | None] | None = None,
    scope: Any = _UNSET,
) -> dict[str, Any]:
    """The given parts merged into the draft's canvas. A card key with a position is placed, one with
    ``None`` is removed; a key folded with ``True`` is folded, one with ``False`` or ``None`` is
    unfolded; ``scope`` replaces the chosen scope (``None`` is the default). A part left out stays as
    it is. ``422 INVALID_CANVAS`` when the draft would hold more than :data:`MAX_CARDS` placed or
    folded cards, or ``scope`` is none of :data:`SCOPES`; nothing changes then."""
    draft = load_draft_for_update(session, draft_id)
    kept = _kept(draft.canvas_json)
    placed: dict[str, Any] = kept["positions"]
    for key, position in (positions or {}).items():
        if position is None:
            placed.pop(key, None)
        else:
            placed[key] = {"x": position["x"], "y": position["y"]}
    shut: dict[str, bool] = kept["folded"]
    for key, value in (folded or {}).items():
        if value:
            shut[key] = True
        else:
            shut.pop(key, None)
    if scope is not _UNSET:
        if scope is not None and scope not in SCOPES:
            raise api_error(
                422,
                "INVALID_CANVAS",
                "The scope is model, changed or workbook",
                {"scope": scope, "allowed": list(SCOPES)},
            )
        kept["scope"] = scope
    for part, held in (("positions", placed), ("folded", shut)):
        if len(held) > MAX_CARDS:
            raise api_error(
                422,
                "INVALID_CANVAS",
                f"A canvas holds at most {MAX_CARDS} cards; remove cards that are gone before placing more",
                {"cards": len(held), "limit": MAX_CARDS, "part": part},
            )
    # Not the draft's version or update time: the board is not a change of the draft.
    draft.canvas_json = kept if (placed or shut or kept["scope"]) else None
    session.flush()
    return _answer(draft)


def _kept(raw: dict[str, Any] | None) -> dict[str, Any]:
    """The stored document with every part present, as copies; the older positions-only shape too."""
    raw = dict(raw or {})
    if raw and not (raw.keys() & {"positions", "folded", "scope"}):
        raw = {"positions": raw}
    return {
        "positions": dict(raw.get("positions") or {}),
        "folded": dict(raw.get("folded") or {}),
        "scope": raw.get("scope"),
    }


def _answer(draft: ModelDraft) -> dict[str, Any]:
    kept = _kept(draft.canvas_json)
    return {
        "positions": kept["positions"],
        "folded": sorted(kept["folded"]),
        "scope": kept["scope"],
    }
