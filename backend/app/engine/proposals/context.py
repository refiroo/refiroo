"""What a provider may be sent (AP-D3): the send level's policy.

``AI_SEND_LEVEL`` is the ceiling: ``structure`` sends keys, labels, headers, attribute names and
types and no value; ``samples`` adds values, at most ``AI_SAMPLE_VALUES`` per column whatever a
feature asks for; ``values`` sends the values a feature asks for, as many as it needs. A feature that
needs more than the ceiling is not offered (``FEATURE_LEVELS``). This module reads no data: each
feature builds its own context, and asks ``Policy.values`` how many values it may include.

The one exception is the question in words (AG-D35, revised 2026-11-01): it is offered at
``structure`` and sends nothing of the data there, but at ``samples`` and ``values`` it sends the
names of the records of a relationship's types when the list holds at most 50 of them, a short list
whole and not ``AI_SAMPLE_VALUES`` of it.
"""

from dataclasses import dataclass

from ...config import SEND_LEVELS, SendLevel
from .provider import Purpose

# The least each purpose needs to be useful. The inference's names work from headers alone, and
# are better with the columns' values.
FEATURE_LEVELS: dict[Purpose, SendLevel] = {
    "connectionTest": "structure",
    # Record names are values (AP2-D3).
    "mappingTarget": "values",
    # The question and the list's fields, conditions and relationships; the names of short lists
    # only at samples or values (AG-D35, revised 2026-11-01).
    "queryTranslation": "structure",
    # The facts of a model change and counts of records, no record (AO-D1).
    "impactSummary": "structure",
    # Counts and the model's labels; names only at ``values`` (AO-D23).
    "historyAccount": "structure",
}


@dataclass(frozen=True)
class Policy:
    level: SendLevel
    samples: int

    def allows(self, needed: SendLevel) -> bool:
        return SEND_LEVELS.index(needed) <= SEND_LEVELS.index(self.level)

    def offers(self, purpose: Purpose) -> bool:
        return self.allows(FEATURE_LEVELS[purpose])

    def values(self, wanted: int) -> int:
        """How many of the ``wanted`` values may be sent: none at ``structure``, at most
        ``AI_SAMPLE_VALUES`` at ``samples``, all of them at ``values``."""
        if not self.allows("samples"):
            return 0
        return wanted if self.allows("values") else min(wanted, self.samples)


# The characters a token holds at the least (JSON with codes tokenises densely).
CHARS_PER_TOKEN = 3


def estimated_tokens(characters: int) -> int:
    """The tokens ``characters`` of a request cost, estimated."""
    return characters // CHARS_PER_TOKEN


def within_window(characters: int, context_tokens: int | None, answer_tokens: int = 0) -> bool:
    """Whether a request of ``characters`` and an answer of ``answer_tokens`` fit half of the
    model's window (the rest is the model's); always without a window."""
    if context_tokens is None:
        return True
    return estimated_tokens(characters) + answer_tokens <= context_tokens // 2
