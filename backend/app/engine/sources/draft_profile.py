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

from datetime import UTC, datetime
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...errors import ApiError
from ...models.database import (
    ImportProfile,
    Job,
    ModelDraft,
    ModelRelease,
    SourceFile,
    SourceFileColumn,
    SourceFileSheet,
)
from ...models.imports import ImportProfileDefinition, InlineProfile
from ...models.schema import EngineModel
from ...models.sources import DryRunRequest
from ..imports.profiles import check_profile, definition_of
from ..model.authoring.kinds import Sheet
from ..model.compiler import compile_authored_model
from ..model.diagnostics import ModelDiagnostic
from ..workspaces.catalogue import resolve_workspace
from .dry_run import submit_dry_run
from .store import profile_state

# Steps of only these kinds change nothing a load writes, so no dry run follows them (D79): labels,
# the release identity, layout, navigation and consumer API definitions.
NO_DRY_RUN = frozenset(
    {
        "setLabel",
        "setRelease",
        "setProfile",
        "addView",
        "removeView",
        "insertViewItem",
        "moveViewItem",
        "removeViewItem",
        "setViewProperty",
        "addDetailPage",
        "removeDetailPage",
        "addNavigationGroup",
        "removeNavigationGroup",
        "setNavigationGroup",
        "placeCollection",
        "addConsumerApi",
        "removeConsumerApi",
        "setConsumerApiPart",
        "insertConsumerApiPart",
        "moveConsumerApiPart",
        "removeConsumerApiPart",
    }
)


def current_source(session: Session, draft: ModelDraft) -> SourceFile | None:
    """The draft's current source file (D5: a newer upload supersedes the older)."""
    return session.scalar(
        select(SourceFile)
        .where(SourceFile.draft_id == draft.id, SourceFile.superseded_at.is_(None))
        .order_by(SourceFile.id.desc())
        .limit(1)
    )


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
        if isinstance(header, str) and header:
            headers.setdefault(sheet_index, []).append(header)
    found = {}
    for row in session.scalars(
        select(SourceFileSheet).where(SourceFileSheet.source_file_id == source.id).order_by(SourceFileSheet.sheet_index)
    ):
        found[row.name] = Sheet(row.name, (row.profile or {}).get("headerRow"), tuple(headers.get(row.sheet_index, ())))
    return found, source.name


def definition(profile: dict[str, Any] | None) -> tuple[dict[str, Any] | None, list[int]]:
    """The import profile the draft's profile stands for, and, per source in it, its position in
    the draft's profile: no ``id``, no editor members, and no source without columns."""
    if not profile or not profile.get("sources"):
        return None, []
    sources, positions = [], []
    for position, source in enumerate(profile["sources"]):
        if not source.get("columns"):
            continue
        sources.append({name: value for name, value in source.items() if name != "id"})
        positions.append(position)
    if not sources:
        return None, []
    return {"sources": sources, "valueMaps": profile.get("valueMaps") or {}}, positions


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
    compiled = compile_authored_model(draft.model_json)
    profile = draft.profile_json
    found = diagnostics(profile, compiled.model if compiled.valid else None)
    exported, _ = definition(profile)
    source = current_source(session, draft)
    return {
        "version": draft.version,
        "profile": profile,
        "definition": exported,
        "valid": exported is not None and compiled.valid and not any(_blocks(item) for item in found),
        "diagnostics": found,
        "sourceFile": (
            {"id": source.public_id, "name": source.name, "profile": profile_state(session, source)["state"]}
            if source is not None
            else None
        ),
    }


def _blocks(item: ModelDiagnostic) -> bool:
    """A warning an import would refuse the profile for (not a reminder such as a missing key)."""
    return item.code not in ("COLUMN_UNMAPPED", "SOURCE_WITHOUT_COLUMNS", "SOURCE_WITHOUT_KEY")


def runs_dry_run(operations: list[dict[str, Any]]) -> bool:
    """Whether a step of these operations can change what the load writes (D79)."""
    for operation in operations:
        name = operation.get("kind")
        if name == "restoreElements":
            name = (operation.get("undoes") or {}).get("kind")
        if name not in NO_DRY_RUN:
            return True
    return False


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
    compiled = compile_authored_model(draft.model_json)
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

