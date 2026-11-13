"""Proposals from findings (Product 0.10 A6, D89–D91, D96–D98): each pattern a batch of the
editor's own operation kinds, with the keys of what it adds generated from labels (A-D6), its
alternatives, and the anchor and signature that later inferences recognise it by (D92).

A key is given to a **role** of a proposal ("type", "list", "source", …). Proposing again reuses
the keys an earlier proposal of the same anchor gave its roles, so the same workbook asks for the
same elements and only what changed is applied (``compare.py``). In **extend** mode (D91) a sheet,
a column or a lookup is matched to what the draft's model already declares before anything is
added; columns of one workbook that share a header and a value type share one global attribute type
(D98). Names are English words where a pattern needs one of its own ("Has …", "Language",
"Translation"); every name is the administrator's to change in the editor.
"""

import copy
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol
from uuid import uuid4

from ...model.authoring.keys import key_from_label
from .facts import Column, Table, Workbook
from .patterns import DESCRIPTION_PATTERNS, LIST_PATTERNS, Finding, fold, shape_of

# The schema language that declares navigation groups (0.10 N1, D1).
# D91's thresholds.
MATCH_SHARE = 0.5
FIT_SHARE = 0.95
# D97: words a joined multi-valued column's header starts with, dropped from the set's name.
OTHER_WORDS = ("other", "more", "additional")
# What a note under a list's header says (0.10 A8a, D119), as the list type's description.
NOTE_DESCRIPTIONS = {"many": "Multiple answers: a record may refer to several", "one": "One answer: a record refers to one"}
# Words ending a code column's header, dropped from its list's name.
CODE_WORDS = ("code", "codes", "id", "no", "nr", "number", "key")
# D111 (0.10 A7): a sheet maps to an existing type when this share of the type's attribute and
# relation names, and at least this many, are headers of the sheet.
FIELDS_SHARE = 0.5
FIELDS_LEAST = 2
# Values listed in the evidence of missing IDs and drift (D112).
DIFFERENCES_LISTED = 50


class Stored(Protocol):
    """What a workbook's columns hold that the workspace's records do not (0.10 A7, D112): asked of
    the staged cells and the records by set statements (``run.py``)."""

    def missing(self, sheet: str, column: str, type_key: str, attribute: str | None) -> list[dict[str, Any]]:
        """The column's values (placeholders aside) that no record of the type holds, by name or by
        the attribute, with their rows."""
        ...

    def drift(self, sheet: str, code: str, name: str, type_key: str, attribute: str) -> list[dict[str, Any]]:
        """Each code a record of the type holds whose names in the file differ from the record's."""
        ...

    def holds_records(self, type_key: str) -> bool: ...


def singular(label: str) -> str:
    words = label.strip().split()
    if not words:
        return label
    last = words[-1]
    lower = last.lower()
    if lower.endswith("ies") and len(last) > 4:
        last = last[:-3] + "y"
    elif lower.endswith(("ches", "shes", "sses", "xes", "uses")):
        last = last[:-2]
    elif lower.endswith("s") and not lower.endswith(("ss", "us", "is")) and len(last) > 3:
        last = last[:-1]
    return " ".join([*words[:-1], last])


def plural(label: str) -> str:
    words = label.strip().split()
    if not words:
        return label
    last = words[-1]
    lower = last.lower()
    if lower.endswith("y") and len(last) > 1 and lower[-2] not in "aeiou":
        last = last[:-1] + "ies"
    elif lower.endswith(("s", "x", "ch", "sh")):
        last = last + "es"
    else:
        last = last + "s"
    return " ".join([*words[:-1], last])


def _capital(label: str) -> str:
    return label[:1].upper() + label[1:] if label else label


def readable(label: str) -> str:
    """A header or sheet name as words (D103): underscores and joined capitals split
    ("StopName_Code" → "Stop Name Code", "RBStopType" → "RB Stop Type"), and a
    header written in capitals with more than one word in sentence case ("IS_INTERNAL" → "Is internal")."""
    text = re.sub(r"[_]+", " ", label)
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    letters = re.sub(r"[^A-Za-z]", "", text)
    if letters and letters.isupper() and " " in text:
        text = text.capitalize()
    return text or label


def _type_name(table: Table, key: Column) -> str:
    """D103: a row type's name from its key column's header when it ends in a code word, without it
    ("Type Code" → Type), else from the sheet's name."""
    words = readable(key.header).split()
    if len(words) > 1 and words[-1].lower() in CODE_WORDS:
        return _capital(singular(" ".join(words[:-1])))
    return _capital(singular(readable(table.name)))


@dataclass
class Proposal:
    pattern: str
    sheet: str | None
    columns: list[str]
    summary: str
    evidence: dict[str, Any]
    operations: list[dict[str, Any]]
    anchor: str
    signature: str
    keys: dict[str, str] = field(default_factory=dict)
    alternatives: list[dict[str, Any]] = field(default_factory=list)
    requires: list[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid4()))
    state: str = "open"
    # The elements a proposal creates and those it names, for requirements and ownership.
    created: set[str] = field(default_factory=set)
    # Column header -> the binding kind the proposal gives it, by source id (disagreements, D92).
    binds: dict[str, tuple[str, str]] = field(default_factory=dict)

    def body(self) -> dict[str, Any]:
        return {
            "pattern": self.pattern,
            "sheet": self.sheet,
            "columns": self.columns,
            "summary": self.summary,
            "evidence": self.evidence,
            "operations": self.operations,
            "alternatives": self.alternatives,
            "requires": self.requires,
            "anchor": self.anchor,
            "signature": self.signature,
            "keys": self.keys,
            "state": self.state,
            "created": sorted(self.created),
            "binds": {column: list(value) for column, value in self.binds.items()},
        }


@dataclass
class RowType:
    """What loads a sheet's rows: its type, source, key attribute and application."""

    type_key: str
    source: str
    key_attribute: str | None
    application: str
    name: str
    released: bool = False


