"""Action groups, roles, groups, grants and permissions as the API answers them (Product 0.12 Z1)."""

from typing import Any

from sqlalchemy.orm import Session

from ...common.pagination import Page
from ...engine.authorization import administration
from ...engine.authorization.administration import GrantRow
from ...engine.authorization.catalogue import ACTIONS, GROUPS
from ...engine.authorization.permissions import Permissions
from ...engine.model.registry import resolve_model_snapshot
from ...models.database import Role, User, UserGroup, Workspace
from ..schemas.authorization import (
    ActionGroupList,
    ActionGroupResponse,
    ActionResponse,
    GrantPage,
    GrantPrincipalResponse,
    GrantResponse,
    GrantRoleResponse,
    GrantScopeResponse,
    GroupMemberPage,
    GroupMemberResponse,
    GroupPage,
    GroupResponse,
    HeldGroup,
    OperationRef,
    PermissionSource,
    PermissionsResponse,
    RolePage,
    RoleResponse,
)


def action_groups(document: dict[str, Any]) -> ActionGroupList:
    """The catalogue, each action with the operations of ``document`` declaring it."""
    operations: dict[str, list[OperationRef]] = {}
    for path, methods in document["paths"].items():
        for method, operation in methods.items():
            if isinstance(operation, dict) and "x-action" in operation:
                operations.setdefault(operation["x-action"], []).append(
                    OperationRef(method=method.upper(), path=path)
                )
    return ActionGroupList(
        items=[
            ActionGroupResponse(
                key=group.key,
                name=group.name,
                description=group.description,
                grantableAt=group.reach,
                narrowable=group.narrowable,
                actions=[
                    ActionResponse(
                        key=action.key,
                        description=action.description,
                        operations=operations.get(action.key, []),
                    )
                    for action in ACTIONS.values()
                    if group.key in action.groups
                ],
            )
            for group in GROUPS.values()
        ]
    )


def role_response(session: Session, role: Role) -> RoleResponse:
    return RoleResponse(
        key=role.key,
        name=role.name,
        description=role.description,
        predefined=role.predefined,
        actionGroups=list(administration.groups_of(session, role)),
        grants=administration.holders(session, role),
        version=role.version,
        createdAt=role.created_at,
        updatedAt=role.updated_at,
    )


def role_page(session: Session, page: Page[Role]) -> RolePage:
    return RolePage(items=[role_response(session, role) for role in page.items], **page.links())


def group_response(session: Session, group: UserGroup) -> GroupResponse:
    return GroupResponse(
        id=group.public_id,
        name=group.name,
        description=group.description,
        members=administration.member_count(session, group),
        version=group.version,
        createdAt=group.created_at,
        updatedAt=group.updated_at,
    )


def group_page(session: Session, page: Page[UserGroup]) -> GroupPage:
    return GroupPage(items=[group_response(session, group) for group in page.items], **page.links())


def member_response(user: User) -> GroupMemberResponse:
    return GroupMemberResponse(
        id=user.public_id, username=user.username, name=user.name, active=user.active
    )


def member_page(page: Page[User]) -> GroupMemberPage:
    return GroupMemberPage(items=[member_response(user) for user in page.items], **page.links())


def _names(session: Session, workspace_key: str, kind: str, keys: list[str]) -> list[str]:
    """The names of a narrowing's keys in the workspace's model; a key it lacks as it is."""
    if not keys:
        return []
    model = resolve_model_snapshot(session, workspace_key).model
    items = model.applications if kind == "applications" else model.objectTypes
    names = {item.key: item.name for item in items}
    return [names.get(key, key) for key in keys]


def grant_response(session: Session, row: GrantRow) -> GrantResponse:
    grant = row.grant
    workspace = grant.workspace_key
    return GrantResponse(
        id=grant.public_id,
        principal=GrantPrincipalResponse(
            kind=row.principal_kind, id=row.principal_id, name=row.principal_name
        ),
        role=GrantRoleResponse(key=row.role.key, name=row.role.name),
        scope=GrantScopeResponse(
            instance=grant.workspace_key is None,
            workspaceKey=grant.workspace_key,
            applications=list(grant.applications),
            recordTypes=list(grant.record_types),
            applicationNames=_names(session, workspace, "applications", grant.applications)
            if workspace
            else [],
            recordTypeNames=_names(session, workspace, "recordTypes", grant.record_types)
            if workspace
            else [],
        ),
        createdAt=grant.created_at,
    )


def grant_page(session: Session, page: Page[GrantRow]) -> GrantPage:
    return GrantPage(items=[grant_response(session, row) for row in page.items], **page.links())


def permissions_response(permissions: Permissions, workspace: Workspace) -> PermissionsResponse:
    """What the caller holds in a workspace; a group's narrowing is the union of its grants', none
    when any grant holds it unnarrowed."""
    holdings = permissions.groups_in(workspace.key)
    roles: dict[str, GrantRoleResponse] = {}
    held: list[HeldGroup] = []
    for holding in holdings:
        roles.setdefault(
            holding.role_key, GrantRoleResponse(key=holding.role_key, name=holding.role_name)
        )
    for group in GROUPS.values():
        granting = [holding for holding in holdings if group.key in holding.groups]
        if not granting:
            continue
        narrowed = group.narrowable and all(
            holding.applications or holding.record_types for holding in granting
        )
        held.append(
            HeldGroup(
                key=group.key,
                name=group.name,
                applications=sorted({key for item in granting for key in item.applications})
                if narrowed
                else [],
                recordTypes=sorted({key for item in granting for key in item.record_types})
                if narrowed
                else [],
                sources=[
                    PermissionSource(
                        grantId=holding.grant_id,
                        role=roles[holding.role_key],
                        scope="instance" if holding.workspace_key is None else "workspace",
                        group=GrantPrincipalResponse(
                            kind="group",
                            id=holding.through_group_id,
                            name=holding.through_group_name or "",
                        )
                        if holding.through_group_id
                        else None,
                    )
                    for holding in granting
                ],
            )
        )
    return PermissionsResponse(
        workspaceKey=workspace.key,
        workspaceLabel=workspace.label,
        roles=list(roles.values()),
        actionGroups=held,
    )
