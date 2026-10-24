"""Model mappings: what the API answers (Product 0.11 X1, D104–D113)."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

from .common import ApiErrorBody, CollectionPage, PrincipalResponse


class MappingProblem(BaseModel):
    """An entry naming what a release lacks or no longer allows (D110), at its pointer into the
    mapping, on the ``source`` or ``target`` side."""

    code: Literal[
        "ELEMENT_NOT_IN_RELEASE",
        "BINDING_NOT_ALLOWED",
        "VALUE_TYPES_NOT_CONVERTIBLE",
        "ATTRIBUTE_FILLED_TWICE",
    ]
    pointer: str
    side: Literal["source", "target"]
    message: str


class MappingCoverage(BaseModel):
    """What the mapping leaves out (D110): source types, attributes and relationships not mapped;
    the target's required attributes and relationships nothing fills; the parents a source record
    may stand under that its target type cannot (``PARENT_NOT_ALLOWED``, ``PARENT_TYPE_NOT_MAPPED``,
    ``PARENT_REQUIRED`` with ``parentType`` null for the top)."""

    types: list[str]
    attributes: list[dict[str, str]]
    relations: list[dict[str, str]]
    required: list[dict[str, str]]
    requiredRelations: list[dict[str, str]]
    parents: list[dict[str, Any]]


class MappingTypeEntry(BaseModel):
    """What one source type becomes (D106): its target type, its attributes (``target`` with an
    optional ``valueMap``, or ``ignore``), its relationships, where its records stand, how existing
    target records are matched, and the defaults of target attributes."""

    source: str
    target: str
    attributes: list[dict[str, Any]]
    relations: list[dict[str, Any]]
    defaults: dict[str, Any]
    parent: dict[str, Any] | None = None
    match: dict[str, Any] | None = None


class ModelMappingSummary(BaseModel):
    key: str
    name: str
    sourceModelKey: str
    targetModelKey: str
    sourceReleaseId: str
    targetReleaseId: str
    version: int
    updatedAt: datetime


class ModelMappingResponse(ModelMappingSummary):
    """A mapping with its problems and coverage, against its releases or the releases of the
    workspaces the read named."""

    types: list[MappingTypeEntry]
    valueMaps: dict[str, dict[str, Any]]
    problems: list[MappingProblem]
    coverage: MappingCoverage
    createdAt: datetime


class ModelMappingPage(CollectionPage[ModelMappingSummary]):
    """Model mappings in key order."""


class ModelMappingOperationEntry(BaseModel):
    """One operation in a mapping's history (D105), as a draft's."""

    sequence: int
    step: int
    kind: str
    parameters: dict[str, Any]
    inverse: dict[str, Any]
    mappingVersion: int
    # Who applied it (0.12 Z4, D315); null for an operation from before Z4.
    author: PrincipalResponse | None
    at: datetime
    undone: bool
    origin: dict[str, Any]


class ModelMappingOperationPage(CollectionPage[ModelMappingOperationEntry]):
    """A mapping's history in sequence order."""


class ModelMappingStepResponse(BaseModel):
    """The mapping after a step: its version, the step's entries and its problems."""

    version: int
    entries: list[ModelMappingOperationEntry]
    problems: list[MappingProblem]


class MappingInferenceCounts(BaseModel):
    open: int
    applied: int
    held: int
    rejected: int


class MappingInferenceResponse(BaseModel):
    """A mapping's latest inference (D108): ``checking`` while its job runs, then ``completed``
    with its proposals' counts by status and its warnings; ``failed`` with the error."""

    jobId: str
    state: Literal["checking", "completed", "failed", "cancelled", "expired"]
    mappingVersion: int
    sourceWorkspaceKey: str
    targetWorkspaceKey: str
    sourceReleaseId: str
    targetReleaseId: str
    counts: MappingInferenceCounts
    warnings: list[str]
    error: ApiErrorBody | None


class MappingProposalResponse(BaseModel):
    """A proposal (D108): a source type's or one of its relationships' target, its score and
    evidence, the operations it applies, its alternatives as operations to send after it, the
    proposals it requires and its status: ``open``, ``applied``, ``held`` (the mapping decides it
    otherwise) or ``rejected`` (a step that applied it was undone)."""

    id: str
    position: int
    kind: Literal["type", "relation"]
    sourceType: str
    relation: str | None
    target: str
    score: float
    summary: str
    evidence: list[dict[str, Any]]
    operations: list[dict[str, Any]]
    alternatives: list[dict[str, Any]]
    requires: list[str]
    status: Literal["open", "applied", "held", "rejected"]


class MappingProposalPage(CollectionPage[MappingProposalResponse]):
    """The latest inference's proposals in the order they apply."""
