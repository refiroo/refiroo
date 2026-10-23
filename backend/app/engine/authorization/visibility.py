"""Lists filtered to what the caller may see, as conditions on the list's own statement (Product
0.12 Z1, D249, D285, D288; Z2, D294, D295). ``None`` means no condition: an instance grant covers
every workspace.
"""

from typing import Any

from sqlalchemy import and_, false, or_

from ...models.database import Job, SourceFile
from .catalogue import JOB_GROUPS
from .permissions import Permissions, PrincipalKind


def in_workspaces(column: Any, permissions: Permissions, groups: frozenset[str] | None) -> Any:
    """Rows whose workspace the caller holds any of ``groups`` in (any group without it)."""
    keys = permissions.workspaces(groups)
    if keys is None:
        return None
    return column.in_(sorted(keys)) if keys else false()


def requested_by(kind: PrincipalKind, row_id: int) -> Any:
    """Jobs the caller requested (D294)."""
    column = Job.requested_by_user_id if kind == "user" else Job.requested_by_client_id
    return column == row_id


def visible_jobs(permissions: Permissions, kind: PrincipalKind, row_id: int) -> Any:
    """Jobs the caller requested, and those whose kind's group they hold in their workspace
    (D285, D294)."""
    conditions = [requested_by(kind, row_id)]
    for job_kind, group in JOB_GROUPS.items():
        if job_kind == "migration":
            for change_set, held in ((False, group), (True, "change-sets")):
                where = in_workspaces(Job.workspace_key, permissions, frozenset({held}))
                own = Job.change_set_id.is_not(None) if change_set else Job.change_set_id.is_(None)
                conditions.append(
                    and_(Job.kind == job_kind, own, where if where is not None else True)
                )
            continue
        if group == "model-authoring":
            if permissions.allows(group, None):
                conditions.append(Job.kind == job_kind)
            continue
        where = in_workspaces(Job.workspace_key, permissions, frozenset({group}))
        conditions.append(
            and_(Job.kind == job_kind, where) if where is not None else Job.kind == job_kind
        )
    return or_(*conditions)


def uploaded_by(kind: PrincipalKind, row_id: int) -> Any:
    column = SourceFile.uploaded_by_user_id if kind == "user" else SourceFile.uploaded_by_client_id
    return column == row_id


def visible_source_files(permissions: Permissions, kind: PrincipalKind, row_id: int) -> Any:
    """Source files the caller uploaded, those of a workspace where they hold Bulk and import, and
    those naming no workspace when they hold it at the instance (D248, D295). ``None`` when they
    hold it at the instance."""
    keys = permissions.workspaces(frozenset({"bulk"}))
    if keys is None:
        return None
    return or_(
        uploaded_by(kind, row_id),
        SourceFile.workspace_key.in_(sorted(keys)) if keys else false(),
    )


def may_use_source_file(
    permissions: Permissions, kind: PrincipalKind, row_id: int, source: SourceFile
) -> bool:
    """The same rule for one file."""
    if source.uploaded_by_user_id == row_id and kind == "user":
        return True
    if source.uploaded_by_client_id == row_id and kind == "client":
        return True
    if source.workspace_key is None:
        return permissions.allows("bulk", None)
    return permissions.allows("bulk", source.workspace_key)
