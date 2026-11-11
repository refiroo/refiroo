"""Action groups, roles, groups, grants, a workspace's access and the caller's permissions (Product
0.12 Z1, ADR-044, API.md § Security).

Everything but the caller's own permissions and grants needs Security administration at the
instance.
"""

from fastapi import APIRouter, Query, Request, Response

from ...engine.authorization import administration
from ...engine.workspaces.catalogue import resolve_workspace
from ...models.commands import (
    GrantCreate,
    GroupCreate,
    GroupMemberAdd,
    GroupMembersAdd,
    GroupMembersRemove,
    GroupUpdate,
    RoleCreate,
    RoleUpdate,
)
from ..access import INSTANCE, SIGNED_IN, AuthorizedRoute, CurrentPermissions, requires
from ..dependencies import CurrentPrincipal, DbSession
from ..paging import PageQuery
from ..projections import authorization as present
from ..schemas.authorization import (
    ActionGroupList,
    GrantOption,
    GrantOptionsResponse,
    GrantPage,
    GrantResponse,
    GroupMemberPage,
    GroupMemberResponse,
    GroupMembersResult,
    GroupPage,
    GroupResponse,
    HeldAnywhereList,
    PermissionsResponse,
    RolePage,
    RoleResponse,
)

router = APIRouter(route_class=AuthorizedRoute, prefix="/api/v1", tags=["security"])

_PAGE_SIZE = Query(default=50, ge=1, le=500, alias="pageSize")


@router.get("/me/permissions", response_model=PermissionsResponse)
@requires("signed-in", at=SIGNED_IN)
def get_my_permissions(
    permissions: CurrentPermissions,
    session: DbSession,
    workspace_key: str | None = Query(default=None, alias="workspaceKey"),
) -> PermissionsResponse:
    """The action groups the caller holds in a workspace (the default workspace without
    ``workspaceKey``), each with its narrowing and the grants it comes from."""
    workspace = resolve_workspace(session, workspace_key)
    return present.permissions_response(session, permissions, workspace)


@router.get("/me/action-groups", response_model=HeldAnywhereList)
@requires("signed-in", at=SIGNED_IN)
def get_my_action_groups(permissions: CurrentPermissions, session: DbSession) -> HeldAnywhereList:
    """Every action group the caller holds anywhere: at the instance, or in which workspaces
    (D328). The interface lists a settings page to whoever holds its group somewhere."""
    return present.held_anywhere(session, permissions)


@router.get("/me/grants", response_model=GrantPage)
@requires("signed-in", at=SIGNED_IN)
def list_my_grants(
    principal: CurrentPrincipal, session: DbSession, paging: PageQuery, page_size: int = _PAGE_SIZE
) -> GrantPage:
    """The caller's grants: direct, and for a person those of their groups, whose ``principal``
    is then the group (D284)."""
    return present.grant_page(
        session,
        administration.own_grant_page(
            session, principal.kind, principal.row_id, page=paging, page_size=page_size
        ),
    )


@router.get("/action-groups", response_model=ActionGroupList)
@requires("security.manage", at=INSTANCE)
def list_action_groups(request: Request) -> ActionGroupList:
    """The catalogue roles are made of: each action group with its actions and the operations
    declaring them (D227, D256)."""
    return present.action_groups(request.app.openapi())


@router.get("/roles", response_model=RolePage)
@requires("security.manage", at=INSTANCE)
def list_roles(session: DbSession, paging: PageQuery, page_size: int = _PAGE_SIZE) -> RolePage:
    """The predefined roles, then custom ones as created."""
    return present.role_page(
        session, administration.role_page(session, page=paging, page_size=page_size)
    )


@router.post("/roles", response_model=RoleResponse, status_code=201)
@requires("security.manage", at=INSTANCE)
def post_role(payload: RoleCreate, session: DbSession) -> RoleResponse:
    """A custom role from ``actionGroups``, or copied from another role (``copiedFrom``); its key
    comes from its name."""
    return present.role_response(session, administration.create_role(session, payload))


@router.get("/roles/{role_key}", response_model=RoleResponse)
@requires("security.manage", at=INSTANCE)
def get_role(role_key: str, session: DbSession) -> RoleResponse:
    return present.role_response(session, administration.load_role(session, role_key))


@router.patch("/roles/{role_key}", response_model=RoleResponse)
@requires("security.manage", at=INSTANCE)
def patch_role(role_key: str, payload: RoleUpdate, session: DbSession) -> RoleResponse:
    """Change a custom role; a predefined one answers ``409 ROLE_PREDEFINED``. Its holders gain or
    lose the groups on their next request."""
    return present.role_response(session, administration.update_role(session, role_key, payload))


