"""Model drafts changed by recorded operations (0.10 A2, ADR-041)."""

# The consumer API kinds (0.10 A4c) register themselves in ``kinds.KINDS`` when imported; importing
# them with the package gives every reader of KINDS the whole vocabulary.
from . import consumer  # noqa: F401
