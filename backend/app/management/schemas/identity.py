"""The caller, people, OAuth clients and token signing keys (Product 0.12 I1, API.md § Security)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from .common import CollectionPage


class MeResponse(BaseModel):
    """Who the request's token belongs to."""

    id: str
    kind: Literal["user", "client"]
    name: str
    username: str | None = Field(description="A person's username; null for a client")
    email: str | None
    lastSignInAt: datetime | None = Field(
        description="A person's last sign-in, or when a client last obtained a token"
    )
    signedInWith: str | None = Field(
        description="How a person signed in to this session: `password`; null for a client"
    )
    sessionId: str | None = Field(description="A person's session; null for a client")


class SessionResponse(BaseModel):
    """One of a person's open browser sessions."""

    id: str
    current: bool = Field(description="The session the request's token was issued in")
    signedInWith: str
    userAgent: str | None = Field(description="The browser that signed in, as it named itself")
    createdAt: datetime
    lastUsedAt: datetime = Field(description="When the session was last renewed")
    endsAt: datetime = Field(description="When it ends unless renewed sooner, or at the latest")


class SessionPage(CollectionPage[SessionResponse]):
    """A person's open sessions in the order they started (ADR-030)."""


class PasswordResetLinkResponse(BaseModel):
    """A one-time link that sets a person's password, answered this once (D272)."""

    url: str = Field(description="The link to pass to the person; valid once")
    expiresAt: datetime


class UserResponse(BaseModel):
    id: str
    username: str
    name: str
    email: str | None
    active: bool = Field(description="False once deactivated; a person is never deleted")
    hasPassword: bool = Field(
        description="Whether the person has set a password; never the password"
    )
    version: int
    createdAt: datetime
    updatedAt: datetime
    lastSignInAt: datetime | None


class UserPage(CollectionPage[UserResponse]):
    """People in the order they were created (ADR-030)."""


class ClientSecretInfo(BaseModel):
    """One of a client's valid secrets; never its value after it was answered."""

    id: str
    createdAt: datetime
    expiresAt: datetime | None = Field(description="The end of its overlap after a rotation")
    lastUsedAt: datetime | None


class ClientResponse(BaseModel):
    id: str = Field(description="The OAuth client_id")
    name: str
    active: bool = Field(description="False once deactivated; a client is never deleted")
    version: int
    createdAt: datetime
    updatedAt: datetime
    lastUsedAt: datetime | None = Field(description="When the client last obtained a token")
    secrets: list[ClientSecretInfo]


class ClientWithSecret(ClientResponse):
    """A client with the secret just made, answered this once."""

    secretId: str
    secret: str = Field(description="The client_secret; it is never answered again")


class ClientPage(CollectionPage[ClientResponse]):
    """Clients in the order they were created (ADR-030)."""


class SigningKeyResponse(BaseModel):
    """A token signing key, without its private half."""

    kid: str
    state: Literal["current", "verifying", "retired"] = Field(
        description="current signs new tokens; verifying still accepts the tokens it signed; "
        "retired accepts none"
    )
    createdAt: datetime
    rotatedAt: datetime | None
    retiredAt: datetime | None


class SigningKeyPage(CollectionPage[SigningKeyResponse]):
    """Token signing keys, newest first (ADR-030)."""
