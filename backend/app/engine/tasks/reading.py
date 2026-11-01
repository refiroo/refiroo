"""The rules' reading of a workbook against a workspace (Product 0.16 AP6a, AP-D12 to AP-D16).

The tables of the file are those the profile gives (a sheet, a sheet's main block, a list of a sheet
laid out for reading: ``sources/inference/facts``). For each table the reading counts, in
PostgreSQL over the staged cells and the workspace's live data, how many of each column's distinct
texts are the keys or names of each type's stored records. A table whose best (type, column) holds
at least half of the column's distinct texts is **an update of that type**, matched by that column;
otherwise it is new data. Nothing is read row by row through Python: the figures are set statements.

A table is a plain dictionary (it is stored as the task's ``reading`` and shown as it is, apart from
the keys that begin with an underscore or sit in ``INTERNAL``): ``place`` says where it stands in
the file, ``overlaps`` holds every (column, type, key) the file matched, so a different key or type
is chosen without reading the workspace again.
"""

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from ...models.database import SourceFile, SourceFileSheet
from ..sources.inference.facts import BlockTable, Column, StagedTable, staged_workbook
from . import placement, translations
from .catalog import TypeInfo, Types, kind_of, label_of, normal, type_infos
from .sql import FILE_KEYS, LAST_ROW, attribute_of, parameters_of, stored_query

__all__ = [
    "FILE_KEYS",
    "FileTable",
    "TypeInfo",
    "Types",
    "normal",
    "parameters_of",
    "stored_query",
    "type_infos",
]

NOT_DATA = "No table: notes for people"
NEW_DATA = (
    "Nothing in it matches a type's records; a new kind of thing needs a model extension, which "
    "this version cannot do yet"
)
LEFT_OUT = (
    "'{header}' is a column {type} does not have. Adding it is a model extension, which this "
    "version cannot do yet; it is left out of this load"
)
# The keys of a table the API does not show.
NO_PARENT = (
    "New rows have no place to go: {type} records stand under a parent, the stored ones do not share "
    "one and nothing in the file names one, so new keys are left out of this load by default"
)
INTERNAL = ("place", "overlaps", "distinct", "profileSource")


@dataclass
class FileTable:
    """A table of the file as the profile gives it, with its columns' statistics."""

    sheet: str
    sheet_index: int
    header_row: int
    last_row: int | None
    rows: int
    block: dict[str, Any] | None
    list_index: int | None
    columns: list[Column]
    titles: tuple[str, ...] = ()
    # The list's note or second header row: ``{row, text, meaning}`` (D119, D144).
    note: dict[str, Any] | None = None

    @property
    def name(self) -> str:
        return self.sheet

    def range(self) -> str:
        first = min(self.columns, key=lambda c: c.number).letter
        last = max(self.columns, key=lambda c: c.number).letter
        return f"{first}{self.header_row}:{last}{self.last_row or self.header_row + self.rows}"


@dataclass
class Layout:
    """The tables of the file, and its blocks of a header with no rows below it (``titles``: sheet,
    range and the header's words)."""

    tables: list[FileTable]
    titles: list[dict[str, str]]


def file_layout(session: Session, source: SourceFile) -> Layout:
    workbook = staged_workbook(session, source)
    blocks: dict[int, list[dict[str, Any]]] = {
        index: (profile or {}).get("blocks") or []
        for index, profile in session.execute(
            select(SourceFileSheet.sheet_index, SourceFileSheet.profile).where(
                SourceFileSheet.source_file_id == source.id
            )
        )
    }
    found: list[FileTable] = []
    titles: list[dict[str, str]] = []

    def title(name: str, where: str, columns: list[Column]) -> None:
        titles.append(
            {
                "sheet": name,
                "range": where,
                "text": " · ".join(c.header for c in sorted(columns, key=lambda c: c.number)),
            }
        )

    for sheet in workbook.sheets:
        if not isinstance(sheet, StagedTable) or not sheet.columns:
            continue
        block = next(
            (b for b in blocks.get(sheet.index, []) if b.get("headerRow") == sheet.header_row), {}
        )
        if not sheet.rows:
            title(sheet.name, block.get("range", f"A{sheet.header_row}"), sheet.columns)
            continue
        found.append(
            FileTable(
                sheet.name,
                sheet.index,
                sheet.header_row,
                None,
                sheet.rows,
                sheet.block,
                None,
                list(sheet.columns),
                (),
                block.get("note"),
            )
        )
    for item in workbook.blocks:
        if not isinstance(item, BlockTable) or not item.columns:
            continue
        if not item.rows:
            title(item.name, item.range, item.columns)
            continue
        found.append(
            FileTable(
                item.name,
                item.sheet_index,
                item.header_row,
                item.last_row,
                item.rows,
                {
                    "firstColumn": item.first_column,
                    "lastColumn": item.last_column,
                    "lastRow": item.last_row,
                },
                item.block,
                list(item.columns),
                item.titles,
                item.note,
            )
        )
    found.sort(key=lambda item: (item.sheet_index, item.list_index or 0))
    return Layout(found, titles)


