"""Roles, groups and grants, as a Security administrator manages them (Product 0.12 Z1, ADR-044).

Predefined roles are read-only (``ROLE_PREDEFINED``); a role still granted is not deleted
(``ROLE_IN_USE``). A grant names one principal, a role and a scope; a workspace grant may narrow
writes to applications and record types of that workspace's model (``GRANT_SCOPE_UNKNOWN``
otherwise, D281); an instance grant is never narrowed. No change may leave the instance without an
active person holding Security administration there (``LAST_SECURITY_ADMINISTRATOR``, D283).
"""

import re
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Select, delete, exists, func, or_, select, union_all
from sqlalchemy.orm import Session

from ...common.pagination import Page, PageRequest, integer_key, paginate_statement
from ...errors import ApiError, api_error
from ...models.commands import (
    GrantCreate,
    GroupCreate,
    GroupUpdate,
    RoleCreate,
    RoleUpdate,
)
from ...models.database import (
    Grant,
    OAuthClient,
    Role,
    RoleActionGroup,
    User,
    UserGroup,
    UserGroupMember,
    Workspace,
)
from ..identity import security_events
from ..model.registry import resolve_model_snapshot
from ..reads.object_query import name_contains
from ..workspaces.catalogue import load_workspace
from .catalogue import FIRST_ADMINISTRATOR_ROLES, GROUPS, PREDEFINED_ROLES
from .permissions import role_groups

# --- shared ---------------------------------------------------------------------------------------


def _changing[T](session: Session, change: Callable[[], T], *, guard: bool = False) -> T:
    """Run ``change`` and commit; with ``guard``, refuse it when it leaves no Security
    administrator who had one before (D283)."""
    try:
        before = security_administrators(session) if guard else 0
        result = change()
        session.flush()
        if guard:
            refuse_last_administrator(session, before)
        session.commit()
    except ApiError:
        session.rollback()
        raise
    return result


def _stale(what: str, current: int) -> ApiError:
    return api_error(
        409, "VERSION_CONFLICT", f"{what} version has changed", {"currentVersion": current}
    )


def _holding_roles(group_key: str) -> Select[tuple[int]]:
    """A statement selecting the roles that hold ``group_key``: predefined by the catalogue,
    custom by their rows."""
    predefined = [key for key, groups in PREDEFINED_ROLES.items() if group_key in groups]
    return select(Role.id).where(
        or_(
            Role.predefined.is_(True) & Role.key.in_(predefined),
            Role.predefined.is_(False)
            & exists().where(
                (RoleActionGroup.role_id == Role.id) & (RoleActionGroup.group_key == group_key)
            ),
        )
    )


def security_administrators(session: Session) -> int:
    """Active people holding Security administration at the instance, directly or through a group
    (D283); clients do not count."""
    roles = _holding_roles("security-admin")
    instance = (Grant.workspace_key.is_(None)) & Grant.role_id.in_(roles)
    direct = select(Grant.user_id).where(instance, Grant.user_id.is_not(None))
    grouped = (
        select(UserGroupMember.user_id)
        .join(Grant, Grant.group_id == UserGroupMember.group_id)
        .where(instance)
    )
    return (
        session.scalar(
            select(func.count(User.id)).where(
                User.active.is_(True), or_(User.id.in_(direct), User.id.in_(grouped))
            )
        )
        or 0
    )


# --- roles ----------------------------------------------------------------------------------------


def known_groups(keys: list[str]) -> list[str]:
    """``keys`` in the catalogue's order; an unknown one is ``422 ACTION_GROUP_UNKNOWN``."""
    unknown = sorted(set(keys) - set(GROUPS))
    if unknown:
        raise api_error(
            422,
            "ACTION_GROUP_UNKNOWN",
            f"No action group '{unknown[0]}'",
            {"actionGroups": unknown},
        )
    return [key for key in GROUPS if key in set(keys)]


def custom_groups(session: Session, role: Role) -> list[str]:
    return list(
        session.scalars(select(RoleActionGroup.group_key).where(RoleActionGroup.role_id == role.id))
    )


