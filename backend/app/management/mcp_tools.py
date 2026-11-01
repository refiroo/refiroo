"""The tools and resources an assistant can read at ``/mcp`` (Product 0.16 AG-D18, AG-D22, AG-D24).

A tool names the action group it needs; one the caller lacks is not listed, and is refused if called
(hide, never disable). A tool that names a workspace refuses one the caller cannot read in the words of
one that does not exist. Every tool calls what its route calls, so authorization and paging are the
API's, and answers in its route's shape. Each consumer API definition adds a tool of its own
(``engine/agent_access/lookup``). Eleven change-set tools write into a change set the caller created
and nothing else (AG-D26, AG-D27): a change reaches live data only when a person approves it.
"""

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..common.pagination import PageRequest
from ..config import get_settings
from ..engine.agent_access import lookup
from ..engine.authorization.catalogue import GROUPS
from ..engine.authorization.permissions import Permissions
from ..engine.change_sets import approvals
from ..engine.change_sets.records import patch_change_set_attribute
from ..engine.identity.authentication import Principal
from ..engine.model.consumer_definitions import consumer_apis
from ..engine.model.registry import ModelSnapshot, resolve_model_snapshot, resolve_request_model
from ..engine.reads import changes
from ..engine.reads.snapshot_reads import change_set_context
from ..engine.records.rules import get_application, get_object_type
from ..errors import api_error
from ..models.commands import ObjectCreate, ObjectUpdate, RelationCreate, RelationUpdate
from ..models.database import ChangeSet, Workspace
from ..models.queries import ModelQuery
from .projections.changes import change_page
from .projections.home import created_by
from .projections.mapping import coverage, open_mapping_read
from .projections.model_metadata import build_application_responses, build_object_type_responses
from .projections.model_query import query_objects
from .routers.change_sets import (
    change_set_response,
    new_change_set,
    object_change_page,
    own_change_set_page,
    relation_change_page,
    validated_change_set,
)
from .routers.objects import (
    change_set_object_created,
    change_set_object_updated,
    live_object,
    live_object_history,
    refuse_repeated_attributes,
    snapshot_object,
)
from .routers.relations import (
    change_set_relation_created,
    change_set_relation_updated,
    live_relation_page,
    snapshot_relation_page,
)
from .routers.workspaces import workspace_page
from .schemas.change_sets import ChangeSetCreate, ChangeSetValidation

BROWSE = "browse"
CHANGE_SETS = "change-sets"
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
    # The action of a tool that writes (AG-D28): it runs once, as this action, and commits itself.
    writes: str | None = None

    def offered_to(self, permissions: Permissions) -> bool:
        return self.group is None or permissions.allows_anywhere(self.group)


def _dumped(answer: BaseModel) -> dict[str, Any]:
    return answer.model_dump(mode="json", by_alias=True)


def answer_size(answer: dict[str, Any]) -> int:
    return len(json.dumps(answer, default=str).encode())


def _readable(call: Call, workspace: str, holding: str | None = None) -> str:
    """The workspace, when the caller may browse it and, with ``holding``, holds that group in it."""
    if not call.permissions.allows(BROWSE, workspace) or not (
        holding is None or call.permissions.allows(holding, workspace)
    ):
        raise api_error(404, "WORKSPACE_NOT_FOUND", f"Workspace '{workspace}' not found")
    return workspace


def _own_change_set(call: Call, change_set_id: str) -> ChangeSet:
    """The change set, when this caller created it and holds Work in change sets in its workspace;
    any other is not found in the route's words (AG-D27). Every tool naming one comes through here."""
    item = call.session.scalar(
        select(ChangeSet).where(ChangeSet.id == change_set_id, created_by(call.principal))
    )
    if item is None or not call.permissions.allows(CHANGE_SETS, item.workspace_key):
        raise api_error(404, "CHANGE_SET_NOT_FOUND", f"Change set '{change_set_id}' not found")
    return item


