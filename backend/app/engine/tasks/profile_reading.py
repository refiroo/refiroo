"""Reading a workbook by a stored import profile that fits it (Product 0.16 AP6a).

The instance holds the import profiles that read the layouts it has loaded before. Before the rules
read a file, the stored profiles of the workspace's model are fitted to it, with the profile check's
column comparison (``sources/profile_check.compare_columns``): a profile **fits** when every one of
its sources finds its sheet and a table of the file at its place and none of the columns it names is
missing (renamed columns allowed). Of several that fit, the one with the most sources, then the
newest last load, is followed: each of its sources is one table of the reading (``owner: profile``,
every binding of the source shown with what it fills), and the columns of the file it does not
name are listed as left out. Tables the profile does not cover are read by the rules.
"""

from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from ...models.database import ImportProfile, Job, ModelRelease, SourceFile
from ...models.imports import ImportProfileDefinition, Source
from ...models.schema import EngineModel
from ..imports.binding import named_columns
from ..imports.profiles import check_profile, parsed
from ..sources.profile_check import compare_columns, previous_file
from ..sources.staged import StagedFile
from . import placement, reading
from .catalog import Types, kind_of, label_of

NOT_READ = "The profile “{name}” does not read it"
NOT_READ_BEFORE = "The profile “{name}” does not read it; the file it read before had it too"
OTHER = "Read together with another column's binding"


@dataclass
class Fitted:
    profile: ImportProfile
    definition: ImportProfileDefinition
    # (index of the source in the profile, the source as it reads this file, its table of the file)
    sources: list[tuple[int, dict[str, Any], reading.FileTable]]
    # The headers of the file the profile read before, by sheet name: a column the profile does not
    # read and that file had too was left out then, so it is no decision now.
    earlier_headers: dict[str, set[str]]


def _last_load(session: Session, key: str) -> int:
    return (
        session.scalar(
            select(func.max(Job.sequence_id)).where(
                Job.kind == "import", Job.parameters["profile"]["key"].as_string() == key
            )
        )
        or 0
    )


def candidates(
    session: Session, model: EngineModel
) -> list[tuple[ImportProfile, ImportProfileDefinition]]:
    """The stored profiles written for the model that are valid under its release, those with the
    most sources first, then the newest last load."""
    found = []
    for profile in session.scalars(
        select(ImportProfile)
        .join(ModelRelease, ModelRelease.id == ImportProfile.checked_release_id)
        .where(ModelRelease.release_key == model.release.key)
    ):
        definition = parsed(profile)
        if not check_profile(model, definition):
            found.append((profile, definition))
    found.sort(
        key=lambda item: (
            -len(item[1].sources),
            -_last_load(session, item[0].key),
            -item[0].updated_at.timestamp(),
        )
    )
    return found


def _table_of(
    tables: list[reading.FileTable], used: set[int], sheet: str | None, source: Source
) -> reading.FileTable | None:
    for item in tables:
        if id(item) in used or item.sheet != sheet or item.header_row != source.headerRow:
            continue
        if (
            source.block is not None
            and item.block is not None
            and item.block.get("firstColumn") != source.block.firstColumn
        ):
            continue
        return item
    return None


def fit(
    session: Session, source_file: SourceFile, model: EngineModel, tables: list[reading.FileTable]
) -> Fitted | None:
    """The stored profile that fits the file best, or ``None``: of those whose every source reads
    it, the one a file was last loaded by (what the person last did with this layout), then the one
    that names the most columns."""
    staged = StagedFile(session, source_file.id)
    best: Fitted | None = None
    best_rank: tuple[float, int] = (-1.0, -1)
    for profile, definition in candidates(session, model):
        earlier_file = previous_file(session, profile.key, source_file)
        earlier = StagedFile(session, earlier_file.id) if earlier_file is not None else None
        used: set[int] = set()
        used_sheets: set[str | None] = set()
        sources: list[tuple[int, dict[str, Any], reading.FileTable]] = []
        for index, entry in enumerate(definition.sources):
            report, followed = compare_columns(session, entry, staged, earlier, set(), False)
            sheet = entry.sheet or (staged.sheet_names[0] if staged.sheet_names else None)
            # A second source of a sheet a source reads already (a parent's values on the rows of
            # its children): the table is read by the first.
            if (
                report["sheetFound"]
                and followed is not None
                and not report["columns"]["missing"]
                and sheet in used_sheets
                and _table_of(tables, used, sheet, entry) is None
            ):
                continue
            item = _table_of(tables, used, sheet, entry)
            if (
                not report["sheetFound"]
                or followed is None
                or report["columns"]["missing"]
                or item is None
            ):
                break
            used_sheets.add(sheet)
            used.add(id(item))
            sources.append((index, followed, item))
        else:
            named = sum(
                1
                for entry in definition.sources
                for binding in entry.columns
                if not binding.ignore
            )
            rank = (float(_last_load(session, profile.key)), named)
            if rank > best_rank:
                best = Fitted(profile, definition, sources, headers_of(session, earlier_file))
                best_rank = rank
    return best


_HEADERS = text(
    "SELECT s.name, c.statistics ->> 'header' FROM source_file_columns c"
    " JOIN source_file_sheets s ON s.source_file_id = c.source_file_id"
    " AND s.sheet_index = c.sheet_index WHERE c.source_file_id = :file"
)


