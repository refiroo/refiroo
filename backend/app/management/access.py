"""The route check: every operation declares its action and where its workspace comes from, and each
request is allowed or refused once, after authentication and before the handler (Product 0.12 Z1,
ADR-044, D277).

    @router.get("/workspaces/{workspace_key}/feed", ...)
    @requires("feed.read", at=WORKSPACE_PATH)
    def read_feed(...): ...

``requires`` marks the endpoint; ``AuthorizedRoute`` publishes the declaration in the operation's
OpenAPI entry (``x-action``, ``x-action-groups``, D256); ``authorized``, one of the management
dependencies, resolves the workspace with the engine's own lookups (an unknown change set, record
or job answers the handler's ``404``) and checks the caller's permissions. A refusal is
``403 FORBIDDEN`` naming the action, the groups that would allow it and the workspace (D249).
"""

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import Depends, Request
from fastapi.routing import APIRoute
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.datastructures import UploadFile as StarletteUploadFile

from ..engine.authorization.catalogue import ACTIONS, group_names
from ..engine.authorization.permissions import Permissions, permissions_of
from ..engine.authorization.requesters import job_group, requester
from ..engine.authorization.writes import Writer, refuses_live_data, set_writer
from ..engine.change_sets.submissions import allow_withdrawal
from ..engine.events.subscriptions import load_subscription
from ..engine.identity.authentication import Principal
from ..engine.jobs.store import load_job
from ..engine.model.workspace_models import default_workspace_key
from ..engine.tasks.store import refuse_draft_not_its_own
from ..engine.workspaces.catalogue import load_workspace
from ..errors import api_error
from ..models.database import AiTask, ChangeSet, ModelDraft, ObjectRelation, Publication, RdmObject
from .dependencies import CurrentPrincipal, DbSession, expect_model_release, started
from .query_parameters import refuse_after_authorization


@dataclass(frozen=True)
class Check:
    """What one request must hold: ``groups`` (any of them) in each of ``workspaces`` (None: at
    the instance); ``anywhere`` at any scope; nothing at all for a signed-in action."""

    groups: tuple[str, ...]
    workspaces: tuple[str | None, ...] = (None,)
    anywhere: bool = False
    # A write that names no change set, so it writes live data (a batch or an import, R-F2).
    live: bool = False


@dataclass(frozen=True)
class Context:
    request: Request
    session: Session
    body: dict[str, Any] | None

    def path(self, name: str) -> str:
        return str(self.request.path_params[name])

    def query(self, name: str) -> str | None:
        return self.request.query_params.get(name)

    def field(self, name: str) -> Any:
        return (self.body or {}).get(name)

    def default_workspace(self) -> str:
        return default_workspace_key(self.session)


# A resolver turns a request into the check it needs; ``groups`` are the action's.
Resolver = Callable[[Context, tuple[str, ...]], Check]


@dataclass(frozen=True)
class Where:
    """Where a route's workspace comes from, by name (for the OpenAPI entry) and resolver."""

    name: str
    resolve: Resolver
    # Whether the resolver reads the request body (JSON, or an import form's ``request`` field).
    reads_body: bool = False


def _change_set_workspace(context: Context, change_set_id: str) -> str:
    key = context.session.scalar(
        select(ChangeSet.workspace_key).where(ChangeSet.id == change_set_id)
    )
    if key is None:
        raise api_error(404, "CHANGE_SET_NOT_FOUND", f"Change set '{change_set_id}' not found")
    return key


def _publication_workspace(context: Context, publication_id: str) -> str:
    key = context.session.scalar(
        select(Publication.workspace_key).where(Publication.id == publication_id)
    )
    if key is None:
        raise api_error(404, "PUBLICATION_NOT_FOUND", "Publication not found")
    return key


def _record_workspace(context: Context, object_id: str) -> str:
    """A live record's workspace; the default workspace's for one that does not exist, so the
    write answers its own not-found, as the handler resolves it."""
    return (
        context.session.scalar(select(RdmObject.workspace_key).where(RdmObject.id == object_id))
        or context.default_workspace()
    )


