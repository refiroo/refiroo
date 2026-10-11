"""Keys of new elements, generated from their labels (A-D6)."""

import re
import unicodedata
from collections.abc import Iterable


def key_from_label(label: str, taken: Iterable[str]) -> str:
    """Lower-case, hyphen-separated ASCII from ``label``, accents dropped; ``-2``, ``-3``… on a
    clash with ``taken``."""
    ascii_text = unicodedata.normalize("NFKD", label).encode("ascii", "ignore").decode()
    base = re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-") or "element"
    used = set(taken)
    key, suffix = base, 2
    while key in used:
        key, suffix = f"{base}-{suffix}", suffix + 1
    return key
