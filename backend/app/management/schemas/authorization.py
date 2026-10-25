"""Action groups, roles, groups, grants and the caller's permissions (Product 0.12 Z1, API.md §
Security)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from .common import CollectionPage
from .identity import SignInProviderRef


class OperationRef(BaseModel):
    method: str
    path: str


class ActionResponse(BaseModel):
    key: str
    description: str
    operations: list[OperationRef] = Field(description="The operations declaring this action")


class ActionGroupResponse(BaseModel):
    key: str
    name: str
    description: str
    grantableAt: Literal["workspace", "instance"] = Field(
        description="workspace: in a workspace or at the instance; instance: only at the instance"
    )
    narrowable: bool = Field(
        description="Whether a grant's applications and record types narrow it (writes only)"
    )
    actions: list[ActionResponse]


class ActionGroupList(BaseModel):
    items: list[ActionGroupResponse]


class RoleResponse(BaseModel):
    key: str
    name: str
    description: str | None
    predefined: bool = Field(description="A predefined role is read-only")
    actionGroups: list[str]
    grants: int = Field(description="How many grants give this role")
    version: int
    createdAt: datetime
    updatedAt: datetime


class RolePage(CollectionPage[RoleResponse]):
    """Roles: the predefined ones first, then custom ones as created (ADR-030)."""


class GroupSourceResponse(BaseModel):
    """A provider group's provider and the groups claim's value it stands for (0.12 I3, D364)."""

    provider: SignInProviderRef
    claimValue: str


class GroupResponse(BaseModel):
    id: str
    name: str
    description: str | None
    source: GroupSourceResponse | None = Field(
        description="A provider group's source; its members come from sign-ins. Null: local"
    )
    members: int
    version: int
    createdAt: datetime
    updatedAt: datetime


class GroupPage(CollectionPage[GroupResponse]):
    """Groups in the order they were created (ADR-030)."""


class GroupMemberResponse(BaseModel):
    id: str
    username: str
    name: str
    active: bool
    seenAt: datetime | None = Field(
        default=None, description="A provider group's member: when a sign-in last named them in it"
    )


class GroupMemberPage(CollectionPage[GroupMemberResponse]):
    """A group's members in the order they were created (ADR-030)."""


class GrantPrincipalResponse(BaseModel):
    kind: Literal["user", "client", "group"]
    id: str
    name: str


class GrantRoleResponse(BaseModel):
    key: str
    name: str


class GrantScopeResponse(BaseModel):
    instance: bool = Field(description="True for the whole instance, every workspace included")
    workspaceKey: str | None
    applications: list[str] = Field(description="Writes narrowed to these applications")
    recordTypes: list[str] = Field(description="Writes narrowed to these record types")
    applicationNames: list[str] = Field(
        description="The applications' names in the workspace's model, in the order of "
        "applications; a key the model no longer has is given as it is"
    )
    recordTypeNames: list[str] = Field(
        description="The record types' names in the workspace's model, in the order of recordTypes"
    )
    missingApplications: list[str] = Field(
        description="Applications of the narrowing the workspace's model no longer has (D296)"
    )
    missingRecordTypes: list[str] = Field(
        description="Record types of the narrowing the workspace's model no longer has (D296)"
    )


class GrantConsumerApiResponse(BaseModel):
    key: str
    name: str | None = Field(
        description="The consumer API's name in the workspace's model; null when it no longer "
        "declares the API"
    )


class GrantResponse(BaseModel):
    id: str
    principal: GrantPrincipalResponse
    role: GrantRoleResponse | None = Field(description="The role; null for a consumer API grant")
    consumerApi: GrantConsumerApiResponse | None = Field(
        description="The consumer API this grant lets its holder read in its workspace, instead of "
        "a role (Z3, D306); null for a role grant"
    )
    scope: GrantScopeResponse
    stale: bool = Field(
        description="The narrowing names an application or record type the workspace's model no "
        "longer has, or the consumer API it grants is no longer declared; those allow nothing, and "
        "a grant naming only such allows no writes (D296, D306)"
    )
    createdAt: datetime


class GrantPage(CollectionPage[GrantResponse]):
    """Grants in the order they were made (ADR-030)."""


class PermissionSource(BaseModel):
    grantId: str
    role: GrantRoleResponse
    scope: Literal["workspace", "instance"]
    group: GrantPrincipalResponse | None = Field(
        description="The group the grant reaches the caller through; null for a direct grant"
    )


class HeldGroup(BaseModel):
    key: str
    name: str
    applications: list[str] = Field(
        description="Writes narrowed to these applications; empty when not narrowed"
    )
    recordTypes: list[str] = Field(
        description="Writes narrowed to these record types; empty when not narrowed"
    )
    stale: bool = Field(
        description="The narrowing names an application or record type the workspace's model no "
        "longer has, which allows nothing (D296)"
    )
    sources: list[PermissionSource]


class PermissionsResponse(BaseModel):
    workspaceKey: str
    workspaceLabel: str
    roles: list[GrantRoleResponse] = Field(description="The roles that apply in the workspace")
    actionGroups: list[HeldGroup] = Field(
        description="The action groups the caller holds in the workspace, from grants there or at "
        "the instance"
    )


class HeldWorkspace(BaseModel):
    key: str
    label: str


class HeldAnywhere(BaseModel):
    """An action group the caller holds somewhere (Z5, D328)."""

    key: str
    name: str
    instance: bool = Field(description="Held at the instance, so in every workspace")
    workspaces: list[HeldWorkspace] = Field(
        description="The workspaces it is held in, by label; empty when held at the instance"
    )


class HeldAnywhereList(BaseModel):
    items: list[HeldAnywhere] = Field(description="In the catalogue's order")


class GrantOption(BaseModel):
    key: str
    name: str


class GrantOptionsResponse(BaseModel):
    """What a grant in a workspace can name, from the workspace's model (0.12 SP2, D355)."""

    applications: list[GrantOption] = Field(description="Applications a grant may narrow to")
    recordTypes: list[GrantOption] = Field(description="Record types a grant may narrow to")
    consumerApis: list[GrantOption] = Field(description="Consumer APIs a grant may name")
