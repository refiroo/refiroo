"""A move: what a client sends (Product 0.11 X2, D114–D117, API.md § Moves).

``POST /moves`` names the two workspaces, the mapping at the version the client read, what moves
and which state of the source it is read from. In X2 a move is its dry run alone
(``stage: preview``, D114), which X3 loads into a change set once confirmed, or at once with
``stage: execute`` (D128).
"""

from typing import Literal

from pydantic import UUID4, BaseModel, ConfigDict, Field, model_validator

from .queries import QueryCriterion

# The records a selection names by ID (D116), as an atomic batch's items.
MAX_OBJECT_IDS = 10_000


class MoveSelectionType(BaseModel):
    """One source type and its own criteria, as an export's scope (D116)."""

    model_config = ConfigDict(extra="forbid")

    objectTypeKey: str
    where: list[QueryCriterion] = Field(default_factory=list)


class MoveSelection(BaseModel):
    """What moves: the records every given part selects; empty, the whole workspace (I7, D116)."""

    model_config = ConfigDict(extra="forbid")

    types: list[MoveSelectionType] | None = Field(default=None, min_length=1)
    parentObjectId: UUID4 | None = Field(
        default=None, description="This record and every record under it"
    )
    objectIds: list[UUID4] | None = Field(default=None, min_length=1, max_length=MAX_OBJECT_IDS)

    @model_validator(mode="after")
    def each_type_once(self) -> MoveSelection:
        keys = [item.objectTypeKey for item in self.types or []]
        if len(keys) != len(set(keys)):
            raise ValueError("Each object type is named once")
        return self


class MoveMapping(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=1, max_length=160)
    expectedVersion: int = Field(ge=1)


class MoveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sourceWorkspaceKey: str = Field(min_length=1)
    targetWorkspaceKey: str = Field(min_length=1)
    mapping: MoveMapping
    selection: MoveSelection = Field(default_factory=MoveSelection)
    sourceAt: str = Field(
        default="live",
        min_length=1,
        description="live, read when the dry run starts, or a publication ID of the source (I30)",
    )
    mode: Literal["copy", "move"] = Field(
        default="copy",
        description="copy (the source untouched) or move: the copy, plus a change set of the "
        "source deleting what was loaded (D17, D134)",
    )
    stage: Literal["preview", "execute"] = Field(
        default="preview",
        description="preview: the dry run waits for POST /jobs/{jobId}/confirm; execute: it loads "
        "at once (D128). Either way it loads into a new change set of the target (D130)",
    )
