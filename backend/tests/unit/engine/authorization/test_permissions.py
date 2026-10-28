"""What a caller's grants allow (Z1, ADR-044): instance grants cover every workspace, a group is
held where any grant gives it, the catalogue's roles and actions name groups that exist, and the
cached permissions follow the generation PostgreSQL raises on every change (D278)."""

from itertools import product

import pytest
from sqlalchemy import select

from app.db import SessionLocal
from app.engine.authorization import administration
from app.engine.authorization.catalogue import (
    ACTIONS,
    FEATURE_GROUPS,
    FIRST_ADMINISTRATOR_ROLES,
    GROUPS,
    JOB_GROUPS,
    PREDEFINED_ROLES,
)
from app.engine.authorization.permissions import Holding, Permissions, permissions_of
from app.engine.identity.clients import create_client
from app.models.commands import ClientCreate, GroupCreate
from app.models.database import AuthorizationState


def _holding(groups: tuple[str, ...], workspace: str | None, **narrowing) -> Holding:
    return Holding(
        grant_id="g",
        role_key="r",
        role_name="R",
        groups=groups,
        workspace_key=workspace,
        applications=tuple(narrowing.get("applications", ())),
        record_types=tuple(narrowing.get("record_types", ())),
        through_group_id=None,
        through_group_name=None,
    )


@pytest.mark.parametrize(
    ("held_at", "asked_in", "allowed"),
    [
        (None, None, True),  # an instance grant, asked at the instance
        (None, "a", True),  # an instance grant covers every workspace
        ("a", "a", True),
        ("a", "b", False),
        ("a", None, False),  # a workspace grant never reaches the instance
    ],
)
def test_where_a_grant_applies(held_at, asked_in, allowed):
    permissions = Permissions((_holding(("browse",), held_at),))
    assert permissions.allows("browse", asked_in) is allowed
    assert permissions.allows("edit-live", asked_in) is False


def test_any_scope_and_the_workspaces_a_caller_holds_something_in():
    permissions = Permissions((_holding(("bulk",), "a"), _holding(("browse",), "b")))
    assert permissions.allows_anywhere("bulk") and not permissions.allows_anywhere("publish")
    assert permissions.workspaces() == {"a", "b"}
    assert permissions.workspaces(frozenset({"bulk"})) == {"a"}
    assert permissions.workspaces(frozenset({"publish"})) == frozenset()
    with_instance = Permissions((*permissions.holdings, _holding(("operations",), None)))
    assert with_instance.workspaces() is None
    assert with_instance.workspaces(frozenset({"bulk"})) == {"a"}


def test_holdings_in_a_workspace_include_the_instance_ones():
    holdings = (
        _holding(("browse",), "a"),
        _holding(("operations",), None),
        _holding(("feed",), "b"),
    )
    assert Permissions(holdings).groups_in("a") == [holdings[0], holdings[1]]


def test_no_grant_allows_nothing_anywhere():
    nothing = Permissions(())
    for group, workspace in product(GROUPS, (None, "a")):
        assert not nothing.allows(group, workspace)
    assert nothing.workspaces() == frozenset()


def test_the_catalogue_names_only_groups_it_has():
    for groups in PREDEFINED_ROLES.values():
        assert set(groups) <= set(GROUPS)
    for action in ACTIONS.values():
        assert set(action.groups) <= set(GROUPS), action.key
        assert action.doing or not action.groups, action.key
    assert set(JOB_GROUPS.values()) <= set(GROUPS)
    assert set(FIRST_ADMINISTRATOR_ROLES) <= set(PREDEFINED_ROLES)
    # Every group can be reached through some action or a feature's option, and every group is in
    # some predefined role.
    reached = {group for action in ACTIONS.values() for group in action.groups}
    assert reached | set(FEATURE_GROUPS) == set(GROUPS) and not reached & set(FEATURE_GROUPS)
    assert {group for groups in PREDEFINED_ROLES.values() for group in groups} == set(GROUPS)
    # The first administrator can do everything the instance needs set up.
    held = {group for role in FIRST_ADMINISTRATOR_ROLES for group in PREDEFINED_ROLES[role]}
    assert held == set(GROUPS)


def _generation(session) -> int:
    return session.scalar(select(AuthorizationState.generation))


def test_changes_raise_the_generation_and_the_cache_follows_it(seeded):
    with SessionLocal() as session:
        client, _ = create_client(session, ClientCreate(name="Cached"))
        start = _generation(session)
        assert permissions_of(session, "client", client.id, start).holdings == ()
        administration.grant_roles(session, "client", client.id, ("reader",))
        session.commit()
        moved = _generation(session)
        assert moved > start
        # Read at the old generation, the cached answer stands; at the new one it is read again.
        assert permissions_of(session, "client", client.id, start).holdings == ()
        [holding] = permissions_of(session, "client", client.id, moved).holdings
        assert (holding.role_key, holding.groups, holding.workspace_key) == (
            "reader",
            ("browse",),
            None,
        )
        administration.create_group(session, GroupCreate(name="Raises it too"))
        assert _generation(session) > moved
