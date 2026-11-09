"""The model configurations journey tests run on (TEST_HARNESS_PLAN H4c).

A journey test names structures, never a configuration's keys: ``R`` (a root type with typed
attributes and rules), ``H`` (a self-hierarchy), ``Bnn`` (a many-to-many relationship across
applications) and so on. A configuration maps each structure it holds to its own keys.

- **generated-a** and **generated-b** are generated here. They hold every structure and differ in
  keys and in shape: in B the record a dependant's scoped uniqueness counts from (``G``) is two levels
  above it, with a container type ``M`` between, and the types are split across the two applications
  differently.
- **example** is the starter model delivered with the engine. It holds a few of the structures; a test
  runs on it only when it holds all the structures the test names.

Every test runs on generated A, and on the example model where it holds the test's structures,
otherwise on generated B: two configurations each (H4c, decided 2026-10-02).

- **parity** is the consumer API's parity fixture (Base 0.9 C8, C-D72): the starter with locations,
  availability, durations and a single-valued self relation, and CONSUMER_API's reference definition.
  It is fixture content, not product scope, and only the parity tests use it; no structure maps to it.

Structures:

- ``A1``, ``A2``: two applications.
- ``R``: a root type. Attributes ``R.u`` (unique text, searchable, filterable, sortable), ``R.n``
  (integer, minimum 0, maximum 100), ``R.b`` (boolean), ``R.dt`` (date), ``R.q`` (required text),
  ``R.ro`` (read-only text with a default), ``R.x1``/``R.x2`` (at least one of the two).
- ``R2``: a type under ``R`` with its own unique, optional ``R2.u``; it may also hold ``R.u``, a
  unique value two types share (a reference naming ``R`` by ``R.u`` can find an ``R2``).
- ``H``: a root type with a self-hierarchy; ``H.code`` (searchable, filterable, sortable), ``H.rank``.
- ``P``, ``Q``: root types; ``C``: a type under ``P`` or ``Q`` (never at the top); ``C2`` under ``C``.
- ``K``: a root type of the other application than ``H``; ``K.code``, ``K.rank``.
- ``G``: a root type; ``M``: a container under ``G``; ``D``: a dependant under ``G`` or ``M`` (in B and
  the example only under ``M``: the shape ``deep-scope``) with ``D.active``; ``D2`` under ``D``.
- ``L1`` (root), ``L2`` under ``L1``, ``L3`` under ``L2`` or ``L3``: the restructuring ladder; ``L1``
  never contains ``L1``. ``L.only1`` and ``Ll1k`` (to ``K``) only ``L1`` has, ``Ll2k`` (to ``K``) only
  ``L2``; ``L2`` requires ``L.extra``, which ``L1`` lacks.
- Relationships: ``B11`` R→K one-to-one, ``B1n`` R→K one-to-many, ``Bn1`` H→K many-to-one (an H
  holds one K, a K serves many H; 0.9 K3a), ``Bnn`` H→K many-to-many with
  ``Bnn.weight`` (integer, minimum 1) and ``Bnn.note``; ``Bown`` R→D required one-to-many (D a
  dependant of R), unique per R within a ``G`` while ``D.active`` is true; ``Bscope`` R→D optional
  many-to-many with the same scope rule and the relationship's own ``Bscope.flag`` (boolean) and
  ``Bscope.note`` (text), and from ``R2`` to ``D`` without them; ``Hparent`` the
  self-hierarchy's containment. ``Bsrc`` H→K many-to-many whose ``from`` end takes an ``H`` whose
  ``H.code`` starts with "OK" (the mapping grid's sources, view ``Vsrc``). Candidates (0.9 K7): ``Bcand`` H→K many-to-many whose ``to`` end takes a
  ``K`` whose ``K.code`` starts with "OK"; ``Banc`` R→D many-to-many whose ``from`` end takes an ``R``
  with ``R.b`` true and whose ``to`` end a ``D`` under a ``G`` whose name contains "reserved" (any
  case).
- Views: ``Vrt`` a relationships table over ``Bnn`` (0.13 RV: ``from:name`` and ``Bnn.weight``
  filters, four sorts, grouped by ``H``), ``Bassoc`` carries ``Bnn.weight`` and ``Bnn.note`` too (the matrix ``Massoc``);
  ``Vnn`` a relationship view (``mappingGrid``) over ``Bnn``, read from ``H``; ``Vcand`` over
  ``Bcand``; the matrix ``Mcand`` over ``Banc`` (R rows, G columns, D cells).
- ``Capi``: a consumer API exposing ``R``, ``R2`` and ``D`` (generated only): the ``id`` role,
  ``code`` (``R2.u``, then ``R.u``), ``name``, ``active`` (``R.b``, default true), ``R.n`` (default
  50) and ``R.dt``, ``parent``, ``path`` and ``hierarchy``; projections ``B11`` outgoing (one),
  ``Bown`` outgoing with ``ancestor:G.name`` (many) and ``Bscope`` outgoing (many, also showing ``relation:Bscope.flag`` and ``relation:Bscope.note``, and matched by
  ``relation:Bscope.note`` in the filters ``label``, ``score`` (scoring and crosswalk) and ``flag``, and in the XREF rule at 55); the lists
  ``all`` (``R``, sorted by ``R.n``), ``entries`` (``R2`` under ``R``), ``permits`` (``D`` under
  ``G``), and ``rates`` and ``fees`` over ``E`` (dated) and ``F`` (not), also exposed (J23, C16); the parameters ``container`` (``ancestor``, ``M`` by name), ``permit`` (``projection``
  over ``Bown`` by ``ancestor:G.name``, ``requireMatch``, ``targetable``), ``token`` (``related``, ``K`` by name
  through ``B11``), ``peer`` (``related``, ``R`` by name through ``self`` and the shared
  ``Bscope``), ``kind`` (``objectType``) and ``watch`` (``projection`` over ``Bscope`` by
  ``ancestor:G.name``, ``scoresFrom``, ``targetable``); a ``match`` (J29): own ``id`` 1000, ``R.u`` and
  ``R2.u`` 500/40, ``name`` 200/30, promoted over ``B11`` (``K.code`` 80, ``name`` 75, ``K.code``
  contains 10) and over ``Bscope`` (``name`` 60, preferring ``R2``). Its API key, list keys, public
  names, output names and parameter names are ``Capi.…`` keys.
"""

