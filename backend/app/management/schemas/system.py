from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class EngineInfo(BaseModel):
    version: str = Field(description="The product version, as the API document's info.version")
    managementApi: Literal["v1"]


class ActiveModelRelease(BaseModel):
    id: str
    key: str
    name: str
    version: str
    schemaVersion: str
    activatedAt: datetime = Field(
        description="When the release was activated or its schema upgraded (the runtime state's "
        "updatedAt)"
    )


class DatabaseInfo(BaseModel):
    revision: str | None = Field(description="The database's migration revision")


class SystemSetting(BaseModel):
    name: str = Field(description="The environment variable")
    group: Literal["runtime", "capabilities", "limits", "webhooks"]
    description: str = Field(description="What the setting controls")
    value: Any = Field(
        description="The value in effect, typed; null for a secret, and DATABASE_URL without its "
        "password"
    )
    default: Any = Field(description="The value without the variable; null for a secret")
    source: Literal["environment", "default"]


class SystemResponse(BaseModel):
    """What the deployment runs and how it is configured. Settings are read at startup and change
    only with a restart."""

    engine: EngineInfo
    schemaLanguages: list[str]
    activeModelRelease: ActiveModelRelease
    database: DatabaseInfo
    settings: list[SystemSetting]
