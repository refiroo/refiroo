"""``GET /api/v1/system`` (0.9 U3): what the deployment runs, for anyone signed in, and
``GET /api/v1/system/configuration``: how it is configured, for operators once roles exist (0.12
D246). Read-only and behind no capability, like ``/capabilities``."""

from dataclasses import asdict
from datetime import UTC, datetime

from fastapi import APIRouter, Query, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy import select

from ...build_reference import build_reference
from ...common.pagination import datetime_key, paginate_statement, text_key
from ...common.prometheus import CONTENT_TYPE
from ...common.time import as_utc
from ...config import ENGINE_LICENSE, ENGINE_VERSION, get_settings
from ...engine.model.compiler import SCHEMA_VERSIONS
from ...engine.model.registry import (
    ModelRegistryUnavailable,
    WorkspaceModelUnavailable,
    model_registry,
)
from ...engine.processes.reads import live_processes, workspace_readiness
from ...engine.reads.system import read_system_state
from ...models.database import BackupRehearsal, EngineProcess, Workspace
from ..access import (
    INSTANCE,
    SIGNED_IN,
    AuthorizedRoute,
    requires,
)
from ..dependencies import DbSession
from ..paging import PageQuery
from ..projections import ai as ai_projection
from ..projections.operations import (
    metrics_text,
    process_response,
    readiness_response,
    rehearsal_response,
    summary_response,
)
from ..schemas.agent_access import McpSystemInfo
from ..schemas.system import (
    ActiveModelRelease,
    BackupRehearsalPage,
    BuildInfo,
    DatabaseInfo,
    EngineInfo,
    InstanceProduct,
    ProcessPage,
    SystemConfiguration,
    SystemResponse,
    SystemSetting,
    SystemSummary,
    WorkspaceReadinessPage,
)

router = APIRouter(route_class=AuthorizedRoute, prefix="/api/v1", tags=["system"])
# ``/metrics`` beside ``/health``, outside the management API's prefix (0.11 O1, D193, D197).
metrics_router = APIRouter(route_class=AuthorizedRoute, tags=["system"])


@router.get("/system", response_model=SystemResponse)
@requires("signed-in", at=SIGNED_IN)
def get_system(request: Request, session: DbSession) -> SystemResponse:
    state = read_system_state(session)
    release = state.active_release
    build = build_reference()
    return SystemResponse(
        engine=EngineInfo(
            version=ENGINE_VERSION,
            managementApi="v1",
            license=ENGINE_LICENSE,
            sourceCode=get_settings().source_code_url,
            build=BuildInfo(commit=build.commit, tag=build.tag),
        ),
        schemaLanguages=list(SCHEMA_VERSIONS),
        activeModelRelease=ActiveModelRelease(
            id=release.public_id,
            key=release.release_key,
            name=release.release_name,
            version=release.release_version,
            schemaVersion=release.schema_version,
            activatedAt=as_utc(state.activated_at),
        ),
        product=_instance_product(session),
        ai=ai_projection.system_info(request.app.state.ai),
        mcp=McpSystemInfo(enabled=request.app.state.identity_settings.agent_access),
    )


def _instance_product(session: DbSession) -> InstanceProduct | None:
    try:
        product = model_registry.resolve_workspace(session, None).model.product
    except WorkspaceModelUnavailable, ModelRegistryUnavailable:
        return None
    return InstanceProduct(name=product.name, description=product.description)


@router.get("/system/configuration", response_model=SystemConfiguration)
@requires("operations.read", at=INSTANCE)
def get_configuration(request: Request, session: DbSession) -> SystemConfiguration:
    """The database's migration revision and every setting with its value, its default and where
    the value came from; a secret shows neither (D246)."""
    return SystemConfiguration(
        database=DatabaseInfo(revision=read_system_state(session).revision),
        settings=[
            SystemSetting(**asdict(setting)) for setting in request.app.state.settings_report
        ],
    )


def _report_this_process(request: Request, session: DbSession) -> None:
    """Write this process's row first, so the asking process's own figures are current; the
    others' are as of their last heartbeat (0.11 O1, D192)."""
    heartbeat = getattr(request.app.state, "running_heartbeat", None)
    if heartbeat is not None:
        heartbeat.beat(session)
        session.commit()


