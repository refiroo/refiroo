"""Model drafts changed by recorded operations (0.10 A2, ADR-041)."""

# The consumer API kinds (0.10 A4c) and the source and mapping kinds (0.10 A5) register themselves in
# ``kinds.KINDS`` when imported; importing them with the package gives every reader of KINDS the
# whole vocabulary.
from . import consumer, mapping  # noqa: F401
