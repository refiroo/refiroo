"""Process configuration, read from the environment into one validated object.

``get_settings`` caches, so configuration is parsed and validated once rather than re-read on every
access. Building an application re-reads it through :func:`reload_settings`, which is what lets a
test change the environment and construct a differently configured app in the same process.
"""

import os
import secrets
from collections.abc import Mapping
from functools import cache
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL_PATH = PROJECT_ROOT / "model" / "rdm-starter.json"
DEFAULT_CORS_ORIGINS = "http://localhost:5173"

TRUTHY = {"1", "true", "yes", "on"}

# Where the API reference page at /docs loads its script from: the copy bundled with the engine, so
# the page works without internet access, or the same pinned version from a CDN.
ApiReferenceScript = Literal["bundled", "cdn"]
API_REFERENCE_SCRIPTS: tuple[ApiReferenceScript, ...] = ("bundled", "cdn")

# Regenerating this per process is deliberate: without RDM_CURSOR_SIGNING_KEY, cursors issued
# before a restart stop verifying after it. It is generated once at import so reloading settings
# does not invalidate cursors this process has already handed out.
_EPHEMERAL_CURSOR_SIGNING_KEY = secrets.token_bytes(32)


class Settings(BaseModel):
    """Validated view of the environment this process runs under."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    # The PostgreSQL URL (PG-D2); required, and checked at startup (``db.check_database_url``) so a
    # missing or non-PostgreSQL URL is refused with an instruction rather than a traceback.
    database_url: str | None = None
    model_path: Path = DEFAULT_MODEL_PATH
    cors_origins: tuple[str, ...] = (DEFAULT_CORS_ORIGINS,)
    model_admin_mutations_enabled: bool = False
    workspace_admin_mutations_enabled: bool = True
    web_concurrency: int = Field(default=1, ge=1)
    cursor_signing_key: bytes = _EPHEMERAL_CURSOR_SIGNING_KEY
    api_reference_script: ApiReferenceScript = "bundled"
    # Job creation (bulk writes, imports, exports) as a deployment capability group (ADR-036, D10).
    integration_jobs_enabled: bool = True
    # Batch and job limits (D13) and retention (D14); reported by GET /capabilities.
    batch_max_items: int = Field(default=1_000, ge=1)
    batch_max_bytes: int = Field(default=5 * 1024 * 1024, ge=1)
    atomic_job_max_items: int = Field(default=10_000, ge=1)
    job_retention_days: int = Field(default=7, ge=1)
    # Background jobs (P6): their item and body limits (D13, §B1), the items one chunk commits and
    # the worker's lease on a job, renewed with each chunk (D30).
    background_job_max_items: int = Field(default=1_000_000, ge=1)
    batch_background_max_bytes: int = Field(default=50 * 1024 * 1024, ge=1)
    job_chunk_items: int = Field(default=500, ge=1)
    job_lease_seconds: int = Field(default=120, ge=1)

    @classmethod
    def from_env(cls, environ: dict[str, str] | None = None) -> Self:
        env = os.environ if environ is None else environ
        configured_model_path = env.get("RDM_MODEL_PATH")
        configured_signing_key = env.get("RDM_CURSOR_SIGNING_KEY")
        return cls(
            database_url=env.get("DATABASE_URL", "").strip() or None,
            model_path=Path(configured_model_path) if configured_model_path else DEFAULT_MODEL_PATH,
            cors_origins=tuple(
                origin.strip()
                for origin in env.get("CORS_ORIGINS", DEFAULT_CORS_ORIGINS).split(",")
            ),
            model_admin_mutations_enabled=(
                env.get("MODEL_ADMIN_MUTATIONS_ENABLED", "false").strip().lower() in TRUTHY
            ),
            workspace_admin_mutations_enabled=(
                env.get("WORKSPACE_ADMIN_MUTATIONS_ENABLED", "true").strip().lower() in TRUTHY
            ),
            web_concurrency=_worker_count(env.get("WEB_CONCURRENCY", "1")),
            cursor_signing_key=(
                configured_signing_key.encode()
                if configured_signing_key
                else _EPHEMERAL_CURSOR_SIGNING_KEY
            ),
            api_reference_script=_api_reference_script(
                env.get("RDM_API_REFERENCE_SCRIPT", "bundled")
            ),
            integration_jobs_enabled=(
                env.get("INTEGRATION_JOBS_ENABLED", "true").strip().lower() in TRUTHY
            ),
            batch_max_items=_positive(env, "BATCH_MAX_ITEMS", 1_000),
            batch_max_bytes=_positive(env, "BATCH_MAX_BYTES", 5 * 1024 * 1024),
            atomic_job_max_items=_positive(env, "ATOMIC_JOB_MAX_ITEMS", 10_000),
            job_retention_days=_positive(env, "JOB_RETENTION_DAYS", 7),
            background_job_max_items=_positive(env, "BACKGROUND_JOB_MAX_ITEMS", 1_000_000),
            batch_background_max_bytes=_positive(
                env, "BATCH_BACKGROUND_MAX_BYTES", 50 * 1024 * 1024
            ),
            job_chunk_items=_positive(env, "JOB_CHUNK_ITEMS", 500),
            job_lease_seconds=_positive(env, "JOB_LEASE_SECONDS", 120),
        )

    def validate_model_admin_topology(self) -> None:
        """Reject model mutations when Uvicorn is configured with multiple workers."""
        if not self.model_admin_mutations_enabled:
            return
        if self.web_concurrency != 1:
            raise RuntimeError(
                "MODEL_ADMIN_MUTATIONS_ENABLED requires WEB_CONCURRENCY=1 until "
                "cross-process model release propagation is implemented"
            )


def _worker_count(raw: str) -> int:
    try:
        worker_count = int(raw.strip())
    except ValueError as exc:
        raise RuntimeError("WEB_CONCURRENCY must be a positive integer") from exc
    if worker_count < 1:
        raise RuntimeError("WEB_CONCURRENCY must be a positive integer")
    return worker_count


def _positive(env: Mapping[str, str], name: str, default: int) -> int:
    raw = env.get(name)
    if raw is None:
        return default
    try:
        value = int(raw.strip())
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a positive integer, not {raw!r}") from exc
    if value < 1:
        raise RuntimeError(f"{name} must be a positive integer, not {raw!r}")
    return value


def _api_reference_script(raw: str) -> ApiReferenceScript:
    value = raw.strip().lower()
    for script in API_REFERENCE_SCRIPTS:
        if value == script:
            return script
    raise RuntimeError(
        f"RDM_API_REFERENCE_SCRIPT must be one of {', '.join(API_REFERENCE_SCRIPTS)}, not {raw!r}"
    )


@cache
def get_settings() -> Settings:
    return Settings.from_env()


def reload_settings() -> Settings:
    """Re-read the environment; called when an application is constructed."""
    get_settings.cache_clear()
    return get_settings()


def model_path() -> Path:
    return get_settings().model_path


def database_url() -> str | None:
    return get_settings().database_url


def cursor_signing_key() -> bytes:
    return get_settings().cursor_signing_key


def cors_origins() -> list[str]:
    return list(get_settings().cors_origins)


def model_admin_mutations_enabled() -> bool:
    return get_settings().model_admin_mutations_enabled


def workspace_admin_mutations_enabled() -> bool:
    return get_settings().workspace_admin_mutations_enabled