def _snapshot(call: Call, arguments: dict[str, Any]) -> ModelSnapshot:
    """The workspace's model, or with ``changeSetId`` the model that change set pins."""
    workspace = _readable(call, arguments["workspace"])
    change_set_id = arguments.get("changeSetId")
    if change_set_id is None:
        return resolve_model_snapshot(call.session, workspace)
    _own_change_set(call, change_set_id)
    return resolve_request_model(call.session, workspace, change_set_id, None)


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
    body = {
        name: value for name, value in arguments.items() if name not in ("workspace", "changeSetId")
    }
    if "changeSetId" in arguments:
        body["context"] = {"changeSetId": arguments["changeSetId"]}
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
    paging = PageRequest(cursor=arguments.get("cursor"))
    if "changeSetId" in arguments:
        get_object_type(snapshot.model, arguments["objectType"])
        context = change_set_context(call.session, arguments["changeSetId"])
        record = snapshot_object(
            call.session, snapshot.model, context, arguments["objectType"], arguments["id"]
        )
        relations = snapshot_relation_page(
            call.session, snapshot.model, context, arguments["id"], paging, arguments["pageSize"]
        )
    else:
        record = live_object(
            call.session, snapshot.model, arguments["objectType"], arguments["id"], workspace
        )
        relations = live_relation_page(
            call.session, snapshot.model, arguments["id"], workspace, paging, arguments["pageSize"]
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


def _payload[Payload: BaseModel](model: type[Payload], body: dict[str, Any]) -> Payload:
    """The route's own body for a write, so its checks are the route's."""
    try:
        return model.model_validate(body)
    except ValidationError as invalid:
        first = invalid.errors()[0]
        where = ".".join(str(part) for part in first["loc"])
        message = f"{where}: {first['msg']}" if where else first["msg"]
        raise api_error(422, "REQUEST_VALIDATION_ERROR", message) from None


def _given(arguments: dict[str, Any], *names: str) -> dict[str, Any]:
    return {name: arguments[name] for name in names if name in arguments}


def _attribute_list(attributes: Any) -> list[dict[str, Any]]:
    """Values given by key or as a list, as the route's list of attribute values."""
    if isinstance(attributes, dict):
        return [{"attributeTypeKey": key, "value": value} for key, value in attributes.items()]
    return list(attributes or ())


def _my_change_sets(call: Call, arguments: dict[str, Any]) -> dict[str, Any]:
    workspace = arguments.get("workspace")
    if workspace is not None:
        _readable(call, workspace, CHANGE_SETS)
    return _dumped(
        own_change_set_page(
            call.session,
            call.principal,
            call.permissions,
            PageRequest(cursor=arguments.get("cursor")),
            arguments["pageSize"],
            holding=CHANGE_SETS,
            workspace_key=workspace,
        )
    )


def _read_change_set(call: Call, arguments: dict[str, Any]) -> dict[str, Any]:
    answer = change_set_response(call.session, _own_change_set(call, arguments["changeSetId"]))
    submission = answer.submission
    last = submission.decisions[-1] if submission and submission.decisions else None
    return {
        "id": answer.id,
        "workspace": answer.workspaceKey,
        "name": answer.name,
        "version": answer.version,
        "modelReleaseId": answer.modelReleaseId,
        "modelReleaseKey": answer.modelReleaseKey,
        "submission": None
        if submission is None
        else {
            "state": submission.state,
            "comment": submission.comment,
            "submittedVersion": submission.version,
            "lastDecision": None
            if last is None
            else {
                "outcome": last.outcome,
                "comment": last.comment,
                "decidedAt": last.decidedAt.isoformat(),
                "decidedBy": last.decider.name if last.decider else None,
            },
        },
    }


def _change_set_changes(call: Call, arguments: dict[str, Any]) -> dict[str, Any]:
    change_set_id = _own_change_set(call, arguments["changeSetId"]).id
    paging = PageRequest(cursor=arguments.get("cursor"))
    read = relation_change_page if arguments.get("kind") == "relationships" else object_change_page
    return _dumped(read(call.session, change_set_id, paging, arguments["pageSize"]))


def _cut_diagnostics(result: ChangeSetValidation, start: int) -> dict[str, Any]:
    """The diagnostics from ``start``, as many as fit the answer size, and where to read on."""
    limit = get_settings().mcp_answer_bytes
    end = len(result.diagnostics)
    while True:
        shown = result.diagnostics[start:end]
        answer: dict[str, Any] = {
            "valid": result.valid,
            "count": len(result.diagnostics),
            "diagnostics": shown,
        }
        if end < len(result.diagnostics):
            answer["nextCursor"] = str(end)
        if answer_size(answer) <= limit or len(shown) <= 1:
            return answer
        end = start + len(shown) // 2


def _validate_change_set(call: Call, arguments: dict[str, Any]) -> dict[str, Any]:
    change_set_id = _own_change_set(call, arguments["changeSetId"]).id
    cursor = arguments.get("cursor")
    if cursor is not None and not cursor.isdecimal():
        raise api_error(422, "INVALID_CURSOR", "Validation cursor is invalid")
    # Reading on records nothing: the check was recorded by the call that started it.
    result = validated_change_set(call.session, change_set_id, record=cursor is None)
    return _cut_diagnostics(result, int(cursor or 0))


def _create_change_set(call: Call, arguments: dict[str, Any]) -> dict[str, Any]:
    workspace = _readable(call, arguments["workspace"], CHANGE_SETS)
    started = new_change_set(
        call.session, workspace, ChangeSetCreate(name=arguments["name"], source="currentLive")
    )
    return {
        "changeSetId": started.id,
        "workspace": started.workspaceKey,
        "name": started.name,
        "version": started.version,
        "modelReleaseId": started.modelReleaseId,
    }


def _add_record(call: Call, arguments: dict[str, Any]) -> dict[str, Any]:
    item = _own_change_set(call, arguments["changeSetId"])
    payload = _payload(
        ObjectCreate,
        {
            **_given(
                arguments,
                "applicationKey",
                "objectTypeKey",
                "name",
                "parentObjectId",
                "changeSetId",
                "expectedChangeSetVersion",
            ),
            "attributes": _attribute_list(arguments.get("attributes")),
        },
    )
    refuse_repeated_attributes(payload.attributes)
    row = change_set_object_created(call.session, payload)
    return {"id": row.object_id, "version": row.version, "changeSetVersion": item.version}


def _change_record(call: Call, arguments: dict[str, Any]) -> dict[str, Any]:
    item = _own_change_set(call, arguments["changeSetId"])
    body = _given(
        arguments,
        "name",
        "parentObjectId",
        "expectedVersion",
        "changeSetId",
        "expectedChangeSetVersion",
    )
    if "attributes" in arguments:
        body["attributes"] = _attribute_list(arguments["attributes"])
    payload = _payload(ObjectUpdate, body)
    refuse_repeated_attributes(payload.attributes)
    row = change_set_object_updated(call.session, arguments["objectType"], arguments["id"], payload)
    return {"id": row.object_id, "version": row.version, "changeSetVersion": item.version}


def _set_field(call: Call, arguments: dict[str, Any]) -> dict[str, Any]:
    item = _own_change_set(call, arguments["changeSetId"])
    row = patch_change_set_attribute(
        call.session,
        item.id,
        arguments["id"],
        arguments["attributeTypeKey"],
        arguments["value"],
        arguments["expectedChangeSetVersion"],
        arguments["expectedVersion"],
    )
    return {"id": row.object_id, "version": row.version, "changeSetVersion": item.version}


def _add_relation(call: Call, arguments: dict[str, Any]) -> dict[str, Any]:
    item = _own_change_set(call, arguments["changeSetId"])
    payload = _payload(
        RelationCreate,
        _given(
            arguments,
            "relationTypeKey",
            "fromObjectId",
            "toObjectId",
            "attributes",
            "changeSetId",
            "expectedChangeSetVersion",
        ),
    )
    row, _set_version = change_set_relation_created(call.session, payload)
    return {"id": row.relation_id, "version": row.version, "changeSetVersion": item.version}


def _change_relation(call: Call, arguments: dict[str, Any]) -> dict[str, Any]:
    item = _own_change_set(call, arguments["changeSetId"])
    payload = _payload(
        RelationUpdate,
        _given(
            arguments, "attributes", "expectedVersion", "changeSetId", "expectedChangeSetVersion"
        ),
    )
    row = change_set_relation_updated(call.session, arguments["id"], payload)
    return {"id": row.relation_id, "version": row.version, "changeSetVersion": item.version}


def _submit_change_set(call: Call, arguments: dict[str, Any]) -> dict[str, Any]:
    item = _own_change_set(call, arguments["changeSetId"])
    submission = approvals.submit(
        call.session, item.id, arguments["expectedChangeSetVersion"], arguments.get("comment")
    )
    return {
        "submissionId": submission.id,
        "state": submission.state,
        "changeSetVersion": submission.version_submitted,
    }


def _schema(required: tuple[str, ...], **properties: Any) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": list(required),
        "additionalProperties": False,
    }


