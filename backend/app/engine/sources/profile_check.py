"""An import profile's check of its next file (Product 0.10 A5c, D82, D83).

A file uploaded to a stored profile (``POST /source-files`` with ``owner.profileKey``) is profiled,
then checked by a job of kind ``profileCheck``, which writes nothing. ``POST
/import-profiles/{key}/check`` checks the profile's current file again (after the profile changed).
The check reports, in one job so the report is one consistent read:

- **Columns**, by header against the profile and the file the profile last read (the profile's
  previous file, else the stored file its last import read): *missing* per source (it names the
  column, the file lacks it), *new* once per sheet, on its first source (no source on the sheet
  names it and the earlier file lacked it), and *renamed* (a missing and a new column at the same
  position sharing at least half their distinct values, :data:`RENAME_SHARE`; without an earlier
  file nothing is renamed).
- **The profile against the active release** (J35.3): ``valid`` and every problem at its pointer.
- **What the load would do**, when the profile holds: the file bound through the profile as it
  would read the file (renamed columns read under their new header, missing ones left out, a source
  whose sheet is gone left out) in the profile's workspace, live, and every item previewed in a
  transaction rolled back, as a dry run is (``dry_run.summary``); and what binding found on the way
  (``binding._findings``): new values of match columns, name drift and records missing from the
  file (D82).

The lists are paged by ``GET /import-profiles/{key}/check/findings``; the previewed rows by
``…/check/rows``.
"""

import copy
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from openpyxl.utils import get_column_letter
from pydantic import ValidationError
from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from ...db import lock_job_subject
from ...errors import api_error
from ...models.database import Job, ModelRelease, SourceFile
from ...models.imports import ImportProfileDefinition, Source
from ...models.schema import EngineModel
from ..imports.binding import named_columns
from ..imports.profiles import check_profile, load_profile, parsed, source_order
from ..imports.readers import Area
from ..jobs.store import ItemOutcome, complete_job, job_parameter, record_outcomes, start_job
from ..model.registry import resolve_model_snapshot
from ..workspaces.catalogue import resolve_workspace
from .dry_run import require_file, summary
from .staged import StagedFile
from .store import profile_state

KIND = "profileCheck"
RUNNING = ("queued", "running")
# A missing and a new column at one position are one column renamed when they share at least this
# share of the larger of their distinct value counts (D83).
RENAME_SHARE = 0.5


def queue_check(session: Session, source: SourceFile, *, retention_days: int) -> Job:
    """The check of a profile's file, queued, its earlier check still running asked to stop; the
    caller commits."""
    profile = load_profile(session, source.profile_key)
    lock_job_subject(session, KIND, profile.key)
    session.execute(
        update(Job)
        .where(
            Job.kind == KIND,
            Job.state.in_(RUNNING),
            job_parameter("profileKey") == profile.key,
        )
        .values(cancel_requested_at=datetime.now(UTC))
        .execution_options(synchronize_session=False)
    )
    workspace = resolve_workspace(session, source.workspace_key)
    return start_job(
        session,
        kind=KIND,
        workspace_key=workspace.key,
        change_set_id=None,
        model_release_id=resolve_model_snapshot(session, workspace.key).release_db_id,
        parameters={
            "policy": "independent",
            "run": "background",
            "stage": "preview",
            # As the load from Settings › Imports runs (D81): a changed row updates its record.
            "onExisting": "overwrite",
            "otherWorkspaceIds": "refuse",
            "profileKey": profile.key,
            "sourceFileId": source.public_id,
            "profile": {"key": profile.key, "version": profile.version, "definition": None},
            "file": {
                "name": source.name,
                "format": source.format,
                "bytes": source.bytes,
                "sha256": source.sha256,
            },
        },
        total=None,
        retention_days=retention_days,
        queued=True,
    )


def submit_check(
    session: Session, profile_key: str, workspace_key: str, *, retention_days: int
) -> Job:
    """Check the profile's current file in a workspace again; commits. ``404
    SOURCE_FILE_NOT_FOUND`` when the profile holds no file there, ``409 SOURCE_FILE_PROFILE_NOT_READY`` before it is profiled."""
    profile = load_profile(session, profile_key)
    source = current_file(session, profile.key, workspace_key)
    if source is None:
        raise api_error(
            404,
            "SOURCE_FILE_NOT_FOUND",
            f"Import profile '{profile.key}' holds no file in workspace '{workspace_key}'; upload "
            "one with POST /source-files",
        )
    state = profile_state(session, source)
    if state["state"] != "completed":
        raise api_error(
            409,
            "SOURCE_FILE_PROFILE_NOT_READY",
            f"Source file '{source.public_id}' is not profiled yet: its profile is "
            f"{state['state']}",
            state,
        )
    job = queue_check(session, source, retention_days=retention_days)
    session.commit()
    return job