def groups_of(session: Session, role: Role) -> tuple[str, ...]:
    return role_groups(role, None if role.predefined else custom_groups(session, role))


def load_role(session: Session, key: str, *, for_update: bool = False) -> Role:
    statement = select(Role).where(Role.key == key)
    role = session.scalar(statement.with_for_update() if for_update else statement)
    if role is None:
        raise api_error(404, "ROLE_NOT_FOUND", f"Role '{key}' not found")
    return role


def role_page(session: Session, *, page: PageRequest, page_size: int) -> Page[Role]:
    """Roles: the predefined ones in the catalogue's order, then custom ones as created."""
    return paginate_statement(
        session,
        select(Role),
        keys=(integer_key("sequenceId", Role.id, "id"),),
        scope="roles",
        filters={},
        page=page,
        page_size=page_size,
        message="Role list cursor is invalid",
    )


def holders(session: Session, role: Role) -> int:
    return session.scalar(select(func.count(Grant.id)).where(Grant.role_id == role.id)) or 0


def _name_taken(session: Session, name: str, other: int | None = None) -> None:
    statement = select(Role.id).where(func.lower(Role.name) == name.lower())
    if other is not None:
        statement = statement.where(Role.id != other)
    if session.scalar(statement) is not None:
        raise api_error(409, "ROLE_NAME_TAKEN", f"Another role is named '{name}'")


def _role_key(session: Session, name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:56] or "role"
    key, number = base, 1
    while session.scalar(select(Role.id).where(Role.key == key)) is not None:
        number += 1
        key = f"{base}-{number}"
    return key


def create_role(session: Session, payload: RoleCreate) -> Role:
    def change() -> Role:
        _name_taken(session, payload.name)
        if payload.actionGroups is not None:
            keys = known_groups(payload.actionGroups)
        elif payload.copiedFrom is not None:
            keys = list(groups_of(session, load_role(session, payload.copiedFrom)))
        else:
            keys = []
        role = Role(
            key=_role_key(session, payload.name),
            name=payload.name,
            description=payload.description,
            predefined=False,
        )
        session.add(role)
        session.flush()
        session.add_all(RoleActionGroup(role_id=role.id, group_key=key) for key in keys)
        security_events.record(
            session, "role", role.key, "created",
            details={"name": role.name, "actionGroups": keys},
        )  # fmt: skip
        return role

    return _changing(session, change)


def _custom(role: Role) -> None:
    if role.predefined:
        raise api_error(
            409,
            "ROLE_PREDEFINED",
            f"'{role.name}' is a predefined role and cannot change; copy it to make your own",
        )


def update_role(session: Session, key: str, payload: RoleUpdate) -> Role:
    def change() -> Role:
        role = load_role(session, key, for_update=True)
        _custom(role)
        if role.version != payload.expectedVersion:
            raise _stale("Role", role.version)
        fields = payload.model_fields_set
        if "name" in fields and payload.name is not None:
            _name_taken(session, payload.name, role.id)
            role.name = payload.name
        if "description" in fields:
            role.description = payload.description
        if "actionGroups" in fields and payload.actionGroups is not None:
            keys = known_groups(payload.actionGroups)
            session.execute(delete(RoleActionGroup).where(RoleActionGroup.role_id == role.id))
            session.add_all(RoleActionGroup(role_id=role.id, group_key=item) for item in keys)
        role.version += 1
        role.updated_at = datetime.now(UTC)
        security_events.record(
            session, "role", role.key, "updated", version=role.version,
            details=security_events.changed(
                sorted(fields), name=role.name, actionGroups=payload.actionGroups
            ),
        )  # fmt: skip
        return role

    return _changing(session, change, guard=True)


def delete_role(session: Session, key: str) -> None:
    def change() -> None:
        role = load_role(session, key, for_update=True)
        _custom(role)
        if holders(session, role):
            raise api_error(
                409,
                "ROLE_IN_USE",
                f"'{role.name}' is still granted; remove its grants first",
                {"grants": holders(session, role)},
            )
        session.execute(delete(Role).where(Role.id == role.id))
        security_events.record(session, "role", role.key, "deleted", details={"name": role.name})

    _changing(session, change)


