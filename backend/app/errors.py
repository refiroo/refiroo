"""The engine's error: an HTTP status, a stable machine-readable code, a message and details.

The API tiers render it (``management/errors.py``); nothing here depends on the web framework.
"""

from typing import Any


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, details: Any | None = None):
        self.status = status
        self.code = code
        self.message = message
        self.details = details


def api_error(status: int, code: str, message: str, details: Any | None = None) -> ApiError:
    return ApiError(status=status, code=code, message=message, details=details)
