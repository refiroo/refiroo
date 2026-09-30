"""Process configuration, read from the environment into one validated object.

``get_settings`` caches, so configuration is parsed and validated once rather than re-read on every
access. Building an application re-reads it through :func:`reload_settings`, which is what lets a
test change the environment and construct a differently configured app in the same process.
"""

import os
import secrets
from functools import cache
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL_PATH = PROJECT_ROOT / "model" / "rdm-starter.json"
DEFAULT_DATABASE_URL = "sqlite:///./rdm-engine.db"
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

    database_url: str = DEFAULT_DATABASE_URL
    model_path: Path = DEFAULT_MODEL_PATH
    cors_origins: tuple[str, ...] = (DEFAULT_CORS_ORIGINS,)
    model_admin_mutations_enabled: bool = False
    workspace_admin_mutations_enabled: bool = True
    web_concurrency: int = Field(default=1, ge=1)
    cursor_signing_key: bytes = _EPHEMERAL_CURSOR_SIGNING_KEY
    api_reference_script: ApiReferenceScript = "bundled"

    @classmethod
    def from_env(cls, environ: dict[str, str] | None = None) -> Self:
        env = os.environ if environ is None else environ
        configured_model_path = env.get("RDM_MODEL_PATH")
        configured_signing_key = env.get("RDM_CURSOR_SIGNING_KEY")
        return cls(
            database_url=env.get("DATABASE_URL", DEFAULT_DATABASE_URL),
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


def database_url() -> str:
    return get_settings().database_url


def cursor_signing_key() -> bytes:
    return get_settings().cursor_signing_key


def cors_origins() -> list[str]:
    return list(get_settings().cors_origins)


def model_admin_mutations_enabled() -> bool:
    return get_settings().model_admin_mutations_enabled


def workspace_admin_mutations_enabled() -> bool:
    return get_settings().workspace_admin_mutations_enabled