# --- groups ---------------------------------------------------------------------------------------


def load_group(session: Session, public_id: str, *, for_update: bool = False) -> UserGroup:
    statement = select(UserGroup).where(UserGroup.public_id == public_id)
    group = session.scalar(statement.with_for_update() if for_update else statement)
    if group is None:
        raise api_error(404, "GROUP_NOT_FOUND", f"Group '{public_id}' not found")
    return group


def group_page(
    session: Session,
    *,
    q: str | None = None,
    member_id: str | None = None,
    page: PageRequest,
    page_size: int,
) -> Page[UserGroup]:
    """Groups as created; ``q`` matches the name, ``memberId`` keeps a person's groups (D300)."""
    statement = select(UserGroup)
    if q:
        statement = statement.where(name_contains(UserGroup.name, q))
    if member_id is not None:
        statement = statement.where(
            UserGroup.id.in_(
                select(UserGroupMember.group_id)
                .join(User, User.id == UserGroupMember.user_id)
                .where(User.public_id == member_id)
            )
        )
    return paginate_statement(
        session,
        statement,
        keys=(integer_key("sequenceId", UserGroup.id, "id"),),
        scope="groups",
        filters={"q": q, "memberId": member_id},
        page=page,
        page_size=page_size,
        message="Group list cursor is invalid",
    )


def member_count(session: Session, group: UserGroup) -> int:
    return (
        session.scalar(
            select(func.count())
            .select_from(UserGroupMember)
            .where(UserGroupMember.group_id == group.id)
        )
        or 0
    )


def _group_name(session: Session, name: str, other: int | None = None) -> None:
    statement = select(UserGroup.id).where(func.lower(UserGroup.name) == name.lower())
    if other is not None:
        statement = statement.where(UserGroup.id != other)
    if session.scalar(statement) is not None:
        raise api_error(409, "GROUP_NAME_TAKEN", f"Another group is named '{name}'")


def create_group(session: Session, payload: GroupCreate) -> UserGroup:
    def change() -> UserGroup:
        _group_name(session, payload.name)
        group = UserGroup(name=payload.name, description=payload.description)
        session.add(group)
        session.flush()
        security_events.record(
            session, "group", group.public_id, "created", about=[group.public_id],
            details={"name": group.name},
        )  # fmt: skip
        return group

    return _changing(session, change)


def update_group(session: Session, public_id: str, payload: GroupUpdate) -> UserGroup:
    def change() -> UserGroup:
        group = load_group(session, public_id, for_update=True)
        if group.version != payload.expectedVersion:
            raise _stale("Group", group.version)
        fields = payload.model_fields_set
        if "name" in fields and payload.name is not None:
            _group_name(session, payload.name, group.id)
            group.name = payload.name
        if "description" in fields:
            group.description = payload.description
        group.version += 1
        group.updated_at = datetime.now(UTC)
        security_events.record(
            session, "group", group.public_id, "updated", about=[group.public_id],
            version=group.version, details=security_events.changed(sorted(fields), name=group.name),
        )  # fmt: skip
        return group

    return _changing(session, change)


def delete_group(session: Session, public_id: str) -> None:
    """A group, its memberships and its grants (D283 applies)."""

    def change() -> None:
        group = load_group(session, public_id, for_update=True)
        members = session.scalars(
            select(User.public_id)
            .join(UserGroupMember, UserGroupMember.user_id == User.id)
            .where(UserGroupMember.group_id == group.id)
        ).all()
        session.execute(delete(UserGroup).where(UserGroup.id == group.id))
        security_events.record(
            session, "group", group.public_id, "deleted", about=[group.public_id, *members],
            details={"name": group.name},
        )  # fmt: skip

    _changing(session, change, guard=True)


