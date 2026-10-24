from datetime import datetime
from typing import Any, Literal

from pydantic import UUID4, BaseModel, ConfigDict, Field, model_validator

from .common import CollectionPage, PrincipalResponse
from .records import AttributeOutput, ObjectPathPart
from .workspaces import MigrationTypeMapping


class ChangeSetCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, max_length=300)
    source: Literal["currentLive", "publication"] | None = None
    derivedFromPublicationId: UUID4 | None = None
    modelReleaseId: UUID4 | None = None

    @model_validator(mode="after")
    def validate_source(self) -> ChangeSetCreate:
        if self.source == "publication" and self.derivedFromPublicationId is None:
            raise ValueError("derivedFromPublicationId is required when source is publication")
        if self.source == "currentLive" and self.derivedFromPublicationId is not None:
            raise ValueError("derivedFromPublicationId cannot be combined with source currentLive")
        if self.derivedFromPublicationId is not None and self.modelReleaseId is not None:
            raise ValueError(
                "Historical creation retains its source model; change version afterward"
            )
        return self


class ChangeSetModelReleaseUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    modelReleaseId: UUID4
    expectedChangeSetVersion: int = Field(ge=1)


class ChangeSetMigrationRequest(BaseModel):
    """A move of the change set onto the release its workspace runs (0.11 V3, D87, D91), converting
    its content where that release differs. ``targetReleaseId`` may be left out; if sent it must be
    the workspace's release. ``typeMappings`` names what a type of the change set's release became
    in it, so its records keep their IDs."""

    model_config = ConfigDict(extra="forbid")

    expectedChangeSetVersion: int = Field(ge=1)
    targetReleaseId: UUID4 | None = None
    typeMappings: list[MigrationTypeMapping] = Field(default_factory=list, max_length=500)


class ChangeSetUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, max_length=300)
    expectedVersion: int = Field(ge=1)


class ChangeSetResponse(BaseModel):
    id: str
    workspaceKey: str
    name: str | None
    modelReleaseId: str
    modelReleaseKey: str
    modelReleaseVersion: str
    source: Literal["currentLive", "publication", "empty"]
    derivedFromPublicationId: str | None
    version: int
    createdAt: datetime
    updatedAt: datetime
    # Who created it (0.12 Z4, D315); null for one from before Z4.
    createdBy: PrincipalResponse | None


class ChangeSetPage(CollectionPage[ChangeSetResponse]):
    pass


class OwnChangeSetResponse(ChangeSetResponse):
    """One of the caller's open change sets, wherever it is (0.12 HM1, D333)."""

    workspaceLabel: str
    # The records and relations it adds, changes or removes, as its two change lists total them.
    changeCount: int


class OwnChangeSetPage(CollectionPage[OwnChangeSetResponse]):
    pass


class PublicationResponse(BaseModel):
    id: str
    workspaceKey: str
    modelReleaseId: str
    modelReleaseKey: str
    modelReleaseVersion: str
    publicationNumber: int
    status: Literal["active", "withdrawn"]
    derivedFromPublicationId: str | None
    supersedesPublicationId: str | None
    createdAt: datetime
    publishedAt: datetime
    withdrawnAt: datetime | None
    # The position of its ``published`` feed entry: live data at that position is the publication,
    # so a feed reader re-syncs from it (INTEGRATION_API F5). None when published before the feed.
    feedPosition: int | None
    # Who published it, and who withdrew it or published the one that superseded it (0.12 Z4,
    # D315); null from before Z4, and ``withdrawnBy`` while it is active.
    publishedBy: PrincipalResponse | None
    withdrawnBy: PrincipalResponse | None


class PublicationPage(CollectionPage[PublicationResponse]):
    pass


ChangeKind = Literal["added", "changed", "removed"]


class ObjectChangeState(BaseModel):
    """A record as the change set's source holds it (``before``) or as the change set does (``after``).

    ``objectTypeKey`` is the type on that side; a type change (ADR-034) makes the two differ.
    """

    objectTypeKey: str
    name: str
    parentObjectId: str | None
    attributes: list[AttributeOutput]
    version: int


class ObjectChange(BaseModel):
    """What a change set does to one record (Base 0.8 P2a, D31).

    ``changedFields`` names what differs between ``before`` and ``after`` (``objectType`` first
    when the type changed, then ``name``, ``parent`` and attribute keys); a missing side counts
    as holding nothing, so an added or removed record names every field it holds. A ``changed`` entry may name none: its version still advanced, and
    publishing still claims it against live. ``beforePath`` is where the source held a moved
    record (a ``changed`` entry naming ``parent``, Base 0.8 P2b); ``null`` otherwise.
    """

    kind: ChangeKind
    objectId: str
    objectTypeKey: str
    applicationKey: str
    before: ObjectChangeState | None
    after: ObjectChangeState | None
    changedFields: list[str]
    path: list[ObjectPathPart]
    beforePath: list[ObjectPathPart] | None = None


class ObjectChangePage(CollectionPage[ObjectChange]):
    """A change set's record changes by type, name and ID."""


class RelationChangeEnd(BaseModel):
    """One end of a changed relation, read in the change set, or in its source for a removed end."""

    objectId: str
    objectTypeKey: str | None
    name: str | None


class RelationChangeState(BaseModel):
    attributes: dict[str, Any]
    version: int


class RelationChange(BaseModel):
    """What a change set does to one relation (Base 0.8 P2a, D31).

    ``containment`` marks an engine-maintained parent edge (D32): its type is one of the ``to``
    end type's parent relations under the change set's model.
    """

    kind: ChangeKind
    relationId: str
    relationTypeKey: str
    containment: bool
    fromObject: RelationChangeEnd
    toObject: RelationChangeEnd
    before: RelationChangeState | None
    after: RelationChangeState | None
    changedFields: list[str]


class RelationChangePage(CollectionPage[RelationChange]):
    """A change set's relation changes by type and ID."""


class ChangeSetPublishRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expectedChangeSetVersion: int = Field(ge=1)
    expectedActivePublicationId: UUID4 | None = None


class ChangeSetValidation(BaseModel):
    valid: bool
    diagnostics: list[dict[str, Any]]