import json
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Any

STARTER = Path(__file__).resolve().parents[3] / "model" / "rdm-starter.json"


@dataclass(frozen=True)
class Configuration:
    name: str
    model: dict[str, Any]
    keys: dict[str, str]
    # Structures the configuration holds beyond its keys (a shape, not a key), e.g. "M".
    shapes: frozenset[str] = field(default_factory=frozenset)

    def holds(self, structures: tuple[str, ...]) -> bool:
        return all(item in self.keys or item in self.shapes for item in structures)

    def key(self, structure: str) -> str:
        return self.keys[structure]


# --- generated -----------------------------------------------------------------------------------


def _naming(variant: str) -> dict[str, str]:
    """The keys of one generated configuration: A in kebab case, B in another style entirely."""
    a = {
        "A1": "atlas",
        "A2": "harbour",
        "R": "ledger",
        "H": "branch",
        "P": "estate",
        "Q": "venue",
        "C": "room",
        "C2": "shelf",
        "K": "token",
        "G": "region",
        "M": "zone",
        "D": "permit",
        "D2": "clause",
        "L1": "tier-one",
        "L2": "tier-two",
        "L3": "tier-three",
        "R.u": "ledger-number",
        "R.n": "score",
        "R.b": "flagged",
        "R.dt": "opened-on",
        "R.q": "owner-name",
        "R.ro": "origin",
        "R.x1": "summary",
        "R.x2": "remark",
        "H.code": "branch-code",
        "H.rank": "position",
        "K.code": "token-code",
        "K.rank": "weight-class",
        "D.active": "in-force",
        "L.code": "tier-code",
        "L.extra": "tier-extra",
        "L.only1": "tier-note",
        "Bnn.weight": "strength",
        "Bnn.note": "comment",
        "Bscope.flag": "is-primary",
        "Bscope.note": "local-label",
        "B11": "ledger-pairs-token",
        "B1n": "ledger-lists-token",
        "Bnn": "branch-cites-token",
        "Bown": "ledger-holds-permit",
        "Bscope": "ledger-watches-permit",
        "Ll2k": "tier-uses-token",
        "Ll1k": "tier-cites-token",
        "A3": "lens",
        "N": "notice",
        "Bh1n": "branch-orders-token",
        "Bh1n.qty": "quantity",
        "Breq": "branch-needs-notice",
        "Bsk": "branch-guards-room",
        "Bassoc": "ledger-notes-permit",
        "Brev": "permit-cites-ledger",
        "Vnnr": "token-branch-links",
        "V2": "branch-token-orders",
        "Mown": "permits-by-region",
        "Massoc": "notes-by-region",
        "Mrev": "citations-by-region",
        "Bone": "ledger-pins-permit",
        "Mscope": "watches-by-region",
        "Mone": "pins-by-region",
        "V": "article",
        "V.code": "article-code",
        "V.rank": "article-rank",
        "V.amount": "article-amount",
        "V.flag": "article-flag",
        "V.on": "article-date",
        "V.at": "article-stamp",
        "Bvk": "article-cites-token",
        "E": "tariff",
        "E.from": "tariff-from",
        "E.to": "tariff-to",
        "F": "season",
        "R2": "entry",
        "R2.u": "entry-number",
        "Bee": "tariff-follows-tariff",
        "Vnn": "branch-token-links",
        "Bn1": "branch-grades-token",
        "Bcand": "branch-picks-token",
        "Banc": "ledger-reserves-permit",
        "Vcand": "branch-token-picks",
        "Bsrc": "branch-lists-token",
        "Vsrc": "branch-token-lists",
        "Mcand": "reserves-by-region",
        "Vrt": "branch-token-rows",
    }
    if variant == "a":
        return a
    return {structure: "x_" + key.replace("-", "_") + "_7" for structure, key in a.items()}