def member_page(
    session: Session, public_id: str, *, page: PageRequest, page_size: int
) -> Page[User]:
    group = load_group(session, public_id)
    statement = (
        select(User)
        .join(UserGroupMember, UserGroupMember.user_id == User.id)
        .where(UserGroupMember.group_id == group.id)
    )
    return paginate_statement(
        session,
        statement,
        keys=(integer_key("sequenceId", User.id, "id"),),
        scope=f"group-members:{public_id}",
        filters={},
        page=page,
        page_size=page_size,
        message="Group member list cursor is invalid",
    )


def _user(session: Session, public_id: str) -> User:
    user = session.scalar(select(User).where(User.public_id == public_id))
    if user is None:
        raise api_error(404, "USER_NOT_FOUND", f"User '{public_id}' not found")
    return user


def add_member(session: Session, public_id: str, user_id: str) -> User:
    def change() -> User:
        group = load_group(session, public_id, for_update=True)
        user = _user(session, user_id)
        member = session.get(UserGroupMember, (group.id, user.id))
        if member is None:
            session.add(UserGroupMember(group_id=group.id, user_id=user.id))
            security_events.record(
                session, "group", group.public_id, "member-added",
                about=[group.public_id, user.public_id],
                details={"groupName": group.name, "userId": user.public_id},
            )  # fmt: skip
        return user

    return _changing(session, change)


def remove_member(session: Session, public_id: str, user_id: str) -> None:
    def change() -> None:
        group = load_group(session, public_id, for_update=True)
        user = _user(session, user_id)
        removed = session.execute(
            delete(UserGroupMember).where(
                UserGroupMember.group_id == group.id, UserGroupMember.user_id == user.id
            )
        )
        if not removed.rowcount:
            raise api_error(
                404, "GROUP_MEMBER_NOT_FOUND", f"User '{user_id}' is not in group '{group.name}'"
            )
        security_events.record(
            session, "group", group.public_id, "member-removed",
            about=[group.public_id, user.public_id],
            details={"groupName": group.name, "userId": user.public_id},
        )  # fmt: skip

    _changing(session, change, guard=True)


# --- grants ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class GrantRow:
    """A grant with what it names, as the API answers it."""

    grant: Grant
    # None for a consumer API grant (D306).
    role: Role | None
    principal_kind: str
    principal_id: str
    principal_name: str


_GRANT_KEYS = (integer_key("sequenceId", Grant.id, "grant_sequence"),)


def _grant_statement() -> Select[Any]:
    return (
        select(Grant, Role, User, OAuthClient, UserGroup, Grant.id.label("grant_sequence"))
        .outerjoin(Role, Role.id == Grant.role_id)
        .outerjoin(User, User.id == Grant.user_id)
        .outerjoin(OAuthClient, OAuthClient.id == Grant.client_id)
        .outerjoin(UserGroup, UserGroup.id == Grant.group_id)
    )


def _grant_row(row: Any) -> GrantRow:
    grant, role, user, client, group = row[:5]
    principal = user or client or group
    kind = "user" if user is not None else "client" if client is not None else "group"
    return GrantRow(grant, role, kind, principal.public_id, principal.name)


def _principal_ids(session: Session, kind: str, public_id: str) -> dict[str, int]:
    model = {"user": User, "client": OAuthClient, "group": UserGroup}[kind]
    row_id = session.scalar(select(model.id).where(model.public_id == public_id))
    if row_id is None:
        code = {"user": "USER_NOT_FOUND", "client": "CLIENT_NOT_FOUND", "group": "GROUP_NOT_FOUND"}
        raise api_error(404, code[kind], f"No {kind} '{public_id}'")
    return {f"{kind}_id": row_id}


def _check_narrowing(
    session: Session, workspace_key: str, applications: list[str], types: list[str]
) -> None:
    """A workspace grant's narrowing names applications and record types of its model (D281)."""
    if not applications and not types:
        return
    model = resolve_model_snapshot(session, workspace_key).model
    unknown_applications = sorted(set(applications) - {item.key for item in model.applications})
    unknown_types = sorted(set(types) - {item.key for item in model.objectTypes})
    if unknown_applications or unknown_types:
        raise api_error(
            422,
            "GRANT_SCOPE_UNKNOWN",
            f"Workspace '{workspace_key}' has no "
            + (
                f"application '{unknown_applications[0]}'"
                if unknown_applications
                else f"record type '{unknown_types[0]}'"
            ),
            {"applications": unknown_applications, "recordTypes": unknown_types},
        )


