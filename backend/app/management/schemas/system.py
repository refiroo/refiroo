from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from .agent_access import McpSystemInfo
from .ai import AiSystemInfo
from .common import CollectionPage


class BuildInfo(BaseModel):
    commit: str | None = Field(description="The short commit the running code was built from")
    tag: str | None = Field(description="The release tag on that commit; null when it has none")


class EngineInfo(BaseModel):
    version: str = Field(description="The product version, as the API document's info.version")
    managementApi: Literal["v1"]
    license: str = Field(description="The licence the engine is offered under, an SPDX identifier")
    sourceCode: str = Field(
        description="Where the corresponding source of the running version is (SOURCE_CODE_URL)"
    )
    build: BuildInfo = Field(description="The commit and tag the code was built from (0.13 BR)")


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
    group: Literal["runtime", "capabilities", "limits", "webhooks", "ai"]
    description: str = Field(description="What the setting controls")
    value: Any = Field(
        description="The value in effect, typed; null for a secret, and DATABASE_URL without its "
        "password"
    )
    default: Any = Field(description="The value without the variable; null for a secret")
    source: Literal["environment", "default"]


class InstanceProduct(BaseModel):
    name: str
    description: str | None


class SystemResponse(BaseModel):
    """What the deployment runs, for anyone signed in (D246). How it is configured is
    ``GET /system/configuration``."""

    engine: EngineInfo
    schemaLanguages: list[str]
    activeModelRelease: ActiveModelRelease
    # The instance's name in the top bar: the default workspace's model's product, readable by a
    # person who may browse no workspace (0.12 HM1, D338); null when that model cannot be served.
    product: InstanceProduct | None = None
    # Whether an AI provider is set, the most that may leave the instance (0.16 AP1); a client
    # offers an AI action only then.
    ai: AiSystemInfo
    # Whether assistants can reach the instance at /mcp (0.16 AG1).
    mcp: McpSystemInfo


class SystemConfiguration(BaseModel):
    """How the deployment is configured, for operators (D246). Settings are read at startup and
    change only with a restart."""

    database: DatabaseInfo
    settings: list[SystemSetting]


class ProcessThread(BaseModel):
    name: Literal[
        "jobWorker",
        "exportWorker",
        "assistantWorker",
        "jobListener",
        "eventDeriver",
        "webhookDispatcher",
        "mailSender",
        "heartbeat",
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


class SummaryJobs(BaseModel):
    kind: str
    state: Literal["queued", "running", "awaiting_confirmation"]
    count: int


class SummaryProcesses(BaseModel):
    live: int
    silent: int


class SummaryWorkspaces(BaseModel):
    served: int = Field(description="Active workspaces every live process serves")
    unavailable: int = Field(
        description="Active workspaces some live process cannot serve, or that run no release"
    )


class SummarySubscriptions(BaseModel):
    active: int = Field(description="Delivering, not failing")
    failing: int = Field(description="Active while a batch is retried")
    suspended: int


class SystemSummary(BaseModel):
    """The instance's figures counted now, as ``/metrics``' instance gauges (0.11 O2, D201)."""

    processes: SummaryProcesses
    workspaces: SummaryWorkspaces
    jobs: list[SummaryJobs] = Field(
        description="Jobs queued, running or awaiting confirmation, by kind and state; a kind and "
        "state with none is left out"
    )
    webhookSubscriptions: SummarySubscriptions


class RehearsalRelease(BaseModel):
    id: str
    key: str
    version: str
    schemaVersion: str


class RehearsalWorkspace(BaseModel):
    """One active workspace of the restored copy."""

    workspaceKey: str
    release: RehearsalRelease | None = Field(description="The release it runs in the copy")
    state: Literal["served", "unavailable"]
    reason: Literal["unsupportedSchema", "invalid", "noRelease"] | None = Field(
        description="Why the engine could not serve it from the copy"
    )
    records: int
    relations: int = Field(description="Relationships whose source record is in the workspace")
    openChangeSets: int
    publications: int
    liveRecords: int = Field(description="The instance's records of the workspace when checked")


class RehearsalFailure(BaseModel):
    code: Literal[
        "DATABASE_UNREACHABLE",
        "DATABASE_URL_INVALID",
        "DATABASE_COLLATION",
        "DATABASE_EXTENSIONS",
        "DATABASE_REVISION_UNKNOWN",
        "DATABASE_MIGRATION_FAILED",
        "WORKSPACES_NOT_SERVED",
    ]
    message: str = Field(description="What a recovery from the backup would meet, and what to do")


class BackupRehearsalResponse(BaseModel):
    """A backup restored into a separate database and checked there (0.11 O2, D198–D200)."""

    id: str
    checkedAt: datetime
    backup: str | None = Field(description="The backup's name given to the check")
    dataAsOf: datetime | None = Field(description="The copy's newest change in the audit trail")
    revisionBefore: str | None = Field(description="The copy's migration revision as restored")
    revisionAfter: str | None = Field(description="Its revision once prepared; null if it was not")
    engineVersion: str
    host: str = Field(description="Where the check ran")
    result: Literal["passed", "failed"]
    failure: RehearsalFailure | None
    workspaces: list[RehearsalWorkspace]


class BackupRehearsalPage(CollectionPage[BackupRehearsalResponse]):
    pass
