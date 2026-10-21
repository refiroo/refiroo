from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from .common import CollectionPage


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


class ProcessThread(BaseModel):
    name: Literal[
        "jobWorker", "exportWorker", "jobListener", "eventDeriver", "webhookDispatcher", "heartbeat"
    ]
    state: Literal["running", "failing", "off"] = Field(
        description="off: not started in this process (its capability is off, or no workspace "
        "can be served)"
    )
    reason: (
        Literal["poolExhausted", "tooManyConnections", "transactionEnded", "unreachable", "error"]
        | None
    ) = Field(default=None, description="Why its rounds fail: a database reason, or error")
    since: datetime | None = Field(default=None, description="When the failure began")


class ProcessPool(BaseModel):
    size: int = Field(description="DATABASE_POOL_SIZE")
    maxOverflow: int = Field(description="DATABASE_POOL_MAX_OVERFLOW")
    inUse: int = Field(description="Connections checked out when the process last reported")


class UnavailableRelease(BaseModel):
    releaseId: str
    schemaVersion: str
    reason: Literal["unsupportedSchema", "invalid", "notLoaded"] = Field(
        description="unsupportedSchema: outside the engine's schema window; invalid: the model "
        "does not validate; notLoaded: activated but not loaded by this process, which serves it "
        "again after a restart"
    )


class ProcessCounters(BaseModel):
    requests: int = Field(description="Requests answered since the process started")
    serverErrors: int = Field(description="Of them, answered with a 5xx status")
    databaseUnavailable: dict[str, int] = Field(
        description="Times a request or a background thread got no database connection, by reason"
    )


class ProcessResponse(BaseModel):
    """One engine process as it last reported itself (0.11 O1)."""

    id: str = Field(description="host:pid:random, as a job's leaseOwner begins")
    host: str
    pid: int
    engineVersion: str
    startedAt: datetime
    heartbeatAt: datetime
    state: Literal["live", "silent"] = Field(
        description="silent: no report for three PROCESS_HEARTBEAT_SECONDS; a stopped process "
        "leaves the list, one that died is listed silent for a day"
    )
    ready: bool = Field(description="Whether it serves requests: at least one workspace's model")
    threads: list[ProcessThread]
    pool: ProcessPool
    unavailableReleases: list[UnavailableRelease]
    counters: ProcessCounters


class ProcessPage(CollectionPage[ProcessResponse]):
    pass


class ReadinessRelease(BaseModel):
    id: str
    key: str
    version: str
    schemaVersion: str


class ReadinessProcess(BaseModel):
    processId: str
    reason: Literal["unsupportedSchema", "invalid", "notLoaded"]
    schemaVersion: str


class WorkspaceReadinessResponse(BaseModel):
    """Whether every live process serves a workspace's model (0.11 O1)."""

    workspaceKey: str
    release: ReadinessRelease | None = Field(description="The release it runs; null for none")
    state: Literal["served", "unavailable"]
    unavailableIn: list[ReadinessProcess] = Field(
        description="The live processes that cannot serve its release, each with why"
    )


class WorkspaceReadinessPage(CollectionPage[WorkspaceReadinessResponse]):
    pass
