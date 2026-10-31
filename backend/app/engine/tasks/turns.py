"""What the assistant's design reads of a workbook (Product 0.16 AP6, AP-D5, AP-D26).

The design (``design_job.py``) sends the assistant the rules' reading of each table
(:func:`reading_brief`): the sheet, what it was read as, the key column and the columns with their
bindings; the tables nothing needs the person for go in a line each. The assistant asks for at most
``design.MAX_READS`` reads, which the engine answers (:func:`answer_read`): a sheet's cells by range,
a column's distinct values, a type's stored records by a word. A read that cannot be answered is
returned as an error, never raised.

What a dry run refused is counted by :func:`job.checked` with at most :data:`REFUSED_VALUES` cell
values per code and column.
"""

from typing import Any

CELL_ROWS = 50
VALUE_LIMIT = 200
RECORD_LIMIT = 20
# The cell values of one refusal the check keeps.
REFUSED_VALUES = 20


def reading_brief(tables: list[dict[str, Any]], compact: frozenset[str] = frozenset()) -> list[Any]:
    """Each table as the assistant sees the rules' reading of it; the tables of ``compact`` (those
    nothing needs the person for) in a line."""
    shown: list[Any] = []
    for t in tables:
        if t["table"] in compact:
            by = f" by column {t['keyColumn']}" if t["keyColumn"] else ""
            followed = f" (profile {t['profile']['name']})" if t.get("profile") else ""
            shown.append(
                f"{t['table']} '{t['sheet']}': an update of {t['objectTypeKey']}{by}, "
                f"{t['matched']} match, nothing to decide{followed}"
            )
            continue
        shown.append(
            {
                "table": t["table"],
                "sheet": t["sheet"],
                "as": t["as"],
                "objectTypeKey": t["objectTypeKey"],
                "reason": t["reason"],
                "evidence": t["evidence"],
                "profile": (t.get("profile") or {}).get("name"),
                "keyColumn": t["keyColumn"],
                "keyOptions": [
                    {"column": o["column"], "header": o["header"], "matched": o["matched"]}
                    for o in t["keyOptions"]
                ],
                "matched": t["matched"],
                "new": t["new"],
                "missing": t["missing"],
                "attention": t.get("attention", []),
                "columns": [
                    {"column": c["column"], "header": c["header"], "binding": c["binding"]}
                    for c in t["columns"]
                ],
            }
        )
    return shown


# --- the reads the engine answers -----------------------------------------------------------------
