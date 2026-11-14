"""The network of the assistant's session in a container (0.17 SR-D6).

The image's start step (``backend/refiroo-engine-start``) sets a firewall rule for the session users when
the container has ``NET_ADMIN``, and leaves the outcome in a file this module reads. Three states:

- ``restricted``: the session users reach only this engine and the allow-list proxy
  (``backend/refiroo_session_proxy.py``), through which the session's ``HTTPS_PROXY`` points;
- ``unrestricted``: the container has no ``NET_ADMIN`` (or was not started as root), so nothing limits
  where a session connects: a known limitation, told in the log at start and in ``GET /ai/status``;
- ``failed``: ``NET_ADMIN`` is there and the setup failed: assistant turns do not start, and say why.

Outside a container the operating system's sandbox is the boundary and none of this applies.
"""

import logging
import os
import socket
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)

RESTRICTED = "restricted"
UNRESTRICTED = "unrestricted"
FAILED = "failed"
PROXY_PORT = 3128
# Where the start step leaves its outcome; ``AI_AGENT_NETWORK_STATE`` names another file (tests).
STATE_FILE = "/run/refiroo-net/session-network"
NO_CAPABILITY = "the container has no NET_ADMIN capability (cap_add: [NET_ADMIN] in compose.yml)"
HOW_TO_RESTRICT = (
    "give the engine container the NET_ADMIN capability (cap_add: [NET_ADMIN] in compose.yml, "
    "`--cap-add NET_ADMIN` with docker run) and start it as root, so that its start step can set the rule"
)


@dataclass(frozen=True)
class SessionNetwork:
    state: str
    note: str | None = None


def state_file() -> Path:
    return Path(os.environ.get("AI_AGENT_NETWORK_STATE", "").strip() or STATE_FILE)


def read_state() -> SessionNetwork:
    """What the start step left: a missing or unreadable file means it did not run as root with
    ``NET_ADMIN`` (a container started as another user), so the network is not restricted."""
    try:
        text = state_file().read_text().strip()
    except OSError:
        return SessionNetwork(UNRESTRICTED, NO_CAPABILITY)
    word, _, note = text.partition(" ")
    if word == RESTRICTED:
        return SessionNetwork(RESTRICTED)
    if word == FAILED:
        return SessionNetwork(FAILED, note or "the start step reported a failure")
    return SessionNetwork(UNRESTRICTED, note or NO_CAPABILITY)


def proxy_reachable(port: int = PROXY_PORT) -> bool:
    try:
        socket.create_connection(("127.0.0.1", port), timeout=2).close()
    except OSError:
        return False
    return True


def proxy_variables() -> dict[str, str]:
    """The proxy variables the session is given when its network is restricted: the proxy for what it
    sends out, none for this machine (the engine's API is reached directly)."""
    return {
        "HTTPS_PROXY": f"http://127.0.0.1:{PROXY_PORT}",
        "NO_PROXY": "127.0.0.1,localhost,::1",
    }


def report(enabled: bool, in_container: bool) -> SessionNetwork | None:
    """The network state for ``GET /ai/status``: ``None`` where it does not apply (no assistant, or no
    container)."""
    if not enabled or not in_container:
        return None
    return read_state()


def warn_at_start() -> None:
    """One WARNING at start when the session's network is not restricted, one ERROR when its setup failed."""
    found = read_state()
    if found.state == UNRESTRICTED:
        log.warning(
            "The assistant's session can reach any host: %s. To restrict it to the AI provider's hosts and "
            "this engine, %s (docs/OPERATIONS.md, AI_AGENT_SANDBOX)",
            found.note,
            HOW_TO_RESTRICT,
        )
    elif found.state == FAILED:
        log.error(
            "The assistant's network rule could not be set (%s): assistant turns do not start",
            found.note,
        )
