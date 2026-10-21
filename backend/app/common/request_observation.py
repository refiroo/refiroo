"""Every HTTP request named, counted, timed and logged once (Product 0.11 O1, D194–D196).

An ASGI middleware rather than Starlette's ``BaseHTTPMiddleware``, so streamed responses (exports,
the job event stream) pass through untouched. It takes the request's ID from ``X-Request-Id`` or
makes one, returns it on the response, and after the response writes one access line on the
``app.access`` logger and counts the request under its route template.
"""

import logging
import time
from typing import Any

from .logs import RequestContext, begin_request, request_id_from
from .outage import database_unavailable
from .request_metrics import UNMATCHED_ROUTE, request_metrics

REQUEST_ID_HEADER = "X-Request-Id"
_HEADER = REQUEST_ID_HEADER.lower().encode("latin-1")

access_logger = logging.getLogger("app.access")
# Asked every few seconds by an orchestrator or a scraper: their access lines are DEBUG.
_PROBES = frozenset({"/health", "/health/live", "/metrics"})


class RequestObservation:
    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        sent_id = next(
            (value.decode("latin-1") for name, value in scope["headers"] if name == _HEADER),
            None,
        )
        context = RequestContext(request_id_from(sent_id), scope["method"], scope["path"])
        begin_request(context)
        status = 500
        started = time.perf_counter()

        async def send_with_id(message: dict[str, Any]) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                headers = [
                    (name, value) for name, value in message.get("headers", []) if name != _HEADER
                ]
                headers.append((_HEADER, context.request_id.encode("latin-1")))
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        except Exception as exc:
            # Answered by the server's error handler outside this middleware: 503 when it is a
            # missing database connection, otherwise 500 (``management/errors.py``).
            status = 503 if database_unavailable(exc) is not None else 500
            raise
        finally:
            seconds = time.perf_counter() - started
            route = scope.get("route")
            context.route = getattr(route, "path", None) or UNMATCHED_ROUTE
            request_metrics.record(context.method, context.route, status, seconds)
            access_logger.log(
                logging.DEBUG if context.path in _PROBES else logging.INFO,
                "%s %s %s %.1f ms",
                context.method,
                context.path,
                status,
                seconds * 1000,
                extra={
                    "fields": {
                        "path": context.path,
                        "status": status,
                        "durationMs": round(seconds * 1000, 1),
                    }
                },
            )
