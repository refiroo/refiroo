"""A job runs with its requester's permissions (Product 0.12 Z2, D236, D294).

The route check allows the submission; confirming it and each step the worker takes check the
requester again, as they stand then: a requester deactivated, or no longer holding the group the
job's kind is used under in its workspace, makes the step refuse with ``403 FORBIDDEN`` naming the
requester, and the job fails with that reason. A job from before Z2 has no requester and runs as
the engine's.
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...errors import api_error
from ...models.database import AuthorizationState, Job, OAuthClient, User
from ..identity.principals import named
from .catalogue import JOB_GROUPS, group_names
from .permissions import PrincipalKind, permissions_of
from .writes import JOB_ACTIONS, SYSTEM, Writer, doing


def job_group(job: Job) -> str:
    """The group a job's kind is used under; Work in change sets for a change set's own migration
    (D285). A workspace migration that publishes a change set (V2) also names the change set but
    is the workspace's release switch: Model release (0.12 R-F4). Only the change set's own
    migration stores ``moves: changeSet`` (``change_set_migrations``)."""
    if (
        job.kind == "migration"
        and job.change_set_id
        and (job.parameters or {}).get("moves") == "changeSet"
    ):
        return "change-sets"
    return JOB_GROUPS[job.kind]


def requester(job: Job) -> tuple[PrincipalKind, int] | None:
    if job.requested_by_user_id is not None:
        return "user", job.requested_by_user_id
    if job.requested_by_client_id is not None:
        return "client", job.requested_by_client_id
    return None


def requested_by(session: Session, job: Job) -> dict[str, Any] | None:
    """The requester as a job shows it: kind, public ID and name."""
    return named(session, requester(job))


def job_writer(session: Session, job: Job) -> Writer:
    """The writer a step of ``job`` runs as: its requester with their permissions now, under the
    group its kind is used with; ``403 FORBIDDEN`` when they lost it."""
    found = requester(job)
    if found is None:
        return SYSTEM
    kind, row_id = found
    model = User if kind == "user" else OAuthClient
    generation = (
        select(AuthorizationState.generation).where(AuthorizationState.id == 1).scalar_subquery()
    )
    active, generation = session.execute(
        select(model.active, generation).where(model.id == row_id)
    ).one()
    permissions = permissions_of(session, kind, row_id, generation or 0)
    group = job_group(job)
    action = JOB_ACTIONS[job.kind]
    workspace_key = None if group == "model-authoring" else job.workspace_key

    def refused(message: str):
        details = {
            "action": action,
            "groups": [group],
            "workspaceKey": workspace_key,
            "requestedBy": requested_by(session, job),
        }
        return api_error(403, "FORBIDDEN", message, details)

    if not active:
        raise refused(
            f"Job '{job.id}' was requested by {'a person' if kind == 'user' else 'a client'} "
            "who has been deactivated; it does not go on"
        )
    if not permissions.allows(group, workspace_key):
        where = f" in workspace '{workspace_key}'" if workspace_key else " at the instance"
        raise refused(
            f"Job '{job.id}' does not go on: {doing(action, (group,)).lower()}{where} needs "
            f"{group_names((group,))}, which its requester no longer holds"
        )
    return Writer(permissions, (group,), action, principal=found)