def file_tables(session: Session, source: SourceFile) -> list[FileTable]:
    return file_layout(session, source).tables


def place_of(item: FileTable) -> dict[str, Any]:
    return {
        "sheetIndex": item.sheet_index,
        "headerRow": item.header_row,
        "lastRow": item.last_row,
        "block": item.block,
        "note": item.note["row"] if item.note else 0,
        "noteText": item.note["text"] if item.note else None,
    }


_OVERLAPS = """
WITH v AS (
    SELECT column_number AS c, text AS t FROM source_file_cells
    WHERE source_file_id = :file AND sheet_index = :sheet AND row_number > :header
      AND row_number <= :last AND row_number <> :note AND column_number = ANY(:columns)
      AND btrim(text) <> ''
    GROUP BY 1, 2),
k AS (
    SELECT o.object_type_key AS type_key, '' AS attr, o.name AS t FROM objects o
    WHERE o.workspace_key = :workspace AND o.object_type_key = ANY(:types)
    UNION ALL
    SELECT o.object_type_key, a.attribute_type_key, a.text_value FROM attribute_values a
    JOIN objects o ON o.id = a.object_id
    WHERE o.workspace_key = :workspace AND o.object_type_key = ANY(:types)
      AND a.attribute_type_key = ANY(:attributes) AND a.text_value IS NOT NULL)
SELECT v.c, k.type_key, k.attr, count(DISTINCT v.t) FROM v JOIN k ON k.t = v.t
GROUP BY 1, 2, 3
"""

_DISTINCT = """
SELECT column_number, count(DISTINCT text) FROM source_file_cells
WHERE source_file_id = :file AND sheet_index = :sheet AND row_number > :header
  AND row_number <= :last AND row_number <> :note AND column_number = ANY(:columns)
  AND btrim(text) <> ''
GROUP BY 1
"""


def overlap_rows(
    session: Session, file_id: int, item: FileTable, workspace: str, types: dict[str, TypeInfo]
) -> tuple[dict[int, int], list[dict[str, Any]]]:
    """Each column's distinct texts, and for each (column, type, key) the distinct texts that are
    the key of one of the type's stored records in the workspace."""
    parameters = {
        "file": file_id,
        "sheet": item.sheet_index,
        "header": item.header_row,
        "last": item.last_row or LAST_ROW,
        "note": item.note["row"] if item.note else 0,
        "columns": [c.number for c in item.columns],
    }
    distinct = dict(session.execute(text(_DISTINCT), parameters).all())
    attributes = sorted({key for info in types.values() for key, _ in info.unique})
    letters = {c.number: c for c in item.columns}
    found = [
        {
            "column": letters[column].letter,
            "header": letters[column].header,
            "objectTypeKey": type_key,
            "key": {"attributeTypeKey": attr} if attr else {"field": "name"},
            "matched": matched,
        }
        for column, type_key, attr, matched in session.execute(
            text(_OVERLAPS),
            {
                **parameters,
                "workspace": workspace,
                "types": sorted(types),
                "attributes": attributes,
            },
        ).all()
    ]
    return distinct, found


def order_of(entry: dict[str, Any]) -> tuple[int, int, str]:
    return (-entry["matched"], 0 if "attributeTypeKey" in entry["key"] else 1, entry["column"])


