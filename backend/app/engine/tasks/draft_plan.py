"""Carrying the assistant's design out in a model draft (Product 0.16 AP6).

A design task works on a draft of its workspace's model (its base: the release active there) and on
a working copy of the workbook: the person's sheets as given, followed by one sheet per type of the
records the structure needs (``Structure`` sheets), which the import loads before the person's sheets
like any other. The working copy is the draft's source file, staged and profiled in the database, so
the draft's dry run checks every row of both. Model operations are applied as the editor applies
them (``model/authoring``), all or none; the profile is checked against the draft's compiled model.
"""

import copy
import io
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from openpyxl import load_workbook
from pydantic import ValidationError
from sqlalchemy import text, update
from sqlalchemy.orm import Session

from ...errors import ApiError
from ...models.database import ModelDraft, SourceFile
from ...models.imports import ImportProfileDefinition
from ..imports.binding import named_columns, source_mismatch
from ..imports.profiles import check_profile
from ..jobs.files import JobFiles
from ..model.authoring.history import apply_request
from ..model.compiler import compile_model
from ..model.drafts import create_draft
from ..model.workspace_models import load_assignment
from ..sources.profiling import profile_source_file
from ..sources.staged import StagedFile
from .design import DataSheet, Derived, StructureRecord

STRUCTURE = "Structure"
NAME, PARENT = "Name", "Parent"


def open_draft(session: Session, workspace_key: str, name: str) -> ModelDraft:
    """A draft of the model active in the workspace; the caller commits."""
    release = load_assignment(session, workspace_key)[1]
    return create_draft(
        session,
        name=name[:300],
        model=copy.deepcopy(release.model_json),
        base_release_id=release.public_id,
    )


def apply(
    session: Session, draft: ModelDraft, operations: list[dict[str, Any]], max_items: int
) -> dict[str, Any]:
    """The operations applied to the draft as one step, or the refusal; commits either way."""
    if not operations:
        return {"applied": 0}
    try:
        result = apply_request(session, draft.public_id, draft.version, operations, max_items)
    except ApiError as error:
        session.rollback()
        return {"refused": {"code": error.code, "message": error.message, "details": error.details}}
    session.commit()
    errors = [d for d in result.diagnostics if d.severity == "error"]
    return {
        "applied": len(operations),
        "draftErrors": [{"code": d.code, "path": d.path, "message": d.message} for d in errors][
            :40
        ],
    }


def _sheet_name(info: dict[str, Any], taken: set[str]) -> str:
    base = f"{STRUCTURE} {info.get('name') or info['key']}"[:31]
    name, number = base, 2
    while name in taken:
        suffix = f" {number}"
        name, number = base[: 31 - len(suffix)] + suffix, number + 1
    taken.add(name)
    return name


def _ordered(records: list[StructureRecord]) -> list[StructureRecord]:
    """Parents before the records under them, as far as the list names them."""
    by_name = {(r.objectTypeKey, r.name): r for r in records}
    depth: dict[str, int] = {}

    def level(record: StructureRecord, seen: frozenset[str] = frozenset()) -> int:
        if record.ref in depth:
            return depth[record.ref]
        parent = record.parent
        above = by_name.get((parent.objectTypeKey, parent.name)) if parent else None
        found = 0 if above is None or above.ref in seen else level(above, seen | {record.ref}) + 1
        depth[record.ref] = found
        return found

    return sorted(records, key=level)


def _unique(model: dict[str, Any], type_key: str, record: StructureRecord) -> str | None:
    unique = {
        a["key"]
        for a in model.get("attributeTypes") or []
        if (a.get("features") or {}).get("unique")
    }
    item = next((t for t in model.get("objectTypes") or [] if t["key"] == type_key), None)
    for binding in (item or {}).get("attributes") or []:
        if binding["attributeTypeKey"] in unique and record.attributes.get(
            binding["attributeTypeKey"]
        ):
            return binding["attributeTypeKey"]
    return None


