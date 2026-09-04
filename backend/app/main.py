from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import cors_origins
from .db import SessionLocal, bootstrap_model, create_database
from .errors import (
    ApiError,
    api_error_handler,
    http_error_handler,
    unexpected_error_handler,
    validation_error_handler,
)
from .routers import attributes, model, objects, relations
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


app = FastAPI(
    title="RDM Engine API",
    version="0.3.0",
    description="API-first, model-driven reference data management engine.",
    lifespan=lifespan,
)
app.add_exception_handler(ApiError, api_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(StarletteHTTPException, http_error_handler)
app.add_exception_handler(Exception, unexpected_error_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(model.router)
app.include_router(objects.router)
app.include_router(relations.router)
app.include_router(attributes.router)