def generated(variant: str) -> Configuration:
    k = _naming(variant)
    deep_scope = variant == "b"
    containment: list[tuple[str, str, str]] = []  # (relation key, parent type, child type)

    def attribute(structure: str, value_type: str = "text", **extra: Any) -> dict[str, Any]:
        return {"key": k[structure], "name": structure, "valueType": value_type, **extra}

    searchable = {"searchable": True, "filterable": True, "sortable": True}
    attribute_types = [
        attribute("R.u", features={**searchable, "unique": True}),
        attribute(
            "R.n",
            "integer",
            features={"filterable": True, "sortable": True},
            validation={"minimum": 0, "maximum": 100},
        ),
        attribute("R.b", "boolean", features={"filterable": True}),
        attribute("R.dt", "date", features={"filterable": True, "sortable": True}),
        attribute("R.q", features={"searchable": True}),
        attribute("R.ro", default="imported"),
        attribute("R.x1", "longText"),
        attribute("R.x2", "longText"),
        attribute("H.code", features=searchable),
        attribute("H.rank", "integer", features={"filterable": True, "sortable": True}),
        attribute("K.code", features=searchable),
        attribute("K.rank", "integer", features={"filterable": True, "sortable": True}),
        attribute("D.active", "boolean", default=True, features={"filterable": True}),
        attribute("L.code", features=searchable),
        attribute("L.extra"),
        attribute("L.only1"),
        attribute("Bh1n.qty", "integer"),
        attribute("V.code", features={**searchable, "unique": True}),
        attribute("V.rank", "integer", features={"filterable": True, "sortable": True}),
        attribute("V.amount", "decimal", features={"filterable": True, "sortable": True}),
        attribute("V.flag", "boolean", features={"filterable": True}),
        attribute("V.on", "date", features={"filterable": True, "sortable": True}),
        attribute("V.at", "dateTime", features={"filterable": True, "sortable": True}),
        attribute("E.from", "date", features={"filterable": True, "sortable": True}),
        attribute("E.to", "date", features={"filterable": True, "sortable": True}),
        attribute("R2.u", features={**searchable, "unique": True}),
        attribute(
            "Bnn.weight",
            "integer",
            validation={"minimum": 1},
            features={"filterable": True, "sortable": True},
        ),
        attribute("Bnn.note", features={"filterable": True, "sortable": True}),
        attribute("Bscope.flag", "boolean"),
        attribute("Bscope.note"),
    ]

    def binding(structure: str, order: int, **extra: Any) -> dict[str, Any]:
        return {"attributeTypeKey": k[structure], "order": order, **extra}

    def object_type(
        structure: str,
        display: str,
        attributes: list[dict[str, Any]],
        *,
        root: bool,
        parents: tuple[str, ...] = (),
        **extra: Any,
    ) -> dict[str, Any]:
        item = {
            "key": k[structure],
            "name": structure,
            "pluralName": f"{structure}s",
            "displayAttributeTypeKey": k[display],
            "attributes": attributes,
            "features": {"rootCreatable": root},
            **extra,
        }
        if parents:
            relations = []
            for parent in parents:
                relation = f"{k[parent]}--holds--{k[structure]}"
                containment.append((relation, parent, structure))
                relations.append(relation)
            item["behavior"] = {"parentRelationTypeKeys": relations}
        return item

    l_attributes = [binding("L.code", 10, required=True)]
    d_parent = ("M",) if deep_scope else ("G", "M")
    object_types = [
        object_type(
            "R",
            "R.u",
            [
                binding("R.u", 10, required=True),
                binding("R.n", 20),
                binding("R.b", 30),
                binding("R.dt", 40),
                binding("R.q", 50, required=True),
                binding("R.ro", 60, readOnly=True),
                binding("R.x1", 70),
                binding("R.x2", 80),
            ],
            root=True,
            validation={"atLeastOneOf": [k["R.x1"], k["R.x2"]]},
        ),
        object_type(
            "H",
            "H.code",
            [binding("H.code", 10, required=True), binding("H.rank", 20)],
            root=True,
            parents=("H",),
        ),
        object_type("P", "H.code", [binding("H.code", 10)], root=True),
        object_type("Q", "H.code", [binding("H.code", 10)], root=True),
        object_type("C", "H.code", [binding("H.code", 10)], root=False, parents=("P", "Q")),
        object_type("C2", "H.code", [binding("H.code", 10)], root=False, parents=("C",)),
        object_type(
            "K", "K.code", [binding("K.code", 10, required=True), binding("K.rank", 20)], root=True
        ),
        object_type("G", "K.code", [binding("K.code", 10, required=True)], root=True),
        object_type(
            "D",
            "K.code",
            [binding("K.code", 10), binding("D.active", 20)],
            root=False,
            parents=d_parent,
        ),
        object_type("D2", "K.code", [binding("K.code", 10)], root=False, parents=("D",)),
        object_type("N", "K.code", [binding("K.code", 10, required=True)], root=True),
        object_type(
            "V",
            "V.code",
            [
                binding(f"V.{name}", order)
                for order, name in enumerate(
                    ("code", "rank", "amount", "flag", "on", "at"), start=1
                )
            ],
            root=True,
            parents=("V",),
        ),
        object_type(
            "E",
            "K.code",
            [binding("K.code", 10), binding("E.from", 20), binding("E.to", 30)],
            root=True,
            effectivePeriod={
                "startAttributeTypeKey": k["E.from"],
                "endAttributeTypeKey": k["E.to"],
            },
        ),
        object_type(
            "F",
            "K.code",
            [binding("K.code", 10), binding("E.from", 20), binding("E.to", 30)],
            root=True,
        ),
        # R2.u is optional, so a consumer field reading it first can meet empty text (J28).
        object_type(
            "R2",
            "R2.u",
            [binding("R2.u", 10), binding("R.u", 20)],
            root=False,
            parents=("R",),
        ),
        object_type("L1", "L.code", [*l_attributes, binding("L.only1", 20)], root=True),
        object_type(
            "L2",
            "L.code",
            [*l_attributes, binding("L.extra", 20, required=True)],
            root=False,
            parents=("L1",),
        ),
        object_type("L3", "L.code", l_attributes, root=False, parents=("L2", "L3")),
    ]
    object_types.append(
        object_type("M", "K.code", [binding("K.code", 10)], root=False, parents=("G",))
    )

    def relation_type(key: str, **features: bool) -> dict[str, Any]:
        return {
            "key": key,
            "reverseKey": f"{key}--rev",
            "name": f"{key} forward",
            "reverseName": f"{key} reverse",
            "features": features,
        }

    scope = {
        "uniqueToAncestorTypeKey": k["G"],
        "uniqueWhenToAttributeEquals": {"attributeTypeKey": k["D.active"], "value": True},
    }
    relation_types = [
        relation_type(key, parentOf=True, hierarchical=parent == child)
        for key, parent, child in containment
    ]
    relation_types += [
        relation_type(k[name], searchable=True)
        for name in (
            "B11",
            "B1n",
            "Bn1",
            "Bnn",
            "Bown",
            "Bscope",
            "Ll2k",
            "Ll1k",
            "Bh1n",
            "Breq",
            "Bsk",
            "Bassoc",
            "Bone",
            "Brev",
            "Bvk",
            "Bee",
            "Bcand",
            "Bsrc",
            "Banc",
        )
    ]
    allowed = [
        {
            "relationTypeKey": key,
            "fromObjectTypeKey": k[parent],
            "toObjectTypeKey": k[child],
            "cardinality": "one-to-many",
        }
        for key, parent, child in containment
    ] + [
        {
            "relationTypeKey": k["B11"],
            "fromObjectTypeKey": k["R"],
            "toObjectTypeKey": k["K"],
            "cardinality": "one-to-one",
        },
        {
            "relationTypeKey": k["B1n"],
            "fromObjectTypeKey": k["R"],
            "toObjectTypeKey": k["K"],
            "cardinality": "one-to-many",
        },
        {
            "relationTypeKey": k["Bn1"],
            "fromObjectTypeKey": k["H"],
            "toObjectTypeKey": k["K"],
            "cardinality": "many-to-one",
        },
        {
            "relationTypeKey": k["Bnn"],
            "fromObjectTypeKey": k["H"],
            "toObjectTypeKey": k["K"],
            "cardinality": "many-to-many",
            "attributeTypeKeys": [k["Bnn.weight"], k["Bnn.note"]],
        },
        {
            "relationTypeKey": k["Bown"],
            "fromObjectTypeKey": k["R"],
            "toObjectTypeKey": k["D"],
            "cardinality": "one-to-many",
            "required": True,
            "features": scope,
        },
        # Which records may be chosen (0.9 K7): a K by its code, a D by its G's name, an R by a flag.
        {
            "relationTypeKey": k["Bcand"],
            "fromObjectTypeKey": k["H"],
            "toObjectTypeKey": k["K"],
            "cardinality": "many-to-many",
            "candidates": {"to": [{"field": k["K.code"], "op": "startsWith", "value": "OK"}]},
        },
        {
            "relationTypeKey": k["Bsrc"],
            "fromObjectTypeKey": k["H"],
            "toObjectTypeKey": k["K"],
            "cardinality": "many-to-many",
            "candidates": {"from": [{"field": k["H.code"], "op": "startsWith", "value": "OK"}]},
        },
        {
            "relationTypeKey": k["Banc"],
            "fromObjectTypeKey": k["R"],
            "toObjectTypeKey": k["D"],
            "cardinality": "many-to-many",
            "candidates": {
                "from": [{"field": k["R.b"], "op": "eq", "value": True}],
                "to": [{"field": f"ancestor:{k['G']}.name", "op": "contains", "value": "reserved"}],
            },
        },
        {
            "relationTypeKey": k["Bscope"],
            "fromObjectTypeKey": k["R"],
            "toObjectTypeKey": k["D"],
            "cardinality": "many-to-many",
            "features": scope,
            "attributeTypeKeys": [k["Bscope.flag"], k["Bscope.note"]],
        },
        # An R2 may watch a D too, so a D can relate to an R and an R2 (J29.1, preferTargetTypes).
        {
            "relationTypeKey": k["Bscope"],
            "fromObjectTypeKey": k["R2"],
            "toObjectTypeKey": k["D"],
            "cardinality": "many-to-many",
        },
        {
            "relationTypeKey": k["Ll2k"],
            "fromObjectTypeKey": k["L2"],
            "toObjectTypeKey": k["K"],
            "cardinality": "many-to-many",
        },
        {
            "relationTypeKey": k["Ll1k"],
            "fromObjectTypeKey": k["L1"],
            "toObjectTypeKey": k["K"],
            "cardinality": "many-to-many",
        },
        {
            "relationTypeKey": k["Bh1n"],
            "fromObjectTypeKey": k["H"],
            "toObjectTypeKey": k["K"],
            "cardinality": "one-to-many",
            "attributeTypeKeys": [k["Bh1n.qty"]],
        },
        # Required and not owning: every N record needs one, and no H record owns it.
        {
            "relationTypeKey": k["Breq"],
            "fromObjectTypeKey": k["H"],
            "toObjectTypeKey": k["N"],
            "cardinality": "many-to-many",
            "required": True,
        },
        # Unique per H within a P ancestor of the room; a room under Q has none.
        {
            "relationTypeKey": k["Bsk"],
            "fromObjectTypeKey": k["H"],
            "toObjectTypeKey": k["C"],
            "cardinality": "many-to-many",
            "features": {"uniqueToAncestorTypeKey": k["P"]},
        },
        {
            "relationTypeKey": k["Bassoc"],
            "fromObjectTypeKey": k["R"],
            "toObjectTypeKey": k["D"],
            "cardinality": "many-to-many",
            "attributeTypeKeys": [k["Bnn.weight"], k["Bnn.note"]],
        },
        {
            "relationTypeKey": k["Bone"],
            "fromObjectTypeKey": k["R"],
            "toObjectTypeKey": k["D"],
            "cardinality": "one-to-one",
        },
        {
            "relationTypeKey": k["Brev"],
            "fromObjectTypeKey": k["D"],
            "toObjectTypeKey": k["R"],
            "cardinality": "many-to-many",
        },
        {
            "relationTypeKey": k["Bvk"],
            "fromObjectTypeKey": k["V"],
            "toObjectTypeKey": k["K"],
            "cardinality": "many-to-many",
        },
        {
            "relationTypeKey": k["Bee"],
            "fromObjectTypeKey": k["E"],
            "toObjectTypeKey": k["E"],
            "cardinality": "many-to-many",
        },
    ]
    keys = dict(k)
    keys["Hparent"] = next(key for key, parent, child in containment if parent == child == "H")

    # B splits the types across the applications differently from A; H and K, R and D, and L2 and K
    # are in different applications in both.
    if deep_scope:
        first = ["H", "P", "Q", "C", "C2", "L1", "L2", "L3", "G", "M", "D", "D2", "V", "E", "F"]
        second = ["R", "K", "N", "R2"]
    else:
        first = ["R", "H", "P", "Q", "C", "C2", "L1", "L2", "L3", "V", "E", "F", "R2"]
        second = ["K", "G", "M", "D", "D2", "N"]
    types = {item["key"]: item for item in object_types}

    def table(structure: str) -> dict[str, Any]:
        display = types[k[structure]]["displayAttributeTypeKey"]
        return {
            "key": f"{k[structure]}--list",
            "name": f"{structure} list",
            "type": "table",
            "objectTypeKey": k[structure],
            "config": {
                "columns": ["name", display],
                # R's list also filters by the permits it is related to (J54: a relationship
                # filter, including under an ancestor).
                "filterFields": [display, f"related:{k['Bassoc']}"]
                if structure == "R"
                else [display],
                "sortFields": ["name", display],
                "defaultSort": "name",
                "pageSize": 20,
            },
        }

    def application(structure: str, members: list[str]) -> dict[str, Any]:
        views = [table(member) for member in members]
        return {
            "key": k[structure],
            "name": structure,
            "objectTypeKeys": [k[m] for m in members],
            "defaultView": views[0]["key"],
            "views": views,
        }

    applications = [application("A1", first), application("A2", second)]
    h_application = applications[0]
    h_application["views"].append(
        {
            "key": k["Vnn"],
            "name": "Vnn",
            "type": "mappingGrid",
            "config": {
                "relationTypeKey": k["Bnn"],
                "fromObjectTypeKey": k["H"],
                "toObjectTypeKey": k["K"],
                "direction": "outgoing",
                "sourceColumns": ["name", k["H.code"]],
                "targetDisplayColumns": ["name", k["K.code"]],
                "candidateSearchFields": ["name", k["K.code"]],
                "pageSize": 20,
            },
        }
    )
    # A relationships table over Bnn (0.13 RV): both ends, the relationship's own values, rows
    # headed by their H record.
    h_application["views"].append(
        {
            "key": k["Vrt"],
            "name": "Vrt",
            "type": "relationTable",
            "config": {
                "relationTypeKey": k["Bnn"],
                "fromObjectTypeKey": k["H"],
                "toObjectTypeKey": k["K"],
                "fromColumns": ["name", k["H.code"]],
                "toColumns": ["name", k["K.code"]],
                "attributeColumns": [k["Bnn.weight"], k["Bnn.note"]],
                "filterFields": ["from:name", f"relation:{k['Bnn.weight']}"],
                "sortFields": [
                    "from:name",
                    "to:name",
                    f"relation:{k['Bnn.weight']}",
                    f"relation:{k['Bnn.note']}",
                ],
                "defaultSort": "from:name",
                "groupBy": "from",
                "pageSize": 20,
            },
        }
    )
    second_application = applications[1]

    def mapping(structure: str, relation: str, source: str, target: str, direction: str):
        return {
            "key": k[structure],
            "name": structure,
            "type": "mappingGrid",
            "config": {
                "relationTypeKey": k[relation],
                "fromObjectTypeKey": k[source],
                "toObjectTypeKey": k[target],
                "direction": direction,
                "sourceColumns": ["name", k["H.code" if direction == "outgoing" else "K.code"]],
                "targetDisplayColumns": [
                    "name",
                    k["K.code" if direction == "outgoing" else "H.code"],
                ],
                "candidateSearchFields": [
                    "name",
                    k["K.code" if direction == "outgoing" else "H.code"],
                ],
                "pageSize": 20,
            },
        }

    h_application["views"].append(mapping("V2", "Bh1n", "H", "K", "outgoing"))
    h_application["views"].append(mapping("Vcand", "Bcand", "H", "K", "outgoing"))
    h_application["views"].append(mapping("Vsrc", "Bsrc", "H", "K", "outgoing"))
    second_application["views"].append(mapping("Vnnr", "Bnn", "H", "K", "incoming"))

    # A3 lists records the other applications own: relation matrices of R rows, G columns, D cells.
    lens_types = ["R", "G", "M", "D"]

    def matrix(structure: str, relation: str, direction: str, actions: list[str]):
        return {
            "key": k[structure],
            "name": structure,
            "type": "relationMatrix",
            "config": {
                "relationTypeKey": k[relation],
                "direction": direction,
                "rowObjectTypeKey": k["R"],
                "columnObjectTypeKey": k["G"],
                "cellObjectTypeKey": k["D"],
                "rowColumns": ["name", k["R.u"]],
                "columnLabelField": k["K.code"],
                "cellFields": [k["K.code"], k["D.active"]],
                "searchFields": ["name", k["R.u"]],
                "cellActions": actions,
                "pageSize": 20,
            },
        }

    lens = application("A3", lens_types)
    lens["views"] += [
        matrix("Mown", "Bown", "outgoing", ["create", "edit"]),
        matrix("Massoc", "Bassoc", "outgoing", ["link", "unlink", "edit"]),
        matrix("Mrev", "Brev", "incoming", ["link", "unlink"]),
        matrix("Mscope", "Bscope", "outgoing", ["link", "unlink"]),
        matrix("Mone", "Bone", "outgoing", ["link", "unlink"]),
        matrix("Mcand", "Banc", "outgoing", ["link", "unlink"]),
    ]
    applications.append(lens)
    model = {
        "schemaVersion": "0.10",
        "release": {
            "key": f"journeys-{variant}",
            "name": f"Journey model {variant.upper()}",
            "version": "1.0.0",
        },
        "product": {
            "name": f"Journey model {variant.upper()}",
            "description": "Generated for the journey tests (H4c)",
        },
        "attributeTypes": attribute_types,
        "objectTypes": object_types,
        "relationTypes": relation_types,
        "objectTypeRelations": allowed,
        "applications": applications,
        "consumerApis": [_consumer_api(variant, k)],
    }
    keys.update(_consumer_names(variant))
    return Configuration(
        f"generated-{variant}", model, keys, frozenset({"deep-scope"} if deep_scope else set())
    )


