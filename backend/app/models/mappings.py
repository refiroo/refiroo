"""Model mappings: what a client sends (Product 0.11 X1, API.md § Mappings between two models).

A mapping is created between two workspaces (the releases they run) or two releases, changed by
operations at ``expectedVersion``, and proposed by an inference over two workspaces.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

MappingKey = Field(min_length=1, max_length=160, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


class ModelMappingCreate(BaseModel):
    """Each side named by a workspace or by a release, not both (D104)."""

    model_config = ConfigDict(extra="forbid")

    key: str = MappingKey
    name: str = Field(min_length=1, max_length=200)
    sourceWorkspaceKey: str | None = None
    targetWorkspaceKey: str | None = None
    sourceReleaseId: str | None = None
    targetReleaseId: str | None = None


class ModelMappingOperationsRequest(BaseModel):
    """One step of a mapping's history: operations applied in order, all or none."""

    model_config = ConfigDict(extra="forbid")

    expectedVersion: int = Field(ge=1)
    operations: list[dict[str, Any]] = Field(min_length=1)


class ModelMappingUndoRequest(BaseModel):
    """Undo the latest step not yet undone, or ``step``, or the ``steps`` together."""

    model_config = ConfigDict(extra="forbid")

    expectedVersion: int = Field(ge=1)
    step: int | None = Field(default=None, ge=1)
    steps: list[int] | None = Field(default=None, min_length=1)


class ModelMappingVersionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expectedVersion: int = Field(ge=1)


class MappingInferenceRequest(BaseModel):
    """The two workspaces whose models the mapping maps and whose records it compares (D108)."""

    model_config = ConfigDict(extra="forbid")

    sourceWorkspaceKey: str = Field(min_length=1)
    targetWorkspaceKey: str = Field(min_length=1)


class MappingInferenceApplication(BaseModel):
    """The proposals to apply, every open one when ``proposals`` is absent."""

    model_config = ConfigDict(extra="forbid")

    expectedVersion: int = Field(ge=1)
    proposals: list[str] | None = Field(default=None, min_length=1)
