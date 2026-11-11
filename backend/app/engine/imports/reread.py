"""A previewed import read again with other fields (Base 0.17 EX1, PP-D26).

The preview of a matrix or relationship column says which field its cells are matched by and lets the
person choose another. Choosing starts a new preview of the same file: the profile that read the first
(a stored one, the one the workbook carries, or one given inline) with each chosen column's field
replaced, run as ``stage: preview`` again. The first preview is cancelled; nothing was written by
either.
"""

from typing import Any

from sqlalchemy.orm import Session

from ...errors import api_error
from ...models.database import Job
from ...models.imports import (
    ColumnReadingChoice,
    ImportProfileDefinition,
    ImportRequest,
    InlineProfile,
    MatchBy,
)
from ..jobs.background import open_job_context, request_cancel
from ..jobs.files import JobFiles
from ..jobs.store import AWAITING, load_job
from ..model.candidate_places import identifying_fields
from .profiles import source_order
from .submit import Upload, submit_import


def reread_import(
    session: Session,
    job_id: str,
    readings: list[ColumnReadingChoice],
    *,
    files: JobFiles,
    max_bytes: int,
    retention_days: int,
) -> Job:
    """The new preview of the waiting import ``job_id`` with ``readings`` applied."""
    job = load_job(session, job_id)
    if job.kind != "import" or job.state != AWAITING:
        raise api_error(
            409,
            "JOB_NOT_AWAITING_CONFIRMATION",
            f"Job '{job.id}' is {job.state}; only an import preview waiting for confirmation can be"
            " read again with other fields",
            {"jobId": job.id, "state": job.state},
        )
    profile = (job.parameters or {}).get("profile")
    if not profile or not profile.get("definition"):
        raise api_error(
            422,
            "IMPORT_HAS_NO_PROFILE",
            "This import was read without a profile, so it has no columns to read differently",
            {"jobId": job.id},
        )
    model = open_job_context(session, job).model
    definition = ImportProfileDefinition.model_validate(profile["definition"])
    order = source_order(model, definition) or list(range(len(definition.sources)))
    changed = definition.model_dump(mode="json", exclude_none=True)
    for index, choice in enumerate(readings):
        at = f"/readings/{index}"
        if choice.source >= len(order):
            raise _invalid(f"The binding report has no source {choice.source}", f"{at}/source")
        source = changed["sources"][order[choice.source]]
        binding = next(
            (
                item
                for item in source["columns"]
                if item.get("column") == choice.column and item.get("relation")
            ),
            None,
        )
        if binding is None:
            raise _invalid(
                f"Column '{choice.column}' is no relationship or matrix column of that source",
                f"{at}/column",
            )
        _apply(model, binding["relation"], choice.field, at)
    path = files.source(job.id)
    if not path.is_file():
        raise api_error(
            410,
            "IMPORT_FILE_MISSING",
            f"The file of import '{job.id}' is no longer in the job file directory; send it again",
        )
    parameters = job.parameters
    request = ImportRequest(
        workspaceKey=None if job.change_set_id else job.workspace_key,
        changeSetId=job.change_set_id,
        expectedChangeSetVersion=job.change_set_version,
        profile=InlineProfile.model_validate(changed),
        format=parameters["file"]["format"],
        policy=parameters["policy"],
        onExisting=parameters["onExisting"],
        otherWorkspaceIds=parameters["otherWorkspaceIds"],
        stage="preview",
    )
    origin = {key: profile[key] for key in ("key", "version", "embedded") if key in profile}
    with path.open("rb") as file:
        upload = Upload.read(parameters["file"]["name"], file, max_bytes)
        found, _ = submit_import(
            session,
            request,
            upload,
            files=files,
            idempotency_key=None,
            retention_days=retention_days,
            origin=origin,
        )
    request_cancel(session, job.id, files=files, retention_days=retention_days)
    return found


def _apply(model: Any, relation: dict[str, Any], field: str, at: str) -> None:
    """The column's relationship matched by ``field``: a matrix column's ``within.field``, any other
    relationship column's ``matchBy``."""
    choices = identifying_fields(model, relation["objectTypeKey"])
    if field not in choices:
        raise _invalid(
            f"'{field}' does not identify a '{relation['objectTypeKey']}' record; choose one of"
            f" {', '.join(choices)}",
            f"{at}/field",
        )
    within = relation.get("within")
    if within is not None:
        within["field"] = field
        within.pop("labelAttributeTypeKey", None)
    else:
        by = MatchBy(field="name") if field == "name" else MatchBy(attributeTypeKey=field)
        relation["matchBy"] = by.model_dump(exclude_none=True)
        if field != "name":
            # A value naming no record creates a record by its name only.
            relation.pop("missing", None)


def _invalid(message: str, path: str) -> Any:
    return api_error(422, "INVALID_IMPORT_READING", message, {"path": path})
