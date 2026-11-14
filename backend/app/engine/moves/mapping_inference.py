"""A model mapping's inference (0.11 X1, D108, D109): the job that proposes, its reads, and the
application of its proposals as steps marked Proposed.

``POST /model-mappings/{key}/inference`` names a source and a target workspace running the
mapping's two models and queues a job of kind ``mappingInference``. The worker compares the
mapping's two releases element by element and proposes:

- per source type, the target type it becomes (``mapType``), its attributes (``mapAttribute``),
  when both types stand under a parent, where (``setParent``), and, when the two workspaces' records
  share values, how existing target records are found: by a unique attribute the pair maps
  (``setMatch``);
- per relationship a mapped source type holds at its ``from`` end, the target relationship
  (``mapRelation``) between the mapped types, with its relation attributes.

Each proposal carries its **evidence** and up to three alternatives. A candidate is scored from:
the same key in one model (``sameModel``, I34: identity), the same key (``sameKey``), the keys'
words (``keyTokens``), the same name (``sameName``), the attributes the two types share by key or
name with convertible values (``attributes``), the parents already proposed (``parent``) and the
**stored records**: the share of the source type's names and unique values found among a target
type's records, read for every pair of types in one statement over the two workspaces
(``storedRecords``). A candidate below one point is not proposed.

A proposal's ID is the same in every inference of the mapping, so its status reads from the
mapping as it is and its history (D92's statuses, read rather than stored): ``applied`` while the
entry is as the proposal makes it, ``held`` when the mapping decides it otherwise, ``rejected`` when
a step that applied it was undone, ``open`` otherwise.
"""

import json
import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from ...common.pagination import Page, PageRequest, integer_key, paginate_statement
from ...errors import api_error
from ...models.database import (
    Job,
    ModelMapping,
    ModelMappingOperation,
    ModelMappingProposal,
    WorkspaceModel,
)
from ...models.schema import ObjectTypeRelationDefinition
from ..jobs.background import CANCELLABLE, replace_earlier_job
from ..jobs.store import job_parameter, start_job
from ..model.authoring import history
from ..model.authoring.kinds import Applied
from ..records.values import conversion, value_json_sql
from .mappings import MAPPINGS, Releases, load_mapping, mismatch
from .sides import Side

KIND = "mappingInference"
STATUSES = ("open", "applied", "held", "rejected")
# A candidate scoring less is not proposed; alternatives are the next ones with any evidence.
THRESHOLD = 1.0
ALTERNATIVES = 3
_KEYS = (integer_key("position", ModelMappingProposal.position, "position"),)
_NAMESPACE = uuid.UUID("6f1d2b2e-0b51-4f7c-9c38-5d0f6f3a9e11")


# --- scoring ---------------------------------------------------------------------------------------


def _words(key: str) -> set[str]:
    return {word for word in re.split(r"[^0-9a-z]+", key.lower()) if word}


def _folded(name: str | None) -> str:
    return " ".join((name or "").lower().split())


def _likeness(
    source_key: str,
    source_name: str | None,
    target_key: str,
    target_name: str | None,
    same_model: bool,
) -> tuple[float, list[dict[str, Any]]]:
    """How much two elements' keys and names say they are one: a score and its evidence."""
    if source_key == target_key:
        return (10.0, [{"kind": "sameModel"}]) if same_model else (3.0, [{"kind": "sameKey"}])
    score, evidence = 0.0, []
    words, others = _words(source_key), _words(target_key)
    if words & others:
        share = len(words & others) / len(words | others)
        score += 2 * share
        evidence.append({"kind": "keyTokens", "share": round(share, 2)})
    if source_name and _folded(source_name) == _folded(target_name):
        score += 2.0
        evidence.append({"kind": "sameName"})
    return score, evidence


@dataclass
class Candidate:
    target: str
    score: float
    evidence: list[dict[str, Any]]
    direction: str = "outgoing"


