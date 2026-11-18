"""Agent access for security administrators (Product 0.16 AG1)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .common import CollectionPage
from .identity import ClientResponse


class McpSystemInfo(BaseModel):
    enabled: bool = Field(description="Whether assistants can reach the instance at /mcp")


class AgentAccessStatus(BaseModel):
    """The settings as read at start and the last 30 days' calls."""

    enabled: bool
    url: str = Field(description="The address an assistant connects to")
    ratePerMinute: int
    openRegistration: bool = Field(description="Whether an assistant may register itself")
    redirectHosts: list[str] = Field(
        description="HTTPS hosts a self-registered assistant may return to, besides this computer"
    )
    callsDays: int = Field(description="Days a call's record is kept")
    calls30Days: int
    lastCallAt: datetime | None
    sessionIdleDays: int = Field(
        description="Days an assistant's session may go without a renewal before it ends"
    )
    sessionDays: int = Field(description="Days an assistant's session lasts in all")
    sessionLimitsVersion: int = Field(
        description="The version of the two limits; rises by one with every change"
    )
    browserSessionIdleHours: int = Field(
        description="Hours a browser sign-in may go without use, set in the server's environment"
    )
    browserSessionDays: int = Field(
        description="Days a browser sign-in lasts in all, set in the server's environment"
    )


class AgentAccessUpdate(BaseModel):
    """The limits of an assistant's session; a field left out keeps its value."""

    model_config = ConfigDict(extra="forbid")

    sessionIdleDays: int | None = Field(default=None, ge=1, le=365)
    sessionDays: int | None = Field(
        default=None, ge=1, le=365, description="Not fewer than the days without use"
    )
    expectedVersion: int | None = Field(
        default=None, ge=0, description="The `sessionLimitsVersion` the client read"
    )


class AgentClientResponse(ClientResponse):
    calls30Days: int
    lastCallAt: datetime | None


class AgentClientPage(CollectionPage[AgentClientResponse]):
    """Agent clients in the order they were created (ADR-030)."""


class AgentApplicationResponse(BaseModel):
    id: str = Field(description="Its OAuth client_id")
    name: str = Field(description="What the assistant says of itself")
    source: Literal["registered", "administrator"]
    returnsTo: list[str] = Field(description="Where a sign-in may return, in a person's words")
    blocked: bool
    signedIn: int = Field(description="People with an open session for it")
    createdAt: datetime
    lastUsedAt: datetime | None = Field(description="When someone last signed in or renewed")


class AgentApplicationPage(CollectionPage[AgentApplicationResponse]):
    """The assistants people sign in with, in the order they were registered (ADR-030)."""


class AgentApplicationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    redirectUris: list[str] = Field(
        min_length=1, description="Exact HTTPS addresses, or a loopback address on any port"
    )


class AgentCallResponse(BaseModel):
    id: str
    occurredAt: datetime
    principal: str = Field(description="The person's or client's name")
    principalKind: Literal["user", "client"]
    principalId: str
    application: str | None = Field(description="The assistant; null for a client's own calls")
    tool: str
    arguments: list[str] = Field(description="The names of its arguments, never their values")
    outcome: Literal["answered", "refused", "limited", "failed"]
    durationMs: int
    requestId: str | None


class AgentCallPage(CollectionPage[AgentCallResponse]):
    """Tool calls newest first (ADR-030)."""
