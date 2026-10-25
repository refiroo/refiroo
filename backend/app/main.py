import logging
import os
import shlex
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .common.logs import configure_logging
from .common.request_observation import REQUEST_ID_HEADER, RequestObservation
from .config import ENGINE_VERSION, Settings, describe_settings, get_settings, reload_settings
from .consumer import router as consumer_router
from .db import DatabaseStartupError, SessionLocal, create_database, get_engine, libpq_url
from .engine.events.dispatcher import THREAD_NAME as DISPATCHER_THREAD
from .engine.events.dispatcher import EventDispatcher
from .engine.events.subscriptions import SubscriptionSettings
from .engine.events.worker import THREAD_NAME as DERIVER_THREAD
from .engine.events.worker import EventDeriver
from .engine.identity.settings import IdentitySettings
from .engine.indexes.matrix_states import build_at_startup as build_matrix_states
from .engine.jobs.events import THREAD_NAME as LISTENER_THREAD
from .engine.jobs.events import JobListener
from .engine.jobs.files import JobFiles
from .engine.jobs.inline import BatchLimits
from .engine.jobs.worker import EXPORT_KINDS, EXPORT_THREAD_NAME, JobWorker, WorkerSettings
from .engine.model.bootstrap import bootstrap_model
from .engine.model.compiler import SCHEMA_VERSIONS, after_window
from .engine.model.loader import load_bootstrap_model
from .engine.model.registry import model_registry
from .engine.model.workspace_models import workspaces_running
from .engine.processes.heartbeat import ProcessHeartbeat
from .errors import ApiError
from .management.access import MANAGEMENT_DEPENDENCIES
from .management.brand_assets import brand_router
from .management.errors import (
    api_error_handler,
    http_error_handler,
    unexpected_error_handler,
    validation_error_handler,
)
from .management.query_parameters import refuse_unknown_parameters
from .management.reference import api_reference_router
from .management.routers import (
    attributes,
    authorization,
    change_sets,
    changes,
    consumer_subscriptions,
    identity,
    imports,
    inference,
    jobs,
    mapping,
    model,
    model_management,
    model_mappings,
    model_releases,
    moves,
    oauth,
    oauth_console,
    objects,
    queries,
    relation_matrix,
    relations,
    source_files,
    system,
    workspaces,
)
from .management.schemas.common import ApiErrorResponse

logger = logging.getLogger(__name__)


def schema_upgrade_command(settings: Settings) -> str:
    backend_path = Path(__file__).resolve().parents[1]
    command = shlex.join(
        [
            sys.executable,
            "-m",
            "app.cli.model_schema_upgrade",
            "--model",
            str(settings.model_path.resolve()),
        ]
    )
    return f"cd {shlex.quote(str(backend_path))} && {command}"


def database_reachable() -> bool:
    """Whether the database answers now: a process that serves no request without it is not ready
    while it is unreachable (H4c, J12.8). Requests answer it concisely, and nothing is logged here,
    since a probe asks often."""
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError, DatabaseStartupError:
        return False
    return True


