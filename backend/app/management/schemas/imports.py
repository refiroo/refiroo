"""Import profiles (Base 0.9 J2, INTEGRATION_API §J3)."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field
from pydantic.json_schema import SkipJsonSchema

from ...models.imports import CsvOptions, Source
from .common import CollectionPage, omitted_when_none, without_default


class ImportProfileProblem(BaseModel):
    """Something in the profile the model release does not resolve, at its JSON pointer."""

    path: str
    code: str
    message: str


class ImportProfileResponse(BaseModel):
    """A stored profile. ``checkedAgainst`` is the release it was saved against; ``valid`` and
    ``problems`` say how it reads under the active release, so a profile a later release broke
    shows what to fix before an import is refused for it."""

    key: str
    name: str
    version: int
    checkedAgainst: str
    valid: bool
    problems: list[ImportProfileProblem]
    createdAt: datetime
    updatedAt: datetime
    csv: CsvOptions | SkipJsonSchema[None] = Field(
        default=None, exclude_if=omitted_when_none, json_schema_extra=without_default
    )
    sources: list[Source]
    valueMaps: dict[str, dict[str, Any]]


class ImportProfilePage(CollectionPage[ImportProfileResponse]):
    """Import profiles in key order."""
