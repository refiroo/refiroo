"""Exception handlers that render engine and framework errors as the API's error body."""

import logging
import uuid

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

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
                "code": "request_validation_error",
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
                "code": "http_error",
                "message": str(exc.detail),
            }
        },
        headers=exc.headers,
    )


async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
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
                "code": "internal_error",
                "message": (
                    f"The {request.method} {request.url.path} operation failed unexpectedly."
                    " Retry or contact support with"
                    f" reference {correlation_id}."
                ),
                "details": {"correlationId": correlation_id},
            }
        },
    )