def current_file(session: Session, profile_key: str, workspace_key: str) -> SourceFile | None:
    """The profile's newest file not superseded in that workspace, never another's: a profile is
    instance-wide, its files are not (0.12 E1, F5)."""
    return session.scalar(
        select(SourceFile)
        .where(
            SourceFile.profile_key == profile_key,
            SourceFile.workspace_key == workspace_key,
            SourceFile.superseded_at.is_(None),
        )
        .order_by(SourceFile.id.desc())
        .limit(1)
    )


def latest_check(session: Session, profile_key: str, workspace_key: str) -> Job | None:
    """The latest check of the profile's file in that workspace (a check runs in its file's)."""
    load_profile(session, profile_key)
    return session.scalar(
        select(Job)
        .where(
            Job.kind == KIND,
            Job.workspace_key == workspace_key,
            job_parameter("profileKey") == profile_key,
        )
        .order_by(Job.sequence_id.desc())
        .limit(1)
    )


def prepare(session: Session, job: Job, model: EngineModel) -> bool:
    """Before the check binds its file: the columns and the profile's problems go on the job's
    report and the profile as it reads this file into its parameters. ``False`` when nothing can
    be bound (the profile has problems, or no source fits the file): the report is complete."""
    profile = load_profile(session, job.parameters["profileKey"])
    definition = parsed(profile)
    source = session.scalar(
        select(SourceFile).where(SourceFile.public_id == job.parameters["sourceFileId"])
    )
    if source is None:
        raise api_error(
            404,
            "SOURCE_FILE_NOT_FOUND",
            f"Source file '{job.parameters['sourceFileId']}' was deleted",
        )
    previous = previous_file(session, profile.key, source)
    staged = StagedFile(session, source.id)
    earlier = StagedFile(session, previous.id) if previous is not None else None
    problems = [problem.body() for problem in check_profile(model, definition)]
    sources, kept = [], []
    sheet_of = [entry.sheet or (staged.sheet_names[0] if staged.sheet_names else None) for entry in definition.sources]
    named_on: dict[str | None, set[str]] = {}
    for sheet, entry in zip(sheet_of, definition.sources, strict=True):
        named_on.setdefault(sheet, set()).update(name for _, name in named_columns(entry, ""))
    for index, entry in enumerate(definition.sources):
        first_on_sheet = sheet_of.index(sheet_of[index]) == index
        found, followed = compare_columns(
            session, entry, staged, earlier, named_on[sheet_of[index]], first_on_sheet
        )
        sources.append(
            {
                "profileSource": index,
                "source": None,
                "sheet": entry.sheet or (staged.sheet_names[0] if staged.sheet_names else None),
                "objectTypeKey": entry.objectTypeKey,
                "missing": entry.missing or "report",
                **found,
            }
        )
        if followed is not None:
            kept.append((index, followed))
    # A column another source on the sheet reads under a new header is renamed there, not new.
    renamed_to = {
        (entry["sheet"], item["to"])
        for entry in sources
        for item in (entry["columns"] or {}).get("renamed", [])
    }
    for entry in sources:
        if entry["columns"] is not None:
            entry["columns"]["new"] = [
                item for item in entry["columns"]["new"] if (entry["sheet"], item["column"]) not in renamed_to
            ]
    effective: ImportProfileDefinition | None = None
    if kept and not problems:
        effective = ImportProfileDefinition.model_validate(
            {
                **definition.model_dump(mode="json", exclude_none=True, include={"csv", "valueMaps"}),
                "sources": [followed for _, followed in kept],
            }
        )
        order = source_order(model, effective) or list(range(len(kept)))
        for position, at in enumerate(order):
            sources[kept[at][0]]["source"] = position
    job.report = {
        **(job.report or {}),
        "check": {
            "profileKey": profile.key,
            "profileVersion": profile.version,
            "sourceFileId": source.public_id,
            "previousSourceFileId": previous.public_id if previous is not None else None,
            "releaseId": _release_public_id(session, job.model_release_id),
            "valid": not problems,
            "problems": problems,
            "sources": sources,
            "findings": None,
            "dryRun": None,
        },
    }
    if effective is None:
        return False
    job.parameters = {
        **job.parameters,
        "profile": {
            "key": profile.key,
            "version": profile.version,
            "definition": effective.model_dump(mode="json", exclude_none=True),
        },
    }
    return True


def record_findings(job: Job, findings: dict[str, Any] | None) -> None:
    report = dict(job.report or {})
    report["check"] = {**report["check"], "findings": findings}
    job.report = report


