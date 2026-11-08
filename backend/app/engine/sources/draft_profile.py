"""A model draft's import profile (Product 0.10 A5, D75, D79, D80).

A draft holds one profile in ``model_drafts.profile_json``, changed only by operations
(``authoring/mapping.py``, and the model kinds through ``authoring/profile_side.py``). Beside the
import profile it holds what only the editor needs: a source's ``id``, the sheets ignored and the
**unmapped** entries a model step left. :func:`definition` is the import profile an import takes,
without them; :func:`diagnostics` are the profile's warnings, checked against the draft's own model
(D12), at ``/profile/…`` pointers; they never block installing the model.

After a step that can change what the load writes (D79), :func:`dry_run_after` queues the draft's
dry run with this profile; at installation, :func:`save_at_installation` writes it as an instance
profile checked against the release just installed (D80).
"""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...errors import ApiError, api_error
from ...models.database import (
    ImportProfile,
    Job,
    ModelDraft,
    ModelRelease,
    SourceFile,
    SourceFileCell,
    SourceFileColumn,
    SourceFileSheet,
)
from ...models.imports import ImportProfileDefinition, InlineProfile
from ...models.schema import EngineModel
from ...models.sources import DryRunRequest
from ..imports.profiles import MISMATCH, check_profile, definition_of, model_key_of
from ..model.authoring.kinds import Sheet
from ..model.compiler import compile_model
from ..model.diagnostics import ModelDiagnostic
from ..workspaces.catalogue import resolve_workspace
from .dry_run import runs_dry_run, submit_dry_run
from .profile_export import definition
from .store import profile_state


def current_source(session: Session, draft: ModelDraft) -> SourceFile | None:
    """The draft's current source file (D5: a newer upload supersedes the older)."""
    return session.scalar(
        select(SourceFile)
        .where(SourceFile.draft_id == draft.id, SourceFile.superseded_at.is_(None))
        .order_by(SourceFile.id.desc())
        .limit(1)
    )


def _row_reader(session: Session, file_id: int, sheet_index: int) -> Callable[[int], dict[int, str]]:
    """A row of the sheet's staged cells as trimmed text by column number (0.10 A8b, D126)."""

    def read(row_number: int) -> dict[int, str]:
        return {
            number: text.strip()
            for number, text in session.execute(
                select(SourceFileCell.column_number, SourceFileCell.text).where(
                    SourceFileCell.source_file_id == file_id,
                    SourceFileCell.sheet_index == sheet_index,
                    SourceFileCell.row_number == row_number,
                )
            )
            if text.strip()
        }

    return read


def sheets(session: Session, draft: ModelDraft) -> tuple[dict[str, Sheet] | None, str | None]:
    """The sheets of the draft's profiled source file, with their columns' headers, and its name;
    ``None`` when the draft has no file or it is not profiled yet."""
    source = current_source(session, draft)
    if source is None or profile_state(session, source)["state"] != "completed":
        return None, source.name if source else None
    headers: dict[int, list[str]] = {}
    for sheet_index, statistics in session.execute(
        select(SourceFileColumn.sheet_index, SourceFileColumn.statistics)
        .where(SourceFileColumn.source_file_id == source.id)
        .order_by(SourceFileColumn.sheet_index, SourceFileColumn.column_number)
    ):
        header = statistics.get("header")
        # Trimmed as the import's reader names a column (``readers.header_cell``); found on a real
        # workbook whose headers end in a space (0.10 A8a).
        if isinstance(header, str) and header.strip():
            headers.setdefault(sheet_index, []).append(header.strip())
    found = {}
    for row in session.scalars(
        select(SourceFileSheet).where(SourceFileSheet.source_file_id == source.id).order_by(SourceFileSheet.sheet_index)
    ):
        found[row.name] = Sheet(
            row.name,
            (row.profile or {}).get("headerRow"),
            tuple(headers.get(row.sheet_index, ())),
            _row_reader(session, source.id, row.sheet_index),
        )
    return found, source.name


