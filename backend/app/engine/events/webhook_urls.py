"""Which URLs a webhook subscription may name (Base 0.9 C11, C-D101 revised, 0.17 RF6).

Any host, any port. A URL is absolute HTTPS without user information or a fragment, at most 2,048
characters; plain HTTP only to a loopback host. An address that is, or whose host name resolves
to, a non-public address is refused unless ``WEBHOOK_PRIVATE_ADDRESSES_ALLOWED`` is on
(``address_refusal``, the one rule: the dispatcher applies it again when it sends, C12);
link-local addresses are refused whatever the setting says.
"""

import ipaddress
import socket
from collections.abc import Callable
from typing import Any
from urllib.parse import urlsplit

from ...common.addresses import LOOPBACK
from ...config import get_settings
from ...errors import ApiError, api_error

MAX_URL_LENGTH = 2048
SETTING = "WEBHOOK_PRIVATE_ADDRESSES_ALLOWED"

_NAT64 = ipaddress.ip_network("64:ff9b::/96")
_NAT64_LOCAL = ipaddress.ip_network("64:ff9b:1::/48")
_NON_PUBLIC = f"is a private or otherwise non-public address; private addresses are refused on this instance ({SETTING} allows them)"

Resolver = Callable[..., list[tuple[Any, ...]]]


def private_addresses_allowed() -> bool:
    return get_settings().webhook_private_addresses_allowed


def address_refusal(address: str, *, private_allowed: bool) -> str | None:
    """Why a webhook may not go to ``address`` (a literal, with an optional zone); ``None`` when it
    may. Link-local addresses, where cloud metadata services listen, are always refused. Every
    other address that is not public (loopback, private, unique-local, shared 100.64.0.0/10,
    unspecified, multicast, reserved, an IPv4-mapped or NAT64 (``64:ff9b::/96``) IPv6 address of any
    of these, and the local-use NAT64 range ``64:ff9b:1::/48``) is refused unless ``private_allowed``."""
    ip = ipaddress.ip_address(address.split("%", 1)[0])
    if isinstance(ip, ipaddress.IPv6Address):
        if ip.ipv4_mapped is not None:
            ip = ip.ipv4_mapped
        elif ip in _NAT64:
            # NAT64 reaches the IPv4 address in its last 32 bits: the same rule applies to it.
            ip = ipaddress.IPv4Address(int(ip) & 0xFFFFFFFF)
        elif ip in _NAT64_LOCAL:
            # Local-use NAT64 (RFC 8215) embeds the address at a place that varies: never public.
            if ip.is_link_local or not private_allowed:
                return _NON_PUBLIC
            return None
    if ip.is_link_local:
        return "is link-local, where cloud metadata services listen"
    if private_allowed:
        return None
    if not ip.is_global or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
        return _NON_PUBLIC
    return None


def literal_of(host: str) -> str:
    return host.strip("[]")


def host_refusal(host: str, port: int, resolve: Resolver = socket.getaddrinfo) -> str | None:
    """Why a webhook may not go to ``host`` (a name or a literal address), as a sentence about the
    host; ``None`` when it may, or when a name does not resolve yet (the delivery says so then).
    Every resolved address counts."""
    allowed = private_addresses_allowed()
    try:
        literal = literal_of(host)
        ipaddress.ip_address(literal.split("%", 1)[0])
        addresses = [literal]
    except ValueError:
        try:
            found = resolve(host, port, type=socket.SOCK_STREAM)
        except OSError:
            return None
        addresses = list(dict.fromkeys(str(info[4][0]) for info in found))
    for address in addresses:
        reason = address_refusal(address, private_allowed=allowed)
        if reason is not None:
            # The address a name resolves to is not given to the author: it would map internal names.
            return f"host '{host}' " + (
                f"resolves to an address that {reason}" if address != literal_of(host) else reason
            )
    return None


def check_webhook_url(
    url: str, pointer: str = "/url", resolve: Resolver = socket.getaddrinfo
) -> ApiError | None:
    """The refusal of ``url``, or ``None`` when it may be used."""

    def invalid(reason: str) -> ApiError:
        return api_error(
            400, "INVALID_WEBHOOK_URL", f"The webhook URL {reason}", {"pointer": pointer}
        )

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
    reason = host_refusal(host, parts.port or (443 if parts.scheme == "https" else 80), resolve)
    if reason is not None:
        return invalid(reason)
    return None