def _relation_workspace(context: Context, relation_id: str) -> str:
    return (
        context.session.scalar(
            select(RdmObject.workspace_key)
            .join(ObjectRelation, ObjectRelation.from_object_id == RdmObject.id)
            .where(ObjectRelation.id == relation_id)
        )
        or context.default_workspace()
    )


def _live_or_change_set(
    context: Context, change_set_id: Any, live_workspace: Callable[[], str]
) -> Check:
    """The record writes (D244): Work in change sets in the change set's workspace, Edit live in
    the record's otherwise."""
    if change_set_id:
        return Check(("change-sets",), (_change_set_workspace(context, str(change_set_id)),))
    return Check(("edit-live",), (live_workspace(),))


def _context(context: Context, groups: tuple[str, ...]) -> Check:
    """A read in a change set, a publication, or one or more named workspaces (the default
    workspace without one)."""
    change_set_id = context.query("changeSetId")
    if change_set_id:
        return Check(groups, (_change_set_workspace(context, change_set_id),))
    publication_id = context.query("publicationId")
    if publication_id:
        return Check(groups, (_publication_workspace(context, publication_id),))
    keys = context.request.query_params.getlist("workspaceKey")
    return Check(groups, tuple(keys) if keys else (context.default_workspace(),))


def _body_context(context: Context, groups: tuple[str, ...]) -> Check:
    """A write naming ``changeSetId`` or ``workspaceKey`` in its body (the default workspace
    without either)."""
    change_set_id = context.field("changeSetId")
    if change_set_id:
        return Check(groups, (_change_set_workspace(context, str(change_set_id)),))
    return Check(
        groups,
        (context.field("workspaceKey") or context.default_workspace(),),
        live=context.request.method != "GET",
    )


def _import_form(context: Context, groups: tuple[str, ...]) -> Check:
    """An import names its context inside the form's ``request`` JSON field."""
    try:
        request = json.loads(context.field("request") or "{}")
    except ValueError:
        request = {}
    inner = Context(context.request, context.session, request if isinstance(request, dict) else {})
    return _body_context(inner, groups)


def _job(context: Context, groups: tuple[str, ...]) -> Check:
    """A job by its requester (D294), or by the group that starts its kind, in its workspace
    (D285); Work in change sets for a change set's migration."""
    job = load_job(context.session, context.path("job_id"))
    caller = context.request.state.principal
    if requester(job) == (caller.kind, caller.row_id):
        return Check(())
    group = job_group(job)
    if group == "model-authoring":
        return Check((group,))
    return Check((group,), (job.workspace_key,))


def _ai_task(context: Context, groups: tuple[str, ...]) -> Check:
    """An assistant task's workspace (0.16 AP6a); the default workspace's for a task that does not
    exist, so the handler answers its own not-found. Who may see the task is decided there."""
    key = context.session.scalar(
        select(AiTask.workspace_key).where(AiTask.public_id == context.path("task_id"))
    )
    return Check(groups, (key or context.default_workspace(),))


def _model_draft(context: Context, groups: tuple[str, ...]) -> Check:
    """The workspace a model draft remembers (0.16 WM-D3); the instance for a draft remembering none,
    or one that does not exist, so the handler answers its own not-found."""
    key = context.session.scalar(
        select(ModelDraft.workspace_key).where(ModelDraft.public_id == context.path("draft_id"))
    )
    return Check(groups, (key,)) if key else Check(groups)


def _move(context: Context, groups: tuple[str, ...]) -> Check:
    """Copy and move in the target; reading the source is checked by ``_move_source`` (D286)."""
    return Check(groups, (context.field("targetWorkspaceKey") or context.default_workspace(),))


