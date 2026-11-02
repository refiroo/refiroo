"""An account of what a model change does, in plain language (Product 0.16 AO1).

The engine states the facts and the model only words them. A fact is one line the engine wrote from
the diff of two models, the check of the workspace's data against the candidate, the consumer API
check and a count of the workspace's records per touched type (AO-D12). Its ID derives from its kind,
code and path, so the same fact keeps its ID. The provider is sent the facts, at most ``FACT_LIMIT``
per kind with each kind's true total (AO-D14), and no record: a record count is a number and nothing
else. What it answers is checked here: a statement that cites no fact that exists is dropped and
counted (AO-D2). Nothing is asked of it that a fact does not carry, and the prompt forbids judging
(AO-D18). The route reads, releases its transaction, asks and writes the call record; no transaction
is held while the provider answers (J48.8).
"""

import hashlib
import json
from collections.abc import Iterable, Sequence
from typing import Any, ClassVar, Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...models.database import RdmObject
from ..model.diagnostics import ModelDiagnostic
from ..model.diff import SemanticChange
from . import calls, summaries
from .registry import AiConfiguration
from .summaries import (
    DEFAULT_LANGUAGE,  # noqa: F401  (the account's constants stay reachable here)
    FACT_LIMIT,  # noqa: F401
    TEXT_LIMIT,  # noqa: F401
    Fact,
    Statement,
    Summary,
    SummaryAnswer,
)

PROMPT_VERSION = "impact-summary/2"
PURPOSE = "impactSummary"

Kind = Literal["blocked", "data", "contract", "change", "records"]
KINDS: tuple[Kind, ...] = ("blocked", "data", "contract", "change", "records")
_PREFIX = {"blocked": "bl", "data": "da", "contract": "co", "change": "ch", "records": "re"}

INSTRUCTIONS = """You write a short account of what a change to a data model does, for the person who is about to activate it.
The context holds the facts: each has an id, a kind, a text and sometimes a count, a path, and for a change what it was before and after.
- change: one difference between the model now and the model proposed.
- data: a rule the workspace's data would break, with how many it breaks.
- blocked: activation is refused until something else happens.
- contract: what the change does to the consumer APIs that read this model.
- records: how many records of a type the change touches stand in the workspace.
Where a kind has more facts than the context lists, `more` gives how many and an id for the group that you may cite; `totals` gives each kind's true number of facts. Write "and 12 more", never that facts were not shown or not sent to you: the reader has all of them.
Write 1 to 6 short statements in the language given by the context's language. Each statement says what the facts say and cites the ids of the facts it rests on in factIds, one or more.
- Say only what the facts carry. Do not guess a consequence, a reason or an effect on records that no fact states; when a change has no data fact, say nothing about the data.
- State what changes and by how much. Never say that a change is safe, risky, harmless, breaking, recommended or advisable, and give no advice.
- Use the names in the facts as they are written, and numbers from the facts and the totals exactly: do not count the facts yourself.
- A statement without a fact id is discarded."""


# --- the facts ---


def fact_id(kind: Kind, code: str, path: str) -> str:
    digest = hashlib.sha256(f"{kind}\0{code}\0{path}".encode()).hexdigest()[:8]
    return f"{_PREFIX[kind]}-{digest}"


class _Names:
    """The labels of the models' elements, the candidate's before the baseline's."""

    _COLLECTIONS: ClassVar[dict[str, str]] = {
        "objectTypes": "object type",
        "attributeTypes": "attribute type",
        "relationTypes": "relation type",
        "applications": "application",
        "consumerApis": "consumer API",
    }

    def __init__(self, *documents: dict[str, Any]) -> None:
        self._names: dict[str, dict[str, str]] = {name: {} for name in self._COLLECTIONS}
        for document in reversed([item for item in documents if item]):
            for collection, names in self._names.items():
                for item in document.get(collection, ()):
                    if isinstance(item, dict) and "key" in item:
                        names[item["key"]] = str(item.get("name") or item["key"])

    def label(self, collection: str, key: str) -> str:
        return f"'{self._names.get(collection, {}).get(key, key)}'"

    def knows(self, collection: str) -> bool:
        return collection in self._COLLECTIONS

    def noun(self, collection: str) -> str:
        return self._COLLECTIONS[collection]


def _unescape(segment: str) -> str:
    return segment.replace("~1", "/").replace("~0", "~")


def _shown(value: Any) -> str:
    if isinstance(value, dict | list):
        return "its definition"
    text = json.dumps(value, ensure_ascii=False)
    return text if len(text) <= 60 else text[:59] + "…"


def describe(change: SemanticChange, names: _Names) -> str:
    """One line for a difference, from the models' own labels."""
    parts = [_unescape(part) for part in change.path.split("/")[1:]]
    rest: list[str]
    if parts[0] == "objectTypeRelations" and len(parts) >= 4:
        relation, source, target = parts[1:4]
        subject = (
            f"Relationship {names.label('relationTypes', relation)} from "
            f"{names.label('objectTypes', source)} to {names.label('objectTypes', target)}"
        )
        rest = parts[4:]
    elif names.knows(parts[0]) and len(parts) >= 2:
        subject = f"{names.noun(parts[0]).capitalize()} {names.label(parts[0], parts[1])}"
        rest = parts[2:]
    else:
        subject, rest = "The model", parts
    if not rest:
        if change.kind == "changed":
            return f"{subject} changes from {_shown(change.before)} to {_shown(change.after)}"
        return f"{subject} is {'added' if change.kind == 'added' else 'removed'}"
    if parts[0] == "objectTypes" and rest[0] == "attributes" and len(rest) == 2:
        attribute = names.label("attributeTypes", rest[1])
        type_label = names.label("objectTypes", parts[1])
        if change.kind == "added":
            required = isinstance(change.after, dict) and change.after.get("required")
            return (
                f"Attribute {attribute} is added to object type {type_label}"
                f" ({'required' if required else 'optional'})"
            )
        if change.kind == "removed":
            return f"Attribute {attribute} is removed from object type {type_label}"
    where = " › ".join(rest)
    if change.kind == "added":
        return f"{subject}: {where} is added"
    if change.kind == "removed":
        return f"{subject}: {where} is removed"
    if isinstance(change.before, dict | list) or isinstance(change.after, dict | list):
        return f"{subject}: {where} changes"
    return f"{subject}: {where} changes from {_shown(change.before)} to {_shown(change.after)}"


