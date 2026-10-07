"""Which URLs a webhook subscription may name (Base 0.9 C11, C-D101 revised).

Any host, any port. A URL is absolute HTTPS without user information or a fragment, at most 2,048
characters; plain HTTP only to a loopback host. Name resolution and redirects are the dispatcher's
to check when it sends (C12).
"""

from urllib.parse import urlsplit

from ...errors import ApiError, api_error

MAX_URL_LENGTH = 2048
LOOPBACK = frozenset({"localhost", "127.0.0.1", "::1"})


def check_webhook_url(url: str, pointer: str = "/url") -> ApiError | None:
    """The refusal of ``url``, or ``None`` when it may be used."""

    def invalid(reason: str) -> ApiError:
        return api_error(400, "INVALID_WEBHOOK_URL", f"The webhook URL {reason}", {"pointer": pointer})

    if len(url) > MAX_URL_LENGTH:
        return invalid(f"is longer than {MAX_URL_LENGTH} characters")
    try:
        parts = urlsplit(url)
        host = parts.hostname
        parts.port  # noqa: B018 - a port that is not a number raises here
    except ValueError:
        return invalid("is not a valid URL")
    if parts.scheme not in ("https", "http") or not host:
        return invalid("must be an absolute https URL")
    if parts.username is not None or parts.password is not None:
        return invalid("must not hold user information: the request is signed instead")
    if parts.fragment or url.endswith("#"):
        return invalid("must not hold a fragment")
    if parts.scheme == "http" and host.lower() not in LOOPBACK:
        return invalid("must use https; plain http is allowed only to a loopback host")
    return None
