"""A stand-in provider for the 0.16 AG4 browser runner (`ag4-ask-in-words.mjs`).

The fake provider cannot be scripted from another process, so this one answers a few fixed phrasings
of a question, on whatever list it is asked about: it reads the list's fields from the context it is
sent, as a real model would, and names nothing the context does not hold.

    since 2026-01-01          the list's updatedAt, on or after the date (none in a change set)
    none under <name>         the first relationship, with none of its records under <name>
    any under <name>          the same, with some
    by <name>                 a part no filter can say (who changed a record)
    slowly                    the answer comes after three seconds
    fail                      the provider is unreachable
"""

import re
import time

from app.engine.proposals.provider import ProposalRequest, ProviderAnswer, ProviderError


class AskStandIn:
    name = "ask-stand-in"
    model = "stand-in-1"

    def propose(self, request: ProposalRequest) -> ProviderAnswer:
        question = request.context["question"]
        fields = request.context["fields"]
        if "slowly" in question:
            time.sleep(3)
        if "fail" in question:
            raise ProviderError("unreachable", "The provider could not be reached")
        filters, not_expressed = [], []
        stamp = next((f["field"] for f in fields if f["field"] == "updatedAt"), None)
        relation = next((f["field"] for f in fields if f["kind"] == "relationship"), None)
        since = re.search(r"since (\d{4}-\d{2}-\d{2})", question)
        if since and stamp:
            filters.append({"field": stamp, "condition": "gte", "value": since.group(1)})
        for word, condition in (("none under", "notUnder"), ("any under", "under")):
            found = re.search(rf"{word} (.+?)(?: by | since |$)", question)
            if found and relation:
                filters.append(
                    {"field": relation, "condition": condition, "value": found.group(1).strip()}
                )
        by = re.search(r"\bby (\w+)", question)
        if by:
            not_expressed.append(
                {
                    "part": f"by {by.group(1)}",
                    "reason": "This list has no filter for who changed a record",
                }
            )
        data = {"filters": filters, "search": "", "notExpressed": not_expressed}
        return ProviderAnswer(data, self.model, tokens_in=10, tokens_out=10)


def provider() -> AskStandIn:
    return AskStandIn()
