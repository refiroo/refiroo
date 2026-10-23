"""What a caller may do: their grants, direct and through groups, read once per generation
(Product 0.12 Z1, ADR-044, D226, D278).

The authentication statement reads ``authorization_state.generation`` with the token's principal,
so each process knows on every request whether roles, groups, memberships or grants changed since
it last read the caller's permissions, in any process. The cache is keyed by the database too: a
test process talks to many databases cloned from one seed, whose principals share IDs.
"""

from collections import OrderedDict
from dataclasses import dataclass
from threading import Lock
from typing import Literal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ...models.database import Grant, Role, RoleActionGroup, UserGroup, UserGroupMember
from .catalogue import GROUPS, PREDEFINED_ROLES

PrincipalKind = Literal["user", "client"]


@dataclass(frozen=True)
class Holding:
    """One grant as it applies to the caller."""

    grant_id: str
    role_key: str
    role_name: str
    groups: tuple[str, ...]
    # None: the instance, which covers every workspace.
    workspace_key: str | None
    applications: tuple[str, ...]
    record_types: tuple[str, ...]
    # The group the grant reaches the caller through; None for a direct grant.
    through_group_id: str | None
    through_group_name: str | None


@dataclass(frozen=True)
class Narrowing:
    """What one group allows writing in a workspace (Z2, D289): a record whose application or type
    a grant names; every record when ``everything``. Names the model no longer has match nothing,
    so a stale grant never widens (D296)."""

    everything: bool
    applications: frozenset[str] = frozenset()
    record_types: frozenset[str] = frozenset()

    def permits(self, application_key: str, object_type_key: str) -> bool:
        return (
            self.everything
            or application_key in self.applications
            or object_type_key in self.record_types
        )


EVERYTHING = Narrowing(everything=True)


@dataclass(frozen=True)
class Permissions:
    holdings: tuple[Holding, ...]

    def allows(self, group: str, workspace_key: str | None) -> bool:
        """Whether the caller holds ``group`` in ``workspace_key`` (an instance grant covers every
        workspace), or at the instance when ``workspace_key`` is None."""
        return any(
            group in holding.groups
            and (holding.workspace_key is None or holding.workspace_key == workspace_key)
            for holding in self.holdings
        )

    def allows_anywhere(self, group: str) -> bool:
        """Whether the caller holds ``group`` at any scope (D248, D287)."""
        return any(group in holding.groups for holding in self.holdings)

    def workspaces(self, groups: frozenset[str] | None = None) -> frozenset[str] | None:
        """The workspaces where the caller holds any of ``groups`` (any group without it); None
        when an instance grant covers every workspace."""
        keys: set[str] = set()
        for holding in self.holdings:
            if groups is not None and not groups.intersection(holding.groups):
                continue
            if holding.workspace_key is None:
                return None
            keys.add(holding.workspace_key)
        return frozenset(keys)

    def narrowing(self, group: str, workspace_key: str) -> Narrowing | None:
        """What ``group`` allows writing in ``workspace_key``; None when the caller does not hold
        it there. The grants' narrowings add up, and one grant without any allows every record
        (D289); a group that is not narrowable is never narrowed (D290)."""
        granting = [holding for holding in self.groups_in(workspace_key) if group in holding.groups]
        if not granting:
            return None
        if not GROUPS[group].narrowable or any(
            not (holding.applications or holding.record_types) for holding in granting
        ):
            return EVERYTHING
        return Narrowing(
            everything=False,
            applications=frozenset(key for item in granting for key in item.applications),
            record_types=frozenset(key for item in granting for key in item.record_types),
        )

    def groups_in(self, workspace_key: str | None) -> list[Holding]:
        """The holdings that apply in ``workspace_key`` (instance ones included)."""
        return [
            holding
            for holding in self.holdings
            if holding.workspace_key is None or holding.workspace_key == workspace_key
        ]


_CACHE_SIZE = 2000
_cache: OrderedDict[tuple[str, PrincipalKind, int], tuple[int, Permissions]] = OrderedDict()
_lock = Lock()


def role_groups(role: Role, custom: list[str] | None) -> tuple[str, ...]:
    """A role's groups: the catalogue's for a predefined role, its rows for a custom one, in the
    catalogue's order."""
    held = set(PREDEFINED_ROLES.get(role.key, ()) if role.predefined else custom or ())
    return tuple(key for key in GROUPS if key in held)


def read_permissions(session: Session, kind: PrincipalKind, principal_id: int) -> Permissions:
    """The caller's grants in one statement: direct ones, and for a person those of their groups."""
    custom = (
        select(func.array_agg(RoleActionGroup.group_key))
        .where(RoleActionGroup.role_id == Role.id)
        .scalar_subquery()
    )
    statement = (
        select(Grant, Role, custom, UserGroup.public_id, UserGroup.name)
        .join(Role, Role.id == Grant.role_id)
        .outerjoin(UserGroup, UserGroup.id == Grant.group_id)
    )
    if kind == "user":
        member_of = select(UserGroupMember.group_id).where(UserGroupMember.user_id == principal_id)
        statement = statement.where(
            or_(Grant.user_id == principal_id, Grant.group_id.in_(member_of))
        )
    else:
        statement = statement.where(Grant.client_id == principal_id)
    holdings = tuple(
        Holding(
            grant_id=grant.public_id,
            role_key=role.key,
            role_name=role.name,
            groups=role_groups(role, groups),
            workspace_key=grant.workspace_key,
            applications=tuple(grant.applications),
            record_types=tuple(grant.record_types),
            through_group_id=group_id,
            through_group_name=group_name,
        )
        for grant, role, groups, group_id, group_name in session.execute(
            statement.order_by(Grant.id)
        )
    )
    return Permissions(holdings)


def permissions_of(
    session: Session, kind: PrincipalKind, principal_id: int, generation: int
) -> Permissions:
    """The caller's permissions at ``generation``, read again only when it changed."""
    key = (str(session.get_bind().url), kind, principal_id)
    with _lock:
        held = _cache.get(key)
        if held is not None and held[0] == generation:
            _cache.move_to_end(key)
            return held[1]
    permissions = read_permissions(session, kind, principal_id)
    with _lock:
        _cache[key] = (generation, permissions)
        _cache.move_to_end(key)
        while len(_cache) > _CACHE_SIZE:
            _cache.popitem(last=False)
    return permissions