def base_table(number: int, item: FileTable) -> dict[str, Any]:
    return {
        "table": f"t{number}",
        "sheet": item.sheet,
        "range": item.range(),
        "list": item.list_index,
        "rows": item.rows,
        "as": "newData",
        "objectTypeKey": None,
        "applicationKey": None,
        "parentTypeKeys": [],
        "typeName": None,
        "reason": "",
        "evidence": "",
        "owner": "rules",
        "origin": None,
        "profile": None,
        "keyColumn": None,
        "key": None,
        "keyOptions": [],
        "matched": 0,
        "new": 0,
        "missing": 0,
        "namesDiffer": 0,
        "meaning": [],
        "parent": None,
        "notes": [],
        "attention": [],
        "leftOut": [],
        "columns": [
            {
                "column": c.letter,
                "number": c.number,
                "header": c.header,
                "binding": None,
                "kind": None,
                "label": "",
                "leftOut": None,
                "owner": "rules",
                "valueType": c.value_type(),
            }
            for c in item.columns
        ],
        "choices": {
            "newRecords": {"value": "create", "owner": "rules"},
            "names": {"value": "file", "owner": "rules"},
            "missing": {"value": "leave", "owner": "rules"},
            "load": {"value": True, "owner": "rules"},
        },
        "place": place_of(item),
        "titles": list(item.titles),
        "overlaps": [],
        "distinct": {},
    }


def best_key(table: dict[str, Any], types: dict[str, TypeInfo]) -> dict[str, Any] | None:
    """The (column, type, key) holding the most of its column's distinct texts, at least half."""
    candidates = [
        entry
        for entry in table["overlaps"]
        if entry["objectTypeKey"] in types
        and entry["matched"] > 0
        and entry["matched"] * 2 >= table["distinct"].get(entry["column"], 0)
    ]
    return min(candidates, key=order_of) if candidates else None


def key_options(table: dict[str, Any], type_key: str) -> list[dict[str, Any]]:
    return sorted(
        (
            {k: v for k, v in entry.items() if k not in ("objectTypeKey", "given")}
            for entry in table["overlaps"]
            if entry["objectTypeKey"] == type_key and (entry["matched"] > 0 or entry.get("given"))
        ),
        key=order_of,
    )


def as_update(
    session: Session,
    file_id: int,
    workspace: str,
    types: Types,
    table: dict[str, Any],
    type_key: str,
    option: dict[str, Any],
) -> None:
    """Read ``table`` as an update of ``type_key`` matched by ``option`` (one of its key options):
    the bindings of its columns, the counts of keys matched, new, missing and names that differ, and
    where its rows stand in the model's hierarchy. The person's and the assistant's marks on columns
    stay; a table that followed a stored profile is read by the rules from here."""
    info = types[type_key]
    if table.get("profile") is not None:
        table["profile"] = None
        table["profileSource"] = None
        table["reason"] = ""
        for column in table["columns"]:
            if column["owner"] == "profile":
                column["owner"] = "rules"
    columns = {c["column"]: c for c in table["columns"]}
    key_column = columns[option["column"]]
    by_attribute = "attributeTypeKey" in option["key"]
    name_column = None
    if by_attribute:
        name_column = _name_column(table, info, key_column["column"])
    bound = {normal(label): key for key, label, _ in info.writable} | {
        normal(key): key for key, _, _ in info.writable
    }
    for column in table["columns"]:
        if column["owner"] != "rules":
            continue
        column["leftOut"] = None
        column.pop("evidence", None)
        if column is key_column:
            column["binding"] = dict(option["key"])
        elif column is name_column:
            column["binding"] = {"field": "name"}
        elif (attribute := bound.get(normal(column["header"]))) is not None and not (
            by_attribute and attribute == option["key"]["attributeTypeKey"]
        ):
            column["binding"] = {"attributeTypeKey": attribute}
        else:
            column["binding"] = None
            column["leftOut"] = LEFT_OUT.format(header=column["header"], type=info.label)
    translations.apply(session, workspace, info, table["columns"])
    for column in table["columns"]:
        column["kind"] = kind_of(column["binding"])
        column["label"] = label_of(types, column["binding"])
    figures = counts(
        session,
        file_id,
        table["place"],
        workspace,
        type_key,
        key_column["number"],
        option["key"],
        name_column["number"] if name_column else None,
    )
    kind = "names" if not by_attribute else _label(info, option["key"]["attributeTypeKey"]).lower()
    table.update(
        {
            "as": "update",
            "objectTypeKey": type_key,
            "applicationKey": info.application,
            "parentTypeKeys": list(info.parents),
            "typeName": info.label,
            "keyColumn": key_column["column"],
            "key": dict(option["key"]),
            "keyOptions": key_options(table, type_key),
            "matched": figures["matched"],
            "new": figures["distinct"] - figures["matched"],
            "missing": figures["missing"],
            "namesDiffer": figures["differ"],
            "reason": f"An update of {info.plural}"
            if figures["matched"]
            else f"New records of {info.plural}",
            # What the key column holds, for ``evidence`` (stored, not answered).
            "keyKind": kind,
        }
    )
    place_rows(session, file_id, workspace, types, table, info)
    table["evidence"] = evidence(table)


