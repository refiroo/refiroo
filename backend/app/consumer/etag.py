"""The consumer API's entity tags (Base 0.9 C6a, C-D65).

A tag names a version of what a read answers: the data it read, the model release that shaped it
and the contract version. For live data the data version is the workspace's feed position, which
every live write, publish and withdrawal raises (F1); a pinned read's is its publication, which never
changes. The tag is opaque: a digest of those parts, then ``:`` and the contract version.

The route reads the data version before the data, so a tag is never newer than the answer it labels:
at worst a client is sent an answer it already has. ``If-None-Match`` is compared after the read, as
RFC 9110 compares it for ``GET``: weakly, any listed tag or ``*`` matching.
"""

import hashlib
from collections.abc import Iterable


def entity_tag(parts: Iterable[str], contract_version: int | str) -> str:
    """The quoted tag of a read over ``parts`` (the data version and the release)."""
    digest = hashlib.sha256("\x1f".join(parts).encode()).hexdigest()[:20]
    return f'"{digest}:{contract_version}"'


def none_match(header: str | None, tag: str) -> bool:
    """Whether ``If-None-Match`` names ``tag``: ``*``, or one of its comma-separated tags compared
    weakly (``W/`` ignored). An absent header, or one naming no such tag, does not match."""
    if header is None:
        return False
    if header.strip() == "*":
        return True
    return any(candidate.strip().removeprefix("W/") == tag for candidate in header.split(","))