def _held_in_a_workspace(session: Session, role: Role) -> None:
    """A workspace grant of a role whose every group is held only at the instance would allow
    nothing; it is refused (D302)."""
    groups = groups_of(session, role)
    if groups and all(GROUPS[group].reach == "instance" for group in groups):
        raise api_error(
            422,
            "GRANT_SCOPE_INVALID",
            f"{role.name} is granted at the instance (instance: true): its action groups are not "
            "held in a workspace",
            {"role": role.key},
        )


def _check_consumer_api(session: Session, workspace_key: str, consumer_api: str) -> None:
    """A consumer API grant names an API the workspace's model declares (D306)."""
    model = resolve_model_snapshot(session, workspace_key).model
    if consumer_api not in {item.key for item in model.consumerApis or ()}:
        raise api_error(
            422,
            "GRANT_SCOPE_UNKNOWN",
            f"Workspace '{workspace_key}' has no consumer API '{consumer_api}'",
            {"consumerApi": consumer_api},
        )


def create_grant(session: Session, payload: GrantCreate) -> GrantRow:
    scope = payload.scope
    if scope.instance == (scope.workspaceKey is not None):
        raise api_error(
            422,
            "GRANT_SCOPE_INVALID",
            "A grant's scope is either the instance (instance: true) or one workspace (workspaceKey)",
        )
    if payload.consumerApi is not None:
        return _create_consumer_api_grant(session, payload)
    if scope.instance and (scope.applications or scope.recordTypes):
        raise api_error(
            422,
            "GRANT_SCOPE_INVALID",
            "An instance grant is not narrowed; narrow a grant in one workspace",
        )

    def change() -> Grant:
        role = load_role(session, payload.role)
        principal = _principal_ids(session, payload.principal.kind, payload.principal.id)
        if scope.workspaceKey is not None:
            _held_in_a_workspace(session, role)
            load_workspace(session, scope.workspaceKey)
            _check_narrowing(session, scope.workspaceKey, scope.applications, scope.recordTypes)
        grant = Grant(
            role_id=role.id,
            workspace_key=scope.workspaceKey,
            applications=sorted(set(scope.applications)),
            record_types=sorted(set(scope.recordTypes)),
            **principal,
        )
        session.add(grant)
        return _granted(session, grant)

    grant = _changing(session, change)
    return load_grant(session, grant.public_id)


def _create_consumer_api_grant(session: Session, payload: GrantCreate) -> GrantRow:
    """Read of one consumer API in one workspace, never narrowed (D306)."""
    scope, consumer_api = payload.scope, payload.consumerApi
    assert consumer_api is not None
    if scope.workspaceKey is None or scope.applications or scope.recordTypes:
        raise api_error(
            422,
            "GRANT_SCOPE_INVALID",
            "A consumer API is granted in one workspace (workspaceKey), never at the instance or "
            "narrowed",
        )
    workspace_key = scope.workspaceKey

    def change() -> Grant:
        principal = _principal_ids(session, payload.principal.kind, payload.principal.id)
        load_workspace(session, workspace_key)
        _check_consumer_api(session, workspace_key, consumer_api)
        grant = Grant(
            consumer_api=consumer_api,
            workspace_key=workspace_key,
            applications=[],
            record_types=[],
            **principal,
        )
        session.add(grant)
        return _granted(session, grant)

    grant = _changing(session, change)
    return load_grant(session, grant.public_id)