def place_rows(
    session: Session,
    file_id: int,
    workspace: str,
    types: Types,
    table: dict[str, Any],
    info: TypeInfo,
) -> None:
    """Where the table's rows stand (``placement``): the source's fixed parent, or that new rows
    cannot be placed, in which case they are left out unless the person chose otherwise."""
    columns = {c["column"]: c for c in table["columns"]}
    name_column = next(
        (
            c["number"]
            for c in table["columns"]
            if c["binding"] == {"field": "name"} and c["column"] != table["keyColumn"]
        ),
        None,
    )
    found = placement.choose(
        session,
        workspace,
        types,
        info,
        file_id,
        table["place"],
        columns[table["keyColumn"]]["number"],
        table["key"],
        name_column,
        [*table.get("titles", ()), table["sheet"]],
    )
    table["parent"] = found.parent
    table["noParent"] = not found.placed
    table["notes"] = [] if found.placed else [NO_PARENT.format(type=info.label)]
    new = table["choices"]["newRecords"]
    if new["owner"] == "rules":
        table["choices"]["newRecords"] = {
            "value": "create" if found.placed else "leaveOut",
            "owner": "rules",
        }


def _count(number: int, one: str, many: str) -> str:
    return f"{number} {one if number == 1 else many}"


def evidence(table: dict[str, Any]) -> str:
    """An update table's evidence from its figures as they are now: written again whenever they
    change (the key chosen, the matches by meaning), so the sentence and the choices agree."""
    header = next(
        (c["header"] for c in table["columns"] if c["column"] == table["keyColumn"]),
        table["keyColumn"],
    )
    wanted = table["key"].get("attributeTypeKeys")
    if wanted:
        # AP-D43: the key is the values of several columns together.
        header = "' + '".join(
            c["header"]
            for attribute in wanted
            for c in table["columns"]
            if c["binding"] == {"attributeTypeKey": attribute}
        )
    meant = len(table.get("meaning") or [])
    distinct = table["matched"] + table["new"] + meant
    if table["key"].get("field") == "name":
        kind = "names"
    else:
        # The attribute's label as the rules found it, unless the key has since moved off it.
        kind = table.get("keyKind") if table.get("keyKind") not in (None, "names") else "keys"
    if table["matched"] == 0 and not meant:
        # A table of records not stored yet: its key column is the assistant's or the person's.
        parts = [
            (
                f"No stored record has one of the {distinct} {kind} in its '{header}' column: "
                "every row is a new record."
            )
        ]
    else:
        parts = [
            f"Its '{header}' column holds the records' {kind}: {table['matched']} of {distinct} match."
        ]
    if meant:
        parts.append(
            f"{_count(meant, 'row is', 'rows are')} spelled differently but "
            f"{'means' if meant == 1 else 'mean'} a stored record."
        )
    if table["new"] and (table["matched"] or meant):
        parts.append(f"{_count(table['new'], 'key is', 'keys are')} new.")
    if table["namesDiffer"]:
        parts.append(
            f"{_count(table['namesDiffer'], 'name differs', 'names differ')} from the stored ones."
        )
    if table["missing"]:
        parts.append(
            f"{_count(table['missing'], 'stored record is', 'stored records are')} not in the file."
        )
    parent = table.get("parent")
    if parent is not None and parent.get("source") == placement.SHARED:
        parts.append(f"Its records sit under “{parent['value']}”; new rows go there too.")
    elif parent is not None and parent.get("source") == placement.TITLED:
        parts.append(f"Its title or sheet names “{parent['value']}”; new rows go under it.")
    elif parent is not None and parent.get("source") == placement.PROFILE:
        parts.append(f"The profile puts its rows under “{parent['value']}”.")
    return " ".join(parts)


def _label(info: TypeInfo, attribute: str) -> str:
    return next((label for key, label in info.unique if key == attribute), attribute)