@dataclass
class Proposal:
    anchor: str
    kind: str
    source_type: str
    target: str
    score: float
    evidence: list[dict[str, Any]]
    operations: list[dict[str, Any]]
    # What the proposal leaves in the mapping, read back to tell its status.
    expected: dict[str, Any]
    alternatives: list[dict[str, Any]] = field(default_factory=list)
    requires: list[str] = field(default_factory=list)
    relation: str | None = None

    @property
    def summary(self) -> str:
        if self.kind == "type":
            return f"Type '{self.source_type}' becomes '{self.target}'"
        return f"Relation '{self.relation}' of '{self.source_type}' becomes '{self.target}'"

    def signature(self) -> str:
        return json.dumps(self.operations, sort_keys=True)


class Inference:
    """The proposals for one source and one target release, given what the stored records share:
    ``stored[(source type, target type)]`` values found, ``totals[source type]`` values read and
    ``keys[(source type, target type)]`` the pairs of unique attributes whose values they share."""

    def __init__(
        self,
        source: Side,
        target: Side,
        stored: dict[tuple[str, str], int] | None = None,
        totals: dict[str, int] | None = None,
        keys: dict[tuple[str, str], set[tuple[str, str]]] | None = None,
    ) -> None:
        self.source, self.target = source, target
        self.same_model = source.model_key == target.model_key
        self.stored = stored or {}
        self.totals = totals or {}
        self.keys = keys or {}
        self._attribute_likeness: dict[tuple[str, str], float] = {}

    def attribute_likeness(self, source_key: str, target_key: str) -> float:
        """A source attribute's likeness to a target attribute; none when no value converts."""
        pair = (source_key, target_key)
        if pair not in self._attribute_likeness:
            source, target = (
                self.source.model.attribute_type(source_key),
                self.target.model.attribute_type(target_key),
            )
            if (
                source is None
                or target is None
                or conversion(source.valueType, target.valueType) == "never"
            ):
                self._attribute_likeness[pair] = 0.0
            else:
                score, _ = _likeness(
                    source_key, source.name, target_key, target.name, self.same_model
                )
                self._attribute_likeness[pair] = score + (
                    0.5 if score and source.valueType == target.valueType else 0.0
                )
        return self._attribute_likeness[pair]

    def attribute_pairs(self, sources: list[str], targets: list[str]) -> list[tuple[str, str]]:
        """Each source attribute with the target attribute most like it, each target taken once."""
        scored = sorted(
            ((self.attribute_likeness(a, b), a, b) for a in sources for b in targets),
            key=lambda item: (-item[0], sources.index(item[1]), targets.index(item[2])),
        )
        taken: dict[str, str] = {}
        used: set[str] = set()
        for score, a, b in scored:
            if score < THRESHOLD or a in taken or b in used:
                continue
            taken[a], used = b, used | {b}
        return [(a, taken[a]) for a in sources if a in taken]

    # --- types ---

    def _type_candidates(self, source_type: str, parents: dict[str, str]) -> list[Candidate]:
        source = self.source.model.object_type(source_type)
        assert source is not None
        own = [b.attributeTypeKey for b in source.attributes]
        found = []
        for target in self.target.model.objectTypes:
            score, evidence = _likeness(
                source_type, source.name, target.key, target.name, self.same_model
            )
            theirs = [b.attributeTypeKey for b in target.attributes]
            if own:
                matched = sum(
                    1
                    for a in own
                    if any(self.attribute_likeness(a, b) >= THRESHOLD for b in theirs)
                )
                if matched:
                    score += 2 * matched / len(own)
                    evidence.append({"kind": "attributes", "matched": matched, "of": len(own)})
            matched = self.stored.get((source_type, target.key), 0)
            if matched:
                total = max(self.totals.get(source_type, matched), matched)
                score += 3 * matched / total
                evidence.append({"kind": "storedRecords", "matched": matched, "of": total})
            mapped_parents = {
                parents[p] for _, p in self.source.parents(source_type) if p in parents
            }
            if mapped_parents and mapped_parents <= {p for _, p in self.target.parents(target.key)}:
                score += 0.5
                evidence.append({"kind": "parent"})
            if score > 0:
                found.append(Candidate(target.key, round(score, 3), evidence))
        found.sort(key=lambda c: (-c.score, self.target.type_keys.index(c.target)))
        return found

    def _type_proposal(
        self, source_type: str, best: Candidate, others: list[Candidate], chosen: dict[str, str]
    ) -> Proposal:
        t = best.target
        operations: list[dict[str, Any]] = [
            {"kind": "mapType", "sourceType": source_type, "targetType": t}
        ]
        attributes = []
        pairs = self.attribute_pairs(
            [b.attributeTypeKey for b in self.source.bindings(source_type)],
            [b.attributeTypeKey for b in self.target.bindings(t)],
        )
        for a, b in pairs:
            operations.append(
                {"kind": "mapAttribute", "sourceType": source_type, "attribute": a, "target": b}
            )
            attributes.append({"source": a, "target": b})
        parent = self._parent(source_type, t, chosen)
        if parent is not None:
            operations.append({"kind": "setParent", "sourceType": source_type, "parent": parent})
        # Records the target already holds are found by a unique attribute the pair maps, when
        # the two workspaces' records share values (I12); never on names alone.
        match = None
        if self.stored.get((source_type, t)):
            # The unique pair whose values the records share, else the first unique pair.
            unique_pairs = [
                (a, b) for a, b in pairs if self.source.unique(a) and self.target.unique(b)
            ]
            shared = self.keys.get((source_type, t), set())
            unique = next(
                (b for a, b in unique_pairs if (a, b) in shared),
                unique_pairs[0][1] if unique_pairs else None,
            )
            if unique is not None:
                match = {"attributeTypeKey": unique}
                operations.append({"kind": "setMatch", "sourceType": source_type, "match": match})
        return Proposal(
            anchor=f"type:{source_type}",
            kind="type",
            source_type=source_type,
            target=t,
            score=best.score,
            evidence=best.evidence,
            operations=operations,
            expected={"target": t, "attributes": attributes, "parent": parent, "match": match},
            alternatives=[
                {
                    "target": c.target,
                    "score": c.score,
                    "label": f"'{source_type}' becomes '{c.target}'",
                    "operations": [
                        {"kind": "mapType", "sourceType": source_type, "targetType": c.target}
                    ],
                }
                for c in others[:ALTERNATIVES]
            ],
        )

    def _parent(
        self, source_type: str, target_type: str, chosen: dict[str, str]
    ) -> dict[str, Any] | None:
        """Under the target record of the source parent, through the containment the mapped parent
        names when there is one (I21, I22)."""
        theirs = self.target.parents(target_type)
        ours = self.source.parents(source_type)
        if not ours or not theirs:
            return None
        parent: dict[str, Any] = {"from": "source"}
        parent_types = {p for _, p in ours}
        through = [
            r
            for r, p in theirs
            if len(parent_types) == 1 and chosen.get(next(iter(parent_types))) == p
        ]
        if not through and len(theirs) == 1:
            through = [theirs[0][0]]
        if len(through) == 1:
            parent["relationTypeKey"] = through[0]
        return parent

    # --- relations ---

    def _relation_proposals(
        self, source_type: str, chosen: dict[str, str], type_anchor: str
    ) -> list[Proposal]:
        t = chosen[source_type]
        bindings: dict[str, list[ObjectTypeRelationDefinition]] = {}
        for item in self.source.relations_from(source_type):
            bindings.setdefault(item.relationTypeKey, []).append(item)
        found = []
        for relation, ours in bindings.items():
            ends = {chosen[b.toObjectTypeKey] for b in ours if b.toObjectTypeKey in chosen}
            if not ends:
                continue
            candidates = self._relation_candidates(relation, ours, t, ends)
            if not candidates or candidates[0].score < THRESHOLD:
                continue
            best = candidates[0]
            theirs = self.target.relation_ends(best.target, t, best.direction)
            pairs = self.attribute_pairs(
                list(dict.fromkeys(a for b in ours for a in b.attributeTypeKeys)),
                list(dict.fromkeys(a for b in theirs for a in b.attributeTypeKeys)),
            )
            operation: dict[str, Any] = {
                "kind": "mapRelation",
                "sourceType": source_type,
                "relation": relation,
                "target": best.target,
                "direction": best.direction,
            }
            item: dict[str, Any] = {
                "source": relation,
                "target": best.target,
                "direction": best.direction,
            }
            if pairs:
                operation["attributes"] = item["attributes"] = [
                    {"source": a, "target": b} for a, b in pairs
                ]
            found.append(
                Proposal(
                    anchor=f"relation:{source_type}/{relation}",
                    kind="relation",
                    source_type=source_type,
                    relation=relation,
                    target=best.target,
                    score=best.score,
                    evidence=best.evidence,
                    operations=[operation],
                    expected=item,
                    requires=[type_anchor],
                    alternatives=[
                        {
                            "target": c.target,
                            "score": c.score,
                            "label": f"'{relation}' becomes '{c.target}' ({c.direction})",
                            "operations": [
                                {
                                    **operation,
                                    "target": c.target,
                                    "direction": c.direction,
                                    "attributes": [],
                                }
                            ],
                        }
                        for c in candidates[1 : 1 + ALTERNATIVES]
                    ],
                )
            )
        return found

    def _relation_candidates(
        self,
        relation: str,
        ours: list[ObjectTypeRelationDefinition],
        target_type: str,
        ends: set[str],
    ) -> list[Candidate]:
        source_relation = self.source.model.relation_type(relation)
        cardinalities = {b.cardinality for b in ours}
        options: dict[tuple[str, str], str] = {}
        for item in self.target.model.objectTypeRelations:
            if item.relationTypeKey in self.target.containment:
                continue
            if item.fromObjectTypeKey == target_type and item.toObjectTypeKey in ends:
                options.setdefault((item.relationTypeKey, "outgoing"), item.cardinality)
            if item.toObjectTypeKey == target_type and item.fromObjectTypeKey in ends:
                options.setdefault((item.relationTypeKey, "incoming"), _reversed(item.cardinality))
        found = []
        for (key, direction), cardinality in options.items():
            theirs = self.target.model.relation_type(key)
            score, evidence = _likeness(
                relation,
                source_relation.name if source_relation else None,
                key,
                theirs.name if theirs else None,
                self.same_model,
            )
            if direction == "incoming" and score >= 10:
                score, evidence = 3.0, [{"kind": "sameKey"}]
            if cardinality in cardinalities:
                score += 0.5
                evidence = [*evidence, {"kind": "cardinality", "cardinality": cardinality}]
            if len(options) == 1:
                score += 0.5
                evidence = [*evidence, {"kind": "onlyRelation"}]
            found.append(Candidate(key, round(score, 3), evidence, direction))
        found.sort(key=lambda c: (-c.score, c.target, c.direction))
        return found

    # --- the whole ---

    def proposals(self) -> list[Proposal]:
        chosen: dict[str, str] = {}
        candidates: dict[str, list[Candidate]] = {}
        # Twice: the second pass knows the parents the first chose.
        for _ in range(2):
            for source_type in self.source.type_keys:
                found = self._type_candidates(source_type, chosen)
                candidates[source_type] = found
                if found and found[0].score >= THRESHOLD:
                    chosen[source_type] = found[0].target
                else:
                    chosen.pop(source_type, None)
        types = [
            self._type_proposal(s, candidates[s][0], candidates[s][1:], chosen)
            for s in self.source.type_keys
            if s in chosen
        ]
        relations = [
            r for p in types for r in self._relation_proposals(p.source_type, chosen, p.anchor)
        ]
        return types + relations


