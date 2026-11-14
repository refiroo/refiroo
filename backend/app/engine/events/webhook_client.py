"""One webhook request, to an address checked before connecting (Base 0.9 C12, C-D107).

The host is resolved once per attempt and the request goes to an address that was checked, so a
name cannot be pointed elsewhere between the check and the connection; TLS is verified against the
host name and the system trust store (``SSL_CERT_FILE`` overrides it). A webhook's addresses follow
the one rule of ``webhook_urls.address_refusal`` (0.17 RF6): when the host resolves to any
non-public address the request is refused, unless ``WEBHOOK_PRIVATE_ADDRESSES_ALLOWED`` is on, and
a link-local address (``169.254.0.0/16``, ``fe80::/10``, where cloud metadata services listen) is
refused whatever the setting says. A sign-in provider's requests (``exchange`` with no
``private_allowed``) keep their own rule: link-local and unspecified addresses are refused, and a
loopback one unless the URL names a loopback host. Redirects are not followed. The whole exchange has one timeout, and at most
4 KiB of the answer is read, for the error message and the delivery log (U5a). No outbound proxy
is used.

The answer is a success (``2xx``) or a failure of one kind: ``status``, ``redirect``, ``timeout``,
``connection``, ``tls`` or ``address``, with a message of at most 200 characters (C-D108).
"""

import http.client
import ipaddress
import socket
import ssl
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

from ...common.addresses import LOOPBACK
from .webhook_urls import address_refusal as webhook_address_refusal
from .webhook_urls import private_addresses_allowed

READ_BYTES = 4096
MESSAGE_LENGTH = 200

Resolver = Callable[..., list[tuple[Any, ...]]]


@dataclass(frozen=True)
class Answer:
    """What a receiver answered: ``error`` is ``None`` for a ``2xx``; ``body`` is up to 4 KiB of the
    answer, ``None`` when none was read."""

    status: int | None
    error: dict[str, Any] | None
    body: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


def _failure(kind: str, message: str, status: int | None = None, body: str | None = None) -> Answer:
    error: dict[str, Any] = {"kind": kind, "message": " ".join(message.split())[:MESSAGE_LENGTH]}
    if status is not None:
        error["status"] = status
    return Answer(status, error, body)


def address_refusal(host: str, address: str) -> str | None:
    """A sign-in provider's rule: why ``address``, which ``host`` resolved to, may not be connected
    to; ``None`` when it may. (A webhook's is ``webhook_urls.address_refusal``.)"""
    ip = ipaddress.ip_address(address.split("%", 1)[0])
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    if ip.is_link_local:
        return "is link-local, where cloud metadata services listen"
    if ip.is_unspecified:
        return "is unspecified"
    if ip.is_loopback and host.lower().rstrip(".") not in LOOPBACK:
        return "is a loopback address, allowed only for a URL naming a loopback host"
    return None


def _host_header(host: str, port: int, https: bool) -> str:
    name = f"[{host}]" if ":" in host else host
    return name if port == (443 if https else 80) else f"{name}:{port}"


def post(
    url: str,
    body: bytes,
    request_headers: Mapping[str, str],
    *,
    timeout: float,
    resolve: Resolver = socket.getaddrinfo,
) -> Answer:
    """POST ``body`` to ``url``; the receiver's answer, or why there was none."""
    return exchange(
        "POST",
        url,
        body,
        request_headers,
        timeout=timeout,
        resolve=resolve,
        private_allowed=private_addresses_allowed(),
    )


def exchange(
    method: str,
    url: str,
    body: bytes | None,
    request_headers: Mapping[str, str],
    *,
    timeout: float,
    read_bytes: int = READ_BYTES,
    resolve: Resolver = socket.getaddrinfo,
    private_allowed: bool | None = None,
) -> Answer:
    """One request to an address checked before connecting, as a webhook's (a sign-in provider's
    discovery, keys and token exchange read more of the answer, 0.12 I3, D362). ``private_allowed``
    is the webhook rule (every resolved address must pass); ``None`` is the provider's."""
    parts = urlsplit(url)
    host = parts.hostname or ""
    https = parts.scheme == "https"
    port = parts.port or (443 if https else 80)
    target = (parts.path or "/") + (f"?{parts.query}" if parts.query else "")
    deadline = time.monotonic() + timeout

    def remaining() -> float:
        left = deadline - time.monotonic()
        if left <= 0:
            raise TimeoutError
        return left

    try:
        found = resolve(host, port, type=socket.SOCK_STREAM)
    except OSError as exc:
        return _failure("connection", f"Host '{host}' could not be resolved: {exc}")
    addresses = list(dict.fromkeys(str(info[4][0]) for info in found))
    if private_allowed is None:
        allowed = [address for address in addresses if address_refusal(host, address) is None]
        if not allowed:
            first = addresses[0] if addresses else "nothing"
            return _failure(
                "address",
                f"Host '{host}' resolves to {first}, which {address_refusal(host, first)}",
            )
    else:
        for address in addresses:
            reason = webhook_address_refusal(address, private_allowed=private_allowed)
            if reason is not None:
                return _failure("address", f"Host '{host}' resolves to {address}, which {reason}")
        allowed = addresses
        if not allowed:
            return _failure("connection", f"Host '{host}' could not be resolved")

    sock: socket.socket | None = None
    try:
        last: OSError | None = None
        for address in allowed:
            try:
                sock = socket.create_connection((address, port), timeout=remaining())
                break
            except TimeoutError:
                raise
            except OSError as exc:
                last = exc
        if sock is None:
            return _failure("connection", f"Could not connect to '{host}' port {port}: {last}")
        if https:
            sock.settimeout(remaining())
            sock = ssl.create_default_context().wrap_socket(sock, server_hostname=host)
        connection = http.client.HTTPConnection(host, port)
        connection.sock = sock
        sock.settimeout(remaining())
        connection.putrequest(method, target, skip_host=True, skip_accept_encoding=True)
        connection.putheader("Host", _host_header(host, port, https))
        for name, value in request_headers.items():
            connection.putheader(name, value)
        if body is not None:
            connection.putheader("Content-Length", str(len(body)))
        connection.endheaders(body)
        sock.settimeout(remaining())
        response = connection.getresponse()
        sock.settimeout(remaining())
        text = response.read(read_bytes).decode("utf-8", "replace")
        status = response.status
        if 200 <= status < 300:
            return Answer(status, None, text)
        if 300 <= status < 400:
            location = response.getheader("Location") or "nowhere"
            return _failure(
                "redirect",
                f"The receiver answered {status} redirecting to {location}; redirects are not followed",
                status,
                text,
            )
        return _failure("status", f"{status} {response.reason}: {text}".rstrip(": "), status, text)
    except TimeoutError:
        return _failure("timeout", f"No answer from '{host}' within {timeout:g} s")
    except ssl.SSLError as exc:
        return _failure("tls", f"TLS with '{host}' failed: {exc}")
    except (OSError, http.client.HTTPException) as exc:
        return _failure(
            "connection", f"The connection to '{host}' failed: {exc or type(exc).__name__}"
        )
    finally:
        if sock is not None:
            sock.close()
