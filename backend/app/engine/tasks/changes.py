"""The records a task's latest check would change (Product 0.16 AP6a, AP6): each with the fields
that differ, what it holds now and what the load would write. A plan's are read per table of the
reading; a design's per source of its working copy, through the dry run's own profile and the
draft's model.

The check's job keeps an outcome per row; its inputs go when it completes. A page of changed
records is read from the outcomes (the record and the row it came from), and what the load would
write is read again from the row's staged cells through the plan's value maps and the attribute
types (``imports/cells.py``), the way the binding converted them: a read of one page, not set work.
The live values are the records' own.
"""

from dataclasses import dataclass
from typing import Any

from openpyxl.utils.cell import column_index_from_string
from sqlalchemy import Select, cast, select, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

from ...common.pagination import Page, PageRequest, integer_key, paginate_statement
from ...errors import ApiError, api_error
from ...models.database import (
    AiTask,
    AttributeValue,
    Job,
    JobItem,
    ModelDraft,
    RdmObject,
    SourceFile,
    SourceFileSheet,
)
from ...models.schema import EngineModel
from ..imports.cells import attribute_value, cell_text, is_empty
from ..model.compiler import compile_model
from ..records.values import row_value
from ..sources.values import unstaged


def _changed(task: AiTask, job: Job, source: int) -> Select[Any]:
    items = (
        select(JobItem.item_index, JobItem.row_number, JobItem.outcome)
        .where(
            JobItem.job_id == job.sequence_id,
            JobItem.source_index == source,
            JobItem.status == "applied",
            cast(JobItem.outcome, JSONB)["action"].astext == "updated",
        )
        .subquery()
    )
    return select(items)


def change_page(
    session: Session,
    task: AiTask,
    model: EngineModel,
    *,
    source_index: int | None = None,
    page: PageRequest,
    page_size: int,
) -> tuple[list[dict[str, Any]], Page[Any]]:
    """A page of the changed records of a source of the check (``source_index``), read against the
    draft's model."""
    where = _design_place(session, task, source_index)
    model = where.model
    job = where.job
    sub = _changed(task, job, where.index).subquery()
    found: Page[Any] = paginate_statement(
        session,
        select(sub),
        keys=(integer_key("index", sub.c.item_index, "item_index"),),
        scope="ai-task-changes",
        filters={"taskId": task.public_id, "table": where.name, "check": job.id},
        page=page,
        page_size=page_size,
        message="Change cursor is invalid",
        rows=True,
    )
    rows = list(found.items)
    ids = [row.outcome["id"] for row in rows]
    live_names = dict(
        session.execute(select(RdmObject.id, RdmObject.name).where(RdmObject.id.in_(ids))).all()
    )
    live_values: dict[str, dict[str, Any]] = {}
    for value in session.scalars(select(AttributeValue).where(AttributeValue.object_id.in_(ids))):
        live_values.setdefault(value.object_id, {})[value.attribute_type_key] = row_value(value)
    source, maps, numbers = where.source, where.maps, where.numbers
    table_id = where.name
    bound = {
        c["column"]: c
        for c in source["columns"]
        if c.get("column") in numbers and (c.get("attributeTypeKey") or c.get("field") == "name")
    }
    cells = _cells(session, task, where, [row.row_number for row in rows], list(numbers.values()))
    items = []
    for row in rows:
        record_id = row.outcome["id"]
        fields = []
        name_now = live_names.get(record_id)
        name_after = name_now
        after_values: dict[str, Any] = {}
        for header, binding in bound.items():
            raw = cells.get((row.row_number, numbers[header]))
            try:
                mapped = _mapped(raw, maps.get(binding.get("valueMap") or "", {}))
                if binding.get("field") == "name":
                    name_after = cell_text(mapped) if not is_empty(mapped) else name_now
                else:
                    definition = model.attribute_type(binding["attributeTypeKey"])
                    if definition is not None:
                        after_values[definition.key] = (
                            attribute_value(definition, mapped) if not is_empty(mapped) else None
                        )
            except ApiError:
                continue
        if name_after != name_now:
            fields.append({"field": "name", "label": "Name", "now": name_now, "after": name_after})
        for key, after in after_values.items():
            now = live_values.get(record_id, {}).get(key)
            definition = model.attribute_type(key)
            if after is not None and after != now and definition is not None:
                fields.append({"field": key, "label": definition.name, "now": now, "after": after})
        items.append(
            {
                "recordId": record_id,
                # The record as the person knows it now; a new name shows as a changed field.
                "name": name_now,
                "table": table_id,
                "fields": fields,
            }
        )
    return items, found