@asynccontextmanager
async def lifespan(application: FastAPI):
    loaded_model = load_bootstrap_model()

    def startup_writes() -> None:
        bootstrap_model(loaded_model)
        # Processes starting together build the matrix states one at a time, each after the first
        # finding them built (0.11 O1: they collided on the build's unique key before).
        with SessionLocal() as session:
            build_matrix_states(session)

    try:
        # The bootstrap install runs under the startup lock too (0.11 N1, D168).
        create_database(then=startup_writes)
    except DatabaseStartupError as exc:
        model_registry.mark_unhealthy()
        # Maintenance mode: no route reads the database, a token included (0.12 I1).
        application.state.maintenance = True
        logger.error("%s", exc)
        yield
        return
    with SessionLocal() as session:
        # A release this version cannot serve makes only its workspaces unavailable (0.11 D29).
        unavailable_releases = model_registry.start(session)
        consequence = (
            "Until this is resolved, their requests answer HTTP 503; other workspaces are served."
            if model_registry.ready
            else "Until this is resolved, /health returns HTTP 503."
        )
        for unavailable in unavailable_releases:
            workspaces = ", ".join(workspaces_running(session, unavailable.release_db_id))
            if unavailable.unsupported_schema and after_window(unavailable.schema_version):
                # A later engine wrote this release; no command of this version can read it (D101).
                logger.error(
                    "RDM Engine cannot serve workspaces %s: they run model release %s of schema "
                    f"%s, but this version supports schema {', '.join(SCHEMA_VERSIONS)}.\n"
                    "This database was used by a later RDM Engine. Start that version to serve these "
                    "workspaces, or migrate them there to a release of a supported schema before "
                    "starting this version again.\n%s",
                    workspaces,
                    unavailable.release_id,
                    unavailable.schema_version,
                    consequence,
                )
            elif unavailable.unsupported_schema:
                logger.error(
                    "RDM Engine cannot serve workspaces %s: they run model release %s of schema "
                    f"%s, but this version supports schema {', '.join(SCHEMA_VERSIONS)}.\n"
                    "Stop all RDM Engine processes using this database, run this exact command in "
                    "the same configured environment, then restart the API:\n  %s\n%s",
                    workspaces,
                    unavailable.release_id,
                    unavailable.schema_version,
                    schema_upgrade_command(get_settings()),
                    consequence,
                )
            else:
                logger.error(
                    "RDM Engine cannot serve workspaces %s: their model release %s is invalid "
                    "(%d diagnostics). %s",
                    workspaces,
                    unavailable.release_id,
                    len(unavailable.diagnostics),
                    consequence,
                )
    # A process that can serve no workspace's model runs no jobs: each chunk would fail its job.
    worker = application.state.job_worker if application.state.run_job_worker else None
    exporter = application.state.export_worker if application.state.run_job_worker else None
    if not model_registry.ready:
        worker = exporter = None
    if worker is not None:
        # Files a stopped process left behind: partial ones, or a finished job's (D55).
        with SessionLocal() as session:
            application.state.job_files.reconcile(session)
        worker.start()
    if exporter is not None:
        exporter.start()
    listener = application.state.job_listener if application.state.run_job_listener else None
    if listener is not None and not model_registry.ready:
        listener = None
    if listener is not None:
        listener.start()
    # The event deriver (C10) runs where the model can be served, as the job worker does.
    deriver = application.state.event_deriver if application.state.run_event_deriver else None
    if deriver is not None and not model_registry.ready:
        deriver = None
    if deriver is not None:
        deriver.start()
    # The webhook dispatcher (C12): only with subscriptions on (C-D102), where the model is served.
    dispatcher = (
        application.state.consumer_dispatcher if application.state.run_consumer_dispatcher else None
    )
    if dispatcher is not None and not model_registry.ready:
        dispatcher = None
    if dispatcher is not None:
        dispatcher.start()
    # Each process reports itself to the others, ready or not (0.11 O1, D192).
    heartbeat = (
        application.state.process_heartbeat if application.state.run_process_heartbeat else None
    )
    if heartbeat is not None:
        heartbeat.started_threads = {
            name
            for name, thread in (
                (worker.thread_name if worker else "", worker),
                (exporter.thread_name if exporter else "", exporter),
                (LISTENER_THREAD, listener),
                (DERIVER_THREAD, deriver),
                (DISPATCHER_THREAD, dispatcher),
            )
            if thread is not None
        }
        heartbeat.start()
        application.state.running_heartbeat = heartbeat
    try:
        yield
    finally:
        if heartbeat is not None:
            application.state.running_heartbeat = None
            heartbeat.stop()
        if dispatcher is not None:
            dispatcher.stop()
        if deriver is not None:
            deriver.stop()
        if listener is not None:
            listener.stop()
        if exporter is not None:
            exporter.stop()
        if worker is not None:
            worker.stop()