@router.get("/system/processes", response_model=ProcessPage)
@requires("operations.read", at=INSTANCE)
def list_processes(
    request: Request,
    session: DbSession,
    paging: PageQuery,
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
) -> ProcessPage:
    """Every engine process on this database, as it last reported itself, in ID order (0.11 O1):
    live or silent, ready or not, its background threads, its pool, the releases it cannot serve
    and its counters."""
    _report_this_process(request, session)
    page = paginate_statement(
        session,
        select(EngineProcess),
        keys=(text_key("id", EngineProcess.process_id, "process_id"),),
        scope="system-processes",
        filters={},
        page=paging,
        page_size=page_size,
        message="Process cursor is invalid",
    )
    now = datetime.now(UTC)
    return ProcessPage(items=[process_response(row, now) for row in page.items], **page.links())


@router.get("/system/readiness", response_model=WorkspaceReadinessPage)
@requires("operations.read", at=INSTANCE)
def list_readiness(
    request: Request,
    session: DbSession,
    paging: PageQuery,
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
) -> WorkspaceReadinessPage:
    """Each active workspace, in key order, with its release and whether every live process
    serves it; the processes that cannot are named with why (0.11 O1)."""
    _report_this_process(request, session)
    page = paginate_statement(
        session,
        select(Workspace).where(Workspace.status == "active"),
        keys=(text_key("workspaceKey", Workspace.key, "key"),),
        scope="system-readiness",
        filters={},
        page=paging,
        page_size=page_size,
        message="Readiness cursor is invalid",
    )
    readiness = workspace_readiness(
        session, [item.key for item in page.items], live_processes(session)
    )
    return WorkspaceReadinessPage(
        items=[readiness_response(item) for item in readiness], **page.links()
    )


@router.get("/system/summary", response_model=SystemSummary)
@requires("operations.read", at=INSTANCE)
def get_summary(request: Request, session: DbSession) -> SystemSummary:
    """The instance's figures counted now: processes live and silent, workspaces served and
    unavailable, jobs waiting or running by kind, webhook subscriptions by state (0.11 O2). The
    same figures as ``/metrics``' instance gauges, as JSON."""
    _report_this_process(request, session)
    return summary_response(session)


@router.get("/system/backup-rehearsals", response_model=BackupRehearsalPage)
@requires("operations.read", at=INSTANCE)
def list_backup_rehearsals(
    session: DbSession,
    paging: PageQuery,
    page_size: int = Query(default=20, ge=1, le=200, alias="pageSize"),
) -> BackupRehearsalPage:
    """Backups restored into a separate database and checked there with ``python -m
    app.cli.restore_check``, newest first, passed or failed, each with every workspace of the copy
    (0.11 O2)."""
    page = paginate_statement(
        session,
        select(BackupRehearsal),
        keys=(
            datetime_key("checkedAt", BackupRehearsal.checked_at, "checked_at", descending=True),
            text_key("id", BackupRehearsal.public_id, "public_id", descending=True),
        ),
        scope="system-backup-rehearsals",
        filters={},
        page=paging,
        page_size=page_size,
        message="Backup rehearsal cursor is invalid",
    )
    return BackupRehearsalPage(
        items=[rehearsal_response(row) for row in page.items], **page.links()
    )


@metrics_router.get(
    "/metrics",
    response_class=PlainTextResponse,
    responses={200: {"content": {"text/plain": {}}, "description": "Prometheus text format 0.0.4"}},
)
@requires("operations.read", at=INSTANCE)
def get_metrics(request: Request, session: DbSession) -> PlainTextResponse:
    """The instance's metrics in the Prometheus text format: every live process's series labelled
    ``process``, and the jobs, webhook subscriptions, processes and unavailable workspaces counted
    now (0.11 O1). One scrape covers every worker and node."""
    _report_this_process(request, session)
    return PlainTextResponse(metrics_text(session), media_type=CONTENT_TYPE)
