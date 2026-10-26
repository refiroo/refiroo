"""The caller, people, OAuth clients, token signing keys and sign-in providers (Product 0.12 I1,
I3, API.md § Security)."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from .common import ActorResponse, CollectionPage, PrincipalResponse


class SignInProviderRef(BaseModel):
    key: str
    name: str


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
        description="How a person signed in to this session: `password`, or a sign-in provider's "
        "key (I3); null for a client"
    )
    signInProvider: SignInProviderRef | None = Field(
        default=None, description="The sign-in provider of this session; null for a password"
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
    sentTo: str | None = Field(
        default=None, description="The address the link was queued for, when asked with `send`"
    )


class UserRoleWorkspace(BaseModel):
    key: str
    label: str


class UserRole(BaseModel):
    """A role the person holds, directly or through a group (D298)."""

    key: str
    name: str
    instance: bool = Field(description="Held for the whole instance; then no workspaces are named")
    workspaces: list[UserRoleWorkspace] = Field(
        description="The workspaces it is held in, by label"
    )


class UserIdentityResponse(BaseModel):
    """How a sign-in provider knows the person: the provider and the ID token's subject (D363)."""

    provider: SignInProviderRef
    subject: str


class SecondFactorSummary(BaseModel):
    """A person's authenticator app, as an administrator reads it (0.12 I4b)."""

    method: Literal["authenticator-app"]
    confirmedAt: datetime
    recoveryCodesLeft: int


class PasskeyResponse(BaseModel):
    """A passkey by the name its person gave it; never the credential (0.12 I4c, D394)."""

    id: str
    name: str
    createdAt: datetime
    lastUsedAt: datetime | None = Field(
        description="When it last signed the person in; null if never"
    )


class PasskeyPage(CollectionPage[PasskeyResponse]):
    """A person's passkeys in the order they were made (ADR-030)."""


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
    roles: list[UserRole] = Field(
        description="The roles the person holds, directly or through a group, and where (D298)"
    )
    identities: list[UserIdentityResponse] = Field(
        description="The sign-in providers the person signs in with (0.12 I3, D363)"
    )
    localKept: bool = Field(
        description="Signs in with a password while local sign-in is off: an administrator made "
        "on the server (D365)"
    )
    secondFactor: SecondFactorSummary | None = Field(
        description="The authenticator app they sign in with after their password; null without "
        "one (0.12 I4b, D383)"
    )
    passkeys: int = Field(description="How many passkeys they have (0.12 I4c, D389)")


class UserPage(CollectionPage[UserResponse]):
    """People in the order they were created (ADR-030)."""


class ClientSecretInfo(BaseModel):
    """One of a client's valid secrets; never its value after it was answered."""

    id: str
    createdAt: datetime
    expiresAt: datetime | None = Field(description="The end of its overlap after a rotation")
    lastUsedAt: datetime | None
    hint: str | None = Field(
        description="Its last four characters, to tell secrets apart; null for a secret made "
        "before 0.12 SP2 (D350)"
    )


class ClientConsumerApi(BaseModel):
    """A consumer API a client is granted, by key: its name comes from each workspace's model."""

    key: str
    workspaces: list[UserRoleWorkspace] = Field(description="The workspaces it is granted in")


class ClientResponse(BaseModel):
    id: str = Field(description="The OAuth client_id")
    name: str
    active: bool = Field(description="False once deactivated; a client is never deleted")
    version: int
    createdAt: datetime
    updatedAt: datetime
    lastUsedAt: datetime | None = Field(description="When the client last obtained a token")
    secrets: list[ClientSecretInfo]
    roles: list[UserRole] = Field(
        description="The roles the client holds and where; a client belongs to no group (D348)"
    )
    consumerApis: list[ClientConsumerApi] = Field(
        description="The consumer APIs the client is granted, each with its workspaces (D348)"
    )
    createdBy: PrincipalResponse | None = Field(
        description="Who created it; null when made on the server or before 0.12 Z4 (D349)"
    )


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


SecurityAggregate = Literal[
    "user",
    "group",
    "role",
    "grant",
    "client",
    "token-signing-key",
    "sign-in",
    "sign-in-provider",
    "mail-settings",
    "approval-policy",
]


class SecurityEventResponse(BaseModel):
    """A change to access, or a sign-in (0.12 Z4, D317, D318). ``aggregateId`` is the person's,
    group's or client's public ID, the role's key, the grant's ID, the key's ``kid``, a sign-in
    provider's key (``local`` for local sign-in) or, for a sign-in, the person's ID (``unknown``
    for a username nobody has). ``details`` holds what changed
    (``changedFields`` and the new values for an update; the principal, role and scope for a grant;
    the username and address for a sign-in), never a password, secret, link or key. ``actor`` is
    who made it; a failed sign-in names nobody."""

    id: str
    aggregateType: SecurityAggregate
    aggregateId: str
    action: str
    version: int
    occurredAt: datetime
    actor: ActorResponse | None
    details: dict[str, Any]


class SecurityEventPage(CollectionPage[SecurityEventResponse]):
    """Security events, newest first (ADR-030)."""


class SignInProviderResponse(BaseModel):
    """An OpenID Connect provider people sign in with (0.12 I3, D366); never its secret."""

    key: str = Field(description="In the provider's addresses; fixed")
    name: str = Field(description='The sign-in button reads "Continue with *name*"')
    issuer: str
    clientId: str
    clientSecretSet: bool = Field(description="The client secret is saved; it is never answered")
    groupsClaim: str | None = Field(
        description="The ID token claim holding the person's groups; null: groups are not used"
    )
    enabled: bool
    signOutOfProvider: bool = Field(
        description="Signing out of the engine signs the person out of the provider too (I4a)"
    )
    redirectUri: str = Field(description="The address to register with the provider")
    signedOutUri: str = Field(
        description="The address to register for returning from the provider's sign-out (I4a)"
    )
    people: int = Field(description="How many people have signed in with it")
    lastSignInAt: datetime | None
    version: int
    createdAt: datetime
    updatedAt: datetime


class SignInProviderPage(CollectionPage[SignInProviderResponse]):
    """Sign-in providers in the order they were created (ADR-030)."""


class MySecondFactorResponse(BaseModel):
    """The caller's second factor (0.12 I4b)."""

    enabled: bool = Field(description="An authenticator app is set up and confirmed")
    confirmedAt: datetime | None
    recoveryCodesLeft: int
    passkeys: int = Field(description="How many passkeys the caller has (0.12 I4c)")
    required: bool = Field(
        description="The instance requires a second factor with a password: the last one cannot "
        "be removed"
    )


class SecondFactorEnrolment(BaseModel):
    """What the caller needs to set an authenticator app up, answered once (D386)."""

    secret: str = Field(description="The key to type into the app, base32")
    otpauthUri: str = Field(description="The address a QR code carries (the Key URI Format)")
    qrSvg: str = Field(description="The QR code as an inline SVG, ready to show")


class RecoveryCodesResponse(BaseModel):
    """Ten one-time recovery codes, answered once (D385)."""

    recoveryCodes: list[str]


class LocalSignInResponse(BaseModel):
    """Whether people sign in with a password (D365)."""

    enabled: bool = Field(
        description="False: only the people who keep local sign-in use a password"
    )
    secondFactorRequired: bool = Field(
        description="A password alone does not sign anyone in: they set up an authenticator app on "
        "the sign-in page when they have none (0.12 I4b, D388)"
    )
    keptPeople: int = Field(
        description="Active people who keep local sign-in while it is off (made on the server)"
    )
    version: int
    updatedAt: datetime
