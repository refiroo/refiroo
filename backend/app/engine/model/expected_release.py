"""The release a request names as the one it was built on (Product 0.11 M6a, D63–D64).

A client that read a workspace's model and writes later names that model's release in
``X-Expected-Model-Release-Id``. The API tier keeps it on the request's session (``expect``); the
places that fix a request's own context check it (``check``): the write units for live data and for
a change set, and the request snapshot of a read. When the context resolves another release the
request is refused before anything is written, with the code a client already handles for an
activation committed while it ran (``registry.require_resolved_release``). Without the header
nothing is checked.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...errors import api_error
from ...models.database import ModelRelease, WorkspaceModel

_EXPECTED = "expected_model_release_id"


def expect(session: Session, release_id: str | None) -> None:
    """Keep the release the request names for ``check``; ``None`` names none."""
    if release_id:
        session.info[_EXPECTED] = release_id


def check(
    session: Session,
    workspace_key: str,
    release_db_id: int | None = None,
    *,
    change_set_id: str | None = None,
) -> None:
    """Refuse the request when it named a release and its context resolves another:
    ``release_db_id``, or the release ``workspace_key`` runs now when it is ``None``."""
    expected = session.info.get(_EXPECTED)
    if expected is None:
        return
    if release_db_id is None:
        current = session.scalar(
            select(ModelRelease.public_id)
            .join(WorkspaceModel, WorkspaceModel.model_release_id == ModelRelease.id)
            .where(WorkspaceModel.workspace_key == workspace_key)
        )
    else:
        current = session.scalar(
            select(ModelRelease.public_id).where(ModelRelease.id == release_db_id)
        )
    if current is None or current == expected:
        return
    where = f"Change set '{change_set_id}'" if change_set_id else f"Workspace '{workspace_key}'"
    details = {
        "workspaceKey": workspace_key,
        "expectedReleaseId": expected,
        "currentReleaseId": current,
    }
    if change_set_id:
        details["changeSetId"] = change_set_id
    raise api_error(
        409,
        "MODEL_RELEASE_CHANGED",
        f"{where} runs another model release than the one this request was built on; nothing was "
        "saved. Reload and retry against its current model",
        details,
    )