def grant_roles(session: Session, kind: str, row_id: int, role_keys: tuple[str, ...]) -> None:
    """Give ``role_keys`` at the instance to a person or client (``create_admin``,
    ``create_client --role``, the harness); not committed."""
    roles = session.scalars(select(Role).where(Role.key.in_(role_keys))).all()
    missing = sorted(set(role_keys) - {role.key for role in roles})
    if missing:
        raise api_error(404, "ROLE_NOT_FOUND", f"Role '{missing[0]}' not found")
    session.add_all(
        Grant(
            role_id=role.id,
            workspace_key=None,
            applications=[],
            record_types=[],
            **{f"{kind}_id": row_id},
        )
        for role in roles
    )


def grant_first_administrator(session: Session, user_id: int) -> None:
    grant_roles(session, "user", user_id, FIRST_ADMINISTRATOR_ROLES)


def _grant_details(row: GrantRow) -> dict[str, Any]:
    grant = row.grant
    return {
        "principal": {
            "kind": row.principal_kind,
            "id": row.principal_id,
            "name": row.principal_name,
        },
        "role": {"key": row.role.key, "name": row.role.name} if row.role else None,
        "consumerApi": grant.consumer_api,
        "workspaceKey": grant.workspace_key,
        "applications": list(grant.applications or []),
        "recordTypes": list(grant.record_types or []),
    }


def _granted(session: Session, grant: Grant) -> Grant:
    """The grant just added, with its security event (D317), in the same transaction."""
    session.flush()
    row = load_grant(session, grant.public_id)
    security_events.record(
        session, "grant", grant.public_id, "created", about=[row.principal_id],
        details=_grant_details(row),
    )  # fmt: skip
    return grant


def load_grant(session: Session, public_id: str) -> GrantRow:
    row = session.execute(_grant_statement().where(Grant.public_id == public_id)).one_or_none()
    if row is None:
        raise api_error(404, "GRANT_NOT_FOUND", f"Grant '{public_id}' not found")
    return _grant_row(row)


def delete_grant(session: Session, public_id: str) -> None:
    def change() -> None:
        row = load_grant(session, public_id)
        session.execute(delete(Grant).where(Grant.public_id == public_id))
        security_events.record(
            session, "grant", public_id, "deleted", about=[row.principal_id],
            details=_grant_details(row),
        )  # fmt: skip

    _changing(session, change, guard=True)


def grant_page(
    session: Session,
    *,
    principal_id: str | None,
    workspace_key: str | None,
    role_key: str | None,
    consumer_api: str | None = None,
    page: PageRequest,
    page_size: int,
) -> Page[GrantRow]:
    """Grants as created; ``principalId`` matches a person, client or group, ``workspaceKey`` the
    grants made in that workspace, ``consumerApi`` the grants of that consumer API."""
    statement = _grant_statement()
    if principal_id is not None:
        statement = statement.where(
            or_(
                User.public_id == principal_id,
                OAuthClient.public_id == principal_id,
                UserGroup.public_id == principal_id,
            )
        )
    if workspace_key is not None:
        statement = statement.where(Grant.workspace_key == workspace_key)
    if role_key is not None:
        statement = statement.where(Role.key == role_key)
    if consumer_api is not None:
        statement = statement.where(Grant.consumer_api == consumer_api)
    page_of_rows = paginate_statement(
        session,
        statement,
        keys=_GRANT_KEYS,
        scope="grants",
        filters={
            "principalId": principal_id,
            "workspaceKey": workspace_key,
            "roleKey": role_key,
            "consumerApi": consumer_api,
        },
        page=page,
        page_size=page_size,
        message="Grant list cursor is invalid",
        rows=True,
    )
    return replace(page_of_rows, items=[_grant_row(row) for row in page_of_rows.items])


def access_page(
    session: Session, workspace_key: str, *, page: PageRequest, page_size: int
) -> Page[GrantRow]:
    """Every grant that applies in a workspace: made there, or at the instance (J40.7)."""
    load_workspace(session, workspace_key)
    statement = _grant_statement().where(
        or_(Grant.workspace_key == workspace_key, Grant.workspace_key.is_(None))
    )
    page_of_rows = paginate_statement(
        session,
        statement,
        keys=_GRANT_KEYS,
        scope=f"access:{workspace_key}",
        filters={},
        page=page,
        page_size=page_size,
        message="Access list cursor is invalid",
        rows=True,
    )
    return replace(page_of_rows, items=[_grant_row(row) for row in page_of_rows.items])