class Builder:
    """Builds the proposals of one inference against the draft's model and profile."""

    def __init__(
        self,
        model: dict[str, Any],
        profile: dict[str, Any] | None,
        workbook: Workbook,
        *,
        mode: str,
        file_name: str,
        application_key: str | None,
        application_name: str | None,
        reuse: dict[str, dict[str, str]],
        released: Callable[[str], bool],
        identifiers: dict[tuple[str, str], dict[str, str]] | None = None,
        stored: Stored | None = None,
    ) -> None:
        self.model = model
        self.profile = profile or {}
        self.workbook = workbook
        self.mode = mode
        self.file_name = file_name
        self.application_key = application_key
        self.application_name = application_name
        self.reuse = reuse
        self.released = released
        # D96: ID columns whose values an existing type holds, with the parent they stand under.
        self.identifiers = identifiers or {}
        # D112: what the columns hold that the workspace's records do not (extend mode).
        self.stored = stored if mode == "extend" else None
        # Warnings the proposals raise (a list to be defined, an unknown type word, what differs).
        self.warnings: list[str] = []
        # A model description's type, and its lists by target (0.10 A7).
        self.described: RowType | None = None
        self.described_lists: dict[str, tuple[str, str]] = {}
        # D112's sentence on a lookup's missing values, by (sheet, column), for the column's later
        # proposals to repeat.
        self.missing_sentences: dict[tuple[str, str], str] = {}
        self.taken: dict[str, set[str]] = {
            "applications": {a.get("key") for a in model.get("applications") or []},
            "objectTypes": {t.get("key") for t in model.get("objectTypes") or []},
            "attributeTypes": {a.get("key") for a in model.get("attributeTypes") or []},
            "relations": {
                k
                for r in model.get("relationTypes") or []
                for k in (r.get("key"), r.get("reverseKey"))
                if k
            },
            "sources": {s.get("id") for s in self.profile.get("sources") or []},
            "valueMaps": set((self.profile.get("valueMaps") or {}).keys()),
            "groups": {
                g.get("key")
                for a in model.get("applications") or []
                for g in ((a.get("navigation") or {}).get("groups") or [])
            },
        }
        self.rows: dict[str, RowType] = {}
        self.attributes: dict[tuple[str, str, bool], list[tuple[str, tuple[int, int], Proposal | None]]] = {}
        self.list_types: dict[int, str] = {}
        self.proposals: list[Proposal] = []
        self._attached: set[tuple[str, str]] = set()
        self.app: str | None = None
        self.tables = {t.name: t for t in workbook.sheets}
        # Row types given a parent by a proposal: one parent each (D99, found on a sheet with three
        # repeated columns, each setting the parent anew and the last one winning).
        self.contained: set[str] = set()
        # The type and source whose name a column holds, by (sheet, column number), for translations
        # found by their values (D100).
        self.named: dict[tuple[str, int], RowType] = {}
        # The language list and the translation type, created once per inference: (proposal id,
        # language, translation).
        self.translation_types: tuple[str, str, str] | None = None
        # Each list's proposal by its finding, for a run's alternative (0.10 A8c, D143).
        self.block_proposals: dict[int, Proposal] = {}

    # --- keys -------------------------------------------------------------------------------

    def key(self, proposal: Proposal, role: str, collection: str, label: str) -> str:
        """The key of ``role``: the one an earlier proposal of the same anchor gave it, or one
        generated from ``label`` that nothing holds."""
        earlier = self.reuse.get(proposal.anchor, {}).get(role)
        if earlier is not None:
            key = earlier
        else:
            key = key_from_label(label, self.taken[collection])
        self.taken[collection].add(key)
        proposal.keys[role] = key
        return key

    # --- the model as it is -----------------------------------------------------------------

    def _type(self, key: str) -> dict[str, Any] | None:
        return next((t for t in self.model.get("objectTypes") or [] if t.get("key") == key), None)

    def _attribute_type(self, key: str) -> dict[str, Any] | None:
        return next((a for a in self.model.get("attributeTypes") or [] if a.get("key") == key), None)

    def _binds(self, type_key: str, attribute_key: str) -> bool:
        found = self._type(type_key)
        return bool(found) and any(b.get("attributeTypeKey") == attribute_key for b in found.get("attributes") or [])

    def _application_of(self, type_key: str) -> str | None:
        return next(
            (a["key"] for a in self.model.get("applications") or [] if type_key in (a.get("objectTypeKeys") or [])),
            None,
        )

    def _relation_between(self, source: str, target: str) -> str | None:
        return next(
            (
                r["relationTypeKey"]
                for r in self.model.get("objectTypeRelations") or []
                if r.get("fromObjectTypeKey") == source and r.get("toObjectTypeKey") == target
                and not self._containment(r["relationTypeKey"])
            ),
            None,
        )

    def _containment(self, relation_key: str) -> bool:
        relation = next((r for r in self.model.get("relationTypes") or [] if r.get("key") == relation_key), None)
        return bool(relation and (relation.get("features") or {}).get("parentOf"))

    @staticmethod
    def _fits(column: Column, value_type: str | None) -> bool:
        if value_type in (None, "text", "longText"):
            return True
        return column.value_types.get(value_type, 0) >= FIT_SHARE * max(column.filled, 1)

    # --- extend mode (D91) --------------------------------------------------------------------

    def matched_type(self, table: Table, key: Column) -> str | None:
        if self.mode != "extend":
            return None
        overlaps = [
            o for o in key.overlaps if o.get("objectTypeKey") and o.get("share", 0) >= MATCH_SHARE and self._type(o["objectTypeKey"])
        ]
        if overlaps:
            return max(overlaps, key=lambda o: o["share"])["objectTypeKey"]
        sheet = fold(table.name)
        for item in self.model.get("objectTypes") or []:
            if sheet in (fold(item.get("name") or ""), fold(item.get("pluralName") or "")):
                return item["key"]
        return self.described_by({fold(c.header) for c in table.columns})

    def fields_of(self, type_key: str) -> set[str]:
        """A type's attribute names and the names of the relations it holds, folded (D111)."""
        found = self._type(type_key) or {}
        names = {fold((self._attribute_type(b.get("attributeTypeKey")) or {}).get("name") or "") for b in found.get("attributes") or []}
        relations = {r.get("key"): r for r in self.model.get("relationTypes") or []}
        for allowed in self.model.get("objectTypeRelations") or []:
            relation = relations.get(allowed.get("relationTypeKey")) or {}
            if allowed.get("fromObjectTypeKey") == type_key and not (relation.get("features") or {}).get("parentOf"):
                names.add(fold(relation.get("name") or ""))
        return names - {""}

    def described_by(self, headers: set[str]) -> str | None:
        """D111 (a): the type at least half of whose attribute and relation names (two at least) are
        among ``headers``; the best share first."""
        if self.mode != "extend":
            return None
        best: tuple[float, str] | None = None
        for item in self.model.get("objectTypes") or []:
            names = self.fields_of(item["key"])
            if len(names) < FIELDS_LEAST:
                continue
            share = len(names & headers) / len(names)
            if len(names & headers) >= FIELDS_LEAST and share >= FIELDS_SHARE and (best is None or share > best[0]):
                best = (share, item["key"])
        return best[1] if best else None

    def existing_list(self, name: str) -> str | None:
        """D111 (b): the existing type a list proposed under ``name`` is, by its name or plural."""
        if self.mode != "extend":
            return None
        wanted = fold(name)
        for item in self.model.get("objectTypes") or []:
            if wanted in (fold(item.get("name") or ""), fold(item.get("pluralName") or "")):
                return item["key"]
        return None

    def matched_code(self, column: Column) -> tuple[str, str] | None:
        """D111 (c): the existing type and unique attribute holding at least half the column's
        values."""
        if self.mode != "extend":
            return None
        overlaps = [
            o for o in column.overlaps
            if o.get("objectTypeKey") and o.get("attributeTypeKey") and o.get("share", 0) >= MATCH_SHARE and self._type(o["objectTypeKey"])
        ]
        if not overlaps:
            return None
        best = max(overlaps, key=lambda o: o["share"])
        return best["objectTypeKey"], best["attributeTypeKey"]

    def matched_lookup(self, column: Column) -> str | None:
        if self.mode != "extend":
            return None
        overlaps = [
            o
            for o in column.overlaps
            if o.get("objectTypeKey") and o.get("field") == "name" and o.get("share", 0) >= MATCH_SHARE and self._type(o["objectTypeKey"])
        ]
        return max(overlaps, key=lambda o: o["share"])["objectTypeKey"] if overlaps else None

    def _existing_attribute(self, type_key: str | None, column: Column, value_type: str) -> str | None:
        """D91: an attribute the type binds named as the column whose type the cells fit, else a
        global attribute type of that name and fitting type."""
        if self.mode != "extend":
            return None
        header = fold(column.header)
        candidates = [a for a in self.model.get("attributeTypes") or [] if fold(a.get("name") or "") == header]
        candidates = [a for a in candidates if self._fits(column, a.get("valueType")) and (a.get("valueType") or "text") in _compatible(value_type)]
        bound = [a for a in candidates if type_key and self._binds(type_key, a["key"])]
        return (bound or candidates or [{}])[0].get("key")

    # --- attributes (D98) ----------------------------------------------------------------------

    def attribute(
        self, proposal: Proposal, role: str, table: Table, column: Column, type_key: str, *, unique: bool = False, value_type: str | None = None
    ) -> tuple[str, list[dict[str, Any]]]:
        """The attribute type a column fills on ``type_key`` and the operations it needs: an
        existing one (D91), one another column of the workbook shares (D98), or a new one."""
        value_type = value_type or column.value_type()
        operations: list[dict[str, Any]] = []
        key = self._existing_attribute(type_key, column, value_type)
        if key is None:
            key = self._shared(table, column, value_type, unique)
        if key is None:
            key = self.key(proposal, role, "attributeTypes", readable(column.header))
            features: dict[str, Any] = {"unique": True} if unique else {}
            operations.append(
                {"kind": "addAttributeType", "key": key, "name": readable(column.header), "valueType": value_type, "features": features}
            )
            self.attributes.setdefault((fold(column.header), value_type, unique), []).append(
                (key, (table.index, column.number), proposal)
            )
        else:
            proposal.keys[role] = key
        if not self._binds(type_key, key) and not self._attached_here(type_key, key):
            operations.append({"kind": "attachAttribute", "objectType": type_key, "attributeType": key})
            self._attached.add((type_key, key))
        return key, operations

    def _attached_here(self, type_key: str, key: str) -> bool:
        return (type_key, key) in self._attached

    def _shared(self, table: Table, column: Column, value_type: str, unique: bool) -> str | None:
        for key, at, _ in self.attributes.get((fold(column.header), value_type, unique), []):
            if at[0] == table.index:
                continue
            if unique and self.workbook.common(at, (table.index, column.number)):
                continue
            return key
        return None

    # --- building ------------------------------------------------------------------------------

    def build(self, findings: list[Finding]) -> list[Proposal]:
        self.app = self._application()
        for finding in findings:
            if finding.pattern == "keyColumn":
                self._add(self._key_column(finding))
        by_id = {id(f): f for f in findings}
        for finding in findings:
            if finding.pattern == "keyColumn":
                continue
            method = getattr(self, f"_{finding.pattern}", None)
            if method is None:
                continue
            if finding.sheet not in self.rows and finding.pattern not in ("translationsByRow", "navigationGroup", "listBlock", *DESCRIPTION_PATTERNS):
                continue
            proposal = method(finding, by_id) if finding.pattern == "navigationGroup" else method(finding)
            if proposal is not None:
                self._add(proposal, finding)
        # D143 (0.10 A8c): a run of lists of one shape may be read as one list under their headers.
        runs = {id(f.detail["run"]): f.detail["run"] for f in findings if f.pattern == "listBlock" and f.detail.get("run")}
        for run in runs.values():
            self._one_list(run)
        # A new application is proposed for what goes into it: alone, it would be an application
        # without types, which a model refuses (found on a workbook whose every sheet is laid out
        # for reading).
        if [p.pattern for p in self.proposals] == ["newApplication"]:
            self.proposals = []
        # A sheet read by its main block (facts.main_block) loads every source from that block only.
        for proposal in self.proposals:
            for operation in proposal.operations:
                block = getattr(self.tables.get(operation.get("sheet")), "block", None)
                if operation.get("kind") == "addSource" and block:
                    operation["block"] = dict(block)
        return self.proposals

    def list_proposal(self, finding: Finding, application: str | None, translations: tuple[str, str] | None) -> Proposal | None:
        """One list's proposal on its own (0.10 A8b, D128): new types go into ``application``, and
        translations reuse the draft's language list and translation type when it has them."""
        self.app = application
        if translations is not None:
            self.translation_types = ("", *translations)
        proposal = self._listBlock(finding)
        if proposal is not None:
            proposal.requires = [r for r in proposal.requires if r]
        return proposal

    def _add(self, proposal: Proposal | None, finding: Finding | None = None) -> None:
        if proposal is None:
            return
        if finding is not None and finding.pattern == "listBlock":
            self.block_proposals[id(finding)] = proposal
        if finding is not None and finding.pattern in LIST_PATTERNS and "list" in proposal.keys:
            self.list_types[id(finding)] = proposal.keys["list"]
        self.proposals.append(proposal)

    def _application(self) -> str:
        """The application new types go into: a new one (its proposal first), the one named, or
        in extend mode the application most matched types are in (D91)."""
        if self.mode == "newApplication":
            name = self.application_name or _capital(re.sub(r"[_\-]+", " ", self.file_name.rsplit(".", 1)[0]).strip()) or "Workbook"
            proposal = self._new("newApplication", None, [], f"A new application, {name}, named after the file.", {"name": name}, "newApplication")
            key = self.application_key or self.key(proposal, "application", "applications", name)
            if self.application_key:
                proposal.keys["application"] = key
            proposal.operations = [{"kind": "addApplication", "key": key, "name": name}]
            self.proposals.append(proposal)
            return key
        if self.application_key:
            return self.application_key
        counts: dict[str, int] = {}
        for table in self.workbook.sheets:
            key = next((c for c in table.columns if c.candidate_key), None)
            matched = self.matched_type(table, key) if key else None
            app = self._application_of(matched) if matched else None
            if app:
                counts[app] = counts.get(app, 0) + 1
        if counts:
            return max(counts, key=counts.get)
        return (self.model.get("applications") or [{}])[0].get("key")

    def _new(self, pattern: str, sheet: str | None, columns: list[str], summary: str, evidence: dict[str, Any], anchor: str) -> Proposal:
        return Proposal(
            pattern=pattern,
            sheet=sheet,
            columns=columns,
            summary=summary,
            evidence=evidence,
            operations=[],
            anchor=anchor,
            signature="|".join([pattern, sheet or "", *columns]),
        )

    def _start(self, finding: Finding, summary: str, anchor_column: str | None = None) -> tuple[Proposal, Table, list[Column]]:
        table = self.tables[finding.sheet]
        by_number = {c.number: c for c in table.columns}
        columns = [by_number[n] for n in finding.columns]
        headers = [c.header for c in columns]
        anchor = "|".join(filter(None, [finding.pattern, finding.sheet, anchor_column]))
        return self._new(finding.pattern, finding.sheet, headers, summary, finding.evidence, anchor), table, columns

    def _map(self, proposal: Proposal, source: str, column: str, binding: dict[str, Any]) -> dict[str, Any]:
        proposal.binds[column] = (source, next(k for k in ("field", "attributeTypeKey", "parent", "relation", "relatedRecord") if k in binding))
        return {"kind": "mapColumn", "source": source, "column": column, "binding": binding}

    def _list_type(self, proposal: Proposal, name: str) -> tuple[str, list[dict[str, Any]]]:
        key = self.key(proposal, "list", "objectTypes", name)
        return key, [{"kind": "addObjectType", "applicationKey": self.app, "key": key, "name": name, "pluralName": plural(name), "parent": None}]

    def _relation(self, proposal: Proposal, row: RowType, target: str, target_name: str, cardinality: str, role: str = "relation") -> tuple[str, list[dict[str, Any]]]:
        existing = self._relation_between(row.type_key, target)
        if existing is not None:
            proposal.keys[role] = existing
            return existing, []
        name = f"Has {target_name.lower()}"
        key = self.key(proposal, role, "relations", f"{row.name} {name}")
        reverse = self.key(proposal, f"{role}Reverse", "relations", f"{target_name} of {row.name}")
        return key, [
            {"kind": "addRelationType", "key": key, "reverseKey": reverse, "name": name, "reverseName": f"{target_name} of"},
            {"kind": "allowRelation", "relationType": key, "from": row.type_key, "to": target, "cardinality": cardinality},
        ]

    # --- the patterns ----------------------------------------------------------------------------

    def _key_column(self, finding: Finding) -> Proposal:
        table = self.tables[finding.sheet]
        by_number = {c.number: c for c in table.columns}
        key_column = by_number[finding.columns[0]]
        name_column = by_number[finding.columns[1]] if len(finding.columns) > 1 else None
        type_name = _type_name(table, key_column)
        summary = (
            f"Each row of {table.name} is one {type_name}: {key_column.header} is filled and different on all "
            f"{key_column.rows} rows"
            + (f", and {name_column.header} is its name." if name_column else ".")
        )
        proposal, _, _ = self._start(finding, summary)
        operations: list[dict[str, Any]] = []
        matched = self.matched_type(table, key_column)
        if matched is not None:
            type_key = matched
            proposal.keys["type"] = type_key
            app = self._application_of(type_key) or self.app
        else:
            type_key = self.key(proposal, "type", "objectTypes", type_name)
            app = self.app
            plural_name = plural(type_name)
            operations.append(
                {"kind": "addObjectType", "applicationKey": app, "key": type_key, "name": type_name, "pluralName": plural_name, "parent": None}
            )
        attribute, attach = self.attribute(proposal, "keyAttribute", table, key_column, type_key, unique=True, value_type="text" if key_column.textual else key_column.value_type())
        operations += attach
        source = self.key(proposal, "source", "sources", f"{table.name} {type_key}")
        operations.append(
            {"kind": "addSource", "id": source, "sheet": table.name, "objectType": type_key, "applicationKey": app, "key": {"attributeTypeKey": attribute}}
        )
        operations.append(self._map(proposal, source, key_column.header, {"attributeTypeKey": attribute}))
        if name_column is not None:
            operations.append(self._map(proposal, source, name_column.header, {"field": "name"}))
        proposal.operations = operations
        found_type = self._type(type_key)
        self.rows[table.name] = RowType(
            type_key,
            source,
            attribute,
            app,
            (found_type or {}).get("name") or type_name,
            released=self.released(f"objectType:{type_key}"),
        )
        if name_column is not None:
            self.named[(table.name, name_column.number)] = self.rows[table.name]
        return proposal

    def _repeatedParent(self, finding: Finding) -> Proposal:
        table = self.tables[finding.sheet]
        by_number = {c.number: c for c in table.columns}
        group = by_number[finding.detail["group"]]
        dependents = [by_number[n] for n in finding.detail["dependents"]]
        key_column = by_number.get(finding.detail["key"]) if finding.detail["key"] else None
        row = self.rows[table.name]
        name = _capital(singular(readable(group.header)))
        held = ", ".join(c.header for c in dependents)
        summary = (
            f"{group.header} repeats over the rows in {group.distinct} groups, and {held} "
            f"{'is' if len(dependents) == 1 else 'are'} the same within every group: a parent type {name} holding them."
        )
        proposal, _, _ = self._start(finding, summary, group.header)
        parent = self.key(proposal, "type", "objectTypes", name)
        operations: list[dict[str, Any]] = [
            {"kind": "addObjectType", "applicationKey": self.app, "key": parent, "name": name, "pluralName": plural(name), "parent": None}
        ]
        attributes: dict[int, str] = {}
        if key_column is not None:
            for column in dependents:
                attribute, more = self.attribute(
                    proposal, f"attribute:{column.header}", table, column, parent, unique=column is key_column
                )
                attributes[column.number] = attribute
                operations += more
        # One parent per type (D99): a further repeated column is a list the row refers to.
        contained = not row.released and row.type_key not in self.contained
        if contained:
            self.contained.add(row.type_key)
            relation = self.key(proposal, "containment", "relations", f"{parent} contains")
            reverse = self.key(proposal, "containmentReverse", "relations", f"{row.type_key} in")
            operations.append(
                {
                    "kind": "setContainment",
                    "objectType": row.type_key,
                    "parent": _parent_of(parent, relation, reverse, optional=group.filled < table.rows),
                }
            )
        else:
            relation, more = self._relation(proposal, row, parent, name, "many-to-one")
            operations += more
        if key_column is not None:
            source = self.key(proposal, "source", "sources", f"{table.name} {parent}")
            operations.append(
                {"kind": "addSource", "id": source, "sheet": table.name, "objectType": parent, "applicationKey": self.app, "key": {"attributeTypeKey": attributes[key_column.number]}}
            )
            self.named[(table.name, group.number)] = RowType(parent, source, attributes[key_column.number], self.app, name)
            operations.append(self._map(proposal, source, group.header, {"field": "name"}))
            for column in dependents:
                operations.append(self._map(proposal, source, column.header, {"attributeTypeKey": attributes[column.number]}))
        match: dict[str, Any] = {"objectTypeKey": parent, "matchBy": {"field": "name"}}
        if key_column is None:
            match["missing"] = "create"
        if contained:
            operations.append(self._map(proposal, row.source, group.header, {"parent": match}))
        else:
            operations.append(self._map(proposal, row.source, group.header, {"relation": {"relationTypeKey": relation, **match}}))
        proposal.operations = operations
        if contained:
            alternative_relation = self.key(proposal, "altRelation", "relations", f"{row.name} has {name}")
            alternative_reverse = self.key(proposal, "altRelationReverse", "relations", f"{name} of {row.name}")
            proposal.alternatives = [
                {
                    "label": f"Make {name} a list {row.name} refers to, not its parent",
                    "operations": [
                        {"kind": "setContainment", "objectType": row.type_key, "parent": None},
                        {"kind": "addRelationType", "key": alternative_relation, "reverseKey": alternative_reverse, "name": f"Has {name.lower()}", "reverseName": f"{name} of"},
                        {"kind": "allowRelation", "relationType": alternative_relation, "from": row.type_key, "to": parent, "cardinality": "many-to-one"},
                        {"kind": "mapColumn", "source": row.source, "column": group.header, "binding": {"relation": {"relationTypeKey": alternative_relation, "objectTypeKey": parent, "matchBy": {"field": "name"}}}},
                    ],
                }
            ]
        return proposal

    def _codeAndName(self, finding: Finding) -> Proposal:
        table = self.tables[finding.sheet]
        by_number = {c.number: c for c in table.columns}
        code, name_column = by_number[finding.detail["code"]], by_number[finding.detail["name"]]
        row = self.rows[table.name]
        words = readable(code.header).split()
        while words and words[-1].lower() in CODE_WORDS:
            words.pop()
        name = _capital(singular(" ".join(words) or readable(name_column.header)))
        matched = self.matched_code(code)
        existing = matched[0] if matched else self.existing_list(name)
        if matched:
            return self._stored_pair(finding, table, code, name_column, row, matched[0], matched[1])
        summary = (
            f"{code.header} and {name_column.header} vary together ({code.distinct} codes, {name_column.distinct} names): "
            f"a list {name} with its code, each {row.name} referring to one."
        )
        proposal, _, _ = self._start(finding, summary, code.header)
        if existing:
            target, operations = existing, []
            proposal.keys["list"] = existing
            name = (self._type(existing) or {}).get("name") or name
        else:
            target, operations = self._list_type(proposal, name)
        attribute, more = self.attribute(proposal, "codeAttribute", table, code, target, unique=True, value_type="text")
        operations += more
        relation, more = self._relation(proposal, row, target, name, "many-to-one")
        operations += more
        source = self.key(proposal, "source", "sources", f"{table.name} {target}")
        operations.append(
            {"kind": "addSource", "id": source, "sheet": table.name, "objectType": target, "applicationKey": self.app, "key": {"attributeTypeKey": attribute}}
        )
        operations.append(self._map(proposal, source, code.header, {"attributeTypeKey": attribute}))
        operations.append(self._map(proposal, source, name_column.header, {"field": "name"}))
        operations.append(
            self._map(proposal, row.source, code.header, {"relation": {"relationTypeKey": relation, "objectTypeKey": target, "matchBy": {"attributeTypeKey": attribute}}})
        )
        self.named[(table.name, name_column.number)] = RowType(target, source, attribute, self.app, name)
        # The name column is bound twice on one sheet only for the list's own source.
        proposal.binds[name_column.header] = (source, "field")
        proposal.binds[code.header] = (row.source, "relation")
        proposal.operations = operations
        code_text = self.key(proposal, "altCode", "attributeTypes", code.header)
        name_text = self.key(proposal, "altName", "attributeTypes", name_column.header)
        proposal.alternatives = [
            {
                "label": f"Read {code.header} and {name_column.header} as two text attributes of {row.name} instead",
                "operations": [
                    {"kind": "addAttributeType", "key": code_text, "name": code.header, "valueType": "text", "features": {}},
                    {"kind": "attachAttribute", "objectType": row.type_key, "attributeType": code_text},
                    {"kind": "addAttributeType", "key": name_text, "name": name_column.header, "valueType": "text", "features": {}},
                    {"kind": "attachAttribute", "objectType": row.type_key, "attributeType": name_text},
                    {"kind": "mapColumn", "source": row.source, "column": code.header, "binding": {"attributeTypeKey": code_text}},
                    {"kind": "mapColumn", "source": row.source, "column": name_column.header, "binding": {"attributeTypeKey": name_text}},
                    {"kind": "removeSource", "source": source},
                    *([] if existing else [{"kind": "removeObjectType", "objectType": target}]),
                ],
            }
        ]
        return proposal

    def _stored_pair(
        self, finding: Finding, table: Table, code: Column, name_column: Column, row: RowType, target: str, attribute: str
    ) -> Proposal:
        """D111 (c), D112: a code and name pair whose codes are a stored list's: each row relates to
        the record of its code; the stored names stand, and where the file names a code otherwise
        that is drift, reported, with loading the file's names as the alternative."""
        name = (self._type(target) or {}).get("name") or target
        attribute_name = (self._attribute_type(attribute) or {}).get("name") or attribute
        proposal, _, _ = self._start(finding, "", code.header)
        proposal.keys["list"] = target
        relation, operations = self._relation(proposal, row, target, name, "many-to-one")
        operations.append(
            self._map(proposal, row.source, code.header, {"relation": {"relationTypeKey": relation, "objectTypeKey": target, "matchBy": {"attributeTypeKey": attribute}}})
        )
        proposal.binds[code.header] = (row.source, "relation")
        proposal.operations = operations
        drift = self.stored.drift(table.name, code.header, name_column.header, target, attribute) if self.stored else []
        missing = self.stored.missing(table.name, code.header, target, attribute) if self.stored else []
        proposal.evidence = {
            **finding.evidence,
            "acrossFiles": True,
            "drift": drift[:DIFFERENCES_LISTED],
            "driftCodes": len(drift),
            "missing": missing[:DIFFERENCES_LISTED],
            "missingValues": len(missing),
        }
        proposal.summary = (
            f"{code.header} holds the {attribute_name} of the stored {name} records: each {row.name} refers to the one of its code, "
            f"and {name_column.header} is left unread, since the stored names stand."
        )
        if drift:
            listed = "; ".join(
                f"{d['code']} is {d['stored']}, here {' and '.join(n['value'] for n in d['names'] if n['value'] != d['stored'])}" for d in drift[:5]
            )
            proposal.summary += f" {len(drift)} codes are named otherwise in this file ({listed})."
            self.warnings.append(f"{name_column.header} of sheet '{table.name}' names {len(drift)} {name} codes otherwise than the stored records: {listed}")
        if missing:
            listed = ", ".join(f"{m['value']} ({m['rows']})" for m in missing[:5])
            proposal.summary += f" {len(missing)} codes are not stored yet ({listed}): their rows are refused until they are."
            self.warnings.append(f"{code.header} of sheet '{table.name}' names {len(missing)} {name} codes the stored records lack: {listed}")
        source = self.key(proposal, "altSource", "sources", f"{table.name} {target}")
        proposal.alternatives = [
            {
                "label": f"Load the names in {name_column.header} onto the stored {name} records (renaming them in the change set)",
                "operations": [
                    {"kind": "addSource", "id": source, "sheet": table.name, "objectType": target, "applicationKey": self._application_of(target) or self.app, "key": {"attributeTypeKey": attribute}},
                    {"kind": "mapColumn", "source": source, "column": code.header, "binding": {"attributeTypeKey": attribute}},
                    {"kind": "mapColumn", "source": source, "column": name_column.header, "binding": {"field": "name"}},
                ],
            }
        ]
        return proposal

    def _nameDrift(self, finding: Finding) -> Proposal | None:
        table = self.tables[finding.sheet]
        by_number = {c.number: c for c in table.columns}
        code, name_column = (by_number[n] for n in finding.columns)
        pair = next((p for p in self.proposals if p.pattern == "codeAndName" and p.sheet == table.name and p.columns[0] == code.header), None)
        # A pair read onto a stored list loads no names of its own, so its names map nothing (D112).
        if pair is None or "source" not in pair.keys:
            return None
        entries: dict[str, str] = {}
        for item in finding.detail["drift"]:
            names = item["names"]
            for other in names[1:]:
                entries[other["value"]] = names[0]["value"]
        described = "; ".join(f"{k} → {v}" for k, v in entries.items())
        summary = (
            f"{len(finding.detail['drift'])} codes of {code.header} carry more than one {name_column.header}: "
            f"map {described}, the more frequent name of each code, so every code loads one name."
        )
        proposal, _, _ = self._start(finding, summary, code.header)
        name = self.key(proposal, "valueMap", "valueMaps", f"{name_column.header} names")
        source = pair.keys["source"]
        proposal.operations = [{"kind": "setValueMap", "name": name, "entries": entries, "source": source, "column": name_column.header}]
        proposal.alternatives = [
            {
                "label": "Only warn: rows with a less frequent name are refused",
                "operations": [{"kind": "setValueMap", "name": name, "entries": None}],
            }
        ]
        return proposal

    def _flagColumns(self, finding: Finding) -> Proposal:
        table = self.tables[finding.sheet]
        by_number = {c.number: c for c in table.columns}
        flags = [by_number[n] for n in finding.detail["flags"]]
        joined = by_number.get(finding.detail["joined"]) if finding.detail["joined"] else None
        row = self.rows[table.name]
        if joined is not None:
            words = joined.header.split()
            if words and words[0].lower() in OTHER_WORDS:
                words = words[1:]
            name = _capital(singular(readable(" ".join(words) or joined.header)))
        else:
            name = f"{row.name} flags"
        listed = ", ".join(c.header for c in flags)
        summary = (
            f"{listed} hold only {'/'.join(v.upper() if len(v) == 1 else v for v in finding.evidence['vocabulary'])}"
            + (f", and {joined.header} beside them lists more of the same set, split on {finding.detail['delimiter']!r}" if joined else "")
            + f": one list {name}, each {row.name} having several."
        )
        proposal, _, _ = self._start(finding, summary, flags[0].header)
        existing = self.existing_list(name)
        if existing:
            target, operations = existing, []
            proposal.keys["list"] = existing
        else:
            target, operations = self._list_type(proposal, name)
        relation, more = self._relation(proposal, row, target, name, "many-to-many")
        operations += more
        for column in flags:
            operations.append(
                {
                    "kind": "setColumnReading",
                    "source": row.source,
                    "column": column.header,
                    "reading": "relationFlag",
                    "relationTypeKey": relation,
                    "objectTypeKey": target,
                    "target": column.header,
                }
            )
            proposal.binds[column.header] = (row.source, "relationFlags")
        operations.append({"kind": "addValuesToList", "source": row.source, "column": flags[0].header})
        if joined is not None:
            operations.append(
                self._map(
                    proposal,
                    row.source,
                    joined.header,
                    {"relation": {"relationTypeKey": relation, "objectTypeKey": target, "matchBy": {"field": "name"}, "split": finding.detail["delimiter"], "missing": "create"}},
                )
            )
        proposal.operations = operations
        entries = _yes_no(finding.evidence["vocabulary"])
        alternative: list[dict[str, Any]] = []
        for column in flags:
            attribute = self.key(proposal, f"alt:{column.header}", "attributeTypes", column.header)
            value_map = self.key(proposal, f"altMap:{column.header}", "valueMaps", f"{column.header} yes no")
            alternative += [
                {"kind": "addAttributeType", "key": attribute, "name": column.header, "valueType": "boolean", "features": {}},
                {"kind": "attachAttribute", "objectType": row.type_key, "attributeType": attribute},
                {"kind": "mapColumn", "source": row.source, "column": column.header, "binding": {"attributeTypeKey": attribute}},
                {"kind": "setValueMap", "name": value_map, "entries": entries, "source": row.source, "column": column.header},
            ]
        proposal.alternatives = [{"label": f"Make {listed} yes/no attributes of {row.name} instead", "operations": alternative}]
        return proposal

    def _multiValued(self, finding: Finding) -> Proposal:
        table = self.tables[finding.sheet]
        column = next(c for c in table.columns if c.number == finding.columns[0])
        row = self.rows[table.name]
        name = _capital(singular(readable(column.header)))
        summary = (
            f"{column.header} holds several values split on {finding.detail['delimiter']!r} in "
            f"{round(finding.evidence['share'] * 100)}% of its cells: a list {name}, each {row.name} having several."
        )
        proposal, _, _ = self._start(finding, summary, column.header)
        existing = self.existing_list(name)
        if existing:
            target, operations = existing, []
            proposal.keys["list"] = existing
        else:
            target, operations = self._list_type(proposal, name)
        relation, more = self._relation(proposal, row, target, name, "many-to-many")
        operations += more
        operations.append(
            self._map(
                proposal,
                row.source,
                column.header,
                {"relation": {"relationTypeKey": relation, "objectTypeKey": target, "matchBy": {"field": "name"}, "split": finding.detail["delimiter"], "missing": "create"}},
            )
        )
        proposal.operations = operations
        return proposal

    def _textLookup(self, finding: Finding) -> Proposal:
        table = self.tables[finding.sheet]
        column = next(c for c in table.columns if c.number == finding.columns[0])
        row = self.rows[table.name]
        existing = self.matched_lookup(column) or self.existing_list(_capital(singular(readable(column.header))))
        name = (self._type(existing) or {}).get("name") if existing else _capital(singular(readable(column.header)))
        summary = (
            f"{column.header} has {column.distinct} values over {column.filled} rows: "
            + (f"each {row.name} refers to one of the existing {name} records." if existing else f"a list {name}, each {row.name} referring to one; values not in the list are created by the load.")
        )
        proposal, _, _ = self._start(finding, summary, column.header)
        operations: list[dict[str, Any]] = []
        if existing:
            target = existing
            proposal.keys["list"] = existing
        else:
            target, operations = self._list_type(proposal, name)
        relation, more = self._relation(proposal, row, target, name, "many-to-one")
        operations += more
        lookup: dict[str, Any] = {"relationTypeKey": relation, "objectTypeKey": target, "matchBy": {"field": "name"}}
        if not existing:
            lookup["missing"] = "create"
        operations.append(self._map(proposal, row.source, column.header, {"relation": lookup}))
        proposal.operations = operations
        text_attribute = self.key(proposal, "altAttribute", "attributeTypes", column.header)
        alternative = [
            {"kind": "addAttributeType", "key": text_attribute, "name": column.header, "valueType": "text", "features": {}},
            {"kind": "attachAttribute", "objectType": row.type_key, "attributeType": text_attribute},
            {"kind": "mapColumn", "source": row.source, "column": column.header, "binding": {"attributeTypeKey": text_attribute}},
        ]
        if not existing:
            alternative.append({"kind": "removeObjectType", "objectType": target})
        proposal.alternatives = [{"label": f"Read {column.header} as a text attribute of {row.name} instead", "operations": alternative}]
        if existing:
            self._missing(proposal, table, column, row, target, None, lookup)
        return proposal

    def _missing(
        self, proposal: Proposal, table: Table, column: Column, row: RowType, target: str, attribute: str | None, lookup: dict[str, Any] | None
    ) -> None:
        """D112: the column's values no stored record of ``target`` holds, in the evidence and the
        warnings, their rows refused by the load; created on load as the alternative, where a match
        by name can create them."""
        if self.stored is None or not self.stored.holds_records(target):
            return
        missing = self.stored.missing(table.name, column.header, target, attribute)
        proposal.evidence = {**proposal.evidence, "missing": missing[:DIFFERENCES_LISTED], "missingValues": len(missing)}
        if not missing:
            return
        name = (self._type(target) or {}).get("name") or target
        listed = ", ".join(f"{m['value']} ({m['rows']})" for m in missing[:5]) + (", …" if len(missing) > 5 else "")
        sentence = f"{len(missing)} of its values are not {name} records yet ({listed}): their rows are refused until they are."
        proposal.summary += f" {sentence}"
        self.missing_sentences[(table.name, column.header)] = sentence
        self.warnings.append(f"{column.header} of sheet '{table.name}' names {len(missing)} {name} values the stored records lack: {listed}")
        if lookup is not None:
            created = {**lookup, "missing": "create"}
            proposal.alternatives.append(
                {
                    "label": f"Create the {len(missing)} missing {name} values on load",
                    "operations": [{"kind": "mapColumn", "source": row.source, "column": column.header, "binding": {"relation": created}}],
                }
            )

    def _placeholders(self, finding: Finding) -> Proposal | None:
        table = self.tables[finding.sheet]
        column = next(c for c in table.columns if c.number == finding.columns[0])
        row = self.rows[table.name]
        found = [f"{p['value']} ({p['count']} rows)" for p in finding.evidence["placeholders"]]
        listed = found[0] if len(found) == 1 else ", ".join(found[:-1]) + f" and {found[-1]}"
        verb = "stands" if len(found) == 1 else "stand"
        summary = f"In {column.header}, {listed} {verb} for no value: send {'it' if len(found) == 1 else 'them'} to empty."
        proposal, _, _ = self._start(finding, summary, column.header)
        name = self.key(proposal, "valueMap", "valueMaps", f"{column.header} placeholders")
        entries = {value: None for value in finding.detail["values"]}
        proposal.operations = [{"kind": "setValueMap", "name": name, "entries": entries, "source": row.source, "column": column.header}]
        # A text lookup's alternative keeps reading through the map.
        for earlier in self.proposals:
            if earlier.sheet == table.name and earlier.pattern == "textLookup" and earlier.columns == [column.header]:
                for alternative in earlier.alternatives:
                    for operation in alternative["operations"]:
                        if operation["kind"] == "mapColumn" and operation["column"] == column.header:
                            operation["binding"]["valueMap"] = name
                # The column's latest proposal is this one, so it also says what the lookup found
                # missing from the stored list, and offers creating it (0.10 A7, D112).
                sentence = self.missing_sentences.get((table.name, column.header))
                if sentence:
                    proposal.summary += f" {sentence}"
                    proposal.evidence = {**proposal.evidence, "missing": earlier.evidence["missing"]}
                    proposal.alternatives = [copy.deepcopy(a) for a in earlier.alternatives if a["label"].startswith("Create the ")]
        return proposal

    def _externalId(self, finding: Finding) -> Proposal:
        table = self.tables[finding.sheet]
        column = next(c for c in table.columns if c.number == finding.columns[0])
        row = self.rows[table.name]
        identifier = self.identifiers.get((table.name, column.header)) if self.mode == "extend" else None
        if identifier is not None and self._type(identifier["type"]):
            return self._mapped_identifier(finding, table, column, row, identifier)
        unique = column.candidate_key
        summary = (
            f"{column.header} is a GUID on every row"
            + (", all different: a unique attribute of " if unique else ": an attribute of ")
            + f"{row.name}."
        )
        proposal, _, _ = self._start(finding, summary, column.header)
        attribute, operations = self.attribute(proposal, "attribute", table, column, row.type_key, unique=unique, value_type="text")
        operations.append(self._map(proposal, row.source, column.header, {"attributeTypeKey": attribute}))
        proposal.operations = operations
        alternative: list[dict[str, Any]] = [{"kind": "ignoreColumn", "source": row.source, "column": column.header}]
        if any(o["kind"] == "attachAttribute" for o in operations):
            alternative.append({"kind": "detachAttribute", "objectType": row.type_key, "attributeType": attribute})
        if any(o["kind"] == "addAttributeType" for o in operations):
            alternative.append({"kind": "removeAttributeType", "attributeType": attribute})
        proposal.alternatives = [{"label": f"Ignore {column.header}", "operations": alternative}]
        return proposal

    def _mapped_identifier(self, finding: Finding, table: Table, column: Column, row: RowType, identifier: dict[str, str]) -> Proposal:
        """D96: the column's values are already a type's unique values, under one parent record
        (a system's mappings under the system): each row's record relates to the record holding its
        value. A relation matched by the attribute links the records that exist; a related record
        would only find one the row already relates to, and create a second record holding the same
        unique value otherwise."""
        target = identifier["type"]
        found = self._type(target) or {}
        name = found.get("name") or target
        summary = (
            f"The values of {column.header} are already the {identifier['attribute']} of {name} records under "
            f"{identifier['parent']}: each {row.name} relates to the {name} holding its value."
        )
        proposal, _, _ = self._start(finding, summary, column.header)
        relation, operations = self._relation(proposal, row, target, name, "many-to-one")
        operations.append(
            self._map(
                proposal,
                row.source,
                column.header,
                {"relation": {"relationTypeKey": relation, "objectTypeKey": target, "matchBy": {"attributeTypeKey": identifier["attribute"]}}},
            )
        )
        proposal.operations = operations
        proposal.alternatives = [{"label": f"Ignore {column.header}", "operations": [{"kind": "ignoreColumn", "source": row.source, "column": column.header}]}]
        return proposal

    def _attribute(self, finding: Finding) -> Proposal:
        table = self.tables[finding.sheet]
        column = next(c for c in table.columns if c.number == finding.columns[0])
        row = self.rows[table.name]
        vocabulary = finding.detail.get("vocabulary")
        value_type = "boolean" if vocabulary else column.value_type()
        unique = column.candidate_key and not vocabulary
        described = f"only {'/'.join(v.upper() if len(v) == 1 else v for v in vocabulary)}" if vocabulary else _described(value_type)
        summary = f"{column.header} holds {described} on {column.filled} of {column.rows} rows: " + (
            f"a unique attribute of {row.name}." if unique else f"an attribute of {row.name}."
        )
        proposal, _, _ = self._start(finding, summary, column.header)
        attribute, operations = self.attribute(proposal, "attribute", table, column, row.type_key, unique=unique, value_type=value_type)
        operations.append(self._map(proposal, row.source, column.header, {"attributeTypeKey": attribute}))
        if vocabulary:
            name = self.key(proposal, "valueMap", "valueMaps", f"{column.header} yes no")
            operations.append(
                {"kind": "setValueMap", "name": name, "entries": _yes_no(vocabulary), "source": row.source, "column": column.header}
            )
        proposal.operations = operations
        return proposal

    def _sheetReference(self, finding: Finding) -> Proposal | None:
        table = self.tables[finding.sheet]
        column = next(c for c in table.columns if c.number == finding.columns[0])
        row = self.rows[table.name]
        target = self.rows.get(finding.detail["target"])
        by_name = finding.detail.get("by_name", False)
        if target is None or (target.key_attribute is None and not by_name):
            return None
        summary = (
            f"{round(finding.evidence['share'] * 100)}% of the values of {column.header} are {target.name} "
            f"{'names' if by_name else 'codes'} of sheet {finding.detail['target']}: each {row.name} refers to one {target.name}."
        )
        proposal, _, _ = self._start(finding, summary, column.header)
        relation, operations = self._relation(proposal, row, target.type_key, target.name, "many-to-one")
        operations.append(
            self._map(
                proposal,
                row.source,
                column.header,
                {"relation": {"relationTypeKey": relation, "objectTypeKey": target.type_key, "matchBy": {"field": "name"} if by_name else {"attributeTypeKey": target.key_attribute}}},
            )
        )
        proposal.operations = operations
        return proposal

    def _levelColumns(self, finding: Finding) -> Proposal | None:
        table = self.tables[finding.sheet]
        by_number = {c.number: c for c in table.columns}
        row = self.rows[table.name]
        if row.released or row.type_key in self.contained:
            return None
        self.contained.add(row.type_key)
        if "parent_code" in finding.detail:
            column = by_number[finding.detail["parent_code"]]
            summary = f"The values of {column.header} are {row.name} codes of the same sheet: each {row.name} stands under another."
            proposal, _, _ = self._start(finding, summary, column.header)
            relation = self.key(proposal, "containment", "relations", f"{row.type_key} contains")
            reverse = self.key(proposal, "containmentReverse", "relations", f"{row.type_key} in")
            proposal.operations = [
                # The rows without a parent code are the hierarchy's top.
                {"kind": "setContainment", "objectType": row.type_key, "parent": _parent_of(row.type_key, relation, reverse, optional=True)},
                self._map(proposal, row.source, column.header, {"parent": {"objectTypeKey": row.type_key, "matchBy": {"attributeTypeKey": row.key_attribute}}}),
            ]
            return proposal
        levels = [by_number[n] for n in finding.detail["levels"]]
        summary = f"{', '.join(c.header for c in levels)} are levels of a hierarchy: a type per level, each under the one before, and {row.name} under the last."
        proposal, _, _ = self._start(finding, summary, levels[0].header)
        operations: list[dict[str, Any]] = []
        previous: tuple[str, str, Column] | None = None
        for index, column in enumerate(levels):
            name = _capital(singular(readable(column.header)))
            level = self.key(proposal, f"level{index}", "objectTypes", name)
            parent: dict[str, Any] | None = None
            if previous is not None:
                relation = self.key(proposal, f"containment{index}", "relations", f"{previous[0]} contains")
                reverse = self.key(proposal, f"containmentReverse{index}", "relations", f"{level} in")
                parent = _parent_of(previous[0], relation, reverse, optional=previous[2].filled < table.rows)
            operations.append({"kind": "addObjectType", "applicationKey": self.app, "key": level, "name": name, "pluralName": plural(name), "parent": parent})
            attribute, more = self.attribute(proposal, f"levelAttribute{index}", table, column, level, unique=True, value_type="text")
            operations += more
            source = self.key(proposal, f"levelSource{index}", "sources", f"{table.name} {level}")
            operations.append({"kind": "addSource", "id": source, "sheet": table.name, "objectType": level, "applicationKey": self.app, "key": {"attributeTypeKey": attribute}})
            operations.append(self._map(proposal, source, column.header, {"attributeTypeKey": attribute}))
            if previous is not None:
                operations.append(
                    {"kind": "mapColumn", "source": source, "column": previous[2].header, "binding": {"parent": {"objectTypeKey": previous[0], "matchBy": {"attributeTypeKey": previous[1]}}}}
                )
            previous = (level, attribute, column)
        relation = self.key(proposal, "containmentRow", "relations", f"{previous[0]} contains")
        reverse = self.key(proposal, "containmentRowReverse", "relations", f"{row.type_key} in")
        operations.append(
            {
                "kind": "setContainment",
                "objectType": row.type_key,
                "parent": _parent_of(previous[0], relation, reverse, optional=previous[2].filled < table.rows),
            }
        )
        operations.append(self._map(proposal, row.source, previous[2].header, {"parent": {"objectTypeKey": previous[0], "matchBy": {"attributeTypeKey": previous[1]}}}))
        proposal.operations = operations
        return proposal

    def _translations(self, proposal: Proposal, row: RowType) -> tuple[str, str, str, list[dict[str, Any]]]:
        """A language list and a translation type under it, made by the inference's first
        translations and required by the others, and the relation from ``row``'s type."""
        operations: list[dict[str, Any]] = []
        if self.translation_types is None:
            language = self.key(proposal, "language", "objectTypes", "Language")
            translation = self.key(proposal, "translation", "objectTypes", "Translation")
            containment = self.key(proposal, "containment", "relations", f"{language} contains")
            reverse = self.key(proposal, "containmentReverse", "relations", f"{translation} in")
            operations += [
                {"kind": "addObjectType", "applicationKey": self.app, "key": language, "name": "Language", "pluralName": "Languages", "parent": None},
                {
                    "kind": "addObjectType",
                    "applicationKey": self.app,
                    "key": translation,
                    "name": "Translation",
                    "pluralName": "Translations",
                    "parent": _parent_of(language, containment, reverse),
                },
            ]
            self.translation_types = (proposal.id, language, translation)
        else:
            first, language, translation = self.translation_types
            proposal.keys["language"], proposal.keys["translation"] = language, translation
            proposal.requires.append(first)
        relation = self.key(proposal, "relation", "relations", f"{row.name} has translation")
        relation_reverse = self.key(proposal, "relationReverse", "relations", f"translation of {row.name}")
        operations += [
            {"kind": "addRelationType", "key": relation, "reverseKey": relation_reverse, "name": "Has translation", "reverseName": "Translation of"},
            {"kind": "allowRelation", "relationType": relation, "from": row.type_key, "to": translation, "cardinality": "one-to-many"},
        ]
        return language, translation, relation, operations

    def _translationsByRow(self, finding: Finding) -> Proposal | None:
        table = self.tables[finding.sheet]
        by_number = {c.number: c for c in table.columns}
        row = self.rows.get(finding.detail["target"])
        if row is None or row.key_attribute is None:
            return None
        reference, language_column, name_column = (by_number[finding.detail[k]] for k in ("reference", "language", "name"))
        languages = finding.evidence["languages"]
        summary = (
            f"Each {reference.header} of {finding.detail['target']} appears once per language ({len(languages)}) in "
            f"{table.name}: translations of {name_column.header}, under a list of languages created by the load."
        )
        proposal, _, _ = self._start(finding, summary)
        language, translation, relation, operations = self._translations(proposal, row)
        source = self.key(proposal, "source", "sources", f"{table.name} {row.type_key}")
        operations += [
            {"kind": "addSource", "id": source, "sheet": table.name, "objectType": row.type_key, "applicationKey": row.application, "key": {"attributeTypeKey": row.key_attribute}},
            {"kind": "setSource", "source": source, "record": "existing"},
            self._map(proposal, source, reference.header, {"attributeTypeKey": row.key_attribute}),
            self._map(
                proposal,
                source,
                name_column.header,
                {
                    "relatedRecord": {
                        "relationTypeKey": relation,
                        "applicationKey": self.app,
                        "objectTypeKey": translation,
                        "parent": {"objectTypeKey": language, "matchBy": {"field": "name"}, "column": language_column.header, "missing": "create"},
                        "field": "name",
                    }
                },
            ),
        ]
        proposal.operations = operations
        proposal.alternatives = [
            {
                "label": f"Ignore the sheet {table.name}",
                "operations": [
                    {"kind": "ignoreSheet", "sheet": table.name},
                    {"kind": "removeObjectType", "objectType": translation},
                    {"kind": "removeObjectType", "objectType": language},
                ],
            }
        ]
        return proposal

    def _translationsByColumn(self, finding: Finding) -> Proposal | None:
        table = self.tables[finding.sheet]
        by_number = {c.number: c for c in table.columns}
        row = self.rows[table.name]
        columns = [by_number[n] for n in finding.columns]
        if "base" in finding.detail:
            # Found by values (D100): the translations of whatever type the base column names; a
            # base no type takes its name from leaves its translations attributes of the row.
            named = self.named.get((table.name, finding.detail["base"]))
            if named is None:
                for column in columns:
                    self._add(self._attribute(Finding("attribute", table.name, [column.number], {"valueType": column.value_type(), "unique": column.candidate_key})))
                return None
            row = named
        summary = (
            f"{', '.join(c.header for c in columns)} translate {finding.evidence['name']} into "
            f"{', '.join(finding.evidence['languages'])}"
            + (", value for value" if finding.evidence.get("byValues") else "")
            + ": translations under a list of languages created by the load."
        )
        proposal, _, _ = self._start(finding, summary)
        language, translation, relation, operations = self._translations(proposal, row)
        for column in columns:
            operations.append(
                self._map(
                    proposal,
                    row.source,
                    column.header,
                    {
                        "relatedRecord": {
                            "relationTypeKey": relation,
                            "applicationKey": self.app,
                            "objectTypeKey": translation,
                            "parent": {"objectTypeKey": language, "matchBy": {"field": "name"}, "value": finding.detail["languages"][column.number], "missing": "create"},
                            "field": "name",
                        }
                    },
                )
            )
        proposal.operations = operations
        return proposal

    # --- a model description (0.10 A7, D107–D109) -------------------------------------------------

    def _modelDescription(self, finding: Finding) -> Proposal:
        fields = finding.detail["fields"]
        lookups = [f for f in fields if f["kind"] in ("lookup", "multi") and f["target"]]
        proposal, table, columns = self._start(
            finding,
            "",
        )
        matched = self.described_by({fold(f["field"]) for f in fields})
        name = (self._type(matched) or {}).get("name") if matched else _capital(singular(readable(table.name)))
        proposal.summary = (
            f"{table.name} describes a model: {len(fields)} fields in {columns[0].header} with their types in "
            f"{columns[1].header}, {len(lookups)} of them looking up a list {columns[2].header} names"
            + (f": they are the fields of the existing {name}." if matched else f": a type {name} with them, its lists read from the sheets they name.")
        )
        operations: list[dict[str, Any]] = []
        if matched:
            type_key = matched
            proposal.keys["type"] = matched
            app = self._application_of(matched) or self.app
        else:
            type_key = self.key(proposal, "type", "objectTypes", name)
            app = self.app
            operations.append({"kind": "addObjectType", "applicationKey": app, "key": type_key, "name": name, "pluralName": plural(name), "parent": None})
        if table.name not in (self.profile.get("ignoredSheets") or []):
            operations.append({"kind": "ignoreSheet", "sheet": table.name})
        proposal.operations = operations
        self.described = RowType(type_key, "", None, app or "", name, released=self.released(f"objectType:{type_key}"))
        return proposal

    def _describedList(self, finding: Finding) -> Proposal | None:
        evidence = finding.evidence
        target = evidence["target"]
        name = _capital(singular(readable(target)))
        sheet = evidence.get("sheet")
        if evidence.get("toBeDefined"):
            summary = f"{target} is to be defined: its sheet {sheet} holds only {', '.join(evidence['values'])}. The list {name} is added with nothing to load."
        elif sheet is None:
            summary = f"{target} has no sheet: the list {name} is added, its records " + (
                "named by the flag fields when a file holding them loads." if evidence.get("records") == "named by the fields" else "added later."
            )
        else:
            summary = f"{target} names the sheet {sheet}: a list {name}, read from it."
        proposal = self._new("describedList", finding.sheet, [], summary, evidence, f"describedList|{target}")
        existing = self.existing_list(name)
        operations: list[dict[str, Any]] = []
        if existing:
            target_key = existing
            proposal.keys["list"] = existing
            name = (self._type(existing) or {}).get("name") or name
        else:
            target_key, operations = self._list_type(proposal, name)
        self.described_lists[target] = (target_key, name)
        if evidence.get("toBeDefined"):
            self.warnings.append(f"{target} is to be defined: its sheet {sheet} holds no value yet, so the list {name} loads nothing")
            if sheet not in (self.profile.get("ignoredSheets") or []):
                operations.append({"kind": "ignoreSheet", "sheet": sheet})
        elif sheet is not None and finding.columns:
            table = self.tables[sheet]
            by_number = {c.number: c for c in table.columns}
            key = by_number.get(finding.detail.get("key"))
            label = by_number.get(finding.detail.get("name"))
            proposal.columns = [c.header for c in (key, label) if c is not None]
            source = self.key(proposal, "source", "sources", f"{sheet} {target_key}")
            app = self._application_of(target_key) or self.app
            add: dict[str, Any] = {"kind": "addSource", "id": source, "sheet": sheet, "objectType": target_key, "applicationKey": app}
            maps: list[dict[str, Any]] = []
            attribute = None
            if key is not None:
                attribute, more = self.attribute(proposal, "keyAttribute", table, key, target_key, unique=True, value_type="text" if key.textual else key.value_type())
                operations += more
                add["key"] = {"attributeTypeKey": attribute}
                maps.append(self._map(proposal, source, key.header, {"attributeTypeKey": attribute}))
            if label is not None:
                maps.append(self._map(proposal, source, label.header, {"field": "name"}))
            operations += [add, *maps]
            placeholders = finding.detail.get("placeholders") or []
            if key is not None and placeholders:
                value_map = self.key(proposal, "valueMap", "valueMaps", f"{key.header} placeholders")
                operations.append({"kind": "setValueMap", "name": value_map, "entries": dict.fromkeys(placeholders), "source": source, "column": key.header})
                operations.append({"kind": "setSource", "source": source, "rowsWithoutKey": "skip"})
                rows = sum(p["count"] for p in evidence.get("placeholderKeys") or [])
                proposal.summary += f" A row whose {key.header} is {', '.join(placeholders)} ({rows} {'row' if rows == 1 else 'rows'}) stands for no record and is skipped."
        proposal.operations = operations
        return proposal

    def _describedField(self, finding: Finding) -> Proposal | None:
        described = self.described
        if described is None:
            return None
        entry = finding.detail["field"]
        field_name, kind, target = entry["field"], entry["kind"], entry["target"]
        listed = self.described_lists.get(target) if target else None
        proposal = self._new("describedField", finding.sheet, [], "", finding.evidence, f"describedField|{finding.sheet}|{field_name}")
        if kind in ("lookup", "multi") and listed:
            target_key, list_name = listed
            _, operations = self._named_relation(proposal, described, target_key, field_name, "many-to-one" if kind == "lookup" else "many-to-many")
            proposal.summary = f"{field_name} is a {entry['type']} of {target}: each {described.name} refers to {'one' if kind == 'lookup' else 'several'} of {list_name}."
            proposal.operations = operations
            return proposal
        value_type = {"flag": "boolean", "lookup": "text", "multi": "text"}.get(kind, kind)
        if not entry.get("known"):
            self.warnings.append(f"Field '{field_name}' has the type '{entry['type']}', which is not a type word: read as text")
        attribute = self._described_attribute(described.type_key, field_name, value_type)
        operations: list[dict[str, Any]] = []
        if attribute is None:
            attribute = self.key(proposal, "attribute", "attributeTypes", field_name)
            operations.append({"kind": "addAttributeType", "key": attribute, "name": field_name, "valueType": value_type, "features": {}})
        else:
            proposal.keys["attribute"] = attribute
        if not self._binds(described.type_key, attribute):
            operations.append({"kind": "attachAttribute", "objectType": described.type_key, "attributeType": attribute})
        proposal.summary = f"{field_name} is {entry['type'] or 'without a type'}: an attribute of {described.name} holding {_described(value_type)}."
        proposal.operations = operations
        return proposal

    def _describedFlags(self, finding: Finding) -> Proposal | None:
        described = self.described
        listed = self.described_lists.get(finding.detail["target"])
        if described is None or listed is None:
            return None
        target_key, list_name = listed
        fields = finding.detail["fields"]
        proposal = self._new(
            "describedFlags",
            finding.sheet,
            [],
            f"{', '.join(fields)} are flags of {finding.detail['target']}: one list {list_name}, each {described.name} having several, "
            "a flag set standing for the record of its field's name.",
            finding.evidence,
            f"describedFlags|{finding.sheet}|{finding.detail['target']}",
        )
        _, proposal.operations = self._named_relation(proposal, described, target_key, readable(finding.detail["target"]), "many-to-many")
        return proposal

    # --- a list of a sheet laid out for reading (0.10 A8a, D116–D119) ------------------------------

    def _listBlock(self, finding: Finding) -> Proposal | None:
        block = finding.detail["block"]
        evidence = finding.evidence
        by_number = {c.number: c for c in block.columns}
        names = block.columns[0]
        place = f"{finding.sheet} {block.range}"
        if not finding.detail["list"]:
            if finding.detail.get("reason") == "free":
                self.warnings.append(f"{names.header} ({place}) is a free field, not a list: nothing is proposed for it")
            else:
                self.warnings.append(f"{names.header} ({place}) is a header with no values under it, not a list: nothing is proposed for it")
            return None
        name = _capital(singular(readable(names.header)))
        note = evidence.get("note")
        summary = f"{names.header} ({place}) lists {names.filled} values: a list {name}, read from its block by name."
        proposal = self._new("listBlock", finding.sheet, [c.header for c in block.columns], summary, evidence, f"listBlock|{finding.sheet}|{block.first_column}{block.header_row}")
        existing = self.existing_list(name)
        operations: list[dict[str, Any]] = []
        if existing:
            target = existing
            proposal.keys["list"] = existing
            name = (self._type(existing) or {}).get("name") or name
        else:
            target, operations = self._list_type(proposal, name)
            if note and note["meaning"] in NOTE_DESCRIPTIONS:
                operations[0]["description"] = NOTE_DESCRIPTIONS[note["meaning"]]
        app = self._application_of(target) or self.app
        source = self.key(proposal, "source", "sources", f"{finding.sheet} {target}")
        operations.append(
            {
                "kind": "addSource",
                "id": source,
                "sheet": finding.sheet,
                "objectType": target,
                "applicationKey": app,
                "headerRow": block.header_row,
                "block": {"firstColumn": block.first_column, "lastColumn": block.last_column, "lastRow": block.last_row},
                "key": {"field": "name"},
            }
        )
        operations.append(self._map(proposal, source, names.header, {"field": "name"}))
        if note:
            value_map = self.key(proposal, "valueMap", "valueMaps", f"{names.header} note")
            operations.append({"kind": "setValueMap", "name": value_map, "entries": {note["text"]: None}, "source": source, "column": names.header})
            operations.append({"kind": "setSource", "source": source, "rowsWithoutKey": "skip"})
            if note["meaning"] == "heading":
                proposal.summary += f" {note['text']!r} under its header answers none of its yes/no columns: a second header row, skipped."
            else:
                said = NOTE_DESCRIPTIONS.get(note["meaning"], "it is a free field").lower()
                proposal.summary += f" The note {note['text']!r} under its header says {said}; its row is skipped."
        row = RowType(target, source, None, app, name, released=self.released(f"objectType:{target}"))
        alternatives: list[dict[str, Any]] = []
        if finding.detail["translations"]:
            _, translation, relation, more = self._translations(proposal, row)
            operations += more
            for number, language in finding.detail["translations"]:
                column = by_number[number]
                operations.append(
                    self._map(
                        proposal,
                        source,
                        column.header,
                        {
                            "relatedRecord": {
                                "relationTypeKey": relation,
                                "applicationKey": self.app,
                                "objectTypeKey": translation,
                                "parent": {"objectTypeKey": proposal.keys["language"], "matchBy": {"field": "name"}, "value": language, "missing": "create"},
                                "field": "name",
                            }
                        },
                    )
                )
                attribute = self.key(proposal, f"altAttribute:{column.header}", "attributeTypes", column.header)
                alternatives.append(
                    {
                        "label": f"Read {column.header} as a text attribute of {name} instead",
                        "operations": [
                            {"kind": "addAttributeType", "key": attribute, "name": readable(column.header), "valueType": "text", "features": {}},
                            {"kind": "attachAttribute", "objectType": target, "attributeType": attribute},
                            {"kind": "mapColumn", "source": source, "column": column.header, "binding": {"attributeTypeKey": attribute}},
                        ],
                    }
                )
            languages = ", ".join(language for _, language in finding.detail["translations"])
            proposal.summary += f" {', '.join(by_number[n].header for n, _ in finding.detail['translations'])} translate its names ({languages})."
        flags = [by_number[n] for n in finding.detail["flags"]]
        vocabularies = finding.detail["vocabularies"]
        if len(flags) == 1:
            column = flags[0]
            attribute, more = self.attribute(proposal, f"flag:{column.header}", block, column, target, value_type="boolean")
            operations += more
            operations.append(self._map(proposal, source, column.header, {"attributeTypeKey": attribute}))
            map_key = self.key(proposal, f"flagMap:{column.header}", "valueMaps", f"{column.header} yes no")
            operations.append({"kind": "setValueMap", "name": map_key, "entries": _yes_no(vocabularies[column.number]), "source": source, "column": column.header})
            proposal.summary += f" {column.header} holds yes or no: a yes/no attribute."
        elif flags:
            flag_list, more = self._list_type(proposal, f"{name} flags") if not self.existing_list(f"{name} flags") else (self.existing_list(f"{name} flags"), [])
            operations += more
            relation, more = self._relation(proposal, row, flag_list, f"{name} flags", "many-to-many", role="flagRelation")
            operations += more
            for column in flags:
                operations.append(
                    {
                        "kind": "setColumnReading",
                        "source": source,
                        "column": column.header,
                        "reading": "relationFlag",
                        "relationTypeKey": relation,
                        "objectTypeKey": flag_list,
                        "target": column.header,
                    }
                )
                proposal.binds[column.header] = (source, "relationFlags")
            operations.append({"kind": "addValuesToList", "source": source, "column": flags[0].header})
            proposal.summary += f" {', '.join(c.header for c in flags)} hold yes or no: one list of them, each value having several."
        for number in finding.detail["attributes"]:
            column = by_number[number]
            attribute, more = self.attribute(proposal, f"attribute:{column.header}", block, column, target)
            operations += more
            operations.append(self._map(proposal, source, column.header, {"attributeTypeKey": attribute}))
        if evidence.get("empty"):
            empty = ", ".join(e["column"] for e in evidence["empty"])
            proposal.summary += f" {empty} {'holds' if len(evidence['empty']) == 1 else 'hold'} no values yet and {'is' if len(evidence['empty']) == 1 else 'are'} not read."
        proposal.operations = operations
        proposal.alternatives = alternatives
        return proposal

    def _one_list(self, run: list[Finding]) -> None:
        """D143 (0.10 A8c): on each list of a run of one shape, the alternative of one list under
        their headers. It takes away what each list's proposal added (its source, value maps, list
        type and flag list, whose relations and attributes go with them, D31; not the shared language list and translation
        type), then adds a parent list named after the run's title (else the sheet) holding the
        headers, one list contained in it, and a source per list fixed to its header (D141), keyed
        by name under it (D142). Columns are read by position as the first list's, named after its
        headers; notes and second header rows are skipped as before. The title's navigation group
        holds the two new lists."""
        members = [(f, self.block_proposals.get(id(f))) for f in run]
        if any(p is None for _, p in members):
            return
        added: list[tuple[Finding, Proposal, dict[str, Any]]] = []
        for finding, proposal in members:
            (source,) = [o for o in proposal.operations if o["kind"] == "addSource"]
            if not any(o["kind"] == "addObjectType" and o["key"] == source["objectType"] for o in proposal.operations):
                return  # a list onto a type the model holds is not taken away (extend mode)
            added.append((finding, proposal, source))
        first, _, first_source = added[0]
        block = first.detail["block"]
        sheet = first.sheet
        shared = set(self.translation_types[1:]) if self.translation_types else set()
        removals: list[dict[str, Any]] = []
        for _, proposal, source in added:
            removals.append({"kind": "removeSource", "source": source["id"]})
        for _, proposal, _ in added:
            removals += [{"kind": "setValueMap", "name": o["name"], "entries": None} for o in proposal.operations if o["kind"] == "setValueMap"]
        for _, proposal, _ in added:
            removals += [
                {"kind": "removeObjectType", "objectType": o["key"]}
                for o in proposal.operations
                if o["kind"] == "addObjectType" and o["key"] not in shared
            ]

        title = block.titles[-1] if block.titles else None
        name = _capital(singular(readable(title or sheet)))
        app = first_source.get("applicationKey") or self.app
        scratch = self._new("listBlock", sheet, [], "", {}, f"oneList|{sheet}|{block.first_column}{block.header_row}")
        parent = self.key(scratch, "parent", "objectTypes", f"{name} category")
        one = self.key(scratch, "list", "objectTypes", name)
        containment = self.key(scratch, "containment", "relations", f"{parent} contains")
        reverse = self.key(scratch, "containmentReverse", "relations", f"{one} in")
        operations: list[dict[str, Any]] = [
            {"kind": "addObjectType", "applicationKey": app, "key": parent, "name": f"{name} category", "pluralName": plural(f"{name} category"), "parent": None},
            {"kind": "addObjectType", "applicationKey": app, "key": one, "name": name, "pluralName": plural(name), "parent": _parent_of(parent, containment, reverse)},
        ]
        shape = shape_of(first)
        others = block.columns[1:]
        yes_no = [i for i, kind in enumerate(shape) if kind == "yesNo"]
        row = RowType(one, "", None, app, name)
        relation = None
        if "translation" in shape and self.translation_types is not None:
            _, _, translation = self.translation_types
            relation = self.key(scratch, "relation", "relations", f"{name} has translation")
            relation_reverse = self.key(scratch, "relationReverse", "relations", f"translation of {name}")
            operations += [
                {"kind": "addRelationType", "key": relation, "reverseKey": relation_reverse, "name": "Has translation", "reverseName": "Translation of"},
                {"kind": "allowRelation", "relationType": relation, "from": one, "to": translation, "cardinality": "one-to-many"},
            ]
        attributes: dict[int, str] = {}
        maps: dict[int, str] = {}
        for index, kind in enumerate(shape):
            column = others[index]
            if kind == "attribute" or (kind == "yesNo" and len(yes_no) == 1):
                value_type = "boolean" if kind == "yesNo" else column.value_type()
                key = self.key(scratch, f"attribute:{index}", "attributeTypes", readable(column.header))
                attributes[index] = key
                operations += [
                    {"kind": "addAttributeType", "key": key, "name": readable(column.header), "valueType": value_type, "features": {}},
                    {"kind": "attachAttribute", "objectType": one, "attributeType": key},
                ]
                if kind == "yesNo":
                    maps[index] = self.key(scratch, f"flagMap:{index}", "valueMaps", f"{column.header} yes no")
        flag_list = flag_relation = None
        if len(yes_no) > 1:
            flag_list, more = self._list_type(scratch, f"{name} flags")
            operations += more
            flag_relation, more = self._relation(scratch, row, flag_list, f"{name} flags", "many-to-many", role="flagRelation")
            operations += more
        vocabularies: dict[int, set[str]] = {i: set() for i in maps}
        for finding, _, _ in added:
            for index in maps:
                number = finding.detail["block"].columns[1 + index].number
                vocabularies[index] |= set(finding.detail["vocabularies"].get(number, []))
        for position, (finding, _, source) in enumerate(added):
            member = finding.detail["block"]
            columns = member.columns[1:]
            header = member.columns[0].header
            languages = dict(finding.detail["translations"])
            source_id = self.key(scratch, f"source:{position}", "sources", f"{sheet} {one} {header}")
            operations.append(
                {
                    "kind": "addSource",
                    "id": source_id,
                    "sheet": sheet,
                    "objectType": one,
                    "applicationKey": app,
                    "headerRow": source["headerRow"],
                    "block": dict(source["block"]),
                    "key": {"field": "name"},
                    "parent": {"objectTypeKey": parent, "matchBy": {"field": "name"}, "value": header, "missing": "create"},
                }
            )
            operations.append(self._map(scratch, source_id, header, {"field": "name"}))
            note = finding.evidence.get("note")
            if note:
                value_map = self.key(scratch, f"valueMap:{position}", "valueMaps", f"{header} note")
                operations.append({"kind": "setValueMap", "name": value_map, "entries": {note["text"]: None}, "source": source_id, "column": header})
                operations.append({"kind": "setSource", "source": source_id, "rowsWithoutKey": "skip"})
            flagged = []
            for index, kind in enumerate(shape):
                column = columns[index]
                if kind == "translation" and relation is not None:
                    _, language, translation = self.translation_types
                    operations.append(
                        self._map(
                            scratch,
                            source_id,
                            column.header,
                            {
                                "relatedRecord": {
                                    "relationTypeKey": relation,
                                    "applicationKey": self.app,
                                    "objectTypeKey": translation,
                                    "parent": {"objectTypeKey": language, "matchBy": {"field": "name"}, "value": languages[column.number], "missing": "create"},
                                    "field": "name",
                                }
                            },
                        )
                    )
                elif index in attributes:
                    operations.append(self._map(scratch, source_id, column.header, {"attributeTypeKey": attributes[index]}))
                    if index in maps:
                        operations.append(
                            {"kind": "setValueMap", "name": maps[index], "entries": _yes_no(sorted(vocabularies[index])), "source": source_id, "column": column.header}
                        )
                elif kind == "yesNo" and flag_list is not None:
                    flagged.append(column.header)
                    operations.append(
                        {
                            "kind": "setColumnReading",
                            "source": source_id,
                            "column": column.header,
                            "reading": "relationFlag",
                            "relationTypeKey": flag_relation,
                            "objectTypeKey": flag_list,
                            "target": column.header,
                        }
                    )
            if flagged:
                operations.append({"kind": "addValuesToList", "source": source_id, "column": flagged[0]})
        group = next(
            (
                (o["applicationKey"], o["key"])
                for p in self.proposals
                if p.pattern == "navigationGroup"
                for o in p.operations
                if o["kind"] == "addNavigationGroup" and {s["objectType"] for _, _, s in added} & set(o["collections"])
            ),
            None,
        )
        if group is not None:
            operations += [{"kind": "placeCollection", "applicationKey": group[0], "collection": c, "group": group[1]} for c in (parent, one)]
        alternative = {"label": f"Read these {len(added)} lists as one list under their headers", "operations": removals + operations}
        for _, proposal, _ in added:
            proposal.alternatives.append(copy.deepcopy(alternative))

    def _named_relation(self, proposal: Proposal, row: RowType, target: str, name: str, cardinality: str) -> tuple[str, list[dict[str, Any]]]:
        """A relation named as a described field, or the one of that name already allowed between
        the two types (D111 (d))."""
        relations = {r.get("key"): r for r in self.model.get("relationTypes") or []}
        for allowed in self.model.get("objectTypeRelations") or []:
            relation = relations.get(allowed.get("relationTypeKey")) or {}
            if (allowed.get("fromObjectTypeKey"), allowed.get("toObjectTypeKey")) == (row.type_key, target) and fold(relation.get("name") or "") == fold(name):
                proposal.keys["relation"] = relation["key"]
                return relation["key"], []
        key = self.key(proposal, "relation", "relations", f"{row.name} {name}")
        reverse = self.key(proposal, "relationReverse", "relations", f"{name} of {row.name}")
        return key, [
            {"kind": "addRelationType", "key": key, "reverseKey": reverse, "name": name, "reverseName": f"{name} of"},
            {"kind": "allowRelation", "relationType": key, "from": row.type_key, "to": target, "cardinality": cardinality},
        ]

    def _described_attribute(self, type_key: str, name: str, value_type: str) -> str | None:
        """An existing attribute type of the field's name and a fitting type, the type's own first."""
        if self.mode != "extend":
            return None
        candidates = [
            a for a in self.model.get("attributeTypes") or []
            if fold(a.get("name") or "") == fold(name) and (a.get("valueType") or "text") in _compatible(value_type)
        ]
        bound = [a for a in candidates if self._binds(type_key, a["key"])]
        return (bound or candidates or [{}])[0].get("key")

    def _navigationGroup(self, finding: Finding, by_id: dict[int, Finding]) -> Proposal | None:
        collections = [self.list_types[id(f)] for f in finding.detail["lists"] if id(f) in self.list_types]
        collections = [c for c in collections if self._application_of(c) in (None, self.app)]
        if len(collections) < 2:
            return None
        row = self.rows.get(finding.sheet)
        title = finding.evidence.get("title")
        # The lists under a title of a sheet laid out for reading are grouped by it (0.10 A8a).
        label = readable(title) if title else f"{row.name if row else readable(finding.sheet)} lists"
        summary = f"Group the {len(collections)} lists the sheet {finding.sheet} adds in the sidebar as \"{label}\", folded."
        anchor = "|".join(filter(None, ["navigationGroup", finding.sheet, title]))
        proposal = self._new("navigationGroup", finding.sheet, [], summary, finding.evidence, anchor)
        key = self.key(proposal, "group", "groups", label)
        proposal.operations = [
            {"kind": "addNavigationGroup", "applicationKey": self.app, "key": key, "label": label, "collapsed": True, "collections": collections}
        ]
        return proposal