@router.delete("/roles/{role_key}", status_code=204)
@requires("security.manage", at=INSTANCE)
def delete_role(role_key: str, session: DbSession) -> Response:
    """Delete a custom role no grant gives (``409 ROLE_IN_USE`` otherwise)."""
    administration.delete_role(session, role_key)
    return Response(status_code=204)


@router.get("/groups", response_model=GroupPage)
@requires("security.manage", at=INSTANCE)
def list_groups(
    session: DbSession,
    paging: PageQuery,
    q: str | None = Query(default=None, max_length=200),
    member_id: str | None = Query(default=None, alias="memberId"),
    page_size: int = _PAGE_SIZE,
) -> GroupPage:
    """Groups as created; ``q`` matches the name, ``memberId`` keeps a person's groups (D300)."""
    return present.group_page(
        session,
        administration.group_page(
            session, q=q, member_id=member_id, page=paging, page_size=page_size
        ),
    )


@router.post("/groups", response_model=GroupResponse, status_code=201)
@requires("security.manage", at=INSTANCE)
def post_group(payload: GroupCreate, session: DbSession) -> GroupResponse:
    """A local group of people; a grant to it applies to its members (D229). With ``source``, a
    provider group made ahead of its members' sign-ins (``409 GROUP_CLAIM_TAKEN`` when the claim
    value has a group already, I3, D364)."""
    return present.group_response(session, administration.create_group(session, payload))


@router.get("/groups/{group_id}", response_model=GroupResponse)
@requires("security.manage", at=INSTANCE)
def get_group(group_id: str, session: DbSession) -> GroupResponse:
    return present.group_response(session, administration.load_group(session, group_id))


@router.patch("/groups/{group_id}", response_model=GroupResponse)
@requires("security.manage", at=INSTANCE)
def patch_group(group_id: str, payload: GroupUpdate, session: DbSession) -> GroupResponse:
    return present.group_response(session, administration.update_group(session, group_id, payload))


@router.delete("/groups/{group_id}", status_code=204)
@requires("security.manage", at=INSTANCE)
def delete_group(group_id: str, session: DbSession) -> Response:
    """Delete a group with its memberships and grants."""
    administration.delete_group(session, group_id)
    return Response(status_code=204)


@router.get("/groups/{group_id}/members", response_model=GroupMemberPage)
@requires("security.manage", at=INSTANCE)
def list_group_members(
    group_id: str, session: DbSession, paging: PageQuery, page_size: int = _PAGE_SIZE
) -> GroupMemberPage:
    return present.member_page(
        session,
        administration.load_group(session, group_id),
        administration.member_page(session, group_id, page=paging, page_size=page_size),
    )


@router.post("/groups/{group_id}/members", response_model=GroupMemberResponse, status_code=201)
@requires("security.manage", at=INSTANCE)
def post_group_member(
    group_id: str, payload: GroupMemberAdd, session: DbSession
) -> GroupMemberResponse:
    """Add a person to the group; adding one already in it changes nothing. A provider group's
    members come from sign-ins (``409 GROUP_FROM_PROVIDER``)."""
    return present.member_response(administration.add_member(session, group_id, payload.userId))


@router.post("/groups/{group_id}/members/batch", response_model=GroupMembersResult)
@requires("security.manage", at=INSTANCE)
def post_group_members(
    group_id: str, payload: GroupMembersAdd, session: DbSession
) -> GroupMembersResult:
    """Add several people at once, by their IDs or by e-mail addresses as pasted (in
    any case), up to 500, in one transaction (0.12 SP1b, D401). Each input answers what it did:
    ``added``, ``alreadyMember``, ``deactivated`` (not added) or ``notFound``; with ``dryRun``
    ``toAdd`` in place of ``added`` and nothing changes. A provider group's members come from
    sign-ins (``409 GROUP_FROM_PROVIDER``)."""
    return present.members_result(
        administration.add_members(
            session,
            group_id,
            user_ids=payload.userIds,
            identifiers=payload.identifiers,
            dry_run=payload.dryRun,
        )
    )


@router.post("/groups/{group_id}/members/removal", response_model=GroupMembersResult)
@requires("security.manage", at=INSTANCE)
def post_group_members_removal(
    group_id: str, payload: GroupMembersRemove, session: DbSession
) -> GroupMembersResult:
    """Take several people out at once, up to 500, in one transaction (0.12 SP1b, D402): each
    answers ``removed``, ``notMember`` or ``notFound``. Refused whole when it would leave no
    Security administrator (``409 LAST_SECURITY_ADMINISTRATOR``, D283)."""
    return present.members_result(administration.remove_members(session, group_id, payload.userIds))