SIGNED_IN = Where("signed-in", lambda context, groups: Check(()))
INSTANCE = Where("instance", lambda context, groups: Check(groups))
ANYWHERE = Where("any scope", lambda context, groups: Check(groups, anywhere=True))
WORKSPACE_PATH = Where(
    "the path's workspace", lambda context, groups: Check(groups, (context.path("workspace_key"),))
)
WORKSPACE_QUERY = Where(
    "the query's workspace",
    lambda context, groups: Check(
        groups, (context.query("workspaceKey") or context.default_workspace(),)
    ),
)
CONTEXT = Where("the query's change set, publication or workspace", _context)
CHANGE_SET_PATH = Where(
    "the change set's workspace",
    lambda context, groups: Check(
        groups, (_change_set_workspace(context, context.path("change_set_id")),)
    ),
)
PUBLICATION_PATH = Where(
    "the publication's workspace",
    lambda context, groups: Check(
        groups,
        (_publication_workspace(context, context.path("publication_id")),),
    ),
)
SUBSCRIPTION_PATH = Where(
    "the subscription's workspace",
    lambda context, groups: Check(
        groups, (load_subscription(context.session, context.path("subscription_id")).workspace_key,)
    ),
)
JOB_PATH = Where("the job's workspace and kind", _job)
BODY = Where("the body's change set or workspace", _body_context, reads_body=True)
AI_TASK_PATH = Where("the AI task's workspace", _ai_task)
MODEL_DRAFT_PATH = Where("the workspace the model draft remembers, else the instance", _model_draft)
QUERY_TRANSLATION = Where(
    "the body's change set or publication, or the path's workspace",
    lambda context, groups: Check(
        groups,
        (
            _change_set_workspace(context, str(context.field("changeSetId")))
            if context.field("changeSetId")
            else _publication_workspace(context, str(context.field("publicationId")))
            if context.field("publicationId")
            else context.path("workspace_key"),
        ),
    ),
    reads_body=True,
)
IMPORT_FORM = Where("the import request's change set or workspace", _import_form, reads_body=True)
MOVE = Where("the move's target and source workspaces", _move, reads_body=True)


def _write_change_set(context: Context) -> Any:
    """The change set a record or relationship write names, where its handler reads it: the query
    on a DELETE, the body on any other write (0.12 R-F1)."""
    if context.request.method == "DELETE":
        return context.query("changeSetId")
    return context.field("changeSetId")


MAPPING_PROPOSAL = Where(
    "the change set, or the path's workspace",
    lambda context, groups: Check(
        ("change-sets",),
        (
            _change_set_workspace(context, str(context.field("changeSetId")))
            if context.field("changeSetId")
            else context.path("workspace_key"),
        ),
    ),
    reads_body=True,
)
RECORD_WRITE = Where(
    "the change set, or the record's workspace",
    lambda context, groups: _live_or_change_set(
        context,
        _write_change_set(context),
        lambda: _record_workspace(context, context.path("object_id")),
    ),
    reads_body=True,
)
RECORD_WRITE_QUERY = Where(
    "the query's change set, or the record's workspace",
    lambda context, groups: _live_or_change_set(
        context,
        context.query("changeSetId"),
        lambda: _record_workspace(context, context.path("object_id")),
    ),
)
RELATION_WRITE = Where(
    "the change set, or the relationship's workspace",
    lambda context, groups: _live_or_change_set(
        context,
        _write_change_set(context),
        lambda: _relation_workspace(context, context.path("relation_id")),
    ),
    reads_body=True,
)
RECORD_CREATE = Where(
    "the change set, or the body's workspace",
    lambda context, groups: _live_or_change_set(
        context,
        context.field("changeSetId"),
        lambda: context.field("workspaceKey") or context.default_workspace(),
    ),
    reads_body=True,
)
RELATION_CREATE = Where(
    "the change set, or the from record's workspace",
    lambda context, groups: _live_or_change_set(
        context,
        context.field("changeSetId"),
        lambda: _record_workspace(context, str(context.field("fromObjectId") or "")),
    ),
    reads_body=True,
)


def _named_read(live_workspace: Callable[[Context], str]) -> Resolver:
    """A read naming a record or relationship: in the change set, publication or workspace the
    query names, or in the workspace holding it."""

    def resolve(context: Context, groups: tuple[str, ...]) -> Check:
        if any(context.query(name) for name in ("changeSetId", "publicationId", "workspaceKey")):
            return _context(context, groups)
        return Check(groups, (live_workspace(context),))

    return resolve