def create_app() -> FastAPI:
    settings = reload_settings()
    configure_logging(settings.log_format, settings.log_level)
    settings.validate_secrets()
    settings.prepare_job_file_dir()
    mutations_enabled = settings.model_admin_mutations_enabled
    workspace_mutations_enabled = settings.workspace_admin_mutations_enabled
    application = FastAPI(
        title="refiroo API",
        version=ENGINE_VERSION,
        description="The API of refiroo, an application built on the RDM engine: API-first, model-driven reference data management.",
        lifespan=lifespan,
        # Every route accepts only the query parameters it declares (D-3).
        dependencies=[Depends(refuse_unknown_parameters)],
        # /docs is the Scalar reference page (api_reference_router), not Swagger UI or ReDoc.
        docs_url=None,
        redoc_url=None,
        swagger_ui_oauth2_redirect_url=None,
        responses={
            "default": {
                "model": ApiErrorResponse,
                "description": "Structured API error",
                "content": {
                    "application/json": {
                        "examples": {
                            "invalidCursor": {
                                "summary": "Cursor does not match this collection request",
                                "value": {
                                    "error": {
                                        "code": "INVALID_CURSOR",
                                        "message": "Cursor is invalid",
                                    }
                                },
                            },
                            "versionConflict": {
                                "summary": "Optimistic concurrency claim is stale",
                                "value": {
                                    "error": {
                                        "code": "VERSION_CONFLICT",
                                        "message": "Object version has changed",
                                    }
                                },
                            },
                            "requestValidation": {
                                "summary": "Request body or parameters are invalid",
                                "value": {
                                    "error": {
                                        "code": "REQUEST_VALIDATION_ERROR",
                                        "message": "Request validation failed",
                                        "details": [],
                                    }
                                },
                            },
                        }
                    }
                },
            }
        },
    )
    application.state.model_admin_mutations_enabled = mutations_enabled
    application.state.maintenance = False
    application.state.workspace_admin_mutations_enabled = workspace_mutations_enabled
    application.state.integration_jobs_enabled = settings.integration_jobs_enabled
    application.state.consumer_resolve_max_items = settings.consumer_resolve_max_items
    application.state.consumer_subscriptions_enabled = settings.consumer_subscriptions_enabled
    application.state.consumer_webhook_log_retention_days = (
        settings.consumer_webhook_log_retention_days
    )
    assert settings.secrets_encryption_key is not None
    # Tokens (0.12 I1, ADR-043): their issuer, lifetime and signing keys.
    application.state.identity_settings = IdentitySettings(
        encryption_key=settings.secrets_encryption_key,
        issuer=settings.public_url,
        access_token_seconds=settings.access_token_minutes * 60,
        signing_key_days=settings.token_signing_key_days,
        browser_origins=settings.cors_origins,
        session_idle_hours=settings.session_idle_hours,
        session_days=settings.session_days,
        password_reset_hours=settings.password_reset_hours,
        password_min_length=settings.password_min_length,
    )
    application.state.subscription_settings = (
        SubscriptionSettings(
            encryption_key=settings.secrets_encryption_key,
            retention_days=settings.feed_retention_days,
            log_retention_days=settings.consumer_webhook_log_retention_days,
        )
        if settings.consumer_subscriptions_enabled
        else None
    )
    application.state.batch_limits = BatchLimits(
        max_items=settings.batch_max_items,
        max_bytes=settings.batch_max_bytes,
        atomic_max_items=settings.atomic_job_max_items,
        retention_days=settings.job_retention_days,
        background_max_items=settings.background_job_max_items,
        background_max_bytes=settings.batch_background_max_bytes,
        chunk_items=settings.job_chunk_items,
        import_max_bytes=settings.import_max_bytes,
        preview_max_items=settings.job_preview_max_items,
    )
    # The in-process job worker (P6): none with the capability off. Tests that drive the worker
    # themselves set ``run_job_worker`` to False before the application starts.
    # Export files (0.9 J1, D55); served by GET /jobs/{id}/output whatever the capability.
    application.state.model_operation_max_items = settings.model_operation_max_items
    application.state.job_files = JobFiles(settings.job_file_dir)
    worker_settings = WorkerSettings(
        chunk_items=settings.job_chunk_items,
        lease_seconds=settings.job_lease_seconds,
        retention_days=settings.job_retention_days,
        atomic_max_items=settings.atomic_job_max_items,
        background_max_items=settings.background_job_max_items,
        preview_max_items=settings.job_preview_max_items,
        inference_assistant=settings.inference_assistant,
        inference_assistant_rows=settings.inference_assistant_rows,
    )
    application.state.job_worker = (
        JobWorker(SessionLocal, worker_settings, files=application.state.job_files)
        if settings.integration_jobs_enabled
        else None
    )
    # Exports run on a worker of their own, so neither kind waits behind the other (D53).
    application.state.export_worker = (
        JobWorker(
            SessionLocal,
            worker_settings,
            kinds=EXPORT_KINDS,
            files=application.state.job_files,
            sweeps=False,
            thread_name=EXPORT_THREAD_NAME,
        )
        if settings.integration_jobs_enabled
        else None
    )
    application.state.run_job_worker = True
    # The job event stream's listener (0.9 J1u, D58): it only listens, so tests keep it running.
    application.state.session_factory = SessionLocal
    # It also wakes this process's workers when any process queues or changes a job (0.11 N2).
    workers = [w for w in (application.state.job_worker, application.state.export_worker) if w]

    def wake_workers() -> None:
        for worker in workers:
            worker.wake()

    application.state.job_listener = JobListener(libpq_url, wake_workers)
    application.state.run_job_listener = True
    application.state.feed_retention_days = settings.feed_retention_days
    # The consumer event deriver (C10). Tests that derive themselves set ``run_event_deriver`` to
    # False before the application starts.
    application.state.event_deriver = EventDeriver(
        SessionLocal, retention_days=settings.feed_retention_days
    )
    application.state.run_event_deriver = True
    # The webhook dispatcher (C12): none with the subscriptions capability off (C-D102). Tests that
    # dispatch themselves set ``run_consumer_dispatcher`` to False before the application starts.
    application.state.consumer_dispatcher = (
        EventDispatcher(SessionLocal, application.state.subscription_settings)
        if application.state.subscription_settings is not None
        else None
    )
    application.state.run_consumer_dispatcher = True
    # The process heartbeat (0.11 O1): tests that report themselves set ``run_process_heartbeat``
    # to False before the application starts.
    application.state.process_heartbeat = ProcessHeartbeat(
        SessionLocal, settings.process_heartbeat_seconds
    )
    application.state.run_process_heartbeat = True
    application.state.running_heartbeat = None
    # What GET /system reports: the settings as this process read them, fixed until a restart (U-D2).
    application.state.settings_report = describe_settings(settings, os.environ)
    application.add_exception_handler(ApiError, api_error_handler)
    application.add_exception_handler(RequestValidationError, validation_error_handler)
    application.add_exception_handler(StarletteHTTPException, http_error_handler)
    application.add_exception_handler(Exception, unexpected_error_handler)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        # A browser on another origin reads the release a model came from, to name it on its
        # writes (0.11 M6a, D65).
        expose_headers=["X-Model-Release-Id", REQUEST_ID_HEADER],
    )
    # Outermost: every request named, counted, timed and logged once (0.11 O1, D194–D196).
    application.add_middleware(RequestObservation)

    @application.get("/health")
    def health(response: Response) -> dict[str, str]:
        if not model_registry.ready or not database_reachable():
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return {"status": "unhealthy"}
        return {"status": "ok"}

    @application.get("/health/live")
    def live() -> dict[str, str]:
        """The process answers; asks nothing else, so a database outage restarts no process
        (0.11 O1, D191). Readiness is ``/health``."""
        return {"status": "ok"}

    application.include_router(api_reference_router(settings.api_reference_script))
    application.include_router(brand_router())
    # The OAuth endpoints need no token (D245); every management router below needs one.
    application.include_router(oauth.router)
    application.include_router(oauth_console.router)
    application.include_router(identity.router, dependencies=MANAGEMENT_DEPENDENCIES)
    application.include_router(authorization.router, dependencies=MANAGEMENT_DEPENDENCIES)
    application.include_router(model.router, dependencies=MANAGEMENT_DEPENDENCIES)
    application.include_router(system.router, dependencies=MANAGEMENT_DEPENDENCIES)
    application.include_router(system.metrics_router, dependencies=MANAGEMENT_DEPENDENCIES)
    application.include_router(model_releases.router, dependencies=MANAGEMENT_DEPENDENCIES)
    application.include_router(workspaces.read_router, dependencies=MANAGEMENT_DEPENDENCIES)
    if workspace_mutations_enabled:
        application.include_router(workspaces.admin_router, dependencies=MANAGEMENT_DEPENDENCIES)
    application.include_router(change_sets.router, dependencies=MANAGEMENT_DEPENDENCIES)
    application.include_router(changes.router, dependencies=MANAGEMENT_DEPENDENCIES)
    if mutations_enabled:
        application.include_router(model_management.router, dependencies=MANAGEMENT_DEPENDENCIES)
    application.include_router(objects.router, dependencies=MANAGEMENT_DEPENDENCIES)
    application.include_router(queries.router, dependencies=MANAGEMENT_DEPENDENCIES)
    application.include_router(attributes.router, dependencies=MANAGEMENT_DEPENDENCIES)
    application.include_router(relations.router, dependencies=MANAGEMENT_DEPENDENCIES)
    application.include_router(mapping.router, dependencies=MANAGEMENT_DEPENDENCIES)
    application.include_router(relation_matrix.router, dependencies=MANAGEMENT_DEPENDENCIES)
    application.include_router(jobs.router, dependencies=MANAGEMENT_DEPENDENCIES)
    application.include_router(imports.router, dependencies=MANAGEMENT_DEPENDENCIES)
    application.include_router(source_files.router, dependencies=MANAGEMENT_DEPENDENCIES)
    application.include_router(model_mappings.router, dependencies=MANAGEMENT_DEPENDENCIES)
    if settings.integration_jobs_enabled:
        application.include_router(jobs.write_router, dependencies=MANAGEMENT_DEPENDENCIES)
        application.include_router(imports.write_router, dependencies=MANAGEMENT_DEPENDENCIES)
        application.include_router(
            model_mappings.write_router, dependencies=MANAGEMENT_DEPENDENCIES
        )
        application.include_router(source_files.write_router, dependencies=MANAGEMENT_DEPENDENCIES)
        application.include_router(
            change_sets.migration_router, dependencies=MANAGEMENT_DEPENDENCIES
        )
        if mutations_enabled:
            application.include_router(
                source_files.dry_run_router, dependencies=MANAGEMENT_DEPENDENCIES
            )
            application.include_router(inference.router, dependencies=MANAGEMENT_DEPENDENCIES)
            application.include_router(moves.router, dependencies=MANAGEMENT_DEPENDENCIES)
            application.include_router(
                model_management.migration_router, dependencies=MANAGEMENT_DEPENDENCIES
            )
    if settings.consumer_subscriptions_enabled:
        application.include_router(
            consumer_subscriptions.router, dependencies=MANAGEMENT_DEPENDENCIES
        )
    application.include_router(consumer_router.router)
    return application


app = create_app()
