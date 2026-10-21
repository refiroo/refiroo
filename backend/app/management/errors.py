"""Exception handlers that render engine and framework errors as the API's error body."""

import logging
import uuid

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from ..common.outage import UNAVAILABLE_CAUSES, database_unavailable
from ..errors import ApiError

logger = logging.getLogger(__name__)


async def api_error_handler(_request: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                **({"details": jsonable_encoder(exc.details)} if exc.details is not None else {}),
            }
        },
        headers=exc.headers,
    )


async def validation_error_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "REQUEST_VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": jsonable_encoder(exc.errors()),
            }
        },
    )


async def http_error_handler(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": "HTTP_ERROR",
                "message": str(exc.detail),
            }
        },
        headers=exc.headers,
    )


# How long a client waits before sending a request again that found no database connection.
RETRY_AFTER_SECONDS = 5


def _database_unavailable(request: Request, exc: Exception) -> JSONResponse | None:
    """``503 DATABASE_UNAVAILABLE`` for a request that got no database connection (0.11 Q1, D180):
    an operating condition the operator acts on, logged in one line naming the cause and the
    settings, its traceback at DEBUG."""
    reason = database_unavailable(exc)
    if reason is None:
        return None
    cause = UNAVAILABLE_CAUSES[reason]
    logger.log(
        logging.ERROR if reason == "unreachable" else logging.WARNING,
        "%s %s answered 503: %s",
        request.method,
        request.url.path,
        cause,
    )
    logger.debug("The database error of %s %s", request.method, request.url.path, exc_info=exc)
    return JSONResponse(
        status_code=503,
        content={
            "error": {
                "code": "DATABASE_UNAVAILABLE",
                "message": (
                    f"The {request.method} {request.url.path} operation "
                    f"{'lost its' if reason == 'transactionEnded' else 'got no'} database "
                    f"connection: {cause}. Nothing was saved; send it again in a few seconds."
                ),
                "details": {"reason": reason},
            }
        },
        headers={"Retry-After": str(RETRY_AFTER_SECONDS)},
    )


async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    unavailable = _database_unavailable(request, exc)
    if unavailable is not None:
        return unavailable
    correlation_id = uuid.uuid4().hex[:12]
    logger.error(
        "Unhandled API error [%s] for %s %s",
        correlation_id,
        request.method,
        request.url.path,
    )
    logger.debug(
        "Unhandled API cause [%s]",
        correlation_id,
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": (
                    f"The {request.method} {request.url.path} operation failed unexpectedly."
                    " Retry or contact support with"
                    f" reference {correlation_id}."
                ),
                "details": {"correlationId": correlation_id},
            }
        },
    )