def _name_column(table: dict[str, Any], info: TypeInfo, key_letter: str) -> dict[str, Any] | None:
    """The column holding the records' names: the one matching most stored names, else a header
    equal to Name or the type's label."""
    named = [
        entry
        for entry in table["overlaps"]
        if entry["objectTypeKey"] == info.key
        and "field" in entry["key"]
        and entry["column"] != key_letter
        and entry["matched"] > 0
    ]
    columns = {c["column"]: c for c in table["columns"]}
    if named:
        return columns[min(named, key=order_of)["column"]]
    wanted = {"name", normal(info.label)}
    return next(
        (
            c
            for c in table["columns"]
            if c["column"] != key_letter and normal(c["header"]) in wanted
        ),
        None,
    )


def counts(
    session: Session,
    file_id: int,
    place: dict[str, Any],
    workspace: str,
    type_key: str,
    key_column: int,
    key: dict[str, Any],
    name_column: int | None,
) -> dict[str, int]:
    """The file's distinct keys, those found among the type's stored keys, the stored records no
    key names, and the matched keys whose name cell differs from the stored name."""
    stored = stored_query(attribute_of(key))
    row = session.execute(
        text(
            f"WITH f AS ({FILE_KEYS}), s AS ({stored}) SELECT"
            " (SELECT count(*) FROM f),"
            " (SELECT count(DISTINCT f.key) FROM f JOIN s ON s.key = f.key),"
            " (SELECT count(*) FROM s WHERE NOT EXISTS (SELECT 1 FROM f WHERE f.key = s.key)),"
            " (SELECT count(DISTINCT f.key) FROM f JOIN s ON s.key = f.key"
            "   WHERE f.name IS NOT NULL AND btrim(f.name) <> '' AND f.name <> s.name)"
        ),
        parameters_of(place, file_id, workspace, type_key, key_column, key, name_column),
    ).one()
    return {"distinct": row[0], "matched": row[1], "missing": row[2], "differ": row[3]}


def combination_counts(
    session: Session,
    file_id: int,
    place: dict[str, Any],
    workspace: str,
    type_key: str,
    key_columns: list[int],
    attributes: list[str],
) -> dict[str, int]:
    """:func:`counts` for a key of several attributes (AP-D43): a row of the file has a key when
    every key column is filled, and the stored records of the type with every attribute filled hold
    one. A key is the texts of the columns, or of the attributes, in the key's order; names are not
    compared."""
    row = session.execute(
        text(
            """
            WITH f AS (
                SELECT string_agg(k.text, CAST(:sep AS text) ORDER BY u.ord) AS key
                FROM source_file_cells k
                JOIN unnest(CAST(:key_columns AS integer[])) WITH ORDINALITY u(col, ord)
                    ON u.col = k.column_number
                WHERE k.source_file_id = :file AND k.sheet_index = :sheet
                  AND k.row_number > :header AND k.row_number <= :last AND k.row_number <> :note
                  AND btrim(k.text) <> ''
                GROUP BY k.row_number HAVING count(*) = :n),
            s AS (
                SELECT string_agg(a.text_value, CAST(:sep AS text) ORDER BY u.ord) AS key
                FROM objects o
                JOIN attribute_values a ON a.object_id = o.id AND a.text_value IS NOT NULL
                JOIN unnest(CAST(:attributes AS text[])) WITH ORDINALITY u(attr, ord)
                    ON u.attr = a.attribute_type_key
                WHERE o.workspace_key = :workspace AND o.object_type_key = :type
                GROUP BY o.id HAVING count(*) = :n)
            SELECT
                (SELECT count(DISTINCT key) FROM f),
                (SELECT count(DISTINCT f.key) FROM f JOIN s ON s.key = f.key),
                (SELECT count(*) FROM s WHERE NOT EXISTS (SELECT 1 FROM f WHERE f.key = s.key))
            """
        ),
        {
            **parameters_of(place, file_id, workspace, type_key, key_columns[0], {}, None),
            "key_columns": key_columns,
            "attributes": attributes,
            "n": len(attributes),
            "sep": "\x1f",
        },
    ).one()
    return {"distinct": row[0], "matched": row[1], "missing": row[2], "differ": 0}


def new_keys(
    session: Session,
    file_id: int,
    place: dict[str, Any],
    workspace: str,
    type_key: str,
    key_column: int,
    key: dict[str, Any],
    name_column: int | None,
) -> list[str]:
    """The file's keys no stored record of the type holds."""
    stored = stored_query(attribute_of(key))
    return list(
        session.scalars(
            text(
                f"WITH f AS ({FILE_KEYS}), s AS ({stored}) SELECT f.key FROM f"
                " WHERE NOT EXISTS (SELECT 1 FROM s WHERE s.key = f.key) ORDER BY f.key"
            ),
            parameters_of(place, file_id, workspace, type_key, key_column, key, name_column),
        )
    )


