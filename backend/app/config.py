"""Process configuration, read from the environment into one validated object.

``get_settings`` caches, so configuration is parsed and validated once rather than re-read on every
access. Building an application re-reads it through :func:`reload_settings`, which is what lets a
test change the environment and construct a differently configured app in the same process.
"""

import base64
import os
import secrets
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError

# The product version: the management API document's ``info.version`` and ``GET /api/v1/system``.
# ``pyproject.toml`` carries the same value, held equal by ``tests/unit/test_config.py``.
ENGINE_VERSION = "0.11.0"

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL_PATH = PROJECT_ROOT / "model" / "rdm-starter.json"
# Where export files wait for download when JOB_FILE_DIR is not set (0.9 J1, D55).
DEFAULT_JOB_FILE_DIR = PROJECT_ROOT / "var" / "job-files"
DEFAULT_CORS_ORIGINS = "http://localhost:5173"
# The engine's address as callers reach it: the token issuer (0.12 I1, D259).
DEFAULT_PUBLIC_URL = "http://localhost:8000"

TRUTHY = {"1", "true", "yes", "on"}

# Where the API reference page at /docs loads its script from: the copy bundled with the engine, so
# the page works without internet access, or the same pinned version from a CDN.
ApiReferenceScript = Literal["bundled", "cdn"]
API_REFERENCE_SCRIPTS: tuple[ApiReferenceScript, ...] = ("bundled", "cdn")

# How the process writes its log (0.11 O1, D195): plain lines for a terminal, or one JSON object a
# line for a log collector.
LogFormat = Literal["text", "json"]
LOG_FORMATS: tuple[LogFormat, ...] = ("text", "json")
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR"]
LOG_LEVELS: tuple[LogLevel, ...] = ("DEBUG", "INFO", "WARNING", "ERROR")