def _parent_of(parent: str, relation: str, reverse: str, *, optional: bool = False) -> dict[str, Any]:
    """A containment ``parent`` parameter under a new relation; ``optional`` where some rows have
    no parent (D99: a required parent refused every row with an empty parent cell)."""
    return {
        "objectTypes": [parent],
        "relationType": {"key": relation, "reverseKey": reverse, "name": "Contains", "reverseName": "In"},
        **({"optional": True} if optional else {}),
    }


def _yes_no(vocabulary: list[str]) -> dict[str, bool]:
    """A yes/no column's words to true and false, as written in any case."""
    truthy = {"y", "yes", "x", "true", "1"}
    return {spelled: value in truthy for value in vocabulary for spelled in sorted({value, value.upper(), value.capitalize()})}



def _compatible(value_type: str) -> tuple[str, ...]:
    """Value types an existing attribute may have to take a column read as ``value_type``."""
    if value_type == "integer":
        return ("integer", "decimal", "text", "longText")
    if value_type in ("decimal", "boolean", "date", "dateTime"):
        return (value_type, "text", "longText")
    return ("text", "longText")


def _described(value_type: str) -> str:
    return {
        "integer": "whole numbers",
        "decimal": "numbers",
        "boolean": "true or false",
        "date": "dates",
        "dateTime": "dates and times",
        "longText": "long text",
    }.get(value_type, "text")


def copied(operations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return copy.deepcopy(operations)
