"""What a caller may do: their grants, direct and through groups, read once per generation
(Product 0.12 Z1, ADR-044, D226, D278).

The authentication statement reads ``authorization_state.generation`` with the token's principal,
so each process knows on every request whether roles, groups, memberships or grants changed since
it last read the caller's permissions, in any process. The cache is keyed by the database too: a
test process talks to many databases cloned from one seed, whose principals share IDs.
"""

from collections import OrderedDict
from dataclasses import dataclass, replace
from threading import Lock
from typing import Literal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ...models.database import Grant, Role, RoleActionGroup, UserGroup, UserGroupMember
from .catalogue import AGENT_CEILING, GROUPS, PREDEFINED_ROLES

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
    # The consumer APIs the caller may read, as (workspace, consumer API) pairs (Z3, D306).
    consumer_apis: frozenset[tuple[str, str]] = frozenset()

    def reads_consumer_api(self, consumer_api: str, workspace_key: str) -> bool:
        """Whether a grant lets the caller read ``consumer_api`` in ``workspace_key`` (D307)."""
        return (workspace_key, consumer_api) in self.consumer_apis

    def consumer_apis_in(self, workspace_key: str) -> frozenset[str]:
        """The consumer APIs the caller may read in ``workspace_key``."""
        return frozenset(api for key, api in self.consumer_apis if key == workspace_key)

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

    def within_agent_ceiling(self) -> Permissions:
        """What an ``agent`` token may do of these: each grant cut down to the ceiling, and a grant
        with nothing left dropped; consumer API grants stand (0.16 AG-D15)."""
        holdings = (
            replace(holding, groups=kept)
            for holding in self.holdings
            if (kept := tuple(group for group in holding.groups if group in AGENT_CEILING))
        )
        return Permissions(tuple(holdings), self.consumer_apis)

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
    """The caller's grants in one statement: direct ones, and for a person those of their groups;
    a grant naming a consumer API instead of a role goes to ``consumer_apis``."""
    custom = (
        select(func.array_agg(RoleActionGroup.group_key))
        .where(RoleActionGroup.role_id == Role.id)
        .scalar_subquery()
    )
    statement = (
        select(Grant, Role, custom, UserGroup.public_id, UserGroup.name)
        .outerjoin(Role, Role.id == Grant.role_id)
        .outerjoin(UserGroup, UserGroup.id == Grant.group_id)
    )
    if kind == "user":
        member_of = select(UserGroupMember.group_id).where(UserGroupMember.user_id == principal_id)
        statement = statement.where(
            or_(Grant.user_id == principal_id, Grant.group_id.in_(member_of))
        )
    else:
        statement = statement.where(Grant.client_id == principal_id)
    holdings: list[Holding] = []
    consumer_apis: set[tuple[str, str]] = set()
    for grant, role, groups, group_id, group_name in session.execute(statement.order_by(Grant.id)):
        if role is None:
            consumer_apis.add((grant.workspace_key, grant.consumer_api))
            continue
        holdings.append(
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
        )
    return Permissions(tuple(holdings), frozenset(consumer_apis))


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
