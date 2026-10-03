import logging
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

from .config import Settings, get_settings, reload_settings
from .db import DatabaseStartupError, SessionLocal, create_database, get_engine
from .engine.indexes.matrix_states import build_at_startup as build_matrix_states
from .engine.jobs.inline import BatchLimits
from .engine.jobs.worker import JobWorker, WorkerSettings
from .engine.model.bootstrap import bootstrap_model
from .engine.model.compiler import SUPPORTED_SCHEMA_VERSIONS
from .engine.model.loader import load_bootstrap_model
from .engine.model.registry import UnsupportedSelectedModelSchema, model_registry
from .errors import ApiError
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
    change_sets,
    jobs,
    mapping,
    model,
    model_management,
    model_releases,
    objects,
    queries,
    relation_matrix,
    relations,
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
    try:
        create_database()
    except DatabaseStartupError as exc:
        model_registry.mark_unhealthy()
        logger.error("%s", exc)
        yield
        return
    bootstrap_model(loaded_model)
    with SessionLocal() as session:
        try:
            model_registry.resolve_active(session)
            build_matrix_states(session)
        except UnsupportedSelectedModelSchema as exc:
            model_registry.mark_unhealthy()
            logger.error(
                "RDM Engine cannot serve model-backed requests: the database selects schema %s, "
                f"but this version supports schema {', '.join(sorted(SUPPORTED_SCHEMA_VERSIONS))}.\n"
                "Stop all RDM Engine processes using this database, run this exact command in the "
                "same configured environment, then restart the API:\n  %s\n"
                "Until the transition succeeds, /health returns HTTP 503.",
                exc.schema_version,
                schema_upgrade_command(get_settings()),
            )
    # A process that cannot serve the model runs no jobs: each chunk would fail its job.
    worker = application.state.job_worker if application.state.run_job_worker else None
    if worker is not None and not model_registry.ready:
        worker = None
    if worker is not None:
        worker.start()
    try:
        yield
    finally:
        if worker is not None:
            worker.stop()


def create_app() -> FastAPI:
    settings = reload_settings()
    settings.validate_model_admin_topology()
    mutations_enabled = settings.model_admin_mutations_enabled
    workspace_mutations_enabled = settings.workspace_admin_mutations_enabled
    application = FastAPI(
        title="RDM Engine API",
        version="0.9.0-alpha.1",
        description="API-first, model-driven reference data management engine.",
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
                                        "code": "invalid_cursor",
                                        "message": "Cursor is invalid",
                                    }
                                },
                            },
                            "versionConflict": {
                                "summary": "Optimistic concurrency claim is stale",
                                "value": {
                                    "error": {
                                        "code": "version_conflict",
                                        "message": "Object version has changed",
                                    }
                                },
                            },
                            "requestValidation": {
                                "summary": "Request body or parameters are invalid",
                                "value": {
                                    "error": {
                                        "code": "request_validation_error",
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
    application.state.workspace_admin_mutations_enabled = workspace_mutations_enabled
    application.state.integration_jobs_enabled = settings.integration_jobs_enabled
    application.state.batch_limits = BatchLimits(
        max_items=settings.batch_max_items,
        max_bytes=settings.batch_max_bytes,
        atomic_max_items=settings.atomic_job_max_items,
        retention_days=settings.job_retention_days,
        background_max_items=settings.background_job_max_items,
        background_max_bytes=settings.batch_background_max_bytes,
        chunk_items=settings.job_chunk_items,
    )
    # The in-process job worker (P6): none with the capability off. Tests that drive the worker
    # themselves set ``run_job_worker`` to False before the application starts.
    application.state.job_worker = (
        JobWorker(
            SessionLocal,
            WorkerSettings(
                chunk_items=settings.job_chunk_items,
                lease_seconds=settings.job_lease_seconds,
                retention_days=settings.job_retention_days,
            ),
        )
        if settings.integration_jobs_enabled
        else None
    )
    application.state.run_job_worker = True
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
    )

    @application.get("/health")
    def health(response: Response) -> dict[str, str]:
        if not model_registry.ready or not database_reachable():
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return {"status": "unhealthy"}
        return {"status": "ok"}

    application.include_router(api_reference_router(settings.api_reference_script))
    application.include_router(model.router)
    application.include_router(model_releases.router)
    application.include_router(workspaces.read_router)
    if workspace_mutations_enabled:
        application.include_router(workspaces.admin_router)
    application.include_router(change_sets.router)
    if mutations_enabled:
        application.include_router(model_management.router)
    application.include_router(objects.router)
    application.include_router(queries.router)
    application.include_router(attributes.router)
    application.include_router(relations.router)
    application.include_router(mapping.router)
    application.include_router(relation_matrix.router)
    application.include_router(jobs.router)
    if settings.integration_jobs_enabled:
        application.include_router(jobs.write_router)
    return application


app = create_app()