def _reversed(cardinality: str) -> str:
    return {"one-to-many": "many-to-one", "many-to-one": "one-to-many"}.get(
        cardinality, cardinality
    )


# --- the stored records (one statement) -------------------------------------------------------------

# A unique value in its text form, as a name is compared: text as it is, a number, a date or a
# boolean as its JSON form reads (0.11 Q2, D189).
_UNIQUE_TEXT = f"{value_json_sql('a')} #>> '{{}}'"

_SHARED = f"""
WITH source_values AS (
    SELECT o.object_type_key AS type_key, NULL::text AS attr, o.name AS value FROM objects o
    WHERE o.workspace_key = :source
    UNION
    SELECT o.object_type_key, a.attribute_type_key, {_UNIQUE_TEXT} FROM attribute_values a
    JOIN objects o ON o.id = a.object_id AND o.workspace_key = :source
    WHERE a.attribute_type_key = ANY(:source_unique)
),
target_values AS (
    SELECT o.object_type_key AS type_key, NULL::text AS attr, o.name AS value FROM objects o
    WHERE o.workspace_key = :target
    UNION
    SELECT o.object_type_key, a.attribute_type_key, {_UNIQUE_TEXT} FROM attribute_values a
    JOIN objects o ON o.id = a.object_id AND o.workspace_key = :target
    WHERE a.attribute_type_key = ANY(:target_unique)
)
SELECT s.type_key, t.type_key, count(DISTINCT s.value),
    coalesce(jsonb_agg(DISTINCT jsonb_build_array(s.attr, t.attr))
        FILTER (WHERE s.attr IS NOT NULL AND t.attr IS NOT NULL), '[]')
FROM source_values s JOIN target_values t ON t.value = s.value
GROUP BY s.type_key, t.type_key
UNION ALL
SELECT s.type_key, NULL, count(DISTINCT s.value), '[]' FROM source_values s GROUP BY s.type_key
"""


