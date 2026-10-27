"""Publication requests, decisions and the approval policy (0.12 A1, API.md § Approvals)."""

from datetime import datetime
from typing import Literal

from pydantic import UUID4, BaseModel, ConfigDict, Field

from .common import CollectionPage, PrincipalResponse

RequestState = Literal["submitted", "withdrawn", "approved", "sentBack"]


class SubmissionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expectedChangeSetVersion: int = Field(ge=1)
    comment: str | None = Field(default=None, max_length=2000)


class DecisionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    outcome: Literal["approve", "sendBack"]
    comment: str | None = Field(default=None, max_length=2000)
    expectedChangeSetVersion: int = Field(ge=1)
    expectedActivePublicationId: UUID4 | None = None


class DecisionResponse(BaseModel):
    id: str
    outcome: Literal["approve", "sendBack"]
    version: int = Field(description="The change set's version the decision was made on")
    comment: str | None
    decidedAt: datetime
    decider: PrincipalResponse | None


class PublicationRequestResponse(BaseModel):
    """A change set's submission for publication and the decisions on it. ``changeSetName`` is the
    change set's name when it was submitted: an approved change set no longer exists."""

    id: str
    workspaceKey: str
    changeSetId: str
    changeSetName: str | None
    version: int = Field(description="The change set's version that was submitted")
    state: RequestState
    submitter: PrincipalResponse | None
    comment: str | None
    submittedAt: datetime
    publicationId: str | None = Field(description="The publication an approval made")
    decisions: list[DecisionResponse]


class PublicationRequestPage(CollectionPage[PublicationRequestResponse]):
    """Publication requests, newest first (ADR-030)."""


class ApprovalPolicyUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    requireApproval: bool
    secondPerson: bool
    expectedVersion: int = Field(ge=0, description="The policy's version read; 0 before any is set")


class ApprovalPolicyResponse(BaseModel):
    workspaceKey: str
    requireApproval: bool
    secondPerson: bool
    version: int
    approverCount: int = Field(
        description="The active people and clients who hold the `approve` action group in the "
        "workspace, by an instance grant or a grant of that workspace, directly or (for a "
        "person) through a group; a count, no names"
    )
