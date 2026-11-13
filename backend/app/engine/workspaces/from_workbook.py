"""A new workspace from a workbook (0.17 PL4, PP-D1, PP-D44).

One step over the engine's existing ones, in one transaction: the model draft a workbook made is
installed as a release, a workspace is created on that release, and the workbook's stored file is
queued as an ordinary import job into the workspace's live data. Nothing here reads or writes data
of its own: the draft, the install, the workspace assignment and the import are the functions the
separate routes use.
"""

import copy
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from ...db import lock_job_subject
from ...errors import api_error
from ...models.database import AiTask, Job, ModelDraft, ModelRelease, Workspace
from ...models.imports import ImportProfileDefinition, ImportRequest
from ..imports.profiles import check_profile, invalid_profile
from ..imports.submit import submit_import
from ..indexes import matrix_states
from ..jobs.files import JobFiles
from ..model.authoring.keys import key_from_label
from ..model.compiler import compile_model
from ..model.drafts import load_draft_for_update, require_draft_version
from ..model.releases import ReleaseIdentityConflict, next_free_version
from ..model.workspace_models import assign_new_workspace
from ..sources import draft_profile
from ..sources.dry_run import InvalidDraft
from ..sources.profile_export import definition as exported_profile
from ..sources.store import require_profile, stored_upload


class UnsupportedDraftSchema(Exception):
    """The draft's schema language is outside the window this deployment reads."""

    def __init__(self, schema_version: str, draft_id: str) -> None:
        super().__init__(schema_version)
        self.schema_version = schema_version
        self.draft_id = draft_id


@dataclass(frozen=True)
class FromWorkbook:
    workspace: Workspace
    release: ModelRelease
    job: Job


def free_workspace_key(session: Session, name: str) -> str:
    """A workspace key from the name, with ``-2``, ``-3``… after it when it is taken."""
    taken = set(session.scalars(select(Workspace.key)))
    return key_from_label(name, taken)


def _require_free_draft(session: Session, draft: ModelDraft) -> None:
    """The draft is no other workspace's and no assistant task's (as ``workspace_draft`` never takes
    them): ``409 DRAFT_HELD_BY_WORKSPACE`` or ``409 AI_TASK_DRAFT_HELD``."""
    if draft.workspace_key is not None:
        raise api_error(
            409,
            "DRAFT_HELD_BY_WORKSPACE",
            f"Model draft '{draft.public_id}' belongs to workspace '{draft.workspace_key}'; "
            "make a new draft to create another workspace",
            {"draftId": draft.public_id, "workspaceKey": draft.workspace_key},
        )
    if session.scalar(select(exists().where(AiTask.draft_id == draft.id))):
        raise api_error(
            409,
            "AI_TASK_DRAFT_HELD",
            "An assistant task holds this draft: make a new draft, from the same release if it "
            "should start the same",
            {"draftId": draft.public_id},
        )


def create_from_workbook(
    session: Session,
    *,
    draft_id: str,
    expected_version: int,
    name: str,
    key: str | None,
    files: JobFiles,
    max_bytes: int,
    retention_days: int,
) -> FromWorkbook:
    """Install the draft, create the workspace on its release and queue the workbook's load; one
    commit. Refused before anything is written: the draft's version, a model or profile that does
    not hold (``InvalidDraft``, ``422 INVALID_IMPORT_PROFILE``), a workbook not profiled yet, a
    workspace key that is taken."""
    draft = load_draft_for_update(session, draft_id)
    require_draft_version(draft, expected_version)
    _require_free_draft(session, draft)
    source = draft_profile.current_source(session, draft)
    if source is None:
        raise api_error(
            422,
            "DRAFT_HAS_NO_WORKBOOK",
            f"Model draft '{draft_id}' has no workbook; add one to create a workspace from it",
        )
    require_profile(session, source)
    compiled = compile_model(draft.model_json)
    if compiled.unsupported_schema_version is not None:
        raise UnsupportedDraftSchema(compiled.unsupported_schema_version, draft.public_id)
    if not compiled.valid or compiled.model is None:
        raise InvalidDraft(compiled.diagnostics)
    exported, _ = exported_profile(draft.profile_json)
    if exported is None:
        raise api_error(
            422,
            "INVALID_IMPORT_PROFILE",
            f"Model draft '{draft_id}' has no profile that loads a column",
            {"pointer": "/profile"},
        )
    problems = check_profile(compiled.model, ImportProfileDefinition.model_validate(exported))
    if problems:
        raise invalid_profile(problems)
    # One new workspace key is chosen at a time across processes until this transaction ends, so
    # a second request finds the first's workspace and takes the next free key (or is refused).
    lock_job_subject(session, "workspace-key", "new")
    workspace_key = key or free_workspace_key(session, name)
    if session.get(Workspace, workspace_key) is not None:
        raise api_error(
            409, "WORKSPACE_ALREADY_EXISTS", f"Workspace '{workspace_key}' already exists"
        )

    # A key another model's profile holds is never the person's to resolve: the draft takes a free one.
    clash = draft_profile.key_conflict(session, draft.profile_json, compiled.model.release.key)
    if clash is not None:
        draft.profile_json = {
            **(draft.profile_json or {}),
            "key": draft_profile.free_key(session, (draft.profile_json or {})["key"]),
        }
    try:
        release, _, saved = draft_profile.install_draft(session, draft, compiled.model)
    except ReleaseIdentityConflict as conflict:
        # The release's key and version are another model's: the draft takes the next free version.
        model_json = copy.deepcopy(draft.model_json)
        model_json["release"]["version"] = next_free_version(
            session, conflict.release_key, conflict.release_version
        )
        draft.model_json = model_json
        draft.version += 1
        draft.updated_at = datetime.now(UTC)
        recompiled = compile_model(draft.model_json)
        if not recompiled.valid or recompiled.model is None:
            raise InvalidDraft(recompiled.diagnostics) from None
        release, _, saved = draft_profile.install_draft(session, draft, recompiled.model)
    if saved is None:  # Checked above; the profile held against the model it was installed with.
        raise api_error(
            422,
            "INVALID_IMPORT_PROFILE",
            "The profile does not hold against the installed release",
            {"pointer": "/profile"},
        )

    workspace = Workspace(key=workspace_key, label=name.strip(), status="active")
    session.add(workspace)
    session.flush()
    assign_new_workspace(session, workspace_key, release.public_id)
    session.flush()
    matrix_states.sync_workspace(session, workspace_key)
    # The draft is the workspace's own from here: editing its model continues this draft.
    draft.workspace_key = workspace_key
    # The draft changed: a repeat of this request, which read the old version, is refused.
    draft.version += 1
    draft.updated_at = datetime.now(UTC)
    session.flush()

    request = ImportRequest(
        workspaceKey=workspace_key,
        profileKey=saved.key,
        policy="independent",
        onExisting="overwrite",
        stage="execute",
        sourceFileId=source.public_id,
    )
    with stored_upload(session, source.public_id, files=files, max_bytes=max_bytes) as upload:
        job, _ = submit_import(
            session,
            request,
            upload,
            files=files,
            idempotency_key=None,
            retention_days=retention_days,
        )
    session.refresh(workspace)
    return FromWorkbook(workspace, release, job)