@router.delete("/groups/{group_id}/members/{user_id}", status_code=204)
@requires("security.manage", at=INSTANCE)
def delete_group_member(group_id: str, user_id: str, session: DbSession) -> Response:
    """Take a person out of the group; its grants stop applying to them on their next request."""
    administration.remove_member(session, group_id, user_id)
    return Response(status_code=204)


@router.get("/grants", response_model=GrantPage)
@requires("security.manage", at=INSTANCE)
def list_grants(
    session: DbSession,
    paging: PageQuery,
    principal_id: str | None = Query(default=None, alias="principalId"),
    workspace_key: str | None = Query(default=None, alias="workspaceKey"),
    role_key: str | None = Query(default=None, alias="roleKey"),
    consumer_api: str | None = Query(default=None, alias="consumerApi"),
    page_size: int = _PAGE_SIZE,
) -> GrantPage:
    """Grants as made; ``principalId`` names a person, client or group, ``workspaceKey`` the grants
    made in that workspace, ``roleKey`` a role, ``consumerApi`` the grants of a consumer API."""
    return present.grant_page(
        session,
        administration.grant_page(
            session,
            principal_id=principal_id,
            workspace_key=workspace_key,
            role_key=role_key,
            consumer_api=consumer_api,
            page=paging,
            page_size=page_size,
        ),
    )


@router.post("/grants", response_model=GrantResponse, status_code=201)
@requires("security.manage", at=INSTANCE)
def post_grant(payload: GrantCreate, session: DbSession) -> GrantResponse:
    """Give a role to a person, client or group, at the instance or in a workspace, optionally
    narrowing writes to applications and record types of its model (``422 GRANT_SCOPE_UNKNOWN``
    otherwise). A role whose every action group is held only at the instance is granted there
    (``422 GRANT_SCOPE_INVALID`` in a workspace, D302). Instead of ``role``, ``consumerApi`` grants
    read of a consumer API the workspace's model declares, in one workspace and never narrowed,
    to a client only (``422 CONSUMER_API_CLIENTS_ONLY`` for a person or a group, D306). It applies from the principal's next request."""
    return present.grant_response(session, administration.create_grant(session, payload))


@router.delete("/grants/{grant_id}", status_code=204)
@requires("security.manage", at=INSTANCE)
def delete_grant(grant_id: str, session: DbSession) -> Response:
    """Remove a grant; it stops applying on the principal's next request. Removing the last active
    person's Security administration answers ``409 LAST_SECURITY_ADMINISTRATOR``."""
    administration.delete_grant(session, grant_id)
    return Response(status_code=204)


@router.get("/users/{user_id}/grants", response_model=GrantPage)
@requires("security.manage", at=INSTANCE)
def list_user_grants(
    user_id: str, session: DbSession, paging: PageQuery, page_size: int = _PAGE_SIZE
) -> GrantPage:
    """A person's grants: those made to them and those of their groups, a group's naming the group
    (D299)."""
    return present.grant_page(
        session,
        administration.user_grant_page(session, user_id, page=paging, page_size=page_size),
    )


@router.get("/workspaces/{workspace_key}/grant-options", response_model=GrantOptionsResponse)
@requires("security.manage", at=INSTANCE)
def get_grant_options(workspace_key: str, session: DbSession) -> GrantOptionsResponse:
    """What a grant in the workspace can name: the applications, record types and consumer APIs
    of its model, by key and name, without Browse there (D355)."""
    found = administration.grant_options(session, workspace_key)

    def listed(items: tuple[tuple[str, str], ...]) -> list[GrantOption]:
        return [GrantOption(key=key, name=name) for key, name in items]

    return GrantOptionsResponse(
        applications=listed(found.applications),
        recordTypes=listed(found.record_types),
        consumerApis=listed(found.consumer_apis),
    )


@router.get("/workspaces/{workspace_key}/access", response_model=GrantPage)
@requires("security.manage", at=INSTANCE)
def list_workspace_access(
    workspace_key: str, session: DbSession, paging: PageQuery, page_size: int = _PAGE_SIZE
) -> GrantPage:
    """Who can do what here: every grant that applies in the workspace, made there or at the
    instance; a grant to a group names the group (J40.7)."""
    return present.grant_page(
        session,
        administration.access_page(session, workspace_key, page=paging, page_size=page_size),
    )
