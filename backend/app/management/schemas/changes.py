"""Data and model changes across workspaces (Product 0.12 Z6, D340, D343)."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field
from pydantic.json_schema import SkipJsonSchema

from .common import ActorResponse, CollectionPage, omitted_when_none, without_default


def _omitted() -> Any:
    return Field(default=None, exclude_if=omitted_when_none, json_schema_extra=without_default)


class ChangeWorkspace(BaseModel):
    key: str
    label: str


class ChangeSetRef(BaseModel):
    """The change set an entry was made in, or a publication published; ``name`` as it was last
    named, also once published or discarded."""

    id: str
    name: str | None
    # Whether it is still open, so it can be opened; a published or discarded one is gone.
    open: bool


class ChangeObject(BaseModel):
    """A relationship's end, named as it is now; ``name`` is null for a record since removed."""

    id: str
    name: str | None


class ChangeSubject(BaseModel):
    """What an entry changed, named as it is now (D343): a record (its type and name), a
    relationship (its type and both ends), a change set, a publication (its number), a model draft
    or a release. ``removed`` says whether a record or relationship is gone from where it was."""

    id: str
    name: str | SkipJsonSchema[None] = _omitted()
    number: int | SkipJsonSchema[None] = _omitted()
    # A record's application, where it opens.
    applicationKey: str | SkipJsonSchema[None] = _omitted()
    objectTypeKey: str | SkipJsonSchema[None] = _omitted()
    objectTypeName: str | SkipJsonSchema[None] = _omitted()
    relationTypeKey: str | SkipJsonSchema[None] = _omitted()
    relationTypeName: str | SkipJsonSchema[None] = _omitted()
    fromObject: ChangeObject | SkipJsonSchema[None] = _omitted()
    toObject: ChangeObject | SkipJsonSchema[None] = _omitted()
    removed: bool | SkipJsonSchema[None] = _omitted()


class ChangeAttribute(BaseModel):
    key: str
    # From the entry's workspace's model; the key when the model no longer has it.
    name: str


class ChangeCause(BaseModel):
    """What made the change: a single write (``user``), a job or a publication."""

    kind: str
    # Omitted for a single write.
    id: str | SkipJsonSchema[None] = _omitted()


class ChangeEntry(BaseModel):
    """One change: where, what, how and by whom; never values (D343)."""

    id: str
    occurredAt: datetime
    kind: Literal["record", "relationship", "change-set", "publication", "model"]
    # record: created, updated, deleted, reclassified; relationship: created, updated, deleted;
    # change set: created, renamed, validated, discarded, …; publication: published, withdrawn;
    # model: created, updated, deleted (a draft), installed, activated. Readers ignore others.
    action: str
    # Null for model administration outside workspaces, and for a deleted workspace's entries.
    workspace: ChangeWorkspace | None
    changeSet: ChangeSetRef | None
    subject: ChangeSubject
    changedFields: list[str]
    attributes: list[ChangeAttribute]
    cause: ChangeCause
    actor: ActorResponse | None


class ChangePage(CollectionPage[ChangeEntry]):
    pass
