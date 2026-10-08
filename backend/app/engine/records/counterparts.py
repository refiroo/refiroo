"""Counterparts: another workspace's records as this workspace's own (0.9 J5, D96, D97).

Record IDs are unique across the instance, so a file holding another workspace's record IDs (its
export) cannot load here as they are (D49). Asked for, such an ID stands for its counterpart: the
record of this workspace whose ID is derived from the original ID and this workspace's key alone.
The same file therefore finds on its next load what its first created, and a workspace's types load
file by file. API.md documents the namespace, so a client can compute where a record went.
"""

from uuid import UUID, uuid5

NAMESPACE = UUID("2218e355-f627-4a22-a009-bebe5423891c")


def counterpart(workspace_key: str, object_id: str) -> str:
    """The ID that another workspace's record ``object_id`` has in ``workspace_key``: the name-based
    UUID of ``{workspaceKey}/{id}`` in ``NAMESPACE`` (SHA-1, as ``uuid5``), marked as version 4.
    Every public record ID the API accepts is a version-4 UUID, so a counterpart is one too and a
    client can send it back like any other ID."""
    return str(UUID(bytes=uuid5(NAMESPACE, f"{workspace_key}/{object_id}").bytes, version=4))
