"""The product's name as the default workspace's model gives it: what the authenticator app labels
an account with, the sign-in pages carry and every mail calls the product. Kept apart so the modules
that change a person's sign-in can queue a security message (``mail/security_notice``) without an
import cycle."""

from sqlalchemy.orm import Session

from ...errors import ApiError
from ..model.registry import resolve_model_snapshot


def product_name(session: Session, fallback: str) -> str:
    """The default workspace's product name, or ``fallback`` where there is none."""
    try:
        return resolve_model_snapshot(session, None).model.product.name
    except ApiError:
        return fallback
