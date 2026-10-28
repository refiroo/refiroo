"""Whose write it is, and which records it may write (Product 0.12 Z2, ADR-044, D289–D293).

The route check puts the caller's **writer** on the request's session (``set_writer``): their
permissions, the groups the route was allowed under and its action; the worker puts a job's
requester's there for each step (D294). The write unit (``records/writes.py``) and the batch lookup
ask ``allowance`` what the writer may write in a workspace, once per workspace and writer, and
refuse what falls outside it with ``refuse_types``, as one check over the distinct types a write
touches. A write with no writer is refused with ``WRITER_UNKNOWN``: a path that forgets to say whose
write it is fails closed (D292). The engine's own writes name ``SYSTEM``.
"""

from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass

from sqlalchemy.orm import Session

from ...errors import ApiError, api_error
from .catalogue import ACTIONS, group_names
from .permissions import EVERYTHING, Narrowing, Permissions, PrincipalKind

# The groups whose routes and jobs write records; a writer holding none of them writes nothing.
WRITE_GROUPS = frozenset(
    {
        "edit-live",
        "change-sets",
        "publish",
        "approve",
        "bulk",
        "copy-move",
        "model-release",
        "model-authoring",
        "workspace-admin",
    }
)

# How a job's step is named in a refusal, by its kind (D294).
JOB_ACTIONS: dict[str, str] = {
    "batch": "bulk.write",
    "import": "bulk.write",
    "profile": "source-files.manage",
    "profileCheck": "import-profiles.manage",
    "export": "exports.create",
    "move": "moves.create",
    "mappingInference": "model-mappings.manage",
    "migration": "model.activate",
    "dryRun": "model.author",
    "inference": "model.author",
}

_WRITES = {"edit-live": "Changing records live", "change-sets": "Changing records in a change set"}


@dataclass(frozen=True)
class Writer:
    """Whose write this is: their permissions and the groups the request or job step is allowed
    under, with its action for refusals; ``permissions`` is None for the engine itself."""

    permissions: Permissions | None
    groups: tuple[str, ...]
    action: str
    # The caller as a job records its requester: kind and row ID.
    principal: tuple[PrincipalKind, int] | None = None


SYSTEM = Writer(None, (), "system")

_WRITER = "authorization_writer"
_ALLOWANCES = "authorization_allowances"


def set_writer(session: Session, writer: Writer | None) -> None:
    """Name whose writes this session makes from now on."""
    if writer is None:
        session.info.pop(_WRITER, None)
    else:
        session.info[_WRITER] = writer
    session.info.pop(_ALLOWANCES, None)


@contextmanager
def writing_as(session: Session, writer: Writer) -> Iterator[None]:
    """Make the session's writes meanwhile as ``writer``, then as before."""
    previous = session.info.get(_WRITER)
    set_writer(session, writer)
    try:
        yield
    finally:
        set_writer(session, previous)


def writer_of(session: Session) -> Writer | None:
    return session.info.get(_WRITER)


def requester_of(session: Session) -> tuple[PrincipalKind, int] | None:
    """The caller behind the session's writes, which a job or an upload records (D294, D295)."""
    writer = session.info.get(_WRITER)
    return writer.principal if writer is not None else None


def doing(action: str, groups: tuple[str, ...]) -> str:
    """How a refusal names what was being done."""
    if (
        action in ("records.write", "change-sets.write")
        and len(groups) == 1
        and groups[0] in _WRITES
    ):
        return _WRITES[groups[0]]
    return ACTIONS[action].doing if action in ACTIONS else "Writing records"


def _writer(session: Session) -> Writer:
    writer = session.info.get(_WRITER)
    if writer is None:
        raise api_error(
            500,
            "WRITER_UNKNOWN",
            "This write does not name whose write it is; nothing was saved",
        )
    return writer


