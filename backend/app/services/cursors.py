import base64
import hashlib
import hmac
import json
from typing import Any

from ..config import cursor_signing_key
from ..errors import api_error


def encode_cursor(
    position: tuple[str, ...],
    *,
    scope: str,
    sort: tuple[str, ...],
    filters: dict[str, Any],
) -> str:
    payload = json.dumps(
        {
            "version": 1,
            "scope": scope,
            "sort": sort,
            "filters": filter_fingerprint(filters),
            "position": position,
        },
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
    try:
        encoded_payload, encoded_signature = cursor.split(".")
        payload = _base64_decode(encoded_payload)
        signature = _base64_decode(encoded_signature)
        expected_signature = hmac.digest(cursor_signing_key(), payload, "sha256")
        if not hmac.compare_digest(signature, expected_signature):
            raise ValueError
        decoded = json.loads(payload)
    except (ValueError, json.JSONDecodeError):
        raise api_error(422, "invalid_cursor", message) from None
    position = decoded.get("position") if isinstance(decoded, dict) else None
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
    ):
        raise api_error(422, "invalid_cursor", message)
    return tuple(position)


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