def own_grant_page(
    session: Session, kind: str, row_id: int, *, page: PageRequest, page_size: int
) -> Page[GrantRow]:
    """The caller's grants: direct, and for a person those of their groups (D284)."""
    return _held_grant_page(session, kind, row_id, "my-grants", page=page, page_size=page_size)


def user_grant_page(
    session: Session, public_id: str, *, page: PageRequest, page_size: int
) -> Page[GrantRow]:
    """A person's grants, direct and through their groups, as their page shows them (D299)."""
    user = _user(session, public_id)
    return _held_grant_page(
        session, "user", user.id, f"user-grants:{public_id}", page=page, page_size=page_size
    )


def _held_grant_page(
    session: Session, kind: str, row_id: int, scope: str, *, page: PageRequest, page_size: int
) -> Page[GrantRow]:
    statement = _grant_statement()
    if kind == "user":
        member_of = select(UserGroupMember.group_id).where(UserGroupMember.user_id == row_id)
        statement = statement.where(or_(Grant.user_id == row_id, Grant.group_id.in_(member_of)))
    else:
        statement = statement.where(Grant.client_id == row_id)
    page_of_rows = paginate_statement(
        session,
        statement,
        keys=_GRANT_KEYS,
        scope=scope,
        filters={},
        page=page,
        page_size=page_size,
        message="Grant list cursor is invalid",
        rows=True,
    )
    return replace(page_of_rows, items=[_grant_row(row) for row in page_of_rows.items])


@dataclass(frozen=True)
class HeldRole:
    """A role a person holds, directly or through a group: at the instance, or in workspaces given
    as (key, label); an instance role names no workspaces, since it covers them all (D298)."""

    key: str
    name: str
    instance: bool
    workspaces: tuple[tuple[str, str], ...]


def held_roles(session: Session, user_ids: list[int]) -> dict[int, list[HeldRole]]:
    """The roles each of ``user_ids`` holds, in one statement for a page of people (D298)."""
    if not user_ids:
        return {}
    direct = select(Grant.user_id.label("user_id"), Grant.role_id, Grant.workspace_key).where(
        Grant.user_id.in_(user_ids)
    )
    through = (
        select(UserGroupMember.user_id.label("user_id"), Grant.role_id, Grant.workspace_key)
        .join(Grant, Grant.group_id == UserGroupMember.group_id)
        .where(UserGroupMember.user_id.in_(user_ids))
    )
    held = union_all(direct, through).subquery()
    rows = session.execute(
        select(held.c.user_id, Role.key, Role.name, held.c.workspace_key, Workspace.label)
        .distinct()
        .join(Role, Role.id == held.c.role_id)
        .outerjoin(Workspace, Workspace.key == held.c.workspace_key)
        .order_by(held.c.user_id, Role.key, Workspace.label)
    ).all()
    found: dict[int, dict[str, tuple[str, bool, list[tuple[str, str]]]]] = {}
    for user_id, key, name, workspace_key, label in rows:
        _, instance, workspaces = found.setdefault(user_id, {}).get(key, (name, False, []))
        if workspace_key is None:
            instance = True
        else:
            workspaces.append((workspace_key, label))
        found[user_id][key] = (name, instance, workspaces)
    order = {key: index for index, key in enumerate(PREDEFINED_ROLES)}
    return {
        user_id: [
            HeldRole(key, name, instance, () if instance else tuple(workspaces))
            for key, (name, instance, workspaces) in sorted(
                roles.items(), key=lambda item: (order.get(item[0], len(order)), item[1][0])
            )
        ]
        for user_id, roles in found.items()
    }


def refuse_last_administrator(session: Session, before: int) -> None:
    if before > 0 and security_administrators(session) == 0:
        raise api_error(
            409,
            "LAST_SECURITY_ADMINISTRATOR",
            "This would leave no active person holding Security administration at the instance; "
            "give it to someone else first",
        )