def _sheets(
    records: list[StructureRecord], model: dict[str, Any], taken: set[str]
) -> list[tuple[str, str, list[StructureRecord], list[str], str | None]]:
    """Per type of the records, in parent order: its sheet's name, the type, its records, its
    attribute columns and the parent type."""
    types = {t["key"]: t for t in model.get("objectTypes") or []}
    groups: dict[str, list[StructureRecord]] = {}
    for record in _ordered(records):
        groups.setdefault(record.objectTypeKey, []).append(record)
    found = []
    for type_key, members in groups.items():
        name = _sheet_name(types.get(type_key) or {"key": type_key}, taken)
        attributes = sorted({k for r in members for k in r.attributes})
        parent_type = next((r.parent.objectTypeKey for r in members if r.parent), None)
        found.append((name, type_key, members, attributes, parent_type))
    return found


def structure_sources(
    records: list[StructureRecord], model: dict[str, Any], taken: set[str] | None = None
) -> list[dict[str, Any]]:
    """The profile sources that load the structure sheets (first, in parent order). ``taken``: the
    workbook's own sheet names, which a structure sheet's name avoids."""
    applications = {
        key: app["key"]
        for app in model.get("applications") or []
        for key in app.get("objectTypeKeys") or []
    }
    sources = []
    for name, type_key, members, attributes, parent_type in _sheets(
        records, model, set(taken or ())
    ):
        key_attribute = _unique(model, type_key, members[0])
        columns: list[dict[str, Any]] = [{"column": NAME, "field": "name"}]
        columns += [{"column": k, "attributeTypeKey": k} for k in attributes]
        if parent_type:
            columns.append(
                {
                    "column": PARENT,
                    "parent": {"objectTypeKey": parent_type, "matchBy": {"field": "name"}},
                }
            )
        sources.append(
            {
                "sheet": name,
                "applicationKey": members[0].applicationKey or applications.get(type_key, ""),
                "objectTypeKey": type_key,
                "key": {"attributeTypeKey": key_attribute} if key_attribute else {"field": "name"},
                "columns": columns,
            }
        )
    return sources


# A derived sheet's rows, and how long its query may run.
DERIVED_MAX_ROWS = 200_000
DERIVED_TIMEOUT = "30s"
READER = "rdm_derived_reader"

_CELLS_VIEW = """
CREATE TEMP VIEW cells AS
SELECT s.name AS sheet, c.row_number AS row, c.column_number AS col, c.text AS value
FROM source_file_cells c JOIN source_file_sheets s
    ON s.source_file_id = c.source_file_id AND s.sheet_index = c.sheet_index
WHERE c.source_file_id = {file}
"""


def _one_select(sql: str) -> str:
    """The query without its comments and last semicolon; refused when it is more than one
    statement or does not read: a semicolon outside a quoted text ends a statement."""
    without = re.sub(r"--[^\n]*|/\*.*?\*/", " ", sql, flags=re.DOTALL).strip().rstrip(";").strip()
    outside = re.sub(r"'(?:[^']|'')*'|\"(?:[^\"]|\"\")*\"", "", without)
    if ";" in outside or not re.match(r"\(*\s*(select|with|values)\b", without, re.IGNORECASE):
        raise ValueError("A derived sheet's query is one SELECT")
    return without


def run_derived(
    session: Session, file_id: int, spec: Derived
) -> tuple[list[str], list[tuple[Any, ...]]]:
    """The query's headers and rows. It runs as a role granted nothing but the file's cells, read
    only and with a time limit, in a savepoint undone afterwards: one statement, a SELECT."""
    query = _one_select(spec.sql)
    savepoint = session.begin_nested()
    try:
        connection = session.connection()
        connection.exec_driver_sql(_CELLS_VIEW.format(file=int(file_id)))
        connection.exec_driver_sql("REVOKE ALL ON cells FROM PUBLIC")
        connection.exec_driver_sql(f"GRANT SELECT ON cells TO {READER}")
        schema = connection.exec_driver_sql("SELECT pg_my_temp_schema()::regnamespace::text").scalar()
        connection.exec_driver_sql(f"GRANT USAGE ON SCHEMA {schema} TO {READER}")
        connection.exec_driver_sql(f"SET LOCAL statement_timeout = '{DERIVED_TIMEOUT}'")
        connection.exec_driver_sql(f"SET LOCAL ROLE {READER}")
        connection.exec_driver_sql("SET LOCAL transaction_read_only = on")
        result = connection.exec_driver_sql(
            f"SELECT * FROM ({query}) derived LIMIT {DERIVED_MAX_ROWS + 1}"
        )
        headers = list(result.keys())
        rows = [tuple(row) for row in result]
    finally:
        savepoint.rollback()
    if len(rows) > DERIVED_MAX_ROWS:
        raise ValueError(f"The query gives more than {DERIVED_MAX_ROWS} rows")
    return headers, rows