def shared_values(
    session: Session, source: Side, target: Side, source_workspace: str, target_workspace: str
) -> tuple[dict[tuple[str, str], int], dict[str, int], dict[tuple[str, str], set[tuple[str, str]]]]:
    """Per pair of types, the names and unique values the two workspaces' records share; per source
    type, the values it holds; and per pair of types, the pairs of unique attributes whose values
    they share. One statement in PostgreSQL (principle 6)."""
    stored: dict[tuple[str, str], int] = {}
    totals: dict[str, int] = {}
    keys: dict[tuple[str, str], set[tuple[str, str]]] = {}
    rows = session.execute(
        text(_SHARED),
        {
            "source": source_workspace,
            "target": target_workspace,
            "source_unique": [a.key for a in source.model.attributeTypes if source.unique(a.key)],
            "target_unique": [a.key for a in target.model.attributeTypes if target.unique(a.key)],
        },
    )
    for source_type, target_type, count, pairs in rows:
        if target_type is None:
            totals[source_type] = count
        else:
            stored[(source_type, target_type)] = count
            keys[(source_type, target_type)] = {(a, b) for a, b in pairs}
    return stored, totals, keys


# --- the job -------------------------------------------------------------------------------------


def submit_inference(
    session: Session,
    key: str,
    source_workspace_key: str,
    target_workspace_key: str,
    *,
    retention_days: int,
) -> Job:
    """Queue the mapping's inference over two workspaces running its two models, and stop its
    earlier one still running; commits."""
    mapping = load_mapping(session, key)
    releases = Releases(session)
    source = releases.of_workspace(source_workspace_key)
    target = releases.of_workspace(target_workspace_key)
    if (source.model_key, target.model_key) != (mapping.source_model_key, mapping.target_model_key):
        raise mismatch(mapping, source.model_key, target.model_key)
    job = replace_earlier_job(
        session,
        KIND,
        "mappingKey",
        mapping.key,
        lambda: start_job(
            session,
            kind=KIND,
            workspace_key=target_workspace_key,
            change_set_id=None,
            model_release_id=session.scalar(
                select(WorkspaceModel.model_release_id).where(
                    WorkspaceModel.workspace_key == target_workspace_key
                )
            ),
            parameters={
                "mappingKey": mapping.key,
                "mappingVersion": mapping.version,
                "sourceWorkspaceKey": source_workspace_key,
                "targetWorkspaceKey": target_workspace_key,
                "sourceReleaseId": mapping.definition["sourceReleaseId"],
                "targetReleaseId": mapping.definition["targetReleaseId"],
            },
            total=None,
            retention_days=retention_days,
            queued=True,
        ),
    )
    session.commit()
    return job