def _mapped(raw: Any, mapping: dict[str, Any]) -> Any:
    if raw is not None:
        key = cell_text(raw)
        if key in mapping:
            return mapping[key]
    return raw


@dataclass
class _Place:
    """Where a page of changes is read: the check's dry run, the profile's source and its value
    maps, the header → column numbers and the staged sheet of the file the dry run read."""

    job: Job
    index: int
    name: str
    source: dict[str, Any]
    maps: dict[str, Any]
    numbers: dict[str, int]
    file: int | None
    sheet: int
    model: EngineModel | None = None


def _check_job(session: Session, task: AiTask) -> Job:
    job = session.scalar(select(Job).where(Job.id == task.check["dryRunJobId"]))
    if job is None:
        raise api_error(409, "AI_TASK_STATE", "The check's dry run is no longer kept")
    return job


def _design_place(session: Session, task: AiTask, source_index: int | None) -> _Place:
    """A design task's sheet: the dry run's own profile, the working copy it read and the draft's
    model; ``422 AI_TASK_TABLE_UNKNOWN`` for a source the check has no figures for."""
    if not task.check or not task.check.get("dryRunJobId"):
        raise api_error(
            409,
            "AI_TASK_STATE",
            f"AI task '{task.public_id}' has no check yet",
            {"state": task.state},
        )
    known = [s["source"] for s in task.check.get("sheets", []) if "source" in s]
    if source_index is None or source_index not in known:
        raise api_error(
            422,
            "AI_TASK_TABLE_UNKNOWN",
            f"The latest check has no source {source_index} "
            f"(sources: {', '.join(str(k) for k in known)})",
            {"source": source_index},
        )
    job = _check_job(session, task)
    definition = job.parameters["profile"]["definition"]
    source = definition["sources"][source_index]
    file = session.scalar(
        select(SourceFile.id).where(SourceFile.public_id == job.parameters["sourceFileId"])
    )
    sheet = session.scalar(
        select(SourceFileSheet.sheet_index).where(
            SourceFileSheet.source_file_id == file, SourceFileSheet.name == source.get("sheet")
        )
    )
    if file is None or sheet is None:
        raise api_error(409, "AI_TASK_STATE", "The check's working copy is no longer kept")
    header = int(source.get("headerRow") or 1)
    numbers = {
        cell_text(unstaged(value)): column
        for column, value in session.execute(
            text(
                "SELECT column_number, value FROM source_file_cells WHERE source_file_id = :file"
                " AND sheet_index = :sheet AND row_number = :row"
            ),
            {"file": file, "sheet": sheet, "row": header},
        )
        if not is_empty(unstaged(value))
    }
    # A binding that names its column by letter (0.13 AQ) reads it as the dry run did: by the header
    # the letter holds, or `Column AJ` for an empty header cell.
    named = {column: header for header, column in numbers.items()}
    source = {
        **source,
        "columns": [_by_header(binding, numbers, named) for binding in source.get("columns") or []],
    }
    draft = session.get(ModelDraft, task.draft_id)
    compiled = compile_model(draft.model_json) if draft is not None else None
    if compiled is None or compiled.model is None:
        raise api_error(409, "AI_TASK_STATE", "The task's model draft does not compile")
    return _Place(
        job,
        source_index,
        str(source.get("sheet") or source_index),
        source,
        definition.get("valueMaps") or {},
        numbers,
        file,
        sheet,
        compiled.model,
    )


def _by_header(
    binding: dict[str, Any], numbers: dict[str, int], named: dict[int, str]
) -> dict[str, Any]:
    if "letter" not in binding:
        return binding
    number = column_index_from_string(binding["letter"])
    header = named.get(number) or f"Column {binding['letter']}"
    numbers.setdefault(header, number)
    return {**{k: v for k, v in binding.items() if k != "letter"}, "column": header}


def _cells(
    session: Session, task: AiTask, where: _Place, rows: list[int], columns: list[int]
) -> dict[tuple[int, int], Any]:
    if not rows:
        return {}
    # A plan's rows are the task's uploaded file's; a design's, the working copy its dry run read.
    owner = "c.source_file_id = :file" if where.file is not None else "f.task_id = :task"
    found = session.execute(
        text(
            "SELECT c.row_number, c.column_number, c.value FROM source_file_cells c"
            " JOIN source_files f ON f.id = c.source_file_id"
            f" WHERE {owner} AND c.sheet_index = :sheet"
            " AND c.row_number = ANY(:rows) AND c.column_number = ANY(:columns)"
        ),
        {
            "file": where.file,
            "task": task.id,
            "sheet": where.sheet,
            "rows": rows,
            "columns": columns,
        },
    )
    return {(row, column): unstaged(value) for row, column, value in found}