def touched_types(changes: Iterable[SemanticChange], *documents: dict[str, Any]) -> list[str]:
    """The object types the differences touch: named by a path, an end of a touched relationship, a
    type an application gains or loses, or a type that binds a changed attribute type."""
    found: set[str] = set()
    changed_attributes: set[str] = set()
    for change in changes:
        parts = [_unescape(part) for part in change.path.split("/")[1:]]
        if parts[0] == "objectTypes" and len(parts) >= 2:
            found.add(parts[1])
        elif parts[0] == "objectTypeRelations" and len(parts) >= 4:
            found.update(parts[2:4])
        elif parts[0] == "applications" and len(parts) >= 4 and parts[2] == "objectTypeKeys":
            found.add(parts[3])
        elif parts[0] == "attributeTypes" and len(parts) >= 2:
            changed_attributes.add(parts[1])
    if changed_attributes:
        for document in documents:
            for item in document.get("objectTypes", ()):
                if any(
                    binding.get("attributeTypeKey") in changed_attributes
                    for binding in item.get("attributes", ())
                ):
                    found.add(item["key"])
    return sorted(found)


def record_counts(session: Session, workspace_key: str, type_keys: Sequence[str]) -> dict[str, int]:
    """The workspace's live records per type, in one grouped statement over the whole set."""
    if not type_keys:
        return {}
    rows = session.execute(
        select(RdmObject.object_type_key, func.count())
        .where(RdmObject.workspace_key == workspace_key, RdmObject.object_type_key.in_(type_keys))
        .group_by(RdmObject.object_type_key)
    )
    return {key: count for key, count in rows}


def build_facts(
    session: Session,
    *,
    workspace_key: str,
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    changes: Sequence[SemanticChange],
    compatibility: Sequence[ModelDiagnostic],
    contract: Sequence[ModelDiagnostic],
) -> list[Fact]:
    """Every fact about moving ``workspace_key`` from ``baseline`` to ``candidate`` (canonical
    documents): blocked, data, contract, change and records, each in its own order."""
    names = _Names(candidate, baseline)
    facts: list[Fact] = []
    seen: set[str] = set()

    def add(fact: Fact) -> None:
        if fact.id in seen:
            return
        seen.add(fact.id)
        facts.append(fact)

    if compatibility:
        add(
            Fact(
                fact_id("blocked", "MODEL_MIGRATION_REQUIRED", ""),
                "blocked",
                "The workspace's data does not fit the changed model as it is: a migration is "
                "needed before it can be activated",
            )
        )
    if any(item.severity == "error" for item in contract):
        add(
            Fact(
                fact_id("blocked", "CONSUMER_CONTRACT_VERSION_REQUIRED", ""),
                "blocked",
                "A consumer API changes without a higher contract version, which activation "
                "refuses until the version is raised",
            )
        )
    for item in sorted(compatibility, key=lambda entry: -(entry.count or 0)):
        counted = f" (count: {item.count})" if item.count is not None else ""
        add(
            Fact(
                fact_id("data", item.code, item.path),
                "data",
                f"{item.message}{counted}",
                item.path,
                item.count,
            )
        )
    for item in contract:
        add(Fact(fact_id("contract", item.code, item.path), "contract", item.message, item.path))
    for change in changes:
        add(
            Fact(
                fact_id("change", change.kind, change.path),
                "change",
                describe(change, names),
                change.path,
                None,
                None if change.kind == "added" else change.before,
                None if change.kind == "removed" else change.after,
            )
        )
    counts = record_counts(session, workspace_key, touched_types(changes, baseline, candidate))
    for key, count in sorted(counts.items(), key=lambda entry: (-entry[1], entry[0])):
        label = names.label("objectTypes", key)
        add(
            Fact(
                fact_id("records", "RECORDS", f"/objectTypes/{key}"),
                "records",
                f"Object type {label} has {count} {'record' if count == 1 else 'records'} here",
                f"/objectTypes/{key}",
                count,
            )
        )
    return facts


# --- the context and the answer ---


def context_of(facts: Sequence[Fact], language: str) -> dict[str, Any]:
    """What the provider is sent: at most ``FACT_LIMIT`` facts per kind, the largest counts first
    where a kind has counts, and per kind the true total with a group a statement may cite."""
    return summaries.context_of(facts, language, KINDS, largest_first=("data", "records"))


group_id = summaries.group_id


def checked(answer: SummaryAnswer, facts: Sequence[Fact]) -> tuple[list[Statement], int]:
    return summaries.checked(answer, facts, KINDS)


def explain(
    session: Session,
    ai: AiConfiguration,
    facts: list[Fact],
    *,
    language: str,
    requester: calls.Requester,
) -> Summary:
    """The facts, worded, with the shared asking of ``summaries.explain``."""
    return summaries.explain(
        session,
        ai,
        facts,
        purpose=PURPOSE,
        prompt_version=PROMPT_VERSION,
        instructions=INSTRUCTIONS,
        kinds=KINDS,
        largest_first=("data", "records"),
        language=language,
        requester=requester,
    )


with_level = summaries.with_level