def proposal_id(mapping: ModelMapping, anchor: str) -> str:
    """A proposal's ID, the same in every inference of the mapping."""
    return str(uuid.uuid5(_NAMESPACE, f"{mapping.id}/{anchor}"))


def run_inference(session: Session, job: Job, *, check: Callable[[], None] = lambda: None) -> None:
    """Propose the job's mapping between its two releases, read with its two workspaces' records,
    and store the proposals in place of the earlier ones; the caller completes the job and commits.
    ``check`` renews the lease and stops on a cancel request between the phases."""
    parameters = job.parameters
    mapping = load_mapping(session, parameters["mappingKey"])
    releases = Releases(session)
    source = releases.side(parameters["sourceReleaseId"])
    target = releases.side(parameters["targetReleaseId"])
    assert source is not None and target is not None
    stored, totals, keys = shared_values(
        session, source, target, parameters["sourceWorkspaceKey"], parameters["targetWorkspaceKey"]
    )
    check()
    proposals = Inference(source, target, stored, totals, keys).proposals()
    check()
    ids = {p.anchor: proposal_id(mapping, p.anchor) for p in proposals}
    session.execute(
        delete(ModelMappingProposal).where(ModelMappingProposal.mapping_id == mapping.id)
    )
    session.flush()
    for position, proposal in enumerate(proposals):
        session.add(
            ModelMappingProposal(
                public_id=ids[proposal.anchor],
                mapping_id=mapping.id,
                inference_id=job.id,
                position=position,
                kind=proposal.kind,
                signature=proposal.signature(),
                body={
                    "anchor": proposal.anchor,
                    "sourceType": proposal.source_type,
                    "relation": proposal.relation,
                    "target": proposal.target,
                    "score": proposal.score,
                    "summary": proposal.summary,
                    "evidence": proposal.evidence,
                    "operations": proposal.operations,
                    "alternatives": proposal.alternatives,
                    "requires": [ids[a] for a in proposal.requires if a in ids],
                    "expected": proposal.expected,
                },
            )
        )
    warnings = []
    unproposed = [key for key in source.type_keys if f"type:{key}" not in ids]
    if unproposed:
        warnings.append(
            f"No type of the target is like {', '.join(unproposed)}: map them by hand or leave them out"
        )
    job.report = {
        **(job.report or {}),
        "mappingInference": {"proposals": len(proposals), "warnings": warnings},
    }


