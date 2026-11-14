"""The assistant session's egress proxy (SR-D6).

In a container the session's users may reach only the engine and this proxy (a firewall rule set at
container start, ``refiroo-engine-start``). The proxy accepts ``CONNECT host:443`` for a host name on its
allow-list and nothing else: no IP literal, no other port, no plain HTTP request. The session's own
``HTTPS_PROXY`` points here. It runs as a user that is not a session user, with none of the engine's
environment, and uses only the standard library so that it starts with nothing of the engine loaded.

The allow-list is the AI provider's hosts, from the same settings the session is started with:

- the Anthropic API (default): ``api.anthropic.com``, and the hosts a subscription's sign-in and token
  renewal use, ``claude.ai`` and ``platform.claude.com``;
- ``ANTHROPIC_BASE_URL`` (a gateway or another endpoint): that host, and the two sign-in hosts only when a
  subscription token (``CLAUDE_CODE_OAUTH_TOKEN``) is set;
- Amazon Bedrock (``CLAUDE_CODE_USE_BEDROCK``): the region's ``bedrock-runtime``, ``bedrock`` and ``sts``
  hosts and the global ``sts.amazonaws.com``;
- ``AI_AGENT_API_URL`` when it is not on this machine;
- ``AI_AGENT_ALLOWED_HOSTS``: more host names, comma separated, ``*.example.com`` for every host below one.
"""

import asyncio
import ipaddress
import os
import re
import sys
from urllib.parse import urlparse

PORT = 3128
HTTPS = 443
# The hosts a subscription's sign-in and its token renewal use, beside the API's own.
SIGN_IN_HOSTS = ("claude.ai", "platform.claude.com")
ANTHROPIC_HOSTS = ("api.anthropic.com", *SIGN_IN_HOSTS)
HEADER_LIMIT = 8192
CONNECT_SECONDS = 15
IDLE_SECONDS = 600
MOST_CONNECTIONS = 128
_HOST = re.compile(
    r"^(?=.{1,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)+$"
)


def _host_of(url: str) -> str | None:
    host = (urlparse(url.strip()).hostname or "").lower() if url.strip() else ""
    return host or None


def _loopback(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _on(value: str) -> bool:
    return value.strip().lower() in ("1", "true", "yes", "on")


def allowed_hosts(environ: dict[str, str]) -> list[str]:
    """The host names (or ``*.suffix`` patterns) a session may reach, from the environment the engine
    gives the session and the one setting that adds more."""
    hosts: list[str] = []
    if _on(environ.get("CLAUDE_CODE_USE_BEDROCK", "")):
        region = environ.get("AWS_REGION", "").strip().lower() or "us-east-1"
        hosts += [
            f"bedrock-runtime.{region}.amazonaws.com",
            f"bedrock.{region}.amazonaws.com",
            f"sts.{region}.amazonaws.com",
            "sts.amazonaws.com",
        ]
    else:
        base = _host_of(environ.get("ANTHROPIC_BASE_URL", ""))
        if base is None:
            hosts += ANTHROPIC_HOSTS
        else:
            hosts.append(base)
            if environ.get("CLAUDE_CODE_OAUTH_TOKEN", "").strip():
                hosts += SIGN_IN_HOSTS
    api = _host_of(environ.get("AI_AGENT_API_URL", ""))
    if api is not None and not _loopback(api):
        hosts.append(api)
    hosts += [h.strip().lower() for h in environ.get("AI_AGENT_ALLOWED_HOSTS", "").split(",")]
    return sorted({host for host in hosts if host})


def permits(allowed: list[str], host: str) -> bool:
    """Whether a CONNECT to ``host`` is allowed: a host name (never an IP literal) that is on the list
    or below a ``*.`` entry of it."""
    host = host.lower().rstrip(".")
    if not _HOST.match(host):
        return False
    try:
        ipaddress.ip_address(host)
        return False
    except ValueError:
        pass
    for entry in allowed:
        if entry.startswith("*."):
            if host.endswith(entry[1:]) and len(host) > len(entry) - 1:
                return True
        elif host == entry:
            return True
    return False


def parse_connect(head: bytes) -> tuple[str, int] | None:
    """``(host, port)`` of a well-formed ``CONNECT host:port HTTP/1.x`` request line, else ``None``."""
    line = head.split(b"\r\n", 1)[0].decode("latin-1")
    parts = line.split(" ")
    if len(parts) != 3 or parts[0] != "CONNECT" or not parts[2].startswith("HTTP/1."):
        return None
    host, separator, port = parts[1].rpartition(":")
    if not separator or not port.isdigit() or not host or host.startswith("["):
        return None
    return host, int(port)


async def _pipe(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        while data := await asyncio.wait_for(reader.read(65536), IDLE_SECONDS):
            writer.write(data)
            await writer.drain()
    except TimeoutError, OSError, asyncio.IncompleteReadError:
        pass
    finally:
        try:
            writer.close()
        except OSError:
            pass


async def _refuse(writer: asyncio.StreamWriter, status: str) -> None:
    writer.write(f"HTTP/1.1 {status}\r\nConnection: close\r\nContent-Length: 0\r\n\r\n".encode())
    try:
        await writer.drain()
    except OSError:
        pass
    writer.close()


def handler(allowed: list[str]):
    slots = asyncio.Semaphore(MOST_CONNECTIONS)
    passed: set[str] = set()

    async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        async with slots:
            try:
                head = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), CONNECT_SECONDS)
            except TimeoutError, asyncio.LimitOverrunError, asyncio.IncompleteReadError, OSError:
                writer.close()
                return
            target = parse_connect(head)
            if target is None:
                await _refuse(writer, "405 Method Not Allowed")
                return
            host, port = target
            if port != HTTPS or not permits(allowed, host):
                # One line, with what is safe to show of a name the session chose.
                print(f"refused CONNECT to {host[:80]!r}:{port}", file=sys.stderr, flush=True)
                await _refuse(writer, "403 Forbidden")
                return
            try:
                remote_reader, remote_writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port), CONNECT_SECONDS
                )
            except TimeoutError, OSError:
                await _refuse(writer, "502 Bad Gateway")
                return
            if host not in passed and len(passed) < 1000:
                # Each allowed host once, so the log shows what the sessions use.
                passed.add(host)
                print(f"allowed CONNECT to {host}", file=sys.stderr, flush=True)
            writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
            await writer.drain()
            await asyncio.gather(_pipe(reader, remote_writer), _pipe(remote_reader, writer))

    return handle


async def serve(allowed: list[str], port: int = PORT) -> None:
    server = await asyncio.start_server(handler(allowed), "127.0.0.1", port, limit=HEADER_LIMIT)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    hosts = allowed_hosts(dict(os.environ))
    print("session proxy allows " + ", ".join(hosts), file=sys.stderr, flush=True)
    asyncio.run(serve(hosts))
