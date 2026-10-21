"""How the engine writes its log (Product 0.11 O1, D195, D196).

``LOG_FORMAT=text`` writes one plain line per record for a terminal; ``json`` writes one JSON object
per line for a log collector, with ``time``, ``level``, ``logger``, ``message`` and ``process``, and
within a request its ``requestId``, ``method`` and ``route``. A traceback goes in ``exception``, at
whatever level the code logs it (AGENTS.md "Error handling": an expected failure keeps it at DEBUG).

The engine's loggers (``app``) and uvicorn's write through one handler on the root logger, which
``configure_logging`` installs once per configuration; handlers others added (a test's capture) are
left alone.
"""

import json
import logging
import re
import sys
import traceback
import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import UTC, datetime

from ..config import LogFormat, LogLevel

# A request ID taken from ``X-Request-Id`` (D196): what proxies send, and nothing a log line could
# be forged with.
_REQUEST_ID = re.compile(r"[A-Za-z0-9._-]{1,64}")
_ENGINE_LOGGER = "app"
_UVICORN_LOGGERS = ("uvicorn", "uvicorn.error")


@dataclass
class RequestContext:
    """The request a log line belongs to. ``route`` is the matched route's template, filled in once
    routing has run."""

    request_id: str
    method: str
    path: str
    route: str | None = field(default=None)


_request: ContextVar[RequestContext | None] = ContextVar("rdm_request", default=None)


def request_id_from(header: str | None) -> str:
    """The client's request ID when it is well formed, otherwise a new one."""
    if header is not None and _REQUEST_ID.fullmatch(header):
        return header
    return uuid.uuid4().hex


def begin_request(context: RequestContext) -> None:
    """Make ``context`` the current request for this task. Not reset at the end: the server's error
    handler runs after the request's middleware has returned and still names the request; each
    request runs in a task of its own."""
    _request.set(context)


def current_request() -> RequestContext | None:
    return _request.get()


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, object] = {
            "time": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "process": record.process,
            "thread": record.threadName,
        }
        request = current_request()
        if request is not None:
            entry["requestId"] = request.request_id
            entry["method"] = request.method
            entry["route"] = request.route or request.path
        fields = getattr(record, "fields", None)
        if isinstance(fields, dict):
            entry.update(fields)
        if record.exc_info:
            entry["exception"] = "".join(traceback.format_exception(*record.exc_info))
        return json.dumps(entry, ensure_ascii=False, default=str)


class TextFormatter(logging.Formatter):
    def __init__(self) -> None:
        super().__init__("%(asctime)s %(levelname)s %(name)s: %(message)s")

    def format(self, record: logging.LogRecord) -> str:
        line = super().format(record)
        request = current_request()
        if request is None:
            return line
        head, newline, rest = line.partition("\n")
        return f"{head} [request {request.request_id}]{newline}{rest}"


class _EngineHandler(logging.StreamHandler):
    """The handler ``configure_logging`` installs, told apart from any other on the root logger."""


def configure_logging(log_format: LogFormat, level: LogLevel) -> None:
    """Write the engine's and uvicorn's records in ``log_format`` from ``level`` up. uvicorn's own
    access line is turned off: the engine writes one per request (``RequestObservation``)."""
    root = logging.getLogger()
    for handler in [h for h in root.handlers if isinstance(h, _EngineHandler)]:
        root.removeHandler(handler)
    handler = _EngineHandler(sys.stderr)
    handler.setFormatter(JsonFormatter() if log_format == "json" else TextFormatter())
    root.addHandler(handler)
    logging.getLogger(_ENGINE_LOGGER).setLevel(level)
    for name in _UVICORN_LOGGERS:
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.propagate = True
    logging.getLogger("uvicorn.access").disabled = True
