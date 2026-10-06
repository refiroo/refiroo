"""Process configuration, read from the environment into one validated object.

``get_settings`` caches, so configuration is parsed and validated once rather than re-read on every
access. Building an application re-reads it through :func:`reload_settings`, which is what lets a
test change the environment and construct a differently configured app in the same process.
"""

import base64
import os
import secrets
from collections.abc import Mapping
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError

# The product version: the management API document's ``info.version`` and ``GET /api/v1/system``.
# ``pyproject.toml`` carries the same value, held equal by ``tests/unit/test_config.py``.
ENGINE_VERSION = "0.9.0-alpha.1"

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
    # How long the change feed answers a position (D8, INTEGRATION_API F5); reported by
    # GET /capabilities.
    feed_retention_days: int = Field(default=30, ge=1)
    # The items one consumer batch resolve holds (C-D13, C-D50); reported by GET /capabilities.
    consumer_resolve_max_items: int = Field(default=1_000, ge=1)
    # Webhook subscriptions as a deployment capability group, off by default (C-D10, C-D102); the
    # hosts their URLs may name (C-D101) and the key their signing keys are encrypted with (C-D96).
    consumer_subscriptions_enabled: bool = False
    consumer_webhook_allowed_hosts: tuple[str, ...] = ()
    consumer_webhook_key_encryption_key: bytes | None = None

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
            feed_retention_days=_positive(env, "FEED_RETENTION_DAYS", 30),
            consumer_resolve_max_items=_positive(env, "CONSUMER_RESOLVE_MAX_ITEMS", 1_000),
            consumer_subscriptions_enabled=(
                env.get("CONSUMER_SUBSCRIPTIONS_ENABLED", "false").strip().lower() in TRUTHY
            ),
            consumer_webhook_allowed_hosts=allowed_hosts(
                env.get("CONSUMER_WEBHOOK_ALLOWED_HOSTS", "")
            ),
            consumer_webhook_key_encryption_key=_encryption_key(
                env.get("CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY", "")
            ),
        )

    def validate_consumer_subscriptions(self) -> None:
        """Refuse to start with subscriptions on and no key to encrypt their signing keys with
        (C-D96): a key generated per process would leave every stored signing key unreadable after
        a restart."""
        if self.consumer_subscriptions_enabled and self.consumer_webhook_key_encryption_key is None:
            raise RuntimeError(
                "CONSUMER_SUBSCRIPTIONS_ENABLED=true requires CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY, the "
                "key webhook signing keys are encrypted with. Generate one with "
                "`python -m app.cli.generate_key` and keep it outside the database"
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


def allowed_hosts(raw: str) -> tuple[str, ...]:
    """The webhook hosts, as listed: comma-separated, compared ignoring case (C-D101)."""
    return tuple(dict.fromkeys(host.strip().lower() for host in raw.split(",") if host.strip()))


def _encryption_key(raw: str) -> bytes | None:
    """The 32-byte key written in URL-safe base64, or none when unset."""
    value = raw.strip()
    if not value:
        return None
    try:
        key = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except ValueError:
        key = b""
    if len(key) != 32:
        raise RuntimeError(
            "CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY must be 32 bytes written in URL-safe base64; "
            "generate one with `python -m app.cli.generate_key`"
        )
    return key


def _api_reference_script(raw: str) -> ApiReferenceScript:
    value = raw.strip().lower()
    for script in API_REFERENCE_SCRIPTS:
        if value == script:
            return script
    raise RuntimeError(
        f"RDM_API_REFERENCE_SCRIPT must be one of {', '.join(API_REFERENCE_SCRIPTS)}, not {raw!r}"
    )


# The four groups of OPERATIONS § Settings, in its order.
SettingGroup = Literal["runtime", "capabilities", "limits", "webhooks"]
SettingSource = Literal["environment", "default"]


@dataclass(frozen=True)
class CatalogueEntry:
    """One setting as the API and the Deployment page describe it. The runbook detail stays in
    OPERATIONS; ``description`` is the one line the API returns."""

    name: str
    field: str
    group: SettingGroup
    description: str
    secret: bool = False


# Every ``Settings`` field once, in OPERATIONS' order. A new setting is added here and to OPERATIONS
# (``tests/unit/test_config.py`` holds both).
SETTINGS_CATALOGUE: tuple[CatalogueEntry, ...] = (
    CatalogueEntry(
        "DATABASE_URL", "database_url", "runtime", "The PostgreSQL database the engine runs on"
    ),
    CatalogueEntry(
        "RDM_MODEL_PATH",
        "model_path",
        "runtime",
        "The model file installed on a database's first start; not the active model",
    ),
    CatalogueEntry(
        "RDM_CURSOR_SIGNING_KEY",
        "cursor_signing_key",
        "runtime",
        "Signs pagination cursors; unset, each process makes its own, so cursors stop working "
        "after a restart and differ between instances",
        secret=True,
    ),
    CatalogueEntry(
        "CORS_ORIGINS", "cors_origins", "runtime", "Browser origins allowed to call the API"
    ),
    CatalogueEntry(
        "RDM_API_REFERENCE_SCRIPT",
        "api_reference_script",
        "runtime",
        "Where the API reference page at /docs loads its script from: bundled or cdn",
    ),
    CatalogueEntry(
        "WEB_CONCURRENCY",
        "web_concurrency",
        "runtime",
        "Server worker processes; must be 1 while model administration is on",
    ),
    CatalogueEntry(
        "MODEL_ADMIN_MUTATIONS_ENABLED",
        "model_admin_mutations_enabled",
        "capabilities",
        "Model drafts, compiling, installing and activating releases",
    ),
    CatalogueEntry(
        "WORKSPACE_ADMIN_MUTATIONS_ENABLED",
        "workspace_admin_mutations_enabled",
        "capabilities",
        "Creating, renaming, retiring, deleting workspaces and choosing the default",
    ),
    CatalogueEntry(
        "INTEGRATION_JOBS_ENABLED",
        "integration_jobs_enabled",
        "capabilities",
        "Creating and cancelling jobs (POST /batches); job reads stay available",
    ),
    CatalogueEntry(
        "CONSUMER_SUBSCRIPTIONS_ENABLED",
        "consumer_subscriptions_enabled",
        "capabilities",
        "Webhook subscriptions and their delivery",
    ),
    CatalogueEntry("BATCH_MAX_ITEMS", "batch_max_items", "limits", "Items in an inline batch"),
    CatalogueEntry(
        "BATCH_MAX_BYTES", "batch_max_bytes", "limits", "Bytes in an inline batch's body"
    ),
    CatalogueEntry(
        "ATOMIC_JOB_MAX_ITEMS",
        "atomic_job_max_items",
        "limits",
        "Items in an atomic batch, inline or background",
    ),
    CatalogueEntry(
        "BACKGROUND_JOB_MAX_ITEMS",
        "background_job_max_items",
        "limits",
        "Items in a background batch",
    ),
    CatalogueEntry(
        "BATCH_BACKGROUND_MAX_BYTES",
        "batch_background_max_bytes",
        "limits",
        "Bytes in a background batch's body",
    ),
    CatalogueEntry(
        "JOB_CHUNK_ITEMS", "job_chunk_items", "limits", "Items one background chunk commits"
    ),
    CatalogueEntry(
        "JOB_LEASE_SECONDS",
        "job_lease_seconds",
        "limits",
        "Seconds a worker holds a job, renewed with each chunk",
    ),
    CatalogueEntry(
        "JOB_RETENTION_DAYS",
        "job_retention_days",
        "limits",
        "Days a finished job keeps its outcomes and idempotency key",
    ),
    CatalogueEntry(
        "FEED_RETENTION_DAYS",
        "feed_retention_days",
        "limits",
        "Days the change feed and consumer events answer a position",
    ),
    CatalogueEntry(
        "CONSUMER_RESOLVE_MAX_ITEMS",
        "consumer_resolve_max_items",
        "limits",
        "Items in one consumer batch resolve",
    ),
    CatalogueEntry(
        "CONSUMER_WEBHOOK_ALLOWED_HOSTS",
        "consumer_webhook_allowed_hosts",
        "webhooks",
        "Hosts a webhook URL may name; empty allows none",
    ),
    CatalogueEntry(
        "CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY",
        "consumer_webhook_key_encryption_key",
        "webhooks",
        "Encrypts the stored webhook signing keys; required with subscriptions on",
        secret=True,
    ),
)


@dataclass(frozen=True)
class ReportedSetting:
    """A setting as ``GET /system`` reports it: typed value and default, never a secret."""

    name: str
    group: SettingGroup
    description: str
    value: Any
    default: Any
    source: SettingSource


def describe_settings(settings: Settings, environ: Mapping[str, str]) -> list[ReportedSetting]:
    """Every catalogued setting with its value, its default and where the value came from. A secret
    reports neither value nor default; the database URL loses its password."""
    defaults = Settings.from_env({})
    reported = []
    for entry in SETTINGS_CATALOGUE:
        hidden = entry.secret
        value = None if hidden else _shown(getattr(settings, entry.field))
        default = None if hidden else _shown(getattr(defaults, entry.field))
        if entry.field == "database_url" and value is not None:
            value = without_password(value)
        source: SettingSource = "environment" if environ.get(entry.name) else "default"
        reported.append(
            ReportedSetting(entry.name, entry.group, entry.description, value, default, source)
        )
    return reported


def _shown(value: Any) -> Any:
    """A setting's value as JSON writes it: paths as text, tuples as lists."""
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, tuple):
        return list(value)
    return value


def without_password(url: str) -> str | None:
    """The URL with its user, host, port and database, and no password; none when it cannot be read
    as a URL, since it might then hold the password anywhere."""
    try:
        parsed = make_url(url)
    except ArgumentError:
        return None
    query = {key: value for key, value in parsed.query.items() if key.lower() != "password"}
    shown = URL.create(
        parsed.drivername,
        username=parsed.username,
        host=parsed.host,
        port=parsed.port,
        database=parsed.database,
        query=query,
    )
    return shown.render_as_string(hide_password=False)


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
