"""The engine's checks of a proposed model, for any workbook (Product 0.16 AP6r).

A design can load cleanly and still not be the model a steward browses: a new type of records the
workspace already holds, a column that groups the rows loaded as a plain value, a relationship only
one end shows, translations left out. Each check reads the workbook's staged cells and the stored
records in PostgreSQL (no row comes into Python) and the draft's model, and names what it found;
the assistant fixes it or explains it (``explains``), and the steward sees both. No check knows a
file, a sheet or a name: they are the same for every workbook.

Each check is ``{id, kind, text, open, explanation?}``; ``open`` is whether the design still
leaves it as found and the assistant has not explained it.
"""

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from .reading import LAST_ROW

# A column is checked for reuse when at least this share of its distinct values are stored names.
REUSE_SHARE = 0.5
# A column "groups the rows" when it has between 2 and this share of its rows as distinct values.
GROUPING_SHARE = 0.34
# At most this many checks of a kind go out: a wide workbook stays readable and in the window.
PER_KIND = 12

_STORED_NAMES = text(
    """
WITH v AS (
    SELECT column_number AS c, lower(btrim(text)) AS t FROM source_file_cells
    WHERE source_file_id = :file AND sheet_index = :sheet AND row_number > :header
      AND row_number <= :last AND row_number <> :note AND column_number = ANY(:columns)
      AND btrim(text) <> ''
    GROUP BY 1, 2),
d AS (SELECT c, count(*) AS n FROM v GROUP BY 1)
SELECT v.c, o.object_type_key, count(DISTINCT v.t) AS matched, d.n
FROM v JOIN d ON d.c = v.c
JOIN objects o ON o.workspace_key = :workspace AND lower(o.name) = v.t
GROUP BY v.c, o.object_type_key, d.n
"""
)

_SPREAD = text(
    """
SELECT column_number, count(DISTINCT btrim(text)), count(*) FROM source_file_cells
WHERE source_file_id = :file AND sheet_index = :sheet AND row_number > :header
  AND row_number <= :last AND row_number <> :note AND column_number = ANY(:columns)
  AND btrim(text) <> ''
GROUP BY 1
"""
)


def _bindings(profile: dict[str, Any] | None) -> dict[str, dict[str, dict[str, Any]]]:
    """Each sheet's column bindings across the profile's sources, by header."""
    found: dict[str, dict[str, dict[str, Any]]] = {}
    for source in (profile or {}).get("sources") or []:
        sheet = found.setdefault(source.get("sheet") or "", {})
        for column in source.get("columns") or []:
            if "column" not in column:
                # Named by its letter (0.13 AQ) or a set of flag columns: no header to key it by.
                continue
            if column.get("ignore"):
                sheet.setdefault(column["column"], {"ignore": True})
            else:
                sheet[column["column"]] = column
        # A source that loads the type itself by this column reuses its records.
        key = source.get("key") or {}
        if key.get("column"):
            sheet.setdefault(key["column"], {"self": source.get("objectTypeKey")})
    return found


def _targets(binding: dict[str, Any] | None, source_type: str | None = None) -> set[str]:
    """The types a column's binding reaches: its parent, relation, related record or own type."""
    if not binding:
        return set()
    reached = {
        (binding.get(part) or {}).get("objectTypeKey")
        for part in ("parent", "relation", "relatedRecord")
    }
    if binding.get("field") == "name" and source_type:
        reached.add(source_type)
    if binding.get("self"):
        reached.add(binding["self"])
    return {key for key in reached if key}


def _type_of_sheet_name_column(profile: dict[str, Any] | None) -> dict[tuple[str, str], str]:
    """For each (sheet, header) a source binds as the name, the type that source loads."""
    found: dict[tuple[str, str], str] = {}
    for source in (profile or {}).get("sources") or []:
        for column in source.get("columns") or []:
            if column.get("field") == "name" and "column" in column:
                found[(source.get("sheet") or "", column["column"])] = source.get("objectTypeKey")
    return found