def headers_of(session: Session, earlier_file: SourceFile | None) -> dict[str, set[str]]:
    found: dict[str, set[str]] = {}
    if earlier_file is not None:
        for sheet, header in session.execute(_HEADERS, {"file": earlier_file.id}):
            if header:
                found.setdefault(sheet, set()).add(header)
    return found


def table_of(
    session: Session,
    file_id: int,
    workspace: str,
    types: Types,
    number: int,
    fitted: Fitted,
    index: int,
    followed: dict[str, Any],
    item: reading.FileTable,
) -> dict[str, Any]:
    """The reading of one table by the profile source that covers it."""
    name = fitted.profile.name
    table = reading.base_table(number, item)
    distinct, found = reading.overlap_rows(session, file_id, item, workspace, types)
    letters = {c.number: c.letter for c in item.columns}
    table["distinct"] = {letters[n]: count for n, count in distinct.items()}
    table["overlaps"] = found
    named = {header for _, header in named_columns(Source.model_validate(followed), "")}
    bound: dict[str, dict[str, Any]] = {}
    for binding in followed["columns"]:
        rest = {k: v for k, v in binding.items() if k not in ("column", "columns", "valueMap")}
        for header in [binding["column"]] if "column" in binding else binding.get("columns", []):
            bound[header] = rest
    for column in table["columns"]:
        column["owner"] = "profile"
        if column["header"] in bound:
            column["binding"] = bound[column["header"]]
            column["kind"] = kind_of(column["binding"])
            column["label"] = label_of(types, column["binding"])
        elif column["header"] in named:
            column["kind"], column["label"] = "other", OTHER
        else:
            column["leftOut"] = NOT_READ.format(name=name)
            if column["header"] in fitted.earlier_headers.get(item.sheet, set()):
                column["leftOut"] = NOT_READ_BEFORE.format(name=name)
                column["known"] = True
    info = types.get(followed["objectTypeKey"])
    key = followed.get("key")
    key_column = None
    key_shown: dict[str, Any] | None = None
    by_id = False
    key_columns: list[dict[str, Any]] = []
    if key is not None and "attributeTypeKeys" in key:
        # AP-D43: the key is the columns that bind its attributes together; the first stands for
        # it where a single column is shown, and the figures count the combinations.
        key_shown = {"attributeTypeKeys": list(key["attributeTypeKeys"])}
        for attribute in key["attributeTypeKeys"]:
            found = next(
                (c for c in table["columns"] if c["binding"] == {"attributeTypeKey": attribute}),
                None,
            )
            if found is not None:
                key_columns.append(found)
        key_column = key_columns[0] if key_columns else None
        if len(key_columns) != len(key["attributeTypeKeys"]):
            key_column = None
    elif key is not None:
        if "attributeTypeKey" in key:
            key_shown = {"attributeTypeKey": key["attributeTypeKey"]}
            wanted: dict[str, Any] | None = key_shown
        elif key.get("field") == "name":
            key_shown, wanted = {"field": "name"}, {"field": "name"}
        else:
            key_shown, wanted, by_id = {"column": key["column"]}, None, True
        key_column = next(
            (
                c
                for c in table["columns"]
                if (c["header"] == key["column"] if by_id else c["binding"] == wanted)
            ),
            None,
        )
    table.update(
        {
            "as": "update",
            "objectTypeKey": followed["objectTypeKey"],
            "applicationKey": followed["applicationKey"],
            "parentTypeKeys": list(info.parents) if info else [],
            "typeName": info.label if info else followed["objectTypeKey"],
            "reason": f"Read as the profile “{name}” reads this layout",
            "owner": "profile",
            "profile": {
                "key": fitted.profile.key,
                "name": name,
                "version": fitted.profile.version,
                "source": index,
            },
            "profileSource": followed,
            "keyKind": "IDs" if by_id else None,
        }
    )
    table["choices"]["missing"] = {
        "value": "remove" if followed.get("missing") == "delete" else "leave",
        "owner": "rules",
    }
    if followed.get("parent"):
        table["parent"] = {**followed["parent"], "source": placement.PROFILE}
    if key_column is None or info is None:
        table["evidence"] = (
            "The profile reads every row of this table as a new record: it holds no key to match "
            "the rows to stored records by."
        )
        return table
    name_column = next(
        (c for c in table["columns"] if c["binding"] == {"field": "name"} and c is not key_column),
        None,
    )
    if key_columns:
        figures = reading.combination_counts(
            session,
            file_id,
            table["place"],
            workspace,
            followed["objectTypeKey"],
            [c["number"] for c in key_columns],
            list(key_shown["attributeTypeKeys"]),
        )
    else:
        figures = reading.counts(
            session,
            file_id,
            table["place"],
            workspace,
            followed["objectTypeKey"],
            key_column["number"],
            key_shown or {},
            name_column["number"] if name_column else None,
        )
    table.update(
        {
            "keyColumn": key_column["column"],
            "key": key_shown,
            "keyOptions": reading.key_options(table, followed["objectTypeKey"]),
            "matched": figures["matched"],
            "new": figures["distinct"] - figures["matched"],
            "missing": figures["missing"],
            "namesDiffer": figures["differ"],
        }
    )
    table["evidence"] = reading.evidence(table)
    return table
