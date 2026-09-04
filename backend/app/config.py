import os
import secrets
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_EPHEMERAL_CURSOR_SIGNING_KEY = secrets.token_bytes(32)


def model_path() -> Path:
    configured = os.getenv("RDM_MODEL_PATH")
    return Path(configured) if configured else PROJECT_ROOT / "model" / "rdm-starter.json"


def database_url() -> str:
    return os.getenv("DATABASE_URL", "sqlite:///./rdm-engine.db")


def cursor_signing_key() -> bytes:
    configured = os.getenv("RDM_CURSOR_SIGNING_KEY")
    return configured.encode() if configured else _EPHEMERAL_CURSOR_SIGNING_KEY


def cors_origins() -> list[str]:
    raw = os.environ.get("CORS_ORIGINS", "http://localhost:5173")
    return [origin.strip() for origin in raw.split(",")]