# --- reads ------------------------------------------------------------------------------------------


def latest_inference(session: Session, mapping: ModelMapping) -> Job | None:
    return session.scalar(
        select(Job)
        .where(Job.kind == KIND, job_parameter("mappingKey") == mapping.key)
        .order_by(Job.sequence_id.desc())
        .limit(1)
    )


def require_inference(session: Session, mapping: ModelMapping) -> Job:
    job = latest_inference(session, mapping)
    if job is None:
        raise api_error(
            404, "INFERENCE_NOT_FOUND", f"Model mapping '{mapping.key}' has no inference yet"
        )
    return job


def _require_completed(job: Job) -> None:
    if job.state != "completed":
        raise api_error(
            409,
            "INFERENCE_NOT_READY",
            f"The mapping's inference is {job.state}",
            {"state": job.state},
        )


def _rows(session: Session, mapping: ModelMapping) -> list[ModelMappingOperation]:
    return list(
        session.scalars(
            select(ModelMappingOperation)
            .where(ModelMappingOperation.mapping_id == mapping.id)
            .order_by(ModelMappingOperation.sequence)
        )
    )


def _type_state(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "target": entry.get("target"),
        "attributes": sorted(
            entry.get("attributes") or [], key=lambda item: item.get("source", "")
        ),
        "parent": entry.get("parent"),
        "match": entry.get("match"),
        "defaults": entry.get("defaults") or {},
    }


