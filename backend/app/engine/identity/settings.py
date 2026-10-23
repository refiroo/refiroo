"""What the deployment configures for identity (Product 0.12 I1)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class IdentitySettings:
    """The key sealed secrets open with (D253), the token issuer (D259), an access token's lifetime
    (D251) and the age at which the signing key is replaced (D254, D264)."""

    encryption_key: bytes
    issuer: str
    access_token_seconds: int
    signing_key_days: int
