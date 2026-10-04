import base64
import hashlib
import hmac
import json
from typing import Any, Literal

from ..config import cursor_signing_key
from ..errors import api_error

# Where a cursor continues relative to its row: strictly after it, from it (inclusive), strictly
# before it, or up to it (inclusive). Cursors issued before 0.8 carry no direction and mean "after".
CursorDirection = Literal["after", "from", "before", "upto"]
CURSOR_DIRECTIONS: tuple[CursorDirection, ...] = ("after", "from", "before", "upto")


def encode_cursor(
    position: tuple[str, ...],
    *,
    scope: str,
    sort: tuple[str, ...],
    filters: dict[str, Any],
    direction: CursorDirection = "after",
) -> str:
    body: dict[str, Any] = {
        "version": 1,
        "scope": scope,
        "sort": sort,
        "filters": filter_fingerprint(filters),
        "position": position,
    }
    if direction != "after":
        body["direction"] = direction
    payload = json.dumps(
        body,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    signature = hmac.digest(cursor_signing_key(), payload, "sha256")
    return f"{_base64_encode(payload)}.{_base64_encode(signature)}"


def decode_cursor(
    cursor: str,
    *,
    scope: str,
    sort: tuple[str, ...],
    filters: dict[str, Any],
    position_size: int | None = None,
    message: str = "Cursor is invalid",
) -> tuple[str, ...]:
    direction, position = decode_directed_cursor(
        cursor,
        scope=scope,
        sort=sort,
        filters=filters,
        position_size=position_size,
        message=message,
    )
    if direction != "after":
        raise api_error(422, "INVALID_CURSOR", message)
    return position


def decode_directed_cursor(
    cursor: str,
    *,
    scope: str,
    sort: tuple[str, ...],
    filters: dict[str, Any],
    position_size: int | None = None,
    message: str = "Cursor is invalid",
) -> tuple[CursorDirection, tuple[str, ...]]:
    """Decode a paging cursor into its direction and row position."""
    try:
        encoded_payload, encoded_signature = cursor.split(".")
        payload = _base64_decode(encoded_payload)
        signature = _base64_decode(encoded_signature)
        expected_signature = hmac.digest(cursor_signing_key(), payload, "sha256")
        if not hmac.compare_digest(signature, expected_signature):
            raise ValueError
        decoded = json.loads(payload)
    except (ValueError, json.JSONDecodeError):
        raise api_error(422, "INVALID_CURSOR", message) from None
    position = decoded.get("position") if isinstance(decoded, dict) else None
    direction = decoded.get("direction", "after") if isinstance(decoded, dict) else None
    if (
        not isinstance(decoded, dict)
        or decoded.get("version") != 1
        or decoded.get("scope") != scope
        or decoded.get("sort") != list(sort)
        or decoded.get("filters") != filter_fingerprint(filters)
        or not isinstance(position, list)
        or not position
        or not all(isinstance(item, str) for item in position)
        or (position_size is not None and len(position) != position_size)
        or direction not in CURSOR_DIRECTIONS
    ):
        raise api_error(422, "INVALID_CURSOR", message)
    return direction, tuple(position)


METADATA_CURSOR_MESSAGE = "Metadata cursor is invalid"


def encode_metadata_cursor(
    identity: tuple[str, ...],
    *,
    scope: str,
    sort: tuple[str, ...],
    filters: dict[str, Any],
) -> str:
    """Encode a cursor for a model-metadata collection."""
    return encode_cursor(identity, scope=scope, sort=sort, filters=filters)


def decode_metadata_cursor(
    cursor: str,
    *,
    scope: str,
    sort: tuple[str, ...],
    filters: dict[str, Any],
) -> tuple[str, ...]:
    """Decode a cursor for a model-metadata collection."""
    return decode_cursor(
        cursor,
        scope=scope,
        sort=sort,
        filters=filters,
        message=METADATA_CURSOR_MESSAGE,
    )


def filter_fingerprint(filters: dict[str, Any]) -> str:
    canonical = json.dumps(filters, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(canonical).hexdigest()


def _base64_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def _base64_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    decoded = base64.urlsafe_b64decode(value + padding)
    if _base64_encode(decoded) != value:
        raise ValueError
    return decoded
