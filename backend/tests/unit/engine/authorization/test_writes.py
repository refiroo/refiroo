"""What a writer may write (Z2, D289–D292): a narrowed grant allows the records whose application or
type it names, grants add up and one without narrowing allows every record, a group that is not
narrowable is never narrowed, names a model no longer has allow nothing, a relationship needs either
end, and a session naming no writer writes nothing."""

import pytest
from sqlalchemy.orm import Session

from app.engine.authorization.permissions import Holding, Permissions
from app.engine.authorization.writes import (
    SYSTEM,
    Writer,
    allowance,
    refuse_types,
    set_writer,
)
from app.errors import ApiError


def _holding(groups: tuple[str, ...], workspace: str | None = "a", **narrowing) -> Holding:
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


def _session(*holdings: Holding, groups: tuple[str, ...] = ("edit-live",)) -> Session:
    session = Session()
    set_writer(session, Writer(Permissions(holdings), groups, "records.write"))
    return session


@pytest.mark.parametrize(
    ("applications", "types", "record", "allowed"),
    [
        ((), (), ("app-1", "t1"), True),  # not narrowed
        (("app-1",), (), ("app-1", "t1"), True),
        (("app-1",), (), ("app-2", "t2"), False),
        ((), ("t2",), ("app-2", "t2"), True),
        (("app-1",), ("t2",), ("app-2", "t2"), True),  # an application or a type
        (("app-1",), ("t2",), ("app-2", "t3"), False),
        ((), ("gone",), ("app-1", "t1"), False),  # a stale name allows nothing (D296)
    ],
)
def test_what_one_narrowed_grant_allows(applications, types, record, allowed):
    session = _session(_holding(("edit-live",), applications=applications, record_types=types))
    assert allowance(session, "a").permits(*record) is allowed


def test_grants_add_up_and_one_unnarrowed_allows_everything():
    narrowed = _holding(("edit-live",), record_types=("t1",))
    other = _holding(("edit-live",), record_types=("t2",))
    both = allowance(_session(narrowed, other), "a")
    assert both.permits("x", "t1") and both.permits("x", "t2") and not both.permits("x", "t3")
    assert allowance(_session(narrowed, _holding(("edit-live",), None)), "a").everything


def test_a_group_that_is_not_narrowable_and_a_group_not_held():
    # A model administrator's grant narrowed in the workspace still migrates every record (D290).
    held = _holding(("model-release",), record_types=("t1",))
    assert allowance(_session(held, groups=("model-release",)), "a").everything
    with pytest.raises(ApiError) as refused:
        allowance(_session(_holding(("edit-live",), "b")), "a")
    assert (refused.value.status, refused.value.code) == (403, "FORBIDDEN")
    assert refused.value.details["workspaceKey"] == "a"


@pytest.mark.parametrize(
    ("ends", "refused"),
    [
        ((("x", "t1"), ("x", "t1")), None),
        ((("x", "t1"), ("x", "t2")), None),  # either end (D291)
        ((("x", "t2"), ("x", "t1")), None),
        ((("x", "t2"), ("x", "t3")), ["t2", "t3"]),
    ],
)
def test_a_relationship_needs_either_end(ends, refused):
    session = _session(_holding(("edit-live",), record_types=("t1",)))
    if refused is None:
        refuse_types(session, "a", relations=[ends])
        return
    with pytest.raises(ApiError) as error:
        refuse_types(session, "a", relations=[ends])
    assert error.value.details["recordTypes"] == refused


def test_a_session_naming_no_writer_writes_nothing():
    with pytest.raises(ApiError) as missing:
        allowance(Session(), "a")
    assert (missing.value.status, missing.value.code) == (500, "WRITER_UNKNOWN")
    reading = _session(_holding(("browse",)), groups=("browse",))
    with pytest.raises(ApiError) as browsing:
        allowance(reading, "a")
    assert browsing.value.code == "WRITER_UNKNOWN"
    engine = Session()
    set_writer(engine, SYSTEM)
    assert allowance(engine, "a").everything
