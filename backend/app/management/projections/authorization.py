"""Action groups, roles, groups, grants and permissions as the API answers them (Product 0.12 Z1)."""

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...common.pagination import Page
from ...engine.authorization import administration
from ...engine.authorization.administration import GrantRow
from ...engine.authorization.catalogue import ACTIONS, GROUPS
from ...engine.authorization.permissions import Permissions
from ...engine.identity import providers
from ...engine.model.registry import resolve_model_snapshot
from ...models.database import Grant, Role, User, UserGroup, Workspace
from ..schemas.authorization import (
    ActionGroupList,
    ActionGroupResponse,
    ActionResponse,
    GrantConsumerApiResponse,
    GrantPage,
    GrantPrincipalResponse,
    GrantResponse,
    GrantRoleResponse,
    GrantScopeResponse,
    GroupMemberOutcome,
    GroupMemberPage,
    GroupMemberResponse,
    GroupMembersResult,
    GroupPage,
    GroupResponse,
    GroupSourceResponse,
    HeldAnywhere,
    HeldAnywhereList,
    HeldGroup,
    HeldWorkspace,
    OperationRef,
    PermissionSource,
    PermissionsResponse,
    RolePage,
    RoleResponse,
)
from ..schemas.identity import SignInProviderRef


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
    source = None
    if group.provider_id is not None and group.claim_value is not None:
        key, name = providers.names(session, ids=[group.provider_id])[group.provider_id]
        source = GroupSourceResponse(
            provider=SignInProviderRef(key=key, name=name), claimValue=group.claim_value
        )
    return GroupResponse(
        id=group.public_id,
        name=group.name,
        description=group.description,
        source=source,
        members=administration.member_count(session, group),
        version=group.version,
        createdAt=group.created_at,
        updatedAt=group.updated_at,
    )


def group_page(session: Session, page: Page[UserGroup]) -> GroupPage:
    return GroupPage(items=[group_response(session, group) for group in page.items], **page.links())


def member_response(user: User, seen_at: datetime | None = None) -> GroupMemberResponse:
    return GroupMemberResponse(
        id=user.public_id,
        email=user.email,
        name=user.name,
        active=user.active,
        seenAt=seen_at,
    )


def members_result(outcomes: list[administration.MemberOutcome]) -> GroupMembersResult:
    """Each input's outcome of several people added or removed (0.12 SP1b)."""
    return GroupMembersResult(
        items=[
            GroupMemberOutcome(
                input=item.input,
                outcome=item.outcome,
                member=member_response(item.user) if item.user is not None else None,
            )
            for item in outcomes
        ],
        changed=sum(item.outcome in ("added", "removed") for item in outcomes),
    )


def member_page(session: Session, group: UserGroup, page: Page[User]) -> GroupMemberPage:
    seen = administration.seen(session, group, [user.id for user in page.items])
    return GroupMemberPage(
        items=[member_response(user, seen.get(user.id)) for user in page.items], **page.links()
    )


def _model_names(session: Session, workspace_key: str, kind: str) -> dict[str, str]:
    model = resolve_model_snapshot(session, workspace_key).model
    items = model.applications if kind == "applications" else model.objectTypes
    return {item.key: item.name for item in items}


def _names(session: Session, workspace_key: str, kind: str, keys: list[str]) -> list[str]:
    """The names of a narrowing's keys in the workspace's model; a key it lacks as it is."""
    if not keys:
        return []
    names = _model_names(session, workspace_key, kind)
    return [names.get(key, key) for key in keys]


def _missing(session: Session, workspace_key: str | None, kind: str, keys: list[str]) -> list[str]:
    """A narrowing's keys the workspace's model no longer has (D296)."""
    if not keys or workspace_key is None:
        return []
    names = _model_names(session, workspace_key, kind)
    return [key for key in keys if key not in names]


def _consumer_api(session: Session, grant: Grant) -> GrantConsumerApiResponse | None:
    """A consumer API grant's API with its name in the workspace's model; no name when the model no
    longer declares it (D306)."""
    if grant.consumer_api is None or grant.workspace_key is None:
        return None
    model = resolve_model_snapshot(session, grant.workspace_key).model
    names = {item.key: item.name for item in model.consumerApis or ()}
    return GrantConsumerApiResponse(key=grant.consumer_api, name=names.get(grant.consumer_api))


def grant_response(session: Session, row: GrantRow) -> GrantResponse:
    grant = row.grant
    workspace = grant.workspace_key
    missing_applications = _missing(session, workspace, "applications", list(grant.applications))
    missing_types = _missing(session, workspace, "recordTypes", list(grant.record_types))
    consumer_api = _consumer_api(session, grant)
    return GrantResponse(
        id=grant.public_id,
        principal=GrantPrincipalResponse(
            kind=row.principal_kind, id=row.principal_id, name=row.principal_name
        ),
        role=GrantRoleResponse(key=row.role.key, name=row.role.name) if row.role else None,
        consumerApi=consumer_api,
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
            missingApplications=missing_applications,
            missingRecordTypes=missing_types,
        ),
        stale=bool(
            missing_applications or missing_types or (consumer_api and consumer_api.name is None)
        ),
        createdAt=grant.created_at,
    )


def grant_page(session: Session, page: Page[GrantRow]) -> GrantPage:
    return GrantPage(items=[grant_response(session, row) for row in page.items], **page.links())


def permissions_response(
    session: Session, permissions: Permissions, workspace: Workspace
) -> PermissionsResponse:
    """What the caller holds in a workspace; a group's narrowing is the union of its grants', none
    when any grant holds it unnarrowed (D289)."""
    holdings = permissions.groups_in(workspace.key)
    known: dict[str, set[str]] = {}

    def stale(applications: list[str], types: list[str]) -> bool:
        if not applications and not types:
            return False
        if not known:
            known["applications"] = set(_model_names(session, workspace.key, "applications"))
            known["recordTypes"] = set(_model_names(session, workspace.key, "recordTypes"))
        return not (
            set(applications) <= known["applications"] and set(types) <= known["recordTypes"]
        )

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
        applications = (
            sorted({key for item in granting for key in item.applications}) if narrowed else []
        )
        types = sorted({key for item in granting for key in item.record_types}) if narrowed else []
        held.append(
            HeldGroup(
                key=group.key,
                name=group.name,
                applications=applications,
                recordTypes=types,
                stale=stale(applications, types),
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


def held_anywhere(session: Session, permissions: Permissions) -> HeldAnywhereList:
    """Every group the caller holds, at the instance or in which workspaces (D328)."""
    where: dict[str, set[str] | None] = {}
    for holding in permissions.holdings:
        for key in holding.groups:
            if holding.workspace_key is None:
                where[key] = None
            elif where.get(key, set()) is not None:
                where.setdefault(key, set()).add(holding.workspace_key)
    keys = {key for workspaces in where.values() if workspaces for key in workspaces}
    labels = (
        dict(
            session.execute(
                select(Workspace.key, Workspace.label).where(Workspace.key.in_(keys))
            ).all()
        )
        if keys
        else {}
    )
    items = []
    for group in GROUPS.values():
        if group.key not in where:
            continue
        workspaces = where[group.key]
        items.append(
            HeldAnywhere(
                key=group.key,
                name=group.name,
                instance=workspaces is None,
                workspaces=sorted(
                    (
                        HeldWorkspace(key=key, label=labels[key])
                        for key in workspaces or ()
                        if key in labels
                    ),
                    key=lambda item: (item.label.casefold(), item.key),
                ),
            )
        )
    return HeldAnywhereList(items=items)