def allowance(session: Session, workspace_key: str) -> Narrowing:
    """What the session's writer may write in ``workspace_key`` (D289); ``403 FORBIDDEN`` when it
    holds none of its groups there."""
    writer = _writer(session)
    if writer.permissions is None:
        return EVERYTHING
    held = session.info.setdefault(_ALLOWANCES, {})
    if workspace_key in held:
        return held[workspace_key]
    groups = tuple(group for group in writer.groups if group in WRITE_GROUPS)
    if not groups:
        raise api_error(
            500,
            "WRITER_UNKNOWN",
            f"{doing(writer.action, writer.groups)} does not write records; nothing was saved",
        )
    narrowings = [
        narrowing
        for narrowing in (writer.permissions.narrowing(group, workspace_key) for group in groups)
        if narrowing is not None
    ]
    if not narrowings:
        where = f" in workspace '{workspace_key}'"
        raise api_error(
            403,
            "FORBIDDEN",
            f"{doing(writer.action, groups)}{where} needs {group_names(groups)}",
            {"action": writer.action, "groups": list(groups), "workspaceKey": workspace_key},
        )
    if any(narrowing.everything for narrowing in narrowings):
        allowed = EVERYTHING
    else:
        allowed = Narrowing(
            everything=False,
            applications=frozenset().union(*(item.applications for item in narrowings)),
            record_types=frozenset().union(*(item.record_types for item in narrowings)),
        )
    held[workspace_key] = allowed
    return allowed


def _require_route(session: Session, workspace_key: str, only: str, needs: str) -> None:
    """Refuse the write of a writer allowed only under ``only`` where ``needs`` is the group it
    takes: a route authorized for one kind of write must not perform the other (0.12 R-F1)."""
    writer = session.info.get(_WRITER)
    if writer is None or writer.permissions is None:
        return
    held = {group for group in writer.groups if group in WRITE_GROUPS}
    if held != {only}:
        return
    raise api_error(
        403,
        "FORBIDDEN",
        f"{doing(writer.action, (needs,))} in workspace '{workspace_key}' needs "
        f"{group_names((needs,))}",
        {"action": writer.action, "groups": [needs], "workspaceKey": workspace_key},
    )


def require_live(session: Session, workspace_key: str) -> None:
    """A live write by a writer authorized only for change-set work is refused ``403 FORBIDDEN``."""
    _require_route(session, workspace_key, "change-sets", "edit-live")


def require_change_set(session: Session, workspace_key: str) -> None:
    """A change-set write by a writer authorized only for live edits is refused ``403 FORBIDDEN``."""
    _require_route(session, workspace_key, "edit-live", "change-sets")


def refusal(session: Session, workspace_key: str, record_types: Iterable[str]) -> ApiError:
    """``403 FORBIDDEN`` for writing records of ``record_types``, which the writer's grants in the
    workspace do not name (D293)."""
    writer = _writer(session)
    groups = tuple(group for group in writer.groups if group in WRITE_GROUPS)
    refused = sorted(set(record_types))
    named = ", ".join(f"'{key}'" for key in refused)
    return api_error(
        403,
        "FORBIDDEN",
        f"{doing(writer.action, groups)} in workspace '{workspace_key}' is not granted for "
        f"record type{'s' if len(refused) > 1 else ''} {named}",
        {
            "action": writer.action,
            "groups": list(groups),
            "workspaceKey": workspace_key,
            "recordTypes": refused,
        },
    )


def refuse_types(
    session: Session,
    workspace_key: str,
    records: Iterable[tuple[str, str]] = (),
    relations: Iterable[tuple[tuple[str, str], tuple[str, str]]] = (),
) -> None:
    """Refuse a write of ``records`` (application and type) and ``relations`` (their two ends'),
    each pair checked once: a record needs its own type allowed, a relationship either end's
    (D291)."""
    allowed = allowance(session, workspace_key)
    if allowed.everything:
        return
    refused = {type_key for app, type_key in set(records) if not allowed.permits(app, type_key)}
    for start, end in set(relations):
        if not (allowed.permits(*start) or allowed.permits(*end)):
            refused.update((start[1], end[1]))
    if refused:
        raise refusal(session, workspace_key, refused)
