"""The rules' reading of a workbook against a workspace (Product 0.16 AP6a, AP-D12 to AP-D16).

The tables of the file are those the profile gives (a sheet, a sheet's main block, a list of a sheet
laid out for reading: ``reading.file_layout``); a block of a header with no rows below it is a title,
shown apart. Before the rules read anything, a stored import profile that fits the file is followed
(``profile_reading``); the tables it does not cover, and every table when none fits, are read by the
rules (``reading``): for each table the columns' distinct texts that are the keys or names of each
type's stored records are counted in PostgreSQL, and a table whose best (type, column) holds at
least half of its column's distinct texts is **an update of that type**, matched by that column;
otherwise it is new data. A sheet with no table is not data.
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...models.database import SourceFile, SourceFileSheet
from ...models.schema import EngineModel
from . import profile_reading, reading
from .catalog import type_infos


def read_workbook(
    session: Session, source: SourceFile, workspace: str, model: EngineModel
) -> dict[str, Any]:
    """The profiled file as the task's reading: its tables, its titles, its sheets that are no
    table, the profile followed, and the summary."""
    types = type_infos(model)
    layout = reading.file_layout(session, source)
    fitted = profile_reading.fit(session, source, model, layout.tables)
    followed = {id(item): (index, entry) for index, entry, item in fitted.sources} if fitted else {}
    tables: list[dict[str, Any]] = []
    covered: set[int] = set()
    for number, item in enumerate(layout.tables, 1):
        covered.add(item.sheet_index)
        if fitted is not None and id(item) in followed:
            index, entry = followed[id(item)]
            tables.append(
                profile_reading.table_of(
                    session, source.id, workspace, types, number, fitted, index, entry, item
                )
            )
            continue
        table = reading.base_table(number, item)
        distinct, found = reading.overlap_rows(session, source.id, item, workspace, types)
        letters = {c.number: c.letter for c in item.columns}
        table["distinct"] = {letters[n]: count for n, count in distinct.items()}
        table["overlaps"] = found
        best = reading.best_key(table, types)
        if best is None:
            table["reason"] = "New data"
            table["evidence"] = reading.NEW_DATA
            table["choices"]["load"] = {"value": False, "owner": "rules"}
        else:
            reading.as_update(
                session, source.id, workspace, types, table, best["objectTypeKey"], best
            )
        tables.append(table)
    sheets = []
    for index, name in session.execute(
        select(SourceFileSheet.sheet_index, SourceFileSheet.name)
        .where(SourceFileSheet.source_file_id == source.id)
        .order_by(SourceFileSheet.sheet_index)
    ):
        if index not in covered:
            sheets.append(
                {
                    "sheet": name,
                    "rows": reading.rows_of_sheet(session, source.id, index),
                    "as": "notData",
                    "reason": reading.NOT_DATA,
                }
            )
    found_reading: dict[str, Any] = {
        "tables": tables,
        "sheets": sheets,
        "titles": layout.titles,
        "profile": None,
        "profileMaps": {},
    }
    if fitted is not None:
        found_reading["profile"] = {
            "key": fitted.profile.key,
            "name": fitted.profile.name,
            "version": fitted.profile.version,
            "sources": len(fitted.definition.sources),
        }
        found_reading["profileMaps"] = dict(fitted.definition.valueMaps)
    reading.finish(found_reading)
    return found_reading
