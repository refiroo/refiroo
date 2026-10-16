"""Counterparts: another workspace's records as this workspace's own (0.9 J5, D96, D97).

Record IDs are unique across the instance, so a file holding another workspace's record IDs (its
export) cannot load here as they are (D49). Asked for, such an ID stands for its counterpart: the
record of this workspace whose ID is derived from the original ID and this workspace's key alone.
The same file therefore finds on its next load what its first created, and a workspace's types load
file by file. API.md documents the namespace, so a client can compute where a record went.

Counterparts stand only between workspaces running one model (any of its releases): a record of
a workspace running another model is refused, never translated (0.11 M4, D44).
"""

from collections.abc import Iterable
from uuid import UUID, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...models.database import ModelRelease, RdmObject, WorkspaceModel

NAMESPACE = UUID("2218e355-f627-4a22-a009-bebe5423891c")


def counterpart(workspace_key: str, object_id: str) -> str:
    """The ID that another workspace's record ``object_id`` has in ``workspace_key``: the name-based
    UUID of ``{workspaceKey}/{id}`` in ``NAMESPACE`` (SHA-1, as ``uuid5``), marked as version 4.
    Every public record ID the API accepts is a version-4 UUID, so a counterpart is one too and a
    client can send it back like any other ID."""
    return str(UUID(bytes=uuid5(NAMESPACE, f"{workspace_key}/{object_id}").bytes, version=4))


def held_elsewhere(
    session: Session, workspace_key: str, object_ids: Iterable[str]
) -> list[tuple[str, str, str]]:
    """Which of ``object_ids`` other workspaces' live records hold: each ID with its workspace and
    the key of the model that workspace runs. One statement per thousand IDs."""
    ids = sorted(set(object_ids))
    found: list[tuple[str, str, str]] = []
    for start in range(0, len(ids), 1000):
        found += session.execute(
            select(RdmObject.id, RdmObject.workspace_key, ModelRelease.release_key)
            .join(WorkspaceModel, WorkspaceModel.workspace_key == RdmObject.workspace_key)
            .join(ModelRelease, ModelRelease.id == WorkspaceModel.model_release_id)
            .where(
                RdmObject.id.in_(ids[start : start + 1000]),
                RdmObject.workspace_key != workspace_key,
            )
        ).tuples()
    return found