def derived_problems(
    session: Session, source: SourceFile | None, current: dict[str, Any]
) -> list[dict[str, str]]:
    """What is wrong with the design's derived sheets, as a profile's problems."""
    problems = []
    for raw in current.get("derived") or []:
        spec = Derived.model_validate(raw)
        if source is None:
            continue
        try:
            run_derived(session, source.id, spec)
        except Exception as error:  # noqa: BLE001 - any failure of the query goes back as words
            message = str(getattr(error, "orig", error)).split("\n")[0][:400]
            problems.append(
                {"code": "DERIVED_QUERY", "message": f"Derived sheet {spec.name}: {message}"}
            )
    return problems


def derived_sheets(
    session: Session, source: SourceFile, specs: list[dict[str, Any]]
) -> list[tuple[str, list[str], list[tuple[Any, ...]]]]:
    return [
        (spec.name, *run_derived(session, source.id, spec))
        for spec in (Derived.model_validate(raw) for raw in specs)
    ]


def working_book(
    original: Path,
    records: list[StructureRecord],
    model: dict[str, Any],
    data: list[DataSheet] | None = None,
    derived: list[tuple[str, list[str], list[tuple[Any, ...]]]] | None = None,
) -> tuple[bytes, list[dict[str, Any]]]:
    """The person's workbook followed by the assistant's data sheets and the structure sheets, and
    the profile sources that load the structure sheets (the data sheets' are the design's own)."""
    # Opened as a file, not by name: openpyxl judges a name by its extension, and a stored upload
    # has none (as ``imports/readers.py``). With the formulas' last values, as the upload was staged:
    # a copy saved with the formulas alone holds no value in those cells.
    with original.open("rb") as handle:
        book = load_workbook(handle, data_only=True)
    taken = set(book.sheetnames)
    for sheet_data in data or []:
        if sheet_data.name in taken:
            continue
        sheet = book.create_sheet(sheet_data.name)
        sheet.append(list(sheet_data.columns))
        for row in sheet_data.rows:
            sheet.append(list(row))
        taken.add(sheet_data.name)
    for name, headers, rows in derived or []:
        if name not in taken:
            sheet = book.create_sheet(name)
            sheet.append(headers)
            for row in rows:
                sheet.append(row)
            taken.add(name)
    for name, _, members, attributes, parent_type in _sheets(records, model, set(taken)):
        sheet = book.create_sheet(name)
        sheet.append([NAME, *attributes] + ([PARENT] if parent_type else []))
        for record in members:
            row: list[Any] = [record.name, *(record.attributes.get(k) for k in attributes)]
            if parent_type:
                row.append(record.parent.name if record.parent else None)
            sheet.append(row)
    buffer = io.BytesIO()
    book.save(buffer)
    return buffer.getvalue(), structure_sources(records, model, taken)


def stage(
    session: Session,
    draft: ModelDraft,
    content: bytes,
    name: str,
    workspace_key: str,
    files: JobFiles,
    check: Any,
) -> SourceFile:
    """The working copy as the draft's source file, staged and profiled now; the draft's earlier
    file superseded. Commits."""
    import hashlib

    now = datetime.now(UTC)
    source = SourceFile(
        draft_id=draft.id,
        name=name,
        format="xlsx",
        bytes=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
        workspace_key=workspace_key,
        version=1,
        uploaded_at=now,
    )
    session.add(source)
    session.flush()
    session.execute(
        update(SourceFile)
        .where(
            SourceFile.draft_id == draft.id,
            SourceFile.id != source.id,
            SourceFile.superseded_at.is_(None),
        )
        .values(superseded_at=now)
        .execution_options(synchronize_session=False)
    )
    files.directory.mkdir(parents=True, exist_ok=True)
    target = files.upload(source.public_id)
    with target.open("wb") as copy_:
        shutil.copyfileobj(io.BytesIO(content), copy_)
    session.commit()
    profile_source_file(session, source.public_id, target, check)
    session.commit()
    return source