def status_of(
    body: dict[str, Any], kind: str, definition: dict[str, Any], undone: set[str], proposal: str
) -> str:
    entry = next(
        (e for e in definition.get("types") or [] if e.get("source") == body["sourceType"]), None
    )
    expected = body["expected"]
    if kind == "type":
        current = _type_state(entry) if entry else None
        wanted = _type_state({**expected, "defaults": {}}) if entry else None
    else:
        current = next(
            (
                r
                for r in (entry or {}).get("relations") or []
                if r.get("source") == body["relation"]
            ),
            None,
        )
        wanted = expected
    if current is None:
        return "rejected" if proposal in undone else "open"
    return "applied" if current == wanted else "held"


def statuses(
    session: Session, mapping: ModelMapping, rows: list[ModelMappingOperation] | None = None
) -> dict[str, str]:
    """Each stored proposal's status, read from the mapping as it is and its history."""
    rows = rows if rows is not None else _rows(session, mapping)
    applied = {
        (r.origin or {}).get("proposalId")
        for r in rows
        if (r.origin or {}).get("type") == "proposal" and r.undone_by_step is None
    }
    undone = {
        (r.origin or {}).get("proposalId")
        for r in rows
        if (r.origin or {}).get("type") == "proposal" and r.undone_by_step is not None
    }
    found = {}
    for public_id, kind, body in session.execute(
        select(
            ModelMappingProposal.public_id, ModelMappingProposal.kind, ModelMappingProposal.body
        ).where(ModelMappingProposal.mapping_id == mapping.id)
    ):
        found[public_id] = status_of(body, kind, mapping.definition, undone - applied, public_id)
    return found


def read_inference(session: Session, mapping: ModelMapping) -> dict[str, Any]:
    """``GET /model-mappings/{key}/inference``: the latest inference, its proposals' counts by status
    and its warnings."""
    job = require_inference(session, mapping)
    report = (job.report or {}).get(KIND) or {}
    counts = dict.fromkeys(STATUSES, 0)
    if job.state == "completed":
        for status in statuses(session, mapping).values():
            counts[status] += 1
    parameters = job.parameters
    return {
        "jobId": job.id,
        "state": "checking" if job.state in CANCELLABLE else job.state,
        "mappingVersion": parameters.get("mappingVersion"),
        "sourceWorkspaceKey": parameters.get("sourceWorkspaceKey"),
        "targetWorkspaceKey": parameters.get("targetWorkspaceKey"),
        "sourceReleaseId": parameters.get("sourceReleaseId"),
        "targetReleaseId": parameters.get("targetReleaseId"),
        "counts": counts,
        "warnings": report.get("warnings") or [],
        "error": job.error,
    }


