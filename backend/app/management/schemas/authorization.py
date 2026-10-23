"""Action groups, roles, groups, grants and the caller's permissions (Product 0.12 Z1, API.md §
Security)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from .common import CollectionPage


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


class GroupResponse(BaseModel):
    id: str
    name: str
    description: str | None
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


class GrantResponse(BaseModel):
    id: str
    principal: GrantPrincipalResponse
    role: GrantRoleResponse
    scope: GrantScopeResponse
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
    sources: list[PermissionSource]


class PermissionsResponse(BaseModel):
    workspaceKey: str
    workspaceLabel: str
    roles: list[GrantRoleResponse] = Field(description="The roles that apply in the workspace")
    actionGroups: list[HeldGroup] = Field(
        description="The action groups the caller holds in the workspace, from grants there or at "
        "the instance"
    )