def check(draft: ModelDraft, profile: dict[str, Any] | None) -> dict[str, Any]:
    """The draft's errors and the profile's problems against the draft's model."""
    compiled = compile_model(draft.model_json)
    found: dict[str, Any] = {
        "draftErrors": [
            {"code": d.code, "path": d.path, "message": d.message}
            for d in compiled.diagnostics
            if d.severity == "error"
        ][:40]
    }
    if profile is None:
        found["profileProblems"] = [{"code": "NO_PROFILE", "message": "No profile was given"}]
        return found
    try:
        definition = ImportProfileDefinition.model_validate(profile)
    except ValidationError as error:
        found["profileProblems"] = [_shape_problem(e) for e in error.errors()[:40]]
        return found
    if compiled.model is not None and compiled.valid:
        found["profileProblems"] = [p.body() for p in check_profile(compiled.model, definition)][
            :40
        ]
    return found


_NAMES_ON_ROWS = text("""
SELECT row_number, count(DISTINCT btrim(text)) AS found FROM source_file_cells
WHERE source_file_id = :file AND sheet_index = :sheet AND btrim(text) = ANY(:names)
GROUP BY 1 ORDER BY 2 DESC, 1 LIMIT 3
""")

_ROWS_BELOW = text("""
SELECT count(DISTINCT row_number) FROM source_file_cells
WHERE source_file_id = :file AND sheet_index = :sheet AND row_number > :header
""")


