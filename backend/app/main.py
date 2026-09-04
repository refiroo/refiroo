from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import cors_origins, model_admin_mutations_enabled
from .db import SessionLocal, bootstrap_model, create_database
from .errors import (
    ApiError,
    api_error_handler,
    http_error_handler,
    unexpected_error_handler,
    validation_error_handler,
)
from .routers import attributes, model, model_management, objects, relations
from .services.model_loader import load_bootstrap_model
from .services.model_registry import model_registry


@asynccontextmanager
async def lifespan(_: FastAPI):
    loaded_model = load_bootstrap_model()
    create_database()
    bootstrap_model(loaded_model)
    with SessionLocal() as session:
        model_registry.resolve_active(session)
    yield


def create_app() -> FastAPI:
    mutations_enabled = model_admin_mutations_enabled()
    application = FastAPI(
        title="RDM Engine API",
        version="0.3.0",
        description="API-first, model-driven reference data management engine.",
        lifespan=lifespan,
    )
    application.state.model_admin_mutations_enabled = mutations_enabled
    application.add_exception_handler(ApiError, api_error_handler)
    application.add_exception_handler(RequestValidationError, validation_error_handler)
    application.add_exception_handler(StarletteHTTPException, http_error_handler)
    application.add_exception_handler(Exception, unexpected_error_handler)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    application.include_router(model.router)
    if mutations_enabled:
        application.include_router(model_management.router)
    application.include_router(objects.router)
    application.include_router(relations.router)
    application.include_router(attributes.router)
    return application


app = create_app()