def _consumer_names(variant: str) -> dict[str, str]:
    """``Capi``'s API key, public names and output names: chosen by each configuration, as a
    definition's author chooses them."""
    a = {
        "Capi": "ledger-api",
        "Capi.R": "Ledger",
        "Capi.R2": "Entry",
        "Capi.id": "ledgerId",
        "Capi.code": "code",
        "Capi.name": "name",
        "Capi.active": "isActive",
        "Capi.n": "score",
        "Capi.dt": "openedOn",
        "Capi.parent": "parent",
        "Capi.path": "path",
        "Capi.hierarchy": "hierarchy",
        "Capi.B11": "pairedToken",
        "Capi.B11.name": "tokenName",
        "Capi.B11.code": "tokenCode",
        "Capi.Bown": "permits",
        "Capi.Bown.name": "permitName",
        "Capi.Bown.G": "regionName",
        "Capi.D": "Permit",
        "Capi.Bscope": "watchedPermits",
        "Capi.Bscope.name": "watchedName",
        "Capi.Bscope.flag": "isPrimary",
        "Capi.Bscope.note": "localLabel",
        "Capi.all": "ledgers",
        "Capi.entries": "entries",
        "Capi.entries.parent": "ledger",
        "Capi.permits": "permit-list",
        "Capi.permits.parent": "region",
        "Capi.container": "zone",
        "Capi.permit": "permitRegion",
        "Capi.token": "token",
        "Capi.peer": "peer",
        "Capi.kind": "kind",
        "Capi.watch": "watchRegion",
        "Capi.label": "pairLabel",
        "Capi.score": "pairScore",
        "Capi.flag": "pairFlag",
        "Capi.E": "Rate",
        "Capi.F": "Fee",
        "Capi.rates": "rates",
        "Capi.fees": "fees",
    }
    if variant == "a":
        return a
    # The API key and list keys appear in URLs, so B spells them in lowercase and hyphens too.
    in_url = {"Capi", "Capi.all", "Capi.entries", "Capi.permits", "Capi.rates", "Capi.fees"}
    return {
        structure: (
            ("x7-registry" if structure == "Capi" else f"x7-{name}")
            if structure in in_url
            else f"x_{name}_7"
        )
        for structure, name in a.items()
    }


