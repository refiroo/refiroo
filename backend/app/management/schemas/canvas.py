"""A model draft's canvas positions (0.17 PL3b, PP-D54)."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

LIMIT = 1_000_000.0

CanvasScope = Literal["model", "changed", "workbook"]


class CanvasPosition(BaseModel):
    """Where a card sits on the board, in the board's own units."""

    model_config = ConfigDict(extra="forbid")

    x: float = Field(ge=-LIMIT, le=LIMIT, allow_inf_nan=False)
    y: float = Field(ge=-LIMIT, le=LIMIT, allow_inf_nan=False)


class CanvasResponse(BaseModel):
    """What the draft's board keeps: card positions by card key, the folded cards' keys and the chosen
    scope (``null``: the default). Not part of the draft's model, version or history."""

    positions: dict[str, CanvasPosition]
    folded: list[str] = Field(default_factory=list)
    scope: CanvasScope | None = None


class CanvasUpdate(BaseModel):
    """``PATCH /model-drafts/{id}/canvas``: parts merged into what the board keeps, each optional but
    one at least. ``positions`` merge by card key (``null`` removes a card); ``folded`` merge by card
    key (``true`` folds, ``false`` or ``null`` unfolds); ``scope`` replaces the chosen scope (``null``
    returns to the default)."""

    model_config = ConfigDict(extra="forbid")

    positions: dict[str, CanvasPosition | None] | None = Field(default=None, min_length=1)
    folded: dict[str, bool | None] | None = Field(default=None, min_length=1)
    scope: CanvasScope | None = None

    @model_validator(mode="after")
    def something(self) -> CanvasUpdate:
        if not self.model_fields_set & {"positions", "folded", "scope"}:
            raise ValueError("Name positions, folded or scope")
        for part in (self.positions, self.folded):
            if part is not None and any(not 1 <= len(key) <= 200 for key in part):
                raise ValueError("A card key is 1 to 200 characters")
        return self
