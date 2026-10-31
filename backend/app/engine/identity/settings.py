"""What the deployment configures for identity (Product 0.12 I1, I2)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class IdentitySettings:
    """The key sealed secrets open with (D253), the token issuer (D259), an access token's lifetime
    (D251) and the age at which the signing key is replaced (D254, D264); for the browser (I2), the
    origins a sign-in may return to (D267), a session's idle and absolute ends (D251), how long a
    password-reset link lasts (D272) and a password's least length (D276)."""

    encryption_key: bytes
    issuer: str
    access_token_seconds: int
    signing_key_days: int
    browser_origins: tuple[str, ...] = ()
    session_idle_hours: int = 12
    session_days: int = 14
    password_reset_hours: int = 24
    password_min_length: int = 15
    # Agent access (0.16 AG1): whether ``/mcp`` exists, whether an assistant may register itself and
    # the HTTPS hosts it may then return to.
    agent_access: bool = False
    agent_open_registration: bool = True
    agent_redirect_hosts: tuple[str, ...] = ()

    @property
    def secure_cookies(self) -> bool:
        """The refresh cookie is ``Secure`` when the engine is reached over ``https`` (D268)."""
        return self.issuer.startswith("https://")

    def redirect_uris(self) -> tuple[str, ...]:
        """Where the browser's sign-in may return: ``<origin>/signed-in`` for each browser origin."""
        return tuple(f"{origin.rstrip('/')}/signed-in" for origin in self.browser_origins if origin)
