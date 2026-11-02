"""Who proposed a change-set row when a person did not (0.16 AP9, AP-D5, AP-D32).

A session's client is the writer of whatever it does through the API, by whichever route, so the
origin is stamped here, on every row of a change set it writes, and not by each route: a session may
use whatever its grants allow (AP-D29). A person's edit of a marked row keeps the mark and adds who
edited it (AP-D33). The origin holds public IDs, as the task and its client do not outlive what they
made; a read names them as they are now (``origin_with_names``).
"""

from typing import Any

from sqlalchemy import event as orm_event
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from ...models.database import AiTask, ChangeSetObject, ChangeSetRelation, OAuthClient, User
from ..authorization.writes import requester_of
from ..identity.principals import Ref, named, ref

_ORIGINS = "session_client_origins"
_AGENT = "agent_origin"
_NAMES = "origin_names"
# What a person changes of a row; its version alone moves with a rebase and is no edit.
_EDITS = {
    ChangeSetObject: ("name", "parent_object_id", "attributes", "is_deleted"),
    ChangeSetRelation: ("attributes", "is_deleted"),
}


def set_agent_origin(session: Session, *, application: str, proposed_by: str) -> None:
    """What the session writes from now on, an assistant writes through a tool (0.16 AG-D29). It is
    said by the call: a person through an assistant is the same principal as in their browser. The
    application's name is copied, as an unused registration is removed."""
    session.info[_AGENT] = {"kind": "agent", "application": application, "proposedBy": proposed_by}


def _task_of(session: Session, principal: Ref | None) -> dict[str, Any] | None:
    """The origin of what ``principal`` writes when an assistant writes it, or a task's session,
    cached for the session's life; None for everyone else."""
    agent = session.info.get(_AGENT)
    if agent is not None:
        return {"asked": principal, "origin": agent}
    if principal is None or principal[0] != "client":
        return None
    cache = session.info.setdefault(_ORIGINS, {})
    if principal[1] not in cache:
        row = session.execute(
            select(
                AiTask.public_id,
                AiTask.requested_by_user_id,
                AiTask.requested_by_client_id,
                AiTask.design,
            ).where(AiTask.client_id == principal[1])
        ).first()
        cache[principal[1]] = None
        if row is not None:
            design = row.design or {}
            asked = ref(row.requested_by_user_id, row.requested_by_client_id)
            cache[principal[1]] = {
                "asked": asked,
                "origin": {
                    "kind": "ai",
                    "provider": design.get("agentProvider") or "claude-code",
                    "model": design.get("agentModel"),
                    "promptVersion": design.get("agentPrompt") or "agent",
                    "proposedBy": (named(session, asked) or {}).get("id"),
                    "taskId": row.public_id,
                },
            }
    return cache[principal[1]]


def session_origin(session: Session) -> dict[str, Any] | None:
    """The origin of the session's writes when a task's session makes them."""
    found = _task_of(session, requester_of(session))
    return found["origin"] if found else None


def editor_of(session: Session) -> str | None:
    """Who edits when a person, not an assistant's session, writes: the ID a marked row records as
    ``editedBy`` (AP-D33)."""
    principal = requester_of(session)
    if principal is None or _task_of(session, principal) is not None:
        return None
    return (named(session, principal) or {}).get("id")


def asker_of(session: Session) -> Ref | None:
    """The caller behind the writes, and for a task's session who asked it (AP-D34): what a session
    submits is submitted by the person's own request, so they cannot also decide it."""
    principal = requester_of(session)
    found = _task_of(session, principal)
    return found["asked"] if found else principal


def step_marks(session: Session) -> dict[str, Any]:
    """What a model step a session writes says of who asked (AP-D35)."""
    origin = session_origin(session)
    return {"proposedBy": origin["proposedBy"], "taskId": origin["taskId"]} if origin else {}


def _edited(row: Any) -> bool:
    state = inspect(row)
    return any(state.attrs[name].history.has_changes() for name in _EDITS[type(row)])


@orm_event.listens_for(Session, "before_flush")
def _mark_rows(session: Session, _context: Any, _instances: Any) -> None:
    created = [item for item in session.new if type(item) in _EDITS]
    changed = [item for item in session.dirty if type(item) in _EDITS]
    if not created and not changed:
        return
    principal = requester_of(session)
    if principal is None:
        return
    found = _task_of(session, principal)
    if found:
        for row in created:
            row.origin = found["origin"]
        for row in changed:
            if _edited(row):
                row.origin = found["origin"]
        return
    marked = [row for row in changed if row.origin and _edited(row)]
    if marked:
        editor = (named(session, principal) or {}).get("id")
        for row in marked:
            row.origin = {**row.origin, "editedBy": editor}


def _name_of(session: Session, public_id: str) -> str | None:
    names = session.info.setdefault(_NAMES, {})
    if public_id not in names:
        names[public_id] = session.scalar(
            select(User.name).where(User.public_id == public_id)
        ) or session.scalar(select(OAuthClient.name).where(OAuthClient.public_id == public_id))
    return names[public_id]


def origin_with_names(session: Session, origin: dict[str, Any]) -> dict[str, Any]:
    """An origin as a read shows it: who asked and who edited, named as they are now, each looked
    up once per session however many rows name them."""
    named_too = dict(origin)
    for field in ("proposedBy", "editedBy"):
        if origin.get(field):
            named_too[f"{field}Name"] = _name_of(session, origin[field])
    return named_too
