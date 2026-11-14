"""The engine's error: an HTTP status, a stable machine-readable code, a message and details.

The API tiers render it (``management/errors.py``); nothing here depends on the web framework.
"""

from typing import Any


class ApiError(Exception):
    def __init__(
        self,
        status: int,
        code: str,
        message: str,
        details: Any | None = None,
        headers: dict[str, str] | None = None,
    ):
        self.status = status
        self.code = code
        self.message = message
        self.details = details
        self.headers = headers


def api_error(
    status: int,
    code: str,
    message: str,
    details: Any | None = None,
    *,
    headers: dict[str, str] | None = None,
) -> ApiError:
    return ApiError(status=status, code=code, message=message, details=details, headers=headers)


def version_conflict(
    current: int,
    what: str,
    *,
    message: str | None = None,
    details: dict[str, Any] | None = None,
) -> ApiError:
    """The one refusal of a stale write: ``409 VERSION_CONFLICT`` with ``currentVersion``.

    ``what`` names the row for the default message (``"<what> version has changed"``); ``message``
    replaces the whole sentence where a caller says more. ``details`` carries what the caller keeps
    beside ``currentVersion`` (a draft's ``expectedVersion`` and ``operations``, a mapping's
    targets, a release's status). ``CHANGE_SET_VERSION_CONFLICT`` and
    ``RELATION_SET_VERSION_CONFLICT`` stay separate codes: they tell two claims in one request apart.
    """
    return api_error(
        409,
        "VERSION_CONFLICT",
        message or f"{what} version has changed",
        {"currentVersion": current, **(details or {})},
    )


def require_version(
    row: Any,
    expected: int | None,
    what: str,
    *,
    message: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Refuse a write that claims another version than the row holds (call it under the row lock).

    ``row`` is the locked row (or its version as a number; a missing row is version 0). ``expected``
    of None is no claim and passes.
    """
    if expected is None:
        return
    current = row if isinstance(row, int) else (row.version if row is not None else 0)
    if current != expected:
        raise version_conflict(current, what, message=message, details=details)