def diagnostics(profile: dict[str, Any] | None, model: EngineModel | None) -> list[ModelDiagnostic]:
    """The profile's warnings: unmapped entries, sources without columns or key, and every problem
    the import's check finds against the draft's compiled model."""
    if not profile:
        return []
    found: list[ModelDiagnostic] = []
    for index, entry in enumerate(profile.get("unmapped") or []):
        what = entry.get("column") or entry.get("columns") or ("key" if "key" in entry else "source")
        found.append(
            ModelDiagnostic(
                "warning",
                "COLUMN_UNMAPPED",
                f"/profile/unmapped/{index}",
                f"'{what}' of sheet '{entry.get('sheet')}' is no longer mapped: "
                f"{(entry.get('because') or {}).get('kind')} took away what it named",
            )
        )
    for index, source in enumerate(profile.get("sources") or []):
        if not source.get("columns"):
            found.append(
                ModelDiagnostic("warning", "SOURCE_WITHOUT_COLUMNS", f"/profile/sources/{index}", f"Source '{source.get('id')}' maps no column yet")
            )
        elif source.get("key") is None and source.get("record", "upsert") == "upsert":
            found.append(
                ModelDiagnostic(
                    "warning",
                    "SOURCE_WITHOUT_KEY",
                    f"/profile/sources/{index}",
                    f"Source '{source.get('id')}' has no key: every row creates a record, and loading twice creates them twice",
                )
            )
    exported, positions = definition(profile)
    if exported is None:
        return found
    try:
        parsed = ImportProfileDefinition.model_validate(exported)
    except ValidationError as exc:
        for error in exc.errors():
            location = list(error["loc"])
            if location[:1] == ["sources"] and len(location) > 1 and isinstance(location[1], int):
                location[1] = positions[location[1]]
            found.append(
                ModelDiagnostic("warning", "INVALID_IMPORT_PROFILE", "/profile/" + "/".join(str(p) for p in location), error["msg"])
            )
        return found
    if model is not None:
        for problem in check_profile(model, parsed):
            found.append(ModelDiagnostic("warning", problem.code, "/profile" + _draft_path(problem.path, positions), problem.message))
    return found


def _draft_path(path: str, positions: list[int]) -> str:
    parts = path.split("/")
    if len(parts) > 2 and parts[1] == "sources" and parts[2].isdigit():
        parts[2] = str(positions[int(parts[2])])
    return "/".join(parts)


def read(session: Session, draft: ModelDraft) -> dict[str, Any]:
    """``GET /model-drafts/{id}/profile``: the profile as the draft holds it, the import profile it
    stands for, its warnings, and the source file it binds."""
    compiled = compile_model(draft.model_json)
    profile = draft.profile_json
    found = diagnostics(profile, compiled.model if compiled.valid else None)
    conflict = None
    if compiled.valid and compiled.model is not None:
        conflict = key_conflict(session, profile, compiled.model.release.key)
        found += [conflict] if conflict else []
    exported, _ = definition(profile)
    source = current_source(session, draft)
    return {
        "version": draft.version,
        "profile": profile,
        "definition": exported,
        "valid": exported is not None and compiled.valid and not any(_blocks(item) for item in found),
        "diagnostics": found,
        # The key to give the profile instead, when another model's profile holds its key.
        "freeKey": free_key(session, profile["key"]) if conflict and profile else None,
        "sourceFile": (
            {"id": source.public_id, "name": source.name, "profile": profile_state(session, source)["state"]}
            if source is not None
            else None
        ),
    }


def _blocks(item: ModelDiagnostic) -> bool:
    """A warning an import would refuse the profile for (not a reminder such as a missing key)."""
    return item.code not in ("COLUMN_UNMAPPED", "SOURCE_WITHOUT_COLUMNS", "SOURCE_WITHOUT_KEY")