RECORD_READ = Where(
    "the query's context, or the record's workspace",
    _named_read(lambda context: _record_workspace(context, context.path("object_id"))),
)


def _live_or_change_set_read(context: Context, groups: tuple[str, ...]) -> Check:
    """A read of a record live or in a change set, with no publication to name: the change set's
    workspace, the workspace the query names, or the record's."""
    change_set_id = context.query("changeSetId")
    if change_set_id:
        return Check(groups, (_change_set_workspace(context, change_set_id),))
    keys = context.request.query_params.getlist("workspaceKey")
    if keys:
        return Check(groups, tuple(keys))
    return Check(groups, (_record_workspace(context, context.path("object_id")),))


RECORD_READ_NO_PUBLICATION = Where(
    "the change set or workspace the query names, or the record's workspace",
    _live_or_change_set_read,
)
RELATION_READ = Where(
    "the query's context, or the relationship's workspace",
    _named_read(lambda context: _relation_workspace(context, context.path("relation_id"))),
)
MAPPINGS_WRITE = Where(
    "the change set, or the path's workspace",
    lambda context, groups: _live_or_change_set(
        context, context.field("changeSetId"), lambda: context.path("workspace_key")
    ),
    reads_body=True,
)


@dataclass(frozen=True)
class Requirement:
    action: str
    at: Where


def requires[F: Callable[..., Any]](action: str, *, at: Where) -> Callable[[F], F]:
    """Declare the action an operation performs and where its workspace comes from."""
    if action not in ACTIONS:
        raise ValueError(f"unknown action {action!r}")

    def mark(endpoint: F) -> F:
        endpoint.requirement = Requirement(action, at)  # type: ignore[attr-defined]
        return endpoint

    return mark


class AuthorizedRoute(APIRoute):
    """A management route publishing its declaration in the OpenAPI document (D256)."""

    def __init__(self, path: str, endpoint: Callable[..., Any], **kwargs: Any) -> None:
        requirement: Requirement | None = getattr(endpoint, "requirement", None)
        if requirement is not None:
            extra = dict(kwargs.get("openapi_extra") or {})
            extra["x-action"] = requirement.action
            extra["x-action-groups"] = list(ACTIONS[requirement.action].groups)
            extra["x-action-scope"] = requirement.at.name
            kwargs["openapi_extra"] = extra
        super().__init__(path, endpoint, **kwargs)


def requirement_of(request: Request) -> Requirement | None:
    route = request.scope.get("route")
    return getattr(getattr(route, "endpoint", None), "requirement", None)


async def request_body(request: Request) -> dict[str, Any] | None:
    """The body a declaration reads: FastAPI has already read and kept it, so this parses nothing
    twice and reads no more from the client."""
    requirement = requirement_of(request)
    if requirement is None or not requirement.at.reads_body:
        return None
    content_type = request.headers.get("content-type", "")
    try:
        # An import naming a stored source file sends no file part: a URL-encoded form.
        if content_type.startswith(("multipart/form-data", "application/x-www-form-urlencoded")):
            form = await request.form()
            found = {key: value for key, value in form.items() if isinstance(value, str)}
            # The request sent as a file part: the workspace it names is still the one checked,
            # and the route then answers for the part's form.
            part = form.get("request")
            if isinstance(part, StarletteUploadFile):
                found["request"] = (await part.read()).decode(errors="replace")
                await part.seek(0)
            return found
        body = await request.json()
    except ValueError:
        return None
    return body if isinstance(body, dict) else None


# The record writes are refused by the group the request needed (D244).
_WRITES = {"edit-live": "Changing records live", "change-sets": "Changing records in a change set"}


