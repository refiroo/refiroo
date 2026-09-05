from contextlib import asynccontextmanager

from fastapi import FastAPI, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import reload_settings
from .db import SessionLocal, create_database
from .errors import (
    ApiError,
    api_error_handler,
    http_error_handler,
    unexpected_error_handler,
    validation_error_handler,
)
from .models.api import ApiErrorResponse
from .routers import attributes, model, model_management, model_releases, objects, relations
from .services.model.bootstrap import bootstrap_model
from .services.model.loader import load_bootstrap_model
from .services.model.registry import model_registry


@asynccontextmanager
async def lifespan(_: FastAPI):
    loaded_model = load_bootstrap_model()
    create_database()
    bootstrap_model(loaded_model)
    with SessionLocal() as session:
        model_registry.resolve_active(session)
    yield


def create_app() -> FastAPI:
    settings = reload_settings()
    settings.validate_model_admin_topology()
    mutations_enabled = settings.model_admin_mutations_enabled
    application = FastAPI(
        title="RDM Engine API",
        version="0.3.0",
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
    if mutations_enabled:
        application.include_router(model_management.router)
    application.include_router(objects.router)
    application.include_router(relations.router)
    application.include_router(attributes.router)
    return application


app = create_app()
