from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import cors_origins
from .db import create_database, install_model
from .routers import model, objects, relations
from .services.model_loader import current_model


@asynccontextmanager
async def lifespan(_: FastAPI):
    loaded_model = current_model()
    create_database()
    install_model(loaded_model)
    yield


app = FastAPI(
    title="RDM Engine API",
    version="0.3.0",
    description="API-first, model-driven reference data management engine.",
    lifespan=lifespan,
)
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