def forbidden(action: str, groups: tuple[str, ...], workspace_key: str | None) -> Exception:
    where = f" in workspace '{workspace_key}'" if workspace_key else " at the instance"
    doing = ACTIONS[action].doing
    if action == "records.write" and len(groups) == 1:
        doing = _WRITES[groups[0]]
    elif action == "moves.create" and groups == ("browse",):
        doing = "Copying records out of a workspace"
    elif action == "moves.create" and groups == ("change-sets",):
        doing = "Moving records out of a workspace"
    return api_error(
        403,
        "FORBIDDEN",
        f"{doing}{where} needs {group_names(groups)}",
        {"action": action, "groups": list(groups), "workspaceKey": workspace_key},
    )


def caller_permissions(principal: Principal, session: Session) -> Permissions:
    return permissions_of(session, principal.kind, principal.row_id, principal.generation)


def authorized(
    request: Request,
    principal: CurrentPrincipal,
    session: DbSession,
    body: Annotated[dict[str, Any] | None, Depends(request_body)],
) -> Permissions:
    """Allow the request or refuse it with ``403 FORBIDDEN``; the caller's permissions stay on the
    request for the handlers that filter lists (D249, D288). Only then are the query parameters
    checked: no token is ``401``, no right ``403``, an unknown parameter ``422`` (0.12 E1, F1)."""
    permissions = _allowed(request, principal, session, body)
    refuse_after_authorization(request)
    return permissions


def _allowed(
    request: Request,
    principal: Principal,
    session: Session,
    body: dict[str, Any] | None,
) -> Permissions:
    permissions = caller_permissions(principal, session)
    request.state.permissions = permissions
    requirement = requirement_of(request)
    if requirement is None:
        # Fail closed: the contract test refuses an undeclared route before it ships.
        raise api_error(500, "ROUTE_NOT_DECLARED", "This operation declares no action")
    action = ACTIONS[requirement.action]
    check = requirement.at.resolve(Context(request, session, body), action.groups)
    # Whose writes the request makes, for the write unit's record-type check (Z2, D292).
    set_writer(
        session,
        Writer(permissions, check.groups, action.key, principal=(principal.kind, principal.row_id)),
    )
    # ``withdrawSubmission=true`` on any request lets a write to a submitted change set withdraw its
    # submission instead of being refused (0.12 A1, D426); the write unit decides it.
    allow_withdrawal(session, request.query_params.get("withdrawSubmission", "").lower() == "true")
    if check.live and refuses_live_data(session, principal.kind, principal.row_id, check.groups):
        raise api_error(
            403,
            "FORBIDDEN",
            "An assistant's session works in change sets and never writes live data",
            {"action": action.key, "groups": list(check.groups)},
        )
    draft_id = request.path_params.get("draft_id")
    if draft_id is not None and principal.kind == "client":
        refuse_draft_not_its_own(session, draft_id, principal.row_id)
    if not check.groups:
        return permissions
    if check.anywhere:
        if not any(permissions.allows_anywhere(group) for group in check.groups):
            raise forbidden(action.key, check.groups, None)
        return permissions
    for workspace_key in check.workspaces:
        if not any(permissions.allows(group, workspace_key) for group in check.groups):
            if workspace_key is not None:
                # A workspace that does not exist answers its own not-found.
                load_workspace(session, workspace_key)
            raise forbidden(action.key, check.groups, workspace_key)
    if requirement.at is MOVE:
        source = body.get("sourceWorkspaceKey") if body else None
        source = source or default_workspace_key(session)
        # A move deletes what it moved in a change set of the source (D134, D297).
        moving = bool(body) and body.get("mode") == "move"
        for group in ("browse", "change-sets") if moving else ("browse",):
            if not permissions.allows(group, source):
                load_workspace(session, source)
                raise forbidden(action.key, (group,), source)
    return permissions


CurrentPermissions = Annotated[Permissions, Depends(authorized)]


# Every route of the management API needs a token, is checked against the caller's permissions and
# takes the header. In maintenance mode it answers 503 before a session is opened or a token read.
MANAGEMENT_DEPENDENCIES = [
    Depends(started),
    Depends(authorized),
    Depends(expect_model_release),
]