def run(
    session: Session,
    *,
    task_reading: dict[str, Any] | None,
    file_id: int | None,
    workspace: str,
    profile: dict[str, Any] | None,
    model: dict[str, Any],
    base: dict[str, Any] | None,
    explains: dict[str, str],
) -> list[dict[str, Any]]:
    """The checks of the design as it stands."""
    found: list[dict[str, Any]] = []
    names = {t["key"]: t.get("name") or t["key"] for t in model.get("objectTypes") or []}
    stored_types = {t["key"] for t in (base or {}).get("objectTypes") or []}
    bound = _bindings(profile)
    named_by = _type_of_sheet_name_column(profile)

    def add(kind: str, ident: str, words: str, still: bool) -> None:
        if sum(1 for c in found if c["kind"] == kind) >= PER_KIND:
            return
        explanation = explains.get(ident)
        found.append(
            {
                "id": ident,
                "kind": kind,
                "text": words,
                "open": still and not explanation,
                **({"explanation": explanation} if explanation else {}),
            }
        )

    for table in (task_reading or {}).get("tables", []) if file_id else []:
        place = table.get("place") or {}
        columns = {c["number"]: c for c in table.get("columns") or [] if c.get("header")}
        if not columns or "sheetIndex" not in place:
            continue
        sheet = table.get("sheet") or ""
        parameters = {
            "file": file_id,
            "sheet": place["sheetIndex"],
            "header": place.get("headerRow") or 1,
            "last": place.get("lastRow") or LAST_ROW,
            "note": place.get("note") or 0,
            "columns": list(columns),
            "workspace": workspace,
        }
        on_sheet = bound.get(sheet, {})
        # Reuse: a column whose values are, for the most part, records the workspace holds.
        for number, type_key, matched, distinct in session.execute(_STORED_NAMES, parameters):
            if type_key not in stored_types or distinct < 2 or matched < REUSE_SHARE * distinct:
                continue
            header = columns[number]["header"]
            reached = _targets(on_sheet.get(header), named_by.get((sheet, header)))
            add(
                "reuse",
                f"reuse:{sheet}:{header}:{type_key}",
                f"Column “{header}” ({sheet}) names {matched} of {distinct} values the workspace "
                f"holds as {names.get(type_key, type_key)}: link those records, not new ones",
                type_key not in reached,
            )
        # Grouping: a column with few distinct values over many rows, loaded as a plain value.
        for number, distinct, rows in session.execute(_SPREAD, parameters):
            header = columns[number]["header"]
            binding = on_sheet.get(header) or {}
            if (
                rows < 4
                or distinct < 2
                or distinct > GROUPING_SHARE * rows
                or columns[number].get("valueType") not in (None, "text")
                or not binding.get("attributeTypeKey")
            ):
                continue
            add(
                "grouping",
                f"grouping:{sheet}:{header}",
                f"Column “{header}” ({sheet}) has {distinct} values over {rows} rows and is loaded "
                "as a plain value: it groups the rows — a type they sit under or are related to?",
                True,
            )
        # Translations: a column the rules read as a translation that the design does not load.
        for column in columns.values():
            if column.get("kind") != "relatedRecord":
                continue
            binding = on_sheet.get(column["header"]) or {}
            add(
                "translations",
                f"translations:{sheet}:{column['header']}",
                f"Column “{column['header']}” ({sheet}) holds a translation and is not loaded as one",
                not binding.get("relatedRecord"),
            )

    # Both ends: a relationship the draft allows that no page of its "to" type shows.
    held = {
        (b.get("relationTypeKey"), b.get("fromObjectTypeKey"), b.get("toObjectTypeKey"))
        for b in (base or {}).get("objectTypeRelations") or []
    }
    # A parent's containment is shown by the page's children panel, not by a relations panel.
    containment = {
        key
        for t in model.get("objectTypes") or []
        for key in (t.get("behavior") or {}).get("parentRelationTypeKeys") or []
    }
    related_records = {
        (column.get("relatedRecord") or {}).get("objectTypeKey")
        for source in (profile or {}).get("sources") or []
        for column in source.get("columns") or []
    }
    shown: dict[str, set[str]] = {}
    for application in model.get("applications") or []:
        for detail in application.get("details") or []:
            for panel in detail.get("panels") or []:
                config = panel.get("config") or {}
                if panel.get("type") == "relations" and config.get("direction") == "incoming":
                    shown.setdefault(detail.get("objectTypeKey"), set()).update(
                        config.get("relationTypeKeys") or []
                    )
    for binding in model.get("objectTypeRelations") or []:
        identity = (
            binding.get("relationTypeKey"),
            binding.get("fromObjectTypeKey"),
            binding.get("toObjectTypeKey"),
        )
        relation, source_type, target_type = identity
        if identity in held or relation in containment or target_type in related_records:
            continue
        add(
            "bothEnds",
            f"bothEnds:{relation}:{source_type}:{target_type}",
            f"“{relation}” from {names.get(source_type, source_type)} to "
            f"{names.get(target_type, target_type)}: no {names.get(target_type, target_type)} "
            "page shows it",
            relation not in shown.get(target_type, set()),
        )
    return found