# The setting SECRETS_ENCRYPTION_KEY replaced (D253); startup refuses it, naming the new one.
RETIRED_ENCRYPTION_KEY = "CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY"

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
    # The engine's address as callers reach it, the issuer of its tokens and the base of the
    # addresses its OAuth metadata names (0.12 I1, D259).
    public_url: str = DEFAULT_PUBLIC_URL
    # Seals every secret the engine must read back: token signing keys, webhook signing keys
    # (D253, ADR-043). Required; startup refuses without it (``validate_secrets``).
    secrets_encryption_key: bytes | None = None
    # How long an access token lasts (D251), and the age at which the token signing key is
    # replaced when the next token is issued (D254, D264).
    access_token_minutes: int = Field(default=60, ge=1)
    token_signing_key_days: int = Field(default=30, ge=1)
    # A browser session ends after this many idle hours or days in all (D251), and a password-reset
    # link after this many hours (D272).
    session_idle_hours: int = Field(default=12, ge=1)
    session_days: int = Field(default=14, ge=1)
    password_reset_hours: int = Field(default=24, ge=1)
    # A local password's least length: 15 (D252), lowered only on a development machine (D276).
    password_min_length: int = Field(default=15, ge=1, le=128)
    model_admin_mutations_enabled: bool = False
    workspace_admin_mutations_enabled: bool = True
    web_concurrency: int = Field(default=1, ge=1)
    # Each process's database connections (0.11 Q1, D179): kept open, opened beyond them on demand,
    # and how long a caller waits for one before the request answers 503 DATABASE_UNAVAILABLE.
    database_pool_size: int = Field(default=5, ge=1)
    database_pool_max_overflow: int = Field(default=10, ge=0)
    database_pool_timeout: int = Field(default=30, ge=1)
    # Seconds a pooled connection may sit idle inside a transaction before PostgreSQL ends it, so a
    # frozen or cut-off process releases its locks (0.11 N3, D182); 0 turns it off.
    database_idle_transaction_timeout: int = Field(default=300, ge=0)
    # The log's format and level (0.11 O1, D195), and how often each process reports itself to the
    # others through the database (D192).
    log_format: LogFormat = "text"
    log_level: LogLevel = "INFO"
    process_heartbeat_seconds: int = Field(default=15, ge=1)
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
    # The largest file an import takes (D13: 200 MB), stored in JOB_FILE_DIR (0.9 J2).
    import_max_bytes: int = Field(default=200 * 1024 * 1024, ge=1)
    # The items a preview runs, an import's or a batch's; beyond them it is a sample (0.9 J3,
    # D83; 0.9 K2, D119).
    job_preview_max_items: int = Field(default=10_000, ge=1)
    # Operations in one request to a model draft (0.10 A2).
    model_operation_max_items: int = Field(default=500, ge=1)
    # The optional inference assistant (0.10 A6, A-D5, D95): a factory ``module:function``, empty
    # for none, and the rows of each sheet it is sent.
    inference_assistant: str = ""
    inference_assistant_rows: int = Field(default=20, ge=1)
    # Export files and, from J2, uploads (D12, D55): one directory, created at start.
    job_file_dir: Path = DEFAULT_JOB_FILE_DIR
    # How long the change feed answers a position (D8, INTEGRATION_API F5); reported by
    # GET /capabilities.
    feed_retention_days: int = Field(default=30, ge=1)
    # The items one consumer batch resolve holds (C-D13, C-D50); reported by GET /capabilities.
    consumer_resolve_max_items: int = Field(default=1_000, ge=1)
    # Webhook subscriptions as a deployment capability group, off by default (C-D10, C-D102); their
    # signing keys are sealed with SECRETS_ENCRYPTION_KEY (C-D96, D253).
    consumer_subscriptions_enabled: bool = False
    # How long the webhook delivery log keeps a request (U5a, C-D118).
    consumer_webhook_log_retention_days: int = Field(default=7, ge=1)

    @classmethod
    def from_env(cls, environ: dict[str, str] | None = None) -> Self:
        env = os.environ if environ is None else environ
        configured_model_path = env.get("RDM_MODEL_PATH")
        configured_signing_key = env.get("RDM_CURSOR_SIGNING_KEY")
        if env.get(RETIRED_ENCRYPTION_KEY, "").strip():
            raise RuntimeError(
                f"{RETIRED_ENCRYPTION_KEY} is no longer read: SECRETS_ENCRYPTION_KEY replaces it "
                "and seals every stored secret (0.12, D253). Rename the setting, keeping its value, "
                "and start again"
            )
        return cls(
            database_url=env.get("DATABASE_URL", "").strip() or None,
            model_path=Path(configured_model_path) if configured_model_path else DEFAULT_MODEL_PATH,
            cors_origins=tuple(
                origin.strip()
                for origin in env.get("CORS_ORIGINS", DEFAULT_CORS_ORIGINS).split(",")
            ),
            public_url=_public_url(env.get("PUBLIC_URL", "")),
            secrets_encryption_key=encryption_key(env.get("SECRETS_ENCRYPTION_KEY", "")),
            access_token_minutes=_positive(env, "ACCESS_TOKEN_MINUTES", 60),
            token_signing_key_days=_positive(env, "TOKEN_SIGNING_KEY_DAYS", 30),
            session_idle_hours=_positive(env, "SESSION_IDLE_HOURS", 12),
            session_days=_positive(env, "SESSION_DAYS", 14),
            password_reset_hours=_positive(env, "PASSWORD_RESET_HOURS", 24),
            password_min_length=_positive(env, "PASSWORD_MIN_LENGTH", 15),
            model_admin_mutations_enabled=(
                env.get("MODEL_ADMIN_MUTATIONS_ENABLED", "false").strip().lower() in TRUTHY
            ),
            workspace_admin_mutations_enabled=(
                env.get("WORKSPACE_ADMIN_MUTATIONS_ENABLED", "true").strip().lower() in TRUTHY
            ),
            web_concurrency=_worker_count(env.get("WEB_CONCURRENCY", "1")),
            database_pool_size=_positive(env, "DATABASE_POOL_SIZE", 5),
            database_pool_max_overflow=_non_negative(env, "DATABASE_POOL_MAX_OVERFLOW", 10),
            database_pool_timeout=_positive(env, "DATABASE_POOL_TIMEOUT", 30),
            database_idle_transaction_timeout=_non_negative(
                env, "DATABASE_IDLE_TRANSACTION_TIMEOUT", 300
            ),
            log_format=_choice(env, "LOG_FORMAT", LOG_FORMATS, "text", str.lower),
            log_level=_choice(env, "LOG_LEVEL", LOG_LEVELS, "INFO", str.upper),
            process_heartbeat_seconds=_positive(env, "PROCESS_HEARTBEAT_SECONDS", 15),
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
            import_max_bytes=_positive(env, "IMPORT_MAX_BYTES", 200 * 1024 * 1024),
            job_preview_max_items=_positive(env, "JOB_PREVIEW_MAX_ITEMS", 10_000),
            model_operation_max_items=_positive(env, "MODEL_OPERATION_MAX_ITEMS", 500),
            inference_assistant=env.get("INFERENCE_ASSISTANT", "").strip(),
            inference_assistant_rows=_positive(env, "INFERENCE_ASSISTANT_ROWS", 20),
            job_file_dir=Path(env.get("JOB_FILE_DIR", "").strip() or DEFAULT_JOB_FILE_DIR),
            feed_retention_days=_positive(env, "FEED_RETENTION_DAYS", 30),
            consumer_resolve_max_items=_positive(env, "CONSUMER_RESOLVE_MAX_ITEMS", 1_000),
            consumer_subscriptions_enabled=(
                env.get("CONSUMER_SUBSCRIPTIONS_ENABLED", "false").strip().lower() in TRUTHY
            ),
            consumer_webhook_log_retention_days=_positive(env, "CONSUMER_WEBHOOK_LOG_RETENTION_DAYS", 7),
        )

    def prepare_job_file_dir(self) -> None:
        """Create ``JOB_FILE_DIR`` and refuse to start, with job creation on, when it cannot be
        written (D55): otherwise every export would fail later, one job at a time."""
        if not self.integration_jobs_enabled:
            return
        directory = self.job_file_dir
        try:
            directory.mkdir(parents=True, exist_ok=True)
            probe = directory / f".write-check-{os.getpid()}"
            probe.write_bytes(b"")
            probe.unlink()
        except OSError as exc:
            raise RuntimeError(
                f"JOB_FILE_DIR '{directory}' cannot be created or written ({exc.strerror or exc}). "
                "Export files are stored there while jobs are on. Point JOB_FILE_DIR at a "
                "directory this process can write, or turn job creation off with "
                "INTEGRATION_JOBS_ENABLED=false"
            ) from exc

    def validate_secrets(self) -> None:
        """Refuse to start without the key stored secrets are sealed with (D253): token signing
        keys exist on every installation, and a key generated per process would leave every sealed
        secret unreadable after a restart."""
        if self.secrets_encryption_key is None:
            raise RuntimeError(
                "SECRETS_ENCRYPTION_KEY is required: it seals the token signing keys and webhook "
                "signing keys stored in the database. Generate one with "
                "`python -m app.cli.generate_key` and keep it outside the database"
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


def _non_negative(env: Mapping[str, str], name: str, default: int) -> int:
    raw = env.get(name)
    if raw is None:
        return default
    try:
        value = int(raw.strip())
    except ValueError as exc:
        raise RuntimeError(f"{name} must be zero or a positive integer, not {raw!r}") from exc
    if value < 0:
        raise RuntimeError(f"{name} must be zero or a positive integer, not {raw!r}")
    return value


def _choice[T: str](
    env: Mapping[str, str],
    name: str,
    choices: tuple[T, ...],
    default: T,
    normal: Callable[[str], str],
) -> T:
    raw = env.get(name)
    if raw is None or not raw.strip():
        return default
    value = normal(raw.strip())
    for choice in choices:
        if value == choice:
            return choice
    raise RuntimeError(f"{name} must be one of {', '.join(choices)}, not {raw!r}")


def _public_url(raw: str) -> str:
    """The engine's address without a trailing slash; an absolute http(s) URL (RFC 8414)."""
    value = raw.strip().rstrip("/") or DEFAULT_PUBLIC_URL
    scheme, _, rest = value.partition("://")
    if scheme not in ("http", "https") or not rest or "?" in rest or "#" in rest:
        raise RuntimeError(
            f"PUBLIC_URL must be the engine's absolute http or https address, not {raw!r}"
        )
    return value


def encryption_key(raw: str) -> bytes | None:
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
            "SECRETS_ENCRYPTION_KEY must be 32 bytes written in URL-safe base64; "
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
        "PUBLIC_URL",
        "public_url",
        "runtime",
        "The engine's address as callers reach it; the issuer of its tokens",
    ),
    CatalogueEntry(
        "SECRETS_ENCRYPTION_KEY",
        "secrets_encryption_key",
        "runtime",
        "Seals the stored token and webhook signing keys; required",
        secret=True,
    ),
    CatalogueEntry(
        "JOB_FILE_DIR",
        "job_file_dir",
        "runtime",
        "Where export files wait for download; created at start, kept as long as their job",
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
        "Server worker processes on this instance",
    ),
    CatalogueEntry(
        "DATABASE_POOL_SIZE",
        "database_pool_size",
        "runtime",
        "Database connections each process keeps open",
    ),
    CatalogueEntry(
        "DATABASE_POOL_MAX_OVERFLOW",
        "database_pool_max_overflow",
        "runtime",
        "Database connections each process opens beyond the pool size when busy",
    ),
    CatalogueEntry(
        "DATABASE_POOL_TIMEOUT",
        "database_pool_timeout",
        "runtime",
        "Seconds a request waits for a database connection before it answers 503",
    ),
    CatalogueEntry(
        "DATABASE_IDLE_TRANSACTION_TIMEOUT",
        "database_idle_transaction_timeout",
        "runtime",
        "Seconds a connection may sit idle inside a transaction before the database ends it, "
        "releasing a stalled process's locks; 0 turns it off",
    ),
    CatalogueEntry(
        "LOG_FORMAT",
        "log_format",
        "runtime",
        "How the log is written: text lines, or one JSON object a line",
    ),
    CatalogueEntry("LOG_LEVEL", "log_level", "runtime", "The lowest level the log writes"),
    CatalogueEntry(
        "PROCESS_HEARTBEAT_SECONDS",
        "process_heartbeat_seconds",
        "runtime",
        "Seconds between each process's reports of its state to the others",
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
    CatalogueEntry(
        "INFERENCE_ASSISTANT",
        "inference_assistant",
        "capabilities",
        "The inference assistant's factory; empty for none, the default",
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
        "IMPORT_MAX_BYTES", "import_max_bytes", "limits", "Bytes in an import's file"
    ),
    CatalogueEntry(
        "JOB_PREVIEW_MAX_ITEMS",
        "job_preview_max_items",
        "limits",
        "Items a preview of an import or a batch runs before it is a sample",
    ),
    CatalogueEntry(
        "MODEL_OPERATION_MAX_ITEMS",
        "model_operation_max_items",
        "limits",
        "Operations in one request to a model draft",
    ),
    CatalogueEntry(
        "INFERENCE_ASSISTANT_ROWS",
        "inference_assistant_rows",
        "limits",
        "Rows of each sheet the inference assistant is sent",
    ),
    CatalogueEntry(
        "JOB_LEASE_SECONDS",
        "job_lease_seconds",
        "limits",
        "Seconds a worker holds a job, renewed with each chunk",
    ),
    CatalogueEntry(
        "ACCESS_TOKEN_MINUTES",
        "access_token_minutes",
        "runtime",
        "Minutes an access token lasts, for people and clients",
    ),
    CatalogueEntry(
        "TOKEN_SIGNING_KEY_DAYS",
        "token_signing_key_days",
        "runtime",
        "Days a token signing key signs before the next token brings a new one",
    ),
    CatalogueEntry(
        "SESSION_IDLE_HOURS",
        "session_idle_hours",
        "runtime",
        "Hours a browser session lasts without being used",
    ),
    CatalogueEntry(
        "SESSION_DAYS",
        "session_days",
        "runtime",
        "Days a browser session lasts in all before the person signs in again",
    ),
    CatalogueEntry(
        "PASSWORD_RESET_HOURS",
        "password_reset_hours",
        "runtime",
        "Hours a password-reset link stays valid",
    ),
    CatalogueEntry(
        "PASSWORD_MIN_LENGTH",
        "password_min_length",
        "runtime",
        "Characters a local password needs at least; lower only for development",
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
        "CONSUMER_WEBHOOK_LOG_RETENTION_DAYS",
        "consumer_webhook_log_retention_days",
        "webhooks",
        "Days the webhook delivery log keeps a request, its body and its attempts",
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