def _consumer_api(variant: str, k: dict[str, str]) -> dict[str, Any]:
    """``Capi``: a consumer API exposing R, R2 and D, with lists and filters (J28), and E and F, one
    dated and one not (J23)."""
    n = _consumer_names(variant)
    return {
        "key": n["Capi"],
        "name": "Capi",
        "contractVersion": 1,
        "exposes": [k["R"], k["R2"], k["D"], k["E"], k["F"]],
        "publicNames": {
            k["R"]: n["Capi.R"],
            k["R2"]: n["Capi.R2"],
            k["D"]: n["Capi.D"],
            k["E"]: n["Capi.E"],
            k["F"]: n["Capi.F"],
        },
        "object": {
            "fields": {
                n["Capi.id"]: {"role": "id"},
                n["Capi.code"]: {"role": "code", "from": [k["R2.u"], k["R.u"]]},
                n["Capi.name"]: {"role": "name", "from": "name"},
                n["Capi.active"]: {"role": "active", "from": k["R.b"], "default": True},
                n["Capi.n"]: {"from": k["R.n"], "default": 50},
                n["Capi.dt"]: k["R.dt"],
            },
            "parent": {"output": n["Capi.parent"], "fields": ["objectType", "id", "code", "name"]},
            "path": n["Capi.path"],
            "hierarchy": n["Capi.hierarchy"],
            "related": {
                n["Capi.B11"]: {
                    "via": k["B11"],
                    "fields": {n["Capi.B11.name"]: "name", n["Capi.B11.code"]: k["K.code"]},
                },
                n["Capi.Bown"]: {
                    "via": k["Bown"],
                    "fields": {
                        n["Capi.Bown.name"]: "name",
                        n["Capi.Bown.G"]: f"ancestor:{k['G']}.name",
                    },
                },
                n["Capi.Bscope"]: {
                    "via": k["Bscope"],
                    "fields": {
                        n["Capi.Bscope.name"]: "name",
                        n["Capi.Bscope.flag"]: f"relation:{k['Bscope.flag']}",
                        n["Capi.Bscope.note"]: f"relation:{k['Bscope.note']}",
                    },
                },
            },
        },
        "operations": {
            "objects": {},
            "xref": {
                "matchOn": [
                    {"field": "id", "exact": 1000},
                    {"field": k["R.u"], "exact": 500, "contains": 40},
                    {"field": k["R2.u"], "exact": 500, "contains": 40},
                    {"field": "name", "exact": 200, "contains": 30},
                ],
                "alsoMatchThrough": [
                    {
                        "related": n["Capi.B11"],
                        "firstOf": [
                            {"field": k["K.code"], "exact": 80},
                            {"field": "name", "exact": 75},
                            {"field": k["K.code"], "contains": 10},
                        ],
                    },
                    {
                        "related": n["Capi.Bscope"],
                        "firstOf": [
                            {"field": "name", "exact": 60},
                            {"field": f"relation:{k['Bscope.note']}", "exact": 55},
                        ],
                        "preferTypes": [k["R2"]],
                    },
                ],
            },
            "resolve": {},
            "lists": {
                n["Capi.all"]: {"of": k["R"], "sortBy": k["R.n"]},
                n["Capi.entries"]: {
                    "of": k["R2"],
                    "within": {"filter": n["Capi.entries.parent"], "types": [k["R"]]},
                },
                n["Capi.permits"]: {
                    "of": k["D"],
                    "within": {"filter": n["Capi.permits.parent"], "types": [k["G"]]},
                },
                n["Capi.rates"]: {"of": k["E"]},
                n["Capi.fees"]: {"of": k["F"]},
            },
        },
        "filters": {
            n["Capi.container"]: {"under": [k["M"]], "matchOn": ["name"]},
            n["Capi.permit"]: {
                "onRelated": n["Capi.Bown"],
                "matchOn": [f"ancestor:{k['G']}.name"],
                "keepOnlyMatching": True,
                "crosswalk": True,
            },
            n["Capi.token"]: {"linkedTo": [k["K"]], "through": [n["Capi.B11"]], "matchOn": ["name"]},
            n["Capi.peer"]: {
                "linkedTo": [k["R"]],
                "through": ["itself", f"sharedWith:{n['Capi.Bscope']}"],
                "matchOn": ["name"],
            },
            n["Capi.kind"]: {"byType": True},
            n["Capi.watch"]: {
                "onRelated": n["Capi.Bscope"],
                "matchOn": [f"ancestor:{k['G']}.name"],
                "scoreOnlyMatching": True,
                "crosswalk": True,
            },
            # Matches the relationship's own text value, so an item counts through that relationship.
            n["Capi.label"]: {
                "onRelated": n["Capi.Bscope"],
                "matchOn": [f"relation:{k['Bscope.note']}"],
                "keepOnlyMatching": True,
            },
            # The same text, scoring and crosswalking only through the matching relationship.
            n["Capi.score"]: {
                "onRelated": n["Capi.Bscope"],
                "matchOn": [f"relation:{k['Bscope.note']}"],
                "scoreOnlyMatching": True,
                "crosswalk": True,
            },
            # A boolean relationship attribute, compared by its canonical form.
            n["Capi.flag"]: {
                "onRelated": n["Capi.Bscope"],
                "matchOn": [f"relation:{k['Bscope.flag']}"],
                "keepOnlyMatching": True,
            },
        },
    }


