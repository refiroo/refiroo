"""The tools an assistant can call at ``/mcp`` (Product 0.16 AG-D18).

A tool names the action group it needs; one the caller lacks is not listed, and is refused if called
(hide, never disable). Every tool calls what its route calls, so authorization and paging are the
API's. AG2 and AG3 add to this registry.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from ..common.pagination import PageRequest
from ..engine.authorization.catalogue import GROUPS
from ..engine.authorization.permissions import Permissions
from ..engine.identity.authentication import Principal
from .routers.workspaces import workspace_page


@dataclass(frozen=True)
class Call:
    """Who is calling and what they may do on this audience (the ceiling already applied)."""

    session: Session
    principal: Principal
    permissions: Permissions
    application: str | None


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    input_schema: dict[str, Any]
    run: Callable[[Call, dict[str, Any]], dict[str, Any]]
    # The action group the caller must hold somewhere; None for any caller.
    group: str | None = None

    def offered_to(self, permissions: Permissions) -> bool:
        return self.group is None or permissions.allows_anywhere(self.group)


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
        holding="browse",
        page_size=arguments.get("pageSize", 100),
    )
    return page.model_dump(mode="json")


TOOLS: tuple[Tool, ...] = (
    Tool(
        "describe_access",
        "Who this connection acts as and what it may do: its grants and consumer APIs.",
        {"type": "object", "properties": {}, "additionalProperties": False},
        _describe_access,
    ),
    Tool(
        "list_workspaces",
        "The active workspaces this connection may read, a page at a time. Pass nextCursor back as "
        "cursor to read on.",
        {
            "type": "object",
            "properties": {
                "search": {"type": "string"},
                "cursor": {"type": "string"},
                "pageSize": {"type": "integer", "minimum": 1, "maximum": 500},
            },
            "additionalProperties": False,
        },
        _list_workspaces,
        group="browse",
    ),
)
