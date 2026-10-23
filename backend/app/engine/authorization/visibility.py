"""Lists filtered to what the caller may see, as conditions on the list's own statement (Product
0.12 Z1, D249, D285, D288). ``None`` means no condition: an instance grant covers every workspace.
"""

from typing import Any

from sqlalchemy import and_, false, or_

from ...models.database import Job
from .catalogue import JOB_GROUPS
from .permissions import Permissions


def in_workspaces(column: Any, permissions: Permissions, groups: frozenset[str] | None) -> Any:
    """Rows whose workspace the caller holds any of ``groups`` in (any group without it)."""
    keys = permissions.workspaces(groups)
    if keys is None:
        return None
    return column.in_(sorted(keys)) if keys else false()


def visible_jobs(permissions: Permissions) -> Any:
    """Jobs whose kind's group the caller holds in their workspace (D285)."""
    conditions = []
    for kind, group in JOB_GROUPS.items():
        if kind == "migration":
            for change_set, held in ((False, group), (True, "change-sets")):
                where = in_workspaces(Job.workspace_key, permissions, frozenset({held}))
                own = Job.change_set_id.is_not(None) if change_set else Job.change_set_id.is_(None)
                conditions.append(and_(Job.kind == kind, own, where if where is not None else True))
            continue
        if group == "model-authoring":
            if permissions.allows(group, None):
                conditions.append(Job.kind == kind)
            continue
        where = in_workspaces(Job.workspace_key, permissions, frozenset({group}))
        conditions.append(and_(Job.kind == kind, where) if where is not None else Job.kind == kind)
    return or_(*conditions)