def fit_to_file(
    session: Session, file: SourceFile, profile: dict[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """The profile without the sources its file cannot be read by (a sheet, header row or column
    that is not there), and those sources: each with all its problems, where the sheet does hold
    the names it looks for, and its rows. One such source stops no other: the rest are checked. A
    profile none of whose sources fit is returned whole, for the dry run to say so."""
    definition = ImportProfileDefinition.model_validate(profile)
    book = StagedFile(session, file.id)
    found: list[dict[str, Any]] = []
    fitting: list[dict[str, Any]] = []
    for index, (raw, source) in enumerate(zip(profile["sources"], definition.sources, strict=True)):
        problems = source_mismatch(book, source, f"/sources/{index}")
        if not problems:
            fitting.append(raw)
            continue
        hint, rows = None, 0
        if source.sheet in book.sheet_names:
            parameters = {"file": file.id, "sheet": book.sheet_names.index(source.sheet)}
            names = [name for _, name in named_columns(source, "")]
            places = session.execute(_NAMES_ON_ROWS, {**parameters, "names": names}).all()
            hint = (
                "Of the names it looks for, the sheet holds "
                + ", ".join(f"{p.found} on row {p.row_number}" for p in places)
                if places
                else "The sheet holds none of the names it looks for on any row: it may have no "
                "header row at all"
            )
            rows = session.scalar(_ROWS_BELOW, {**parameters, "header": source.headerRow}) or 0
        found.append(
            {
                "source": raw,
                "sheet": source.sheet,
                "objectTypeKey": source.objectTypeKey,
                "headerRow": source.headerRow,
                "rows": rows,
                "problems": problems[:12],
                "more": max(0, len(problems) - 12),
                "hint": hint,
            }
        )
    if not fitting:
        return profile, []
    return {**profile, "sources": fitting}, found


def not_fit_refusals(found: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The sources ``fit_to_file`` left out, as refusals of a dry run."""
    return [
        {
            "sheet": item["sheet"],
            "objectTypeKey": item["objectTypeKey"],
            "code": "SOURCE_DOES_NOT_FIT",
            "rows": item["rows"],
            "examples": [
                {
                    "row": item["headerRow"],
                    "message": (
                        f"The sheet was not read: header row {item['headerRow']} does not hold "
                        f"what this source names. {item['hint'] or ''}"
                    ).strip(),
                    "details": {"problems": item["problems"], "more": item["more"]},
                }
            ],
        }
        for item in found
    ]


_LINK_CELLS = text("""
SELECT DISTINCT btrim(c.text) FROM source_file_cells c
JOIN source_file_sheets sh ON sh.source_file_id = c.source_file_id AND sh.sheet_index = c.sheet_index
JOIN source_file_cells h ON h.source_file_id = c.source_file_id AND h.sheet_index = c.sheet_index
    AND h.column_number = c.column_number AND h.row_number = :header
WHERE c.source_file_id = :file AND sh.name = :sheet AND btrim(h.text) = btrim(:column)
  AND c.row_number > :header AND btrim(c.text) <> ''
""")

_LINK_TARGETS = text("""
SELECT lower(btrim(x.v)), count(*), min(btrim(x.v)) FROM (
    SELECT CASE WHEN :attribute IS NULL THEN o.name ELSE coalesce(a.text_value,
        a.integer_value::text, a.decimal_value::text) END AS v
    FROM objects o LEFT JOIN attribute_values a
        ON a.object_id = o.id AND a.attribute_type_key = :attribute
    WHERE o.workspace_key = :workspace AND o.object_type_key = :type) x
WHERE x.v IS NOT NULL GROUP BY 1
""")


def unresolved_links(
    session: Session,
    file: SourceFile | None,
    workspace: str,
    profile: dict[str, Any] | None,
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """The link columns of the workbook's own sheets whose values find no stored record or several,
    before any dry run: each with the values and what the type does hold. A type another source or
    the design's records load is not checked: its records are not stored yet."""
    if file is None or not profile:
        return []
    sources = profile.get("sources") or []
    loaded = {s.get("objectTypeKey") for s in sources} | {r.get("objectTypeKey") for r in records}
    maps = profile.get("valueMaps") or {}
    found = []
    for source in sources:
        for binding in source.get("columns") or []:
            link = binding.get("relation") or binding.get("parent")
            if not link or not binding.get("column") or link.get("missing") == "create":
                continue
            target = link.get("objectTypeKey")
            match = link.get("matchBy") or {}
            if target in loaded or match.get("field") == "id":
                continue
            attribute = match.get("attributeTypeKey")
            stored = {
                row[0]: (row[1], row[2])
                for row in session.execute(
                    _LINK_TARGETS, {"attribute": attribute, "workspace": workspace, "type": target}
                )
            }
            cells = session.scalars(
                _LINK_CELLS,
                {
                    "file": file.id,
                    "sheet": source.get("sheet"),
                    "header": int(source.get("headerRow") or 1),
                    "column": binding["column"],
                },
            ).all()
            mapping = maps.get(binding.get("valueMap")) or {}
            split = link.get("split")
            not_found: set[str] = set()
            ambiguous: set[str] = set()
            for cell in cells:
                # A map reads the whole cell, then the cell is split.
                value = mapping.get(cell, cell)
                if value is None:
                    continue
                for part in str(value).split(split) if split else [str(value)]:
                    part = part.strip()
                    if not part:
                        continue
                    count = stored.get(part.lower(), (0, ""))[0]
                    if count == 0:
                        not_found.add(part)
                    elif count > 1:
                        ambiguous.add(part)
            if not_found or ambiguous:
                found.append(
                    {
                        "sheet": source.get("sheet"),
                        "objectTypeKey": source.get("objectTypeKey"),
                        "column": binding["column"],
                        "binding": binding,
                        "target": target,
                        "matchBy": match,
                        "notFound": sorted(not_found)[:20],
                        "ambiguous": sorted(ambiguous)[:20],
                        "stored": sorted(v[1] for v in stored.values())[:60],
                    }
                )
    return found


_REFUSED = text("""
SELECT o.source_index, o.outcome -> 'error' ->> 'code' AS code,
    o.outcome -> 'error' ->> 'message' AS message, o.outcome -> 'error' -> 'details' AS details,
    o.row_number, count(*) OVER (PARTITION BY o.source_index, o.outcome -> 'error' ->> 'code') AS rows,
    row_number() OVER (
        PARTITION BY o.source_index, o.outcome -> 'error' ->> 'code' ORDER BY o.row_number
    ) AS nth
FROM job_items o JOIN jobs j ON j.sequence_id = o.job_id
WHERE j.id = :job AND o.status = 'rejected'
""")


_SKIPPED = text("""
SELECT c.row_number FROM source_file_cells c
JOIN source_files f ON f.id = c.source_file_id
JOIN source_file_sheets sh ON sh.source_file_id = f.id AND sh.sheet_index = c.sheet_index
WHERE f.public_id = :file AND sh.name = :sheet AND c.row_number > :header
EXCEPT
SELECT o.row_number FROM job_items o JOIN jobs j ON j.sequence_id = o.job_id
WHERE j.id = :job AND o.source_index = :source
ORDER BY 1
""")


_KEY_FILLED = text("""
SELECT c.row_number FROM source_file_cells c
JOIN source_files f ON f.id = c.source_file_id
JOIN source_file_sheets sh ON sh.source_file_id = f.id AND sh.sheet_index = c.sheet_index
JOIN source_file_cells h ON h.source_file_id = c.source_file_id AND h.sheet_index = c.sheet_index
    AND h.column_number = c.column_number AND h.row_number = :headerRow
WHERE f.public_id = :file AND sh.name = :sheet AND btrim(h.text) = btrim(:header)
  AND c.row_number > :headerRow AND btrim(c.text) <> ''
""")


def _key_header(source: dict[str, Any]) -> str | None:
    """The column a source's key reads."""
    key = source.get("key") or {}
    if key.get("column"):
        return key["column"]
    for binding in source.get("columns") or []:
        if key.get("field") == "name" and binding.get("field") == "name":
            return binding.get("column")
        if key.get("attributeTypeKey") and binding.get("attributeTypeKey") == key["attributeTypeKey"]:
            return binding.get("column")
    return None


def skipped(session: Session, job: Any, sources: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    """The rows of each source that skips rows without a key (``rowsWithoutKey: skip``) the dry run
    wrote nothing for: the filled rows below the header with no outcome, by source, with the first
    three row numbers. A source of a block is not counted (its rows are not the whole sheet's)."""
    found: dict[int, dict[str, Any]] = {}
    for index, source in enumerate(sources):
        if source.get("rowsWithoutKey") != "skip" or source.get("block") or not source.get("sheet"):
            continue
        rows = session.scalars(
            _SKIPPED,
            {
                "file": job.parameters["sourceFileId"],
                "sheet": source["sheet"],
                "header": int(source.get("headerRow") or 1),
                "job": job.id,
                "source": index,
            },
        ).all()
        # A row whose key is filled repeats a key another row wrote: it is that record, not skipped.
        header = _key_header(source)
        if rows and header is not None:
            filled = set(
                session.scalars(
                    _KEY_FILLED,
                    {
                        "file": job.parameters["sourceFileId"],
                        "sheet": source["sheet"],
                        "headerRow": int(source.get("headerRow") or 1),
                        "header": header,
                    },
                )
            )
            rows = [row for row in rows if row not in filled]
        if rows:
            found[index] = {"rows": len(rows), "examples": list(rows[:3])}
    return found


def refusals(session: Session, job_id: str, sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The dry run's refused rows by source and code: how many, and the first three messages with
    their details and row numbers, as the assistant reads them to fix the design."""
    found: dict[tuple[int, str], dict[str, Any]] = {}
    for row in session.execute(
        text(f"SELECT * FROM ({_REFUSED.text}) r WHERE nth <= 3 ORDER BY 1, 2, 5"), {"job": job_id}
    ):
        source = (
            sources[row.source_index]
            if row.source_index is not None and row.source_index < len(sources)
            else {}
        )
        entry = found.setdefault(
            (row.source_index, row.code),
            {
                "sheet": source.get("sheet"),
                "objectTypeKey": source.get("objectTypeKey"),
                "code": row.code,
                "rows": row.rows,
                "examples": [],
            },
        )
        entry["examples"].append(
            {"row": row.row_number, "message": (row.message or "")[:300], "details": row.details}
        )
    return list(found.values())


def _shape_problem(error: Any) -> dict[str, str]:
    """A profile's shape problem as the assistant can act on it: which property, where, and why."""
    path = "/" + "/".join(str(part) for part in error["loc"])
    name = str(error["loc"][-1]) if error["loc"] else ""
    if error["type"] == "extra_forbidden":
        message = (
            f"'{name}' is not a property here: this part does not take it (a value map is named by a "
            "column binding's 'valueMap'; a related record's parent takes objectTypeKey, matchBy and "
            "value, or column with an optional valueMap)"
        )
    elif error["type"] == "missing":
        message = f"'{name}' is required here"
    else:
        message = f"{error['msg']} (at '{name}')"
    return {"path": path, "code": "INVALID", "message": message}
