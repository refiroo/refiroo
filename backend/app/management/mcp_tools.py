"""The tools and resources an assistant can read at ``/mcp`` (Product 0.16 AG-D18, AG-D22, AG-D24).

A tool names the action group it needs; one the caller lacks is not listed, and is refused if called
(hide, never disable). A tool that names a workspace refuses one the caller cannot read in the words of
one that does not exist. Every tool calls what its route calls, so authorization and paging are the
API's, and answers in its route's shape. Each consumer API definition adds a tool of its own
(``engine/agent_access/lookup``). AG3 adds to this registry.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..common.pagination import PageRequest
from ..engine.agent_access import lookup
from ..engine.authorization.catalogue import GROUPS
from ..engine.authorization.permissions import Permissions
from ..engine.identity.authentication import Principal
from ..engine.model.consumer_definitions import consumer_apis
from ..engine.model.registry import ModelSnapshot, resolve_model_snapshot
from ..engine.reads import changes
from ..engine.records.rules import get_application, get_object_type
from ..errors import api_error
from ..models.database import Workspace
from ..models.queries import ModelQuery
from .projections.changes import change_page
from .projections.mapping import coverage, open_mapping_read
from .projections.model_metadata import build_application_responses, build_object_type_responses
from .projections.model_query import query_objects
from .routers.objects import live_object, live_object_history
from .routers.relations import live_relation_page
from .routers.workspaces import workspace_page

BROWSE = "browse"
_PAGE_SIZE = 50


@dataclass(frozen=True)
class Call:
    """Who is calling and what they may do on this audience (the ceiling already applied)."""

    session: Session
    principal: Principal
    permissions: Permissions
    application: str | None


def _always(_arguments: dict[str, Any]) -> bool:
    return True


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    input_schema: dict[str, Any]
    run: Callable[[Call, dict[str, Any]], dict[str, Any]]
    # The action group the caller must hold somewhere; None for any caller.
    group: str | None = None
    # The size of a page when none is asked for; None for a tool whose answer is not a page.
    page_size: int | None = None
    pages: Callable[[dict[str, Any]], bool] = _always
    # Answers whole, past the size cap: what a caller reads when a tool's answer is too long.
    whole: bool = False

    def offered_to(self, permissions: Permissions) -> bool:
        return self.group is None or permissions.allows_anywhere(self.group)


def _dumped(answer: BaseModel) -> dict[str, Any]:
    return answer.model_dump(mode="json", by_alias=True)


def _readable(call: Call, workspace: str) -> str:
    if not call.permissions.allows(BROWSE, workspace):
        raise api_error(404, "WORKSPACE_NOT_FOUND", f"Workspace '{workspace}' not found")
    return workspace


def _snapshot(call: Call, arguments: dict[str, Any]) -> ModelSnapshot:
    return resolve_model_snapshot(call.session, _readable(call, arguments["workspace"]))


def _describe_access(call: Call, _arguments: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": call.principal.kind,
        "id": call.principal.id,
        "name": call.principal.name,
        "through": call.application,
        "grants": [
            {
                "role": holding.role_name,
                "workspace": holding.workspace_key,
                "actionGroups": [GROUPS[group].name for group in holding.groups],
            }
            for holding in call.permissions.holdings
        ],
        "consumerApis": [
            {"workspace": workspace, "consumerApi": consumer_api}
            for workspace, consumer_api in sorted(call.permissions.consumer_apis)
        ],
    }


def _list_workspaces(call: Call, arguments: dict[str, Any]) -> dict[str, Any]:
    page = workspace_page(
        call.session,
        call.permissions,
        PageRequest(cursor=arguments.get("cursor")),
        search=arguments.get("search"),
        workspace_status="active",
        holding=BROWSE,
        page_size=arguments["pageSize"],
    )
    return _dumped(page)


def _named(items: Any) -> list[dict[str, Any]]:
    return [{"key": item.key, "name": item.name} for item in items]


def _describe_model(call: Call, arguments: dict[str, Any]) -> dict[str, Any]:
    model = _snapshot(call, arguments).model
    return {
        "applications": [
            {
                "key": application.key,
                "name": application.name,
                "description": application.description,
                "objectTypes": list(application.objectTypeKeys),
                "views": [
                    {"key": view.key, "name": view.name, "type": view.type}
                    for view in application.views
                ],
            }
            for application in model.applications
        ],
        "objectTypes": _named(model.objectTypes),
        "relationTypes": _named(model.relationTypes),
        "consumerApis": _named(consumer_apis(model)),
    }


def _object_type(snapshot: ModelSnapshot, session: Session, key: str) -> dict[str, Any]:
    return _dumped(
        build_object_type_responses(session, snapshot, [get_object_type(snapshot.model, key)])[0]
    )


def _describe_type(call: Call, arguments: dict[str, Any]) -> dict[str, Any]:
    snapshot = _snapshot(call, arguments)
    key = arguments["objectType"]
    return {
        **_object_type(snapshot, call.session, key),
        "relationships": [
            row.model_dump(mode="json")
            for row in snapshot.model.objectTypeRelations
            if key in (row.fromObjectTypeKey, row.toObjectTypeKey)
        ],
        "views": [
            {"application": application.key, "key": view.key, "name": view.name, "type": view.type}
            for application in snapshot.model.applications
            if key in application.objectTypeKeys
            for view in application.views
        ],
    }


def _find_records(call: Call, arguments: dict[str, Any]) -> dict[str, Any]:
    snapshot = _snapshot(call, arguments)
    body = {name: value for name, value in arguments.items() if name != "workspace"}
    try:
        query = ModelQuery.model_validate(body)
    except ValidationError as invalid:
        raise api_error(422, "INVALID_QUERY", str(invalid.errors()[0]["msg"])) from None
    return _dumped(
        query_objects(call.session, snapshot.model, query, workspace_key=arguments["workspace"])
    )


def _read_record(call: Call, arguments: dict[str, Any]) -> dict[str, Any]:
    snapshot = _snapshot(call, arguments)
    workspace = arguments["workspace"]
    record = live_object(
        call.session, snapshot.model, arguments["objectType"], arguments["id"], workspace
    )
    relations = live_relation_page(
        call.session,
        snapshot.model,
        arguments["id"],
        workspace,
        PageRequest(cursor=arguments.get("cursor")),
        arguments["pageSize"],
    )
    return {"record": _dumped(record), "relations": _dumped(relations)}


def _mapping_coverage(call: Call, arguments: dict[str, Any]) -> dict[str, Any]:
    read = open_mapping_read(
        call.session,
        _readable(call, arguments["workspace"]),
        arguments["application"],
        arguments["view"],
        None,
    )
    return _dumped(
        coverage(
            read,
            arguments.get("search"),
            PageRequest(cursor=arguments.get("cursor")),
            arguments["pageSize"],
            arguments.get("parentObjectId"),
            arguments.get("state"),
        )
    )


def _record_history(call: Call, arguments: dict[str, Any]) -> dict[str, Any]:
    return _dumped(
        live_object_history(
            call.session,
            arguments["objectType"],
            arguments["id"],
            _readable(call, arguments["workspace"]),
            PageRequest(cursor=arguments.get("cursor")),
            arguments["pageSize"],
            arguments.get("kind"),
            arguments.get("actorId"),
        )
    )


def _moment(arguments: dict[str, Any], name: str) -> datetime | None:
    value = arguments.get(name)
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        raise api_error(422, "INVALID_DATE", f"{name} must be an ISO 8601 date and time") from None


def _list_changes(call: Call, arguments: dict[str, Any]) -> dict[str, Any]:
    return _dumped(
        change_page(
            call.session,
            changes.change_page(
                call.session,
                call.permissions,
                actor_id=arguments.get("actorId"),
                workspace_key=_readable(call, arguments["workspace"]),
                kinds=arguments.get("kind", []),
                since=_moment(arguments, "since"),
                until=_moment(arguments, "until"),
                page=PageRequest(cursor=arguments.get("cursor")),
                page_size=arguments["pageSize"],
            ),
        )
    )


def _schema(required: tuple[str, ...], **properties: Any) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": list(required),
        "additionalProperties": False,
    }


_TEXT = {"type": "string"}


def _paged(maximum: int = 500) -> dict[str, Any]:
    return {"cursor": _TEXT, "pageSize": {"type": "integer", "minimum": 1, "maximum": maximum}}


def _query_schema() -> dict[str, Any]:
    """The query's own schema, without its context and what selects a page by position: a tool reads
    live data and pages by cursor."""
    schema = ModelQuery.model_json_schema()
    for name in ("context", "position", "from", "includeTotal"):
        schema["properties"].pop(name)
    defs = schema.get("$defs", {})
    defs.pop("QueryContext", None)
    return {
        **schema,
        "properties": {"workspace": _TEXT, **schema["properties"]},
        "required": ["workspace", *schema.get("required", [])],
        "additionalProperties": False,
    }


READ_ON = "Pass nextCursor back as cursor to read on."

TOOLS: tuple[Tool, ...] = (
    Tool(
        "describe_access",
        "Who this connection acts as and what it may do: its grants and consumer APIs.",
        {"type": "object", "properties": {}, "additionalProperties": False},
        _describe_access,
    ),
    Tool(
        "list_workspaces",
        f"The active workspaces this connection may read, a page at a time. {READ_ON}",
        _schema((), search=_TEXT, **_paged()),
        _list_workspaces,
        group=BROWSE,
        page_size=100,
    ),
    Tool(
        "describe_model",
        "A workspace's model by key and name: its applications with their views, its record types, "
        "relation types and consumer APIs.",
        _schema(("workspace",), workspace=_TEXT),
        _describe_model,
        group=BROWSE,
    ),
    Tool(
        "describe_type",
        "One record type: its attributes with their types and filters, its parents, its "
        "relationships and the views that show it.",
        _schema(("workspace", "objectType"), workspace=_TEXT, objectType=_TEXT),
        _describe_type,
        group=BROWSE,
    ),
    Tool(
        "find_records",
        "Records of one type matching criteria over their fields, ancestors and one relation hop. "
        f"Live data. {READ_ON}",
        _query_schema(),
        _find_records,
        group=BROWSE,
        page_size=_PAGE_SIZE,
    ),
    Tool(
        "read_record",
        f"One record with its values and path, and a page of its relationships. {READ_ON}",
        _schema(
            ("workspace", "objectType", "id"),
            workspace=_TEXT,
            objectType=_TEXT,
            id=_TEXT,
            **_paged(),
        ),
        _read_record,
        group=BROWSE,
        page_size=_PAGE_SIZE,
    ),
    Tool(
        "mapping_coverage",
        "The source records of a mapping view with what they map to; state=unmapped lists those "
        f"without a target. describe_model names the views. {READ_ON}",
        _schema(
            ("workspace", "application", "view"),
            workspace=_TEXT,
            application=_TEXT,
            view=_TEXT,
            state={"type": "string", "enum": ["mapped", "unmapped", "ambiguous"]},
            search=_TEXT,
            parentObjectId=_TEXT,
            **_paged(100),
        ),
        _mapping_coverage,
        group=BROWSE,
        page_size=_PAGE_SIZE,
    ),
    Tool(
        "record_history",
        f"A record's history, newest first. {READ_ON}",
        _schema(
            ("workspace", "objectType", "id"),
            workspace=_TEXT,
            objectType=_TEXT,
            id=_TEXT,
            kind={"type": "string", "enum": ["values", "relationships", "structure"]},
            actorId=_TEXT,
            **_paged(),
        ),
        _record_history,
        group=BROWSE,
        page_size=_PAGE_SIZE,
    ),
    Tool(
        "list_changes",
        f"A workspace's changes, newest first; since is included, until is not. {READ_ON}",
        _schema(
            ("workspace",),
            workspace=_TEXT,
            kind={
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["record", "relationship", "change-set", "publication", "model"],
                },
            },
            actorId=_TEXT,
            since={**_TEXT, "description": "ISO 8601"},
            until={**_TEXT, "description": "ISO 8601"},
            **_paged(),
        ),
        _list_changes,
        group=BROWSE,
        page_size=_PAGE_SIZE,
    ),
)


def _lookup_tool(item: lookup.Lookup) -> Tool:
    return Tool(
        item.name,
        item.description(),
        item.input_schema(),
        lambda call, arguments: lookup.read(call.session, item, arguments),
        page_size=_PAGE_SIZE,
        pages=lookup.pages,
    )


def tools_for(session: Session, permissions: Permissions) -> list[Tool]:
    """What this caller is offered: the fixed tools and a tool per definition it may read."""
    return [
        *(tool for tool in TOOLS if tool.offered_to(permissions)),
        *(_lookup_tool(item) for item in lookup.lookups(session, permissions)),
    ]


def find_tool(session: Session, permissions: Permissions, name: str) -> Tool | None:
    """The tool by name, reading the workspaces' models only for a lookup."""
    if name.startswith(lookup.PREFIX):
        return next((tool for tool in tools_for(session, permissions) if tool.name == name), None)
    return next(
        (tool for tool in TOOLS if tool.name == name and tool.offered_to(permissions)), None
    )


