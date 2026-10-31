"""The assistant designs how a workbook lives in the engine (Product 0.16 AP6, the user's five cases).

The language model designs and the engine carries the design out and checks it. A design turn sends
the person's words, the workbook profiled over every row, the rules' reading of each table, the
workspace's model in short (applications, types with their parents, attributes and relationships)
and what the workspace holds. The answer holds:

- ``modelOperations``: model-draft operations (MODEL_AUTHORING § Operation catalogue), applied to the
  task's draft of the workspace's model all or none, as the editor applies them;
- ``records``: the records the structure needs that no row gives (a domain, a list, a language, a
  system), loaded from sheets the engine adds to the task's working copy of the workbook;
- ``profile``: the import profile that loads the workbook's sheets (API.md § Import profiles),
  checked against the draft's model;
- ``questions``: only what the data cannot answer, each with its choices and the one assumed;
- ``reads``: what the assistant wants to see first.

Whatever the engine refuses goes back with its reason on the next turn; an answer that only repeats
a refusal ends the turns. The design is done when the assistant says so and the draft compiles and
the profile holds against it.
"""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

DESIGN_VERSION = "workbook-design/13"
# Records one query read returns; cells the data sheets of one design may hold.
QUERY_LIMIT = 500
SHEET_CELLS = 20_000

_API = Path(__file__).resolve().parents[4] / "docs" / "API.md"

class DataSheet(BaseModel):
    """A sheet the assistant writes into the working copy: rows the workbook does not hold in a
    shape the profile can load (a translation per record and language, a pair of IDs), loaded by a
    source of the profile like any sheet."""

    name: str = Field(min_length=1, max_length=31)
    columns: list[str] = Field(min_length=1)
    rows: list[list[Any]] = []


class RecordParent(BaseModel):
    objectTypeKey: str
    name: str


class StructureRecord(BaseModel):
    ref: str
    objectTypeKey: str
    applicationKey: str | None = None
    name: str
    attributes: dict[str, Any] = {}
    parent: RecordParent | None = None


class Question(BaseModel):
    text: str = Field(max_length=500)
    options: list[str] = []
    assumed: str | None = None


class LeftOut(BaseModel):
    """Why a column of the workbook no source loads is left out."""

    sheet: str
    column: str
    reason: str = Field(min_length=1, max_length=300)


class Derived(BaseModel):
    """A sheet a read-only query derives from the workbook's cells: the assistant describes the
    reshaping, PostgreSQL gives every row."""

    name: str = Field(min_length=1, max_length=31)
    sheets: list[str] = []
    sql: str = Field(min_length=1, max_length=20000)


def model_brief(
    model: dict[str, Any],
    held: dict[str, int],
    base: dict[str, Any] | None = None,
    *,
    attributes_of: set[str | None] | None = None,
) -> dict[str, Any]:
    """The model as the assistant designs against it: no views, no layouts. With ``base``, the
    release the draft was opened from, what the draft added is marked ``"new": true``: the
    assistant's own changes so far, not the workspace's model. With ``attributes_of``, only those
    types list their attributes (a model too large for the window)."""

    def keys(name: str) -> set[str]:
        return {item["key"] for item in (base or {}).get(name) or []}

    known = {name: keys(name) for name in ("applications", "objectTypes", "relationTypes")}

    def new(name: str, key: str) -> dict[str, bool]:
        return {"new": True} if base is not None and key not in known[name] else {}

    relations = model.get("relationTypes") or []
    bindings = model.get("objectTypeRelations") or []
    containment = {r["key"] for r in relations if (r.get("features") or {}).get("parentOf")}
    attributes = {a["key"]: a for a in model.get("attributeTypes") or []}
    applications = model.get("applications") or []
    app_of: dict[str, list[str]] = {}
    for app in applications:
        for type_key in app.get("objectTypeKeys") or []:
            app_of.setdefault(type_key, []).append(app["key"])
    types = []
    for item in model.get("objectTypes") or []:
        key = item["key"]
        parents = sorted(
            {
                b["fromObjectTypeKey"]
                for b in bindings
                if b["toObjectTypeKey"] == key and b["relationTypeKey"] in containment
            }
        )
        types.append(
            {
                "key": key,
                **new("objectTypes", key),
                "name": item.get("name"),
                "applications": app_of.get(key, []),
                "parents": parents,
                "parentRelationTypes": (item.get("behavior") or {}).get(
                    "parentRelationTypeKeys", []
                ),
                "top": bool((item.get("features") or {}).get("rootCreatable", not parents)),
                "attributes": []
                if attributes_of is not None and key not in attributes_of
                else [
                    {
                        "key": a["attributeTypeKey"],
                        "valueType": (attributes.get(a["attributeTypeKey"]) or {}).get("valueType"),
                        **(
                            {"unique": True}
                            if (
                                (attributes.get(a["attributeTypeKey"]) or {}).get("features") or {}
                            ).get("unique")
                            else {}
                        ),
                        **({"required": True} if a.get("required") else {}),
                    }
                    for a in item.get("attributes") or []
                ],
                **({"rules": item["validation"]} if item.get("validation") else {}),
                "records": held.get(key, 0),
            }
        )
    return {
        "applications": [
            {
                "key": a["key"],
                **new("applications", a["key"]),
                "name": a.get("name"),
                "types": a.get("objectTypeKeys") or [],
            }
            for a in applications
        ],
        "objectTypes": types,
        "attributeTypes": sorted(attributes),
        "relationTypes": [
            {
                "key": r["key"],
                **new("relationTypes", r["key"]),
                "name": r.get("name"),
                "reverseKey": r.get("reverseKey"),
                **({"containment": True} if r["key"] in containment else {}),
                "joins": [
                    {
                        "from": b["fromObjectTypeKey"],
                        "to": b["toObjectTypeKey"],
                        "cardinality": b.get("cardinality"),
                        **({"required": True} if b.get("required") else {}),
                        **({"features": b["features"]} if b.get("features") else {}),
                    }
                    for b in bindings
                    if b["relationTypeKey"] == r["key"]
                ],
            }
            for r in relations
        ],
    }
