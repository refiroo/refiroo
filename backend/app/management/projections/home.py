"""The caller's workspaces and what waits for them there, as the home page reads them (0.12 HM1,
D332): each workspace's applications from its own model and two counts of open change sets, read in
one grouped statement for the page.
"""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...engine.authorization.permissions import Permissions
from ...engine.identity.authentication import Principal
from ...engine.model.registry import (
    ModelRegistryUnavailable,
    WorkspaceModelUnavailable,
    model_registry,
)
from ...engine.model.workspace_models import assignments_of
from ...engine.notifications.following import followed_among
from ...models.database import ChangeSet, Workspace
from ..presenters import workspace_model_response
from ..schemas.workspaces import OwnWorkspaceResponse, WorkspaceApplication


def created_by(principal: Principal) -> Any:
    """Change sets the caller created (D325)."""
    column = (
        ChangeSet.created_by_user_id if principal.kind == "user" else ChangeSet.created_by_client_id
    )
    return column == principal.row_id


def _applications(session: Session, workspace_key: str) -> list[WorkspaceApplication]:
    try:
        model = model_registry.resolve_workspace(session, workspace_key).model
    except WorkspaceModelUnavailable, ModelRegistryUnavailable:
        return []
    return [
        WorkspaceApplication(
            key=item.key,
            name=item.name,
            icon=item.icon,
            color=item.color,
            defaultView=item.defaultView,
        )
        for item in model.applications
    ]


def own_workspace_items(
    session: Session,
    principal: Principal,
    permissions: Permissions,
    workspaces: list[Workspace],
    default_key: str,
) -> list[OwnWorkspaceResponse]:
    keys = [item.key for item in workspaces]
    counts = {
        row.workspace_key: (row.own, row.open)
        for row in session.execute(
            select(
                ChangeSet.workspace_key,
                func.count().filter(created_by(principal)).label("own"),
                func.count().label("open"),
            )
            .where(ChangeSet.workspace_key.in_(keys))
            .group_by(ChangeSet.workspace_key)
        )
    }
    assignments = assignments_of(session, keys)
    following = (
        followed_among(session, principal.row_id, keys) if principal.kind == "user" else set()
    )
    items = []
    for workspace in workspaces:
        own, open_ = counts.get(workspace.key, (0, 0))
        items.append(
            OwnWorkspaceResponse(
                key=workspace.key,
                label=workspace.label,
                isDefault=workspace.key == default_key,
                model=workspace_model_response(assignments[workspace.key]),
                applications=_applications(session, workspace.key),
                ownChangeSets=own,
                openChangeSets=open_ if permissions.allows("publish", workspace.key) else None,
                following=workspace.key in following,
            )
        )
    return items