_SCHEME = "refiroo://workspaces"
_RESOURCE = re.compile(
    rf"^{_SCHEME}/(?P<workspace>[^/]+)/"
    r"(?:(?P<model>model)|applications/(?P<application>[^/]+)|object-types/(?P<type>[^/]+)"
    r"|views/(?P<owner>[^/]+)/(?P<view>[^/]+))$"
)


RESOURCE_TEMPLATES = (
    (f"{_SCHEME}/{{workspace}}/applications/{{key}}", "An application of a workspace's model"),
    (f"{_SCHEME}/{{workspace}}/object-types/{{key}}", "A record type of a workspace's model"),
    (f"{_SCHEME}/{{workspace}}/views/{{application}}/{{key}}", "A view of an application"),
)


def resources_for(session: Session, permissions: Permissions) -> list[tuple[str, str]]:
    """Each readable workspace's model, as its address and its name. Its parts are reached through
    :data:`RESOURCE_TEMPLATES`: listing them made 208 KB on 15 workspaces, more than an assistant
    reads (the real try, AG-D24)."""
    keys = session.scalars(
        select(Workspace.key).where(Workspace.status == "active").order_by(Workspace.key)
    )
    return [
        (f"{_SCHEME}/{key}/model", f"The model of {key}")
        for key in keys.all()
        if permissions.allows(BROWSE, key)
    ]


def _read_resource(call: Call, arguments: dict[str, Any]) -> dict[str, Any]:
    address = _RESOURCE.match(arguments["uri"])
    if address is None:
        raise api_error(404, "RESOURCE_NOT_FOUND", f"No resource at {arguments['uri']}")
    snapshot = _snapshot(call, {"workspace": address["workspace"]})
    if address["model"]:
        return snapshot.model.model_dump(mode="json")
    if address["type"]:
        return _object_type(snapshot, call.session, address["type"])
    if address["application"]:
        application = get_application(snapshot.model, address["application"])
        return _dumped(build_application_responses(call.session, snapshot, [application])[0])
    application = get_application(snapshot.model, address["owner"])
    view = next((item for item in application.views if item.key == address["view"]), None)
    if view is None:
        raise api_error(404, "RESOURCE_NOT_FOUND", f"No resource at {arguments['uri']}")
    return view.model_dump(mode="json")


# How a resource read runs: through the limit and the record of a tool, never listed as one.
READ_RESOURCE = Tool(
    "read_resource",
    "",
    _schema(("uri",), uri=_TEXT),
    _read_resource,
    group=BROWSE,
    whole=True,
)
