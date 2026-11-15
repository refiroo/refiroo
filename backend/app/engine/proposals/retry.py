"""One way to post to a provider and try again (the code reviews of 2026-11-13, D3).

Both HTTP adapters send through ``post_with_retry``. A passing failure (overloaded, rate-limited, a
server that failed for a moment, a connection that did not open) is sent again after a wait: the
provider's ``retry-after`` when it names one, else a delay that doubles. A request that timed out is
never sent again, unless it was the connection that timed out (nothing was sent): the provider may
still be answering it, and a long answer sent twice is charged twice. A wait longer than ``MAX_WAIT_SECONDS`` is not waited for; the answer that asked for it is
returned and the call fails as rate-limited.
"""

import time
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

from .provider import ProviderError

# Tried again by the client: timeout, conflict, rate limit, overload or a passing server failure.
RETRIED_STATUSES = {408, 409, 429, 500, 502, 503, 504, 529}
ATTEMPTS = 3
FIRST_WAIT_SECONDS = 1.0
MAX_WAIT_SECONDS = 30.0


def post_with_retry(
    client: httpx.Client,
    url: str,
    *,
    body: dict[str, Any],
    headers: dict[str, str],
    unreachable: str,
) -> httpx.Response:
    """The provider's answer, whatever its status once the attempts are used up or the status is
    not a passing one. ``unreachable`` is the sentence for a connection that never answered."""
    for attempt in range(ATTEMPTS):
        last = attempt + 1 == ATTEMPTS
        try:
            response = client.post(url, json=body, headers=headers)
        except httpx.ConnectTimeout as exc:
            # The connection never opened, so nothing was sent: sent again like a refused one.
            if last:
                raise ProviderError("unreachable", unreachable) from exc
            _sleep(wait_seconds(None, attempt))
            continue
        except httpx.TimeoutException as exc:
            raise ProviderError(
                "unreachable", "The provider did not answer in time (AI_TIMEOUT_SECONDS)"
            ) from exc
        except httpx.HTTPError as exc:
            if last:
                raise ProviderError("unreachable", unreachable) from exc
            _sleep(wait_seconds(None, attempt))
            continue
        if response.status_code not in RETRIED_STATUSES or last:
            return response
        wait = wait_seconds(response.headers.get("retry-after"), attempt)
        if wait > MAX_WAIT_SECONDS:
            return response
        _sleep(wait)
    raise AssertionError("unreachable")


def wait_seconds(retry_after: str | None, attempt: int) -> float:
    """The provider's ``retry-after`` (seconds or a date) when it sent one, else a delay that
    doubles with each attempt."""
    if retry_after:
        try:
            return max(0.0, float(retry_after))
        except ValueError:
            try:
                moment = parsedate_to_datetime(retry_after)
            except TypeError, ValueError:
                moment = None
            if moment is not None:
                if moment.tzinfo is None:
                    # ``-0000`` names a date with no zone: UTC, as the HTTP date format says.
                    moment = moment.replace(tzinfo=UTC)
                return max(0.0, (moment - datetime.now(UTC)).total_seconds())
    return FIRST_WAIT_SECONDS * 2**attempt


def _sleep(seconds: float) -> None:
    time.sleep(seconds)