def proposal_page(
    session: Session,
    mapping: ModelMapping,
    page: PageRequest,
    page_size: int,
    *,
    source_type: str | None,
) -> tuple[Page[ModelMappingProposal], dict[str, str]]:
    _require_completed(require_inference(session, mapping))
    statement = select(ModelMappingProposal).where(ModelMappingProposal.mapping_id == mapping.id)
    if source_type is not None:
        statement = statement.where(
            ModelMappingProposal.body["sourceType"].as_string() == source_type
        )
    found = paginate_statement(
        session,
        statement,
        keys=_KEYS,
        scope="mapping-proposals",
        filters={"mappingKey": mapping.key, "sourceType": source_type},
        page=page,
        page_size=page_size,
        message="Proposal list cursor is invalid",
    )
    return found, statuses(session, mapping)


# --- applying -------------------------------------------------------------------------------------


def apply_inference(
    session: Session,
    key: str,
    expected_version: int,
    proposals: list[str] | None,
    *,
    max_items: int,
) -> history.StepResult:
    """The proposals asked for (every open one by default), each one step of origin ``proposal``, in
    their order, all or none. Refused when the mapping was re-pointed since the inference: its
    proposals are about other releases (``INFERENCE_STALE``)."""
    mapping = load_mapping(session, key, for_update=True)
    job = require_inference(session, mapping)
    _require_completed(job)
    parameters = job.parameters
    if (parameters["sourceReleaseId"], parameters["targetReleaseId"]) != (
        mapping.definition["sourceReleaseId"],
        mapping.definition["targetReleaseId"],
    ):
        raise api_error(
            409,
            "INFERENCE_STALE",
            "The mapping names other releases than its inference read; propose again before applying",
            {
                "inferenceMappingVersion": parameters.get("mappingVersion"),
                "mappingVersion": mapping.version,
            },
        )
    stored = list(
        session.scalars(
            select(ModelMappingProposal)
            .where(ModelMappingProposal.mapping_id == mapping.id)
            .order_by(ModelMappingProposal.position)
        )
    )
    by_id = {p.public_id: p for p in stored}
    status = statuses(session, mapping)
    if proposals is None:
        wanted = [p for p in stored if status[p.public_id] == "open"]
        if not wanted:
            raise api_error(
                409, "NOTHING_TO_APPLY", "No proposal of the mapping's inference is open"
            )
    else:
        for proposal_id_ in proposals:
            if proposal_id_ not in by_id:
                raise api_error(
                    404,
                    "PROPOSAL_NOT_FOUND",
                    f"The mapping's inference has no proposal '{proposal_id_}'",
                    {"proposal": proposal_id_},
                )
            if status[proposal_id_] == "applied":
                raise api_error(
                    409,
                    "PROPOSAL_ALREADY_APPLIED",
                    f"Proposal '{proposal_id_}' is applied",
                    {"proposal": proposal_id_},
                )
        asked = set(proposals)
        wanted = [p for p in stored if p.public_id in asked]
    names = {p.public_id for p in wanted}
    for proposal in wanted:
        for requirement in proposal.body.get("requires") or []:
            if requirement not in names and status.get(requirement) not in ("applied", "held"):
                raise api_error(
                    422,
                    "PROPOSAL_REQUIREMENT_MISSING",
                    f"Proposal '{proposal.public_id}' needs proposal '{requirement}' applied first or with it",
                    {"proposal": proposal.public_id, "requirement": requirement},
                )
    steps = [
        (p.public_id, list(p.body.get("operations") or []), _origin_of(p, job)) for p in wanted
    ]
    return history.apply_steps(session, key, expected_version, steps, max_items, MAPPINGS)


def _origin_of(proposal: ModelMappingProposal, job: Job) -> Callable[..., dict[str, Any]]:
    def origin(_applied: list[Applied], _definition: dict[str, Any]) -> dict[str, Any]:
        return {
            "type": "proposal",
            "proposalId": proposal.public_id,
            "inferenceId": job.id,
            "kind": proposal.kind,
            "summary": proposal.body.get("summary"),
            "signature": proposal.signature,
        }

    return origin
