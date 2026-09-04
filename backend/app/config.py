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


def model_admin_mutations_enabled() -> bool:
    return os.getenv("MODEL_ADMIN_MUTATIONS_ENABLED", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def validate_model_admin_topology(mutations_enabled: bool) -> None:
    """Reject model mutations when Uvicorn is configured with multiple workers."""
    if not mutations_enabled:
        return
    raw_worker_count = os.getenv("WEB_CONCURRENCY", "1").strip()
    try:
        worker_count = int(raw_worker_count)
    except ValueError as exc:
        raise RuntimeError("WEB_CONCURRENCY must be a positive integer") from exc
    if worker_count < 1:
        raise RuntimeError("WEB_CONCURRENCY must be a positive integer")
    if worker_count != 1:
        raise RuntimeError(
            "MODEL_ADMIN_MUTATIONS_ENABLED requires WEB_CONCURRENCY=1 until "
            "cross-process model release propagation is implemented"
        )


def cors_origins() -> list[str]:
    raw = os.environ.get("CORS_ORIGINS", "http://localhost:5173")
    return [origin.strip() for origin in raw.split(",")]