def stored_names(
    session: Session,
    file_id: int,
    place: dict[str, Any],
    workspace: str,
    type_key: str,
    key_column: int,
    key: dict[str, Any],
    name_column: int,
) -> tuple[dict[str, str], list[str]]:
    """The name cells that differ from the stored name of the record their key matches, each with
    that name. A cell two matched rows carry with different stored names, or one a row that matches
    no record carries too, cannot be mapped (a map is by the cell's text): those are returned
    apart."""
    stored = stored_query(attribute_of(key))
    rows = session.execute(
        text(
            f"WITH f AS ({FILE_KEYS}), s AS ({stored}),"
            " d AS (SELECT f.name AS cell, s.name AS stored FROM f JOIN s ON s.key = f.key"
            "   WHERE f.name IS NOT NULL AND btrim(f.name) <> '' AND f.name <> s.name),"
            " other AS (SELECT DISTINCT f.name AS cell FROM f"
            "   WHERE NOT EXISTS (SELECT 1 FROM s WHERE s.key = f.key))"
            " SELECT d.cell, min(d.stored), count(DISTINCT d.stored),"
            "   EXISTS (SELECT 1 FROM other WHERE other.cell = d.cell)"
            " FROM d GROUP BY d.cell ORDER BY d.cell"
        ),
        parameters_of(place, file_id, workspace, type_key, key_column, key, name_column),
    ).all()
    mapped = {cell: name for cell, name, many, shared in rows if many == 1 and not shared}
    return mapped, [cell for cell, _, many, shared in rows if many != 1 or shared]


def rows_of_sheet(session: Session, file_id: int, sheet_index: int) -> int:
    return (
        session.scalar(
            text(
                "SELECT count(DISTINCT row_number) FROM source_file_cells"
                " WHERE source_file_id = :file AND sheet_index = :sheet"
            ),
            {"file": file_id, "sheet": sheet_index},
        )
        or 0
    )


# --- what needs the person -----------------------------------------------------------------------


def _decided(table: dict[str, Any], choice: str) -> bool:
    return table["choices"][choice]["owner"] == "person"


def attention_of(table: dict[str, Any]) -> list[str]:
    """What of a table still needs the person (a choice they have not made): the keys that are new,
    the names that differ, the stored records the file does not name, the matches by meaning, the
    columns left out, a table not loaded, rows with no place to go. Empty when nothing does."""
    load = table["choices"]["load"]
    if table["as"] != "update" or load["value"] is not True:
        return [] if load["owner"] == "person" else ["notLoaded"]
    found: list[str] = []
    if table["new"] > 0 and not _decided(table, "newRecords"):
        found.append("newKeys")
    if table["namesDiffer"] > 0 and not _decided(table, "names"):
        found.append("namesDiffer")
    if table["missing"] > 0 and not _decided(table, "missing"):
        found.append("missing")
    if table["meaning"] and table["owner"] != "person":
        found.append("meaning")
    # A column the followed profile left out of the file it read before too was no decision then.
    if any(
        c["leftOut"] and c["owner"] != "person" and not c.get("known") for c in table["columns"]
    ):
        found.append("leftOutColumns")
    if table.get("noParent") and table["new"] > 0 and not _decided(table, "newRecords"):
        found.append("noParent")
    return found


def finish(found: dict[str, Any]) -> None:
    """The reading's summary and each table's attention and left-out columns, from the reading as
    it stands (written again whenever a step changed it)."""
    tables = found["tables"]
    for table in tables:
        table["leftOut"] = [
            {"column": c["column"], "header": c["header"], "reason": c["leftOut"]}
            for c in table["columns"]
            if c["leftOut"]
        ]
        table["attention"] = attention_of(table)
    updates = [t for t in tables if t["as"] == "update"]
    loaded = [t for t in updates if t["choices"]["load"]["value"] is True]
    found["summary"] = {
        "tables": len(tables),
        # Every sheet of the file: those holding tables and those holding none.
        "sheets": len(
            {t["sheet"] for t in found["tables"]} | {s["sheet"] for s in found["sheets"]}
        ),
        "updates": len(updates),
        "notLoaded": len(tables) - len(loaded),
        "needDecision": sum(1 for t in tables if t["attention"]),
        "types": len({t["objectTypeKey"] for t in updates}),
        "applications": len({t["applicationKey"] for t in updates if t["applicationKey"]}),
    }