_TEXT = {"type": "string"}
_VERSION = {"type": "integer", "minimum": 1}
# A value is set, never cleared: nothing is removed through a tool (AG-D32).
_VALUE = {"not": {"type": "null"}}
_CHANGE_SET = {
    **_TEXT,
    "description": "A change set this connection created; its ID comes from my_change_sets",
}
_ON_CHANGE_SET = {
    "changeSetId": _CHANGE_SET,
    "expectedChangeSetVersion": {
        **_VERSION,
        "description": "The change set's version as last read; a write fails if it has moved",
    },
}
_RECORD_VERSION = {**_VERSION, "description": "The record's version as last read"}
_ATTRIBUTES = {
    "description": "Values by attribute key, as an object or a list of {attributeTypeKey, value}. "
    "A value is never null.",
    "anyOf": [
        {"type": "object", "additionalProperties": _VALUE},
        {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"attributeTypeKey": _TEXT, "value": _VALUE},
                "required": ["attributeTypeKey", "value"],
                "additionalProperties": False,
            },
        },
    ],
}
_RELATION_ATTRIBUTES = {
    "type": "object",
    "additionalProperties": _VALUE,
    "description": "Values by attribute key; a value is never null",
}
_IN_CHANGE_SET = {
    **_TEXT,
    "description": "Read a change set this connection created, with its unpublished rows, instead "
    "of live data",
}


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
        "properties": {"workspace": _TEXT, "changeSetId": _IN_CHANGE_SET, **schema["properties"]},
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
        "relationships and the views that show it. With changeSetId, as that change set's "
        "model release has it.",
        _schema(
            ("workspace", "objectType"),
            workspace=_TEXT,
            objectType=_TEXT,
            changeSetId=_IN_CHANGE_SET,
        ),
        _describe_type,
        group=BROWSE,
    ),
    Tool(
        "find_records",
        "Records of one type matching criteria over their fields, ancestors and one relation hop. "
        f"Live data, or with changeSetId that change set's. {READ_ON}",
        _query_schema(),
        _find_records,
        group=BROWSE,
        page_size=_PAGE_SIZE,
    ),
    Tool(
        "read_record",
        "One record with its values and path, and a page of its relationships; with changeSetId "
        f"as that change set holds it. {READ_ON}",
        _schema(
            ("workspace", "objectType", "id"),
            workspace=_TEXT,
            objectType=_TEXT,
            id=_TEXT,
            changeSetId=_IN_CHANGE_SET,
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
    Tool(
        "my_change_sets",
        "The open change sets this connection created, newest change first, with version and "
        f"submission state. {READ_ON}",
        _schema((), workspace=_TEXT, **_paged(100)),
        _my_change_sets,
        group=CHANGE_SETS,
        page_size=20,
    ),
    Tool(
        "read_change_set",
        "One of your change sets: its version, model release and submission state, with the last "
        "decision's outcome and comment, such as why it was sent back.",
        _schema(("changeSetId",), changeSetId=_CHANGE_SET),
        _read_change_set,
        group=CHANGE_SETS,
    ),
    Tool(
        "change_set_changes",
        "The records or relationships one of your change sets adds, changes or removes against "
        f"live data. {READ_ON}",
        _schema(
            ("changeSetId",),
            changeSetId=_CHANGE_SET,
            kind={"type": "string", "enum": ["records", "relationships"]},
            **_paged(),
        ),
        _change_set_changes,
        group=CHANGE_SETS,
        page_size=_PAGE_SIZE,
    ),
    Tool(
        "validate_change_set",
        "Check one of your change sets against the model's rules, as submitting does, and list what "
        "is wrong. A long list comes in parts: pass nextCursor back as cursor to read on.",
        _schema(("changeSetId",), changeSetId=_CHANGE_SET, cursor=_TEXT),
        _validate_change_set,
        group=CHANGE_SETS,
        writes="change-sets.write",
    ),
    Tool(
        "create_change_set",
        "Start a change set in a workspace, from its live data. Changes are prepared in it and reach "
        "live data only when a person approves it.",
        _schema(
            ("workspace", "name"),
            workspace=_TEXT,
            name={"type": "string", "minLength": 1, "maxLength": 300},
        ),
        _create_change_set,
        group=CHANGE_SETS,
        writes="change-sets.write",
    ),
    Tool(
        "add_record",
        "Add a new record to one of your change sets. It reaches live data only when a person "
        "approves the change set. Answers its ID and versions.",
        _schema(
            ("changeSetId", "expectedChangeSetVersion", "applicationKey", "objectTypeKey", "name"),
            **_ON_CHANGE_SET,
            applicationKey=_TEXT,
            objectTypeKey=_TEXT,
            name={"type": "string", "minLength": 1, "maxLength": 500},
            parentObjectId=_TEXT,
            attributes=_ATTRIBUTES,
        ),
        _add_record,
        group=CHANGE_SETS,
        writes="records.write",
    ),
    Tool(
        "change_record",
        "Change a record's name, parent or values in one of your change sets; attributes given are "
        "set, others kept. It reaches live data only when a person approves the change set.",
        _schema(
            (
                "changeSetId",
                "expectedChangeSetVersion",
                "objectType",
                "id",
                "expectedVersion",
            ),
            **_ON_CHANGE_SET,
            objectType=_TEXT,
            id=_TEXT,
            expectedVersion=_RECORD_VERSION,
            name={"type": "string", "minLength": 1, "maxLength": 500},
            parentObjectId=_TEXT,
            attributes=_ATTRIBUTES,
        ),
        _change_record,
        group=CHANGE_SETS,
        writes="records.write",
    ),
    Tool(
        "set_field",
        "Set one value of a record in one of your change sets, adding it or replacing it. It reaches "
        "live data only when a person approves the change set.",
        _schema(
            (
                "changeSetId",
                "expectedChangeSetVersion",
                "id",
                "attributeTypeKey",
                "value",
                "expectedVersion",
            ),
            **_ON_CHANGE_SET,
            id=_TEXT,
            attributeTypeKey=_TEXT,
            value=_VALUE,
            expectedVersion=_RECORD_VERSION,
        ),
        _set_field,
        group=CHANGE_SETS,
        writes="records.write",
    ),
    Tool(
        "add_relation",
        "Relate two records in one of your change sets. It reaches live data only when a person "
        "approves the change set.",
        _schema(
            (
                "changeSetId",
                "expectedChangeSetVersion",
                "relationTypeKey",
                "fromObjectId",
                "toObjectId",
            ),
            **_ON_CHANGE_SET,
            relationTypeKey=_TEXT,
            fromObjectId=_TEXT,
            toObjectId=_TEXT,
            attributes=_RELATION_ATTRIBUTES,
        ),
        _add_relation,
        group=CHANGE_SETS,
        writes="records.write",
    ),
    Tool(
        "change_relation",
        "Replace the values of a relationship in one of your change sets. It reaches live data only "
        "when a person approves the change set.",
        _schema(
            (
                "changeSetId",
                "expectedChangeSetVersion",
                "id",
                "expectedVersion",
                "attributes",
            ),
            **_ON_CHANGE_SET,
            id=_TEXT,
            expectedVersion={**_VERSION, "description": "The relationship's version as last read"},
            attributes=_RELATION_ATTRIBUTES,
        ),
        _change_relation,
        group=CHANGE_SETS,
        writes="records.write",
    ),
    Tool(
        "submit_change_set",
        "Send one of your change sets to a person for approval, after checking it. It is then "
        "frozen; the change reaches live data only when a person approves it.",
        _schema(
            ("changeSetId", "expectedChangeSetVersion"),
            **_ON_CHANGE_SET,
            comment={"type": "string", "maxLength": 2000},
        ),
        _submit_change_set,
        group=CHANGE_SETS,
        writes="change-sets.submit",
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