# --- the example model ---------------------------------------------------------------------------


def example() -> Configuration:
    """The starter model: the structures it holds, by their starter keys."""
    keys = {
        "A1": "rdm-master",
        "A2": "rdm-translations",
        "R": "domain",
        "R.u": "domain-code",
        "R.b": "active",
        "G": "language",
        "M": "translation-group",
        "D": "translation",
        "D.active": "active",
        "Bown": "object-has-translation",
    }
    return Configuration(
        "example", json.loads(STARTER.read_text()), keys, frozenset({"deep-scope"})
    )


def parity() -> Configuration:
    """The starter extended as the reference deployment's model is, with CONSUMER_API's definition
    ("Definition shape") written out: the parity fixture (C8). ``Capi`` is its key, so the consumer
    helpers of ``scenario`` read it."""
    model = json.loads(STARTER.read_text())
    model["release"] = {**model["release"], "key": "rdm-parity", "name": "Consumer API parity fixture"}
    model["attributeTypes"] += [
        {"key": "operator-code", "name": "Operator code", "features": {"searchable": True}},
        {"key": "internal-only", "name": "Internal only", "valueType": "boolean"},
    ]
    master_value = next(item for item in model["objectTypes"] if item["key"] == "master-value")
    master_value["attributes"].append({"attributeTypeKey": "internal-only", "order": 90})
    model["objectTypes"].append(
        {
            "key": "location",
            "name": "Location",
            "pluralName": "Locations",
            "attributes": [
                {"attributeTypeKey": "master-id", "required": True, "order": 10},
                {"attributeTypeKey": "value-code", "order": 20},
                {"attributeTypeKey": "value-name", "order": 30},
                {"attributeTypeKey": "operator-code", "order": 40},
                {"attributeTypeKey": "active", "order": 50},
            ],
            "features": {"rootCreatable": False},
            "behavior": {"parentRelationTypeKeys": ["codelist-contains-location"]},
        }
    )
    model["relationTypes"] += [
        {
            "key": "codelist-contains-location",
            "reverseKey": "location-belongs-to-codelist",
            "name": "Contains location",
            "reverseName": "Belongs to codelist",
            "features": {"parentOf": True},
        },
        {
            "key": "available-at-location",
            "reverseKey": "location-offers",
            "name": "Available at",
            "reverseName": "Offers",
            "features": {"searchable": True},
        },
        {
            "key": "has-duration",
            "reverseKey": "duration-of",
            "name": "Has duration",
            "reverseName": "Duration of",
            "features": {"searchable": True},
        },
        {
            "key": "alternative-for",
            "reverseKey": "has-alternative",
            "name": "Alternative for",
            "reverseName": "Has alternative",
            "features": {"searchable": True},
        },
    ]
    model["objectTypeRelations"] += [
        {
            "relationTypeKey": "codelist-contains-location",
            "fromObjectTypeKey": "codelist",
            "toObjectTypeKey": "location",
            "cardinality": "one-to-many",
        },
        {
            "relationTypeKey": "available-at-location",
            "fromObjectTypeKey": "master-value",
            "toObjectTypeKey": "location",
            "cardinality": "many-to-many",
        },
        {
            "relationTypeKey": "has-duration",
            "fromObjectTypeKey": "master-value",
            "toObjectTypeKey": "master-value",
            "cardinality": "many-to-many",
        },
        # One slot type per value: the reference's alternative is an object or null.
        {
            "relationTypeKey": "alternative-for",
            "fromObjectTypeKey": "master-value",
            "toObjectTypeKey": "master-value",
            "cardinality": "one-to-one",
        },
        {
            "relationTypeKey": "system-value-maps-to-master",
            "fromObjectTypeKey": "system-value",
            "toObjectTypeKey": "location",
            "cardinality": "many-to-many",
        },
    ]
    master = next(item for item in model["applications"] if item["key"] == "rdm-master")
    master["objectTypeKeys"].append("location")
    model["consumerApis"] = [_reference_definition()]
    return Configuration("parity", model, {"Capi": "rdm"})


