import logging
import shlex
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import Settings, get_settings, reload_settings
from .db import DatabaseMigrationError, SessionLocal, create_database
from .engine.indexes.matrix_states import build_at_startup as build_matrix_states
from .engine.model.bootstrap import bootstrap_model
from .engine.model.loader import load_bootstrap_model
from .engine.model.registry import UnsupportedSelectedModelSchema, model_registry
from .errors import ApiError
from .management.errors import (
    api_error_handler,
    http_error_handler,
    unexpected_error_handler,
    validation_error_handler,
)
from .management.routers import (
    attributes,
    change_sets,
    mapping,
    model,
    model_management,
    model_releases,
    objects,
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


@asynccontextmanager
async def lifespan(_: FastAPI):
    loaded_model = load_bootstrap_model()
    try:
        create_database()
    except DatabaseMigrationError as exc:
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
                "but this version supports schema 0.5, 0.6 and 0.7.\n"
                "Stop all RDM Engine processes using this database, run this exact command in the "
                "same configured environment, then restart the API:\n  %s\n"
                "Until the transition succeeds, /health returns HTTP 503.",
                exc.schema_version,
                schema_upgrade_command(get_settings()),
            )
    yield


def create_app() -> FastAPI:
    settings = reload_settings()
    settings.validate_model_admin_topology()
    mutations_enabled = settings.model_admin_mutations_enabled
    workspace_mutations_enabled = settings.workspace_admin_mutations_enabled
    application = FastAPI(
        title="RDM Engine API",
        version="0.8.0",
        description="API-first, model-driven reference data management engine.",
        lifespan=lifespan,
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
        if not model_registry.ready:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return {"status": "unhealthy"}
        return {"status": "ok"}

    application.include_router(model.router)
    application.include_router(model_releases.router)
    application.include_router(workspaces.read_router)
    if workspace_mutations_enabled:
        application.include_router(workspaces.admin_router)
    application.include_router(change_sets.router)
    if mutations_enabled:
        application.include_router(model_management.router)
    application.include_router(objects.router)
    application.include_router(attributes.router)
    application.include_router(relations.router)
    application.include_router(mapping.router)
    application.include_router(relation_matrix.router)
    return application


app = create_app()