def dry_run_after(
    session: Session, draft: ModelDraft, operations: list[dict[str, Any]], *, retention_days: int
) -> Job | None:
    """The dry run a step queues (D79): when it can change the load, and the draft holds a profiled
    file and a profile its model accepts. Commits when it queues one."""
    if not runs_dry_run(operations):
        return None
    source = current_source(session, draft)
    exported, _ = definition(draft.profile_json)
    if source is None or exported is None or profile_state(session, source)["state"] != "completed":
        return None
    compiled = compile_model(draft.model_json)
    if not compiled.valid or compiled.model is None:
        return None
    if any(_blocks(item) for item in diagnostics(draft.profile_json, compiled.model)):
        return None
    try:
        workspace = resolve_workspace(session, source.workspace_key, require_active=True)
        return submit_dry_run(
            session,
            draft.public_id,
            DryRunRequest(
                sourceFileId=source.public_id,
                workspaceKey=workspace.key,
                profile=InlineProfile.model_validate(exported),
            ),
            retention_days=retention_days,
        )
    except ApiError:
        # The workspace went or the file is not readable: the step stands, without a dry run.
        return None


def key_conflict(session: Session, profile: dict[str, Any] | None, model_key: str) -> ModelDiagnostic | None:
    """An error when the draft's profile would be saved under the key of another model's profile
    (0.11 D36), which would stop that model's imports: installing and loading refuse it, and the
    editor lists it with the free key it suggests (``details`` of the refusal name it too)."""
    key = (profile or {}).get("key")
    if not key:
        return None
    stored = session.scalar(select(ImportProfile).where(ImportProfile.key == key))
    if stored is None:
        return None
    owner = model_key_of(session, stored)
    if owner == model_key:
        return None
    return ModelDiagnostic(
        "error",
        MISMATCH,
        "/profile/key",
        f"Import profile '{key}' belongs to the model '{owner}'; the draft's model is '{model_key}'. "
        f"Give the draft's profile another key, such as '{free_key(session, key)}'",
    )


def free_key(session: Session, key: str) -> str:
    """``key`` with the first number after it that no stored profile has: ``key-2``, ``key-3``."""
    taken = set(session.scalars(select(ImportProfile.key).where(ImportProfile.key.like(f"{key}-%"))))
    number = 2
    while f"{key}-{number}" in taken:
        number += 1
    return f"{key}-{number}"


def require_installable(session: Session, draft: ModelDraft, model: EngineModel) -> None:
    """Before installing: ``409 IMPORT_PROFILE_MODEL_MISMATCH`` on a key conflict."""
    conflict = key_conflict(session, draft.profile_json, model.release.key)
    if conflict is not None:
        key = (draft.profile_json or {})["key"]
        stored = session.scalar(select(ImportProfile).where(ImportProfile.key == key))
        raise api_error(
            409,
            MISMATCH,
            conflict.message,
            {
                "profileKey": key,
                "modelKey": model_key_of(session, stored) if stored else None,
                "draftModelKey": model.release.key,
                "freeKey": free_key(session, key),
                "pointer": "/profile/key",
            },
        )


def save_at_installation(session: Session, draft: ModelDraft, release: ModelRelease, model: EngineModel) -> ImportProfile | None:
    """The draft's profile as the instance profile of its key, checked against the release just
    installed (D80); created, or the next version of it. Nothing when the profile does not hold
    against the release."""
    profile = draft.profile_json or {}
    exported, _ = definition(profile)
    if exported is None or not profile.get("key"):
        return None
    try:
        parsed = ImportProfileDefinition.model_validate(exported)
    except ValidationError:
        return None
    if check_profile(model, parsed):
        return None
    now = datetime.now(UTC)
    stored = session.scalar(select(ImportProfile).where(ImportProfile.key == profile["key"]).with_for_update())
    if stored is None:
        stored = ImportProfile(key=profile["key"], name=profile.get("name") or profile["key"], version=1, created_at=now)
        session.add(stored)
    else:
        stored.version += 1
        stored.name = profile.get("name") or stored.name
    stored.definition = definition_of(parsed)
    stored.checked_release_id = release.id
    stored.updated_at = now
    session.flush()
    return stored