def _reference_definition() -> dict[str, Any]:
    """CONSUMER_API "Definition shape", its ``…`` written out: ``domain`` exposed, the ``values`` and
    ``all-values`` lists, ``alternative`` with the related record's ``objectType`` (C-D73) and
    ``duration`` as the reference object has them, ``language`` crosswalked to a translation, and its
    event (C9)."""
    return {
        "key": "rdm",
        "name": "RDM consumer API",
        "contractVersion": 1,
        "exposes": ["master-value", "codelist", "domain", "location"],
        "publicNames": {"master-value": "CodelistValue"},
        "object": {
            "fields": {
                "masterId": {"role": "id"},
                "code": {"role": "code", "from": ["operator-code", "value-code", "codelist-code", "domain-code"]},
                "name": {"role": "name", "from": "name"},
                "isActive": {"role": "active", "from": "active", "default": True},
                "validFrom": {"role": "validFrom", "from": "valid-from"},
                "validTo": {"role": "validTo", "from": "valid-to"},
                "formerId": "master-id",
                "valueName": "value-name",
                "sortOrder": {"from": "sort-order", "default": 0},
                "internalOnly": {"from": "internal-only", "default": False},
                "description": "description",
            },
            "parent": ["objectType", "id", "code", "name"],
            "path": True,
            "hierarchy": True,
            "related": {
                "systemVariants": {
                    "via": "master-value-represented-by-system-value",
                    "fields": {
                        "system": "ancestor:system.name",
                        "value": "name",
                        "valueCode": "value-code",
                        "valueName": "value-name",
                        "externalId": "external-id",
                        "isActive": "active",
                    },
                },
                "translations": {
                    "via": "object-has-translation",
                    "fields": {
                        "languageCode": "ancestor:language.language-code",
                        "languageName": "ancestor:language.name",
                        "translatedName": "translated-name",
                        "translatedDescription": "translated-description",
                        "isActive": "active",
                    },
                },
                "availableAt": {
                    "via": "available-at-location",
                    "fields": {
                        "locationId": "master-id",
                        "locationName": "name",
                        "locationValueCode": "value-code",
                        "locationValueName": "value-name",
                    },
                },
                "duration": {
                    "via": "has-duration",
                    "fields": {"durationId": "id", "durationCode": "value-code", "durationName": "name"},
                },
                "alternative": {
                    "via": "alternative-for",
                    "fields": {"objectType": "objectType", "masterId": "id", "code": "value-code", "name": "name"},
                },
            },
        },
        "operations": {
            "objects": {},
            "xref": {
                "matchOn": [
                    {"field": "master-id", "exact": 1000},
                    {"field": "value-code", "exact": 500, "contains": 40},
                    {"field": "operator-code", "exact": 500, "contains": 40},
                    {"field": "name", "exact": 200, "contains": 30},
                    {"field": "value-name", "exact": 200, "contains": 30},
                ],
                "alsoMatchThrough": [
                    {
                        "related": "systemVariants",
                        "firstOf": [
                            {"field": "name", "exact": 80},
                            {"field": "value-code", "exact": 70},
                            {"field": "external-id", "exact": 75},
                            {"field": "value-name", "exact": 75},
                            {"field": "name", "contains": 15},
                            {"field": "value-code", "contains": 10},
                            {"field": "external-id", "contains": 10},
                            {"field": "value-name", "contains": 10},
                        ],
                        "preferTypes": ["location"],
                    },
                    {
                        "related": "translations",
                        "firstOf": [
                            {"field": "translated-name", "exact": 60},
                            {"field": "translated-name", "contains": 12},
                        ],
                    },
                ],
            },
            "resolve": {},
            "lists": {
                "codelists": {"of": "codelist", "within": {"filter": "domain"}},
                "values": {"of": "master-value", "within": {"filter": "codelist"}},
                "all-values": {"of": "master-value"},
            },
            # CONSUMER_API "Event definitions": watched outputs by the names consumers read (C-D81).
            "events": {
                "custom": [
                    {
                        "key": "reference-data-changed",
                        "objectTypes": ["master-value", "codelist", "location"],
                        "changes": ["created", "updated", "deleted"],
                        "watch": {
                            "fields": ["masterId", "code", "name", "isActive", "validFrom", "validTo", "valueName"],
                            "related": ["systemVariants", "translations"],
                        },
                    }
                ]
            },
        },
        "filters": {
            "type": {"byType": True},
            "system": {
                "onRelated": "systemVariants",
                "matchOn": ["ancestor:system.name", "ancestor:system.system-code"],
                "keepOnlyMatching": True,
                "scoreOnlyMatching": True,
                "crosswalk": True,
            },
            "codelist": {"under": ["codelist"], "matchOn": ["name", "codelist-code"]},
            "domain": {"under": ["domain"], "matchOn": ["name", "domain-code"]},
            "location": {
                "linkedTo": ["location"],
                "through": ["availableAt", "itself", "sharedWith:systemVariants"],
                "matchOn": ["master-id", "name", "value-code", "value-name"],
            },
            "language": {
                "onRelated": "translations",
                "matchOn": ["ancestor:language.language-code"],
                "keepOnlyMatching": True,
                "crosswalk": True,
            },
        },
    }


@cache
def all_configurations() -> dict[str, Configuration]:
    items = [generated("a"), generated("b"), example()]
    return {item.name: item for item in items}


def application_of(configuration: Configuration, structure: str) -> str:
    """The application holding a type, from the model."""
    key = configuration.key(structure)
    for item in configuration.model["applications"]:
        if key in item["objectTypeKeys"]:
            return item["key"]
    raise KeyError(structure)


def choose(structures: tuple[str, ...]) -> list[Configuration]:
    """Generated A, and the example where it holds every structure, otherwise generated B."""
    configurations = all_configurations()
    second = configurations["example"]
    if not structures or not second.holds(structures):
        second = configurations["generated-b"]
    return [configurations["generated-a"], second]