def record_check(
    session: Session,
    job: Job,
    outcomes: list[ItemOutcome],
    model: EngineModel,
    *,
    retention_days: int,
) -> None:
    """The check's previewed outcomes and its summary; the job completes. The caller commits."""
    require_file(session, job)
    record_outcomes(session, job, outcomes)
    found = summary(session, job, model)
    check = dict(job.report["check"])
    stored = {entry["source"]: entry["profileSource"] for entry in check["sources"]}
    for entry in found["sources"]:
        entry["profileSource"] = stored.get(entry["source"], entry["profileSource"])
    check["dryRun"] = found
    job.report = {**job.report, "check": check}
    complete_job(session, job, retention_days=retention_days)


def complete_unbound(session: Session, job: Job, *, retention_days: int) -> None:
    """A check with nothing to bind completes with its report alone."""
    complete_job(session, job, retention_days=retention_days)
    job.result = None


# --- columns ------------------------------------------------------------------------------------


def compare_columns(
    session: Session,
    source: Source,
    staged: StagedFile,
    earlier: StagedFile | None,
    sheet_named: set[str],
    reports_new: bool,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """The source's columns compared (module docstring), and the source as it reads this file:
    renamed columns under their new header, missing ones left out; ``None`` when nothing of it
    can be read (its sheet is gone, or no column it loads is left). ``sheet_named``: what every
    source on the sheet names; ``reports_new``: the source is the sheet's first, which lists the
    sheet's new columns."""
    area = Area.of(source.headerRow, source.block)
    sheet = source.sheet or (staged.sheet_names[0] if staged.sheet_names else None)
    report: dict[str, Any] = {"sheetFound": sheet in staged.sheet_names, "columns": None}
    if not report["sheetFound"]:
        return report, None
    table = staged.table(sheet, area)
    now = table.columns() if table is not None else {}
    before = None
    if earlier is not None and sheet in earlier.sheet_names:
        found = earlier.table(sheet, area)
        before = found.columns() if found is not None else None
    named = list(dict.fromkeys(name for _, name in named_columns(source, "")))
    missing = [name for name in named if name not in now]
    known = sheet_named | set(before or {})
    new = [name for name in now if name not in known]
    first = area.first_column or 1
    renamed: list[dict[str, Any]] = []
    for name in list(missing):
        if before is None or name not in before:
            continue
        at = before[name]
        candidate = next((other for other in new if now[other] == at), None)
        if candidate is None:
            continue
        share = _shared(session, earlier, staged, sheet, area, first + at)
        if share >= RENAME_SHARE:
            renamed.append(
                {"from": name, "to": candidate, "letter": _letter(first + at), "shared": share}
            )
            missing.remove(name)
            new.remove(candidate)
    report["columns"] = {
        "new": [{"column": name, "letter": _letter(first + now[name])} for name in new]
        if reports_new
        else [],
        "missing": [{"column": name} for name in missing],
        "renamed": renamed,
    }
    followed = _follow(
        source.model_dump(mode="json", exclude_none=True),
        {item["from"]: item["to"] for item in renamed},
        set(missing),
    )
    return report, followed


def _shared(
    session: Session,
    earlier: StagedFile | None,
    staged: StagedFile,
    sheet: str,
    area: Area,
    column_number: int,
) -> float:
    """The share of the larger distinct value count the column's values in both files share."""
    if earlier is None:
        return 0.0
    counts = session.execute(
        text(
            """
            WITH a AS (SELECT DISTINCT text FROM source_file_cells
                WHERE source_file_id = :a AND sheet_index = :sa AND column_number = :c
                  AND row_number > :header AND (CAST(:last AS integer) IS NULL OR row_number <= :last)),
            b AS (SELECT DISTINCT text FROM source_file_cells
                WHERE source_file_id = :b AND sheet_index = :sb AND column_number = :c
                  AND row_number > :header AND (CAST(:last AS integer) IS NULL OR row_number <= :last))
            SELECT (SELECT count(*) FROM a), (SELECT count(*) FROM b),
                (SELECT count(*) FROM a JOIN b USING (text))
            """
        ),
        {
            "a": earlier.file_id,
            "sa": earlier.sheet_names.index(sheet),
            "b": staged.file_id,
            "sb": staged.sheet_names.index(sheet),
            "c": column_number,
            "header": area.header_row,
            "last": area.last_row,
        },
    ).one()
    larger = max(counts[0], counts[1])
    return round(counts[2] / larger, 4) if larger else 0.0


def _follow(
    source: dict[str, Any], renamed: dict[str, str], missing: set[str]
) -> dict[str, Any] | None:
    """The source with renamed columns under their new header and every member naming a missing
    column left out; ``None`` when no column it loads is left or it no longer reads as a source."""
    found = copy.deepcopy(source)

    def name(value: str) -> str:
        return renamed.get(value, value)

    key = found.get("key")
    if key is not None:
        for member in ("column", "versionColumn", "nameColumn"):
            if member in key:
                key[member] = name(key[member])
        if key.get("column") in missing:
            found.pop("key")
        elif key.get("versionColumn") in missing:
            key.pop("versionColumn")
    gone = _follow_readings(found, name, missing)
    # A column a dropped reading added is missing like any other: every member that names it is
    # left out, or its binding unmapped, as for a column the file lost.
    missing = missing | gone
    columns = []
    for binding in found.get("columns", []):
        if "column" in binding:
            binding["column"] = name(binding["column"])
            if binding["column"] in missing or binding["column"] in gone:
                continue
        if "columns" in binding:
            binding["columns"] = [name(item) for item in binding["columns"] if name(item) not in missing]
            flags = binding["relationFlags"]
            flags["targets"] = {
                name(column): target
                for column, target in flags.get("targets", {}).items()
                if name(column) not in missing
            }
            if not binding["columns"]:
                continue
        relation = binding.get("relation")
        if relation is not None:
            for member in ("idColumn", "versionColumn"):
                if member in relation:
                    relation[member] = name(relation[member])
                    if relation[member] in missing:
                        relation.pop(member)
            relation["attributes"] = [
                {**value, "column": name(value["column"])}
                for value in relation.get("attributes", [])
                if name(value["column"]) not in missing
            ]
        related = binding.get("relatedRecord")
        if related is not None:
            if "versionColumn" in related:
                related["versionColumn"] = name(related["versionColumn"])
                if related["versionColumn"] in missing:
                    related.pop("versionColumn")
            parent = related.get("parent") or {}
            if "column" in parent:
                parent["column"] = name(parent["column"])
                if parent["column"] in missing:
                    continue
        columns.append(binding)
    found["columns"] = columns
    key = found.get("key")
    if key is not None and "attributeTypeKey" in key and not any(
        binding.get("attributeTypeKey") == key["attributeTypeKey"] for binding in columns
    ):
        found.pop("key")
    if "key" not in found:
        found.pop("missing", None)
    if not any(not binding.get("ignore") for binding in columns):
        return None
    try:
        return Source.model_validate(found).model_dump(mode="json", exclude_none=True)
    except ValidationError:
        return None


def _follow_readings(
    found: dict[str, Any], name: Callable[[str], str], missing: set[str]
) -> set[str]:
    """The source's readings (0.17 PP-D6, PP-D7) with renamed columns under their new header; a
    reading whose column is missing is left out, and the columns it added with it: returned, so
    the bindings that named them can go too."""
    gone: set[str] = set()
    headings = found.get("headings")
    if headings is not None:
        headings["column"] = name(headings["column"])
        if headings["column"] in missing:
            gone.add(found.pop("headings")["into"])
    if found.get("fillDown") is not None:
        kept = [name(item) for item in found["fillDown"] if name(item) not in missing]
        if kept:
            found["fillDown"] = kept
        else:
            found.pop("fillDown")
    unpivot = found.get("unpivot")
    if unpivot is not None:
        unpivot["columns"] = [name(item) for item in unpivot["columns"] if name(item) not in missing]
        if len(unpivot["columns"]) < 2:
            gone |= {unpivot["nameColumn"], unpivot["valueColumn"]}
            found.pop("unpivot")
    return gone


def previous_file(session: Session, profile_key: str, source: SourceFile) -> SourceFile | None:
    """The file the profile read before ``source``, in the same workspace: its own earlier file,
    else the stored file its last import read there; ``None`` when neither is profiled. A check in
    one workspace never compares with another's file."""
    for found in session.scalars(
        select(SourceFile)
        .where(
            SourceFile.profile_key == profile_key,
            SourceFile.id < source.id,
            SourceFile.workspace_key.is_not_distinct_from(source.workspace_key),
        )
        .order_by(SourceFile.id.desc())
        .limit(1)
    ):
        if profile_state(session, found)["state"] == "completed":
            return found
    imported = session.scalar(
        select(Job.parameters["sourceFileId"].as_string())
        .where(
            Job.kind == "import",
            Job.workspace_key.is_not_distinct_from(source.workspace_key),
            Job.parameters["profile"]["key"].as_string() == profile_key,
            Job.parameters["sourceFileId"].as_string().is_not(None),
            Job.parameters["sourceFileId"].as_string() != source.public_id,
        )
        .order_by(Job.sequence_id.desc())
        .limit(1)
    )
    if imported is None:
        return None
    found = session.scalar(select(SourceFile).where(SourceFile.public_id == imported))
    if found is None or profile_state(session, found)["state"] != "completed":
        return None
    return found


def _release_public_id(session: Session, release_db_id: int) -> str | None:
    return session.scalar(select(ModelRelease.public_id).where(ModelRelease.id == release_db_id))


def _letter(number: int) -> str:
    return get_column_letter(number)
